"""Original new-build offers remain independent of stock specs and used ships."""
import unittest,sys,os,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,apply_ips,ports
class AvailabilityTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():self.skipTest('Supply the stock ROM.')
        self.p=ShipProject(path)
    def test_defaults_are_native_and_no_patch_when_unchanged(self):
        for i,o in enumerate(self.p.original_availability):
            self.assertEqual(o['industry'],self.p.original[i]['industry'])
            for port in ports(self.p.rom):
                self.assertEqual(port['id']in o['ports'],i in self.p.rom[0x8fae7+port['group']*8:0x8faef+port['group']*8])
        self.assertEqual(self.p.availability_changes(),[])
        self.p.repair_safeguard=False;self.assertEqual(self.p.build(),(self.p.rom,[]))
    def test_move_original_and_new_gate_without_used_changes(self):
        for count in (0,1,5):
            p=ShipProject(self.p.source)
            for _ in range(count):p.add_ship(10)
            before,_=p.build();p.update(10,dict(ports=[31],industry=900));rom,_=p.build()
            self.assertEqual(decode(rom),p.original)
            allowed={0xffd7}|set(range(0xffdc,0xffe0))|set(range(0x219000,0x219000+352))|set(range(0x219200,0x219200+100*(25+count)))|set(range(0x219e00,0x219e00+2*(25+count)))|set(range(0x219f00,0x21a000))
            for a,size in [(0x82144,3),(0x82168,3),(0x82149,10),(0x821c0,4)]:allowed.update(range(a,a+size))
            self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(before,rom))))
            for a,b in [(0x8fae7,0x8fb3f),(0x8251c,0x8257f),(0xa5826,0xa599e)]:self.assertEqual(rom[a:b],before[a:b])
            if count:self.assertEqual(rom[0x200b00:0x200b00+176],before[0x200b00:0x200b00+176])
            stride=25+count
            self.assertEqual(rom[0x219200+31*stride+10],1)
            self.assertEqual(rom[0x219200+30*stride+10],0)
            self.assertEqual(int.from_bytes(rom[0x219e00+20:0x219e00+22],'little'),900)
            self.assertEqual(rom[0x82531:0x8253b],before[0x82531:0x8253b])
    def test_hide_restore_and_roundtrip(self):
        self.p.update(10,dict(ports=[]));self.assertEqual(self.p.original_availability[10]['ports'],[])
        with tempfile.TemporaryDirectory()as f:
            f=Path(f);path=f/'project.json';self.p.save_project(path)
            p=ShipProject(self.p.source);p.load_project(path);self.assertEqual(p.original_availability,self.p.original_availability)
            out=f/'test.sfc';p.export(out);self.assertEqual(apply_ips(p.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
        self.p.update(10,self.p.stock_availability[10]);self.assertEqual(self.p.availability_changes(),[])
    def test_invalid_ports_capitals_and_overflow_are_atomic(self):
        for v in [dict(ports=[0],industry=900),dict(ports=[31,31]),dict(ports=[True]),dict(industry=901),dict(industry=True),dict(ports=[100])]:
            before=self.p.manifest()
            with self.assertRaises(ValueError):self.p.update(10,v)
            self.assertEqual(self.p.manifest(),before)
        # Original unreachable capital offers are grandfathered, not silently removed.
        self.p.update(10,self.p.stock_availability[10])
        for i in range(16):self.p.update(i,dict(ports=[31],industry=0))
        before=self.p.manifest()
        with self.assertRaises(ValueError):self.p.update(16,dict(ports=[31],industry=0))
        self.assertEqual(self.p.manifest(),before)
    def test_old_schema_and_malformed_config(self):
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'test.json'
            m=self.p.manifest();m.pop('gameplay');m.pop('character_edits');m.pop('free_agent_shuffle');m.pop('portraits');m.pop('original_availability');m['version']=3;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle',None);m.pop('item_special_only',None);m.pop('item_blind',None);m.pop('item_special',None);m.pop('item_seed',None);m.pop('custom_items',None);m.pop('item_edits',None);m.pop('custom_ships',None);m.pop('custom_goods',None);m.pop('custom_economy',None);m.pop('custom_mates',None);m.pop('custom_captains',None);m.pop('economy_edits',None);m.pop('goods_edits',None);m['fixes'].pop('fleet_control')
            path.write_text(json.dumps(m));self.p.load_project(path);self.assertEqual(self.p.availability_changes(),[])
            for raw in ('bad',[dict(id=10,ports=[31],industry=901)],[dict(id=10,ports=[31],industry=900)]*2):
                m=self.p.manifest();m['original_availability']=raw;path.write_text(json.dumps(m));before=self.p.manifest()
                with self.assertRaises(ValueError):self.p.load_project(path)
                self.assertEqual(self.p.manifest(),before)
if __name__=='__main__':unittest.main()
