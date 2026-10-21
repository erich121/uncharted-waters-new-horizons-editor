"""The approved catalogue survives presets, migration and user customizations."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mod_tool'))
from app_defaults import library_document, previous_library_document, preset_document
from backend import ShipProject
from content_library import ContentLibrary, new_id


class CuratedDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / 'New Horizons (USA).zip'
        if not cls.source.is_file():
            raise unittest.SkipTest('Requires verified stock USA ROM')
        cls.stock = ShipProject(cls.source)

    def test_preset_hulls_and_names_match_approved_catalogue(self):
        lib = library_document(self.source)
        ships = {e['id']:e for e in lib['entries'] if e['kind']=='ship'}
        self.assertEqual(sum(not i.startswith('stock-') for i in ships), 35)
        self.assertEqual(set(lib['collections']), {'Stock Ships', 'Stock Discoveries'})
        for name, snapshot in preset_document()['presets'].items():
            project = ShipProject(self.source)
            project.load_manifest(snapshot)
            for slot, ship in enumerate(project.ships[25:], 25):
                entry = ships[project.ship_identities[slot]]
                self.assertEqual(ship['name'], entry['ship']['name'], name)
                self.assertLessEqual(len(ship['name']), 13)
            project.build()
        special = preset_document()['presets']["Eric's Custom Special"]
        selected = [s['name'] for s in special['added_ships']]
        self.assertIn('Fluyt', selected)
        self.assertIn('Great Harry', selected)
        self.assertNotIn('Spanish Galeon', selected)
        self.assertNotIn('Dutch Fluyt', selected)

    def test_previous_shipped_catalogue_replaced_and_backed_up(self):
        with tempfile.TemporaryDirectory() as folder:
            lib = ContentLibrary(self.stock.rom, folder)
            previous = previous_library_document()
            lib.entries, lib.collections = copy.deepcopy((previous['entries'],previous['collections']))
            lib.save()
            before = lib.path.read_bytes()
            (lib.root/'.bundled-content-version').write_text('5')
            self.assertTrue(lib.migrate_bundled_defaults(self.source))
            approved = library_document(self.source)
            self.assertEqual({e['id']:e for e in lib.entries}, {e['id']:e for e in approved['entries']})
            self.assertEqual(lib.collections, approved['collections'])
            self.assertEqual(lib.path.with_suffix('.json.bak').read_bytes(), before)
            self.assertFalse(lib.migrate_bundled_defaults(self.source))

    def test_balanced_fleets_are_effective_and_flagships_stronger(self):
        from fleet_difficulty import SOURCES, resolve
        from backend import ports
        project = ShipProject(self.source)
        project.load_manifest(preset_document()['presets']["Eric's Custom Special"])
        sovereign = next(s['id'] for s in project.ships if s['name']=='Sovereign')
        for nation in project.fleet_rules:
            for j,source in enumerate(SOURCES):
                flagship = project.ships[nation[0][j] if nation[0][j]>=0 else source]
                for role in nation:
                    target = role[j]
                    if target>=0:
                        self.assertIsNotNone(resolve(project.ships,source,target)[0])
                        self.assertNotEqual(target,sovereign)
                    escort = project.ships[target if target>=0 else source]
                    self.assertTrue(all(flagship[k]>=escort[k] for k in ('hull','factory_guns','factory_crew')))
        for port in ports(project.rom):
            count = sum(port['id'] in s['ports'] for s in project.ships[25:])
            self.assertLessEqual(count,3 if port['capital'] else 2)
        harry = next(s for s in project.ships if s['name']=='Great Harry')
        self.assertEqual((harry['factory_guns'],harry['factory_crew']),(80,300))

    def test_trading_price_curve_and_capacity_allocations(self):
        project = ShipProject(self.source)
        project.load_manifest(preset_document()['presets']["Eric's Custom Special"])
        by_name = {s['name']:s for s in project.ships}
        ratios = [by_name[n]['price_gold']/by_name[n]['factory_cargo']
                  for n in ('Fluyt','Galeao de Goa','Great Madre','Manila Nau','Sovereign')]
        self.assertEqual(ratios,sorted(ratios))
        for s in project.ships:
            self.assertEqual(s['capacity'],s['factory_guns']+s['factory_crew']+s['factory_cargo'])
        project.build()

    def test_custom_preset_has_very_hard_campaign_settings(self):
        from sailors import CAPTAIN_IDS,decode_sailors
        project = ShipProject(self.source)
        project.load_manifest(preset_document()['presets']["Eric's Custom Special"])
        records = {r['id']:r for r in decode_sailors(project.rom)}
        for edit in project.effective_character_edits():
            records[edit['id']][edit['field']] = edit['value']
        for i in CAPTAIN_IDS:
            if records[i]['nationality']=='Pirate':continue
            for key,floor in dict(leadership=85,seamanship=80,intuition=80,courage=85,swordsmanship=85).items():
                self.assertGreaterEqual(records[i][key],floor)
            self.assertTrue(records[i]['skills']&4)
        self.assertFalse(project.instant_shipbuilding)
        self.assertIsNone(project.starting_gold)
        heavy = {s['name']:s for s in project.ships}
        self.assertEqual(heavy['Full-rigged Ship']['factory_guns'],150)
        self.assertEqual(heavy['Barge']['factory_crew'],450)

    def test_user_edits_and_favorite_removed_ship_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            lib = ContentLibrary(self.stock.rom, folder)
            previous = previous_library_document()
            lib.entries, lib.collections = copy.deepcopy((previous['entries'],previous['collections']))
            edited = next(e for e in lib.entries if e.get('ship',{}).get('name')=='Caravela Armada')
            edited['ship']['hull'] += 1
            favorite = next(e for e in lib.entries if e.get('ship',{}).get('name')=='Spanish Galeon')
            lib.collections['Favorites'] = [favorite['id'], edited['id']]
            lib.save()
            self.assertTrue(lib.migrate_bundled_defaults(self.source))
            self.assertIn(edited,lib.entries)
            self.assertIn(favorite,lib.entries)
            self.assertEqual(lib.collections['Favorites'],[favorite['id'],edited['id']])
            for name in ('Botafogo','Fluyt','Great Harry'):
                self.assertTrue(any(e.get('ship',{}).get('name')==name for e in lib.entries))


if __name__ == '__main__':
    unittest.main()
