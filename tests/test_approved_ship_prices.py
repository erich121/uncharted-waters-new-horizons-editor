"""Protect the exact user-approved proposal from accidental curve changes."""
import json
from pathlib import Path
import unittest
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from ship_price_patch import refit_fee

class ApprovedPrices(unittest.TestCase):
    def test_refit_thresholds_discount_and_no_cap(self):
        self.assertEqual(refit_fee(100000,199),(3.75,3750))
        self.assertEqual(refit_fee(100000,200),(5,5000))
        self.assertEqual(refit_fee(100000,750),(5,5000))
        self.assertEqual(refit_fee(100000,751),(10,10000))
        self.assertEqual(refit_fee(2000000,1250),(10,200000))
        self.assertEqual(refit_fee(1000,30),(3.75,37))

    def test_all_35_prices_match_approved_proposal(self):
        approved=json.loads((ROOT/'output/content-lab/capacity-pricing/proposal-sovereign-75-bars.json').read_text())
        ships=[]
        for name in ('original-ship-balance.json','ships.json'):
            ships+=json.loads((ROOT/'content'/name).read_text())['ships']
        proposed={s['id']:s for s in approved['ships']}
        self.assertEqual({s['id'] for s in ships},set(range(35)))
        for s in ships:
            self.assertEqual(s['base_price_gold'],proposed[s['id']]['proposed_gold'])
            self.assertGreater(s['base_price_gold'],proposed[s['id']]['current_gold'])
            self.assertEqual(s['base_price_gold'],s['price_units']*10*s['price_multiplier'])
            self.assertLessEqual(s['price_units'],32000)
        self.assertEqual(ships[-1]['base_price_gold'],750000)

if __name__=='__main__':
    unittest.main()
