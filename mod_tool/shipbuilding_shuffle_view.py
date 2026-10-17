"""Review building locations for the original hulls before applying."""
import tkinter as tk
from tkinter import ttk,messagebox
from character_mods import random_seed
from shipbuilding_shuffle import generate
from ports import PORT_NAMES

def open_shuffle(app):
 p=app.project
 if not p:return
 app.commit();config=p.shipbuilding_shuffle
 dialog=tk.Toplevel(app.root);dialog.title('Ship building randomizer');dialog.geometry('800x580');dialog.minsize(460,360);dialog.transient(app.root);dialog.grab_set()
 frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Ship building randomizer',font=('Segoe UI',14,'bold')).pack(anchor='w')
 hint=ttk.Label(frame,text='Shuffle stock building-location groups among the original 25 ships. Keep ship stats, prices, industry requirements and added ships unchanged. Port offer counts stay the same; new capital assignments must be reachable. Existing stock capital restrictions remain. A new game is not required for new-build offers; restart the emulator and use a normal save.',wraplength=740);hint.pack(anchor='w',pady=(6,12))
 seed=tk.StringVar(value=config['seed']or '0000');blind=tk.BooleanVar(value=config['blind'])
 row=ttk.Frame(frame);row.pack(anchor='w');ttk.Label(row,text='Seed (0000–9999)').pack(side='left',padx=(0,8));ttk.Entry(row,textvariable=seed,width=8).pack(side='left')
 ttk.Checkbutton(frame,text='Blind shuffle — hide destinations',variable=blind).pack(anchor='w',pady=(8,0))
 footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(12,0))
 box=ttk.Frame(frame);box.pack(fill='both',expand=True,pady=(12,0))
 x=ttk.Scrollbar(box,orient='horizontal');x.pack(side='bottom',fill='x');y=ttk.Scrollbar(box);y.pack(side='right',fill='y')
 preview=tk.Listbox(box,exportselection=False,xscrollcommand=x.set,yscrollcommand=y.set);preview.pack(fill='both',expand=True);x.configure(command=preview.xview);y.configure(command=preview.yview)
 candidates={}
 def refresh(*args):
  preview.delete(0,'end');candidates.clear()
  try:offers=generate(p,seed.get(),blind.get())
  except ValueError as error:preview.insert('end',str(error));return
  candidates['offers']=offers
  if blind.get():preview.insert('end','Blind shuffle: ship building destinations are hidden.');return
  for ship,offer,old in zip(p.ships,offers,p.original_availability):
   preview.insert('end',ship['name']+' — industry '+str(offer['industry']))
   preview.insert('end','  Current: '+', '.join(PORT_NAMES[i]for i in old['ports']))
   preview.insert('end','  Proposed: '+', '.join(PORT_NAMES[i]for i in offer['ports']))
 def apply():
  try:p.set_shipbuilding_shuffle(seed.get(),blind.get());app.reload_project_view();dialog.destroy()
  except ValueError as error:messagebox.showerror('Ship building randomizer',str(error),parent=dialog)
 def restore():
  try:p.clear_shipbuilding_shuffle();app.reload_project_view();dialog.destroy()
  except ValueError as error:messagebox.showerror('Ship building randomizer',str(error),parent=dialog)
 buttons=[]
 for label,command in [('Random seed',lambda:seed.set(random_seed())),('Apply shuffle',apply),('Restore previous locations',restore),('Cancel',dialog.destroy)]:buttons.append(ttk.Button(footer,text=label,command=command))
 def arrange(event):
  row=column=used=0
  for button in buttons:
   width=button.winfo_reqwidth()+6
   if used and used+width>event.width:row+=1;column=used=0
   button.grid(row=row,column=column,sticky='w',padx=(0,6),pady=3);used+=width;column+=1
 footer.bind('<Configure>',arrange);frame.bind('<Configure>',lambda e:hint.configure(wraplength=max(260,e.width-32)))
 for variable in (seed,blind):variable.trace_add('write',refresh)
 app.shipbuilding_shuffle_dialog=dialog;app.shipbuilding_shuffle_seed=seed;app.shipbuilding_shuffle_blind=blind;app.shipbuilding_shuffle_preview=preview;app.shipbuilding_shuffle_buttons=buttons;app.shipbuilding_shuffle_candidates=candidates
 dialog.bind('<Escape>',lambda e:dialog.destroy());refresh()
