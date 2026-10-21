"""Verify independent native capacity/default cargo fields and project persistence."""
import os,sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,MODEL_BASE,SPEC_BASE

class CargoTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():self.skipTest('Set NH_STOCK_ROM to a compatible stock ROM.')
        self.p=ShipProject(path);self.p.repair_safeguard=False
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

    def test_200_guns_and_2000_total_capacity_roundtrip(self):
        from content_library import ContentLibrary,capture_ship
        from backend import apply_ips
        self.p.update(10,dict(max_guns=200,max_crew=500,capacity=2000))
        self.p.add_ship(10)
        self.p.update(25,dict(max_guns=200,max_crew=500,capacity=2000,factory_guns=200,factory_crew=500))
        data,_=self.p.build()
        self.assertEqual(decode(data)[10]['max_guns'],200)
        self.assertEqual(decode(data)[10]['capacity'],2000)
        self.assertEqual(data[0x210000+20],200)
        self.assertEqual(data[0x2100fa+8],200)
        self.assertEqual(data[0x2100fa+4],50)
        self.assertEqual(decode(data)[10]['max_crew'],500)
        self.assertEqual(int.from_bytes(data[0x2100fa+6:0x2100fa+8],'little'),2000)
        self.assertEqual(self.p.ships[25]['factory_cargo'],1300)
        self.assertEqual(self.p.ships[25]['factory_guns']+self.p.ships[25]['factory_crew']+self.p.ships[25]['factory_cargo'],2000)
        with tempfile.TemporaryDirectory()as folder:
            folder=Path(folder);lib=ContentLibrary(self.p.rom,folder/'library');entry=capture_ship(self.p,25);lib.put(entry)
            self.assertEqual(ContentLibrary(self.p.rom,folder/'library').entries[0]['ship']['factory_guns'],200)
            path=folder/'Ships.json';self.p.save_project(path);loaded=ShipProject(self.p.source);loaded.load_project(path)
            self.assertEqual(loaded.ships,self.p.ships)
            target=folder/'Ships.sfc';loaded.export(target)
            self.assertEqual(apply_ips(self.p.rom,target.with_suffix('.ips').read_bytes()),target.read_bytes())
        for index in (10,25):
            before=dict(self.p.ships[index])
            for change in (dict(max_guns=201),dict(max_crew=510),dict(capacity=2001)):
                with self.assertRaises(ValueError):self.p.update(index,change)
                self.assertEqual(self.p.ships[index],before)
        with self.assertRaises(ValueError):self.p.update(25,dict(factory_guns=201))

    def test_lower_crew_limit_trims_starting_spaces_and_persists(self):
        from custom_presets import prepare
        from content_library import capture_ship,validate_ship
        before=dict(self.p.ships[10]);self.assertGreater(before['factory_crew'],50)
        self.p.update(10,dict(max_crew=50,min_crew=1))
        row=self.p.ships[10]
        self.assertEqual(row['factory_crew'],50)
        self.assertEqual(row['capacity'],before['capacity'])
        self.assertEqual(row['factory_cargo'],before['factory_cargo']+before['factory_crew']-50)
        data,_=self.p.build();actual=decode(data)[10]
        self.assertEqual(actual['factory_crew'],50);self.assertEqual(actual['min_crew'],1)
        self.assertEqual(actual['max_crew'],50);self.assertEqual(actual['factory_cargo'],row['factory_cargo'])
        self.assertEqual(prepare(self.p,self.p.manifest()).ships,self.p.ships)
        entry=capture_ship(self.p,10);self.assertEqual(validate_ship(entry,self.p.rom)['ship']['factory_crew'],50)
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'Crew.json';self.p.save_project(path)
            loaded=ShipProject(self.p.source);loaded.load_project(path)
            self.assertEqual(loaded.build()[0],data)
        self.p.update(10,dict(max_crew=100));self.assertEqual(self.p.ships[10]['factory_crew'],50)
        self.p.add_ship(10);self.p.update(25,dict(max_crew=20))
        self.assertEqual(self.p.ships[25]['factory_crew'],20)
        data,_=self.p.build();self.assertEqual(int.from_bytes(data[0x210000+21:0x210000+23],'little'),20)
        self.assertEqual(prepare(self.p,self.p.manifest()).ships,self.p.ships)

    def test_crew_floor_and_invalid_fittings_remain_atomic(self):
        self.p.update(10,dict(min_crew=1,max_crew=10));self.assertEqual(self.p.ships[10]['factory_crew'],10)
        before=self.p.manifest()
        for values in (dict(min_crew=0),dict(max_crew=0),dict(max_crew=1),dict(max_crew=15),dict(min_crew=11)):
            with self.subTest(values=values),self.assertRaises(ValueError):self.p.update(10,values)
            self.assertEqual(self.p.manifest(),before)
        self.p.add_ship(10)
        with self.assertRaises(ValueError):self.p.update(25,dict(max_crew=10,factory_crew=20))

if __name__=='__main__':unittest.main()
