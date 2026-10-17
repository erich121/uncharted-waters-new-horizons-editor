"""Validate balance limits and compatibility with existing ship records."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from original_ship_balance import balance_plan, SPEC_BASE
from new_horizons_rom import read_rom


class OriginalBalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, _ = read_rom(ROOT/'New Horizons (USA).zip')
        cls.design, cls.specs = balance_plan(cls.original)

    def test_existing_outfits_and_progression_remain_valid(self):
        for i in range(25):
            old = self.original[SPEC_BASE+i*12:SPEC_BASE+(i+1)*12]
            new = self.specs[i*12:(i+1)*12]
            self.assertEqual(new[0], old[0])
            self.assertEqual(new[6:10], old[6:10])
            self.assertGreaterEqual(new[4], old[4])
            self.assertLessEqual(new[5], old[5])
            self.assertNotEqual(new, old)

    def test_roles_have_meaningful_tradeoffs(self):
        s = self.design['ships']
        self.assertLess(s[0]['price_units'], s[1]['price_units'])
        self.assertLess(s[0]['base_durability'], s[1]['base_durability'])
        self.assertGreater(s[0]['turning'], s[1]['turning'])
        self.assertGreater(s[5]['turning'], s[6]['turning'])
        self.assertLess(s[5]['power'], s[6]['power'])
        self.assertLess(s[3]['price_units'], s[9]['price_units'])
        self.assertLess(s[3]['power'], s[9]['power'])
        self.assertGreater(s[14]['power'], s[10]['power'])
        self.assertLess(s[14]['price_units'], s[10]['price_units'])
        self.assertGreater(s[15]['base_durability'], s[16]['base_durability'])
        self.assertLess(s[15]['price_units'], s[16]['price_units'])
        self.assertLess(s[15]['power'], s[16]['power'])


if __name__ == '__main__':
    unittest.main()
