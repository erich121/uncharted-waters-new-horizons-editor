"""Native shop source, timing, text and image coverage."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from items import catalogue,picture,picture_data,TOWNS

class ItemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rom=ShipProject(ROOT/'New Horizons (USA).zip').rom

    def test_exact_shop_sources_and_hours(self):
        rows=catalogue(self.rom);self.assertEqual(len(rows),61)
        actual={(row['id'],s['port'],s['slot'])for row in rows for s in row['sources']}
        expected={(self.rom[TOWNS+p*37+29+s],p,s)for p in range(100)for s in range(4)if self.rom[TOWNS+p*37+29+s]!=255}
        self.assertEqual(actual,expected)
        for row in rows:
            self.assertTrue(row['name']and row['description'])
            self.assertEqual(len(row['sources']),len({s['port']for s in row['sources']}))
            for s in row['sources']:
                self.assertEqual(s['rare'],s['slot']==3)
                self.assertEqual(s['hours'],'02:00–02:59'if s['rare']else 'Shop hours')

    def test_all_shop_images_decode(self):
        for row in catalogue(self.rom):
            raw,pal=picture_data(self.rom,row['id']);self.assertEqual((len(raw),len(pal)),(512,32))
            self.assertEqual(picture(self.rom,row['id']).size,(128,128))
        for i in [-1,100]:
            with self.assertRaises(ValueError):picture_data(self.rom,i)

    def test_invalid_shop_id_rejected(self):
        data=bytearray(self.rom);data[TOWNS+29]=100
        with self.assertRaises(ValueError):catalogue(bytes(data))

if __name__=='__main__':unittest.main()
