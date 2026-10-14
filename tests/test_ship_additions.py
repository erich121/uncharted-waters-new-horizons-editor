"""ROM-backed expansion invariants and malformed-project rejection."""
import json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,apply_ips,ports

class ShipAdditionTests(unittest.TestCase):
    def setUp(self):
        source=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not source.is_file():self.skipTest('Set NH_STOCK_ROM to your stock USA ROM or ZIP.')
        self.p=ShipProject(source)
    def test_all_counts_and_independent_records(self):
        for n in range(1,6):
            self.p.add_ship([6,10,13,3,16][n-1]);self.p.update(24+n,dict(name=f'Addition {n}',hull=70+n,ports=[0,31],industry=300))
            rom,_=self.p.build();self.assertEqual(len(rom),0x400000)
            self.assertEqual(decode(rom),self.p.original)
            self.assertEqual(rom[0xb2378:0xb24a4],self.p.rom[0xb2378:0xb24a4])
            self.assertEqual(rom[0x70ded:0x70df1],self.p.rom[0x70ded:0x70df1])
            for i,s in enumerate(self.p.ships[25:]):
                self.assertEqual(rom[0x210000+i*25+18],25+i)
                self.assertEqual(rom[0x2100fa+i*12+1],s['hull'])
                self.assertEqual(int.from_bytes(rom[0x200400+(65+i)*2:0x200402+(65+i)*2],'little'),0x780+i*25)
                self.assertEqual(int.from_bytes(rom[0x200500+(25+i)*2:0x200502+(25+i)*2],'little'),0x87a+i*12)
                self.assertEqual(rom[0x214000+31*n+i],1);self.assertEqual(rom[0x214000+30*n+i],0)
            self.assertEqual(sum(rom)&65535,int.from_bytes(rom[0xffde:0xffe0],'little'))
    def test_roundtrip_export_and_old_schema(self):
        self.p.add_ship(10);self.p.update(25,dict(name='Custom Galleon',ports=[31],industry=900,factory_guns=80,factory_crew=200,capacity=1000,max_guns=90,max_crew=300))
        self.p.update(13,dict(max_guns=60))
        with tempfile.TemporaryDirectory()as f:
            f=Path(f);project=f/'mod.json';self.p.save_project(project)
            other=ShipProject(self.p.source);other.load_project(project);self.assertEqual(other.ships,self.p.ships)
            output=f/'mod.sfc';other.export(output)
            self.assertEqual(apply_ips(self.p.rom,output.with_suffix('.ips').read_bytes()),output.read_bytes())
            old=dict(format='new-horizons-ship-project',version=1,base_sha256=self.p.manifest()['base_sha256'],edits=[])
            project.write_text(json.dumps(old));other.load_project(project);self.assertEqual(len(other.ships),25)
    def test_invalid_new_values_atomic(self):
        self.p.add_ship(10);before=json.dumps(self.p.ships)
        for values in [dict(ports=[]),dict(ports=[0],industry=1000),dict(industry=901),dict(factory_guns=151),dict(capacity=10),dict(factory_crew=499),dict(base_hull=25),dict(ports=[0,0]),dict(ports=[True])]:
            with self.subTest(values=values),self.assertRaises(ValueError):self.p.update(25,values)
            self.assertEqual(json.dumps(self.p.ships),before)
        for _ in range(4):self.p.add_ship(10)
        with self.assertRaises(ValueError):self.p.add_ship(10)
        with self.assertRaises(ValueError):self.p.remove_ship(10)
        self.p.remove_ship(26);self.assertEqual([s['id']for s in self.p.ships],list(range(29)))
    def test_reject_malformed_added_project_without_mutation(self):
        self.p.add_ship(10);before=json.dumps(self.p.ships)
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'bad.json';m=self.p.manifest();m['added_ships'][0]['id']=29;path.write_text(json.dumps(m))
            with self.assertRaises(ValueError):self.p.load_project(path)
            # manifest must not expose mutable project rows to external callers.
            self.assertEqual(json.dumps(self.p.ships),before)

if __name__=='__main__':unittest.main()
