"""Verify additive tables, source preservation, and the distributable IPS."""
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_content_pack import make_pack, make_ips
from new_horizons_rom import read_rom


class ContentPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, _ = read_rom(ROOT / "New Horizons (USA).zip")
        cls.mod, cls.report = make_pack(cls.base)

    def test_original_records_and_pointers_preserved(self):
        for start, size in ((0x881F3, 120*50), (0x8C7CE, 65*25),
                            (0x8CE27, 25*12), (0x8EBC7, 100*23),
                            (0x8DA7F, 100*37)):
            self.assertEqual(self.base[start:start+size], self.mod[start:start+size])
        for old, new, size in ((0xB2378, 0x200000, 300),
                              (0x5D93E, 0x200200, 300),
                              (0xAD0BC, 0x200400, 130),
                              (0xAD13E, 0x200500, 50),
                              (0xAD2C4, 0x200600, 200)):
            self.assertEqual(self.base[old:old+size], self.mod[new:new+size])
        for row in range(11):
            self.assertEqual(self.base[0x8FAE7+row*8:0x8FAEF+row*8],
                             self.mod[0x200B00+row*16:0x200B08+row*16])

    def test_header_and_no_research_shortcut(self):
        self.assertEqual(len(self.mod), 0x400000)
        complement, checksum = struct.unpack_from("<HH", self.mod, 0xFFDC)
        self.assertEqual(complement ^ checksum, 0xFFFF)
        self.assertEqual(sum(self.mod) & 0xFFFF, checksum)
        self.assertEqual(self.base[0xE1961:0xE1965], self.mod[0xE1961:0xE1965])

    def test_ips_recreates_exact_expanded_rom(self):
        patch = make_ips(self.base, self.mod)
        rebuilt = bytearray(self.base)
        cursor = 5
        while patch[cursor:cursor+3] != b"EOF":
            offset = int.from_bytes(patch[cursor:cursor+3], "big")
            size = int.from_bytes(patch[cursor+3:cursor+5], "big")
            cursor += 5
            if size:
                payload = patch[cursor:cursor+size]
                cursor += size
            else:
                size = int.from_bytes(patch[cursor:cursor+2], "big")
                payload = patch[cursor+2:cursor+3]*size
                cursor += 3
            if offset+size > len(rebuilt):
                rebuilt.extend(b"\x00"*(offset+size-len(rebuilt)))
            rebuilt[offset:offset+size] = payload
        self.assertEqual(bytes(rebuilt), self.mod)

    def test_rejects_wrong_base(self):
        with self.assertRaises(ValueError):
            make_pack(self.base[:-1])


if __name__ == "__main__":
    unittest.main()
