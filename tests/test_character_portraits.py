"""Portrait decoder boundaries and stock coverage. Native comparisons use Mesen."""
import os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT if (ROOT/'backend.py').exists()else ROOT/'mod_tool'))
from backend import read_stock
from character_portraits import portrait,native_portrait,word

class CharacterPortraitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(os.environ.get('NH_STOCK_ROM',str(ROOT/'New Horizons (USA).zip')))
        if not path.is_file():raise unittest.SkipTest('Supply the stock ROM.')
        cls.rom,_=read_stock(path)

    def test_all_sailors_decode_at_native_dimensions(self):
        fixed=composed=0
        for i in range(120):
            face=word(self.rom,0x881F3+50*i+26)
            raw,palette=native_portrait(self.rom,face)
            self.assertEqual((len(raw),len(palette)),(960,32))
            self.assertEqual(portrait(self.rom,i,1).size,(40,48))
            if face&0x8000:composed+=1
            else:fixed+=1
        self.assertGreater(fixed,0);self.assertGreater(composed,0)

    def test_pixel_scaling_keeps_exact_blocks(self):
        for i in (38,69,81,114):
            native=portrait(self.rom,i,1);scaled=portrait(self.rom,i,3)
            self.assertEqual(scaled.size,(120,144))
            for x,y in ((0,0),(8,10),(39,47)):
                self.assertEqual(scaled.getpixel((x*3,y*3)),native.getpixel((x,y)))
                self.assertEqual(scaled.getpixel((x*3+2,y*3+2)),native.getpixel((x,y)))

    def test_invalid_record_ids_fail(self):
        for value in (-1,120,True,'69'):
            with self.assertRaises(ValueError):portrait(self.rom,value)

if __name__=='__main__':unittest.main()
