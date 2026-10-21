"""Exercise the playable-character browser in source and frozen Windows builds."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from backend import ShipProject
from sailors import decode_sailors, ATTRIBUTES, LEVEL_FIELDS


def run(Editor, rom_path, report_path):
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    root = None
    result = dict(status='FAIL')
    try:
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, LOCALAPPDATA=folder):
            root = tk.Tk()
            errors = []
            import traceback
            root.report_callback_exception = lambda *args: errors.append(''.join(traceback.format_exception(*args)))
            app = Editor(root)
            def settle():
                ready = tk.BooleanVar(root, False)
                root.after(70, lambda: ready.set(True))
                root.wait_variable(ready)
                root.update()
                assert not errors, errors
            app.switch_section('characters'); settle()
            assert app.characters.list.size() == 0
            app.project = ShipProject(rom_path)
            app.selected = 0
            app.show(0); app.refresh_list(); app.update_status(); settle()
            original = app.project.build()
            app.project.save_project(Path(folder)/'before.json')
            before = (Path(folder)/'before.json').read_bytes()
            expected = decode_sailors(app.project.rom)[:6]
            assert app.characters.list.size() == 6
            sizes = []
            for width, height in [(640,480),(1024,768),(1440,900),(1920,1080)]:
                root.geometry(f'{width}x{height}+0+0'); settle()
                buttons = list(app.section_buttons.values())
                assert [b.cget('text') for b in buttons] == ['Gameplay','World','Ships','Discoveries','Characters','Mates','Fleet Captains','Library']
                assert [b.winfo_rooty() for b in buttons] == sorted(b.winfo_rooty() for b in buttons)
                assert app.characters.list.winfo_height() >= 36
                assert app.characters.scroll.canvas.winfo_width() > 100
                if width>=1440:
                    app.characters.scroll.canvas.yview_moveto(0);settle()
                    assert app.characters.restore_button.winfo_rooty()+app.characters.restore_button.winfo_height()<=app.characters.scroll.canvas.winfo_rooty()+app.characters.scroll.canvas.winfo_height(),'Character restore is clipped at desktop size'
                for i, row in enumerate(expected):
                    app.characters.list.selection_clear(0,'end')
                    app.characters.list.selection_set(i)
                    app.characters.list.event_generate('<<ListboxSelect>>'); settle()
                    assert app.characters.heading.cget('text') == row['name']
                    assert app.characters.photo.width() == 120 and app.characters.photo.height() == 144
                    for key in ATTRIBUTES: assert app.characters.variables[key].get() == str(row[key])
                    assert app.characters.description.cget('text')
                sizes.append([width,height])
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)
            assert all(widget.instate(['disabled'])for widget in app.characters.values.values())
            assert all(widget.instate(['disabled'])for widget in app.characters.skill_checks.values())
            for section in ('mates','captains','ships','world','library','gameplay','characters'):
                app.switch_section(section); settle()
                assert app.section == section
                assert bool(app.characters.frame.winfo_ismapped()) == (section == 'characters')
            app.project.save_project(Path(folder)/'after.json')
            assert before == (Path(folder)/'after.json').read_bytes(), 'Browsing changed the project'
            assert original == app.project.build(), 'Browsing changed ROM output'
            app.characters.custom_box.invoke();settle()
            assert app.project.custom_characters
            from sailors import SKILLS
            for i in range(6):
                app.characters.list.selection_clear(0,'end');app.characters.list.selection_set(i);app.characters.pick();settle()
                app.characters.fixed_luck.set(True)
                for n,key in enumerate(ATTRIBUTES):app.characters.variables[key].set(str(55+(i*7+n*3)%46))
                app.characters.variables['navigation_level'].set(str(1+i*19))
                app.characters.variables['battle_level'].set(str(100-i*19))
                for key,_,bit in SKILLS:app.characters.skill_vars[key].set(bool((31 if i%2 else 0)&bit))
                ready=tk.BooleanVar(root,False);root.after(450,lambda:ready.set(True));root.wait_variable(ready);settle()
                assert app.project.character_record(i)['leadership']==55+i*7
                assert app.project.character_record(i)['skills']==(31 if i%2 else 0)
                assert app.project.character_record(i)['navigation_level']==1+i*19
                assert app.project.character_record(i)['battle_level']==100-i*19
                assert '*'in app.characters.list.get(i)
            changed=app.project.manifest();app.characters.variables['luck'].set('101')
            ready=tk.BooleanVar(root,False);root.after(450,lambda:ready.set(True));root.wait_variable(ready);settle()
            assert app.project.manifest()==changed and 'Finish editing:'in app.status.cget('text')
            app.characters.render();settle()
            app.characters.custom_box.invoke();settle()
            assert not app.project.custom_characters and app.project.character_edits
            assert all(widget.instate(['disabled'])for widget in app.characters.values.values())
            assert app.characters_nav.cget('style')=='Selected.Changed.Nav.TButton'
            app.project.save_project(Path(folder)/'edited.json');copy=ShipProject(rom_path);copy.load_project(Path(folder)/'edited.json')
            assert copy.build()==app.project.build()
            app.switch_section('ships');settle()
            # Loading a different saved state into the same project must not
            # let an inactive character form write stale values back.
            app.project.load_project(Path(folder)/'before.json');app.reload_project_view();app.commit()
            assert app.project.character_edits==[]
            app.project.load_project(Path(folder)/'edited.json');app.reload_project_view();app.switch_section('characters');settle()
            app.characters.custom_box.invoke();settle();app.characters.restore_button.invoke();settle()
            assert not any(e['id']==5 for e in app.project.character_edits)
            assert any(e['id']==0 for e in app.project.character_edits)
            with patch('tkinter.messagebox.askyesno',return_value=True):app.reset_section('characters')
            settle();assert not app.project.character_edits and not app.project.custom_characters
            assert app.project.build()==original
            for section in ('mates','captains'):
                app.switch_data(section);settle()
                for size in ('640x480','1024x768','1440x900','1920x1080'):
                    root.geometry(size+'+0+0');settle()
                    label,number=app.mate_field_widgets['swordsmanship']
                    assert int(label.cget('wraplength'))==0
                    assert label.winfo_reqheight()==app.mate_field_widgets['leadership'][0].winfo_reqheight()
                    assert label.winfo_rootx()+label.winfo_width()<=number.winfo_rootx(),(section,size,'attribute label overlaps value')
            app.switch_section('characters');settle()
            # Optional QA image of the actual rendered application.
            if os.environ.get('NH_CHARACTERS_SCREENSHOT'):
                from PIL import ImageGrab
                root.geometry('1440x900+0+0'); settle()
                app.characters.list.selection_clear(0,'end');app.characters.list.selection_set(0);app.characters.pick();settle()
                app.characters.custom_box.invoke();settle()
                ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(os.environ['NH_CHARACTERS_SCREENSHOT'])
            result = dict(status='PASS', characters=6, portrait_selections=24, sizes=sizes,
                          project_unchanged=True, rom_output_unchanged=True, default_locked=True, editable_stats_and_skills=True, editable_starting_levels=True, swordsmanship_one_line_both_browsers=True, automatic_edits=True, invalid_edits_atomic=True, lock_keeps_edits=True, project_roundtrip=True, selected_and_section_restore=True, inactive_form_preserves_loaded_project=True, navigation_order=True)
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        report_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        if root is not None: root.destroy()


