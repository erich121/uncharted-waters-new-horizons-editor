"""Real automatic preset selection, stored seeds and management controls."""
import json,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject
from custom_presets import PresetStore,starter,MANUAL_EDIT_FLAGS
from custom_preset_view import refresh

def run(Editor,rom,report):
 root=tk.Tk();report=Path(report);report.parent.mkdir(parents=True,exist_ok=True);errors=[];checks=[]
 try:
  app=Editor(root);root.geometry('1440x900+0+0')
  root.report_callback_exception=lambda typ,error,tb:errors.append(str(error))
  def settle():
   done=tk.BooleanVar(root,value=False);root.after(100,lambda:done.set(True));root.wait_variable(done);root.update()
  def choose(name):
   app.custom_preset_name.set(name);app.custom_preset_choice.event_generate('<<ComboboxSelected>>');settle()
  assert app.custom_preset_choice.instate(['disabled'])
  app.load_rom(rom);p=app.project;app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
  expected=['Original Game','Classic Plus','New Discoveries','Trade & Exploration','Classic Plus + Harder',"Eric's Custom Special",'Full Randomizer']
  assert list(app.custom_preset_choice.cget('values'))==expected
  assert app.custom_preset_name.get()=='' and p.manifest()==__import__('app_defaults').startup_project(rom).manifest()
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(str(a))),patch('tkinter.messagebox.askyesno',return_value=True):
   for name in expected[:-1]:
    choose(name);assert p.manifest()==starter(p,name).manifest(),name
    assert not any(getattr(p,flag)for flag in MANUAL_EDIT_FLAGS)
    assert app.export_preset_name==name
    assert not hasattr(app,'custom_preview_dialog')and not hasattr(app,'custom_preset_review')
   choose('Original Game');assert p.build()[0]==p.rom
   assert app.custom_preset_update.instate(['disabled']) and app.custom_preset_delete.instate(['disabled'])
   p.fleet_control=True;app.reload_project_view();assert p.fleet_control
   assert not app.easy_seed_row.winfo_ismapped()
   choose('Classic Plus + Harder');app.switch_section('captains');settle()
   from sailors import CAPTAIN_IDS,ATTRIBUTES,decode_sailors
   stock=decode_sailors(p.rom)
   captain=next(i for i in CAPTAIN_IDS if any(p.character_record(i)[k]!=stock[i][k]for k in ATTRIBUTES))
   app.show_mate(captain);settle();before_edit=p.build()[0]
   assert not p.custom_captains and app.sailor_restore_button.instate(['disabled'])
   app.custom_character_box.invoke();settle();assert p.custom_captains and p.build()[0]==before_edit
   app.sailor_restore_button.invoke();settle()
   assert all(p.character_record(captain)[k]==stock[captain][k]for k in ATTRIBUTES+('skills',))
   app.custom_character_box.invoke();settle();assert not p.custom_captains
   app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
   checks.append('Loaded preset values stay active while manual editing is locked; enabling editing preserves them; Restore captain returns original attributes/skills despite shuffles')
   checks.append('Five supplied snapshots and Original Game load immediately; Hard Mode and Naval Challenge are absent; original project settings remain editable')
   choose('Classic Plus');assert p.manifest()==starter(p,'Classic Plus').manifest()
   with patch('character_mods.random_seed',return_value='1234'):choose('Full Randomizer')
   assert app.easy_seed.get()=='1234' and p.manifest()==starter(p,'Full Randomizer','1234').manifest()
   first=p.manifest();refresh(app);app.update_status();app.switch_section('ships');app.switch_section('gameplay');settle()
   assert p.manifest()==first and app.easy_seed.get()=='1234'
   with patch('character_mods.random_seed',return_value='5678'):app.preset_randomize_seed.invoke();settle()
   assert app.easy_seed.get()=='5678' and p.manifest()!=first
   with patch('character_mods.random_seed',return_value='5678'):choose('Full Randomizer')
   assert app.easy_seed.get()=='5679' and p.manifest()==starter(p,'Full Randomizer','5679').manifest()
   app.easy_seed_entry.focus_force();settle();app.easy_seed.set('0007');app.easy_seed_entry.event_generate('<Return>');settle()
   assert p.manifest()==starter(p,'Full Randomizer','0007').manifest()
   app.easy_blind_check.invoke();settle();assert p.manifest()==starter(p,'Full Randomizer','0007',True).manifest()
   assert 'Destinations hidden'in app.preset_loaded_changes.get('1.0','end')or 'blind'in app.preset_loaded_changes.get('1.0','end').lower()
   checks.append('Fresh seed on Full Randomizer selection; Randomize button, manual zero-padded seed and blind mode apply immediately; refresh never rerolls')
   before=p.manifest();app.easy_seed_entry.focus_force();settle();app.easy_seed.set('bad');app.easy_seed_entry.event_generate('<Return>');settle();assert p.manifest()==before
   try:app.commit();raise AssertionError('Invalid seed allowed export/save commit')
   except ValueError:pass
   app.easy_seed.set('0007');settle();app.commit()
   store=PresetStore();saved=p.manifest();store.save('Stored random world',p);refresh(app)
   choose('Classic Plus')
   with patch('character_mods.random_seed',side_effect=AssertionError('Saved preset rerolled')):choose('Stored random world')
   assert p.manifest()==saved and not app.easy_seed_row.winfo_ismapped()
   p.starting_gold=5000;app.reload_project_view();saved_full=p.manifest()
   store.save('Full Randomizer',p);refresh(app);choose('Classic Plus')
   with patch('character_mods.random_seed',side_effect=AssertionError('Saved Full Randomizer rerolled')):choose('Full Randomizer')
   assert p.manifest()==saved_full and not app.easy_seed_row.winfo_ismapped()
   checks.append('Saved shuffled snapshots keep exact seeds, including an updated preset named Full Randomizer; invalid manual seed is atomic')
   store.save('Broken preset',p);document=json.loads(store.path.read_text(encoding='utf-8'));document['presets']['Broken preset']['version']=999;store.path.write_text(json.dumps(document),encoding='utf-8');refresh(app)
   before=p.manifest();choose('Broken preset');assert p.manifest()==before and errors;errors.clear();assert app.custom_preset_name.get()=='Full Randomizer'
   store.delete('Broken preset')
   store.restore_provided();refresh(app);app.commit();assert p.manifest()==saved_full
   checks.append('Restoring provided preset definitions preserves the currently loaded custom Full Randomizer snapshot, including on export commit')
   choose('Classic Plus');before=p.manifest()
   app.custom_preset_update.invoke();settle();app.preset_editor_description.delete('1.0','end');app.preset_editor_description.insert('1.0','Updated description');app.preset_editor_save.invoke();settle()
   assert store.read()['Classic Plus']==before and store.descriptions()['Classic Plus']=='Updated description'
   for size in ('640x480','1440x900'):
    root.geometry(size+'+0+0');settle();app.gameplay_scrollers[0].canvas.yview_moveto(1);settle()
    for button in (app.custom_preset_save,app.custom_preset_update,app.custom_preset_delete):assert button.winfo_rootx()+button.winfo_width()<=root.winfo_rootx()+root.winfo_width()
   root.geometry('1440x900+0+0');settle();app.gameplay_scrollers[0].canvas.yview_moveto(0)
   for name in list(app.custom_preset_choice.cget('values')):
    app.custom_preset_name.set(name);refresh(app);app.custom_preset_delete.invoke();settle()
   assert p.manifest()==before and list(app.custom_preset_choice.cget('values'))==['Original Game']
   assert app.custom_preset_update.instate(['disabled'])and app.custom_preset_delete.instate(['disabled'])
   app.custom_preset_restore.invoke();settle();assert list(app.custom_preset_choice.cget('values'))==expected and p.manifest()==before
   checks.append('Invalid saved preset preserves project and previous selection; update/delete/restore preserve their existing explicit management behavior')
   with patch('character_mods.random_seed',return_value='2026'):choose('Full Randomizer')
   from PIL import ImageGrab
   settle();ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/'Automatic presets.png')
   # A newly opened stock ROM must not inherit a selected random preset implicitly.
   app.load_rom(rom);settle();assert app.custom_preset_name.get()=='';app.commit();assert app.project.manifest()==__import__('app_defaults').startup_project(rom).manifest()
   assert not errors,errors
  report.write_text(json.dumps(dict(status='PASS',checks=checks),indent=2),encoding='utf-8')
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),errors=errors,checks=checks,traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
