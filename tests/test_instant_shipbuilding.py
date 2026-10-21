import json,unittest,tempfile,os
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject
from legacy_manifest import legacy_manifest
import instant_shipbuilding as instant


class InstantShipbuildingTests(unittest.TestCase):
    def setUp(self):self.p=ShipProject(Path(__file__).resolve().parents[1]/'New Horizons (USA).zip')

    def test_only_timer_and_checksum_change(self):
        p=self.p;self.assertFalse(p.instant_shipbuilding);self.assertEqual(p.build()[0],p.rom)
        p.instant_shipbuilding=True;rom=p.build()[0]
        changed={i for i,(x,y)in enumerate(zip(p.rom,rom))if x!=y}
        self.assertEqual(changed-set(range(0xffdc,0xffe0)),{instant.OFFSET})
        p.instant_shipbuilding=False;self.assertEqual(p.build()[0],p.rom)

    def test_snapshots_ai_limits_and_composition(self):
        p=self.p;p.instant_shipbuilding=True
        from custom_presets import prepare
        q=prepare(p,p.manifest());self.assertTrue(q.instant_shipbuilding);self.assertEqual(q.build(),p.build())
        legacy=p.manifest();legacy.pop('custom_discoveries');legacy['version']=27;legacy.pop('instant_shipbuilding');q.load_manifest(legacy_manifest(legacy));self.assertFalse(q.instant_shipbuilding)
        with tempfile.TemporaryDirectory()as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
            import ai_presets
            doc=json.loads(ai_presets.export(q));doc['gameplay']={'instant_shipbuilding':True}
            _,_,q=ai_presets.candidate(q,json.dumps(doc));self.assertTrue(q.instant_shipbuilding)
        q.fifty_year_campaign=True;q.starting_gold=250000;q.discovery_rewrites=True;q.fleet_control=True
        for i in range(10):q.add_ship(10)
        q.build()
        for invalid in (None,1,'yes'):
            with self.assertRaises(ValueError):instant.validate(invalid)


if __name__=='__main__':unittest.main()
