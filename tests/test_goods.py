"""Original market sources, including economy gates and port specialties."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from goods import catalogue,MARKETS,TOWNS


class GoodsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rom=ShipProject(ROOT/'New Horizons (USA).zip').rom

    def test_all_sources_match_native_records(self):
        rows=catalogue(self.rom)
        self.assertEqual(len(rows),46)
        self.assertEqual(rows[17]['name'],'Silk')
        self.assertEqual(rows[42]['name'],'Porcelain')
        for port in range(100):
            at=TOWNS+port*37;town=self.rom[at:at+37]
            market=self.rom[MARKETS+town[33]*128:MARKETS+(town[33]+1)*128]
            expected={market[110+i]:(market[119+i]*10,'Regional')for i in range(9)if market[110+i]!=255}
            if town[26]!=255:expected[town[26]]=(town[27]*10,'Specialty')
            actual={row['id']:(s['economy_required'],s['kind'])for row in rows for s in row['sources']if s['port']==port}
            self.assertEqual(actual,expected)
        for row in rows:
            self.assertTrue(row['name']and row['sources'])
            self.assertEqual(len(row['sources']),len({s['port']for s in row['sources']}))
        self.assertEqual(len(rows[17]['sources']),1)
        self.assertEqual(len(rows[42]['sources']),22)

    def test_economy_boundaries_not_industry(self):
        original=catalogue(self.rom)
        for good in original:
            for source in good['sources']:
                port=source['port'];gate=source['economy_required']
                for economy in {max(0,gate-1),gate,gate+1}:
                    data=bytearray(self.rom);at=TOWNS+port*37
                    data[at:at+2]=economy.to_bytes(2,'little')
                    data[at+4:at+6]=(0 if economy>=gate else 1000).to_bytes(2,'little')
                    actual=next(s for s in catalogue(bytes(data))[good['id']]['sources']if s['port']==port)
                    self.assertEqual(actual['available_at_start'],economy>=gate)

    def test_reject_invalid_region_and_good(self):
        for offset,value in [(TOWNS+33,13),(TOWNS+26,46)]:
            data=bytearray(self.rom);data[offset]=value
            with self.assertRaises(ValueError):catalogue(bytes(data))

if __name__=='__main__':unittest.main()
