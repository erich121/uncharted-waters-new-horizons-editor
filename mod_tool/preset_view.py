"""Review a prepared preset before changing the project."""
import tkinter as tk
from tkinter import ttk
from easy_presets import PRESETS,RANDOMIZED,preview,apply_plan

def open_preview(app):
 project=app.project;name=app.easy_preset.get();seed=app.easy_seed.get();blind=app.easy_blind.get()
 changes,lines=preview(project,name,seed,blind)
 before=project.manifest()
 dialog=tk.Toplevel(app.root);dialog.title('Review preset — '+name);dialog.geometry('780x570');dialog.minsize(480,360);dialog.transient(app.root);dialog.grab_set()
 frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text=name,font=('Segoe UI',16,'bold')).pack(anchor='w')
 description=ttk.Label(frame,text=PRESETS.get(name,'Legacy preset'),wraplength=720);description.pack(anchor='w',pady=(8,12))
 if name in RANDOMIZED:ttk.Label(frame,text=('Blind shuffle • Destinations hidden'if blind else 'Seed '+seed)+' • New game required').pack(anchor='w',pady=(0,8))
 footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(12,0))
 box=ttk.Frame(frame);box.pack(fill='both',expand=True)
 text=tk.Text(box,wrap='word',font=('Segoe UI',11),width=35,height=10,relief='flat',padx=12,pady=12,background='white',foreground='#17243d')
 scroll=ttk.Scrollbar(box,command=text.yview);scroll.pack(side='right',fill='y');text.pack(fill='both',expand=True);text.configure(yscrollcommand=scroll.set)
 text.insert('end','Changes from your current settings\n\n'+'\n\n'.join(lines)+'\n\nOnly the settings listed above will change. Other settings stay as they are. Applying a preset again does not stack increases. Starting-world and character changes require a new game; fleet changes appear as ships are replaced.');text.configure(state='disabled')
 def apply():
  if app.project is not project or project.manifest()!=before:app.status.configure(text='Settings changed while the preview was open. Review this preset again.');dialog.destroy();return
  apply_plan(project,changes);app.reload_project_view();app.status.configure(text=name+' applied. Changed values are shown in orange.');dialog.destroy()
 accept=ttk.Button(footer,text='Apply preset',style='Primary.TButton',command=apply);accept.pack(side='left')
 cancel=ttk.Button(footer,text='Cancel',command=dialog.destroy);cancel.pack(side='left',padx=8)
 frame.bind('<Configure>',lambda e:description.configure(wraplength=max(240,e.width-32)))
 dialog.bind('<Escape>',lambda e:dialog.destroy())
 app.easy_preview_dialog=dialog;app.easy_preview_text=text;app.easy_preview_apply=accept;app.easy_preview_cancel=cancel
