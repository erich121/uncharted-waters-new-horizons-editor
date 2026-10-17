"""Meaningful boundary checks for ROM edits and the discovered table layout."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("new_horizons_rom", ROOT/"tools"/"new_horizons_rom.py")
romtool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(romtool)


class ROMResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom, _ = romtool.read_rom(ROOT/"New Horizons (USA).zip")

    def manifest(self, *edits):
        return {"base_sha256": romtool.ROM_HASH, "edits": list(edits)}

    def edit(self, kind, i, field, value):
        return {"kind": kind, "id": i, "field": field, "value": value}

    def test_catalog_boundaries_and_pointer_tables(self):
        data = romtool.catalog(self.rom)
        self.assertEqual(len(data["characters"]), 120)
        self.assertEqual(data["characters"][-1]["first_name"], "Richard")
        self.assertEqual(data["ships"][-1]["name"], "Kansen")
        self.assertEqual(data["items"][-1]["text"], "Treasure Chest")
        self.assertEqual(data["items"][0]["description"]["offset"], "0x05DA6A")
        self.assertEqual(data["checksum_stored"], data["checksum_computed"])
        # First-hand recorded starting stats, not assertions mirroring a decoder.
        simon = data["characters"][6]
        self.assertEqual([simon[k] for k in romtool.CHAR_STATS]+[simon["age"]],
                         [74, 74, 86, 53, 77, 61, 87, 64, 14, 15, 24])

    def test_patch_only_changes_allowed_spans(self):
        edits = self.manifest(self.edit("ship", 5, "name", "Sea Falcon"),
                              self.edit("item", 0, "name", "Dirk"),
                              self.edit("character", 6, "leadership", 90))
        changed, log = romtool.patch(self.rom, edits)
        allowed = set(range(0x8CC33, 0x8CC33+18)) | set(range(0xB24A4, 0xB24AB)) | {0x8833B} | set(range(0xFFDC, 0xFFE0))
        actual = {i for i, (a, b) in enumerate(zip(self.rom, changed)) if a != b}
        self.assertTrue(actual <= allowed)
        self.assertEqual(len(changed), 0x200000)
        self.assertEqual(sum(changed)&0xFFFF, romtool.word(changed, 0xFFDE))
        self.assertEqual(romtool.word(changed, 0xFFDC)^romtool.word(changed, 0xFFDE), 0xFFFF)
        self.assertEqual(changed[0xB2378:0xB24A4], self.rom[0xB2378:0xB24A4])
        self.assertEqual(romtool.ztext(changed, 0xB24AB), b"Short Sword")
        self.assertFalse(log["runtime_tested"])

    def test_rejects_table_expansion_overlong_names_unknowns_and_overlap(self):
        bad = [self.edit("ship", 25, "name", "Test"),
               self.edit("character", 120, "first_name", "Test"),
               self.edit("item", 100, "name", "Test"),
               self.edit("item", 0, "name", "Too Long"),
               self.edit("item", 8, "name", "Test"),
               self.edit("ship", 0, "power", 100),
               self.edit("character", 0, "portrait_word", 7),
               self.edit("character", 0, "leadership", True),
               self.edit("character", 0, "first_name", "%s")]
        for edit in bad:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                romtool.patch(self.rom, self.manifest(edit))
        edit = self.edit("character", 0, "first_name", "Test")
        with self.assertRaises(ValueError):
            romtool.patch(self.rom, self.manifest(edit, edit))

    def test_headered_rom_uses_same_logical_offsets_and_rejects_wrong_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"headered.smc"
            path.write_bytes(b"\xAA"*512+self.rom)
            decoded, header = romtool.read_rom(path)
            self.assertEqual(decoded, self.rom)
            self.assertEqual(len(header), 512)
            wrong = bytearray(self.rom)
            wrong[0] ^= 1
            path.write_bytes(wrong)
            with self.assertRaises(ValueError):
                romtool.read_rom(path)


if __name__ == "__main__":
    unittest.main()
