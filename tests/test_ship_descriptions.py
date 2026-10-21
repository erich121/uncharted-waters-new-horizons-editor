import copy
from legacy_manifest import legacy_manifest
import json
import os
from pathlib import Path
import tempfile
import unittest
from backend import ShipProject,apply_ips,ips
from content_library import ContentLibrary,capture_ship,new_id,validate_ship
from library_project import load_ship
import ship_descriptions as sd


class DescriptionTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',Path(__file__).resolve().parents[1]/'New Horizons (USA).zip'))
        if not path.exists():self.skipTest('Requires the stock ROM.')
        self.p=ShipProject(path)

    def test_stock_text_and_unmodified_rom(self):
        self.assertIn('high-performance',sd.text(self.p,13))
        self.assertEqual(len([sd.text(self.p,i)for i in range(25)]),25)
        self.assertEqual(self.p.build(),(self.p.rom,[]))
        sd.set_text(self.p,10,sd.text(self.p,10));self.assertFalse(self.p.ship_descriptions)

    def test_independent_text_same_family_and_preserved_messages(self):
        i=self.p.add_ship(10);j=self.p.add_ship(10)
        sd.set_text(self.p,i,'A fast ocean trader.')
        sd.set_text(self.p,j,'A heavy warship.')
        result=self.p.build()[0]
        self.assertEqual(result[sd.TABLE:sd.TABLE+468*3],self.p.rom[sd.SECONDARY:sd.SECONDARY+468*3])
        self.assertEqual(result[sd.PRIMARY:sd.PRIMARY+900*3],self.p.rom[sd.PRIMARY:sd.PRIMARY+900*3])
        for slot,expected in [(i,'A fast ocean trader.'),(j,'A heavy warship.')]:
            mid=int.from_bytes(result[0x200c00+slot*2:0x200c02+slot*2],'little')
            self.assertEqual(mid,sd.FIRST_ID+slot)
            at=int.from_bytes(result[sd.TABLE+(mid-900)*3:sd.TABLE+(mid-900)*3+3],'little')-0xc00000
            self.assertEqual(result[at:result.index(b'\0',at)].decode('ascii'),expected)
        self.assertEqual(apply_ips(self.p.rom,ips(self.p.rom,result)),result)

    def test_invalid_text_and_hostile_states(self):
        for text in ('',' ','x'*227,'100% capacity','line\nline','é','\0'):
            with self.assertRaises(ValueError):sd.set_text(self.p,0,text)
        for rows in ([dict(id=True,text='Ship')],[dict(id=25,text='Ship')],[dict(id=0,text='Ship')]*2):
            with self.assertRaises(ValueError):sd.read_state(rows,25)
        sd.set_text(self.p,0,'x'*226);self.p.build()

    def test_library_portable_projects_and_swaps(self):
        sd.set_text(self.p,10,'My custom trader.')
        entry=capture_ship(self.p,10);entry['id']=new_id()
        self.assertEqual(entry['version'],3)
        with tempfile.TemporaryDirectory()as folder:
            folder=Path(folder);library=ContentLibrary(self.p.rom,folder/'lib');library.put(entry)
            library.export_file(folder/'ships.nhlib',[entry['id']])
            shared,_=library.read(folder/'ships.nhlib')
            q=ShipProject(self.p.source);i=load_ship(q,shared[0]);self.assertEqual(sd.text(q,i),'My custom trader.')
            load_ship(q,shared[0],13,replace_fleet=True)
            self.assertEqual(sd.text(q,13),'My custom trader.')
            q.save_project(folder/'project.json');r=ShipProject(self.p.source);r.load_project(folder/'project.json')
            self.assertEqual(r.build(),q.build());self.assertEqual(sd.text(r,13),'My custom trader.')

    def test_v1_v2_library_and_v21_project_defaults(self):
        for version in (1,2):
            entry=capture_ship(self.p,10);entry['version']=version;entry.pop('description')
            if version==1:entry.pop('availability')
            validate_ship(entry,self.p.rom)
            q=ShipProject(self.p.source);i=load_ship(q,entry,13)
            self.assertEqual(sd.text(q,i),sd.stock_text(q.rom,10))
        with tempfile.TemporaryDirectory()as folder:
            old=self.p.manifest();old['version']=21;old.pop('ship_descriptions');old.pop('custom_characters')
            path=Path(folder)/'old.json';path.write_text(json.dumps(legacy_manifest(old)))
            self.p.load_project(path);self.assertEqual(self.p.ship_descriptions,{})

    def test_removal_renumbers_text_with_ship(self):
        for _ in range(10):self.p.add_ship(10)
        sd.set_text(self.p,25,'First');sd.set_text(self.p,34,'Last')
        self.p.remove_ship(25)
        self.assertEqual(self.p.ship_descriptions,{33:'Last'})

    def test_storage_collision_rejected(self):
        sd.set_text(self.p,0,'Safe ship')
        data=bytearray(self.p.rom)+bytearray(b'\xff'*0x200000)
        data[sd.TABLE]=0
        with self.assertRaisesRegex(ValueError,'overlaps'):sd.install(data,self.p)
