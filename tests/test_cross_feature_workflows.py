"""Moves/restores and edited markets/shuffles must compose without lost settings."""
import copy
import json
import os
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from backend import ShipProject, apply_ips
from content_library import capture_ship, new_id
from library_project import load_ship, restore_stock_ships
from trade_goods import offers, change, shuffle_plan, seeded_shuffle, validate_shuffle


class CrossFeatureTests(unittest.TestCase):
    def setUp(self):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT / 'New Horizons (USA).zip'))
        if not source.exists():
            self.skipTest('Requires verified stock ROM')
        self.p = ShipProject(source)

    def full_shipyard(self, replaced=False):
        p = self.p
        p.custom_ships = True
        if replaced:
            entry = capture_ship(p, 10)
            entry['id'] = new_id()
            load_ship(p, entry, 0, replace_fleet=True)
        port = p.stock_availability[0]['ports'][0]
        p.update(0, dict(ports=[], industry=0))
        for i in range(1, 25):
            if sum(port in o['ports'] for o in p.all_offers()) >= 16:
                break
            if port not in p.original_availability[i]['ports']:
                p.update(i, dict(ports=p.original_availability[i]['ports']+[port], industry=0))
        p.validate_offer_counts()
        return port

    def test_single_restore_rejects_overfull_yard_without_changing_project(self):
        from app import Editor
        self.full_shipyard()
        before = self.p.manifest()
        errors = []
        app = SimpleNamespace(project=self.p, selected=0, root=None,
                              refresh_list=lambda: None, show=lambda *a: None,
                              fail=lambda e: errors.append(str(e)))
        Editor.restore(app)
        self.assertEqual(before, self.p.manifest())
        self.assertTrue(errors and '16-ship' in errors[0])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'valid.json'
            self.p.save_project(path)
            q = ShipProject(self.p.source)
            q.load_project(path)
            self.assertEqual(q.manifest(), before)

    def test_library_restore_rejects_before_archiving(self):
        from content_library import ContentLibrary
        from library_view import LibraryPanel
        self.full_shipyard(replaced=True)
        before = self.p.manifest()
        errors = []
        with tempfile.TemporaryDirectory() as d:
            store = ContentLibrary(self.p.rom, d)
            app = SimpleNamespace(project=self.p, root=None, reload_project_view=lambda: None,
                                  fail=lambda e: errors.append(str(e)))
            panel = SimpleNamespace(app=app, store=store, refresh=lambda: None)
            with patch('tkinter.messagebox.askyesno', return_value=True):
                LibraryPanel.restore_original(panel, 0)
            self.assertEqual(self.p.manifest(), before)
            self.assertEqual(store.entries, [])
            self.assertFalse(store.path.exists())
        self.assertTrue(errors and '16-ship' in errors[0])

    def test_successful_single_restore_preserves_fleet_identity_and_reopens(self):
        from library_project import restore_ship
        self.p.fleet_rules[0][0][0] = 10
        load_ship(self.p, capture_ship(self.p, 10), 13)
        self.assertEqual(self.p.fleet_rules[0][0][0], 13)
        restore_ship(self.p, 13)
        self.assertEqual(self.p.ships[13]['name'], self.p.original[13]['name'])
        self.assertEqual(self.p.ships[self.p.fleet_rules[0][0][0]]['name'], 'Galleon')
        self.p.build()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'restored.json'
            self.p.save_project(path)
            q = ShipProject(self.p.source)
            q.load_project(path)
            self.assertEqual(q.build(), self.p.build())

    def test_restore_archive_failure_keeps_project(self):
        from library_project import restore_ship
        entry = capture_ship(self.p, 10)
        entry['id'] = new_id()
        load_ship(self.p, entry, 0, replace_fleet=True)
        before = self.p.manifest()
        with self.assertRaises(OSError):
            restore_ship(self.p, 0, archive=lambda entry: (_ for _ in ()).throw(OSError('Disk full')))
        self.assertEqual(self.p.manifest(), before)

    def test_add_ship_keeps_template_portrait_and_description(self):
        from library_project import restore_ship
        raw = self.p.portrait_raw(10)
        custom = bytes([raw[0] ^ 1]) + raw[1:]
        self.p.set_portrait(10, custom)
        self.p.ship_descriptions[10] = 'A custom template description.'
        self.p.update(10, dict(hull=99))
        slot = self.p.add_ship(10)
        self.assertEqual(self.p.ships[slot]['hull'], 99)
        self.assertEqual(self.p.portrait_raw(slot), custom)
        self.assertEqual(self.p.ship_descriptions[slot], self.p.ship_descriptions[10])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'art.json'
            self.p.save_project(path)
            q = ShipProject(self.p.source)
            q.load_project(path)
            self.assertEqual(q.portrait_raw(slot), custom)
            self.assertEqual(q.build(), self.p.build())
        restore_ship(self.p, slot)
        self.assertEqual(self.p.portrait_raw(slot), raw)
        self.assertEqual(self.p.portrait_raw(10), custom)

    def test_save_refuses_unloadable_project_without_touching_previous_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'project.json'
            self.p.save_project(path)
            previous = path.read_bytes()
            for offer in self.p.original_availability[:17]:
                offer['ports'] = [0]
                offer['industry'] = 0
            with self.assertRaises(ValueError):
                self.p.save_project(path)
            self.assertEqual(path.read_bytes(), previous)
            self.assertFalse(path.with_suffix('.json.bak').exists())
            new_path = Path(d)/'invalid.json'
            with self.assertRaises(ValueError):
                self.p.save_project(new_path)
            self.assertFalse(new_path.exists())
            self.assertEqual(self.p.project_path, path.resolve())

    def edited_market(self):
        rows = offers(self.p.rom, [])
        specialty = next(o for o in rows[0] if o['kind'] == 'Specialty')
        self.p.goods_edits = change(self.p.rom, [], 0, specialty['good'], gate=1000)
        regional = next(o for o in rows[0] if o['kind'] == 'Regional')
        self.p.goods_edits = change(self.p.rom, self.p.goods_edits, 0, regional['good'], gate=900)
        # A non-stock slot count must also survive all shuffle modes.
        regional = [o for o in rows[0] if o['kind'] == 'Regional'][1]
        self.p.goods_edits = change(self.p.rom, self.p.goods_edits, 0, regional['good'], remove=True)

    def test_ship_section_restore_follows_moved_stock_identity(self):
        from app import Editor
        self.p.fleet_rules[0][0][0] = 10
        self.p.fleet_rules[0][1][0] = 13
        load_ship(self.p, capture_ship(self.p, 10), 13)
        self.assertEqual(self.p.fleet_rules[0][0][0], 13)
        app = SimpleNamespace(project=self.p, root=None, cancel_auto_edit=lambda: None,
                              auto_edit=lambda: None, reload_project_view=lambda: None)
        with patch('tkinter.messagebox.askyesno', return_value=True):
            Editor.reset_section(app, 'ships')
        self.assertEqual(self.p.ships[self.p.fleet_rules[0][0][0]]['name'], 'Galleon')
        self.assertEqual(self.p.ships[self.p.fleet_rules[0][1][0]]['name'], 'Sloop')
        self.p.build()

    def test_restore_clears_custom_targets_even_in_original_slots(self):
        entry = capture_ship(self.p, 10)
        entry['id'] = new_id()
        load_ship(self.p, entry, 10, replace_fleet=True)
        self.p.fleet_rules[0][0][0] = 10
        added = self.p.add_ship()
        self.p.fleet_rules[0][1][0] = added
        restore_stock_ships(self.p)
        self.assertEqual(self.p.fleet_rules[0][0][0], -1)
        self.assertEqual(self.p.fleet_rules[0][1][0], -1)
        self.assertEqual(len(self.p.ships), 25)

    def test_stock_identity_in_added_slot_survives_restore(self):
        added = self.p.add_ship()
        self.p.fleet_rules[0][0][0] = 10
        load_ship(self.p, capture_ship(self.p, 10), added)
        self.assertEqual(self.p.fleet_rules[0][0][0], added)
        restore_stock_ships(self.p)
        self.assertEqual(self.p.fleet_rules[0][0][0], 10)

    def test_ship_restore_keeps_other_sections_and_is_repeatable(self):
        self.p.update_character(0, dict(battle_level=80))
        self.edited_market()
        before = copy.deepcopy((self.p.character_edits, self.p.goods_edits))
        restore_stock_ships(self.p)
        first = self.p.manifest()
        restore_stock_ships(self.p)
        self.assertEqual(first, self.p.manifest())
        self.assertEqual(before, (self.p.character_edits, self.p.goods_edits))

    def test_stock_goods_seeds_keep_previous_results(self):
        for mode in ('normal', 'specialty', 'all'):
            for blind in (False, True):
                self.assertEqual(shuffle_plan(self.p, '2026', mode, blind)['goods_edits'],
                                 seeded_shuffle(self.p.rom, '2026', mode, blind))

    def test_custom_gates_counts_and_outside_scope_survive(self):
        for mode in ('normal', 'specialty', 'all'):
            self.p = ShipProject(self.p.source)
            self.edited_market()
            before = offers(self.p.rom, self.p.goods_edits)
            self.p.set_goods_shuffle('1234', mode)
            after = offers(self.p.rom, self.p.goods_edits)
            for a, b in zip(before, after):
                self.assertEqual([(o['kind'], o['economy_required']) for o in a],
                                 [(o['kind'], o['economy_required']) for o in b])
                self.assertEqual(len(b), len({o['good'] for o in b}))
                if mode != 'all':
                    kept = 'Specialty' if mode == 'normal' else 'Regional'
                    self.assertEqual([o for o in a if o['kind'] == kept], [o for o in b if o['kind'] == kept])
            for kind in ('Regional', 'Specialty'):
                self.assertEqual(Counter((o['good'], o['price']) for row in before for o in row if o['kind'] == kind),
                                 Counter((o['good'], o['price']) for row in after for o in row if o['kind'] == kind))

    def test_preview_preset_and_application_use_identical_plan(self):
        from easy_presets import _goods
        self.edited_market()
        original = self.p.manifest()
        candidate = shuffle_plan(self.p, '1234', 'normal')
        self.assertEqual(candidate, _goods(self.p, '1234', False, 'normal'))
        self.assertEqual(original, self.p.manifest())
        self.p.set_goods_shuffle('1234', 'normal')
        self.assertEqual(candidate['goods_edits'], self.p.goods_edits)
        self.assertEqual(candidate['goods_shuffle'], self.p.goods_shuffle)

    def test_repeat_new_seed_and_portable_baseline(self):
        self.edited_market()
        self.p.set_goods_shuffle('1234', 'normal')
        first = self.p.manifest()
        self.p.set_goods_shuffle('1234', 'normal')
        self.assertEqual(first, self.p.manifest())
        self.p.set_goods_shuffle('5678', 'normal')
        self.p.set_goods_shuffle('1234', 'normal')
        self.assertEqual(first, self.p.manifest())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'project.json'
            self.p.save_project(path)
            q = ShipProject(self.p.source)
            q.load_project(path)
            q.set_goods_shuffle('1234', 'normal')
            self.assertEqual(first, q.manifest())
            q.export(Path(tmp) / 'goods.sfc')
            self.assertEqual(apply_ips(q.rom, (Path(tmp) / 'goods.ips').read_bytes()), q.build()[0])

    def test_economy_preset_after_shuffle_is_not_lost_on_reshuffle(self):
        from easy_presets import apply
        self.p.set_goods_shuffle('1234', 'normal')
        apply(self.p, 'Trade Opportunities')
        before = offers(self.p.rom, self.p.goods_edits)
        self.p.set_goods_shuffle('5678', 'normal')
        after = offers(self.p.rom, self.p.goods_edits)
        for a, b in zip(before, after):
            self.assertEqual([(o['kind'], o['economy_required']) for o in a],
                             [(o['kind'], o['economy_required']) for o in b])

    def test_blind_outside_scope_stays_hidden_and_portable(self):
        self.p.set_goods_shuffle('9876', 'specialty', True)
        specialty = [[o for o in row if o['kind'] == 'Specialty'] for row in offers(self.p.rom, self.p.goods_edits)]
        candidate = shuffle_plan(self.p, '1234', 'normal', False)
        self.assertTrue(candidate['goods_shuffle']['blind'])
        self.assertTrue(candidate['goods_shuffle']['retained_blind'])
        self.p.set_goods_shuffle('1234', 'normal', False)
        self.assertEqual(specialty, [[o for o in row if o['kind'] == 'Specialty'] for row in offers(self.p.rom, self.p.goods_edits)])
        before = self.p.manifest()
        self.p.set_goods_shuffle('1234', 'normal', False)
        self.assertEqual(before, self.p.manifest())
        with tempfile.TemporaryDirectory() as tmp:
            self.p.export(Path(tmp) / 'blind.sfc')
            report = json.loads((Path(tmp) / 'blind.changes.json').read_text(encoding='utf-8'))
            self.assertEqual(report['goods_edits'], [])
            self.assertNotIn('previous', report['goods_shuffle'])

    def test_invalid_baseline_is_rejected(self):
        for previous in (None, {}, [dict(port=0, offers=[dict(good=0)])]):
            with self.assertRaises(ValueError):
                validate_shuffle(dict(seed='1234', mode='all', previous=previous))


if __name__ == '__main__':
    unittest.main()
