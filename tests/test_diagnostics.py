"""Troubleshooting evidence must survive failures in windowed builds."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticsTests(unittest.TestCase):
    def run_script(self, script):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = dict(os.environ, LOCALAPPDATA=temporary.name,
                           PYTHONPATH=str(ROOT / 'mod_tool'))
        result = subprocess.run([sys.executable, '-c', script], env=environment,
                                capture_output=True, timeout=30)
        folder = Path(temporary.name) / 'New Horizons Editor' / 'Logs'
        return result, folder

    def test_startup_failure_and_native_handler_persist(self):
        result, folder = self.run_script('''
import diagnostics, faulthandler
diagnostics.initialize()
assert faulthandler.is_enabled()
raise RuntimeError('startup sentinel')
''')
        self.assertNotEqual(result.returncode, 0)
        text = (folder / 'editor.log').read_text(encoding='utf-8')
        self.assertIn('Session started', text)
        self.assertIn('Unhandled application error', text)
        self.assertIn('RuntimeError: startup sentinel', text)
        self.assertIn('Traceback', text)
        self.assertTrue((folder / 'native-crash.log').exists())

    def test_windowed_callback_and_thread_failures(self):
        result, folder = self.run_script('''
import diagnostics, threading, sys, tkinter as tk
from types import SimpleNamespace
root=tk.Tk(); root.withdraw()
diagnostics.initialize()
seen=[]
root.report_callback_exception=lambda *args:seen.append(args)
diagnostics.attach_editor(SimpleNamespace(root=root,section='library'))
sys.stderr=None
def broken():raise ValueError('Help callback sentinel')
def thread_broken():raise RuntimeError('thread sentinel')
thread=threading.Thread(target=thread_broken,name='diagnostics-test');thread.start();thread.join()
root.after(0,broken);root.after(100,root.quit);root.mainloop()
assert len(seen)==1
root.destroy()
''')
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        text = (folder / 'editor.log').read_text(encoding='utf-8')
        self.assertIn('UI callback error; section=library', text)
        self.assertIn('ValueError: Help callback sentinel', text)
        self.assertIn('RuntimeError: thread sentinel', text)

    def test_rotates_and_initialization_is_idempotent(self):
        result, folder = self.run_script('''
import diagnostics
directory=diagnostics.initialize()
assert directory==diagnostics.initialize()
assert len(diagnostics.LOGGER.handlers)==1
handler=diagnostics.LOGGER.handlers[0];handler.maxBytes=300
for i in range(40):diagnostics.LOGGER.info('Rotation sentinel %s',i)
''')
        self.assertEqual(result.returncode, 0)
        self.assertTrue((folder / 'editor.log.1').exists())
        self.assertLessEqual(len(list(folder.glob('editor.log*'))), 4)


if __name__ == '__main__':
    unittest.main()
