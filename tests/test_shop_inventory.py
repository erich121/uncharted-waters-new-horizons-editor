"""Check deliberate equipment relocations and retained progression."""
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from new_horizons_rom import read_rom
from shop_inventory_patch import inventory_plan


class ShopInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, _ = read_rom(ROOT/'New Horizons (USA).zip')
        cls.plan, cls.old, cls.new, cls.mapping = inventory_plan(cls.base)

    def test_voyage_roles(self):
        self.assertEqual(self.new[0], [41, 24, 3, 255])  # Lisbon supplies + telescope
        self.assertEqual(self.new[18], [18, 21, 20, 7])  # Alexandria instruments + armor
        self.assertEqual(self.new[29], [9, 16, 58, 21])  # London accessible armor
        self.assertEqual(self.new[30], [10, 24, 255, 14])  # Bristol navigation
        self.assertEqual(self.new[28], [4, 17, 42, 255])  # Nantes storm supplies
        self.assertEqual(self.new[3], [0, 16, 62, 255])
        self.assertEqual(self.new[48], [42, 25, 255, 255])  # Caribbean cat + balm
        self.assertEqual(self.new[77], [41, 57, 22, 255])

    def test_specialties_and_morning_stock_preserved(self):
        for port in (33, 34, 75, 83, 85, 94, 95, 97, 98, 99):
            self.assertEqual(self.old[port], self.new[port])
        for port in range(100):
            if port not in (64, 38):
                self.assertEqual(self.old[port][3], self.new[port][3])
            self.assertEqual(self.old[port].count(255), self.new[port].count(255))
            self.assertEqual(len([v for v in self.new[port] if v != 255]), len(set(v for v in self.new[port] if v != 255)))
        self.assertEqual(Counter(v for row in self.old for v in row), Counter(v for row in self.new for v in row))

    def test_mapping_keeps_unrelated_saved_stock(self):
        for port in range(100):
            for item in range(100):
                expected = item
                for slot in range(4):
                    if self.old[port][slot] == item:
                        expected = self.new[port][slot]
                self.assertEqual(self.mapping[port*100+item], expected)

    def test_flamberge_is_outside_northern_europe_and_stays_rare(self):
        self.assertEqual(self.new[64][3], 12)
        self.assertEqual(self.new[38][3], 76)
        self.assertNotIn(12, [v for row in self.new[29:40] for v in row])
        self.assertNotIn(12, [v for row in self.new for v in row[:3]])


if __name__ == '__main__':
    unittest.main()
