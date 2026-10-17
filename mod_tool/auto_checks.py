"""Verify edits reach the project and dirty markers without Apply buttons."""
import json,copy,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject


def run(Editor,rom_path,report_path):
    root=tk.Tk();report_path=Path(report_path);report_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        app=Editor(root);root.geometry('1100x820+0+0');app.project=ShipProject(rom_path);app.project.custom_ships=True;app.show(0);app.refresh_list()
        def settle():
            done=tk.BooleanVar(root,value=False);root.after(450,lambda:done.set(True));root.wait_variable(done);root.update()
        def edit(widget,value):widget.delete(0,'end');widget.insert(0,str(value));settle()
        errors=[]
        with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            settle();assert not app.apply_button.winfo_ismapped()
            assert all('Changed.'not in button.cget('style')for button in app.section_buttons.values())
            original=app.project.ships[0]['hull'];edit(app.entries['hull'],original+1)
            assert app.project.ships[0]['hull']==original+1 and '*'in app.list.get(0)
            assert app.entries['hull'].cget('style')=='Changed.TSpinbox'
            from app import CHANGE_ORANGE
            assert app.list.itemcget(0,'foreground')==CHANGE_ORANGE
            assert app.list.itemcget(0,'selectforeground')==CHANGE_ORANGE
            assert 'Changed.'in app.section_buttons['ships'].cget('style')
            app.restore_button.invoke();settle()
            assert app.project.ships[0]['hull']==original and '*'not in app.list.get(0)
            assert app.entries['hull'].cget('style')=='TSpinbox'
            assert app.list.itemcget(0,'foreground')=='#17243d'
            edit(app.entries['hull'],original+1)
            edit(app.entries['hull'],'')
            assert app.project.ships[0]['hull']==original+1 and 'Finish editing:'in app.status.cget('text')and not errors
            app.restore_button.invoke();settle()
            assert app.project.ships[0]['hull']==original and '*'not in app.list.get(0)
            app.switch_data('mates');settle();app.custom_character_box.invoke();settle();record=app.character_selection()
            original=app.project.character_record(record)['leadership']
            edit(app.mate_field_widgets['leadership'][1],original-1 if original else 1)
            assert app.project.character_record(record)['leadership']!=original
            assert '*'in app.list.get(app.mate_rows.index(record))and not app.sailor_apply_button.winfo_ismapped()
            assert app.list.itemcget(app.mate_rows.index(record),'foreground')==CHANGE_ORANGE
            assert 'Changed.'in app.section_buttons['mates'].cget('style')
            app.sailor_restore_button.invoke();settle()
            assert app.project.character_record(record)['leadership']==original
            assert '*'not in app.list.get(app.mate_rows.index(record))
            assert 'Changed.'not in app.section_buttons['mates'].cget('style')
            app.switch_section('gameplay');settle();assert app.active_changes.winfo_ismapped()and not app.gameplay_apply_button.winfo_ismapped()
            app.fleet_var.set(True);app.difficulty_var.set(True);settle()
            assert app.project.fleet_control and app.project.fleet_difficulty
            text=app.active_changes_text.cget('text')
            assert 'Fleet Control'in text and 'Custom Fleets'in text and 'Repair Safeguard'not in text
            app.fleet_var.set(False);app.difficulty_var.set(False);settle()
            assert not app.project.fleet_control and not app.project.fleet_difficulty
            assert 'Fleet Control'not in app.active_changes_text.cget('text')
            app.switch_section('world');settle();assert not app.active_changes.winfo_ismapped()
            # Exercise each independent reset against the same saved test fixture.
            fields=('custom_ships','custom_mates','custom_captains','custom_goods','custom_economy','goods_edits','economy_edits','ships','original_availability','portraits','character_edits','free_agent_shuffle','repair_safeguard','fleet_control','fleet_difficulty','fleet_rules')
            def snapshot():return {key:copy.deepcopy(getattr(app.project,key))for key in fields}
            def load_fixture(state):
                for key,value in state.items():setattr(app.project,key,copy.deepcopy(value))
                app.reload_project_view();settle()
            app.switch_data('ships');settle()
            edit(app.entries['hull'],app.project.original[app.selected]['hull']+1)
            app.project.add_ship(10);app.project.fleet_rules[0][0][0]=25
            app.project.custom_mates=True;app.project.custom_captains=True
            app.project.update_character(79,dict(leadership=1))
            app.project.update_character(6,dict(leadership=2))
            app.fleet_var.set(True);settle()
            app.update_status();before=snapshot()
            with patch('tkinter.messagebox.askyesno',return_value=False):app.reset_section('ships')
            assert snapshot()==before
            with patch('tkinter.messagebox.askyesno',return_value=True):app.reset_section('ships')
            assert len(app.project.ships)==25 and not app.project.changes()and not app.project.availability_changes()
            assert app.project.fleet_control and app.project.character_edits==before['character_edits']
            assert app.project.fleet_rules[0][0][0]==-1
            load_fixture(before);assert snapshot()==before
            for section,removed,kept in [('mates',79,6),('captains',6,79)]:
                with patch('tkinter.messagebox.askyesno',return_value=True):app.reset_section(section)
                assert not any(e['id']==removed for e in app.project.character_edits)
                assert any(e['id']==kept for e in app.project.character_edits)
                load_fixture(before);assert snapshot()==before
            app.switch_section('gameplay');settle()
            assert app.gameplay_reset_button.winfo_ismapped()
            with patch('tkinter.messagebox.askyesno',return_value=True):app.gameplay_reset_button.invoke()
            assert not app.project.fleet_control and app.project.repair_safeguard==before['repair_safeguard']
            assert app.project.ships==before['ships']and app.project.character_edits==before['character_edits']
            load_fixture(before);assert snapshot()==before
            from types import SimpleNamespace
            with patch('tkinter.Menu')as menu_factory:
                app.section_menu(SimpleNamespace(x_root=12,y_root=34),'ships')
                menu=menu_factory.return_value
                assert menu.add_command.call_args.kwargs['label']=='Reset section'
                assert menu.add_command.call_args.kwargs['state']=='normal'
                menu.tk_popup.assert_called_once_with(12,34)
                app.section_menu(SimpleNamespace(x_root=12,y_root=34),'world')
                assert menu.add_command.call_args.kwargs['state']=='normal'
            assert app.restore_defaults_button.winfo_ismapped()
            before=snapshot()
            with patch('tkinter.messagebox.askyesno',return_value=False):app.restore_defaults_button.invoke()
            assert snapshot()==before
            with patch('tkinter.messagebox.askyesno',return_value=True):app.restore_defaults_button.invoke()
            settle()
            assert app.project.ships==app.project.original and app.project.original_availability==app.project.stock_availability
            assert not app.project.character_edits and not app.project.portraits
            assert not app.project.fleet_control and not app.project.fleet_difficulty
            assert not app.project.repair_safeguard and not app.project.free_agent_shuffle['enabled']
            assert all('Changed.'not in button.cget('style')for button in app.section_buttons.values())
            # Reproduce hidden character fields reapplying edits after a global reset.
            for section in ('captains','mates'):
                app.switch_data(section);settle();app.custom_character_box.invoke();settle()
                record=app.character_selection();original=app.project.character_record(record)['leadership']
                edit(app.mate_field_widgets['leadership'][1],original-1 if original else 1)
                assert app.project.character_record(record)['leadership']!=original
                app.switch_section('gameplay');settle()
                with patch('tkinter.messagebox.askyesno',return_value=True):app.restore_defaults_button.invoke()
                settle();assert not app.project.character_edits
                assert 'Changed.'not in app.section_buttons[section].cget('style')
                app.switch_data(section);settle()
                assert not app.project.character_edits,'Hidden character fields reapplied an edit after global reset'
                assert app.project.character_record(record)['leadership']==original
                assert app.mate_vars['leadership'].get()==str(original)
                assert '*'not in app.list.get(app.mate_rows.index(record))
                app.commit();assert not app.project.manifest()['character_edits']
                assert 'Changed.'not in app.section_buttons[section].cget('style')
            from sailors import BASE,STRIDE,COUNT
            built,_=app.project.build()
            assert built[BASE:BASE+STRIDE*COUNT]==app.project.rom[BASE:BASE+STRIDE*COUNT]
            app.switch_section('gameplay');settle()
            for section in ('ships','mates','captains'):
                app.switch_data(section);settle()
                app.list.focus_force();root.update()
                rows=app.ship_rows if section=='ships'else app.mate_rows
                start=app.list.curselection()[0]
                # Repeated class-bound key events must keep advancing after list rebuilds.
                for delta in (1,1,1,-1,-1):
                    expected=start+delta
                    key='Down'if delta>0 else 'Up'
                    app.list.event_generate('<KeyPress-'+key+'>');root.update()
                    app.list.event_generate('<KeyRelease-'+key+'>');root.update()
                    assert app.list.curselection()==(expected,),(section,key,expected,app.list.curselection())
                    actual=app.selected if section=='ships'else app.character_selection()
                    assert actual==rows[expected]
                    start=expected
            app.switch_section('gameplay');settle()
            assert app.project.build()==(app.project.rom,[])
            root.geometry('640x480+0+0');settle()
            button=app.restore_defaults_button
            assert button.winfo_ismapped()and button.winfo_rooty()+button.winfo_height()<=root.winfo_rooty()+root.winfo_height()
            assert not errors,errors
        report_path.write_text(json.dumps(dict(status='PASS',automatic_ship_and_character_edits=True,asterisks_update_and_clear_on_restore=True,incomplete_input_preserves_last_valid_data=True,restore_preserved=True,automatic_gameplay_checkboxes=True,active_changes_sidebar=True,manual_apply_buttons_hidden=True,independent_section_resets=True,section_reset_cancel_preserves_project=True,changed_values_colored=True,bright_orange_browser_and_section_markers=True,global_defaults_button_and_cancel=True,character_reset_navigation_does_not_reapply_edits=True,arrow_keys_work_after_list_rebuild=True),indent=2),encoding='utf-8')
    except Exception as error:
        report_path.write_text(json.dumps(dict(status='FAIL',error=repr(error)),indent=2),encoding='utf-8');raise
    finally:root.destroy()
