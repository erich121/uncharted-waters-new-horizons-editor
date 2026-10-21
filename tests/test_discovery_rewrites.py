"""Text-only discovery option, portable snapshots and custom-content precedence."""
from legacy_manifest import legacy_manifest
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import ShipProject, apply_ips, ips
import discovery_content as content
import discovery_rewrites as rewrites
from discoveries import BASE, NAME_POINTERS, catalogue


class DiscoveryRewriteTests(unittest.TestCase):
    def setUp(self):
        path = Path(os.environ.get('NH_STOCK_ROM', Path(__file__).resolve().parents[1] / 'New Horizons (USA).zip'))
        if not path.exists():
            self.skipTest('Requires stock USA ROM')
        self.p = ShipProject(path)

    def test_all_text_only_and_exact_restore(self):
        p = self.p
        self.assertEqual(p.build()[0], p.rom)
        p.discovery_rewrites = True
        result = p.build()[0]
        original, updated = catalogue(p.rom), catalogue(result)
        self.assertEqual(len(rewrites.DESCRIPTIONS), 98)
        for slot, (before, after) in enumerate(zip(original, updated)):
            self.assertNotEqual(before['description'], after['description'])
            self.assertEqual(after['description'], rewrites.DESCRIPTIONS[slot])
            self.assertLessEqual(len(after['description']), 226)
            self.assertEqual({k: v for k, v in before.items() if k != 'description'},
                             {k: v for k, v in after.items() if k != 'description'})
        self.assertEqual(result[BASE:BASE+99*7], p.rom[BASE:BASE+99*7])
        self.assertEqual(result[NAME_POINTERS:NAME_POINTERS+99*3], p.rom[NAME_POINTERS:NAME_POINTERS+99*3])
        # Text-only patch must not touch any original code or art.
        changed = {i for i, (a, b) in enumerate(zip(p.rom, result)) if a != b}
        allowed = set(range(0xebe62, 0xebe62+98*3)) | set(range(0xffdc, 0xffe0)) | {0xffd7}
        self.assertLessEqual(changed, allowed)
        self.assertEqual(apply_ips(p.rom, ips(p.rom, result)), result)
        self.assertEqual(p.discovery_entries, {})
        p.discovery_rewrites = False
        self.assertEqual(p.build()[0], p.rom)

    def test_projects_presets_and_legacy_default(self):
        p = self.p
        p.discovery_rewrites = True
        from custom_presets import prepare, summary, apply_snapshot
        q = prepare(p, p.manifest())
        self.assertTrue(q.discovery_rewrites)
        self.assertEqual(q.build(), p.build())
        p.discovery_rewrites = False
        self.assertIn('Rewritten discovery descriptions: Off → On', summary(p, q))
        apply_snapshot(p, q)
        self.assertTrue(p.discovery_rewrites)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'project.json'
            p.save_project(path)
            q = ShipProject(p.source)
            q.load_project(path)
            self.assertTrue(q.discovery_rewrites)
        old = p.manifest()
        old.pop('custom_discoveries'); old['version']=24
        old.pop('fifty_year_campaign')
        old.pop('starting_gold')
        old.pop('instant_shipbuilding')
        old.pop('discovery_rewrites')
        q.load_manifest(legacy_manifest(old))
        self.assertFalse(q.discovery_rewrites)
        for value in (None, 1, 'true', []):
            bad = p.manifest()
            bad['discovery_rewrites'] = value
            with self.assertRaises(ValueError):
                q.load_manifest(bad)

    def test_custom_discoveries_remain_independent(self):
        p = self.p
        entry = content.capture(p, 0)
        entry['description'] = 'My custom stone circle.'
        content.load(p, entry, 0)
        snapshot = copy.deepcopy(p.discovery_entries)
        p.discovery_rewrites = True
        result = p.build()[0]
        self.assertEqual(catalogue(result)[0]['description'], entry['description'])
        self.assertEqual(content.rows(p)[0]['description'], entry['description'])
        self.assertEqual(content.rows(p)[1]['description'], rewrites.DESCRIPTIONS[1])
        self.assertEqual(p.discovery_entries, snapshot)
        p.discovery_rewrites = False
        self.assertEqual(catalogue(p.build()[0])[0]['description'], entry['description'])

    def test_ai_and_explicit_library_capture(self):
        p = self.p
        import ai_presets
        import json
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            guide = json.loads(ai_presets.export(p))
            guide['gameplay'] = {'discovery_rewrites': True}
            _, _, candidate = ai_presets.candidate(p, json.dumps(guide))
            self.assertTrue(candidate.discovery_rewrites)
            self.assertFalse(p.discovery_rewrites)
            self.assertEqual(candidate.discovery_entries, {})
            self.assertEqual(content.capture(candidate, 0)['description'], rewrites.DESCRIPTIONS[0])

    def test_composition_with_ships_and_ship_text(self):
        p = self.p
        for i in range(10):
            p.add_ship(10)
        p.discovery_rewrites = True
        import ship_descriptions
        ship_descriptions.set_text(p, 25, 'An ocean-going trader.')
        result = p.build()[0]
        self.assertEqual(catalogue(result)[0]['description'], rewrites.DESCRIPTIONS[0])
        self.assertEqual(result[ship_descriptions.TEXT+25*256:ship_descriptions.TEXT+25*256+22], b'An ocean-going trader.')


if __name__ == '__main__':
    unittest.main()
