"""Item-shop editing controls, paired with the read-only map and picture."""
import tkinter as tk
from tkinter import ttk,messagebox
from item_shops import change,restore_item,stock,values
class ItemShopPanel(ttk.Frame):
 def __init__(self,world,parent):
  super().__init__(parent,style='Card.TFrame',padding=(0,10));self.world=world;self.loading=False
  self.enabled=tk.BooleanVar(value=False);self.enable_box=ttk.Checkbutton(world.edit_controls,text='Use custom items',variable=self.enabled,command=self.toggle,state='disabled')
  self.port=tk.StringVar();self.kind=tk.StringVar(value='Regular')
  ttk.Label(self,text='Port',style='Card.TLabel').grid(row=0,column=0,sticky='w',padx=(0,8))
  self.port_box=ttk.Combobox(self,textvariable=self.port,state='disabled',width=24);self.port_box.grid(row=0,column=1,sticky='ew');self.port_box.bind('<<ComboboxSelected>>',self.pick)
  ttk.Label(self,text='Offer',style='Card.TLabel').grid(row=1,column=0,sticky='w',pady=8)
  self.kind_box=ttk.Combobox(self,textvariable=self.kind,values=['Regular','Early morning'],state='disabled',width=24);self.kind_box.grid(row=1,column=1,sticky='ew');self.kind_box.bind('<<ComboboxSelected>>',self.update_offer)
  buttons=ttk.Frame(self,style='Card.TFrame');buttons.grid(row=2,column=0,columnspan=2,sticky='w')
  self.add_button=ttk.Button(buttons,text='Add port',command=self.add);self.add_button.pack(side='left')
  self.remove_button=ttk.Button(buttons,text='Remove port',command=self.remove);self.remove_button.pack(side='left',padx=5)
  self.restore_button=ttk.Button(self,text='Restore this item',command=self.restore);self.restore_button.grid(row=3,column=0,columnspan=2,sticky='w',pady=8)
  ttk.Label(self,text='Three regular slots and one early-morning slot per port. Early offers: 02:00–02:59. Full slots are never overwritten. Use a new game.',style='Hint.Card.TLabel',wraplength=300).grid(row=4,column=0,columnspan=2,sticky='w')
  self.columnconfigure(1,weight=1)
 def toggle(self):
  if not self.world.editor.project:return
  self.world.editor.project.custom_items=self.enabled.get();self.world.editor.update_status()
 def show(self):
  project=self.world.editor.project
  if not project:return
  self.loading=True;enabled=project.custom_items;self.enabled.set(enabled);self.enable_box.configure(state='normal')
  self.port_box.configure(values=[p['name']for p in self.world.port_records[:100]],state='readonly'if enabled else 'disabled')
  port=self.world.good_port_selected
  if port is None:port=max(0,self.port_box.current())
  self.port_box.current(port);row=values(project.rom,project.item_edits)[port];present=self.world.selected in row
  self.kind.set('Early morning'if present and row.index(self.world.selected)==3 else 'Regular')
  changed=row!=stock(project.rom)[port]and present and row.index(self.world.selected)!= (stock(project.rom)[port].index(self.world.selected)if self.world.selected in stock(project.rom)[port]else None)
  self.kind_box.configure(state='readonly'if enabled else 'disabled',style='Changed.TCombobox'if changed else 'TCombobox')
  self.add_button.configure(state='normal'if enabled and not present else 'disabled');self.remove_button.configure(state='normal'if enabled and present else 'disabled');self.restore_button.configure(state='normal'if enabled else 'disabled');self.loading=False
 def pick(self,event=None):
  self.world.good_port_selected=self.port_box.current();port=str(self.port_box.current())
  if self.world.goods_tree.exists(port):self.world.goods_tree.selection_set(port)
  else:self.world.goods_tree.selection_remove(*self.world.goods_tree.selection())
  self.show();self.world.draw_map()
 def apply(self,remove=False):
  project=self.world.editor.project
  if not project or not project.custom_items or self.world.items_hidden():return
  try:
   project.item_edits=change(project.rom,project.item_edits,self.port_box.current(),self.world.selected,early=self.kind.get()=='Early morning',remove=remove)
   project.item_seed=None;self.world.good_port_selected=self.port_box.current();self.world.editor.update_status()
  except ValueError as error:messagebox.showerror('Item shops',str(error),parent=self.world.editor.root);self.show()
 def add(self):self.apply()
 def remove(self):self.apply(remove=True)
 def update_offer(self,event=None):
  if self.loading:return
  project=self.world.editor.project
  if project and self.world.selected in values(project.rom,project.item_edits)[self.port_box.current()]:self.apply()
 def restore(self):
  project=self.world.editor.project
  if not project or not project.custom_items or self.world.items_hidden():return
  try:project.item_edits=restore_item(project.rom,project.item_edits,self.world.selected);project.item_seed=None;self.world.editor.update_status()
  except ValueError as error:messagebox.showerror('Restore item',str(error),parent=self.world.editor.root)
