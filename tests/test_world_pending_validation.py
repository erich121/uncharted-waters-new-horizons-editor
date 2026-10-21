"""Invalid World drafts must survive timers and block save/export/navigation."""
import copy
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from app import Editor
from backend import ShipProject
from economy import values
from trade_goods import offers


class WorldValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not source.exists():
            raise unittest.SkipTest('Requires verified stock USA ROM')
        cls.stock = ShipProject(source)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        environment = patch.dict(os.environ, LOCALAPPDATA=str(self.folder))
        environment.start()
        self.addCleanup(environment.stop)
        self.root = tk.Tk()
        self.addCleanup(self.close_editor)
        self.app = Editor(self.root)
        self.root.geometry('1200x850+20+20')
        self.app.project = copy.deepcopy(self.stock)
        self.app.selected = 0
        self.app.show(0)
        self.root.update()
        self.app.cancel_auto_edit()
        self.app.switch_section('world')
        self.world = self.app.world
        self.p = self.app.project
        self.errors = []
        failures = patch.object(self.app, 'fail', side_effect=lambda error: self.errors.append(str(error)))
        failures.start()
        self.addCleanup(failures.stop)

    def close_editor(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()

    def economy(self):
        self.p.custom_economy = True
        self.world.mode.set('Economy')
        self.world.change_mode()
        return self.world.economy_panel

    def goods(self):
        self.p.custom_goods = True
        self.world.mode.set('Goods')
        self.world.change_mode()
        good = next(row for row in self.world.records if row['sources'])
        self.world.selected = good['id']
        self.world.details()
        port = good['sources'][0]['port']
        self.world.goods_port_box.current(port)
        self.world.select_edit_port()
        return port, good['id']

    def assert_save_and_export_blocked(self):
        for action in (self.app.save_project, self.app.export):
            with patch('tkinter.filedialog.asksaveasfilename') as picker:
                action()
            picker.assert_not_called()
        self.assertEqual(len(self.errors), 2)

    def test_invalid_economy_remains_visible_and_blocks_save_after_timer(self):
        panel = self.economy()
        panel.variables['economy'].set('invalid')
        panel.flush()
        self.assertIsNone(panel.timer)
        self.assertIsNotNone(panel.pending)
        self.app.update_status()
        self.assertEqual(panel.variables['economy'].get(), 'invalid')
        self.assert_save_and_export_blocked()

    def test_invalid_goods_remains_visible_and_blocks_save_after_timer(self):
        self.goods()
        self.world.goods_gate.set('invalid')
        self.world.flush_goods_gate()
        self.assertIsNone(self.world.goods_edit_timer)
        self.app.update_status()
        self.assertEqual(self.world.goods_gate.get(), 'invalid')
        self.assert_save_and_export_blocked()

    def test_invalid_economy_blocks_world_mode_and_section_changes(self):
        panel = self.economy()
        panel.variables['industry'].set('1001')
        panel.flush()
        self.world.mode.set('Goods')
        self.world.change_mode()
        self.assertEqual(self.world.view, 'Economy')
        self.assertEqual(self.world.mode.get(), 'Economy')
        self.app.switch_section('ships')
        self.assertEqual(self.app.section, 'world')
        self.assertEqual(panel.variables['industry'].get(), '1001')

    def test_invalid_economy_blocks_port_and_region_changes(self):
        panel = self.economy()
        port = panel.port
        panel.variables['economy'].set('0')
        panel.flush()
        self.world.list.selection_clear(0, 'end')
        self.world.list.selection_set(self.world.rows.index((port + 1) % 100))
        self.world.pick()
        self.assertEqual(self.world.selected, port)
        self.world.region.set('Northern Europe')
        self.world.change_region()
        self.assertEqual(self.world.region.get(), 'All regions')
        self.assertEqual(panel.port, port)

    def test_invalid_goods_blocks_port_change_and_manual_edit_lock(self):
        port, good = self.goods()
        self.world.goods_gate.set('201')
        self.world.flush_goods_gate()
        self.world.goods_port_box.current((port + 1) % 100)
        self.world.select_edit_port()
        self.assertEqual(self.world.goods_port_box.current(), port)
        self.world.custom_goods_var.set(False)
        self.world.toggle_custom_goods()
        self.assertTrue(self.p.custom_goods)
        self.assertTrue(self.world.custom_goods_var.get())
        self.assertEqual(self.world.goods_pending[:2], (port, good))

    def test_invalid_economy_blocks_lock_and_region_apply(self):
        panel = self.economy()
        panel.variables['economy'].set('bad')
        panel.flush()
        panel.enabled.set(False)
        panel.toggle()
        self.assertTrue(self.p.custom_economy)
        panel.bulk_vars['economy'].set('700')
        panel.apply_region()
        self.assertEqual(self.p.economy_edits, [])

    def test_correcting_economy_saves_latest_valid_values(self):
        panel = self.economy()
        panel.variables['economy'].set('bad')
        panel.flush()
        panel.variables['economy'].set('601')
        target = self.folder / 'economy.json'
        with patch('tkinter.filedialog.asksaveasfilename', return_value=str(target)):
            self.app.save_project()
        q = ShipProject(self.p.source)
        q.load_project(target)
        self.assertEqual(values(q.rom, q.economy_edits)[panel.port]['economy'], 601)
        self.assertIsNone(panel.pending)
        self.assertEqual(self.errors, [])

    def test_correcting_goods_saves_and_keeps_native_gate_range(self):
        port, good = self.goods()
        self.world.goods_gate.set('bad')
        self.world.flush_goods_gate()
        self.world.goods_gate.set('2010')
        target = self.folder / 'goods.json'
        with patch('tkinter.filedialog.asksaveasfilename', return_value=str(target)):
            self.app.save_project()
        q = ShipProject(self.p.source)
        q.load_project(target)
        self.assertEqual(next(row for row in offers(q.rom, q.goods_edits)[port] if row['good'] == good)['economy_required'], 2010)
        self.assertIsNone(self.world.goods_pending)
        self.assertEqual(self.errors, [])

    def test_explicit_restore_clears_invalid_drafts(self):
        panel = self.economy()
        panel.variables['economy'].set('bad')
        panel.flush()
        panel.restore_port()
        self.assertIsNone(panel.pending)
        self.goods()
        self.world.goods_gate.set('bad')
        self.world.flush_goods_gate()
        self.world.restore_good()
        self.assertIsNone(self.world.goods_pending)
        self.app.commit()
        self.assertEqual(self.errors, [])

    def test_world_reset_clears_failed_drafts(self):
        panel = self.economy()
        panel.variables['economy'].set('bad')
        panel.flush()
        with patch('tkinter.messagebox.askyesno', return_value=True):
            self.app.reset_section('world')
        self.assertIsNone(panel.pending)
        self.assertIsNone(self.world.goods_pending)
        self.app.commit()
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main()
