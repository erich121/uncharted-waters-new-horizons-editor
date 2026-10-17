"""Character edits and reproducible four-digit starting-port shuffles."""
import sys,os,json,tempfile,unittest
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,apply_ips
from sailors import BASE,STRIDE,ATTRIBUTES,MATE_IDS,CAPTAIN_IDS,decode_sailors
from character_mods import port_shuffle,seeded_ports,random_seed

class CharacterModsTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():self.skipTest('Supply the stock ROM.')
        self.p=ShipProject(path);self.p.custom_mates=True;self.p.custom_captains=True;self.p.repair_safeguard=False

    def test_seed_reproduces_and_modes_preserve_slots(self):
        stock={r['id']:r['starting_port']for r in decode_sailors(self.p.rom)if r['role']=='Free agent'}
        previous=[]
        for seed in ('0000','0001','1234','9999'):
            for blind in (False,True):
                entries=seeded_ports(self.p.rom,seed,blind)
                self.assertEqual(entries,seeded_ports(self.p.rom,seed,blind))
                mapping={e['id']:e['port']for e in entries}
                self.assertEqual(set(mapping),set(stock))
                self.assertEqual(Counter(mapping.values()),Counter(stock.values()))
                self.assertNotIn(mapping,previous);previous.append(mapping)
        for _ in range(20):self.assertRegex(random_seed(),r'^[0-9]{4}$')

    def test_shuffle_only_changes_port_bytes(self):
        self.p.set_free_agent_shuffle(True,'1234');out,_=self.p.build()
        expected=port_shuffle(self.p.rom,self.p.free_agent_shuffle)
        allowed=set(range(0xffdc,0xffe0))|{BASE+i*STRIDE+45 for i in expected}
        self.assertEqual(len(out),len(self.p.rom))
        self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(self.p.rom,out))))
        for i,port in expected.items():self.assertEqual(out[BASE+i*STRIDE+45],port)
        self.p.set_free_agent_shuffle(False,'0000');self.assertEqual(self.p.build(),(self.p.rom,[]))

    def test_all_attributes_and_ids_restore(self):
        for i in MATE_IDS+CAPTAIN_IDS:self.p.update_character(i,{key:(i+j)%2*100 for j,key in enumerate(ATTRIBUTES)})
        out,_=self.p.build();allowed=set(range(0xffdc,0xffe0))
        for i in MATE_IDS+CAPTAIN_IDS:
            allowed.update(range(BASE+i*STRIDE+28,BASE+i*STRIDE+36))
            for j,key in enumerate(ATTRIBUTES):self.assertEqual(out[BASE+i*STRIDE+28+j],(i+j)%2*100)
        self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(self.p.rom,out))))
        for i in MATE_IDS+CAPTAIN_IDS:self.p.update_character(i,{key:self.p.rom[BASE+i*STRIDE+28+j]for j,key in enumerate(ATTRIBUTES)})
        self.assertEqual(self.p.build(),(self.p.rom,[]))

    def test_invalid_edits_and_seeds_atomic(self):
        for i,values in [(0,dict(luck=100)),(120,dict(luck=100)),(True,dict(luck=100)),(69,dict(age=25)),(69,dict(luck=True)),(69,dict(luck=101)),(69,dict(luck=-1)),(69,dict(leadership=99,luck='90'))]:
            before=self.p.manifest()
            with self.assertRaises(ValueError):self.p.update_character(i,values)
            self.assertEqual(before,self.p.manifest())
        for enabled,seed in [(True,''),(True,'123'),(True,'12345'),(True,'12a4'),(True,'１２３４'),(True,1234),(True,True),(1,'1234')]:
            before=self.p.manifest()
            with self.assertRaises(ValueError):self.p.set_free_agent_shuffle(enabled,seed)
            self.assertEqual(before,self.p.manifest())

    def test_project_and_ips_roundtrip(self):
        self.p.add_ship(10);self.p.update(25,dict(ports=[31],industry=300))
        self.p.update_character(79,dict(leadership=100,luck=0));self.p.update_character(38,dict(courage=99))
        self.p.set_free_agent_shuffle(True,'0012')
        with tempfile.TemporaryDirectory()as f:
            f=Path(f);project=f/'Project.json';out=f/'Campaign.sfc';self.p.save_project(project)
            loaded=ShipProject(self.p.source);loaded.load_project(project)
            self.assertEqual(loaded.manifest(),self.p.manifest())
            report=loaded.export(out)
            self.assertEqual(apply_ips(self.p.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
            self.assertEqual(report['free_agent_shuffle'],self.p.free_agent_shuffle)

    def test_v6_projects_disable_new_features(self):
        old=self.p.manifest();old['version']=6;old.pop('shipbuilding_shuffle',None);old.pop('goods_shuffle',None);old.pop('item_special_only',None);old.pop('item_blind',None);old.pop('item_special',None);old.pop('item_seed',None);old.pop('custom_items',None);old.pop('item_edits',None);old.pop('custom_ships',None);old.pop('custom_goods',None);old.pop('custom_economy',None);old.pop('custom_mates',None);old.pop('custom_captains',None);old.pop('economy_edits',None);old.pop('goods_edits',None);old.pop('gameplay');old.pop('character_edits');old.pop('free_agent_shuffle')
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'Old.json';path.write_text(json.dumps(old))
            self.p.update_character(79,dict(luck=0));self.p.set_free_agent_shuffle(True,'1234')
            self.p.load_project(path)
        self.assertEqual(self.p.character_edits,[])
        self.assertEqual(self.p.free_agent_shuffle,dict(enabled=False,blind=False,seed='0000'))

    def test_invalid_project_keeps_work(self):
        self.p.update_character(38,dict(courage=99));before=self.p.manifest()
        bad=json.loads(json.dumps(before));bad['free_agent_shuffle']['seed']='12345'
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'Bad.json';path.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):self.p.load_project(path)
        self.assertEqual(before,self.p.manifest())

    def test_blind_differs_and_survives_reload(self):
        self.p.set_free_agent_shuffle(True,'1234',True)
        self.assertNotEqual(port_shuffle(self.p.rom,self.p.free_agent_shuffle),{e['id']:e['port']for e in seeded_ports(self.p.rom,'1234')})
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'Blind.json';self.p.save_project(path)
            loaded=ShipProject(self.p.source);loaded.load_project(path)
            self.assertEqual(loaded.build()[0],self.p.build()[0])
            report=loaded.export(Path(f)/'Blind.sfc')
            self.assertNotIn('ports',report['free_agent_shuffle'])
            self.assertEqual(report['free_agent_shuffle']['agents'],40)

if __name__=='__main__':unittest.main()
