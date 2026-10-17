"""Items editing, read-only port hub, and Easy Settings integration."""
import tkinter as tk,json,tempfile,copy
from tkinter import ttk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject,apply_ips
from item_shops import stock,values
from fleet_difficulty import preset

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  app=Editor(root);root.geometry('1440x900+0+0');p=app.project=ShipProject(rom);app.show(0);app.refresh_list();app.switch_section('world');w=app.world;panel=w.item_editor
  def settle():
   done=tk.BooleanVar(root,value=False);root.after(450,lambda:done.set(True));root.wait_variable(done);root.update()
  def mode(name):w.mode.set(name);w.change_mode();settle()
  errors=[]
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
   mode('Items');item=w.records[0]['id'];w.selected=item;w.details();settle();defaults=stock(p.rom)
   assert panel.enable_box.winfo_ismapped()and panel.enable_box.winfo_rooty()<w.columns.winfo_rooty()
   assert panel.port_box.instate(['disabled'])and panel.kind_box.instate(['disabled'])and panel.add_button.instate(['disabled'])
   panel.enable_box.invoke();settle();assert p.custom_items
   port=next(i for i,row in enumerate(defaults)if item not in row and 255 in row[:3]and row[3]==255)
   panel.port_box.current(port);panel.pick();panel.add_button.invoke();settle()
   assert item in values(p.rom,p.item_edits)[port][:3]and '*'in w.list.get(w.rows.index(item))
   panel.kind.set('Early morning');panel.kind_box.event_generate('<<ComboboxSelected>>');settle()
   assert values(p.rom,p.item_edits)[port][3]==item and w.goods_tree.item(str(port),'tags')==('changed',)
   panel.enable_box.invoke();settle();assert not p.custom_items and panel.kind_box.instate(['disabled'])and panel.kind_box.cget('style')=='Changed.TCombobox'
   mode('Port Information');w.selected=port;w.details();settle()
   assert any(r['id']==item and r['rare']for r in w.port_item_rows)and not panel.winfo_ismapped()
   with tempfile.TemporaryDirectory()as d:
    path=Path(d)/'project.json';out=Path(d)/'test.sfc';p.save_project(path);q=ShipProject(rom);q.load_project(path);assert q.item_edits==p.item_edits and not q.custom_items
    q.export(out);assert out.read_bytes()==apply_ips(q.rom,out.with_suffix('.ips').read_bytes())
   mode('Items');w.selected=item;w.details();panel.enable_box.invoke();settle()
   full=next(i for i,row in enumerate(defaults)if 255 not in row[:3]and item not in row)
   panel.port_box.current(full);panel.pick();before=copy.deepcopy(p.item_edits);panel.add_button.invoke();settle();assert p.item_edits==before and len(errors)==1;errors.clear()
   panel.restore_button.invoke();settle();assert not p.item_edits
   old_port=next(i for i,row in enumerate(defaults)if item in row);panel.port_box.current(old_port);panel.pick();panel.remove_button.invoke();settle();assert item not in values(p.rom,p.item_edits)[old_port]
   panel.restore_button.invoke();panel.enable_box.invoke();settle();assert not p.item_edits and not p.custom_items
   app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
   assert app.gameplay_notebook.tab(0,'text')=='Easy Settings'and app.easy_apply.winfo_ismapped()
   app.easy_preset.set('Busy Ports');app.refresh_easy_preset();app.easy_apply.invoke();settle();assert p.economy_edits and not p.custom_economy
   before=copy.deepcopy(p.economy_edits);app.easy_apply.invoke();settle();assert p.economy_edits==before
   app.easy_preset.set('Random Mates');app.refresh_easy_preset();settle();assert app.easy_seed_row.winfo_ismapped()
   app.easy_seed.set('1234');app.easy_apply.invoke();settle();assert p.free_agent_shuffle==dict(enabled=True,blind=False,seed='1234')
   for name,key in [('Stronger Flagships','flagships'),('Stronger Fleets','stronger')]:
    app.easy_preset.set(name);app.refresh_easy_preset();app.easy_apply.invoke();settle();assert p.fleet_difficulty and p.fleet_rules==preset(key)
   app.easy_preset.set('Random Items');app.refresh_easy_preset();app.easy_apply.invoke();settle()
   assert app.item_shuffle_dialog.winfo_exists()
   app.item_shuffle_seed.set('1234');app.item_shuffle_mode.set('Shuffle special items');settle()
   normal=copy.deepcopy(app.item_shuffle_candidates['edits']);assert app.item_shuffle_preview.size()>1
   app.item_shuffle_blind.set(True);settle();assert app.item_shuffle_preview.size()==1 and app.item_shuffle_candidates['edits']!=normal
   app.item_shuffle_buttons[1].invoke();settle();assert p.item_blind and p.item_special_only and p.item_seed=='1234'
   app.switch_section('world');mode('Items');assert not w.good_sources()and not w.item_editor.winfo_ismapped()and not w.goods_tree.get_children()
   mode('Port Information');assert not w.port_item_rows
   app.switch_section('gameplay');app.open_item_seed();settle();assert app.item_shuffle_blind.get()and app.item_shuffle_mode.get()=='Shuffle special items'
   app.item_shuffle_buttons[2].invoke();settle();assert not p.item_edits and p.item_seed is None
   app.easy_preset.set('Skilled Recruits');app.refresh_easy_preset();app.easy_apply.invoke();settle();assert p.character_edits and not p.custom_mates
   app.switch_data('mates');app.show_mate(79);settle();assert app.mate_field_widgets['leadership'][1].instate(['disabled'])and 'Changed.'in app.section_buttons['mates'].cget('style')
   app.switch_section('world');mode('Economy');assert w.economy_panel.entries['economy'].instate(['disabled'])and 'Changed.'in app.world_nav.cget('style')
   with patch('tkinter.messagebox.askyesno',return_value=True):app.restore_defaults()
   assert p.build()==(p.rom,[])and not p.item_edits and not p.custom_items and not errors
  report.write_text(json.dumps(dict(status='PASS',item_add_remove_and_early_offer=True,full_slots_rejected=True,locked_orange_values_export=True,port_information_and_map_follow_items=True,project_rom_ips_roundtrip=True,restore_item_and_global_defaults=True,easy_settings_six_presets_and_item_shuffle_dialog=True,item_shuffle_blind_mode_and_hidden_hub=True,presets_repeat_without_stacking=True,presets_work_while_manual_editing_locked=True),indent=2),encoding='utf-8')
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
