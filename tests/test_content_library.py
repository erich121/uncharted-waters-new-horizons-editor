"""Ship Library portability, hostile input, native table composition and identity swaps."""
from legacy_manifest import legacy_manifest
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from backend import ShipProject, decode, apply_ips
from content_library import ContentLibrary, capture_ship, new_id, stock_id
from library_project import load_ship


class LibraryTests(unittest.TestCase):
    def setUp(self):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not source.exists():
            self.skipTest('Requires the verified stock ROM.')
        self.p = ShipProject(source)

    def custom(self, family=10):
        entry = capture_ship(self.p, family)
        entry['id'] = new_id()
        entry['ship']['name'] = 'Royal Trader'
        return entry

    def test_stock_is_read_only_and_project_edit_saves_separate_variant(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, d)
            stock = capture_ship(self.p, 10)
            lib.put(stock)
            altered = copy.deepcopy(stock)
            altered['ship']['power'] -= 1
            with self.assertRaisesRegex(ValueError, 'read-only'):
                lib.put(altered)
            load_ship(self.p, stock, 10)
            self.p.update(10, dict(name='My Galleon', power=self.p.ships[10]['power']-1))
            variant = capture_ship(self.p, 10)
            self.assertFalse(variant['id'].startswith('stock-'))
            lib.put(variant)
            self.assertEqual(next(e for e in lib.entries if e['id']==stock['id']), stock)
            self.assertEqual(len(lib.entries), 2)

    def test_import_cannot_overwrite_stock_entry_or_collection(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, Path(d)/'lib')
            stock = capture_ship(self.p, 10)
            lib.put(stock);lib.collections={'Stock Game':[stock['id']]};lib.save()
            before = copy.deepcopy(lib.document())
            data = copy.deepcopy(before);data['entries'][0]['ship']['power']-=1
            path=Path(d)/'bad.nhlib';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'read-only'):
                lib.import_file(path,replace=True)
            data=copy.deepcopy(before);data['collections']['Stock Game']=[]
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'read-only'):
                lib.import_file(path,replace=True)
            self.assertEqual(lib.document(),before)

    def test_clear_library_preserves_project_and_keeps_recovery_backup(self):
        with tempfile.TemporaryDirectory()as d:
            lib=ContentLibrary(self.p.rom,d);entry=self.custom();lib.put(entry)
            lib.collections={'Saved ships':[entry['id']]};lib.save()
            before=self.p.manifest();document=copy.deepcopy(lib.document())
            lib.clear();reopened=ContentLibrary(self.p.rom,d)
            self.assertEqual((reopened.entries,reopened.collections),([],{ }))
            self.assertEqual(json.loads(lib.path.with_suffix('.json.bak').read_text(encoding='utf-8')),document)
            self.assertEqual(self.p.manifest(),before)

    def test_clear_write_failure_rolls_back(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory()as d:
            lib=ContentLibrary(self.p.rom,d);lib.put(self.custom());before=copy.deepcopy(lib.document());data=lib.path.read_bytes()
            with patch('content_library.os.replace',side_effect=OSError('write failure')):
                with self.assertRaises(OSError):lib.clear()
            self.assertEqual(lib.document(),before);self.assertEqual(lib.path.read_bytes(),data)

    def test_capture_keeps_current_specs_instead_of_stock(self):
        self.p.update(3,dict(name='Saved Buss',hull=55,power=66,turning=77,max_guns=40,min_crew=30,max_crew=200,capacity=800,price_gold=90000))
        entry=capture_ship(self.p,3)
        for key,value in entry['ship'].items():self.assertEqual(value,self.p.ships[3][key])
        with tempfile.TemporaryDirectory()as d:
            lib=ContentLibrary(self.p.rom,d);lib.put(entry)
            self.p.update(3,dict(hull=80,power=90,price_gold=100000))
            stored=ContentLibrary(self.p.rom,d).entries[0]
            self.assertEqual(stored['ship'],entry['ship'])
            self.assertEqual(stored['availability'],entry['availability'])

    def test_empty_managed_storage_and_all_stock_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, d)
            self.assertEqual(lib.entries, [])
            for i in range(25):
                lib.put(capture_ship(self.p, i))
            self.assertEqual(len(ContentLibrary(self.p.rom, d).entries), 25)
            self.assertTrue(lib.path.with_suffix('.json.bak').exists())

    def test_project_portable_without_library_and_explicit_update(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, Path(d) / 'lib')
            entry = self.custom()
            lib.put(entry)
            load_ship(self.p, entry, 13)
            before = self.p.build()[0]
            self.p.save_project(Path(d) / 'project.json')
            entry['ship']['name'] = 'Updated Trader'
            lib.put(entry)
            q = ShipProject(self.p.source)
            q.load_project(Path(d) / 'project.json')
            self.assertEqual(q.ships[13]['name'], 'Royal Trader')
            self.assertEqual(q.build()[0], before)
            self.assertEqual(q.manifest(), self.p.manifest())
            load_ship(q, entry, 13)
            self.assertEqual(q.ships[13]['name'], 'Updated Trader')

    def test_fleets_follow_identity_and_missing_replacement_is_atomic(self):
        entry = self.custom()
        slot = load_ship(self.p, entry)
        self.p.fleet_rules[0][0][1] = slot
        load_ship(self.p, entry, 3)
        self.assertEqual(self.p.ship_identities[3], entry['id'])
        self.assertEqual(self.p.ship_identities[slot], stock_id(3))
        self.assertEqual(self.p.fleet_rules[0][0][1], 3)
        other = self.custom(5)
        before = self.p.manifest()
        with self.assertRaisesRegex(ValueError, 'Custom Fleet'):
            load_ship(self.p, other, 3)
        self.assertEqual(self.p.manifest(), before)
        load_ship(self.p, other, 3, replace_fleet=True)
        self.assertEqual(self.p.fleet_rules[0][0][1], 3)

    def test_stock_swap_and_native_tables_with_and_without_additions(self):
        for added in (False, True):
            with self.subTest(added=added):
                p = ShipProject(self.p.source)
                if added:
                    p.add_ship(6)
                entry = capture_ship(p, 10)
                p.fleet_rules[0][0][1] = 10
                load_ship(p, entry, 13)
                self.assertEqual(p.ship_identities[10], stock_id(13))
                self.assertEqual(p.fleet_rules[0][0][1], 13)
                rom, _ = p.build()
                self.assertEqual(decode(rom)[13]['name'], 'Galleon')
                self.assertEqual(decode(rom)[10]['name'], 'Sloop')
                for slot, family in [(13, 10), (10, 13)]:
                    table = 0x213400 if added else 0x2B6C9
                    self.assertEqual(rom[table+slot], p.rom[0x2B6C9+family])
                    self.assertEqual(rom[0x8cbb6+slot*25+20:0x8cbb6+slot*25+25], p.rom[0x8cbb6+family*25+20:0x8cbb6+family*25+25])
                self.assertEqual(sum(rom) & 65535, int.from_bytes(rom[0xffde:0xffe0], 'little'))

    def test_share_and_collections_conflict_safe(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, Path(d)/'a')
            e = self.custom()
            lib.put(e)
            lib.collections['Traders'] = [e['id']]
            lib.save()
            path = Path(d)/'ships.nhlib'
            lib.export_file(path)
            other = ContentLibrary(self.p.rom, Path(d)/'b')
            other.import_file(path)
            self.assertEqual(other.document(), lib.document())
            changed = copy.deepcopy(e)
            changed['ship']['name'] = 'Changed Trader'
            other.put(changed)
            before = other.path.read_bytes()
            with self.assertRaises(ValueError):
                other.import_file(path)
            self.assertEqual(other.path.read_bytes(), before)
            other.import_file(path, replace=True)
            self.assertEqual(other.document(), lib.document())

    def test_invalid_import_preserves_disk_and_project(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, Path(d)/'lib')
            e = self.custom()
            lib.put(e)
            before = lib.path.read_bytes()
            for field, value in [('id', '../escape'), ('portrait', 'not tiles'), ('family', 25)]:
                bad = copy.deepcopy(e)
                bad[field] = value
                path = Path(d)/'bad.nhlib'
                path.write_text(json.dumps(dict(lib.document(), entries=[bad])), encoding='utf-8')
                with self.assertRaises(ValueError):
                    lib.import_file(path, replace=True)
                self.assertEqual(lib.path.read_bytes(), before)
            invalid = copy.deepcopy(e)
            invalid['ship']['capacity'] = 1
            snapshot = self.p.manifest()
            with self.assertRaises(ValueError):
                load_ship(self.p, invalid, 13)
            self.assertEqual(self.p.manifest(), snapshot)

    def test_capacity_guard_and_ips_roundtrip(self):
        for _ in range(10):
            self.p.add_ship()
        before = self.p.manifest()
        with self.assertRaises(ValueError):
            load_ship(self.p, self.custom())
        self.assertEqual(self.p.manifest(), before)
        load_ship(self.p, self.custom(), 13)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'Library.sfc'
            self.p.export(path)
            self.assertEqual(apply_ips(self.p.rom, path.with_suffix('.ips').read_bytes()), path.read_bytes())

    def test_edited_original_library_ship_keeps_original_snapshot_identity(self):
        entry = capture_ship(self.p, 10)
        load_ship(self.p, entry, 13)
        self.p.update(13, dict(name='New Galleon'))
        variant = capture_ship(self.p, 13)
        self.assertNotEqual(variant['id'], entry['id'])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'modified-original.json'
            self.p.save_project(path)
            q = ShipProject(self.p.source)
            q.load_project(path)
            self.assertEqual(q.build(), self.p.build())

    def test_old_v19_project_migrates(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.p.manifest()
            m.pop('library_state');m.pop('ship_descriptions');m.pop('custom_characters',None)
            for field in ('custom_discoveries','discovery_rewrites','fifty_year_campaign','starting_gold','instant_shipbuilding'):
                m.pop(field, None)
            m['version']=19
            path = Path(d)/'old.json'
            path.write_text(json.dumps(legacy_manifest(m)), encoding='utf-8')
            self.p.load_project(path)
            self.assertEqual(self.p.build()[0], self.p.rom)
        self.assertEqual(self.p.manifest()['version'], 30)

    def test_build_locations_and_industry_share_and_portable_project(self):
        self.p.update(0, dict(ports=[3], industry=600))
        entry = capture_ship(self.p, 0)
        self.assertEqual(entry['availability'], dict(ports=[3], industry=600))
        self.assertEqual(entry['ship']['industry'], 600)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, Path(d)/'a')
            lib.put(entry)
            path = Path(d)/'ship.nhlib';lib.export_file(path)
            imported = ContentLibrary(self.p.rom, Path(d)/'b');imported.import_file(path)
            self.assertEqual(imported.entries[0], entry)
            q = ShipProject(self.p.source)
            load_ship(q, imported.entries[0], 0, use_locations=True)
            self.assertEqual(q.all_offers()[0], entry['availability'])
            path = Path(d)/'project.json';q.save_project(path)
            r = ShipProject(self.p.source);r.load_project(path)
            self.assertEqual(r.all_offers(), q.all_offers())
            self.assertEqual(r.build(), q.build())
            r.update(0,dict(hull=40,ports=[4],industry=500))
            self.assertEqual(capture_ship(r,0)['availability'],dict(ports=[4],industry=500))
            rom = q.build()[0]
            from availability import PORTS, INDUSTRY
            self.assertEqual(rom[PORTS+3*25], 1)
            self.assertEqual(rom[PORTS], 0)
            self.assertEqual(int.from_bytes(rom[INDUSTRY:INDUSTRY+2], 'little'), 600)

    def test_added_ship_and_keep_project_assignments(self):
        entry = self.custom()
        entry['availability'] = dict(ports=[3], industry=600)
        entry['ship']['industry'] = 600
        old = self.p.all_offers()[13]
        load_ship(self.p, entry, 13, use_locations=False)
        self.assertEqual(self.p.all_offers()[13], old)
        entry['id'] = new_id()
        slot = load_ship(self.p, entry, use_locations=True)
        self.assertEqual(self.p.all_offers()[slot], entry['availability'])
        self.p.build()

    def test_legacy_entries_keep_locations(self):
        entry = self.custom();entry['version']=1;entry.pop('availability');entry.pop('description')
        old = self.p.all_offers()[13]
        load_ship(self.p, entry, 13, use_locations=True)
        self.assertEqual(self.p.all_offers()[13], old)
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, d);lib.put(entry)
            self.assertEqual(ContentLibrary(self.p.rom, d).entries[0], entry)

    def test_location_swap_moves_both_and_clears_shuffle(self):
        self.p.update(0, dict(ports=[3], industry=600))
        self.p.update(1, dict(ports=[4], industry=500))
        entry = capture_ship(self.p, 0)
        old = self.p.all_offers()[1]
        load_ship(self.p, entry, 1, use_locations=True)
        self.assertEqual(self.p.all_offers()[1], entry['availability'])
        self.assertEqual(self.p.all_offers()[0], old)
        self.p.build()

    def test_bad_locations_and_unreachable_capital_are_atomic(self):
        from content_library import validate_ship
        for offer in (dict(ports=[100],industry=600),dict(ports=[3,3],industry=600),dict(ports=[True],industry=600),dict(ports=[3],industry=601)):
            entry = self.custom();entry['availability'] = offer;entry['ship']['industry'] = offer['industry']
            with self.assertRaises(ValueError):validate_ship(entry,self.p.rom)
        entry = self.custom();entry['availability'] = dict(ports=[0],industry=1000);entry['ship']['industry'] = 1000
        before = self.p.manifest()
        with self.assertRaisesRegex(ValueError,'cannot reach'):load_ship(self.p,entry,13,use_locations=True)
        self.assertEqual(self.p.manifest(),before)


if __name__ == '__main__':
    unittest.main()
