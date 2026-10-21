"""Economy editing view; information-only ports share its projected values."""
import tkinter as tk
from tkinter import ttk,messagebox
from economy import stock,values,update,bulk

class EconomyPanel(ttk.Frame):
 def __init__(self,world):
  super().__init__(world.detail_panel,style='Surface.TFrame',padding=12)
  self.world=world;self.loading=False;self.timer=None;self.port=0;self.pending=None;self.proposal=None
  self.enabled=tk.BooleanVar(value=False)
  self.enable_box=ttk.Checkbutton(world.edit_controls,text='Use custom values',variable=self.enabled,command=self.toggle,state='disabled')
  ttk.Label(self,text='Enable manual editing. Current values still apply when unchecked.',style='Hint.Card.TLabel',wraplength=350).pack(anchor='w',pady=(0,10))
  ttk.Label(self,text='Port economy',style='CardTitle.TLabel').pack(anchor='w',pady=(0,10))
  fields=ttk.Frame(self,style='Card.TFrame');fields.pack(fill='x');self.variables={};self.entries={}
  for row,(key,label)in enumerate((('economy','Goods economy'),('industry','Shipbuilding industry'))):
   ttk.Label(fields,text=label,style='Card.TLabel').grid(row=row,column=0,sticky='w',pady=5,padx=(0,10))
   variable=tk.StringVar();entry=ttk.Spinbox(fields,textvariable=variable,from_=1,to=1000,width=8)
   entry.grid(row=row,column=1,sticky='w');self.variables[key]=variable;self.entries[key]=entry
   variable.trace_add('write',self.schedule)
  ttk.Label(self,text='1–1000. Changes apply automatically to this port.',style='Hint.Card.TLabel',wraplength=350).pack(anchor='w',pady=(6,8))
  self.restore_button=ttk.Button(self,text='Restore port',command=self.restore_port);self.restore_button.pack(anchor='w')
  ttk.Separator(self).pack(fill='x',pady=12)
  ttk.Label(self,text='Adjust region',style='CardTitle.TLabel').pack(anchor='w')
  self.scope=ttk.Label(self,style='Hint.Card.TLabel',wraplength=350);self.scope.pack(anchor='w',pady=(5,10))
  controls=ttk.Frame(self,style='Card.TFrame');controls.pack(fill='x')
  self.operation=tk.StringVar(value='Set to');self.operation_box=ttk.Combobox(controls,textvariable=self.operation,values=['Set to','Add','Scale %'],state='readonly',width=10)
  self.operation_box.grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,8));self.operation.trace_add('write',self.preview)
  self.bulk_vars={};self.bulk_entries={}
  for row,(key,label)in enumerate((('economy','Goods economy'),('industry','Shipbuilding industry')),1):
   ttk.Label(controls,text=label,style='Card.TLabel').grid(row=row,column=0,sticky='w',pady=4,padx=(0,10))
   var=tk.StringVar();entry=ttk.Entry(controls,textvariable=var,width=8);entry.grid(row=row,column=1,sticky='w');self.bulk_entries[key]=entry;self.bulk_vars[key]=var;var.trace_add('write',self.preview)
  ttk.Label(self,text='Blank keeps a value unchanged. 100% keeps its level. Results are limited to 1–1000.',style='Hint.Card.TLabel',wraplength=350).pack(anchor='w',pady=(8,10))
  table=ttk.Frame(self,style='Card.TFrame');table.pack(fill='both',expand=True)
  self.tree=ttk.Treeview(table,columns=('port','old_e','new_e','old_i','new_i'),show='headings',height=7,selectmode='none')
  for key,label,width in [('port','Port',65),('old_e','Goods',45),('new_e','After',45),('old_i','Shipbuilding',100),('new_i','After',45)]:
   self.tree.heading(key,text=label,anchor='center');self.tree.column(key,width=width,minwidth=100 if key=='old_i'else 45,stretch=True,anchor='center')
  self.tree.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(table,command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set)
  self.tree.tag_configure('changed',foreground='#ef7800',background='#fff5e9')
  self.preview_status=ttk.Label(self,style='Hint.Card.TLabel',wraplength=350);self.preview_status.pack(anchor='w',pady=8)
  buttons=ttk.Frame(self,style='Card.TFrame');buttons.pack(fill='x')
  self.apply_button=ttk.Button(buttons,text='Apply to region',command=self.apply_region,state='disabled');self.apply_button.pack(side='left')
  self.restore_region_button=ttk.Button(buttons,text='Restore region',command=self.restore_region);self.restore_region_button.pack(side='left',padx=5)
  ttk.Label(self,text='Starting values only. Use a new game. Capitals keep their fixed investment rules; supply ports have no economy records.',style='Hint.Card.TLabel',wraplength=350).pack(anchor='w',pady=(10,0))
 def group(self):
  region=self.world.region.get()
  return [p['id']for p in self.world.port_records[:100]if region=='All regions'or p['region']==region]
 def show(self,port):
  self.port=port;project=self.world.editor.project
  if not project:return
  self.enable_box.configure(state='normal');self.enabled.set(project.custom_economy)
  for widget in [*self.entries.values(),*self.bulk_entries.values(),self.restore_button,self.restore_region_button]:widget.configure(state='normal'if project.custom_economy else 'disabled')
  self.operation_box.configure(state='readonly'if project.custom_economy else 'disabled')
  row=values(project.rom,project.economy_edits)[port];original=stock(project.rom)[port];self.loading=True
  draft=self.pending[1]if self.pending and self.pending[0]==port else {}
  for key,var in self.variables.items():
   var.set(draft.get(key,str(row[key])));self.entries[key].configure(style='Changed.TSpinbox'if row[key]!=original[key]else 'TSpinbox')
  self.loading=False;self.preview()
 def toggle(self):
  if not self.world.editor.project:return
  wanted=self.enabled.get()
  if not self.world.commit_edits():self.enabled.set(self.world.editor.project.custom_economy);return
  self.world.editor.project.custom_economy=wanted;self.world.editor.update_status()
 def schedule(self,*args):
  if self.loading or self.world.view!='Economy'or not self.world.editor.project or not self.world.editor.project.custom_economy:return
  if self.timer is not None:self.world.editor.root.after_cancel(self.timer)
  self.pending=(self.port,{k:v.get()for k,v in self.variables.items()})
  self.timer=self.world.editor.root.after(350,self.flush)
 def cancel(self,discard=True):
  if self.timer is not None:self.world.editor.root.after_cancel(self.timer);self.timer=None
  if discard:self.pending=None
 def flush(self,strict=False):
  if self.pending is None:return
  self.cancel(discard=False);port,raw=self.pending;project=self.world.editor.project
  if not project or not project.custom_economy:self.pending=None;return
  try:edits=update(project.rom,project.economy_edits,port,**{k:int(v)for k,v in raw.items()})
  except ValueError:
   error=ValueError('Economy and industry must be whole numbers from 1 to 1000. Correct the entry or use Restore port.')
   if strict:raise error
   self.world.editor.status.configure(text='Finish editing: '+str(error));return
  self.pending=None;project.economy_edits=edits;self.world.editor.update_status()
 def preview(self,*args):
  if not self.world.editor.project:return
  project=self.world.editor.project;ports=self.group();region=self.world.region.get()
  self.scope.configure(text=f'{region}: {len(ports)} trading ports. Search filters the browser only; this batch covers every port in the group.')
  self.apply_button.configure(text='Apply to all ports'if region=='All regions'else 'Apply to region')
  self.restore_region_button.configure(text='Restore all ports'if region=='All regions'else 'Restore region')
  before=values(project.rom,project.economy_edits);self.proposal=None
  try:
   targets={k:int(v.get())if v.get().strip()else None for k,v in self.bulk_vars.items()}
   self.proposal=bulk(project.rom,project.economy_edits,ports,self.operation.get(),**targets)
   after=values(project.rom,self.proposal);count=sum(before[p]!=after[p]for p in ports)
   self.preview_status.configure(text=f'{count} ports will change.');self.apply_button.configure(state='normal'if count and project.custom_economy else 'disabled')
  except ValueError as error:
   after=before;self.preview_status.configure(text=str(error));self.apply_button.configure(state='disabled')
  self.tree.delete(*self.tree.get_children())
  for p in ports:self.tree.insert('','end',iid=str(p),values=(self.world.port_records[p]['name'],before[p]['economy'],after[p]['economy'],before[p]['industry'],after[p]['industry']),tags=('changed',)if before[p]!=after[p]or before[p]!=stock(project.rom)[p]else ())
 def apply_region(self):
  if not self.world.editor.project or not self.world.editor.project.custom_economy:return
  if not self.world.commit_edits():return
  self.preview()
  if self.proposal is None:return
  self.world.editor.project.economy_edits=self.proposal;self.world.editor.update_status()
 def restore_port(self):
  if not self.world.editor.project or not self.world.editor.project.custom_economy:return
  self.cancel();project=self.world.editor.project
  project.economy_edits=[r for r in project.economy_edits if r['port']!=self.port];self.world.editor.update_status()
 def restore_region(self):
  if not self.world.editor.project or not self.world.editor.project.custom_economy:return
  ports=self.group()
  if not messagebox.askyesno('Restore region',f'Restore economy and industry for all {len(ports)} trading ports in {self.world.region.get()}? Other edits are kept.',parent=self.world.editor.root):return
  self.cancel();project=self.world.editor.project
  project.economy_edits=[r for r in project.economy_edits if r['port']not in ports];self.world.editor.update_status()
