"""Help and Library resizing must leave Tk's timers responsive."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = r'''
import os, sys, traceback, tkinter as tk
from app import Editor
root=tk.Tk(); app=Editor(root)
def failed(*args):
    traceback.print_exception(*args)
    os._exit(1)
root.report_callback_exception=failed
if len(sys.argv)>1:app.load_rom(sys.argv[1])
steps=[]
def configure(size,kind):
    root.geometry(size+'+0+0')
    app.switch_section('library')
    app.library.kind.set(kind);app.library.change_kind()
    app.library.hide_stock_check.invoke()
def help_open():
    app.help();assert app.help_dialog.winfo_exists()
def help_close():
    app.help_dialog.destroy()
for size in ('1440x900','1024x768','800x600'):
    for kind in ('Ships','Discoveries','Items'):
        steps.extend((lambda size=size,kind=kind:configure(size,kind),help_open,help_close))
def advance():
    if steps:
        steps.pop(0)()
        root.after(80,advance)
    else:
        print('PASS: all Library kinds, Help reopens, three sizes, event-loop timers',flush=True)
        root.destroy()
root.after(100,advance)
root.mainloop()
assert not steps
'''


class LibraryHelpTests(unittest.TestCase):
    def check_responsiveness(self, rom=None):
        with tempfile.TemporaryDirectory() as temporary:
            env = dict(os.environ, LOCALAPPDATA=temporary, PYTHONPATH=str(ROOT / 'mod_tool'))
            command = [sys.executable, '-c', SCENARIO]
            if rom is not None:
                command.append(str(rom))
            # A layout hang prevents Tk's own timeout timers from firing.
            # Keep this watchdog outside the UI process.
            result = subprocess.run(command, env=env, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            self.assertIn(b'PASS:', result.stdout)

    def test_library_help_without_rom(self):
        self.check_responsiveness()

    def test_library_help_with_stock_rom(self):
        rom = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not rom.is_file():
            self.skipTest('Requires verified stock USA ROM')
        self.check_responsiveness(rom)


if __name__ == '__main__':
    unittest.main()
