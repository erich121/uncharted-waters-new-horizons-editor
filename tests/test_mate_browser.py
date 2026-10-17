"""Stock-backed checks for sailor roles and independently known starting values."""
import os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject
from sailors import mates,decode_sailors,fleet_captains

class MateBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():raise unittest.SkipTest('Supply the stock ROM.')
        cls.project=ShipProject(path)

    def test_roles_and_captain_exception(self):
        rows=decode_sailors(self.project.rom);browser=mates(self.project.rom)
        self.assertEqual(len(rows),120);self.assertEqual(len(browser),50)
        self.assertEqual(sum(r['role']=='Story companion'for r in browser),10)
        self.assertEqual(sum(r['role']=='Free agent'for r in browser),40)
        self.assertEqual(rows[114]['name'],'Hamid Lal')
        self.assertEqual(rows[114]['role'],'Fleet captain')
        self.assertNotIn(114,[r['id']for r in browser])
        self.assertFalse(any(r['id']<69 for r in browser))

    def test_known_companion_values(self):
        row=next(r for r in mates(self.project.rom)if r['name']=='Rocco Alemkel')
        self.assertEqual([row[k]for k in ('leadership','seamanship','knowledge','intuition',
            'courage','swordsmanship','charm','luck')],[75,82,84,90,93,92,70,70])
        self.assertEqual((row['navigation_level'],row['battle_level'],row['age']),(30,32,65))
        self.assertIsNone(row['starting_port'])

    def test_fleet_captains_partition_and_known_values(self):
        captains=fleet_captains(self.project.rom)
        self.assertEqual(len(captains),64)
        ids={r['id']for r in captains};mate_ids={r['id']for r in mates(self.project.rom)}
        self.assertFalse(ids & mate_ids)
        self.assertEqual(ids|mate_ids,set(range(6,120)))
        self.assertIn(114,ids)
        victor=next(r for r in captains if r['name']=='Victor Russell')
        self.assertEqual(victor['id'],38)
        self.assertEqual((victor['navigation_level'],victor['battle_level']),(16,13))
        self.assertTrue(all(r['starting_port']is None for r in captains))

    def test_known_free_agent_ports_and_levels(self):
        rows={r['name']:r for r in mates(self.project.rom)}
        self.assertEqual(rows['Pilly Reis']['starting_port_name'],'Istanbul')
        self.assertEqual((rows['Pilly Reis']['navigation_level'],rows['Pilly Reis']['battle_level']),(60,50))
        self.assertEqual(rows['Miguel Solis']['starting_port_name'],'Lisbon')
        self.assertEqual(rows['Henry Mancine']['starting_port_name'],'Mombasa')
        self.assertEqual(rows['Jack Diffson']['starting_port_name'],'Nagasaki')

    def test_browsing_does_not_patch_game(self):
        self.project.repair_safeguard=False
        before=self.project.manifest()
        mates(self.project.rom);fleet_captains(self.project.rom);decode_sailors(self.project.rom)
        self.assertEqual(self.project.manifest(),before)
        self.assertEqual(self.project.build(),(self.project.rom,[]))

    def test_nationality_is_stock_allegiance_not_current_fleet(self):
        rows=decode_sailors(self.project.rom)
        self.assertEqual([r['nationality']for r in rows[:6]],
            ['Portugal','Spain','England','Holland','Italy','Turkey'])
        self.assertEqual(rows[38]['nationality'],'England')
        self.assertEqual(rows[77]['nationality'],'Holland')
        self.assertEqual(rows[114]['nationality'],'Pirate')
        self.assertEqual(rows[60]['nationality'],'Portugal')

    def test_malformed_table_is_rejected(self):
        with self.assertRaises(ValueError):decode_sailors(b'')
        broken=bytearray(self.project.rom);broken[0x881F3:0x881F3+13]=b'A'*13
        with self.assertRaises(ValueError):decode_sailors(broken)

if __name__=='__main__':unittest.main()
