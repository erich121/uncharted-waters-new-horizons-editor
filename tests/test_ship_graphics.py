"""Validate the extra portrait's tile format and original asset preservation."""
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from build_content_pack import make_pack
from new_horizons_rom import read_rom
from ship_graphics import decode_tiles, encode_tiles, literal_stream
from extract_snes_map import Decoder


class ShipGraphicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, _ = read_rom(ROOT/'New Horizons (USA).zip')
        cls.art = (ROOT/'assets/ships/sea-falcon-portrait.4bpp').read_bytes()
        cls.mod, cls.report = make_pack(cls.base, cls.art)

    def test_original_graphics_and_palette_preserved(self):
        self.assertEqual(self.base[0x1699BE:0x16E908], self.mod[0x1699BE:0x16E908])
        self.assertEqual(self.base[0xAA8E0:0xAA920], self.mod[0xAA8E0:0xAA920])
        self.assertEqual(self.base[0x2BAA4:0x2BAEF], self.mod[0x2BAA4:0x2BAEF])
        self.assertNotEqual(Decoder(self.base).decode(0x16A951), self.art)

    def test_snes_plane_roundtrip(self):
        pixels = np.arange(48*64, dtype=np.uint8).reshape(48, 64) % 16
        self.assertTrue(np.array_equal(decode_tiles(encode_tiles(pixels)), pixels))
        self.assertEqual(encode_tiles(decode_tiles(self.art)), self.art)

    def test_runtime_asset_and_size_map(self):
        self.assertEqual(Decoder(self.mod).decode(0x202000), self.art)
        self.assertEqual(self.mod[0x201600:0x201619], self.base[0x2B6C9:0x2B6E2])
        self.assertEqual(self.mod[0x201619], self.base[0x2B6CF])
        self.assertEqual(self.report['new_ship']['hull_type'], 25)
        self.assertEqual(self.mod[0xE1961:0xE1965], self.base[0xE1961:0xE1965])

    def test_literal_controls_and_terminator(self):
        for length in (0, 1, 7, 8, 9, 1536):
            raw = bytes(i % 256 for i in range(length))
            stream = literal_stream(raw)
            self.assertEqual(Decoder(self.base+stream).decode(len(self.base)), raw)


if __name__ == '__main__':
    unittest.main()
