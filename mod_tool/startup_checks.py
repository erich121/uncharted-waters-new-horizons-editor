"""Verify remembered ROM startup and recovery with isolated user preferences."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from preferences import remember_rom, last_rom, preferences_path


def run(Editor,rom_path,report_path):
    report_path=Path(report_path);report_path.parent.mkdir(parents=True,exist_ok=True)
    result=dict(status='FAIL');root=None
    try:
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,LOCALAPPDATA=folder), patch('tkinter.messagebox.showerror') as error:
            rom_path=str(Path(rom_path).resolve())
            def start():
                nonlocal root
                root=tk.Tk();root.withdraw();app=Editor(root)
                root.after_idle(app.restore_last_rom);root.update()
                return app
            app=start();assert app.project is None
            # Loading through the normal picker remembers only verified files.
            with patch('tkinter.filedialog.askopenfilename',return_value=rom_path):app.open_rom()
            assert app.project and last_rom()==rom_path
            root.destroy();root=None
            app=start();assert app.project and len(app.project.ships)==25
            assert not app.project.custom_discoveries and not app.project.discovery_entries
            assert app.project.build()[0]==app.project.rom
            assert not __import__('discovery_content').changed_slots(app.project)
            assert 'Stock USA ROM verified' in app.source.cget('text')
            assert app.list.size()==25
            before=preferences_path().read_bytes()
            with patch('tkinter.filedialog.askopenfilename',return_value=''):app.open_rom()
            assert preferences_path().read_bytes()==before
            invalid=Path(folder)/'invalid.sfc';invalid.write_bytes(b'not a game')
            with patch('tkinter.filedialog.askopenfilename',return_value=str(invalid)):app.open_rom()
            assert error.call_count==1 and last_rom()==rom_path
            # A delayed startup callback never replaces an existing project.
            current=app.project;app.project.custom_ships=True
            app.restore_last_rom();assert app.project is current and app.project.custom_ships
            root.destroy();root=None;error.reset_mock()
            for path in (Path(folder)/'missing.zip',invalid):
                remember_rom(path);app=start()
                assert app.project is None and not error.called
                assert 'unavailable or invalid' in app.source.cget('text')
                root.destroy();root=None
            preferences_path().write_text('broken',encoding='utf-8')
            app=start();assert app.project is None and not error.called
            # A new valid choice recovers from corrupt preferences.
            with patch('tkinter.filedialog.askopenfilename',return_value=rom_path):app.open_rom()
            assert app.project and last_rom()==rom_path
            result=dict(status='PASS',automatic_verified_rom_load=True,original_discoveries_on_startup=True,missing_invalid_corrupt_recovery=True,
                        cancel_and_failed_selection_keep_last_good_path=True,existing_project_preserved=True)
    except Exception as exception:
        result['error']=str(exception);raise
    finally:
        report_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        if root is not None:root.destroy()
