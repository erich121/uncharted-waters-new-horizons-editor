"""Complete snapshots replace rather than merge; persistence is isolated and atomic."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject,ips,apply_ips
from custom_presets import PresetStore,prepare,apply_snapshot,preset_name


class CustomPresetTests(unittest.TestCase):
    def test_preset_rom_filename_is_windows_safe(self):
        from custom_presets import export_filename
        cases={None:'New Horizons Modified.sfc','':'New Horizons Modified.sfc','Hard Mode':'Hard Mode.sfc',
               "Veteran's Horizon":"Veteran's Horizon.sfc",'Navy: Atlantic/Pacific?':'Navy_ Atlantic_Pacific_.sfc',
               'CON':'_CON.sfc','con.txt':'_con.txt.sfc','CON .txt':'_CON .txt.sfc','COM1':'_COM1.sfc','LPT2':'_LPT2.sfc',
               'My preset.  ':'My preset.sfc','My preset.SFC':'My preset.sfc','..':'New Horizons Modified.sfc',
               'Étoile':'Étoile.sfc'}
        for name,expected in cases.items():
            with self.subTest(name=name):self.assertEqual(export_filename(name),expected)

    def setUp(self):
        source=Path(__file__).resolve().parents[1]/'New Horizons (USA).zip'
        if not source.exists():self.skipTest('Requires stock ROM')
        self.p=ShipProject(source)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=PresetStore(Path(self.temp.name)/'presets.json')

    def test_complete_roundtrip_and_no_stacking(self):
        from content_library import capture_ship,new_id
        from library_project import load_ship
        entry=capture_ship(self.p,10);entry['id']=new_id();entry['ship']['name']='Preset Galleon'
        slot=load_ship(self.p,entry);self.p.fleet_rules[0][0][1]=slot
        self.p.fleet_difficulty=True;self.p.fleet_control=True;self.p.repair_safeguard=True
        self.p.update_character(0,dict(battle_level=77,luck=50))
        from easy_presets import apply
        apply(self.p,'Fresh World','1234',True)
        snapshot=self.p.manifest();expected=self.p.build()[0]
        self.store.save('My world',self.p)
        q=ShipProject(self.p.source);q.project_path=Path(self.temp.name)/'active.json'
        q.custom_ships=True;q.ships[0]['hull']=99
        path=q.project_path;source=q.source
        draft=prepare(q,PresetStore(self.store.path).read()['My world'])
        self.assertNotEqual(q.manifest(),snapshot)
        apply_snapshot(q,draft)
        self.assertEqual(q.manifest(),snapshot);self.assertEqual(q.source,source);self.assertEqual(q.project_path,path)
        self.assertEqual(q.build()[0],expected)
        self.assertEqual(apply_ips(q.rom,ips(q.rom,expected)),expected)
        q.ships[0]['hull']=90;apply_snapshot(q,draft)
        self.assertEqual(q.manifest(),snapshot)

    def test_stock_snapshot_resets_existing_changes(self):
        self.store.save('Stock',self.p)
        baseline=self.p.manifest();self.p.update_character(0,dict(battle_level=100))
        self.p.fleet_control=True;self.p.custom_characters=True;self.p.add_ship(10)
        apply_snapshot(self.p,prepare(self.p,self.store.read()['Stock']))
        self.assertEqual(self.p.manifest(),baseline)

    def test_duplicate_update_and_delete_preserve_other_presets(self):
        self.store.save('One',self.p);self.store.save('Two',self.p)
        before=self.store.path.read_bytes()
        with self.assertRaises(ValueError):self.store.save('one',self.p)
        self.assertEqual(self.store.path.read_bytes(),before)
        self.p.fleet_control=True;self.store.save('ONE',self.p,replace=True)
        self.assertEqual(set(self.store.read()),{'ONE','Two'})
        self.store.delete('ONE');self.assertEqual(set(self.store.read()),{'Two'})
        with self.assertRaises(ValueError):self.store.delete('missing')

    def test_invalid_manifest_does_not_change_live_project(self):
        baseline=self.p.manifest();bad=copy.deepcopy(baseline);bad['character_edits']=[dict(id=0,field='battle_level',value=101)]
        with self.assertRaises(ValueError):prepare(self.p,bad)
        self.assertEqual(self.p.manifest(),baseline)
        bad=copy.deepcopy(baseline);bad['gameplay']['fleet_rules'][0][0][1]=99
        with self.assertRaises(ValueError):prepare(self.p,bad)
        self.assertEqual(self.p.manifest(),baseline)

    def test_corrupt_storage_never_overwritten(self):
        for content in ('{','[]','{"format":"wrong","version":1,"presets":{}}'):
            self.store.path.write_text(content)
            with self.assertRaises(ValueError):self.store.save('One',self.p)
            self.assertEqual(self.store.path.read_text(),content)

    def test_atomic_write_failure_keeps_previous_file(self):
        self.store.save('One',self.p);before=self.store.path.read_bytes()
        with patch('custom_presets.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):self.store.save('Two',self.p)
        self.assertEqual(self.store.path.read_bytes(),before)
        self.assertEqual({p.name for p in self.store.path.parent.iterdir()},{self.store.path.name,self.store.path.name+'.lock'})

    def test_names_are_data_not_paths(self):
        for name in ('','   ','x'*61,'bad\nname',None):
            with self.assertRaises(ValueError):preset_name(name)
        self.store.save('../A name',self.p)
        self.assertIn('../A name',self.store.read())
        self.assertEqual({p.name for p in self.store.path.parent.iterdir()},{self.store.path.name,self.store.path.name+'.lock'})

    def test_manifest_loading_keeps_project_path(self):
        self.p.project_path=Path(self.temp.name)/'existing.json'
        self.p.load_manifest(self.p.manifest())
        self.assertEqual(self.p.project_path,Path(self.temp.name)/'existing.json')

    def test_provided_presets_replace_complete_state(self):
        from custom_presets import starter
        from app_defaults import provided_names
        PRESETS=provided_names()
        clean=self.p.manifest();self.p.fleet_control=True;self.p.add_ship(10)
        self.p.update_character(0,dict(battle_level=99));before=self.p.manifest()
        for name in PRESETS:
            candidate=starter(self.p,name,'2026',True)
            self.assertEqual(self.p.manifest(),before)
            self.assertEqual(candidate.manifest(),starter(ShipProject(self.p.source),name,'2026',True).manifest())

    def test_deleting_all_provided_persists_and_preserves_saved(self):
        from app_defaults import provided_names
        PRESETS=provided_names()
        self.store.save('My setup',self.p)
        for name in PRESETS:self.store.delete(name,provided=True)
        reopened=PresetStore(self.store.path)
        self.assertEqual(set(reopened.deleted()),set(PRESETS))
        self.assertEqual(set(reopened.read()),{'My setup'})
        self.store.save('Another',self.p);self.assertEqual(set(self.store.deleted()),set(PRESETS))

    def test_updated_provided_preset_does_not_resurrect_after_delete(self):
        self.p.fleet_control=True;self.store.save('Classic Plus',self.p,replace=True)
        self.store.delete('Classic Plus')
        self.assertIn('Classic Plus',PresetStore(self.store.path).deleted())
        self.assertNotIn('Classic Plus',self.store.read())

    def test_earlier_preset_file_migrates_without_losing_data(self):
        old=dict(format='new-horizons-custom-presets',version=1,presets={'My setup':self.p.manifest()})
        self.store.path.write_text(json.dumps(old),encoding='utf-8')
        self.assertEqual(self.store.deleted(),[])
        self.store.delete('Trade & Exploration',provided=True)
        saved=json.loads(self.store.path.read_text(encoding='utf-8'))
        self.assertEqual(saved['version'],3)
        self.assertEqual(saved['presets'],old['presets'])

    def test_restore_provided_preserves_other_snapshots_and_current_edits(self):
        self.p.fleet_control=True;before=self.p.manifest()
        self.store.save('My setup',self.p);self.store.save('Classic Plus',self.p)
        self.store.delete('Trade & Exploration',provided=True)
        self.store.restore_provided()
        self.assertEqual(self.store.deleted(),[])
        self.assertEqual(self.store.read(),{'My setup':before})
        self.assertEqual(self.p.manifest(),before)

    def test_descriptions_update_persist_and_delete(self):
        self.store.save('My setup',self.p,description_text='Trade game\nMy notes')
        self.assertEqual(PresetStore(self.store.path).descriptions()['My setup'],'Trade game\nMy notes')
        self.store.save('My setup',self.p,replace=True,description_text='Changed notes')
        self.assertEqual(self.store.descriptions()['My setup'],'Changed notes')
        self.store.save('My setup',self.p,replace=True)
        self.assertEqual(self.store.descriptions()['My setup'],'Changed notes')
        self.store.delete('My setup');self.assertEqual(self.store.descriptions(),{})

    def test_v2_metadata_migration_and_invalid_description_atomic(self):
        old=dict(format='new-horizons-custom-presets',version=2,presets={'Old':self.p.manifest()},deleted=['Hard Mode'])
        self.store.path.write_text(json.dumps(old),encoding='utf-8')
        self.assertEqual(self.store.descriptions(),{})
        previous=self.store.path.read_bytes()
        for invalid in ('x'*2001,42,'bad\x00description'):
            with self.assertRaises(ValueError):self.store.save('Old',self.p,replace=True,description_text=invalid)
            self.assertEqual(self.store.path.read_bytes(),previous)
        self.store.save('Old',self.p,replace=True,description_text='Now editable')
        self.assertEqual(self.store.deleted(),['Hard Mode'])

    def test_summary_has_only_actual_changes(self):
        from custom_presets import summary
        q=copy.deepcopy(self.p)
        self.assertEqual(summary(self.p,q),['No settings will change.'])
        q.ships[0]['hull']=99
        self.assertEqual(summary(self.p,q),['Ship 01 Balsa / Hull strength: 30 → 99'])
        q.update_character(0,dict(battle_level=75))
        lines=summary(self.p,q)
        self.assertTrue(any('Battle level' in line and '75'in line for line in lines))
        self.assertFalse(any('already matches'in line or 'Complete snapshot'in line for line in lines))

    def test_blind_summary_hides_destinations_and_seeds(self):
        from custom_presets import summary
        q=copy.deepcopy(self.p);q.set_item_shuffle('9123',True,True)
        q.set_goods_shuffle('9123','all',True)
        text='\n'.join(summary(self.p,q))
        self.assertIn('(blind)',text);self.assertNotIn('9123',text)
        from ports import PORT_NAMES
        self.assertFalse(any(name in text for name in PORT_NAMES))
