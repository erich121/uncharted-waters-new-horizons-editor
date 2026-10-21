"""AI translation, atomic validation and saved-preset UI workflows."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
import ai_presets


class AIPresetTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        environment=patch.dict(os.environ,LOCALAPPDATA=temporary.name);environment.start();self.addCleanup(environment.stop)
        rom=Path(os.environ.get('NH_STOCK_ROM',ROOT/'New Horizons (USA).zip'))
        if not rom.exists():self.skipTest('Requires stock USA ROM')
        self.p=ShipProject(rom)

    def response(self,changes):
        return json.dumps(dict(format='new-horizons-ai-preset',version=1,base=ai_presets.fingerprint(self.p),name='AI Test',description='A translated preset.',changes=changes))

    def new_ships(self,count):
        from backend import ports
        room=[port['id']for port in ports(self.p.rom)if port['group']<11 for _ in range(16-sum(port['id']in offer['ports']for offer in self.p.all_offers()))]
        return [dict(id=len(self.p.ships)+i,name=f'AI Ship {i+1}',visual_family=10,build_ports=[room[i]],industry_required=0,shipyard_description=f'A new ocean vessel number {i+1}.')for i in range(count)]

    def test_ten_new_ships_save_load_export_and_review(self):
        from custom_presets import PresetStore,prepare,summary
        from backend import apply_ips
        before=copy.deepcopy(self.p.manifest());rows=self.new_ships(10)
        rules=copy.deepcopy(self.p.fleet_rules);rules[0][0][0]=34
        name,notes,c=ai_presets.candidate(self.p,self.response(dict(new_ships=rows,gameplay=dict(custom_fleets=True,fleet_rules=rules))))
        self.assertEqual(len(c.ships),35);self.assertEqual(c.ships[:25],self.p.ships)
        self.assertEqual(len(set(c.ship_identities)),35)
        self.assertEqual(c.fleet_rules[0][0][0],34)
        self.assertIn('A new ocean vessel number 10.', '\n'.join(summary(self.p,c)))
        self.assertEqual(c.portrait_raw(34),self.p.portrait_raw(10))
        with tempfile.TemporaryDirectory()as folder:
            store=PresetStore(Path(folder)/'presets.json');store.save(name,c,description_text=notes)
            loaded=prepare(self.p,store.read()[name]);self.assertEqual(loaded.manifest(),c.manifest())
            target=Path(folder)/'Ships.sfc';loaded.export(target)
            self.assertEqual(apply_ips(self.p.rom,target.with_suffix('.ips').read_bytes()),target.read_bytes())
        self.assertEqual(self.p.manifest(),before)

    def test_remaining_slots_count_existing_additions(self):
        for _ in range(4):self.p.add_ship(0)
        guide=json.loads(ai_presets.export_legacy(self.p));self.assertEqual(guide['ship_capacity']['remaining_slots'],6)
        old=copy.deepcopy(self.p.ships)
        _,_,c=ai_presets.candidate(self.p,self.response(dict(new_ships=self.new_ships(6))))
        self.assertEqual(c.ships[:29],old);self.assertEqual(len(c.ships),35)
        with self.assertRaisesRegex(ValueError,'At most 6'):ai_presets.candidate(self.p,self.response(dict(new_ships=self.new_ships(7))))

    def test_invalid_new_ships_are_rejected_atomically(self):
        before=self.p.manifest()
        variations=[dict(id=26),dict(visual_family=25),dict(visual_family=True),dict(build_ports=[]),dict(build_ports=[999]),dict(industry_required=11),dict(crew_capacity=999),dict(price_gold_bars=33),dict(portrait='not supported')]
        for changes in variations:
            rows=self.new_ships(2);rows[1].update(changes)
            # A duplicate existing/preceding ID is also forbidden.
            if changes==dict(id=26):rows[1]['id']=25
            with self.subTest(changes=changes),self.assertRaises(ValueError):ai_presets.candidate(self.p,self.response(dict(new_ships=rows)))
            self.assertEqual(self.p.manifest(),before)
        with self.assertRaises(ValueError):ai_presets.candidate(self.p,self.response(dict(new_ships=self.new_ships(11))))

    def test_new_ship_port_capacity_and_fixed_capital_limits(self):
        from backend import ports
        port=next(p['id']for p in ports(self.p.rom)if not p['capital']and p['group']<11 and sum(p['id']in o['ports']for o in self.p.all_offers())>=7)
        count=17-sum(port in o['ports']for o in self.p.all_offers());rows=self.new_ships(count)
        for row in rows:row['build_ports']=[port]
        with self.assertRaisesRegex(ValueError,'16-ship'):ai_presets.candidate(self.p,self.response(dict(new_ships=rows)))
        row=self.new_ships(1)[0];row.update(build_ports=[0],industry_required=1000)
        with self.assertRaisesRegex(ValueError,'cannot reach'):ai_presets.candidate(self.p,self.response(dict(new_ships=[row])))

    def test_new_ship_can_embed_library_artwork_without_exporting_pixels(self):
        from content_library import ContentLibrary,capture_ship
        from custom_presets import PresetStore,prepare
        import portraits
        raw=portraits.encode_tiles([(i*7+i//64)%16 for i in range(3072)])
        self.p.set_portrait(10,raw)
        entry=capture_ship(self.p,10);store=ContentLibrary(self.p.rom);store.put(entry)
        guide=json.loads(ai_presets.export_legacy(self.p));reference=guide['reference']['library_artwork'][0]
        self.assertEqual(reference['library_ship_id'],entry['id'])
        self.assertNotIn(entry['portrait'],json.dumps(guide))
        row=self.new_ships(1)[0];del row['visual_family']
        row.update({key:reference[key]for key in ('library_ship_id','library_art_hash')})
        name,notes,c=ai_presets.candidate(self.p,self.response(dict(new_ships=[row])))
        self.assertEqual(c.portrait_raw(25),raw);self.assertEqual(c.ships[25]['base_hull'],10)
        presets=PresetStore();presets.save(name,c,description_text=notes)
        store.clear()
        loaded=prepare(self.p,presets.read()[name]);self.assertEqual(loaded.portrait_raw(25),raw)
        with self.assertRaisesRegex(ValueError,'missing'):ai_presets.candidate(self.p,self.response(dict(new_ships=[row])))

    def test_changed_library_artwork_or_wrong_family_is_rejected(self):
        from content_library import ContentLibrary,capture_ship,new_id
        import portraits
        entry=capture_ship(self.p,10);entry['id']=new_id();store=ContentLibrary(self.p.rom);store.put(entry)
        reference=json.loads(ai_presets.export_legacy(self.p))['reference']['library_artwork'][0]
        row=self.new_ships(1)[0];row.update({key:reference[key]for key in ('library_ship_id','library_art_hash')})
        wrong=copy.deepcopy(row);wrong['visual_family']=6
        with self.assertRaisesRegex(ValueError,'must match'):ai_presets.candidate(self.p,self.response(dict(new_ships=[wrong])))
        entry['portrait']=portraits.pack({0:portraits.encode_tiles([i%16 for i in range(3072)])})[0]['tiles'];store.put(entry)
        with self.assertRaisesRegex(ValueError,'artwork changed'):ai_presets.candidate(self.p,self.response(dict(new_ships=[row])))

    def test_optional_encoded_images_are_valid_pngs(self):
        import base64,io
        from PIL import Image
        from content_library import ContentLibrary,capture_ship
        import portraits
        entry=capture_ship(self.p,10);ContentLibrary(self.p.rom).put(entry)
        ordinary=json.loads(ai_presets.export_legacy(self.p))['reference']['library_artwork'][0]
        self.assertNotIn('image_png_base64',ordinary)
        encoded=json.loads(ai_presets.export_legacy(self.p,True))['reference']['library_artwork'][0]
        image=Image.open(io.BytesIO(base64.b64decode(encoded['image_png_base64'],validate=True)))
        self.assertEqual(image.size,(64,48))
        self.assertEqual(image.convert('RGB').tobytes(),portraits.image(self.p.portrait_raw(10),self.p.rom).tobytes())

    def test_readable_export_has_references_without_art_or_paths(self):
        text=ai_presets.export_legacy(self.p);data=json.loads(text)
        self.assertNotIn(str(self.p.source),text)
        self.assertNotIn('portraits',data['current'])
        self.assertEqual(data['current']['ships'][10]['price_gold_bars'],6)
        self.assertEqual(data['reference']['stock_ships'][10]['id'],10)
        self.assertEqual(len(data['reference']['ports']),100)
        self.assertEqual(ai_presets.candidate(self.p,json.dumps(data['response_template']))[2].manifest(),self.p.manifest())

    def test_translation_and_preset_roundtrip_preserve_current_setup(self):
        from custom_presets import PresetStore,prepare
        before=copy.deepcopy(self.p.manifest())
        name,notes,c=ai_presets.candidate(self.p,self.response(dict(ships=[dict(id=10,price_gold_bars=7.5,maximum_guns=80)],characters=[dict(id=0,leadership=90)],ports=[dict(id=31,goods_economy=700)],gameplay=dict(repair_safeguard=True))))
        self.assertEqual(c.ships[10]['price_gold'],75000)
        self.assertEqual(c.ships[10]['max_guns'],80)
        self.assertEqual(c.character_record(0)['leadership'],90)
        self.assertEqual(self.p.manifest(),before)
        with tempfile.TemporaryDirectory()as folder:
            store=PresetStore(Path(folder)/'presets.json');store.save(name,c,description_text=notes)
            loaded=prepare(self.p,store.read()[name]);self.assertEqual(loaded.manifest(),c.manifest())
        self.assertEqual(self.p.manifest(),before)

    def test_invalid_and_unknown_changes_never_touch_project(self):
        before=self.p.manifest()
        for changes in ({'ships':[{'id':10,'maximum_guns':999}]},{'ships':[{'id':0,'starting_guns':4}]},{'ships':[{'id':10,'id2':11}]},{'ships':[{'id':10},{'id':10}]},{'gameplay':{'fleet_control':1}},{'portraits':[]},{'characters':[{'id':0,'name':'Rewrite'}]},{'ports':[{'id':31,'goods_economy':0}]},{'ships':[{'id':10,'price_gold_bars':0.0001}]}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):ai_presets.candidate(self.p,self.response(changes))
            self.assertEqual(self.p.manifest(),before)

    def test_stale_response_and_duplicate_json_rejected(self):
        text=self.response({});self.p.update(10,dict(hull=79))
        with self.assertRaisesRegex(ValueError,'different settings'):ai_presets.candidate(self.p,text)
        with self.assertRaisesRegex(ValueError,'Duplicate'):ai_presets.parse('{"name":"A","name":"B"}')
        with self.assertRaises(ValueError):ai_presets.parse('{"value":NaN}')
        with self.assertRaises(ValueError):ai_presets.parse('x'*(ai_presets.MAX_TEXT+1))

    def test_fenced_response_and_calculated_cargo(self):
        _,_,c=ai_presets.candidate(self.p,'```json\n'+self.response({'ships':[{'id':10,'total_capacity':850}]})+'\n```')
        self.assertEqual(c.ships[10]['factory_cargo'],850-c.ships[10]['factory_guns']-c.ships[10]['factory_crew'])

    def test_randomizers_validate_and_are_reproducible(self):
        changes=dict(randomizers=dict(people=dict(seed='0123',mate_stats=True,stat_budget=True),goods=dict(seed='0123',mode='all'),items=dict(seed='0123',mode='all'),shipbuilding=dict(seed='0123')),gameplay=dict(fleet_control=True))
        first=ai_presets.candidate(self.p,self.response(changes))[2]
        second=ai_presets.candidate(self.p,self.response(changes))[2]
        self.assertEqual(first.manifest(),second.manifest())
        self.assertEqual(first.free_agent_shuffle['seed'],'0123')
        with self.assertRaises(ValueError):ai_presets.candidate(self.p,self.response(dict(randomizers=dict(goods=dict(seed='123')))))

    def test_artwork_and_library_are_preserved_locally(self):
        import portraits
        raw=portraits.encode_tiles([i%16 for i in range(3072)])
        self.p.set_portrait(10,raw)
        _,_,c=ai_presets.candidate(self.p,self.response({'ships':[{'id':10,'hull_strength':81}]}))
        self.assertEqual(c.portrait_raw(10),raw)
        self.assertEqual(c.manifest()['library_state'],self.p.manifest()['library_state'])

    def test_port_markets_items_and_description_translate_without_resetting_others(self):
        import trade_goods,item_shops
        offers=trade_goods.offers(self.p.rom,[])[0];offers[0]['economy_required']=100
        slots=item_shops.values(self.p.rom,[])[0];slots[0]=255
        changes=dict(goods=[dict(port=0,offers=offers)],items=[dict(port=0,slots=slots)],descriptions=[dict(id=10,text='A capable ship for naval patrols.')])
        _,_,c=ai_presets.candidate(self.p,self.response(changes))
        self.assertEqual(trade_goods.offers(c.rom,c.goods_edits)[0],offers)
        self.assertEqual(item_shops.values(c.rom,c.item_edits)[0],slots)
        self.assertEqual(c.ship_descriptions[10],changes['descriptions'][0]['text'])
        self.assertEqual(trade_goods.offers(c.rom,c.goods_edits)[1:],trade_goods.offers(self.p.rom,[])[1:])

    def test_added_ship_fittings_and_companion_skill_restrictions(self):
        self.p.add_ship()
        _,_,c=ai_presets.candidate(self.p,self.response(dict(ships=[dict(id=25,total_capacity=900,starting_guns=60,starting_crew_spaces=180)])))
        self.assertEqual(c.ships[25]['factory_cargo'],660)
        self.assertEqual(len(c.ships),len(self.p.ships))
        from sailors import decode_sailors
        companion=next(r for r in decode_sailors(self.p.rom)if 69<=r['id']<79 and r['skills']&31)
        with self.assertRaises(ValueError):ai_presets.candidate(self.p,self.response(dict(characters=[dict(id=companion['id'],skills=0)])))

    def test_ui_import_saves_preset_without_applying_and_loads_normally(self):
        from app import Editor
        from ai_preset_view import exchange
        from custom_presets import PresetStore,prepare
        root=tk.Tk()
        errors=[]
        try:
            with tempfile.TemporaryDirectory()as folder,patch.dict(os.environ,LOCALAPPDATA=folder),patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('tkinter.messagebox.askyesno',return_value=True):
                app=Editor(root);root.geometry('1440x900+0+0');root.update()
                self.assertTrue(app.ai_export_button.instate(['disabled']))
                app.load_rom(self.p.source);root.update();before=copy.deepcopy(app.project.manifest())
                self.assertTrue(app.ai_export_button.instate(['!disabled']))
                exchange(app,False);root.update();app.ai_exchange_buttons['Copy for AI'].invoke()
                exported=json.loads(root.clipboard_get());app.ai_exchange_dialog.destroy()
                response=exported;response.update(name='AI Saved',description='Price test',edit_ships=[dict(ship='Galleon',price_bars=7.5)]);response.pop('guide')
                exchange(app,True);root.update();app.ai_exchange_text.insert('1.0',json.dumps(response));app.ai_exchange_buttons['Review preset'].invoke();root.update()
                self.assertIn('75000',app.ai_review_text.get('1.0','end'))
                app.ai_review_cancel.invoke();root.update();self.assertFalse(PresetStore().read())
                app.ai_exchange_buttons['Review preset'].invoke();root.update();app.ai_review_save.invoke();root.update()
                self.assertEqual(app.project.manifest(),before)
                saved=prepare(app.project,PresetStore().read()['AI Saved']);self.assertEqual(saved.ships[10]['price_gold'],75000)
                app.custom_preset_name.set('AI Saved');app.custom_preset_choice.event_generate('<<ComboboxSelected>>');root.update()
                self.assertEqual(app.project.ships[10]['price_gold'],75000)
                self.assertFalse(errors,errors)
        finally:
            for callback in root.tk.call('after','info'):root.after_cancel(callback)
            root.destroy()
