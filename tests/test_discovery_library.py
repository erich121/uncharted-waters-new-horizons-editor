"""Portable 98-entry discovery pools with isolated artwork and validated imports."""
import base64
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'mod_tool'))
from backend import ShipProject, apply_ips
from content_library import ContentLibrary, new_id
from discovery_content import capture, load, validate, picture, convert_png, rows, stock_id, artwork, opaque_art
from discoveries import BASE, NAME_POINTERS, read_text


class DiscoveryLibraryTests(unittest.TestCase):
    @staticmethod
    def indices(raw):
        return [sum(((raw[t*32+p//2*16+y*2+p%2] >> (7-x)) & 1) << p for p in range(4))
                for t in range(16) for y in range(8) for x in range(8)]

    def setUp(self):
        source = Path(os.environ.get('NH_STOCK_ROM', ROOT/'New Horizons (USA).zip'))
        if not source.exists():
            self.skipTest('Requires stock ROM.')
        self.p = ShipProject(source)

    def custom(self, slot=0):
        entry = capture(self.p, slot)
        entry.update(id=new_id(), name='Custom Discovery', description='A new discovery created for this test.')
        return entry

    def test_all_original_snapshots_and_native_table_unchanged_by_storage(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, d)
            for i in range(98):
                lib.put(capture(self.p, i))
            self.assertEqual(len(ContentLibrary(self.p.rom, d).entries), 98)
            self.assertEqual(self.p.build()[0], self.p.rom)

    def test_converter_snes_dimensions_palette_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            png = Path(d)/'art.png'
            image = Image.new('RGB', (64, 64))
            image.putdata([((x*19)%256, (x*43)%256, (x*71)%256) for x in range(4096)])
            image.save(png)
            e = self.custom()
            e.update(convert_png(png))
            validate(e)
            self.assertEqual(len(base64.b64decode(e['tiles'])), 512)
            self.assertEqual(picture(e, 1).size, (32, 32))
            self.assertLessEqual(len(picture(e, 1).getcolors(1024)), 16)
            self.assertNotIn(0, self.indices(base64.b64decode(e['tiles'])))

    def test_legacy_transparency_repaired_without_editing_project(self):
        from app_defaults import new_project
        from portrait_codec import Decoder
        p = new_project(self.p.source)
        before = p.manifest()
        rom = p.build()[0]
        for slot, entry in p.discovery_entries.items():
            raw, pal = artwork(entry)
            self.assertNotIn(0, self.indices(raw))
            self.assertEqual(opaque_art(raw, pal), (raw, pal))
            self.assertEqual(Decoder(rom).decode(0x300000+slot*0x400, 512), raw)
            self.assertEqual(rom[0x2f1000+slot*32:0x2f1020+slot*32], pal)
        self.assertEqual(p.manifest(), before)

    def test_unused_palette_slot_repair_is_lossless(self):
        raw = bytes(512)  # Solid colour zero, opaque in an image preview.
        pal = b'\x1f\0'+bytes(30)
        fixed, colours = opaque_art(raw, pal)
        self.assertEqual(set(self.indices(fixed)), {1})
        self.assertEqual(colours[2:4], pal[:2])
        self.assertEqual(raw, bytes(512))

    def test_safe_original_art_is_unchanged(self):
        from discoveries import picture_data
        for slot in range(98):
            original = picture_data(self.p.rom, slot)
            if 0 not in self.indices(original[0]):
                self.assertEqual(opaque_art(*original), original)
        self.assertEqual(self.p.build()[0], self.p.rom)

    def test_replacement_is_tied_to_original_location(self):
        e = self.custom(0)
        before = self.p.manifest()
        with self.assertRaises(ValueError): load(self.p, e, 97)
        self.assertEqual(self.p.manifest(), before)
        load(self.p, e, 0)
        raw, _ = self.p.build()
        self.assertEqual(raw[BASE:BASE+99*7], self.p.rom[BASE:BASE+99*7])
        self.assertEqual(read_text(raw, NAME_POINTERS, 0), e['name'])
        self.assertEqual(read_text(raw, 0xebe62, 0), e['description'])

    def test_hundred_entry_library_selects_98_portably(self):
        with tempfile.TemporaryDirectory() as d:
            lib = ContentLibrary(self.p.rom, Path(d)/'lib')
            entries = []
            for i in range(100):
                e = self.custom(i%98)
                e['name'] = f'Custom Site {i:03d}'
                entries.append(e)
            lib.entries = entries
            lib.collections['My Pool'] = [e['id'] for e in entries[:98]]
            lib.save()
            share = Path(d)/'pool.nhlib'
            lib.export_file(share, lib.collections['My Pool'])
            other = ContentLibrary(self.p.rom, Path(d)/'other')
            other.import_file(share)
            self.assertEqual(len(other.entries), 98)
            self.assertIn('My Pool', other.collections)
            self.p.discovery_entries = {i: copy.deepcopy(e) for i, e in enumerate(entries[:98])}
            self.p.discovery_identities = [e['id'] for e in entries[:98]]
            path = Path(d)/'project.json'
            self.p.save_project(path)
            entries[0]['description'] = 'A later Library revision.'
            lib.save()
            q = ShipProject(self.p.source)
            q.load_project(path)
            self.assertNotEqual(q.discovery_entries[0]['description'], entries[0]['description'])
            out = Path(d)/'custom.sfc'
            q.export(out)
            self.assertEqual(apply_ips(q.rom, out.with_suffix('.ips').read_bytes()), out.read_bytes())
            self.assertEqual(len(q.discovery_entries), 98)

    def test_invalid_entries_and_identity_corruption_are_rejected(self):
        before = self.p.manifest()
        for key, value in [('name', 'A'*25), ('description', 'A'*227), ('category', 7), ('difficulty', 256), ('tiles', 'bad'), ('palette', base64.b64encode(b'\xff'*32).decode('ascii'))]:
            e = self.custom()
            e[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                load(self.p, e, 0)
        self.assertEqual(self.p.manifest(), before)
        self.p.discovery_identities[1] = self.p.discovery_identities[0]
        with self.assertRaises(ValueError):
            self.p.build()

    def test_ship_and_discovery_art_storage_does_not_overlap(self):
        for _ in range(5):
            self.p.add_ship(10)
        self.p.set_portrait(25, b'\x35'*1536)
        for i in range(98):
            load(self.p, self.custom(i), i)
        raw, _ = self.p.build()
        self.assertEqual(raw[0x13c0c], 0x5c)
        self.assertEqual(len(raw), 0x400000)
        self.assertEqual(sum(raw)&65535, int.from_bytes(raw[0xffde:0xffe0], 'little'))
        self.assertEqual(len(self.p.discovery_entries), 98)


if __name__ == '__main__':
    unittest.main()
