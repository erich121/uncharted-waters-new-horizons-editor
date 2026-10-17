"""Skill bit mapping, bounded writes, add-only companions and persistence."""
import unittest,sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,apply_ips
from sailors import BASE,STRIDE,MATE_IDS,CAPTAIN_IDS,decode_sailors
from character_mods import apply,validate_edits

class SkillsTests(unittest.TestCase):
    def setUp(self):
        self.p=ShipProject(ROOT/'New Horizons (USA).zip');self.p.custom_mates=True;self.p.custom_captains=True;self.p.repair_safeguard=False

    def test_known_skills_match_native_bit_order(self):
        rows=decode_sailors(self.p.rom)
        self.assertEqual(rows[0]['skill_names'],['Negotiation'])
        self.assertEqual(rows[3]['skill_names'],['Celestial Navigation','Cartography'])
        self.assertEqual(rows[5]['skill_names'],['Accounting','Negotiation'])
        self.assertEqual(rows[79]['skills'],31)

    def test_companions_add_only_and_other_roles_can_remove(self):
        for i in range(69,79):
            original=self.p.character_record(i)['skills']
            for value in range(32):
                if value&original==original:self.p.update_character(i,dict(skills=value))
                else:
                    before=self.p.manifest()
                    with self.assertRaises(ValueError):self.p.update_character(i,dict(skills=value))
                    self.assertEqual(self.p.manifest(),before)
        for i in (6,79,114,119):
            self.p.update_character(i,dict(skills=0));self.assertEqual(self.p.character_record(i)['skill_names'],[])
            self.p.update_character(i,dict(skills=31));self.assertEqual(len(self.p.character_record(i)['skill_names']),5)
        for value in (-1,32,True,'1'):
            with self.assertRaises(ValueError):self.p.update_character(79,dict(skills=value))

    def test_writes_only_skill_bytes_and_preserves_upper_bits(self):
        for i in MATE_IDS+CAPTAIN_IDS:self.p.update_character(i,dict(skills=31 if 69<=i<79 else i%32))
        out,_=self.p.build();allowed=set(range(0xffdc,0xffe0))|{BASE+STRIDE*i+48 for i in MATE_IDS+CAPTAIN_IDS}
        self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(self.p.rom,out))))
        for i in MATE_IDS+CAPTAIN_IDS:
            self.assertEqual(out[BASE+STRIDE*i+48]&31,self.p.character_record(i)['skills'])
        modified=bytearray(self.p.rom);at=BASE+79*STRIDE+48;modified[at]|=224
        data=bytearray(modified);apply(data,modified,[dict(id=79,field='skills',value=0)],dict(enabled=False,blind=False,seed='0000'))
        self.assertEqual(data[at],224)

    def test_project_ips_and_restore(self):
        self.p.update_character(79,dict(skills=4));self.p.update_character(69,dict(skills=31))
        with tempfile.TemporaryDirectory()as f:
            f=Path(f);path=f/'Skills.json';self.p.save_project(path)
            p=ShipProject(self.p.source);p.load_project(path);self.assertEqual(p.manifest(),self.p.manifest())
            out=f/'Skills.sfc';p.export(out)
            self.assertEqual(apply_ips(p.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
            bad=p.manifest();bad['character_edits']=[dict(id=69,field='skills',value=0)]
            path.write_text(json.dumps(bad));before=p.manifest()
            with self.assertRaises(ValueError):p.load_project(path)
            self.assertEqual(p.manifest(),before)
        self.p.character_edits=[];self.assertEqual(self.p.build(),(self.p.rom,[]))

if __name__=='__main__':unittest.main()
