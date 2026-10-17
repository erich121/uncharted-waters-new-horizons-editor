"""Check expanded roster boundaries, original entries, and compiled data."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from build_fleet_pack import load_design, make_fleet, RAM_DEFAULTS, RAM_SPECS, ROM_RECORDS
from new_horizons_rom import read_rom
from extract_snes_map import Decoder


class FleetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, _ = read_rom(ROOT/'New Horizons (USA).zip')
        cls.design = load_design(ROOT/'content/ships.json')
        cls.mod, cls.report = make_fleet(cls.base, cls.design)

    def test_original_records_and_stocks_survive(self):
        for start, end in ((0x8C7CE, 0x8CE27), (0xAD0BC, 0xAD170),
                           (0x1699BE, 0x16E908), (0xAA8E0, 0xAA920)):
            self.assertEqual(self.base[start:end], self.mod[start:end])
        for group in range(11):
            stock = self.mod[0x200B00+group*16:0x200B10+group*16]
            original = bytes(v for v in self.base[0x8FAE7+group*8:0x8FAEF+group*8] if v != 255)
            self.assertEqual(stock[:len(original)], original)
            extra = [s['id'] for s in self.design['ships'] if group in s['stock_groups']]
            self.assertEqual(list(stock[len(original):len(original)+len(extra)]), extra)
            self.assertTrue(all(v == 255 for v in stock[len(original)+len(extra):]))

    def test_each_new_record_compiles_exactly(self):
        for n, ship in enumerate(self.design['ships']):
            template = self.mod[ROM_RECORDS+n*25:ROM_RECORDS+(n+1)*25]
            spec = self.mod[ROM_RECORDS+250+n*12:ROM_RECORDS+250+(n+1)*12]
            self.assertEqual(template[:18].rstrip(b'\0').decode('ascii'), ship['name'])
            self.assertEqual(template[18], ship['id'])
            self.assertEqual(template[20], ship['default']['guns'])
            self.assertEqual(struct.unpack_from('<HH', template, 21),
                             (ship['default']['crew_space'], ship['default']['cargo_space']))
            self.assertEqual(list(spec[:6]), [ship['industry_required']//10,
                             ship['base_durability'], ship['turning'], ship['power'],
                             ship['max_crew']//10, ship['min_crew']])
            self.assertEqual(struct.unpack_from('<H', spec, 6)[0], ship['total_capacity'])
            self.assertEqual(spec[8], ship['max_guns'])
            self.assertEqual(struct.unpack_from('<H', spec, 10)[0], ship['price_units'])

    def test_london_no_longer_offers_most_of_the_pack(self):
        def offered(port, group):
            stock=self.mod[0x200B00+group*16:0x200B10+group*16]
            return [v for v in stock if 25 <= v < 35 and self.mod[0x214000+port*10+v-25]]
        self.assertEqual(offered(29, 1), [27, 30])  # Golden Hind, Mary Rose
        self.assertEqual(offered(30, 1), [31, 34])  # Great Harry, Sovereign
        self.assertEqual(offered(31, 1), [32])      # HMS Beagle
        self.assertEqual(offered(33, 2), [28])      # Mayflower only
        self.assertEqual(offered(32, 2), [29])      # Batavia, investable Antwerp
        self.assertEqual(offered(35, 2), [29])      # Batavia, investable Hamburg

    def test_unreachable_capital_offers_are_rejected(self):
        for hull, port in ((34, 29), (29, 33)):
            design = copy.deepcopy(self.design)
            design['ships'][hull-25]['stock_ports'] = [port]
            with self.assertRaisesRegex(ValueError, 'Unreachable capital offer'):
                make_fleet(self.base, design)

    def test_all_ten_models_have_reachable_stock(self):
        capitals = {0, 1, 2, 8, 29, 33, 77}
        for ship in self.design['ships']:
            reachable = []
            for port in range(100):
                record = 0x8DA7F + port*37
                industry = struct.unpack_from('<H', self.base, record+4)[0]
                if (self.base[record+34] in ship['stock_groups'] and
                    self.mod[0x214000+port*10+ship['id']-25] and
                    ship['industry_required'] <= (industry if port in capitals else 1000)):
                    reachable.append(port)
            self.assertTrue(reachable, ship['name'])

    def test_current_roster_keeps_every_town_within_the_special_ship_caps(self):
        # This distribution uses no more than two everywhere, also satisfying
        # the user's less restrictive three-model maximum for capitals.
        for port in range(100):
            group=self.base[0x8DA7F+port*37+34]
            stock=self.mod[0x200B00+group*16:0x200B10+group*16]
            extras=[v for v in stock if 25 <= v < 35 and self.mod[0x214000+port*10+v-25]]
            self.assertLessEqual(len(extras), 2, f'town {port}')

    def test_original_used_candidates_and_resale_logic_are_preserved(self):
        for start, end in ((0xAA522, 0xAA58C), (0x80015, 0x800EE),
                           (0x800F5, 0x80102), (0x812B2, 0x8137F)):
            self.assertEqual(self.mod[start:end], self.base[start:end])

    def test_all_extra_portraits_have_distinct_valid_sources(self):
        portraits = set()
        for n, ship in enumerate(self.design['ships']):
            pointer = int.from_bytes(self.mod[0x211200+n*3:0x211203+n*3], 'little')
            self.assertEqual(pointer, 0xE20000+n*0x1000)
            tiles = Decoder(self.mod).decode(pointer-0xC00000)
            asset = ROOT/'assets/ships'/ship.get('portrait_asset', f"{ship['name'].lower().replace(' ', '-')}-portrait.4bpp")
            self.assertEqual(tiles, asset.read_bytes())
            self.assertEqual(len(tiles), 1536)
            portraits.add(tiles)
        self.assertEqual(len(portraits), 10)

    def test_extra_ram_is_reserved_and_all_pointers_are_in_range(self):
        self.assertEqual(self.mod[0x8021:0x8025], bytes.fromhex('a2 7c 07 9a'))
        self.assertGreater(RAM_DEFAULTS, 0x077C)
        self.assertLess(RAM_SPECS+120, 0x0900)
        self.assertEqual(struct.unpack_from('<10H', self.mod, 0x200400+130),
                         tuple(RAM_DEFAULTS+n*25 for n in range(10)))
        self.assertEqual(struct.unpack_from('<10H', self.mod, 0x200500+50),
                         tuple(RAM_SPECS+n*12 for n in range(10)))

    def test_shipping_build_has_no_research_shortcut_and_valid_checksum(self):
        self.assertEqual(len(self.mod), 4*1024*1024)
        self.assertEqual(self.mod[0xE1961:0xE1965], self.base[0xE1961:0xE1965])
        complement, checksum = struct.unpack_from('<HH', self.mod, 0xFFDC)
        self.assertEqual(complement ^ checksum, 65535)
        self.assertEqual(sum(self.mod)&65535, checksum)

    def test_invalid_design_is_rejected_before_rom_mutation(self):
        mutations = [('power', 256), ('price_units', 65535), ('industry_required', 1010),
                     ('base_hull', 25), ('stock_groups', [1, 1]), ('stock_ports', [100])]
        for key, value in mutations:
            draft = copy.deepcopy(self.design)
            draft['ships'][0][key] = value
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)/'bad.json'
                path.write_text(json.dumps(draft), encoding='utf-8')
                with self.assertRaises(ValueError, msg=key):
                    load_design(path)


if __name__ == '__main__':
    unittest.main()
