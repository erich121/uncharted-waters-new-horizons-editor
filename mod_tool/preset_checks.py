"""Easy Settings preview/cancel/apply, mixed seeds, blind mode and sizing."""
import json,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject
from easy_presets import PRESETS,RANDOMIZED
from character_mods import group_settings

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  app=Editor(root);assert app.easy_apply.instate(['disabled']);p=app.project=ShipProject(rom);app.show(0);app.refresh_list();app.update_status();errors=[]
  def settle():
   done=tk.BooleanVar(root,value=False);root.after(100,lambda:done.set(True));root.wait_variable(done);root.update()
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
   root.geometry('1440x900+0+0');app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
   assert list(app.easy_choice.cget('values'))==list(PRESETS)and len(PRESETS)==13
   before=p.manifest()
   for name in PRESETS:
    app.easy_preset.set(name);app.refresh_easy_preset();settle()
    assert bool(app.easy_seed_row.winfo_ismapped())==(name in RANDOMIZED)
    app.easy_seed.set('2026');app.easy_blind.set(True);app.easy_apply.invoke();settle()
    assert app.easy_preview_dialog.winfo_exists()and str(app.easy_preview_text.cget('state'))=='disabled'
    assert p.manifest()==before;app.easy_preview_cancel.invoke();settle();assert p.manifest()==before
   root.geometry('640x480+0+0');app.easy_preset.set('Fresh World');app.refresh_easy_preset();settle();assert app.easy_blind_check.winfo_rootx()+app.easy_blind_check.winfo_width()<=root.winfo_rootx()+root.winfo_width();app.easy_apply.invoke();settle()
   app.easy_preview_dialog.geometry('480x360+0+0');settle();assert app.easy_preview_apply.winfo_ismapped()and app.easy_preview_cancel.winfo_ismapped()
   app.easy_preview_apply.invoke();settle();assert p.item_blind and p.goods_shuffle['blind']and group_settings(p.free_agent_shuffle,'ports')['blind']
   assert 'Changed.'not in app.section_buttons['gameplay'].cget('style')
   assert 'Changed.'in app.section_buttons['mates'].cget('style')and 'Changed.'in app.section_buttons['world'].cget('style')
   app.easy_preset.set('New Faces');app.easy_seed.set('9999');app.easy_blind.set(False);app.refresh_easy_preset();app.easy_apply.invoke();settle();app.easy_preview_apply.invoke();settle()
   assert group_settings(p.free_agent_shuffle,'ports')['seed']=='2026'and group_settings(p.free_agent_shuffle,'names')['seed']=='9999'
   root.geometry('1440x900+0+0');app.gameplay_notebook.select(2);settle()
   w=app.world_gameplay_settings;assert 'Blind'in w.links['mates'].cget('text')
   w.open('mates');settle();assert 'earlier presets'in next(w for w in app.shuffle_dialog.winfo_children()[0].winfo_children()if w.winfo_class()=='TLabel'and 'earlier presets'in w.cget('text')).cget('text')
   app.shuffle_dialog.destroy();settle();app.gameplay_notebook.select(0);app.easy_seed.set('bad');app.easy_preset.set('Full Randomizer');before=p.manifest();app.easy_apply.invoke();settle();assert errors and p.manifest()==before;errors.clear()
   assert not any((p.custom_ships,p.custom_items,p.custom_goods,p.custom_economy,p.custom_mates,p.custom_captains))
  report.write_text(json.dumps(dict(status='PASS',presets=list(PRESETS),all_previews_cancel_without_changes=True,seed_and_blind_controls=True,apply_and_mixed_seed_preservation=True,correct_section_highlights=True,editing_locks_preserved=True,invalid_seed_atomic=True,small_preview_buttons_reachable=True),indent=2),encoding='utf-8')
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
