"""Library item settings and legacy discovery archive regressions."""
import copy
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from content_library import ContentLibrary,new_id
import discovery_content as dc
import item_library as il
import item_shops
from currency import item_price,item_amount,parse_item_amount

class LibraryItemTests(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')
 def test_legacy_stonehenge_repeated_archive(self):
  with tempfile.TemporaryDirectory()as d:
   store=ContentLibrary(self.p.rom,d);old=dc.capture(self.p,0);old['version']=1;old.pop('replaces',None);store.put(old)
   current=dc.capture(self.p,0)
   for _ in range(3):store.archive(current);store.archive_many([current])
   self.assertEqual(len(store.entries),1)
   changed=copy.deepcopy(current);changed['description']='A different Stonehenge story.'
   for _ in range(3):store.archive(changed);store.archive_many([changed])
   self.assertEqual(len(store.entries),2)
   duplicate=copy.deepcopy(changed);duplicate['id']=new_id();store.put(duplicate)
   self.assertEqual(len(store.entries),3)
 def test_item_roundtrip_apply_and_native_bytes(self):
  p=self.p;entry=il.capture(p,0);entry['price_gold']=50000;entry['id']=new_id()
  slots=item_shops.values(p.rom,[])
  port=next(i for i,row in enumerate(slots)if 255 in row[:3]and 0 not in row)
  entry['sources'].append(dict(port=port,early=False));entry=il.validate(entry,p.rom)
  with tempfile.TemporaryDirectory()as d:
   store=ContentLibrary(p.rom,Path(d)/'a');store.put(entry);store.export_file(Path(d)/'items.nhlib')
   other=ContentLibrary(p.rom,Path(d)/'b');other.import_file(Path(d)/'items.nhlib');self.assertEqual(other.entries,[entry])
  before=p.manifest();trial=il.prepare(p,entry);self.assertEqual(before,p.manifest());il.apply(p,trial)
  self.assertEqual(il.capture(p,0)['sources'],entry['sources'])
  self.assertEqual(il.capture(p,0)['price_gold'],50000)
  data=p.build()[0];self.assertEqual(int.from_bytes(data[0x8ebda:0x8ebdc],'little'),500)
  self.assertIn(0,data[__import__('items').TOWNS+port*37+29:__import__('items').TOWNS+port*37+32])
 def test_item_full_shop_atomic_and_price_only(self):
  p=self.p;entry=il.capture(p,0);entry['price_gold']=50000
  port=next(i for i,row in enumerate(item_shops.stock(p.rom))if 255 not in row[:3]and 0 not in row)
  entry['sources'].append(dict(port=port,early=False));before=p.manifest()
  with self.assertRaisesRegex(ValueError,'No free'):il.prepare(p,entry)
  self.assertEqual(p.manifest(),before)
  trial=il.prepare(p,entry,False);self.assertEqual(trial.item_edits,p.item_edits);self.assertTrue(trial.item_price_edits)
 def test_units_no_loss_and_exact_threshold(self):
  self.assertEqual(item_price(10000),'10,000 gold');self.assertEqual(item_price(10100),'1.01 gold bars');self.assertEqual(item_price(1000000),'100 gold bars')
  for price in (0,100,10000,10100,50000,1000000,3276700):
   self.assertEqual(parse_item_amount(item_amount(price),'bars'if price>10000 else 'gold'),price)
  for value in ('NaN','Infinity','1.00001'):
   with self.assertRaises(ValueError):parse_item_amount(value,'bars')
if __name__=='__main__':unittest.main()
