"""Verify independent native capacity/default cargo fields and project persistence."""
import os,sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,MODEL_BASE,SPEC_BASE

class CargoTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():self.skipTest('Set NH_STOCK_ROM to a compatible stock ROM.')
        self.p=ShipProject(path)
    def test_every_original_cargo_capacity_and_byte_boundaries(self):
        for i,s in enumerate(self.p.original):
            cargo=s['factory_cargo']+17
            self.p.update(i,dict(factory_cargo=cargo))
        rom,_=self.p.build();actual=decode(rom)
        for i,s in enumerate(actual):
            original=self.p.original[i]
            self.assertEqual(s['factory_cargo'],original['factory_cargo']+17)
            self.assertEqual(s['capacity'],original['capacity']+17)
            for k in set(s)-{'factory_cargo','capacity'}:self.assertEqual(s[k],original[k])
        allowed=set(range(0xffdc,0xffe0))
        for i in range(25):allowed.update([MODEL_BASE+i*25+23,MODEL_BASE+i*25+24,SPEC_BASE+i*12+6,SPEC_BASE+i*12+7])
        self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(self.p.rom,rom))))
    def test_capacity_changes_cargo_and_restore_project(self):
        self.p.update(3,dict(capacity=600));s=self.p.ships[3]
        self.assertEqual(s['factory_cargo'],600-s['factory_guns']-s['factory_crew'])
        with tempfile.TemporaryDirectory()as f:
            project=Path(f)/'cargo.json';self.p.save_project(project)
            other=ShipProject(self.p.source);other.load_project(project);self.assertEqual(self.p.ships,other.ships)
            self.assertEqual(self.p.build()[0],other.build()[0])
    def test_negative_inconsistent_and_noninteger_cargo_are_atomic(self):
        before=dict(self.p.ships[3])
        for v in [dict(factory_cargo=-1),dict(factory_cargo=2000),dict(factory_cargo=True),dict(capacity=20),dict(capacity=900,factory_cargo=100),dict(factory_cargo=1.5)]:
            with self.subTest(v=v),self.assertRaises(ValueError):self.p.update(3,v)
            self.assertEqual(self.p.ships[3],before)
    def test_combined_original_and_added_cargo_exports(self):
        self.p.update(3,dict(factory_cargo=420));self.p.add_ship(10)
        self.p.update(25,dict(factory_cargo=700,ports=[31],industry=900))
        rom,_=self.p.build();self.assertEqual(decode(rom)[3]['factory_cargo'],420)
        self.assertEqual(int.from_bytes(rom[0x210000+23:0x210000+25],'little'),700)
        self.assertEqual(int.from_bytes(rom[0x2100fa+6:0x2100fa+8],'little'),self.p.ships[25]['capacity'])
    def test_shipyard_cargo_matches_requested_value(self):
        self.p.update(3,dict(yard_cargo=420));s=self.p.ships[3]
        self.assertEqual(s['capacity']-s['max_guns']-s['max_crew'],420)
        self.assertEqual(s['capacity'],s['factory_cargo']+s['factory_guns']+s['factory_crew'])
        self.p.add_ship(3);self.assertEqual(self.p.ships[25]['capacity'],s['capacity'])
        before=dict(self.p.ships[13])
        with self.assertRaises(ValueError):self.p.update(13,dict(max_crew=500))
        self.assertEqual(self.p.ships[13],before)

if __name__=='__main__':unittest.main()
