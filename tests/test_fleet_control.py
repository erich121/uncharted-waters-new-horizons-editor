"""Optional fleet patch isolation, memory reservation and project migration."""
from legacy_manifest import legacy_manifest
import unittest,os,sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,apply_ips
class FleetTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():self.skipTest('Supply the stock ROM.')
        self.p=ShipProject(path)
    def test_default_off_and_disabled_identity(self):
        self.assertFalse(self.p.fleet_control);self.p.repair_safeguard=False
        self.assertEqual(self.p.build(),(self.p.rom,[]))
    def test_patch_scope_zero_one_five_with_other_options(self):
        for count in (0,1,5):
            for repair in (False,True):
                p=ShipProject(self.p.source);p.repair_safeguard=repair
                for _ in range(count):p.add_ship(10)
                p.update(10,dict(ports=[31],industry=900))
                before,_=p.build();p.fleet_control=True;rom,_=p.build()
                allowed=set(range(0x218700,0x218b51))|set(range(0xffdc,0xffe0))|{0xffd7}|set(range(0x8021,0x8025))
                for at,size in [(0x1dbe3,6),(0x1dc14,4),(0xd6c48,4),(0x26d95,4),(0x7159f,4)]:allowed.update(range(at,at+size))
                self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(before,rom))))
                self.assertEqual(decode(rom),p.original)
                self.assertEqual(rom[0x8021:0x8025],bytes.fromhex('a2 7c 07 9a'))
                self.assertEqual(rom[0x1dc14:0x1dc18],bytes.fromhex('22 00 87 e1'))
                self.assertEqual(sum(rom)&65535,int.from_bytes(rom[0xffde:0xffe0],'little'))
    def test_option_project_export_roundtrip(self):
        with tempfile.TemporaryDirectory()as f:
            f=Path(f)
            for enabled in (False,True):
                self.p.fleet_control=enabled;path=f/'project.json';self.p.save_project(path)
                p=ShipProject(self.p.source);p.load_project(path);self.assertIs(p.fleet_control,enabled)
                out=f/('on.sfc'if enabled else 'off.sfc');report=p.export(out)
                self.assertIs(report['fixes']['fleet_control'],enabled)
                self.assertEqual(apply_ips(p.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
    def test_legacy_schema_fleet_off_and_invalid_options_atomic(self):
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'legacy.json'
            for version in (1,2,3,4):
                m=self.p.manifest();m.pop('gameplay');m.pop('character_edits');m.pop('free_agent_shuffle');m.pop('portraits');m.pop('library_state',None);m.pop('ship_descriptions',None);m.pop('custom_characters',None);m['version']=version;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle',None);m.pop('item_special_only',None);m.pop('item_blind',None);m.pop('item_special',None);m.pop('item_seed',None);m.pop('custom_items',None);m.pop('item_edits',None);m.pop('custom_ships',None);m.pop('custom_goods',None);m.pop('custom_economy',None);m.pop('custom_mates',None);m.pop('custom_captains',None);m.pop('economy_edits',None);m.pop('goods_edits',None);m['fixes'].pop('fleet_control')
                if version<4:m.pop('original_availability')
                if version<3:m.pop('fixes')
                if version<2:m.pop('added_ships')
                path.write_text(json.dumps(legacy_manifest(m)));self.p.fleet_control=True;self.p.load_project(path);self.assertFalse(self.p.fleet_control)
            for value in ('yes',1,None):
                m=self.p.manifest();m['fixes']['fleet_control']=value;path.write_text(json.dumps(legacy_manifest(m)));before=self.p.manifest()
                with self.assertRaises(ValueError):self.p.load_project(path)
                self.assertEqual(self.p.manifest(),before)
if __name__=='__main__':unittest.main()
