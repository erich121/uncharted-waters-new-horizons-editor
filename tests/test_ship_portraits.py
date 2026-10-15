"""Portrait conversion, portable projects and exact exported graphics."""
import os,sys,tempfile,json,unittest,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import ShipProject,decode,apply_ips
from PIL import Image
import portraits as art

class PortraitTests(unittest.TestCase):
    def setUp(self):
        source=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not source.is_file():self.skipTest('Set NH_STOCK_ROM to the original USA ROM.')
        self.p=ShipProject(source);self.p.repair_safeguard=False
        self.raw=art.encode_tiles([(i*7+i//64)%16 for i in range(3072)])
    def test_originals_decode_roundtrip(self):
        for i in range(25):
            raw=self.p.portrait_raw(i);self.assertEqual(len(raw),1536)
            self.assertEqual(art.encode_tiles(art.decode_tiles(raw)),raw)
            self.assertEqual(art.Decoder(self.p.rom+art.literal_stream(raw)).decode(len(self.p.rom),1536),raw)
    def test_png_conversion_matches_preview(self):
        with tempfile.TemporaryDirectory()as f:
            source=Path(f)/'portrait.png';art.image(self.raw,self.p.rom,5).save(source)
            raw,size=art.convert_png(source,self.p.rom)
            self.assertEqual(size,(320,240));self.assertEqual(raw,self.raw)
            self.assertEqual(art.image(raw,self.p.rom).size,(64,48))
    def test_transparency_and_invalid_file(self):
        with tempfile.TemporaryDirectory()as f:
            source=Path(f)/'alpha.png';Image.new('RGBA',(64,48),(255,0,0,0)).save(source)
            raw,_=art.convert_png(source,self.p.rom);self.assertEqual(art.decode_tiles(raw),[0]*3072)
            Image.new('RGB',(64,48)).save(source,format='JPEG')
            with self.assertRaises(ValueError):art.convert_png(source,self.p.rom)
            source.write_bytes(b'not png')
            with self.assertRaises(OSError):art.convert_png(source,self.p.rom)
            self.assertEqual(self.p.portraits,{})
    def test_original_pointer_scope_and_restore(self):
        self.p.set_portrait(10,self.raw);rom,_=self.p.build()
        self.assertEqual(decode(rom),self.p.original)
        self.assertEqual(art.original_raw(rom,10),self.raw)
        allowed=set(range(0x2BAA4+30,0x2BAA7+30))|set(range(0xFFDC,0xFFE0))|{0xFFD7}
        self.assertTrue(all(i in allowed for i in range(len(self.p.rom))if rom[i]!=self.p.rom[i]))
        self.assertEqual(rom[0x13C0C:0x13D20],self.p.rom[0x13C0C:0x13D20])
        self.p.restore_portrait(10);self.assertEqual(self.p.build()[0],self.p.rom)
    def test_each_added_slot_independent(self):
        self.p.set_portrait(10,self.raw)
        for n in range(5):
            i=self.p.add_ship(10);raw=bytes((b+n+1)%256 for b in self.raw);self.p.set_portrait(i,raw)
            rom,_=self.p.build()
            for j in range(n+1):
                at=int.from_bytes(rom[0x211200+j*3:0x211203+j*3],'little')-0xC00000
                self.assertEqual(at,art.SLOTS+(25+j)*4096)
                self.assertEqual(art.Decoder(rom).decode(at,1536),self.p.portraits[25+j])
            self.assertEqual(art.original_raw(rom,10),self.raw)
            self.assertEqual(rom[0x2B6C9:0x2B6E2],self.p.rom[0x2B6C9:0x2B6E2])
    def test_remove_renumbers_and_clone_uses_stock_art(self):
        for _ in range(3):self.p.add_ship(10)
        self.p.set_portrait(10,self.raw);self.p.set_portrait(26,self.raw);self.p.set_portrait(27,self.raw[::-1])
        self.p.remove_ship(26)
        self.assertEqual(set(self.p.portraits),{10,26});self.assertEqual(self.p.portraits[26],self.raw[::-1])
        self.assertEqual(self.p.portrait_raw(25),art.original_raw(self.p.rom,10))
    def test_portable_project_and_export(self):
        self.p.add_ship(10);self.p.set_portrait(10,self.raw);self.p.set_portrait(25,self.raw[::-1])
        with tempfile.TemporaryDirectory()as f:
            f=Path(f);path=f/'project.json';self.p.save_project(path)
            other=ShipProject(self.p.source);other.load_project(path);self.assertEqual(other.portraits,self.p.portraits)
            out=f/'out.sfc';report=other.export(out)
            self.assertEqual(len(report['custom_portraits']),2)
            self.assertEqual(apply_ips(other.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
            self.assertEqual(other.build()[0],self.p.build()[0])
    def test_invalid_project_is_atomic(self):
        self.p.set_portrait(10,self.raw);before=self.p.manifest()
        invalid=['bad',[dict(id=True,tiles='A'*2048)],[dict(id=25,tiles='A'*2048)],
                 [dict(id=10,tiles='!'*2048)],[dict(id=10,tiles='A'*4)],
                 art.pack(self.p.portraits)*2]
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'bad.json'
            for entries in invalid:
                m=copy.deepcopy(before);m['portraits']=entries;path.write_text(json.dumps(m))
                with self.assertRaises(ValueError):self.p.load_project(path)
                self.assertEqual(self.p.manifest(),before)
        with self.assertRaises(ValueError):self.p.set_portrait(10,b'bad')
        with self.assertRaises(ValueError):self.p.set_portrait(True,self.raw)
    def test_legacy_schema_five(self):
        m=self.p.manifest();m.pop('portraits');m['version']=5
        with tempfile.TemporaryDirectory()as f:
            path=Path(f)/'legacy.json';path.write_text(json.dumps(m));self.p.set_portrait(10,self.raw);self.p.load_project(path)
            self.assertEqual(self.p.portraits,{})
    def test_overlap_refused_and_all_options_compose(self):
        data=bytearray(self.p.rom+b'\xff'*0x200000);data[art.SLOTS+10*4096]=0
        with self.assertRaises(ValueError):art.install(data,self.p.rom,{10:self.raw},25)
        self.p.add_ship(10);self.p.update(25,dict(ports=[31],industry=900))
        self.p.update(10,dict(ports=[31],industry=900));self.p.repair_safeguard=True;self.p.fleet_control=True
        self.p.set_portrait(10,self.raw);self.p.set_portrait(25,self.raw[::-1]);rom,_=self.p.build()
        self.assertEqual(art.original_raw(rom,10),self.raw)
        self.assertEqual(rom[0x1DC14:0x1DC18],bytes.fromhex('22 00 87 e1'))
        self.assertEqual(sum(rom)&65535,int.from_bytes(rom[0xFFDE:0xFFE0],'little'))

if __name__=='__main__':unittest.main()
