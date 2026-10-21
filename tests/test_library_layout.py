"""Library presentation checks: visible desktop actions and reachable compact layouts."""
import copy
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from app import Editor
from backend import ShipProject, ports
from content_library import capture_ship, new_id


class LibraryLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not source.exists():
            raise unittest.SkipTest('Requires verified stock USA ROM')
        cls.stock = ShipProject(source)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        environment = patch.dict(os.environ, LOCALAPPDATA=temporary.name)
        environment.start()
        self.addCleanup(environment.stop)
        self.root = tk.Tk()
        self.addCleanup(self.close_editor)
        self.app = Editor(self.root)
        self.root.geometry('1440x900+0+0')
        self.app.project = copy.deepcopy(self.stock)
        self.app.selected = 10
        self.app.show(10)
        self.app.switch_section('library')
        self.panel = self.app.library
        self.panel.store.clear()  # Explicit one-entry layout fixture, not a fresh-install Library.
        self.entry = capture_ship(self.app.project, 10)
        self.entry['id'] = new_id()
        self.panel.store.put(self.entry)
        self.panel.refresh()
        self.settle()

    def close_editor(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()

    def settle(self):
        flag = tk.BooleanVar(self.root, value=False)
        self.root.after(80, lambda: flag.set(True))
        self.root.wait_variable(flag)
        self.root.update()

    def assert_visible(self, widget):
        canvas = self.panel.scroll.canvas
        self.assertGreaterEqual(widget.winfo_rooty(), canvas.winfo_rooty())
        self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height())
        x = widget.winfo_rootx() + widget.winfo_width() // 2
        y = widget.winfo_rooty() + widget.winfo_height() // 2
        self.assertEqual(self.root.winfo_containing(x, y), widget)

    def test_desktop_primary_actions_and_save_visible_without_scrolling(self):
        for size in ('1440x900', '1920x1000'):
            self.root.geometry(size + '+0+0')
            self.settle()
            self.panel.scroll.canvas.yview_moveto(0)
            self.settle()
            self.assertTrue(self.panel.layout[0])
            for widget in (self.panel.replace_button, self.panel.add_button, self.panel.save_button):
                self.assert_visible(widget)
            self.assertGreater(self.panel.list.winfo_height(), 100)

    def test_compact_actions_reachable_and_no_horizontal_overflow(self):
        for size in ('1280x720', '1024x768', '640x480'):
            self.root.geometry(size + '+0+0')
            self.settle()
            self.assertGreater(self.panel.list.winfo_height(), 20)
            self.assertAlmostEqual(self.panel.scroll.canvas.xview()[1], 1.0, places=3)
            for widget in (self.panel.replace_button, self.panel.add_button, self.panel.save_button):
                self.panel.scroll.focus_visible(SimpleNamespace(widget=widget))
                self.settle()
                self.assert_visible(widget)

    def test_long_content_does_not_push_load_actions_off_desktop(self):
        entry = copy.deepcopy(self.entry)
        entry['ship']['name'] = 'Tall Trading Ship'
        entry['description'] = ('A large trading vessel with spacious holds and a strong hull. ' * 4)[:226]
        entry['availability']['ports'] = [p['id'] for p in ports(self.app.project.rom) if p['group'] < 11][:20]
        self.panel.store.put(entry)
        before = self.app.project.manifest()
        self.panel.refresh()
        self.settle()
        self.panel.scroll.canvas.yview_moveto(0)
        self.settle()
        self.assert_visible(self.panel.replace_button)
        self.assert_visible(self.panel.save_button)
        self.assertAlmostEqual(self.panel.scroll.canvas.xview()[1], 1.0, places=3)
        self.assertEqual(self.app.project.manifest(), before)

    def test_discovery_switch_does_not_leave_ship_fields_visible(self):
        from discovery_content import capture
        self.panel.store.put(capture(self.app.project, 0))
        self.panel.kind.set('Discoveries')
        self.panel.change_kind()
        self.settle()
        self.assertFalse(self.panel.stats.winfo_ismapped())
        self.assertFalse(self.panel.description.winfo_ismapped())
        self.assertEqual(self.panel.card.title_label.cget('text'), 'Stored discovery')
        self.panel.kind.set('Ships')
        self.panel.change_kind()
        self.settle()
        self.assertTrue(self.panel.stats.winfo_ismapped())
        for key, variable in self.panel.stat_values.items():
            self.assertEqual(variable.get(), str(self.entry['ship'][key]))


if __name__ == '__main__':
    unittest.main()
