"""Preset transaction races, Library export recovery and reset disclosure."""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from backend import ShipProject
from content_library import ContentLibrary, capture_ship
from custom_presets import PresetStore
import custom_presets
from file_safety import file_lock


class SecondReviewTests(unittest.TestCase):
    def setUp(self):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not source.exists():
            self.skipTest('Requires verified stock USA ROM')
        self.p = ShipProject(source)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.a = PresetStore(self.folder / 'presets.json')
        self.b = PresetStore(self.a.path)

    def during_prepare(self, callback):
        original = custom_presets.prepare
        fired = [False]
        def interleave(project, manifest):
            if not fired[0]:
                fired[0] = True
                callback()
            return original(project, manifest)
        return patch('custom_presets.prepare', side_effect=interleave)

    def test_overlapping_additions_keep_both_presets_and_descriptions(self):
        with self.during_prepare(lambda: self.b.save('B', self.p, description_text='B notes')):
            self.a.save('A', self.p, description_text='A notes')
        self.assertEqual(set(self.a.read()), {'A', 'B'})
        self.assertEqual(self.a.descriptions(), {'A': 'A notes', 'B': 'B notes'})
        self.assertEqual(set(self.a._document()['presets']), {'A', 'B'})

    def test_new_name_collision_rechecked_after_validation(self):
        with self.during_prepare(lambda: self.b.save('Same', self.p, description_text='First writer')):
            with self.assertRaisesRegex(ValueError, 'already exists'):
                self.a.save('same', self.p, description_text='Second writer')
        self.assertEqual(self.a.descriptions(), {'Same': 'First writer'})

    def test_update_preserves_addition_from_other_window(self):
        self.a.save('A', self.p, description_text='old')
        with self.during_prepare(lambda: self.b.save('B', self.p, description_text='B notes')):
            self.a.save('A', self.p, replace=True, description_text='new')
        self.assertEqual(set(self.a.read()), {'A', 'B'})
        self.assertEqual(self.a.descriptions(), {'A': 'new', 'B': 'B notes'})

    def test_save_does_not_resurrect_concurrently_deleted_preset(self):
        self.a.save('Old', self.p)
        with self.during_prepare(lambda: self.b.delete('Old')):
            self.a.save('New', self.p)
        self.assertEqual(set(self.a.read()), {'New'})
        self.assertEqual(set(self.a.descriptions()), {'New'})

    def test_save_keeps_concurrent_provided_restore(self):
        self.a.save('Classic Plus', self.p)
        self.a.delete('Trade & Exploration', provided=True)
        with self.during_prepare(self.b.restore_provided):
            self.a.save('New', self.p)
        self.assertEqual(set(self.a.read()), {'New'})
        self.assertEqual(self.a.deleted(), [])

    def test_save_delete_and_restore_all_respect_shared_lock(self):
        self.a.save('Existing', self.p)
        before = self.a.path.read_bytes()
        with file_lock(self.a.path.with_suffix('.json.lock'), resource='presets'):
            for action in (lambda: self.b.save('New', self.p), lambda: self.b.delete('Existing'), self.b.restore_provided):
                with self.assertRaisesRegex(ValueError, 'saving presets'):
                    action()
                self.assertEqual(self.a.path.read_bytes(), before)

    def test_inconsistent_descriptions_rejected_before_commit(self):
        self.a.save('Existing', self.p)
        before = self.a.path.read_bytes()
        with self.a._lock():
            with self.assertRaises(ValueError):
                self.a._write(self.a.read(), [], {'Missing': 'Invalid reference'})
        self.assertEqual(self.a.path.read_bytes(), before)

    def library(self):
        library = ContentLibrary(self.p.rom, self.folder / 'library')
        library.put(capture_ship(self.p, 0))
        return library

    def test_library_export_partial_write_is_removed_and_retry_succeeds(self):
        library = self.library()
        before = library.path.read_bytes()
        target = self.folder / 'ships.nhlib'
        def fail(source, destination):
            destination.write(b'{partial')
            raise OSError('disk full')
        with patch('file_safety.shutil.copyfileobj', side_effect=fail):
            with self.assertRaises(OSError):
                library.export_file(target)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.folder.glob('.*.tmp')))
        self.assertEqual(library.path.read_bytes(), before)
        library.export_file(target)
        self.assertEqual(json.loads(target.read_text(encoding='utf-8')), library.document())

    def test_library_export_stage_failure_leaves_no_output(self):
        library = self.library()
        target = self.folder / 'ships.nhlib'
        with patch('file_safety.os.fsync', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                library.export_file(target)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.folder.glob('.*.tmp')))

    def test_library_export_preserves_file_created_during_staging(self):
        from file_safety import stage_bytes
        library = self.library()
        target = self.folder / 'ships.nhlib'
        def other_writer(path, payload):
            temporary = stage_bytes(path, payload)
            target.write_bytes(b'other writer')
            return temporary
        with patch('file_safety.stage_bytes', side_effect=other_writer):
            with self.assertRaises(FileExistsError):
                library.export_file(target)
        self.assertEqual(target.read_bytes(), b'other writer')
        self.assertFalse(list(self.folder.glob('.*.tmp')))

    def test_world_reset_discloses_scope_and_cancel_preserves_everything(self):
        from app import Editor
        import discovery_content, item_shops
        self.p.item_edits = item_shops.seeded_shuffle(self.p.rom, '1234')
        self.p.item_seed = '1234'
        entry = discovery_content.capture(self.p, 0)
        entry['name'] = 'Reset Test Site'
        discovery_content.load(self.p, entry, 0)
        self.p.fleet_control = True
        self.p.update_character(0, dict(battle_level=75))
        self.p.update(0, dict(hull=40))
        before = copy.deepcopy(self.p.__dict__)
        app = SimpleNamespace(project=self.p, root=None, cancel_auto_edit=lambda: None,
                              auto_edit=lambda: None, reload_project_view=lambda: None,
                              world=SimpleNamespace(economy_panel=SimpleNamespace(cancel=lambda: None), goods_edit_timer=None, cancel_goods_edit=lambda:None,item_editor=SimpleNamespace(cancel=lambda:None)))
        messages = []
        with patch('tkinter.messagebox.askyesno', side_effect=lambda title, body, **kw: messages.append(body) or False):
            Editor.reset_section(app, 'world')
        self.assertEqual(self.p.__dict__, before)
        for phrase in ('item shop locations', 'Discovery replacements', 'Goods and item shuffles', 'Library', 'presets'):
            self.assertIn(phrase, messages[0])
        with patch('tkinter.messagebox.askyesno', return_value=True):
            Editor.reset_section(app, 'world')
        self.assertEqual(self.p.item_edits, [])
        self.assertIsNone(self.p.item_seed)
        self.assertEqual(self.p.discovery_entries, before['discovery_entries'])
        self.assertEqual(self.p.ships, before['ships'])
        self.assertEqual(self.p.character_edits, before['character_edits'])
        self.assertEqual(self.p.fleet_control, before['fleet_control'])


if __name__ == '__main__':
    unittest.main()
