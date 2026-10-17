"""Read-only port data and exact compressed world-map decoding."""
import hashlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from world import catalogue,region_names
from rom_map import decode_grid,overview,port_positions,PORT_BASE,WIDTH,HEIGHT

class WorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=ShipProject(ROOT/'New Horizons (USA).zip')
    def test_all_ports_and_starting_values(self):
        before=self.p.manifest();rows=catalogue(self.p.rom)
        self.assertEqual(len(rows),130)
        for i,row in enumerate(rows):
            self.assertEqual(row['id'],i)
            self.assertTrue(0<=row['x']<WIDTH and 0<=row['y']<HEIGHT)
            if i<100:
                at=0x8da7f+i*37
                self.assertEqual(row['economy'],int.from_bytes(self.p.rom[at:at+2],'little'))
                self.assertEqual(row['industry'],int.from_bytes(self.p.rom[at+4:at+6],'little'))
            else:self.assertNotIn('economy',row);self.assertNotIn('industry',row)
        self.assertEqual((rows[0]['name'],rows[0]['economy'],rows[0]['industry']),('Lisbon',780,770))
        self.assertEqual(rows[100]['name'],'Hekla');self.assertEqual(rows[129]['name'],'Forel')
        self.assertEqual(self.p.manifest(),before)
    def test_specialties_use_clean_commodity_names(self):
        from goods import catalogue as goods_catalogue
        goods=goods_catalogue(self.p.rom)
        for row in catalogue(self.p.rom)[:100]:
            good=self.p.rom[0x8da7f+row['id']*37+26]
            self.assertEqual(row['specialty'],'None'if good==255 else goods[good]['name'])
            self.assertTrue(all(ord(c)>=32 for c in row['specialty']))

    def test_native_regions_partition_all_ports(self):
        names=region_names(self.p.rom);self.assertEqual(len(names),13)
        rows=catalogue(self.p.rom)
        self.assertEqual(rows[0]['region'],'Iberia')
        self.assertEqual(rows[41]['region'],'Northern Europe')
        self.assertEqual(sum(row['region']=='Northern Europe'for row in rows),15)
        for row in rows[:100]:
            self.assertEqual(row['region'],names[self.p.rom[0x8da7f+row['id']*37+33]])
        self.assertEqual(sum(row['region']=='Supply ports'for row in rows),30)
        self.assertEqual(sum(sum(row['region']==name for row in rows)for name in names+['Supply ports']),130)

    def test_verified_world_layout_and_port_bounds(self):
        grid=decode_grid(self.p.rom)
        self.assertEqual(hashlib.sha256(grid).hexdigest(),'0e26a098169182a5c0cfa013e91f5e611dd4b3026f66e973e5d42a83f9ec680f')
        self.assertEqual(overview(grid).size,(WIDTH,HEIGHT))
        invalid=bytearray(self.p.rom);invalid[PORT_BASE:PORT_BASE+2]=(WIDTH).to_bytes(2,'little')
        with self.assertRaises(ValueError):port_positions(invalid)
        with self.assertRaises(ValueError):overview(b'')

if __name__=='__main__':unittest.main()
