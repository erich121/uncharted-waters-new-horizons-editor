"""Repair option persistence, exact patch scope and stock-rate preservation."""
import unittest,sys,os,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,apply_ips
from repair import SITES,HELPER,CODE,apply
class RepairTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():self.skipTest('Supply a stock ROM.')
        self.p=ShipProject(path)
    def test_exact_patch_for_zero_one_five(self):
        for n in (0,1,5):
            p=ShipProject(self.p.source)
            for _ in range(n):p.add_ship(10)
            p.repair_safeguard=False;base,_=p.build()
            p.repair_safeguard=True;fixed,_=p.build()
            expected=bytearray(base)
            if len(expected)==0x200000:expected.extend(b'\xff'*0x200000)
            allowed=set(range(0xffdc,0xffe0))|{0xffd7}|set(range(HELPER,HELPER+len(CODE)))
            for site in SITES:
                allowed.update(range(site,site+4));self.assertEqual(fixed[site:site+4],bytes.fromhex('22 00 8c e1'))
            self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(expected,fixed))))
            self.assertEqual(fixed[HELPER:HELPER+len(CODE)],CODE)
            self.assertEqual(decode(fixed),p.original)
            self.assertEqual(len(fixed),0x400000)
            self.assertEqual(sum(fixed)&65535,int.from_bytes(fixed[0xffde:0xffe0],'little'))
    def test_disabled_stock_export_is_exact(self):
        self.assertFalse(self.p.repair_safeguard)
        self.p.repair_safeguard=False;self.assertEqual(self.p.build(),(self.p.rom,[]))
    def test_option_project_export_roundtrip_and_manifest(self):
        with tempfile.TemporaryDirectory()as f:
            f=Path(f)
            for enabled in (False,True):
                self.p.repair_safeguard=enabled;path=f/'project.json';self.p.save_project(path)
                other=ShipProject(self.p.source);other.load_project(path)
                self.assertIs(other.repair_safeguard,enabled)
                out=f/('on.sfc'if enabled else 'off.sfc');report=other.export(out)
                self.assertIs(report['fixes']['repair_safeguard'],enabled)
                self.assertEqual(apply_ips(other.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
    def test_old_projects_get_default_and_invalid_option_is_atomic(self):
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'project.json'
            for version in (1,2):
                m=dict(format='new-horizons-ship-project',version=version,base_sha256=self.p.manifest()['base_sha256'],edits=[])
                if version==2:m['added_ships']=[]
                path.write_text(json.dumps(m));self.p.repair_safeguard=False;self.p.load_project(path);self.assertTrue(self.p.repair_safeguard)
            m=self.p.manifest();m['fixes']['repair_safeguard']='yes';path.write_text(json.dumps(m))
            before=self.p.manifest()
            with self.assertRaises(ValueError):self.p.load_project(path)
            self.assertEqual(self.p.manifest(),before)
    def test_patch_rejects_modified_call_sites_and_overlap(self):
        for at in (SITES[0],HELPER):
            data=bytearray(self.p.rom+b'\xff'*0x200000);data[at]=0
            with self.assertRaises(ValueError):apply(data)
if __name__=='__main__':unittest.main()
