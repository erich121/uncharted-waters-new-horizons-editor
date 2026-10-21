"""Item-shop editing controls, paired with the read-only map and picture."""
import tkinter as tk
from tkinter import ttk,messagebox
from item_shops import change,restore_item,stock,values
class ItemShopPanel(ttk.Frame):
 def __init__(self,world,parent):
  super().__init__(parent,style='Card.TFrame',padding=(0,10));self.world=world;self.loading=False
  self.enabled=tk.BooleanVar(value=False);self.enable_box=ttk.Checkbutton(world.edit_controls,text='Use custom values',variable=self.enabled,command=self.toggle,state='disabled')
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
  self.price_unit='gold';self.price=tk.StringVar();self.price_timer=None;self.price_pending=None
  self.price_label=ttk.Label(self,text='Base price (gold)',style='Card.TLabel');self.price_label.grid(row=5,column=0,sticky='w',pady=(12,0))
  self.price_box=ttk.Spinbox(self,textvariable=self.price,from_=0,to=3276700,increment=100,width=14,state='disabled')
  self.price_box.grid(row=5,column=1,sticky='w',pady=(12,0))
  ttk.Label(self,text='Steps of 100 gold (0.01 bar). Prices above 10,000 gold use bars. New games use these prices; bargaining and resale use the normal game rules.',style='Hint.Card.TLabel',wraplength=300).grid(row=6,column=0,columnspan=2,sticky='w',pady=(4,0))
  self.price.trace_add('write',self.schedule_price)
  self.price_box.bind('<FocusOut>',lambda event:self.flush())
  self.price_box.bind('<Return>',lambda event:self.flush())
  for widget in self.winfo_children():
   info=widget.grid_info();row=int(info.get('row',-1))
   if row<5 and row>=0:widget.grid_configure(row=row+1)
   elif row==5:widget.grid_configure(row=0)
  self.columnconfigure(1,weight=1)
 def schedule_price(self,*args):
  p=self.world.editor.project
  if self.loading or not p or not p.custom_items:return
  if self.price_timer is not None:self.after_cancel(self.price_timer)
  self.price_pending=(p,self.world.selected,self.price.get(),self.price_unit)
  self.price_timer=self.after(350,self.flush)
 def flush(self,strict=False):
  if self.price_timer is not None:self.after_cancel(self.price_timer);self.price_timer=None
  if self.price_pending is None:return
  p,item,text,unit=self.price_pending
  if p is not self.world.editor.project:self.price_pending=None;return
  from item_prices import validate
  try:
   amount=__import__('currency').parse_item_amount(text,unit)
   edits=validate(p.rom,[r for r in p.item_price_edits if r['id']!=item]+[dict(id=item,price_gold=amount)])
  except ValueError as error:
   if strict:raise ValueError('Item price: '+str(error))
   self.world.editor.status.configure(text='Item price: '+str(error));return
  self.price_pending=None
  p.item_price_edits=edits;self.world.editor.update_status()
 def cancel(self):
  if self.price_timer is not None:self.after_cancel(self.price_timer);self.price_timer=None
  self.price_pending=None
 def toggle(self):
  if not self.world.editor.project:return
  wanted=self.enabled.get()
  try:self.flush(strict=True)
  except ValueError as error:
   self.enabled.set(self.world.editor.project.custom_items);self.world.editor.fail(error);return
  self.world.editor.project.custom_items=wanted;self.world.editor.update_status()
 def show(self):
  project=self.world.editor.project
  if not project:return
  self.loading=True;enabled=project.custom_items;self.enabled.set(enabled);self.enable_box.configure(state='normal')
  from item_prices import price,stock as stock_price
  pending=self.price_pending
  from currency import item_unit,item_amount
  draft=bool(pending and pending[0]is project and pending[1]==self.world.selected)
  self.price_unit=pending[3]if draft else item_unit(price(project,self.world.selected))
  self.price_label.configure(text='Base price (gold bars)'if self.price_unit=='bars'else 'Base price (gold)')
  self.price_box.configure(to=327.67 if self.price_unit=='bars'else 3276700,increment=.01 if self.price_unit=='bars'else 100)
  self.price.set(pending[2]if draft else item_amount(price(project,self.world.selected)))
  self.price_box.configure(state='normal'if enabled else 'disabled',style='Changed.TSpinbox'if price(project,self.world.selected)!=stock_price(project.rom,self.world.selected)else 'TSpinbox')
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
  try:self.price_pending=None;project.item_price_edits=[r for r in project.item_price_edits if r['id']!=self.world.selected];project.item_edits=restore_item(project.rom,project.item_edits,self.world.selected);project.item_seed=None;self.world.editor.update_status()
  except ValueError as error:messagebox.showerror('Restore item',str(error),parent=self.world.editor.root)
