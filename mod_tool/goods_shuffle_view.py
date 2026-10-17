"""Trade-location shuffle, using the existing per-port goods patch."""
import tkinter as tk
from tkinter import ttk,messagebox
from trade_goods import seeded_shuffle,offers
from goods import catalogue
from character_mods import random_seed
MODES={'Shuffle normal goods':'normal','Shuffle specialty goods':'specialty','Shuffle all goods':'all'}

def open_shuffle(app):
 p=app.project
 if not p:return
 app.commit();dialog=tk.Toplevel(app.root);dialog.title('Goods seed shuffle');dialog.geometry('700x590');dialog.minsize(400,380);dialog.transient(app.root);dialog.grab_set()
 frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Shuffle goods',font=('Segoe UI',14,'bold')).pack(anchor='w')
 hint=ttk.Label(frame,text='The same four-digit seed, option and blind mode reproduce the same arrangement. Normal and specialty goods shuffle within their own groups. Port offer counts and economy gates stay the same; base prices travel with their goods. Replaces current goods locations. Start a new game.',wraplength=640);hint.pack(anchor='w',pady=(6,12))
 seed=tk.StringVar(value=p.goods_shuffle['seed']or '0000');mode=tk.StringVar(value=next(k for k,v in MODES.items()if v==p.goods_shuffle['mode']))
 row=ttk.Frame(frame);row.pack(fill='x',pady=(0,8));ttk.Label(row,text='Seed (0000–9999)').pack(side='left',padx=(0,10));entry=ttk.Entry(row,textvariable=seed,width=8);entry.pack(side='left')
 choice=ttk.Combobox(frame,textvariable=mode,values=list(MODES),state='readonly',width=32);choice.pack(anchor='w',pady=(0,8))
 blind=tk.BooleanVar(value=p.goods_shuffle.get('blind',False));ttk.Checkbutton(frame,text='Blind shuffle — hide destinations',variable=blind).pack(anchor='w')
 box=ttk.Frame(frame);box.pack(fill='both',expand=True,pady=12);preview=tk.Listbox(box,height=12,exportselection=False);preview.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(box,command=preview.yview);scroll.pack(side='right',fill='y');preview.configure(yscrollcommand=scroll.set)
 names={r['id']:r['name']for r in catalogue(p.rom)};candidates={}
 def refresh(*args):
  candidates.clear();preview.delete(0,'end')
  try:edits=seeded_shuffle(p.rom,seed.get(),MODES[mode.get()],blind.get());candidates['edits']=edits
  except (ValueError,KeyError):preview.insert('end','Enter four digits to preview goods locations.');return
  if blind.get():preview.insert('end','Blind shuffle: destinations are hidden.');return
  from ports import PORT_NAMES
  for port,row in enumerate(offers(p.rom,edits)):
   for offer in row:preview.insert('end',PORT_NAMES[port]+' — '+names[offer['good']]+(' (specialty)'if offer['kind']=='Specialty'else '')+' — economy '+str(offer['economy_required']))
 def apply():
  try:p.set_goods_shuffle(seed.get(),MODES[mode.get()],blind.get());app.reload_project_view();dialog.destroy()
  except ValueError as error:messagebox.showerror('Could not shuffle goods',str(error),parent=dialog)
 def restore():
  p.goods_edits=[];p.goods_shuffle=dict(seed=None,mode='normal');app.reload_project_view();dialog.destroy()
 buttons=ttk.Frame(frame);buttons.pack(fill='x');widgets=[]
 for label,command in [('Random seed',lambda:seed.set(random_seed())),('Apply shuffle',apply),('Restore stock goods',restore),('Cancel',dialog.destroy)]:widgets.append(ttk.Button(buttons,text=label,command=command))
 def arrange(event):
  row=column=used=0
  for button in widgets:
   width=button.winfo_reqwidth()+6
   if used and used+width>event.width:row+=1;column=used=0
   button.grid(row=row,column=column,sticky='w',padx=(0,6),pady=3);used+=width;column+=1
 buttons.bind('<Configure>',arrange);frame.bind('<Configure>',lambda event:hint.configure(wraplength=max(250,event.width-32)))
 for variable in (seed,mode,blind):variable.trace_add('write',refresh)
 app.goods_shuffle_blind=blind
 app.goods_shuffle_dialog=dialog;app.goods_shuffle_seed=seed;app.goods_shuffle_mode=mode;app.goods_shuffle_preview=preview;app.goods_shuffle_candidates=candidates;app.goods_shuffle_buttons=widgets
 refresh()
