"""Stock protagonist profiles stay independent of character-editing features."""
import os
import unittest
from pathlib import Path
from backend import ShipProject
from protagonist_view import characters
from sailors import ATTRIBUTES

class ProtagonistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get('NH_STOCK_ROM', str(Path(__file__).resolve().parents[1]/'New Horizons (USA).zip')))
        if not path.exists(): raise unittest.SkipTest('Supply the stock USA ROM.')
        cls.project = ShipProject(path)

    def test_six_profiles_and_starting_values(self):
        rows = characters(self.project.rom)
        self.assertEqual([r['id'] for r in rows], list(range(6)))
        self.assertEqual([r['name'] for r in rows], ['Joao Franco','Catalina Erantzo','Otto Baynes','Ernst Von Bohr','Pietro Conti','Ali Vezas'])
        self.assertEqual([r['navigation_level'] for r in rows], [1,8,10,11,4,1])
        self.assertEqual([r['battle_level'] for r in rows], [1,10,12,1,1,1])
        self.assertEqual([rows[0][k] for k in ATTRIBUTES], [78,75,73,85,82,82,89,50])
        self.assertTrue(all(r['description'] and r['role']=='Protagonist' for r in rows))

    def test_profiles_are_detached_and_do_not_modify_project(self):
        before = self.project.manifest()
        rows = characters(self.project.rom)
        rows[0]['leadership'] = 1
        self.assertEqual(characters(self.project.rom)[0]['leadership'],78)
        self.assertEqual(self.project.manifest(),before)
        self.assertEqual(self.project.build(),(self.project.rom,[]))
