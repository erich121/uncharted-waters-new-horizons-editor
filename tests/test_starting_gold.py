import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject
from legacy_manifest import legacy_manifest
import starting_gold as gold


class StartingGoldTests(unittest.TestCase):
    def setUp(self):
        self.p=ShipProject(Path(__file__).resolve().parents[1]/'New Horizons (USA).zip')

    def test_limits_and_display(self):
        for bars,value in [('0',0),('0.0001',1),('0.5',5000),('10',100000),('25',250000)]:
            self.assertEqual(gold.from_bars(bars),value)
            self.assertEqual(gold.from_bars(gold.bars(value)),value)
        for value in (-1,250001,True,'5000'):
            with self.assertRaises(ValueError):gold.validate(value)
        for value in ('25.0001','NaN','Infinity','0.00001','-1'):
            with self.assertRaises(ValueError):gold.from_bars(value)

    def test_default_restore_and_composition(self):
        p=self.p;self.assertIsNone(p.starting_gold);self.assertEqual(p.build()[0],p.rom)
        for value in (0,5000,250000):
            p.starting_gold=value;rom=p.build()[0]
            self.assertEqual(len(rom),0x400000)
            self.assertNotEqual(rom[gold.INIT_SITE:gold.INIT_SITE+4],gold.INIT_NATIVE)
        p.starting_gold=None;self.assertEqual(p.build()[0],p.rom)
        p.starting_gold=250000;p.fifty_year_campaign=True;p.discovery_rewrites=True;p.fleet_control=True
        for i in range(10):p.add_ship(10)
        p.build()

    def test_snapshots_ai_and_older_projects(self):
        p=self.p;p.starting_gold=250000
        from custom_presets import prepare,summary
        q=prepare(p,p.manifest());self.assertEqual(q.starting_gold,250000)
        self.assertEqual(q.build(),p.build())
        legacy=p.manifest();legacy.pop('custom_discoveries');legacy['version']=26;legacy.pop('starting_gold');legacy.pop('instant_shipbuilding');q.load_manifest(legacy_manifest(legacy))
        self.assertIsNone(q.starting_gold)
        with tempfile.TemporaryDirectory()as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
            import ai_presets
            doc=json.loads(ai_presets.export(p));doc['gameplay']={'starting_gold':100000}
            _,_,q=ai_presets.candidate(p,json.dumps(doc));self.assertEqual(q.starting_gold,100000)
        for value in (-1,250001,True):
            bad=p.manifest();bad['starting_gold']=value
            with self.assertRaises(ValueError):q.load_manifest(bad)


if __name__=='__main__':unittest.main()
