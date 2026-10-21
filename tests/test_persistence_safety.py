"""Regressions for interrupted writes, concurrent Libraries and blind summaries."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from backend import ShipProject, apply_ips
from content_library import ContentLibrary, capture_ship, new_id
from file_safety import atomic_write, file_lock, publish_files


class FileSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()

    def test_failed_stage_keeps_existing_file_and_cleans_temporary(self):
        target = self.folder / 'data.json'
        target.write_bytes(b'previous')
        with patch('file_safety.os.fsync', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                atomic_write(target, b'new')
        self.assertEqual(target.read_bytes(), b'previous')
        self.assertEqual(list(self.folder.iterdir()), [target])

    def test_export_publish_failure_cleans_current_and_previous_files(self):
        import shutil
        files = [(self.folder / name, b'complete payload') for name in ('a.sfc', 'a.ips', 'a.changes.json')]
        original = shutil.copyfileobj
        def broken(source, destination):
            if Path(destination.name).suffix == '.ips':
                destination.write(b'pa')
                raise OSError('disk full')
            return original(source, destination)
        with patch('file_safety.shutil.copyfileobj', side_effect=broken):
            with self.assertRaises(OSError):
                publish_files(files)
        self.assertEqual(list(self.folder.iterdir()), [])
        publish_files(files)
        for target, payload in files:
            self.assertEqual(target.read_bytes(), payload)

    def test_export_stage_failure_publishes_nothing(self):
        from file_safety import stage_bytes
        files = [(self.folder / name, b'data') for name in ('a.sfc', 'a.ips')]
        def fail_second(path, payload):
            if Path(path).suffix == '.ips':
                raise OSError('disk full')
            return stage_bytes(path, payload)
        with patch('file_safety.stage_bytes', side_effect=fail_second):
            with self.assertRaises(OSError):
                publish_files(files)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_export_collision_preserves_other_writers_file(self):
        import shutil
        files = [(self.folder / name, b'ours') for name in ('a.sfc', 'a.ips')]
        original = shutil.copyfileobj
        def competing_writer(source, destination):
            original(source, destination)
            files[1][0].write_bytes(b'other editor')
        with patch('file_safety.shutil.copyfileobj', side_effect=competing_writer):
            with self.assertRaises(FileExistsError):
                publish_files(files)
        self.assertFalse(files[0][0].exists())
        self.assertEqual(files[1][0].read_bytes(), b'other editor')
        self.assertFalse(list(self.folder.glob('.*.tmp')))

    def test_lock_blocks_another_process_and_releases_after_exit(self):
        path = self.folder / '.library.lock'
        code = ('import sys;sys.path.insert(0,sys.argv[1]);'
                'from file_safety import file_lock;'
                'lock=file_lock(sys.argv[2]);lock.__enter__();print("locked",flush=True);sys.stdin.readline()')
        child = subprocess.Popen([sys.executable, '-c', code, str(ROOT / 'mod_tool'), str(path)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            with self.assertRaisesRegex(ValueError, 'Another editor'):
                with file_lock(path):
                    self.fail('Acquired an already held lock')
        finally:
            child.kill()
            child.communicate(timeout=10)
        with file_lock(path):
            pass


class ProjectAndLibrarySafetyTests(unittest.TestCase):
    def setUp(self):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not source.exists():
            self.skipTest('Requires verified stock USA ROM')
        self.p = ShipProject(source)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()

    def test_project_failed_commit_preserves_main_and_good_backup(self):
        path = self.folder / 'project.json'
        self.p.save_project(path)
        original = path.read_bytes()
        self.p.update(0, dict(hull=40))
        replace = os.replace
        def fail_current(source, destination):
            if Path(destination) == path:
                raise OSError('interrupted commit')
            return replace(source, destination)
        for _ in range(2):
            with patch('file_safety.os.replace', side_effect=fail_current):
                with self.assertRaises(OSError):
                    self.p.save_project(path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(path.with_suffix('.json.bak').read_bytes(), original)
            self.assertFalse(list(self.folder.glob('.*.tmp')))
        self.p.save_project(path)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), self.p.manifest())
        self.assertEqual(path.with_suffix('.json.bak').read_bytes(), original)

    def test_damaged_current_does_not_replace_last_good_backup(self):
        path = self.folder / 'project.json'
        self.p.save_project(path)
        good = path.read_bytes()
        self.p.update(0, dict(hull=40))
        self.p.save_project(path)
        path.write_bytes(b'{broken')
        self.p.save_project(path)
        self.assertEqual(path.with_suffix('.json.bak').read_bytes(), good)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), self.p.manifest())

    def test_invalid_project_does_not_touch_disk(self):
        path = self.folder / 'project.json'
        self.p.save_project(path)
        original = path.read_bytes()
        self.p.ships[0]['hull'] = 101
        with self.assertRaises(ValueError):
            self.p.save_project(path)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(path.with_suffix('.json.bak').exists())

    def test_export_roundtrip_and_existing_output_protection(self):
        target = self.folder / 'game.sfc'
        self.p.update(0, dict(hull=40))
        self.p.export(target)
        self.assertEqual(apply_ips(self.p.rom, target.with_suffix('.ips').read_bytes()), target.read_bytes())
        original = target.read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.p.export(target)
        self.assertEqual(target.read_bytes(), original)

    def test_backend_export_can_retry_after_partial_write(self):
        import shutil
        target = self.folder / 'game.sfc'
        original = shutil.copyfileobj
        def broken(source, destination):
            if Path(destination.name).suffix == '.ips':
                destination.write(b'pa')
                raise OSError('disk full')
            return original(source, destination)
        with patch('file_safety.shutil.copyfileobj', side_effect=broken):
            with self.assertRaises(OSError):
                self.p.export(target)
        self.assertEqual(list(self.folder.iterdir()), [])
        self.p.export(target)
        self.assertEqual(apply_ips(self.p.rom, target.with_suffix('.ips').read_bytes()), target.read_bytes())

    def test_two_libraries_merge_separate_additions_and_collections(self):
        a = ContentLibrary(self.p.rom, self.folder)
        b = ContentLibrary(self.p.rom, self.folder)
        first, second = capture_ship(self.p, 0), capture_ship(self.p, 1)
        a.put(first)
        a.collections = {'First': [first['id']]}
        a.save()
        b.put(second)
        b.collections['Second'] = [second['id']]
        b.save()
        saved = ContentLibrary(self.p.rom, self.folder)
        self.assertEqual({e['id'] for e in saved.entries}, {first['id'], second['id']})
        self.assertEqual(set(saved.collections), {'First', 'Second'})
        self.assertTrue(a.reload_if_changed())
        self.assertEqual(a.document(), saved.document())

    def test_conflicting_entry_update_is_rejected_then_reload_allows_retry(self):
        a = ContentLibrary(self.p.rom, self.folder)
        entry = capture_ship(self.p, 0)
        entry['id'] = new_id()  # Concurrency edits use a user variant, not protected stock.
        a.put(entry)
        b = ContentLibrary(self.p.rom, self.folder)
        first, second = copy.deepcopy(entry), copy.deepcopy(entry)
        first['ship']['hull'], second['ship']['hull'] = 40, 45
        a.put(first)
        with self.assertRaisesRegex(ValueError, 'another editor'):
            b.put(second)
        self.assertEqual(ContentLibrary(self.p.rom, self.folder).entries, [first])
        self.assertTrue(b.reload_if_changed())
        b.put(second)
        self.assertEqual(ContentLibrary(self.p.rom, self.folder).entries, [second])

    def test_stale_clear_rejects_new_addition(self):
        a = ContentLibrary(self.p.rom, self.folder)
        a.put(capture_ship(self.p, 0))
        b = ContentLibrary(self.p.rom, self.folder)
        a.put(capture_ship(self.p, 1))
        with self.assertRaisesRegex(ValueError, 'another editor'):
            b.clear()
        self.assertEqual(len(ContentLibrary(self.p.rom, self.folder).entries), 2)
        b.reload_if_changed()
        b.clear()
        self.assertEqual(ContentLibrary(self.p.rom, self.folder).entries, [])

    def test_same_collection_conflict_keeps_saved_version(self):
        a = ContentLibrary(self.p.rom, self.folder)
        first, second = capture_ship(self.p, 0), capture_ship(self.p, 1)
        a.put(first)
        a.put(second)
        a.collections = {'Favorites': [first['id']]}
        a.save()
        b = ContentLibrary(self.p.rom, self.folder)
        a.collections['Favorites'] = [second['id']]
        a.save()
        b.collections['Favorites'] = [first['id'], second['id']]
        with self.assertRaisesRegex(ValueError, 'another editor'):
            b.save()
        self.assertEqual(ContentLibrary(self.p.rom, self.folder).collections, a.collections)

    def test_blind_goods_seed_hidden_but_normal_seed_visible(self):
        from app import Editor
        class Label:
            def configure(self, **kwargs):
                self.text = kwargs['text']
        label = Label()
        app = SimpleNamespace(project=self.p, active_changes_text=label,
                              sidebar=SimpleNamespace(winfo_width=lambda: 300))
        self.p.goods_shuffle = dict(seed='1234', mode='all', blind=True)
        Editor.refresh_active_changes(app)
        self.assertIn('(blind)', label.text)
        self.assertNotIn('1234', label.text)
        self.p.goods_shuffle['blind'] = False
        Editor.refresh_active_changes(app)
        self.assertIn('1234', label.text)


if __name__ == '__main__':
    unittest.main()
