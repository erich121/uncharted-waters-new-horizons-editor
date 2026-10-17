"""Verify exported native structure and relocated campaign serialization."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from scenario_container import sources,parse_container
from extract_snes_map import Decoder
from ship_graphics import literal_stream
from new_horizons_rom import read_rom


class StoryContainers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=read_rom(ROOT/'New Horizons (USA).zip')[0]

    def test_all_six_native_directories_roundtrip(self):
        totals=[0,0,0]
        for source in sources(self.rom):
            data=Decoder(self.rom).decode(source['compressed_offset'],max_output=65536)
            parsed=parse_container(data)
            self.assertEqual(parsed['hero_word'],source['hero'])
            totals[0]+=len(parsed['modules'])
            totals[1]+=sum(len(m['streams'])for m in parsed['modules'])
            totals[2]+=sum(len(s['entries'])for m in parsed['modules']for s in m['streams'])
            encoded=literal_stream(data)
            self.assertEqual(Decoder(self.rom+encoded).decode(len(self.rom),max_output=65536),data)
        self.assertEqual(totals,[35,150,721])

    def test_ernst_native_ram_source_matches(self):
        source=next(s for s in sources(self.rom)if s['hero']==3)
        decoded=Decoder(self.rom).decode(source['compressed_offset'])
        ram=(ROOT/'output/scenario-research/ernst-opening-wram.bin').read_bytes()
        self.assertEqual(decoded,ram[0x10000:0x10000+len(decoded)])
        first=parse_container(decoded)['modules'][0]['streams'][0]
        self.assertEqual(first['offset'],0x2E)
        self.assertEqual(first['entries'][0],dict(location=33,context=7,code_offset=28))


if __name__=='__main__':unittest.main()
