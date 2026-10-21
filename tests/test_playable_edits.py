import json
from legacy_manifest import legacy_manifest
import tempfile
import unittest
from pathlib import Path
from backend import ShipProject,apply_ips,ips
from character_mods import apply,shuffled_skills,shuffled_stats
from sailors import BASE,STRIDE,ATTRIBUTES


class PlayableEditTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'New Horizons (USA).zip'
        if not path.exists():self.skipTest('Requires the stock ROM.')
        self.p=ShipProject(path)

    def test_all_six_attribute_extremes_write_only_verified_fields(self):
        for i in range(6):self.p.update_character(i,{key:100 if n%2 else 0 for n,key in enumerate(ATTRIBUTES)if key!='luck'})
        result=self.p.build()[0]
        allowed=set(range(0xffdc,0xffe0))|{BASE+i*STRIDE+28+n for i in range(6)for n in range(8)}
        self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(self.p.rom,result))))
        self.assertEqual(apply_ips(self.p.rom,ips(self.p.rom,result)),result)
        self.assertEqual(len(result),0x200000)

    def test_all_skill_masks_and_upper_bits(self):
        for i in range(6):
            modified=bytearray(self.p.rom);modified[BASE+i*STRIDE+48]|=224
            for mask in range(32):
                self.p.update_character(i,dict(skills=mask))
                data=bytearray(modified)
                apply(data,modified,[dict(id=i,field='skills',value=mask)],self.p.free_agent_shuffle)
                self.assertEqual(data[BASE+i*STRIDE+48],224|mask)

    def test_invalid_edits_atomic(self):
        for value in (-1,101,True,'50'):
            before=self.p.manifest()
            with self.assertRaises(ValueError):self.p.update_character(0,dict(leadership=70,luck=value))
            self.assertEqual(self.p.manifest(),before)
        for field in ('age','nationality','name'):
            with self.assertRaises(ValueError):self.p.update_character(0,{field:50})

    def test_starting_levels_bounds_scope_and_roundtrip(self):
        for i in range(6):self.p.update_character(i,dict(navigation_level=1+i*19,battle_level=100-i*19))
        result=self.p.build()[0]
        allowed=set(range(0xffdc,0xffe0))|{BASE+i*STRIDE+j for i in range(6)for j in (36,37)}
        self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(self.p.rom,result))))
        for value in (0,101,True,'20'):
            before=self.p.manifest()
            with self.assertRaises(ValueError):self.p.update_character(0,dict(navigation_level=value))
            self.assertEqual(before,self.p.manifest())
        for i in (6,69,79,114):
            with self.assertRaises(ValueError):self.p.update_character(i,dict(battle_level=20))
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'levels.json';self.p.save_project(path);q=ShipProject(self.p.source);q.load_project(path)
            self.assertEqual(q.build(),self.p.build())

    def test_portable_locked_project_and_schema22_migration(self):
        self.p.update_character(3,dict(leadership=100,skills=31));self.p.custom_characters=False
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'project.json';self.p.save_project(path)
            q=ShipProject(self.p.source);q.load_project(path)
            self.assertFalse(q.custom_characters);self.assertEqual(q.build(),self.p.build())
            old=ShipProject(self.p.source).manifest();old['version']=22;old.pop('custom_characters')
            path.write_text(json.dumps(legacy_manifest(old)));q.load_project(path)
            self.assertFalse(q.custom_characters);self.assertEqual(q.build(),(q.rom,[]))

    def test_mate_and_captain_shuffles_exclude_playable_characters(self):
        self.p.update_character(3,dict(leadership=100,skills=0))
        self.p.set_free_agent_shuffle(True,'1234',names=True,captain_names=True,mate_stats=True,captain_stats=True,mate_skills=True,captain_skills=True)
        generated=shuffled_stats(self.p.rom,self.p.free_agent_shuffle)+shuffled_skills(self.p.rom,self.p.free_agent_shuffle)
        self.assertTrue(all(row['id']>=6 for row in generated))
        self.assertEqual(self.p.character_record(3)['leadership'],100)
        self.assertEqual(self.p.character_record(3)['skills'],0)

    def test_explicit_stock_luck_is_fixed_and_survives_project(self):
        from protagonist_mods import SITE,NATIVE,FLAGS,VALUES
        self.p.update_character(0,dict(luck=50))
        self.assertIn(dict(id=0,field='luck',value=50),self.p.character_edits)
        result=self.p.build()[0]
        self.assertEqual(len(result),0x400000)
        self.assertNotEqual(result[SITE:SITE+7],NATIVE)
        self.assertEqual(result[FLAGS:FLAGS+6],bytes([1,0,0,0,0,0]))
        self.assertEqual(result[VALUES],50)
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'fixed.json';self.p.save_project(path)
            q=ShipProject(self.p.source);q.load_project(path)
            self.assertEqual(q.build(),self.p.build())
        self.p.character_edits=[];self.assertEqual(self.p.build(),(self.p.rom,[]))

    def test_other_edits_keep_native_luck_roll_and_overlap_guard(self):
        from protagonist_mods import SITE,NATIVE,HELPER,install
        self.p.update_character(0,dict(leadership=100,skills=31))
        result=self.p.build()[0]
        self.assertEqual(result[SITE:SITE+7],NATIVE)
        self.assertFalse(any(e['field']=='luck'for e in self.p.character_edits))
        data=bytearray(self.p.rom)+bytearray(b'\xff'*0x200000);data[HELPER]=0
        with self.assertRaisesRegex(ValueError,'overlaps'):install(data,[dict(id=0,field='luck',value=50)])
