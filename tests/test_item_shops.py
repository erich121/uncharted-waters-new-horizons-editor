import sys,unittest,json,tempfile,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,apply_ips
from item_shops import *
from easy_presets import apply,PRESETS
class ItemShopTests(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')
 def test_default_and_only_slot_bytes_changed(self):
  p=self.p;self.assertEqual(p.build(),(p.rom,[]));rows=stock(p.rom);item=catalogue(p.rom,[])[0]['id']
  port=next(i for i,row in enumerate(rows)if item not in row and 255 in row[:3]);p.item_edits=change(p.rom,[],port,item)
  built,_=p.build();allowed={TOWNS+port*37+i for i in range(29,33)}|set(range(0xffdc,0xffe0))
  self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(built,p.rom))));self.assertEqual(len(built),len(p.rom))
  self.assertIn(item,list(built[TOWNS+port*37+29:TOWNS+port*37+33]));self.assertFalse(p.custom_items)
 def test_full_duplicate_and_invalid_rejection(self):
  p=self.p;rows=stock(p.rom);ids=[r['id']for r in catalogue(p.rom,[])];port=next(i for i,row in enumerate(rows)if 255 not in row[:3]);item=next(i for i in ids if i not in rows[port])
  with self.assertRaises(ValueError):change(p.rom,[],port,item)
  for slots in ([ids[0]]*4,[True,255,255,255],[100,255,255,255],[ids[0]]):
   with self.assertRaises(ValueError):validate(p.rom,[dict(port=0,slots=slots)])
  with self.assertRaises(ValueError):change(p.rom,[],100,item)
 def test_move_early_remove_and_restore(self):
  p=self.p;rows=stock(p.rom);port=next(i for i,row in enumerate(rows)if row[0]!=255 and row[3]==255);item=rows[port][0]
  edits=change(p.rom,[],port,item,early=True);self.assertEqual(values(p.rom,edits)[port][3],item);self.assertEqual(values(p.rom,edits)[port][0],255)
  self.assertEqual(restore_item(p.rom,edits,item),[])
  edits=change(p.rom,edits,port,item,remove=True);self.assertNotIn(item,values(p.rom,edits)[port]);self.assertEqual(len(catalogue(p.rom,edits)),61)
 def test_project_and_ips_with_lock_off(self):
  p=self.p;port=0;item=next(i for i in stock(p.rom)[port]if i!=255);p.item_edits=change(p.rom,[],port,item,remove=True)
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'project.json';p.save_project(path);q=ShipProject(p.source);q.load_project(path);self.assertEqual(q.manifest(),p.manifest())
   out=Path(d)/'test.sfc';q.export(out);self.assertEqual(apply_ips(p.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
   before=q.manifest();m=copy.deepcopy(before);m['item_edits'][0]['slots'][0]=100;path.write_text(json.dumps(m),encoding='utf-8')
   with self.assertRaises(ValueError):q.load_project(path)
   self.assertEqual(q.manifest(),before)
 def test_presets_repeat_without_unlocking(self):
  for name in PRESETS:
   p=ShipProject(self.p.source);apply(p,name,seed='1234');before=p.manifest();apply(p,name,seed='1234');self.assertEqual(p.manifest(),before)
   self.assertFalse(any((p.custom_ships,p.custom_items,p.custom_goods,p.custom_economy,p.custom_mates,p.custom_captains)))
   self.assertNotEqual(p.build()[0],p.rom)
 def test_recruits_only_and_seed(self):
  p=self.p;apply(p,'Skilled Recruits');from sailors import decode_sailors
  free={r['id']for r in decode_sailors(p.rom)if r['role']=='Free agent'}
  self.assertEqual(len(free),40);self.assertTrue(all(e['id']in free and e['field']in ('leadership','seamanship')for e in p.character_edits))
  before=p.manifest()
  with self.assertRaises(ValueError):apply(p,'Random Mates',seed='abc')
  self.assertEqual(p.manifest(),before)
class ItemShuffleTests(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')
 def test_modes_counts_repeatability_and_distinct_blind(self):
  from collections import Counter
  original=stock(self.p.rom)
  for seed in ('0000','0001','1234','9999'):
   for include,special_only in ((False,False),(True,False),(False,True)):
    normal=seeded_shuffle(self.p.rom,seed,False,include,special_only);blind=seeded_shuffle(self.p.rom,seed,True,include,special_only)
    self.assertEqual(normal,seeded_shuffle(self.p.rom,seed,False,include,special_only));self.assertNotEqual(normal,blind)
    for edits in (normal,blind):
     rows=values(self.p.rom,edits)
     self.assertEqual(Counter(i for row in original for i in row[:3]),Counter(i for row in rows for i in row[:3]))
     self.assertEqual(Counter(row[3]for row in original),Counter(row[3]for row in rows))
     for before,after in zip(original,rows):
      self.assertEqual([i==255 for i in before],[i==255 for i in after]);used=[i for i in after if i!=255];self.assertEqual(len(used),len(set(used)))
      if special_only:self.assertEqual(before[:3],after[:3])
      if not include and not special_only:self.assertEqual(before[3],after[3])
 def test_shuffle_persistence_atomic_invalid_and_report(self):
  p=self.p;p.set_item_shuffle('1234',True,False,True);before=p.manifest()
  with self.assertRaises(ValueError):p.set_item_shuffle('xyz',False,True)
  self.assertEqual(p.manifest(),before)
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'p.json';p.save_project(path);q=ShipProject(p.source);q.load_project(path);self.assertEqual(q.manifest(),before)
   out=Path(d)/'blind.sfc';report=q.export(out);self.assertFalse(report['item_edits']);self.assertIsNone(report['item_seed']);self.assertTrue(report['item_shuffle']['blind'])
   self.assertEqual(apply_ips(q.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
if __name__=='__main__':unittest.main()
