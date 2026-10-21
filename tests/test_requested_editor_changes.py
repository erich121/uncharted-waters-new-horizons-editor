"""Discovery resets, native fields and project/preset round trips."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,MODEL_BASE
import discovery_content as dc
from discoveries import BASE
from item_prices import validate,price

class RequestedChangesTests(unittest.TestCase):
    def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')

    def test_native_item_prices_difficulty_and_starting_fit(self):
        p=self.p
        p.item_price_edits=validate(p.rom,[dict(id=0,price_gold=3276700)])
        p.discovery_easy=True
        p.update(0,dict(factory_guns=6,factory_crew=14))
        data=p.build()[0]
        self.assertEqual(int.from_bytes(data[0x8ebda:0x8ebdc],'little'),32767)
        self.assertEqual(data[MODEL_BASE+20],6)
        self.assertEqual(int.from_bytes(data[MODEL_BASE+21:MODEL_BASE+23],'little'),14)
        for slot in range(98):
            self.assertEqual(data[BASE+slot*7+5],10)
            self.assertEqual(data[BASE+slot*7:BASE+slot*7+5],p.rom[BASE+slot*7:BASE+slot*7+5])
        from custom_presets import prepare
        q=prepare(p,p.manifest())
        self.assertEqual(q.build(),p.build())
        self.assertEqual(price(q,0),3276700)
        before=p.manifest()
        for edits in ([dict(id=0,price_gold=101)],[dict(id=0,price_gold=3276800)],[dict(id=99,price_gold=100)]):
            with self.assertRaises(ValueError):validate(p.rom,edits)
        self.assertEqual(p.manifest(),before)

    def test_v29_migration_and_invalid_new_state_atomic(self):
        m=self.p.manifest();m['version']=29
        m.pop('item_price_edits');m.pop('discovery_easy')
        self.p.load_manifest(m)
        self.assertFalse(self.p.discovery_easy);self.assertEqual(self.p.item_price_edits,[])
        before=self.p.manifest()
        m=self.p.manifest();m['discovery_easy']=1
        with self.assertRaises(ValueError):self.p.load_manifest(m)
        self.assertEqual(self.p.manifest(),before)

    def test_stock_equivalent_capture_is_not_a_change(self):
        from content_library import new_id
        entry=dc.capture(self.p,0);entry['id']=new_id()
        dc.load(self.p,entry,0)
        self.assertEqual(dc.changed_slots(self.p),set())
        self.p.discovery_entries[0]['description']='A different story.'
        self.assertEqual(dc.changed_slots(self.p),{0})

    def test_builtin_presets_do_not_invent_discovery_changes(self):
        import easy_presets
        for name in easy_presets.PRESETS:
            p=ShipProject(self.p.source)
            easy_presets.apply(p,name,seed='1234')
            self.assertFalse(dc.changed_slots(p),name)

    def test_native_rank_bands(self):
        from items import weapon_rank
        self.assertEqual(weapon_rank(self.p.rom,0),'D')
        self.assertEqual(weapon_rank(self.p.rom,2),'B')
        self.assertEqual(weapon_rank(self.p.rom,11),'\u2605')
        self.assertIsNone(weapon_rank(self.p.rom,16))

    def test_checkbox_locks_editing_without_discarding_loaded_content(self):
        import tkinter as tk
        from app import Editor
        from content_library import new_id
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
            root=tk.Tk();root.withdraw()
            try:
                app=Editor(root);app.project=self.p;app.selected=0
                entry=dc.capture(self.p,0);entry.update(id=new_id(),name='Custom test')
                dc.load(self.p,entry,0)
                self.p.custom_discoveries=True;self.p.discovery_easy=True;self.p.discovery_rewrites=True
                before=self.p.build()[0]
                app.discoveries.custom.set(False);app.discoveries.toggle()
                self.assertTrue(self.p.discovery_entries)
                self.assertFalse(self.p.custom_discoveries)
                self.assertTrue(self.p.discovery_rewrites)
                self.assertTrue(self.p.discovery_easy)
                self.assertEqual(self.p.build()[0],before)
                self.assertEqual(self.p.discovery_entries[0]['id'],entry['id'])
            finally:root.destroy()

if __name__=='__main__':unittest.main()
