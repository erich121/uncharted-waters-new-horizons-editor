import json
from legacy_manifest import legacy_manifest
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import ShipProject, ips, apply_ips
import campaign_length as campaign


class CampaignLengthTests(unittest.TestCase):
    def setUp(self):
        path=Path(os.environ.get('NH_STOCK_ROM',Path(__file__).resolve().parents[1]/'New Horizons (USA).zip'))
        if not path.exists():self.skipTest('Requires stock USA ROM')
        self.p=ShipProject(path)

    def test_only_deadline_and_checksum_change(self):
        p=self.p
        self.assertFalse(p.fifty_year_campaign)
        self.assertEqual(p.build()[0],p.rom)
        p.fifty_year_campaign=True
        rom=p.build()[0]
        self.assertEqual(len(rom),len(p.rom))
        self.assertEqual(rom[campaign.OFFSET:campaign.OFFSET+3],campaign.EXTENDED)
        differences={i for i,(x,y)in enumerate(zip(p.rom,rom))if x!=y}
        self.assertEqual(differences-{*range(0xffdc,0xffe0)},{campaign.OFFSET+1})
        self.assertEqual(apply_ips(p.rom,ips(p.rom,rom)),rom)
        p.fifty_year_campaign=False
        self.assertEqual(p.build()[0],p.rom)

    def test_project_preset_and_historical_defaults(self):
        p=self.p;p.fifty_year_campaign=True
        from custom_presets import prepare,apply_snapshot,summary
        q=prepare(p,p.manifest())
        self.assertTrue(q.fifty_year_campaign)
        self.assertEqual(q.build(),p.build())
        p.fifty_year_campaign=False
        self.assertIn('50-year campaign: Off → On',summary(p,q))
        apply_snapshot(p,q)
        self.assertTrue(p.fifty_year_campaign)
        for version in (24,25):
            legacy=p.manifest();legacy.pop('custom_discoveries');legacy['version']=version;legacy.pop('fifty_year_campaign');legacy.pop('starting_gold');legacy.pop('instant_shipbuilding')
            if version==24:legacy.pop('discovery_rewrites')
            q.load_manifest(legacy_manifest(legacy))
            self.assertFalse(q.fifty_year_campaign)
        with tempfile.TemporaryDirectory()as d:
            path=Path(d)/'project.json';p.save_project(path);q.load_project(path)
            self.assertTrue(q.fifty_year_campaign)

    def test_ai_and_composition(self):
        p=self.p
        import ai_presets
        with tempfile.TemporaryDirectory()as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
            doc=json.loads(ai_presets.export(p));doc['gameplay']={'fifty_year_campaign':True}
            _,_,q=ai_presets.candidate(p,json.dumps(doc))
            self.assertTrue(q.fifty_year_campaign)
        for i in range(10):q.add_ship(10)
        q.discovery_rewrites=True;q.fleet_control=True;q.repair_safeguard=True
        result=q.build()[0]
        self.assertEqual(result[campaign.OFFSET:campaign.OFFSET+3],campaign.EXTENDED)

    def test_invalid_and_native_guard(self):
        for value in (None,1,'yes',[]):
            with self.assertRaises(ValueError):campaign.validate(value)
            doc=self.p.manifest();doc['fifty_year_campaign']=value
            with self.assertRaises(ValueError):self.p.load_manifest(doc)
        data=bytearray(self.p.rom);data[campaign.OFFSET]=0
        with self.assertRaises(ValueError):campaign.install(data,True)


if __name__=='__main__':unittest.main()
