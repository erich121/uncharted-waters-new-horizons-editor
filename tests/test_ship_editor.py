"""Verify real stock data, bounded edits and lossless independent IPS exports."""
import json,tempfile,unittest,zipfile,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,read_stock,sha,ROM_SHA,apply_ips,price_from_bars

class ShipEditorTests(unittest.TestCase):
    def setUp(self):
        source=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not source.is_file():self.skipTest('Set NH_STOCK_ROM to your original USA ROM or ZIP.')
        self.p=ShipProject(source)
    def test_stock_roundtrip_exact(self):
        self.assertEqual(len(self.p.ships),25)
        self.assertEqual(self.p.ships[10]['name'],'Galleon')
        self.assertEqual(self.p.ships[16]['max_guns'],150)
        self.assertEqual(self.p.ships[3]['min_crew'],50)
        self.assertEqual(self.p.build(),(self.p.rom,[]))
    def test_edit_and_independent_allowed_bytes(self):
        self.p.update(3,dict(min_crew=30));self.p.update(13,dict(max_guns=60,name='Small Gunner'))
        self.p.update(10,dict(price_gold=150000))
        data,changes=self.p.build();rows=decode(data)
        self.assertEqual(rows[3]['min_crew'],30);self.assertEqual(rows[13]['max_guns'],60)
        self.assertEqual(rows[13]['name'],'Small Gunner');self.assertEqual(rows[10]['price_gold'],150000)
        allowed={0x8ce27+3*12+5,0x8ce27+13*12+8,0x8ce27+10*12+10,0x8ce27+10*12+11}|set(range(0x8cbb6+13*25,0x8cbb6+13*25+18))|set(range(0xffdc,0xffe0))
        self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(self.p.rom,data))))
        self.assertEqual(sum(data)&65535,int.from_bytes(data[0xffde:0xffe0],'little'))
        self.assertEqual(len(changes),4)
    def test_invalid_updates_are_atomic(self):
        old=dict(self.p.ships[13])
        for value in [dict(max_guns=151),dict(max_guns=1),dict(min_crew=70),dict(max_crew=65),dict(name='A'*18),dict(price_gold=320010),dict(price_gold=101),dict(capacity=300),dict(hull=True)]:
            with self.subTest(value=value),self.assertRaises(ValueError):self.p.update(13,value)
            self.assertEqual(self.p.ships[13],old)
    def test_header_zip_projects_exports_and_no_overwrite(self):
        with tempfile.TemporaryDirectory()as folder:
            f=Path(folder);source=f/'Stock.smc';source.write_bytes(b'A'*512+self.p.rom)
            p=ShipProject(source);p.update(3,dict(min_crew=30))
            project=f/'My Mod.json';p.save_project(project)
            second=ShipProject(source);second.load_project(project);self.assertEqual(second.ships,p.ships)
            before=source.read_bytes();out=f/'New Mod.sfc';report=p.export(out)
            self.assertEqual(source.read_bytes(),before);self.assertEqual(len(out.read_bytes()),0x200000)
            self.assertTrue(report['input_header_removed']);self.assertEqual(apply_ips(self.p.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
            with self.assertRaises(ValueError):p.export(out)
            self.assertEqual(source.read_bytes(),before)
            with self.assertRaises(ValueError):p.save_project(f/'Save.srm')
            p.save_project(project);self.assertTrue(project.with_suffix('.json.bak').exists())
            with zipfile.ZipFile(f/'headered.zip','w')as z:z.writestr('nested/game.smc',before)
            self.assertEqual(read_stock(f/'headered.zip')[0],self.p.rom)
    def test_reject_wrong_rom_and_bad_project_without_partial_changes(self):
        with tempfile.TemporaryDirectory()as folder:
            f=Path(folder);modified=bytearray(self.p.rom);modified[0]^=1;wrong=f/'Wrong.sfc';wrong.write_bytes(modified)
            with self.assertRaises(ValueError):ShipProject(wrong)
            previous=[dict(s)for s in self.p.ships]
            m=self.p.manifest();m['edits']=[dict(id=3,field='min_crew',value=30),dict(id=13,field='max_guns',value=999)]
            project=f/'Bad.json';project.write_text(json.dumps(m))
            with self.assertRaises(ValueError):self.p.load_project(project)
            self.assertEqual(self.p.ships,previous)
    def test_price_precision(self):
        self.assertEqual(price_from_bars('0.001'),10);self.assertEqual(price_from_bars('15'),150000)
        for value in ['NaN','Infinity','x','0.00001']:
            with self.assertRaises(ValueError):price_from_bars(value)

if __name__=='__main__':unittest.main()
