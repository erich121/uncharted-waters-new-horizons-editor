"""One grouped checkbox per randomizer, separate option/preview popups."""
import tkinter as tk,json
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject
from sailors import decode_sailors,CAPTAIN_IDS

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  root.geometry('1440x900+0+0');app=Editor(root);p=app.project=ShipProject(rom);app.show(0);app.refresh_list();app.update_status();w=app.world_gameplay_settings;errors=[]
  def settle(ms=160):
   done=tk.BooleanVar(root,value=False);root.after(ms,lambda:done.set(True));root.wait_variable(done);root.update()
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
   app.switch_section('gameplay');app.gameplay_notebook.select(2);settle()
   expected={'mates':'Use random mates','captains':'Use random fleet captains','items':'Use random items','goods':'Use random goods','shipbuilding':'Use ship building randomizer'}
   assert all(w.checks[k].cget('text')==v for k,v in expected.items())and all(not v.get()for v in w.variables.values())
   before=p.manifest();w.checks['mates'].invoke();settle();assert app.shuffle_group=='mates'and set(app.shuffle_option_widgets)=={'ports','names','mate_stats','mate_skills'}
   app.shuffle_blind.set(True);settle();assert all('hidden'in line.lower()or 'blind'in line.lower()for line in app.shuffle_preview.get(0,'end'));app.shuffle_blind.set(False)
   app.shuffle_seed.set('2026');app.shuffle_mate_stats.set(True);app.shuffle_mate_skills.set(True);app.shuffle_names.set(True);settle()
   lines=list(app.shuffle_preview.get(0,'end'));assert any('Leadership:'in line or 'Seamanship:'in line for line in lines)and any('Skills:'in line for line in lines)and any('Name:'in line for line in lines)
   assert p.manifest()==before;app.shuffle_buttons[3].invoke();settle();assert p.manifest()==before and not w.mates_enabled.get()
   w.checks['mates'].invoke();settle();app.shuffle_seed.set('2026');app.shuffle_mate_stats.set(True);app.shuffle_mate_skills.set(True);app.shuffle_names.set(True);app.shuffle_buttons[1].invoke();settle()
   assert w.mates_enabled.get()and not w.captains_enabled.get();mates=decode_sailors(p.build()[0])
   w.checks['captains'].invoke();settle();assert app.shuffle_group=='captains'and set(app.shuffle_option_widgets)=={'captain_names','captain_stats','captain_skills'}
   app.shuffle_blind.set(True);settle();assert any('hidden'in line.lower()for line in app.shuffle_preview.get(0,'end'));app.shuffle_blind.set(False)
   app.shuffle_seed.set('3456');app.shuffle_captain_stats.set(True);app.shuffle_captain_skills.set(True);app.shuffle_buttons[1].invoke();settle()
   assert w.captains_enabled.get()and p.free_agent_shuffle['seed']=='2026'and p.free_agent_shuffle['captain_seed']=='3456'
   both=decode_sailors(p.build()[0])
   for r in mates:
    if r['role']=='Free agent':assert both[r['id']]==r
   assert all(not button.winfo_ismapped()for button in w.buttons)and not app.difficulty_settings_button.winfo_ismapped()
   before=p.manifest();w.links['captains'].event_generate('<Button-1>');settle();app.shuffle_seed.set('9999');app.shuffle_dialog.destroy();settle();assert p.manifest()==before
   w.checks['mates'].invoke();settle();assert not w.mates_enabled.get()and w.captains_enabled.get()
   after=decode_sailors(p.build()[0])
   for i in CAPTAIN_IDS:assert after[i]==both[i]
   for group in ('items','goods'):
    before=p.manifest();w.checks[group].invoke();settle()
    if group=='items':app.item_shuffle_seed.set('1234');assert app.item_shuffle_preview.size()>0;app.item_shuffle_buttons[3].invoke()
    else:app.goods_shuffle_seed.set('1234');assert app.goods_shuffle_preview.size()>0;app.goods_shuffle_buttons[3].invoke()
    settle();assert p.manifest()==before and not w.variables[group].get()
    w.open(group);settle()
    if group=='items':app.item_shuffle_seed.set('2026');app.item_shuffle_buttons[1].invoke()
    else:app.goods_shuffle_seed.set('2026');app.goods_shuffle_buttons[1].invoke()
    settle();assert w.variables[group].get()
    before=p.manifest();w.links[group].event_generate('<Button-1>');settle()
    blind=app.item_shuffle_blind if group=='items'else app.goods_shuffle_blind;blind.set(True);settle()
    preview=app.item_shuffle_preview if group=='items'else app.goods_shuffle_preview
    assert preview.size()==1 and 'hidden'in preview.get(0).lower()
    if group=='items':app.item_shuffle_buttons[3].invoke()
    else:app.goods_shuffle_buttons[3].invoke()
    settle();assert p.manifest()==before
   w.open('goods');settle();app.goods_shuffle_blind.set(True);app.goods_shuffle_buttons[1].invoke();settle()
   assert 'Blind'in w.links['goods'].cget('text')and '2026'not in w.links['goods'].cget('text')
   app.switch_section('world');world=app.world;world.mode.set('Goods');world.change_mode();settle()
   assert world.goods_hidden()and world.good_sources()==[]and not world.goods_tree.get_children()
   assert not world.map_canvas.find_withtag('goods-port')and world.marker is None
   assert not world.goods_edit_frame.winfo_ismapped()and 'hidden'in world.goods_summary.cget('text')
   world.mode.set('Port Information');world.change_mode();settle()
   assert not world.port_goods.entries and 'Hidden'in world.values['specialty'].get()
   app.switch_section('gameplay');app.gameplay_notebook.select(2);settle()
   for group in ('captains','items','goods'):w.checks[group].invoke();settle();assert not w.variables[group].get()
   assert not p.free_agent_shuffle['enabled']and p.item_seed is None and p.goods_shuffle['seed']is None
   from trade_goods import change
   p.goods_edits=change(p.rom,[],4,10,500);before=p.manifest();app.update_status();assert p.manifest()==before
   assert not errors,errors
  report.write_text(json.dumps(dict(status='PASS',exact_requested_checkbox_labels=expected,separate_mate_and_captain_popups=True,group_specific_options=True,independent_seeds_and_disable=True,all_popups_have_preview=True,draft_apply_cancel=True,manual_world_edits_preserved=True,no_far_right_configure_buttons=True,active_seed_links_reopen=True,blind_option_in_all_four_popups=True,blind_cargo_destinations_hidden=True),indent=2),encoding='utf-8')
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
