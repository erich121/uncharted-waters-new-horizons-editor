"""Bundled app defaults stay portable and separate from native stock data."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mod_tool'))
from backend import ShipProject, ips, apply_ips
from app_defaults import manifest, new_project

ROOT = Path(__file__).resolve().parents[1]


class AppDefaultTests(unittest.TestCase):
    def setUp(self):
        self.source = ROOT / 'New Horizons (USA).zip'
        if not self.source.exists():
            self.skipTest('Requires stock ROM')

    def test_exact_supplied_defaults_are_bundled(self):
        asset = ROOT / 'mod_tool/assets/default-settings.json'
        self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), '48769292719c62ea4085a6b38830ebd272816efe088eb56bfbd34078c67cc456')
        p = new_project(self.source)
        self.assertEqual(p.manifest(), manifest())
        self.assertIsNone(p.project_path)
        self.assertTrue(p.custom_discoveries)
        self.assertEqual(len(p.discovery_entries), 98)
        self.assertEqual(p.discovery_entries[0]['name'], 'Avebury')
        self.assertEqual(p.discovery_entries[1]['name'], "Pompey's Pillar")

    def test_default_library_is_deterministic_and_contains_only_variants(self):
        from app_defaults import library_document
        from content_library import validate_entry
        doc = library_document(self.source)
        self.assertEqual(doc, library_document(self.source))
        self.assertEqual({e['kind'] for e in doc['entries']}, {'ship', 'discovery', 'item'})
        ships = [e for e in doc['entries'] if e['kind'] == 'ship']
        discoveries = [e for e in doc['entries'] if e['kind'] == 'discovery']
        self.assertEqual(len(ships), 60)
        self.assertEqual(len(discoveries), 196)
        self.assertEqual(len([e for e in discoveries if e['id'].startswith('stock-discovery:')]), 98)
        self.assertEqual(len({e['ship']['name'].casefold() for e in ships}), 60)
        self.assertEqual(len({e['replaces'] for e in discoveries}), 98)
        ids = [e['id'] for e in doc['entries']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len([i for i in ids if i.startswith('stock-ship:')]), 25)
        p = ShipProject(self.source)
        stock_names = {s['name'].casefold() for s in p.original}
        custom = [e for e in ships if not e['id'].startswith('stock-ship:')]
        self.assertEqual(len(custom), 35)
        self.assertTrue(all(e['ship']['name'].casefold() not in stock_names for e in custom))
        from content_library import capture_ship
        from discovery_content import capture as capture_discovery
        from item_library import capture as capture_item
        from items import catalogue
        originals = [capture_ship(p,i,variant=False) for i in range(25)]
        originals += [capture_discovery(p,i) for i in range(98)]
        originals += [capture_item(p,row['id']) for row in catalogue(p.rom)]
        self.assertEqual(doc['collections']['Stock Ships'], [e['id'] for e in originals if e['kind']=='ship'])
        self.assertEqual(doc['collections']['Stock Discoveries'], [e['id'] for e in originals if e['kind']=='discovery'])
        self.assertEqual({e['id']:e for e in doc['entries'] if e['id'].startswith('stock-')}, {e['id']:e for e in originals})
        self.assertEqual([e for e in ships if e['id'].startswith('stock-ship:')], [capture_ship(p,i,variant=False) for i in range(25)])
        for entry in doc['entries']:
            validate_entry(entry, p.rom)
        from app_defaults import preset_document
        self.assertEqual(set(doc['collections']), {'Stock Ships', 'Stock Discoveries'})
        self.assertNotIn('Classic Plus', doc['collections'])  # Settings alone are not content.
        self.assertTrue(all(identity in ids for members in doc['collections'].values() for identity in members))

    def test_previous_whole_library_export_remains_importable(self):
        from app_defaults import library_document
        from content_library import ContentLibrary
        import json
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, Path(d)/'library')
            lib.initialize_presets(self.source)
            old = library_document(self.source, _previous=True)
            path = Path(d)/'previous.nhlib'
            path.write_text(json.dumps(old), encoding='utf-8')
            lib.import_file(path)
            self.assertTrue({e['id'] for e in old['entries']} <= {e['id'] for e in lib.entries})
            self.assertNotIn('Stock Game', lib.collections)
            self.assertEqual(len(lib.collections['Stock Ships']), 25)
            self.assertEqual(len(lib.collections['Stock Discoveries']), 98)

    def test_previous_defaults_lose_only_generated_groupings(self):
        from app_defaults import library_document
        from content_library import ContentLibrary
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, d)
            old = library_document(self.source, _previous=True)
            lib.entries, lib.collections = copy.deepcopy((old['entries'], old['collections']))
            custom_ids = [e['id'] for e in old['entries'] if not e['id'].startswith('stock-')]
            lib.collections['My favorites'] = [custom_ids[0]]
            lib.save()
            before = lib.path.read_bytes()
            (lib.root/'.bundled-content-version').write_text('4')
            self.assertTrue(lib.migrate_bundled_defaults(self.source))
            approved = library_document(self.source)
            self.assertEqual({e['id']:e for e in lib.entries}, {e['id']:e for e in approved['entries']})
            self.assertEqual(set(lib.collections), {'Stock Ships', 'Stock Discoveries', 'My favorites'})
            self.assertEqual(lib.collections['My favorites'], [custom_ids[0]])
            self.assertTrue(all(i in {e['id'] for e in lib.entries} for i in custom_ids))
            self.assertEqual(lib.path.with_suffix('.json.bak').read_bytes(), before)
            self.assertFalse(lib.migrate_bundled_defaults(self.source))

    def test_bad_seed_migration_preserves_manual_stock_and_user_edits(self):
        from app_defaults import library_document
        from content_library import ContentLibrary, capture_ship
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, d)
            old = library_document(self.source, _legacy=True)
            lib.entries, lib.collections = old['entries'], old['collections']
            lib.save()
            lib.put(capture_ship(p, 0))  # User deliberately saved a stock ship.
            variant = copy.deepcopy(next(e for e in lib.entries if e['kind'] == 'ship' and e['ship']['name'] == 'Carrack'))
            variant['ship']['name'] = 'My Carrack'
            lib.put(variant)
            before = lib.path.read_bytes()
            self.assertTrue(lib.migrate_bundled_defaults(self.source))
            self.assertEqual(len(lib.entries), len(library_document(self.source)['entries'])+1)
            self.assertIn(variant, lib.entries)
            self.assertIn(capture_ship(p, 0), lib.entries)
            self.assertEqual(lib.path.with_suffix('.json.bak').read_bytes(), before)
            migrated = copy.deepcopy(lib.document())
            self.assertFalse(lib.migrate_bundled_defaults(self.source))
            self.assertEqual(lib.document(), migrated)

    def test_older_custom_library_receives_originals_without_losing_user_data(self):
        from content_library import ContentLibrary, capture_ship, new_id
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, d)
            entry = capture_ship(p, 0)
            entry['id'] = new_id()
            entry['ship']['name'] = 'Personal ship'
            lib.entries = [entry]
            lib.collections = {'My ships': [entry['id']]}
            lib.save()
            before = lib.path.read_bytes()
            (lib.root / '.bundled-content-version').write_text('3')
            self.assertTrue(lib.migrate_bundled_defaults(self.source))
            self.assertIn(entry, lib.entries)
            self.assertEqual(lib.collections['My ships'], [entry['id']])
            self.assertEqual(len(lib.collections['Stock Ships'])+len(lib.collections['Stock Discoveries']), 123)
            self.assertEqual(len(lib.entries), 185)
            self.assertEqual(lib.path.with_suffix('.json.bak').read_bytes(), before)
            self.assertFalse(lib.migrate_bundled_defaults(self.source))

    def test_unrelated_library_keeps_entry_that_matches_old_defaults(self):
        from app_defaults import library_document
        from content_library import ContentLibrary
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, d)
            legacy = library_document(self.source, _legacy=True)
            current_ids = {e['id'] for e in library_document(self.source)['entries']}
            entry = next(e for e in legacy['entries'] if e['id'] not in current_ids)
            lib.put(entry)
            self.assertTrue(lib.migrate_bundled_defaults(self.source))
            self.assertIn(entry, lib.entries)
            self.assertEqual(len(lib.collections['Stock Ships'])+len(lib.collections['Stock Discoveries']), 123)

    def test_stock_name_collision_and_modified_original_are_preserved(self):
        from content_library import ContentLibrary, capture_ship
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, d)
            edited = capture_ship(p, 0)
            edited['ship']['name'] = 'Older edited ship'
            lib.entries = [edited]
            lib.collections = {'Stock Game': [edited['id']], 'Favorites': [edited['id']]}
            lib.save()
            self.assertTrue(lib.migrate_bundled_defaults(self.source))
            variant = next(e for e in lib.entries if e.get('ship', {}).get('name') == 'Older edited ship')
            self.assertFalse(variant['id'].startswith('stock-'))
            self.assertEqual(lib.collections['Favorites'], [variant['id']])
            self.assertEqual(lib.collections['Stock Game'], [variant['id']])
            self.assertIn(capture_ship(p, 0), lib.entries)
            self.assertEqual(len(lib.collections['Stock Ships'])+len(lib.collections['Stock Discoveries']), 123)

    def test_library_defaults_initialize_once_and_restore_after_deletion(self):
        from content_library import ContentLibrary
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, d)
            self.assertTrue(lib.initialize_presets(self.source))
            defaults = copy.deepcopy(lib.document())
            lib.clear()
            self.assertFalse(lib.initialize_presets(self.source))
            self.assertEqual(lib.entries, [])  # An existing intentionally empty file is preserved.
            lib.restore_presets(self.source)
            self.assertEqual(lib.document(), defaults)
            entry = copy.deepcopy(next(e for e in defaults['entries'] if e['kind'] == 'discovery' and not e['id'].startswith('stock-')))
            entry['name'] = 'My discovery'
            lib.put(entry)
            custom = copy.deepcopy(lib.document())
            before = lib.path.read_bytes()
            with patch.object(lib, 'save', side_effect=OSError('Disk full')):
                with self.assertRaises(OSError):
                    lib.restore_presets(self.source)
            self.assertEqual(lib.document(), custom)
            self.assertEqual(lib.path.read_bytes(), before)
            lib.restore_presets(self.source)
            self.assertEqual(lib.document(), defaults)
            self.assertEqual(lib.path.with_suffix('.json.bak').read_bytes(), before)
            lib.path.unlink()
            self.assertTrue(lib.initialize_presets(self.source))
            self.assertEqual(lib.document(), defaults)

    def test_existing_or_invalid_library_is_not_overwritten(self):
        from content_library import ContentLibrary
        p = ShipProject(self.source)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(p.rom, d)
            lib.clear()
            before = lib.path.read_bytes()
            self.assertFalse(lib.initialize_presets(self.source))
            self.assertEqual(lib.path.read_bytes(), before)
            lib.path.write_text('broken')
            self.assertFalse(lib.initialize_presets(self.source))
            self.assertEqual(lib.path.read_text(), 'broken')

    def test_startup_does_not_activate_custom_discoveries(self):
        from app_defaults import startup_project
        p = startup_project(self.source)
        self.assertFalse(p.custom_discoveries)
        self.assertFalse(p.discovery_entries)
        self.assertFalse(p.discovery_rewrites)
        self.assertFalse(p.discovery_easy)
        self.assertEqual(p.discovery_identities, [f'stock-discovery:{i:02d}' for i in range(98)])
        self.assertEqual(p.build()[0], p.rom)
        self.assertEqual(len(new_project(self.source).discovery_entries), 98)

    def test_native_references_and_saved_projects_are_not_overlaid(self):
        native = ShipProject(self.source)
        p = new_project(self.source)
        self.assertEqual(native.original, p.original)
        self.assertEqual(native.stock_availability, p.stock_availability)
        self.assertEqual(native.ships, p.ships)
        self.assertFalse(native.discovery_entries)
        p.load_manifest(native.manifest())
        self.assertEqual(p.manifest(), native.manifest())
        self.assertEqual(p.build()[0], p.rom)

    def test_fresh_setups_do_not_share_mutable_content(self):
        p = new_project(self.source)
        p.discovery_entries[0]['name'] = 'Changed'
        p.discovery_entries.pop(1)
        p.fleet_rules[0][0][1] = -1
        q = new_project(self.source)
        self.assertEqual(q.manifest(), manifest())
        detached = manifest()
        detached['library_state']['discoveries']['entries'].clear()
        self.assertEqual(len(manifest()['library_state']['discoveries']['entries']), 98)

    def test_original_game_is_stock_but_loaded_edits_can_be_saved_separately(self):
        import tempfile
        from custom_presets import starter, PresetStore
        p = starter(new_project(self.source), 'Original Game')
        self.assertEqual(p.build()[0], p.rom)
        p.fleet_control = True
        with tempfile.TemporaryDirectory() as folder:
            store = PresetStore(Path(folder) / 'presets.json')
            for name in ('Original Game', 'original game', ' Original Game '):
                with self.assertRaises(ValueError):
                    store.save(name, p, replace=True)
                with self.assertRaises(ValueError):
                    store.delete(name)
            self.assertFalse(store.path.exists())
            store.save('My original game edits', p)
            self.assertTrue(store.read()['My original game edits']['fixes']['fleet_control'])
        self.assertEqual(starter(p, 'Original Game').build()[0], p.rom)

    def test_bundled_presets_match_supplied_snapshots_exactly(self):
        from app_defaults import preset_document, provided_names
        from custom_presets import starter, prepare
        document = preset_document()
        self.assertEqual(document['deleted'], ['Hard Mode', 'Naval Challenge'])
        self.assertEqual(set(document['presets']), {'Classic Plus', 'New Discoveries', 'Trade & Exploration', 'Classic Plus + Harder', "Eric's Custom Special"})
        self.assertNotIn('Hard Mode', provided_names())
        self.assertNotIn('Naval Challenge', provided_names())
        p = new_project(self.source)
        before = p.manifest()
        for name, snapshot in document['presets'].items():
            with self.subTest(preset=name):
                candidate = starter(p, name, '9999', True)
                expected = ShipProject(self.source)
                expected.load_manifest(snapshot)
                from custom_presets import lock_manual_controls
                lock_manual_controls(expected)
                self.assertEqual(candidate.manifest(), expected.manifest())
                restored = prepare(p, candidate.manifest())
                rom, _ = restored.build()
                self.assertEqual(apply_ips(restored.rom, ips(restored.rom, rom)), rom)
        self.assertEqual(p.manifest(), before)
        special = starter(p, "Eric's Custom Special")
        self.assertEqual(len(special.ships), 35)
        self.assertEqual(len(special.discovery_entries), 98)
        self.assertFalse(starter(p, 'Classic Plus').discovery_entries)
        for name in ('Hard Mode', 'Naval Challenge'):
            with self.assertRaises(ValueError):
                starter(p, name)

    def test_preset_locks_preserve_values_rom_and_saved_snapshot(self):
        import tempfile
        from custom_presets import (starter, PresetStore, prepare,
                                    lock_manual_controls, MANUAL_EDIT_FLAGS)
        p = new_project(self.source)
        for name in ("Eric's Custom Special", 'Classic Plus + Harder', 'Full Randomizer'):
            with self.subTest(preset=name):
                loaded = starter(p, name, '1234')
                self.assertFalse(any(getattr(loaded, flag) for flag in MANUAL_EDIT_FLAGS))
                for flag in MANUAL_EDIT_FLAGS:
                    setattr(loaded, flag, True)
                before = loaded.manifest()
                rom = loaded.build()[0]
                with tempfile.TemporaryDirectory() as folder:
                    store = PresetStore(Path(folder) / 'presets.json')
                    store.save('My unlocked preset', loaded)
                    candidate = prepare(p, store.read()['My unlocked preset'])
                    lock_manual_controls(candidate)
                    self.assertFalse(any(getattr(candidate, flag) for flag in MANUAL_EDIT_FLAGS))
                    self.assertEqual(candidate.build()[0], rom)
                    self.assertEqual(store.read()['My unlocked preset'], before)
                    self.assertEqual(loaded.manifest(), before)

    def test_full_randomizer_uses_defaults_and_explicit_seed(self):
        from custom_presets import starter
        p = new_project(self.source)
        a = starter(p, 'Full Randomizer', '1234', False)
        b = starter(p, 'Full Randomizer', '1234', False)
        self.assertEqual(a.manifest(), b.manifest())
        self.assertEqual(a.discovery_entries, p.discovery_entries)
        self.assertFalse(a.custom_discoveries)
        self.assertEqual(a.free_agent_shuffle['seed'], '1234')
        self.assertNotEqual(a.manifest(), starter(p, 'Full Randomizer', '5678', False).manifest())


if __name__ == '__main__':
    unittest.main()
