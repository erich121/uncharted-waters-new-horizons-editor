"""Name-based exchange and existing-art references, including stale inputs."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
import ai_presets
from backend import ShipProject


class SimpleAIFormatTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        env=patch.dict(os.environ,LOCALAPPDATA=temporary.name);env.start();self.addCleanup(env.stop)
        path=Path(os.environ.get('NH_STOCK_ROM',ROOT/'New Horizons (USA).zip'))
        if not path.exists():self.skipTest('Requires stock USA ROM')
        self.project=ShipProject(path)

    def document(self):
        return json.loads(ai_presets.export(self.project))

    def candidate(self,document):
        return ai_presets.candidate(self.project,json.dumps(document))[2]

    def additions(self,count,art='A11'):
        guide=self.document()['guide']
        ports=[r['port']for r in guide['ports']if r['shipyard']for _ in range(r['shipyard_spaces'])]
        return [dict(name=f'New Ship {i+1}',art=art,ports=[ports[i]],industry=0)for i in range(count)]

    def test_same_format_roundtrip_is_noop_with_or_without_guide(self):
        d=self.document();self.assertEqual(d['version'],2)
        self.assertEqual(self.candidate(d).manifest(),self.project.manifest())
        d.pop('guide');self.assertEqual(self.candidate(d).manifest(),self.project.manifest())
        text=json.dumps(d);self.assertNotIn('base_sha256',text);self.assertNotIn('library_ship_id',text)

    def test_ten_additions_have_automatic_ids_and_family_art(self):
        from custom_presets import PresetStore,prepare
        from backend import apply_ips
        d=self.document();d['add_ships']=self.additions(10)
        d['add_ships'][0].update(price_bars=8,total_capacity=1000,description='A fine ocean trader.')
        d['edit_ships']=[dict(ship='Galleon',price_bars=7.5)]
        rules=d['guide']['gameplay']['fleet_rules'];rules[0][0][0]='New Ship 10'
        d['gameplay']=dict(custom_fleets=True,fleet_rules=rules)
        old=self.project.manifest();c=self.candidate(d)
        self.assertEqual(len(c.ships),35);self.assertEqual(c.ships[25]['base_hull'],10)
        self.assertEqual(c.ships[25]['price_gold'],80000);self.assertEqual(c.ships[10]['price_gold'],75000)
        self.assertEqual(c.fleet_rules[0][0][0],34);self.assertEqual(c.portrait_raw(34),self.project.portrait_raw(10))
        self.assertEqual(c.ship_descriptions[25],'A fine ocean trader.')
        self.assertEqual(self.project.manifest(),old)
        with tempfile.TemporaryDirectory()as folder:
            store=PresetStore(Path(folder)/'presets.json');store.save('Simple AI',c)
            loaded=prepare(self.project,store.read()['Simple AI'])
            self.assertEqual(loaded.manifest(),c.manifest())
            target=Path(folder)/'Trial.sfc';loaded.export(target)
            self.assertEqual(apply_ips(self.project.rom,target.with_suffix('.ips').read_bytes()),target.read_bytes())

    def test_library_art_is_embedded_and_stale_code_fails(self):
        from content_library import ContentLibrary,capture_ship
        from custom_presets import prepare
        import portraits
        library=ContentLibrary(self.project.rom);entry=capture_ship(self.project,10)
        raw=portraits.encode_tiles([i%16 for i in range(3072)])
        entry['portrait']=portraits.pack({0:raw})[0]['tiles'];library.put(entry)
        d=self.document();code=next(r['art']for r in d['guide']['artwork']if r['source']=='Library')
        self.assertTrue(code.startswith('L'));self.assertNotIn(entry['id'],json.dumps(d))
        d['add_ships']=self.additions(1,code);c=self.candidate(d)
        self.assertEqual(c.portrait_raw(25),raw);self.assertEqual(c.ships[25]['base_hull'],10)
        library.clear();loaded=prepare(self.project,c.manifest())
        self.assertEqual(loaded.portrait_raw(25),raw)
        with self.assertRaisesRegex(ValueError,'Artwork reference'):self.candidate(d)
        entry['portrait']=portraits.pack({0:self.project.portrait_raw(10)})[0]['tiles'];library.put(entry)
        with self.assertRaisesRegex(ValueError,'Artwork reference'):self.candidate(d)

    def test_current_custom_portrait_can_be_reused(self):
        import portraits
        raw=portraits.encode_tiles([i//64%16 for i in range(3072)])
        self.project.set_portrait(10,raw)
        d=self.document();code=next(r['art']for r in d['guide']['artwork']if r['source']=='Current project')
        d['add_ships']=self.additions(1,code)
        self.assertEqual(self.candidate(d).portrait_raw(25),raw)

    def test_art_catalogue_does_not_supply_library_ship_identities(self):
        from content_library import ContentLibrary,capture_ship,new_id
        from ai_preset_format import artwork
        library=ContentLibrary(self.project.rom);entry=capture_ship(self.project,10);entry['id']=new_id()
        entry['ship']['name']='Unique Lib Name';entry['description']='A unique Library ship description.'
        library.put(entry);before=copy.deepcopy(library.document())
        code=next(code for code,row in artwork(self.project).items()if row['source']=='Library')
        d=self.document();text=json.dumps(d)
        self.assertNotIn(entry['ship']['name'],text);self.assertNotIn(entry['description'],text)
        for row in d['guide']['artwork']:self.assertEqual(set(row),{'art','source','family'})
        instructions=' '.join(d['guide']['instructions'])
        self.assertIn('independent ship designs',instructions);self.assertIn('newly written shipyard descriptions',instructions)
        self.assertIn('explicitly provide',instructions)
        # The same image can support a design independent of the saved Library ship.
        d['add_ships']=self.additions(1,code)
        d['add_ships'][0].update(name='Coastal Sentinel',hull_strength=83,sailing_power=79,turning=65,
            maximum_guns=70,minimum_sailors=30,crew_capacity=200,total_capacity=700,
            starting_guns=40,starting_crew_spaces=120,price_bars=5.5,description='An armed coastal escort with room for provisions.')
        c=self.candidate(d)
        self.assertEqual(c.ships[25]['name'],'Coastal Sentinel');self.assertEqual(c.ships[25]['max_guns'],70)
        self.assertEqual(c.ships[25]['price_gold'],55000);self.assertEqual(c.ships[25]['base_hull'],10)
        self.assertEqual(c.portrait_raw(25),self.project.portrait_raw(10))
        self.assertEqual(c.ship_descriptions[25],d['add_ships'][0]['description'])
        self.assertEqual(ContentLibrary(self.project.rom).document(),before)
        # Renaming a Library entry does not change its artwork reference or leak the new name.
        entry['ship']['name']='Another Lib Name';library.put(entry)
        self.assertIn(code,{r['art']for r in self.document()['guide']['artwork']})
        self.assertNotIn('Another Lib Name',ai_presets.export(self.project))

    def test_named_goods_items_characters_and_ports(self):
        import trade_goods,item_shops
        from sailors import SKILLS
        d=self.document();guide=d['guide'];port=guide['ports'][0]['port']
        offers=copy.deepcopy(guide['goods'][0]['offers']);offers[0]['economy_required']=100
        slots=copy.deepcopy(guide['items'][0]['slots']);slots[0]=None
        d.update(goods=[dict(port=port,offers=offers)],items=[dict(port=port,slots=slots)],
                 ports=[dict(port=port,goods_economy=700)],characters=[dict(character='C001',leadership=90,skills=[SKILLS[0][1]])])
        c=self.candidate(d)
        self.assertEqual(trade_goods.offers(c.rom,c.goods_edits)[0][0]['economy_required'],100)
        self.assertEqual(item_shops.values(c.rom,c.item_edits)[0][0],255)
        self.assertEqual(c.character_record(0)['skills'],SKILLS[0][2]);self.assertEqual(c.character_record(0)['leadership'],90)

    def test_unknown_ambiguous_invalid_and_stale_inputs_are_atomic(self):
        before=self.project.manifest()
        variations=[dict(edit_ships=[dict(ship='Unknown',price_bars=1)]),dict(add_ships=self.additions(11)),
                    dict(edit_ships=[dict(ship='S01',cargo=10)]),dict(edit_ships=[dict(ship='S01',id=10)]),
                    dict(edit_ships=[dict(ship='S01'),dict(ship='Balsa')]),dict(gameplay=dict(fleet_control=1)),
                    dict(context='changed'),dict(unrecognized=True),dict(characters=[dict(character='C001',skills=['Magic'])])]
        for change in variations:
            with self.subTest(change=change):
                d=self.document();d.update(change)
                with self.assertRaises(ValueError):self.candidate(d)
                self.assertEqual(self.project.manifest(),before)
        self.project.ships[1]['name']='Balsa';d=self.document();d['edit_ships']=[dict(ship='Balsa',price_bars=1)]
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.candidate(d)
        d['edit_ships']=[dict(ship='S01',price_bars=1)];self.assertEqual(self.candidate(d).ships[0]['price_gold'],10000)

    def test_existing_ship_family_cannot_change_accidentally(self):
        d=self.document();d['edit_ships']=[dict(ship='Galleon',art='A01')]
        with self.assertRaisesRegex(ValueError,'matching visual family'):self.candidate(d)

    def test_ai_gun_limit_200_capacity_limit_2000(self):
        d=self.document();self.assertIn('Guns: 0..200',json.dumps(d))
        d['edit_ships']=[dict(ship='Galleon',maximum_guns=200,crew_capacity=500,total_capacity=2000)]
        d['add_ships']=self.additions(1)
        d['add_ships'][0].update(maximum_guns=200,starting_guns=200,crew_capacity=500,total_capacity=2000)
        c=self.candidate(d)
        self.assertEqual(c.ships[10]['max_guns'],200);self.assertEqual(c.ships[25]['factory_guns'],200)
        for key,value in [('maximum_guns',201),('crew_capacity',510),('total_capacity',2001),('starting_guns',201)]:
            bad=copy.deepcopy(d);bad['add_ships'][0][key]=value
            with self.assertRaises(ValueError):self.candidate(bad)

    def test_ai_lower_crew_capacity_trims_original_starting_crew(self):
        before=self.project.manifest()
        for version in (1,2):
            if version==2:
                d=self.document();d['edit_ships']=[dict(ship='Galleon',crew_capacity=10,minimum_sailors=1)]
            else:
                d=dict(format='new-horizons-ai-preset',version=1,base=ai_presets.fingerprint(self.project),name='Crew test',description='',
                       changes=dict(ships=[dict(id=10,crew_capacity=10,minimum_sailors=1)]))
            c=self.candidate(d)
            self.assertEqual(c.ships[10]['factory_crew'],10)
            self.assertEqual(c.ships[10]['factory_cargo'],c.ships[10]['capacity']-c.ships[10]['factory_guns']-10)
            self.assertEqual(self.project.manifest(),before)


if __name__=='__main__':unittest.main()
