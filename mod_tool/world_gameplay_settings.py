"""Compact World settings rows with review-before-apply popup dialogs."""
import tkinter as tk
from tkinter import ttk

class WorldSettings:
 def __init__(self,app,pages):
  style=ttk.Style(app.root);style.configure('Inline.Card.TCheckbutton',padding=0)
  style.configure('Changed.Inline.Card.TCheckbutton',padding=0,foreground='#ef7800');style.map('Changed.Inline.Card.TCheckbutton',foreground=[('disabled','#ef7800')])
  style.configure('Inline.TButton',padding=(6,2))
  self.app=app;self.loading=True;self.timers={};self.project=None
  self.mates_enabled=tk.BooleanVar();self.captains_enabled=tk.BooleanVar();self.item_enabled=tk.BooleanVar();self.goods_enabled=tk.BooleanVar();self.checks={};self.links={}
  self.variables={'mates':self.mates_enabled,'captains':self.captains_enabled,'items':self.item_enabled,'goods':self.goods_enabled,'shipbuilding':tk.BooleanVar()}
  self.openers={'mates':lambda:app.open_free_agent_shuffle('mates'),'captains':lambda:app.open_free_agent_shuffle('captains'),'items':app.open_item_seed,'goods':app.open_goods_seed,'shipbuilding':app.open_shipbuilding_seed}
  frame=pages['Fleets'];row=ttk.Frame(frame,style='Card.TFrame');row.pack(fill='x')
  app.difficulty_var=tk.BooleanVar();app.difficulty_check=ttk.Checkbutton(row,text='Use custom fleets',variable=app.difficulty_var,style='Inline.Card.TCheckbutton',state='disabled');app.difficulty_check.pack(side='left')
  app.difficulty_settings_button=ttk.Button(row,text='Configure fleets…',style='Inline.TButton',command=app.configure_fleets,state='disabled');app.difficulty_check.configure(command=lambda:app.configure_fleets()if app.difficulty_var.get()else None)
  self.fleet_link=ttk.Label(frame,text='Off',style='Card.TLabel');self.fleet_link.pack(anchor='w',pady=(3,0));self.fleet_link.bind('<Button-1>',lambda event:app.configure_fleets()if app.difficulty_var.get()else None);self.fleet_link.bind('<Return>',lambda event:app.configure_fleets()if app.difficulty_var.get()else None);self.fleet_link.bind('<space>',lambda event:app.configure_fleets()if app.difficulty_var.get()else None)
  app.difficulty_description=ttk.Label(frame,text='Top-tier national fleets • Replacements only • Experimental',style='Card.TLabel')
  app.difficulty_note=ttk.Label(frame,text='',style='Card.TLabel')
  for group,section,title,attr,summary in [('mates','Mates','Use random mates','gameplay_randomizer_button','gameplay_randomizer_summary'),('captains','Fleets','Use random fleet captains','gameplay_captain_randomizer_button','gameplay_captain_randomizer_summary'),('items','Items','Use random items','gameplay_item_shuffle_button','gameplay_item_summary'),('goods','Trade','Use random goods','gameplay_goods_shuffle_button','gameplay_goods_summary'),('shipbuilding','Ships','Use ship building randomizer','gameplay_shipbuilding_button','gameplay_shipbuilding_summary')]:
   frame=pages[section];row=ttk.Frame(frame,style='Card.TFrame');row.pack(fill='x',pady=(6,0)if group=='captains'else 0)
   check=ttk.Checkbutton(row,text=title,variable=self.variables[group],command=lambda g=group:self.toggle(g),style='Inline.Card.TCheckbutton');check.grid(row=0,column=0,sticky='w');self.checks[group]=check
   # Keep command handles for existing application hooks; no visible buttons.
   button=ttk.Button(row,command=lambda g=group:self.open(g));setattr(app,attr,button)
   label=ttk.Label(frame,text='Off',style='Card.TLabel',foreground='#596579');label.pack(anchor='w',pady=(3,0));setattr(app,summary,label);self.links[group]=label
   for event in ('<Button-1>','<Return>','<space>'):label.bind(event,lambda event,g=group:self.open(g)if self.variables[g].get()else None)
  self.buttons=[app.gameplay_randomizer_button,app.gameplay_captain_randomizer_button,app.gameplay_item_shuffle_button,app.gameplay_goods_shuffle_button,app.gameplay_shipbuilding_button]
  self.loading=False
 def open(self,group):
  if not self.app.project:return
  try:self.app.commit();self.openers[group]()
  except ValueError as error:self.app.fail(error);self.sync();return
  dialog=getattr(self.app,{'mates':'shuffle_dialog','captains':'shuffle_dialog','items':'item_shuffle_dialog','goods':'goods_shuffle_dialog','shipbuilding':'shipbuilding_shuffle_dialog'}[group],None)
  if dialog and dialog.winfo_exists():dialog.bind('<Destroy>',lambda event:self.app.root.after_idle(self.app.update_status)if event.widget==dialog else None,add='+')
  else:self.sync()
 def toggle(self,group):
  p=self.app.project
  if self.loading or not p:return
  if self.variables[group].get():self.open(group);return
  if group in ('mates','captains'):
   from character_mods import configure_group
   p.free_agent_shuffle=configure_group(p.rom,p.free_agent_shuffle,group,enabled=False)
  elif group=='items'and p.item_seed is not None:p.item_edits=[];p.item_seed=None;p.item_blind=False;p.item_special=False;p.item_special_only=False
  elif group=='goods'and p.goods_shuffle['seed']is not None:p.goods_edits=[];p.goods_shuffle=dict(seed=None,mode='normal')
  elif group=='shipbuilding':
   try:p.clear_shipbuilding_shuffle()
   except ValueError as error:self.app.fail(error);self.sync();return
  self.app.reload_project_view()
 def cancel(self,discard=False):
  # Common editor hook: popup seeds are drafts until Apply, so no pending writes.
  if discard:self.sync()
 def flush(self):pass
 def sync(self):
  p=self.app.project;self.project=p;self.loading=True
  config=p.free_agent_shuffle if p else dict(enabled=False,seed='0000',blind=False)
  from character_mods import group_active,group_settings,group_summary
  enabled={'mates':group_active(config,'mates'),'captains':group_active(config,'captains'),'items':bool(p and p.item_seed is not None),'goods':bool(p and p.goods_shuffle['seed']is not None),'shipbuilding':bool(p and p.shipbuilding_shuffle['seed']is not None)}
  for group,var in self.variables.items():
   var.set(enabled[group]);self.checks[group].configure(state='normal'if p else 'disabled',style=('Changed.'if enabled[group]else '')+'Inline.Card.TCheckbutton')
  for group,label in [('mates',self.app.gameplay_randomizer_summary),('captains',self.app.gameplay_captain_randomizer_summary)]:
   settings=group_settings(config,'captain_names')if group=='captains'else config
   label.configure(text=group_summary(config,group)if enabled[group]else 'Off',foreground='#ef7800'if enabled[group]else '#596579')
  for button in self.buttons:button.configure(state='normal'if p else 'disabled')
  self.app.gameplay_item_summary.configure(text=('Blind shuffle'if p.item_blind else 'Seed '+p.item_seed)if enabled['items']else 'Off',foreground='#ef7800'if enabled['items']else '#596579')
  self.app.gameplay_goods_summary.configure(text=('Blind shuffle'if p.goods_shuffle.get('blind',False)else 'Seed '+p.goods_shuffle['seed'])if enabled['goods']else 'Off',foreground='#ef7800'if enabled['goods']else '#596579')
  self.app.gameplay_shipbuilding_summary.configure(text=('Blind shuffle'if p.shipbuilding_shuffle['blind']else 'Seed '+p.shipbuilding_shuffle['seed'])if enabled['shipbuilding']else 'Off',foreground='#ef7800'if enabled['shipbuilding']else '#596579')
  for group,label in self.links.items():
   active=enabled[group]
   if active:label.configure(text=label.cget('text')+' • Edit…')
   label.configure(cursor='hand2'if active else '',takefocus=active,font=('Segoe UI',10,'underline')if active else ('Segoe UI',10))
  active=bool(p and self.app.difficulty_var.get())
  self.fleet_link.configure(text='Edit fleet settings…'if active else 'Off',foreground='#ef7800'if active else '#596579',cursor='hand2'if active else '',takefocus=active,font=('Segoe UI',10,'underline')if active else ('Segoe UI',10))
  self.loading=False
