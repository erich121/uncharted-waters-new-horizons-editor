"""Four-digit item shuffle dialog, following the mate shuffle controls."""
import tkinter as tk
from tkinter import ttk,messagebox
from item_shops import seeded_shuffle,values
from items import catalogue
from character_mods import random_seed
MODES=('Shuffle items','Shuffle items and special items','Shuffle special items')
def open_shuffle(app):
 p=app.project
 if not p:return
 app.commit();dialog=tk.Toplevel(app.root);dialog.title('Item shop shuffle');dialog.geometry('680x560');dialog.minsize(400,380);dialog.transient(app.root);dialog.grab_set()
 frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Shuffle item locations',font=('Segoe UI',14,'bold')).pack(anchor='w')
 hint=ttk.Label(frame,text='Share the seed, option and blind mode to reproduce this shuffle. Special items are the early-morning offers (02:00–02:59). Stock counts and offer types stay the same. Start a new game.',wraplength=620);hint.pack(anchor='w',pady=(6,12))
 seed=tk.StringVar(value=p.item_seed or '0000');mode=tk.StringVar(value=MODES[2 if p.item_special_only else int(p.item_special)]);blind=tk.BooleanVar(value=p.item_blind)
 row=ttk.Frame(frame);row.pack(fill='x',pady=(0,8));ttk.Label(row,text='Seed (0000–9999)').pack(side='left',padx=(0,10));seed_entry=ttk.Entry(row,textvariable=seed,width=8);seed_entry.pack(side='left')
 choice=ttk.Combobox(frame,textvariable=mode,values=MODES,state='readonly',width=36);choice.pack(anchor='w',pady=(0,8))
 ttk.Checkbutton(frame,text='Blind shuffle — hide destinations',variable=blind).pack(anchor='w',pady=(0,8))
 preview_frame=ttk.Frame(frame);preview_frame.pack(fill='both',expand=True,pady=12);preview=tk.Listbox(preview_frame,height=12,exportselection=False);preview.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(preview_frame,command=preview.yview);scroll.pack(side='right',fill='y');preview.configure(yscrollcommand=scroll.set)
 candidates={};names={i['id']:i['name']for i in catalogue(p.rom)}
 def refresh(*args):
  candidates.clear();preview.delete(0,'end')
  try:edits=seeded_shuffle(p.rom,seed.get(),blind.get(),mode.get()==MODES[1],mode.get()==MODES[2]);candidates['edits']=edits
  except ValueError:preview.insert('end','Enter four digits to preview item locations.');return
  if blind.get():preview.insert('end','Blind shuffle: destinations are hidden.');return
  from ports import PORT_NAMES
  for port,slots in enumerate(values(p.rom,edits)):
   for slot,item in enumerate(slots):
    if item!=255:preview.insert('end',PORT_NAMES[port]+' — '+names[item]+(' (early morning)'if slot==3 else ''))
 def apply():
  try:p.set_item_shuffle(seed.get(),blind.get(),mode.get()==MODES[1],mode.get()==MODES[2]);app.reload_project_view();dialog.destroy()
  except ValueError as error:messagebox.showerror('Could not shuffle items',str(error),parent=dialog)
 def restore():
  p.item_edits=[];p.item_seed=None;p.item_blind=False;p.item_special=False;p.item_special_only=False;app.reload_project_view();dialog.destroy()
 buttons=ttk.Frame(frame);buttons.pack(fill='x');widgets=[]
 for label,command in [('Random seed',lambda:seed.set(random_seed())),('Apply shuffle',apply),('Restore stock items',restore),('Cancel',dialog.destroy)]:
  button=ttk.Button(buttons,text=label,command=command);widgets.append(button)
 def arrange(event):
  row=column=used=0
  for button in widgets:
   width=button.winfo_reqwidth()+6
   if used and used+width>event.width:row+=1;column=used=0
   button.grid(row=row,column=column,sticky='w',padx=(0,6),pady=3);used+=width;column+=1
 buttons.bind('<Configure>',arrange);frame.bind('<Configure>',lambda event:hint.configure(wraplength=max(250,event.width-32)))
 for variable in (seed,mode,blind):variable.trace_add('write',refresh)
 app.item_shuffle_dialog=dialog;app.item_shuffle_seed=seed;app.item_shuffle_mode=mode;app.item_shuffle_blind=blind;app.item_shuffle_preview=preview;app.item_shuffle_candidates=candidates;app.item_shuffle_buttons=widgets
 refresh()
