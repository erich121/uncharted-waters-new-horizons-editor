"""Isolated Windows editor workflow for the optional discovery text refresh."""
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch
from PIL import ImageGrab
from backend import ShipProject
from discoveries import catalogue
from discovery_rewrites import DESCRIPTIONS


def run(Editor, rom, report):
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    errors, checks = [], []
    with tempfile.TemporaryDirectory(prefix='discovery-editor-') as temporary, patch.dict(os.environ, {'LOCALAPPDATA': temporary}):
        root = tk.Tk(); root.attributes('-topmost',True)
        try:
            root.geometry('1440x900+0+0')
            app = Editor(root)
            def settle():
                done = tk.BooleanVar(root, value=False)
                root.after(180, lambda: done.set(True))
                root.wait_variable(done)
                root.update()
            with patch('tkinter.messagebox.showerror', side_effect=lambda *a, **k: errors.append(a)), patch('tkinter.messagebox.askyesno', return_value=True):
                assert app.world_gameplay_settings.discovery_check.instate(['disabled'])
                p = app.project = ShipProject(rom)
                app.selected = 0
                app.show(0)
                app.refresh_list()
                app.update_status()
                app.switch_section('library')
                settle()
                before = app.library.store.document()
                app.switch_section('gameplay')
                app.gameplay_notebook.select(2)
                settle()
                panel = app.world_gameplay_settings
                assert not panel.discovery_var.get()
                panel.discovery_check.invoke()
                settle()
                assert p.discovery_rewrites and not p.discovery_entries
                assert app.library.store.document() == before
                assert 'Rewritten discovery descriptions' in app.active_changes_text.cget('text')
                assert 'Changed' in app.section_buttons['discoveries'].cget('style')
                app.gameplay_scroll.canvas.yview_moveto(1)
                settle()
                assert panel.discovery_check.winfo_ismapped()
                ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(report.parent/'Discovery option.png')
                checks.append('Checkbox enabled after ROM load; orange Discoveries section; no Library additions')
                app.switch_section('world')
                app.world.mode.set('Discoveries')
                app.world.change_mode()
                settle()
                assert app.world.discovery_records[0]['description'] == DESCRIPTIONS[0]
                assert catalogue(p.build()[0])[0]['description'] == DESCRIPTIONS[0]
                checks.append('Editor discovery information matches exported text')
                app.switch_section('gameplay')
                app.gameplay_notebook.select(2)
                panel.discovery_check.invoke()
                settle()
                assert not p.discovery_rewrites and p.build()[0] == p.rom
                panel.discovery_check.invoke()
                settle()
                app.reset_section('gameplay')
                settle()
                assert not p.discovery_rewrites and not panel.discovery_var.get()
                checks.append('Turning off and Reset Gameplay restore original descriptions')
                panel.discovery_check.invoke()
                settle()
                app.restore_defaults()
                settle()
                assert not p.discovery_rewrites and p.build()[0] == p.rom
                assert app.library.store.document() == before and not errors, errors
                checks.append('Restore defaults resets option and leaves Library unchanged')
            report.write_text(json.dumps(dict(status='PASS', checks=checks), indent=2), encoding='utf-8')
        except Exception as error:
            report.write_text(json.dumps(dict(status='FAIL', error=str(error), checks=checks), indent=2), encoding='utf-8')
            raise
        finally:
            root.destroy()
