"""Separate mate/captain seed and preview dialogs over shared native records."""
import tkinter as tk
from tkinter import ttk,messagebox
from character_mods import (MATE_SHUFFLES,CAPTAIN_SHUFFLES,group_active,group_settings,configure_group,preview_changes,random_seed,validate_seed,seeded_ports)
from sailors import decode_sailors
LABELS={'ports':'Random starting ports','names':'Random first and last names','mate_stats':'Random stats (50–100)','mate_skills':'Random skills','captain_names':'Random first and last names','captain_stats':'Random stats (50–100)','captain_skills':'Random skills'}

def open_shuffle(app,group='all'):
 p=app.project
 if not p:return
 try:app.commit()
 except ValueError as error:app.fail(error);return
 config=p.free_agent_shuffle;settings=group_settings(config,'captain_names')if group=='captains'else config
 keys=MATE_SHUFFLES if group=='mates'else CAPTAIN_SHUFFLES if group=='captains'else MATE_SHUFFLES+CAPTAIN_SHUFFLES
 title='Random mates'if group=='mates'else 'Random fleet captains'if group=='captains'else 'People shuffle'
 dialog=tk.Toplevel(app.root);dialog.title(title);dialog.geometry('740x670'if group!='all'else '740x760');dialog.minsize(420,400);dialog.transient(app.root);dialog.grab_set()
 frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text=title,font=('Segoe UI',14,'bold')).pack(anchor='w')
 hint=ttk.Label(frame,text='Preview changes from the original game. Stats keep each person’s total (50–100); skills keep their count. Share the four-digit seed and options to repeat the result. Start a new game.',wraplength=680);hint.pack(anchor='w',pady=(6,10))
 if config.get('option_settings'):hint.configure(text=hint.cget('text')+' Some options may retain seeds from earlier presets. Applying here replaces this group with the seed and options below.')
 seed=tk.StringVar(value=settings['seed']);blind=tk.BooleanVar(value=settings['blind'])
 row=ttk.Frame(frame);row.pack(fill='x',pady=(0,8));ttk.Label(row,text='Seed (0000–9999)').pack(side='left',padx=(0,10));entry=ttk.Entry(row,textvariable=seed,width=8);entry.pack(side='left')
 ttk.Checkbutton(frame,text='Blind shuffle — hide preview',variable=blind).pack(anchor='w',pady=(0,6))
 variables={key:tk.BooleanVar(value=config.get(key,key=='ports'))for key in MATE_SHUFFLES+CAPTAIN_SHUFFLES}
 # Provide a useful initial selection for a group that has not been configured.
 if group=='mates'and not group_active(config,group):variables['ports'].set(True)
 if group=='captains'and not group_active(config,group):variables['captain_names'].set(True)
 widgets={}
 for key in keys:
  w=ttk.Checkbutton(frame,text=LABELS[key],variable=variables[key]);w.pack(anchor='w',pady=(0,5));widgets[key]=w
 preview_frame=ttk.Frame(frame);preview_frame.pack(fill='both',expand=True,pady=10)
 x=ttk.Scrollbar(preview_frame,orient='horizontal');x.pack(side='bottom',fill='x')
 y=ttk.Scrollbar(preview_frame);y.pack(side='right',fill='y')
 preview=tk.Listbox(preview_frame,height=12,exportselection=False,xscrollcommand=x.set,yscrollcommand=y.set);preview.pack(fill='both',expand=True);x.configure(command=preview.xview);y.configure(command=preview.yview)
 candidates={};records=decode_sailors(p.rom)
 def candidate(enabled=True):return configure_group(p.rom,p.free_agent_shuffle,group,seed.get(),blind.get(),{key:variables[key].get()for key in keys},enabled)
 def refresh(*args):
  preview.delete(0,'end');candidates.clear()
  try:validate_seed(seed.get());proposed=candidate()
  except ValueError:preview.insert('end','Enter four digits to preview changes.');return
  candidates[blind.get()]=seeded_ports(p.rom,seed.get(),blind.get())if group!='captains'and variables['ports'].get()else []
  if not any(variables[k].get()for k in keys):preview.insert('end','Select at least one random option.');return
  if blind.get():preview.insert('end','Blind shuffle: changes are hidden.');return
  count=0
  for change in preview_changes(p.rom,p.character_edits,proposed):
   if group=='mates'and records[change['id']]['role']!='Free agent':continue
   if group=='captains'and records[change['id']]['role']!='Fleet captain':continue
   preview.insert('end',change['name']);count+=1
   for label,before,after in change['changes']:preview.insert('end','  '+label+': '+str(before)+' → '+str(after))
   preview.insert('end','')
  if not count:preview.insert('end','No values differ from the original game for these options.')
 def apply(enabled=True):
  try:
   if enabled and not any(variables[k].get()for k in keys):raise ValueError('Select at least one random option.')
   p.free_agent_shuffle=candidate(enabled);app.reload_project_view();dialog.destroy()
  except ValueError as error:messagebox.showerror('Could not configure random characters',str(error),parent=dialog)
 buttons=ttk.Frame(frame);buttons.pack(side='bottom',fill='x',before=preview_frame);actions=[]
 for label,command in [('Random seed',lambda:seed.set(random_seed())),('Apply shuffle',lambda:apply()),('Restore stock',lambda:apply(False)),('Cancel',dialog.destroy)]:actions.append(ttk.Button(buttons,text=label,command=command))
 def arrange(event):
  row=col=used=0
  for w in actions:
   width=w.winfo_reqwidth()+6
   if used and used+width>event.width:row+=1;col=used=0
   w.grid(row=row,column=col,sticky='w',padx=(0,6),pady=3);used+=width;col+=1
 buttons.bind('<Configure>',arrange);frame.bind('<Configure>',lambda event:hint.configure(wraplength=max(260,event.width-32)))
 for v in [seed,blind]+[variables[k]for k in keys]:v.trace_add('write',refresh)
 app.shuffle_dialog=dialog;app.shuffle_preview=preview;app.shuffle_candidates=candidates;app.shuffle_seed=seed;app.shuffle_seed_entry=entry;app.shuffle_blind=blind;app.shuffle_buttons=actions;app.shuffle_option_widgets=widgets;app.shuffle_group=group
 for key,alias in [('ports','ports_enabled'),('names','names'),('mate_stats','mate_stats'),('mate_skills','mate_skills'),('captain_names','captain_names'),('captain_stats','captain_stats'),('captain_skills','captain_skills')]:setattr(app,'shuffle_'+alias,variables[key])
 refresh()
