"""Discovery catalogue bounds, native names/coordinates and blank slot handling."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from discoveries import catalogue,BASE,NAME_POINTERS,picture_data,picture
from rom_map import WIDTH,HEIGHT
class DiscoveryTests(unittest.TestCase):
    def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')
    def test_named_pool_and_native_locations(self):
        before=self.p.manifest();rows=catalogue(self.p.rom)
        self.assertEqual(len(rows),98);self.assertEqual([r['id']for r in rows],list(range(98)))
        self.assertEqual((rows[0]['name'],rows[0]['x'],rows[0]['y']),('Stonehenge',168,270))
        self.assertEqual((rows[-1]['name'],rows[-1]['x'],rows[-1]['y']),('Moai',1574,888))
        self.assertTrue(all(0<=r['x']<WIDTH and 0<=r['y']<HEIGHT for r in rows))
        self.assertEqual(self.p.manifest(),before)
    def test_descriptions_categories_difficulty_and_all_art(self):
        rows=catalogue(self.p.rom)
        self.assertIn('Prehistoric monument',rows[0]['description'])
        self.assertEqual(rows[0]['category'],'Ruins')
        self.assertEqual((rows[0]['difficulty'],rows[0]['required_score']),(10,11))
        for row in rows:
            self.assertTrue(row['description']and row['category'])
            self.assertEqual(row['required_score'],row['difficulty']+1)
            raw,palette=picture_data(self.p.rom,row['id'])
            self.assertEqual((len(raw),len(palette)),(512,32))
            self.assertEqual(picture(self.p.rom,row['id'],1).size,(32,32))

    def test_invalid_pointer_or_position_rejected(self):
        bad=bytearray(self.p.rom);bad[NAME_POINTERS:NAME_POINTERS+3]=b'\0'*3
        with self.assertRaises(ValueError):catalogue(bad)
        bad=bytearray(self.p.rom);bad[BASE:BASE+2]=WIDTH.to_bytes(2,'little')
        with self.assertRaises(ValueError):catalogue(bad)
if __name__=='__main__':unittest.main()
