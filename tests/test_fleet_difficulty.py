"""Stock-only difficulty option, compatibility and isolated patch scope."""
import unittest,sys,tempfile,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,apply_ips
from fleet_difficulty import HELPER,TABLE,SITES,upgrades,install,preset,compile_table,validate_rules

class DifficultyTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():self.skipTest('Supply stock ROM.')
        self.p=ShipProject(path);self.p.repair_safeguard=False

    def test_default_off_and_identity(self):
        self.assertFalse(self.p.fleet_difficulty)
        self.assertEqual(self.p.build(),(self.p.rom,[]))
        self.assertEqual(upgrades(self.p.ships),[(50,55),(51,60)])

    def test_patch_scope_and_composition(self):
        for count in (0,1,5):
            for other in (False,True):
                p=ShipProject(self.p.source);p.repair_safeguard=other;p.fleet_control=other
                for _ in range(count):p.add_ship(10)
                before,_=p.build();p.fleet_difficulty=True;after,_=p.build()
                allowed=set(range(0xffdc,0xffe0))|{0xffd7}|set(range(HELPER,HELPER+0x100))|set(range(TABLE,TABLE+96))
                for site in SITES:allowed.update(range(site,site+7))
                self.assertEqual(len(after),0x400000)
                self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(before,after))))
                self.assertEqual(decode(after),p.original)
                self.assertEqual(before[0x8021:0x8025],after[0x8021:0x8025])
                self.assertEqual(after[0x8c7ce:0x8ce27],p.rom[0x8c7ce:0x8ce27])
                self.assertEqual(sum(after)&65535,int.from_bytes(after[0xffde:0xffe0],'little'))

    def test_no_durability_downgrades_with_edited_hulls(self):
        self.p.update(10,dict(hull=100));self.p.update(20,dict(hull=60))
        self.assertEqual(upgrades(self.p.ships),[])
        self.p.fleet_difficulty=True
        self.assertEqual(decode(self.p.build()[0]),self.p.ships)

    def test_project_ips_and_legacy_migration(self):
        with tempfile.TemporaryDirectory()as f:
            f=Path(f);self.p.fleet_difficulty=True;path=f/'Project.json';self.p.save_project(path)
            p=ShipProject(self.p.source);p.load_project(path);self.assertTrue(p.fleet_difficulty)
            out=f/'Hard.sfc';report=p.export(out)
            self.assertTrue(report['gameplay']['fleet_difficulty'])
            self.assertEqual(apply_ips(p.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
            m=self.p.manifest();m['version']=7;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle',None);m.pop('item_special_only',None);m.pop('item_blind',None);m.pop('item_special',None);m.pop('item_seed',None);m.pop('custom_items',None);m.pop('item_edits',None);m.pop('custom_ships',None);m.pop('custom_goods',None);m.pop('custom_economy',None);m.pop('custom_mates',None);m.pop('custom_captains',None);m.pop('economy_edits',None);m.pop('goods_edits',None);m.pop('gameplay');path.write_text(json.dumps(m));p.load_project(path)
            self.assertFalse(p.fleet_difficulty)
            self.assertEqual(p.build(),(p.rom,[]))
            for value in (1,'yes',None):
                m=self.p.manifest();m['gameplay']['fleet_difficulty']=value;path.write_text(json.dumps(m));before=p.manifest()
                with self.assertRaises(ValueError):p.load_project(path)
                self.assertEqual(p.manifest(),before)

    def test_nations_roles_added_ids_and_removal(self):
        self.p.add_ship(15);self.p.add_ship(15)
        self.p.fleet_rules=preset('stock')
        self.p.fleet_rules[3][0][1]=25
        self.p.fleet_rules[0][1][1]=15
        self.p.fleet_rules[1][2][2]=26
        self.p.fleet_rules[5][3][1]=26
        table=compile_table(self.p.ships,self.p.fleet_rules)
        self.assertEqual(table[3*16+1],65)
        self.assertEqual(table[0*16+4+1],55)
        self.assertEqual(table[1*16+8+2],66)
        self.assertEqual(table[5*16+12+1],66)
        self.assertEqual(sum(v!=255 for v in table),4)
        self.p.remove_ship(25)
        self.assertEqual(self.p.fleet_rules[3][0][1],-1)
        self.assertEqual(self.p.fleet_rules[1][2][2],25)
        self.assertEqual(compile_table(self.p.ships,self.p.fleet_rules)[26],65)

    def test_invalid_rules_atomic_and_schema8_keeps_preset(self):
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'Project.json'
            m=self.p.manifest();m['version']=8;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle',None);m.pop('item_special_only',None);m.pop('item_blind',None);m.pop('item_special',None);m.pop('item_seed',None);m.pop('custom_items',None);m.pop('item_edits',None);m.pop('custom_ships',None);m.pop('custom_goods',None);m.pop('custom_economy',None);m.pop('custom_mates',None);m.pop('custom_captains',None);m.pop('economy_edits',None);m.pop('goods_edits',None);m['gameplay'].pop('fleet_rules');m['gameplay']['fleet_difficulty']=True
            path.write_text(json.dumps(m));self.p.load_project(path)
            self.assertTrue(self.p.fleet_difficulty);self.assertEqual(self.p.fleet_rules,preset())
            for invalid in ([],None,[[[]]*3]*6,[[[True]*4]*4]*6,[[[25]*4]*4]*6):
                before=self.p.manifest();m=self.p.manifest();m['gameplay']['fleet_rules']=invalid;path.write_text(json.dumps(m))
                with self.assertRaises(ValueError):self.p.load_project(path)
                self.assertEqual(self.p.manifest(),before)

    def test_smart_presets_only_use_safe_original_choices(self):
        for name in ('stock','flagships','regional','stronger'):
            rules=preset(name);table=compile_table(self.p.ships,rules)
            for n,nation in enumerate(rules):
                for role,row in enumerate(nation):
                    for i,target in enumerate(row):
                        if target>=0:
                            self.assertLess(target,25)
                            self.assertNotEqual(table[n*16+role*4+i],255)
        self.assertEqual(preset('regional')[4][2][0],14)
        self.assertTrue(all(v==-1 for n in preset('stronger')for v in n[2]))

    def test_schema9_migrates_first_three_and_clears_fourth(self):
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'Old.json';m=self.p.manifest();m['version']=9;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle',None);m.pop('item_special_only',None);m.pop('item_blind',None);m.pop('item_special',None);m.pop('item_seed',None);m.pop('custom_items',None);m.pop('item_edits',None);m.pop('custom_ships',None);m.pop('custom_goods',None);m.pop('custom_economy',None);m.pop('custom_mates',None);m.pop('custom_captains',None);m.pop('economy_edits',None);m.pop('goods_edits',None)
            old=[nation[:3]for nation in preset('regional')]
            m['gameplay']['fleet_rules']=old;m['gameplay']['fleet_difficulty']=True
            path.write_text(json.dumps(m));self.p.load_project(path)
            self.assertTrue(self.p.fleet_difficulty)
            self.assertEqual([nation[:3]for nation in self.p.fleet_rules],old)
            self.assertTrue(all(nation[3]==[-1]*4 for nation in self.p.fleet_rules))
            before=self.p.manifest();m['gameplay']['fleet_rules'][0].append([-1]*4);path.write_text(json.dumps(m))
            with self.assertRaises(ValueError):self.p.load_project(path)
            self.assertEqual(self.p.manifest(),before)

    def test_conflicting_hook_or_helper_rejected(self):
        data=bytearray(self.p.rom);data[SITES[0]]=0
        with self.assertRaises(ValueError):install(data,self.p.ships)
        data=bytearray(self.p.rom)+bytearray(b'\xff'*0x200000);data[HELPER]=0
        with self.assertRaises(ValueError):install(data,self.p.ships)

if __name__=='__main__':unittest.main()
