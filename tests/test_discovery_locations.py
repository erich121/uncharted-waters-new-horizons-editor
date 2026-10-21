"""Fixed discovery Library targets, conflicts, legacy binding and portability."""
from legacy_manifest import legacy_manifest
import copy
from pathlib import Path
import tempfile
import unittest
from backend import ShipProject
from content_library import ContentLibrary, new_id
from discovery_content import capture, bind, target_slot, prepare_replacements, state, read_state, load


class DiscoveryLocationTests(unittest.TestCase):
    def setUp(self):
        self.p = ShipProject(Path(__file__).resolve().parents[1]/'New Horizons (USA).zip')

    def custom(self, slot):
        entry = capture(self.p, slot)
        entry.update(id=new_id(), name='New site '+str(slot))
        return entry

    def test_alternatives_conflict_without_mutation(self):
        a, b = self.custom(0), self.custom(0)
        before = self.p.manifest()
        with self.assertRaises(ValueError): prepare_replacements(self.p, [a,b])
        self.assertEqual(self.p.manifest(), before)
        with self.assertRaises(ValueError): bind(a,1)
        load(self.p,a,0); load(self.p,b,0)
        self.assertEqual(self.p.discovery_entries[0],b)
        self.assertEqual(self.p.discovery_identities[1:],['stock-discovery:%02d'%i for i in range(1,98)])

    def test_library_and_project_preserve_location_and_content(self):
        entries=[self.custom(0),self.custom(2)]
        with tempfile.TemporaryDirectory() as d:
            lib=ContentLibrary(self.p.rom,Path(d)/'a')
            for e in entries:lib.put(e)
            path=Path(d)/'sites.nhlib';lib.export_file(path)
            other=ContentLibrary(self.p.rom,Path(d)/'b');other.import_file(path)
            self.assertEqual(other.entries,entries)
            trial=prepare_replacements(self.p,other.entries)
            self.assertEqual(set(trial.discovery_entries),{0,2})
            project=Path(d)/'project.json';trial.save_project(project)
            self.p.load_project(project)
            self.assertEqual(self.p.build(),trial.build())

    def test_legacy_entry_binding_and_project_upgrade(self):
        e=self.custom(3);e.pop('replaces');e['version']=1
        self.assertIsNone(target_slot(e))
        with self.assertRaises(ValueError):prepare_replacements(self.p,[e])
        bound=bind(e,3)
        self.assertEqual(bound['replaces'],'stock-discovery:03')
        self.p.discovery_entries[3]=e;self.p.discovery_identities[3]=e['id']
        ids,entries=read_state(state(self.p))
        self.assertEqual(entries[3],bound)
        self.assertEqual(capture(self.p,3),bound)

    def test_existing_library_target_cannot_be_changed_by_update(self):
        with tempfile.TemporaryDirectory() as d:
            lib=ContentLibrary(self.p.rom,d);e=self.custom(0);lib.put(e)
            changed=dict(e,replaces='stock-discovery:01')
            with self.assertRaises(ValueError):lib.put(changed)
            path=Path(d)/'bad.nhlib'
            import json
            path.write_text(json.dumps(dict(format='new-horizons-library',version=1,entries=[changed],collections={})),encoding='utf-8')
            with self.assertRaises(ValueError):lib.import_file(path,replace=True)
            legacy=copy.deepcopy(e);legacy.pop('replaces');legacy['version']=1
            lib.put(legacy)
            self.assertEqual(lib.entries[0]['replaces'],'stock-discovery:00')

    def test_bad_replacement_id(self):
        for value in [None,0,True,'stock-discovery:98','stock-ship:00']:
            e=self.custom(0);e['replaces']=value
            with self.assertRaises(ValueError):prepare_replacements(self.p,[e])

    def test_manual_gate_is_portable_but_not_a_rom_switch(self):
        self.assertFalse(self.p.custom_discoveries)
        old=self.p.manifest();old['version']=28;old.pop('custom_discoveries')
        self.p.load_manifest(legacy_manifest(old));self.assertFalse(self.p.custom_discoveries)
        self.p.custom_discoveries=True
        trial=prepare_replacements(self.p,[self.custom(0)])
        manifest=trial.manifest();self.p.load_manifest(manifest)
        self.assertTrue(self.p.custom_discoveries)
        enabled=self.p.build()
        self.p.custom_discoveries=False
        self.assertEqual(self.p.build(),enabled)
        from custom_presets import prepare
        self.assertTrue(prepare(self.p,manifest).custom_discoveries)
        for value in (1,None,'yes'):
            invalid=copy.deepcopy(manifest);invalid['custom_discoveries']=value
            with self.assertRaises(ValueError):self.p.load_manifest(invalid)

    def test_bulk_archive_rollback(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            lib=ContentLibrary(self.p.rom,d);entry=self.custom(0);lib.put(entry)
            before=copy.deepcopy(lib.entries)
            with patch.object(lib,'save',side_effect=OSError('test failure')):
                with self.assertRaises(OSError):lib.archive_many([self.custom(1)])
            self.assertEqual(lib.entries,before)


if __name__=='__main__':unittest.main()
