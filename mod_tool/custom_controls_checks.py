"""Enable controls must guard UI, project persistence and exported bytes."""
import json,tempfile,tkinter as tk
from pathlib import Path
from backend import ShipProject
from tkinter import ttk
def ttk_color(root):return ttk.Style(root).lookup('Changed.TSpinbox','foreground',('disabled',))
from economy import update
from trade_goods import change

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  app=Editor(root);root.geometry('1440x900+0+0');p=app.project=ShipProject(rom);app.show(0);app.refresh_list()
  def settle():
   done=tk.BooleanVar(root,value=False);root.after(450,lambda:done.set(True));root.wait_variable(done);root.update()
  assert not any((p.custom_ships,p.custom_goods,p.custom_economy,p.custom_mates,p.custom_captains))
  assert app.entries['hull'].instate(['disabled'])and app.add_button.instate(['disabled'])
  app.custom_ships_box.invoke();settle();old=p.ships[0]['hull']
  app.entries['hull'].delete(0,'end');app.entries['hull'].insert(0,str(old+1));settle()
  app.custom_ships_box.invoke();settle()
  assert app.entries['hull'].instate(['disabled'])and str(app.entries['hull'].cget('style')).startswith('Changed.')
  assert p.ships[0]['hull']==old+1 and p.build()[0]!=p.rom
  app.restore();app.add();app.remove();assert len(p.ships)==25 and p.ships[0]['hull']==old+1
  for section in ('mates','captains'):
   app.switch_data(section);settle();entry=app.mate_field_widgets['leadership'][1];assert entry.instate(['disabled'])
   assert all(c.instate(['disabled'])for c in app.skill_checks.values());assert app.sailor_restore_button.instate(['disabled'])
   app.custom_character_box.invoke();settle();assert not entry.instate(['disabled'])
   record=app.character_selection();old=p.character_record(record)['leadership'];entry.delete(0,'end');entry.insert(0,str(old-1 if old else 1));settle()
   assert any(e['id']==record for e in p.effective_character_edits())
   app.custom_character_box.invoke();settle();assert entry.instate(['disabled']);assert entry.cget('style')=='Changed.TSpinbox';assert any(e['id']==record for e in p.effective_character_edits())
   assert any(e['id']==record for e in p.character_edits)
  app.switch_section('world');w=app.world
  w.mode.set('Economy');w.change_mode();settle();panel=w.economy_panel
  assert panel.enable_box.winfo_rooty()<w.columns.winfo_rooty()and panel.enable_box.winfo_ismapped()
  assert not w.goods_enable_box.winfo_ismapped()
  assert all(c.instate(['disabled'])for c in [*panel.entries.values(),*panel.bulk_entries.values(),panel.operation_box,panel.restore_button,panel.restore_region_button,panel.apply_button])
  panel.enable_box.invoke();settle();assert p.custom_economy
  panel.entries['economy'].delete(0,'end');panel.entries['economy'].insert(0,'901');settle();assert p.economy_edits
  panel.enable_box.invoke();settle();assert not p.custom_economy and p.economy_edits
  assert panel.entries['economy'].cget('style')=='Changed.TSpinbox'and panel.entries['economy'].instate(['disabled'])
  assert 'Changed.'in app.world_nav.cget('style')
  w.mode.set('Goods');w.change_mode();w.selected=10;w.details();settle()
  assert w.goods_enable_box.winfo_rooty()<w.columns.winfo_rooty()and w.goods_enable_box.winfo_ismapped()
  assert not panel.enable_box.winfo_ismapped()
  assert all(c.instate(['disabled'])for c in (w.goods_port_box,w.goods_gate_box,w.add_good_button,w.remove_good_button,w.restore_good_button))
  w.goods_enable_box.invoke();settle();w.goods_port_box.current(4);w.select_edit_port();w.goods_gate.set('500');w.add_good_button.invoke();settle();assert p.goods_edits
  w.goods_enable_box.invoke();settle();assert not p.custom_goods and p.goods_edits
  assert any(o['port']==4 for o in w.goods_records[10]['sources'])
  assert any(o['port']==4 for o in w.records[10]['sources'])
  locked_rom=p.build()[0];assert locked_rom!=p.rom,'Locked values must remain active in exports'
  before=p.manifest()
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'project.json';p.save_project(path);q=ShipProject(rom);q.load_project(path);assert q.manifest()==before and q.build()[0]==locked_rom
   legacy={key:before[key]for key in ('format','base_sha256','edits','added_ships','fixes','original_availability','portraits','character_edits','free_agent_shuffle','gameplay','goods_edits','economy_edits')};legacy['version']=13
   path.write_text(json.dumps(legacy));q.load_project(path);assert all((q.custom_goods,q.custom_economy,q.custom_mates,q.custom_captains))
   for key in ('custom_ships','custom_goods','custom_economy','custom_mates','custom_captains'):
    setattr(p,key,True);built,_=p.build();assert built==locked_rom;setattr(p,key,False)
  # Presets use the model directly while manual controls remain locked.
  p.economy_edits=update(p.rom,p.economy_edits,4,economy=777)
  p.goods_edits=change(p.rom,p.goods_edits,4,10,600)
  for record in (6,79):p.update_character(record,dict(leadership=42))
  app.update_status();settle()
  assert w.port_records[4]['economy']==777 and w.goods_gate_box.instate(['disabled'])
  w.mode.set('Port Information');w.change_mode();w.selected=4;w.details();settle()
  assert w.values['economy'].get()=='777'and str(w.value_labels['economy'].cget('foreground'))=='#ef7800'
  assert next(o for o in w.port_goods.entries if o['id']==10)['required']==600
  assert p.build()[0]!=locked_rom
  for section,record in [('mates',79),('captains',6)]:
   app.switch_data(section);app.show_mate(record);settle()
   assert app.mate_vars['leadership'].get()=='42'and app.mate_field_widgets['leadership'][1].instate(['disabled'])
   widget=app.mate_field_widgets['leadership'][1];assert widget.cget('style')=='Changed.TSpinbox'
   assert str(ttk_color(root))=='#ef7800'
   assert '*'in app.list.get(app.mate_rows.index(record))and 'Changed.'in app.section_buttons[section].cget('style')
  app.switch_section('world')
  for mode in ('Goods','Economy','Items','Port Information'):
   w.mode.set(mode);w.change_mode();settle();w.scroll.canvas.yview_moveto(0);settle()
   assert bool(w.goods_enable_box.winfo_ismapped())==(mode=='Goods')
   assert bool(panel.enable_box.winfo_ismapped())==(mode=='Economy')
   if mode in ('Goods','Economy'):
    for size in ('640x480','1672x940'):
     root.geometry(size+'+0+0');settle();w.scroll.canvas.yview_moveto(0);settle()
     checkbox=w.goods_enable_box if mode=='Goods'else panel.enable_box
     assert checkbox.winfo_rooty()<w.columns.winfo_rooty()
     assert root.winfo_containing(checkbox.winfo_rootx()+10,checkbox.winfo_rooty()+10)==checkbox,(mode,size,checkbox.winfo_geometry(),checkbox.winfo_rootx(),checkbox.winfo_rooty(),root.winfo_geometry(),str(root.winfo_containing(checkbox.winfo_rootx()+10,checkbox.winfo_rooty()+10)))
  from unittest.mock import patch
  with patch('tkinter.messagebox.askyesno',return_value=True):app.restore_defaults()
  assert not any((p.custom_ships,p.custom_goods,p.custom_economy,p.custom_mates,p.custom_captains))and not p.character_edits and not p.goods_edits and not p.economy_edits
  report.write_text(json.dumps(dict(status='PASS',checks=['Top-of-page checkbox placement, visibility and pointer access at small/full window sizes','Five default-off editing locks','Attributes and skills locked','Pending edits preserved on disable','Locked values still exported','Goods hub retains values while locked','Project round trip','Legacy edits remain enabled','Editing locks do not change exported bytes; preset-style model edits work while locked','Global reset']),indent=2))
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2));raise
 finally:root.destroy()
