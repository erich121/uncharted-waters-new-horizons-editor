"""Real Presets controls; caller must isolate LOCALAPPDATA before Editor."""
import json
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject
from custom_presets import PresetStore


def run(Editor,rom,report):
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    root=tk.Tk();root.attributes('-topmost',True)
    try:
        app=Editor(root);errors=[]
        def settle():
            ready=tk.BooleanVar(root,value=False);root.after(80,lambda:ready.set(True));root.wait_variable(ready);root.update()
        assert app.custom_preset_save.instate(['disabled'])
        p=app.project=ShipProject(rom);app.show(0);app.refresh_list();app.update_status()
        root.geometry('1440x900+0+0');app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
        def new_preset(name=None):
            app.custom_preset_save.invoke();settle()
            if name is None:app.preset_editor_cancel.invoke();return
            app.preset_editor_name.set(name);app.preset_editor_description.insert('1.0','Description stays outside load preview')
            app.preset_editor_save.invoke();settle()
        with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            # Cancel the naming dialog and then save via the actual button.
            new_preset()
            assert not PresetStore().path.exists()
            p.update_character(0,dict(battle_level=65));p.fleet_control=True;app.reload_project_view();settle()
            snapshot=p.manifest();expected=p.build()[0]
            new_preset('My custom world')
            settle();assert not errors and app.custom_preset_name.get()=='My custom world'
            assert PresetStore().read()['My custom world']==snapshot
            p.fleet_control=False;p.update_character(0,dict(battle_level=2));app.reload_project_view();settle()
            before=p.manifest();path=p.project_path
            app.custom_preset_choice.event_generate('<<ComboboxSelected>>');settle()
            assert p.manifest()==snapshot and p.project_path==path and p.build()[0]==expected
            assert 'Battle level'in app.preset_loaded_changes.get('1.0','end')
            assert 'Description stays outside load preview'not in app.preset_loaded_changes.get('1.0','end')
            assert not hasattr(app,'custom_preview_dialog') and not hasattr(app,'custom_preset_review')
            assert 'Changed.'in app.section_buttons['characters'].cget('style')
            # Replacement is explicit; decline leaves the stored snapshot intact.
            p.fleet_control=False;app.reload_project_view();settle()
            with patch('tkinter.messagebox.askyesno',return_value=False):new_preset('My custom world')
            app.preset_editor_cancel.invoke()
            assert PresetStore().read()['My custom world']==snapshot
            with patch('tkinter.messagebox.askyesno',return_value=True):new_preset('My custom world')
            assert PresetStore().read()['My custom world']==p.manifest()
            with patch('tkinter.messagebox.askyesno',return_value=False):app.custom_preset_delete.invoke()
            assert 'My custom world'in PresetStore().read()
            root.geometry('640x480+0+0');settle();app.gameplay_scrollers[0].canvas.yview_moveto(1);settle()
            assert app.custom_preset_save.winfo_ismapped()and app.custom_preset_delete.winfo_rootx()+app.custom_preset_delete.winfo_width()<=root.winfo_rootx()+root.winfo_width()
            root.geometry('1440x900+0+0');settle();app.gameplay_scrollers[0].canvas.yview_moveto(0);settle()
            new_preset('Second preset')
            settle()
            import os
            if os.environ.get('NH_CUSTOM_PRESET_SCREENSHOT'):
                from PIL import ImageGrab
                ImageGrab.grab().save(os.environ['NH_CUSTOM_PRESET_SCREENSHOT'])
            before=p.manifest()
            with patch('tkinter.messagebox.askyesno',return_value=True):app.custom_preset_delete.invoke()
            assert p.manifest()==before and list(PresetStore().read())==['My custom world']
            reset_messages=[]
            with patch('tkinter.messagebox.askyesno',side_effect=lambda title,body,**kwargs:reset_messages.append(body)or False):
                app.reset_section('world')
            assert p.manifest()==before
            for phrase in ('item shop locations and costs','Discovery replacements','Goods and item shuffles','Library content and presets are kept'):
                assert phrase in reset_messages[0],phrase
            assert not errors,errors
        report.write_text(json.dumps(dict(status='PASS',save_cancel=True,save_and_restart_storage=True,replace_confirmation=True,delete_confirmation=True,automatic_selection=True,inline_changes=True,no_load_popup=True,all_settings_replaced=True,rom_roundtrip=True,project_path_preserved=True,orange_character_highlight=True,small_window_controls=True,world_reset_disclosure=True,world_reset_cancel_preserves_project=True),indent=2),encoding='utf-8')
    except Exception as error:
        import traceback
        report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
    finally:root.destroy()
