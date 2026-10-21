import sys,copy,tempfile,json,unittest
from legacy_manifest import legacy_manifest
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,ports,apply_ips
from shipbuilding_shuffle import generate,default
from easy_presets import apply

class ShipbuildingShuffle(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')
 def test_seeded_groups_counts_gates_and_capitals(self):
  p=self.p;catalog=ports(p.economy_rom());pattern=Counter(tuple(o['ports'])for o in p.stock_availability)
  for seed in ('0000','2026','9999','1234'):
   normal=generate(p,seed);blind=generate(p,seed,True);self.assertNotEqual(normal,blind)
   for mode,result in ((False,normal),(True,blind)):
    self.assertEqual(result,generate(p,seed,mode));self.assertEqual(Counter(tuple(o['ports'])for o in result),pattern)
    self.assertTrue(any(a!=b for a,b in zip(result,p.stock_availability)))
    for i,o in enumerate(result):
     self.assertEqual(o['industry'],p.original_availability[i]['industry']);self.assertTrue(o['ports'])
     for port in o['ports']:
      row=catalog[port];self.assertLess(row['group'],11)
      if row['capital']and o['industry']>row['industry']:self.assertIn(port,p.stock_availability[i]['ports']);self.assertLessEqual(o['industry'],p.stock_availability[i]['industry'])
    for port in range(100):self.assertEqual(sum(port in o['ports']for o in result),sum(port in o['ports']for o in p.stock_availability))
 def test_only_original_locations_changed_and_restore_previous(self):
  p=self.p
  for base in (6,10,13,3,16):p.add_ship(base)
  p.update(0,dict(ports=[31],industry=200));before=copy.deepcopy(p.original_availability);ships=copy.deepcopy(p.ships)
  p.set_shipbuilding_shuffle('2026',True);self.assertEqual(p.ships,ships);self.assertEqual([o['industry']for o in before],[o['industry']for o in p.original_availability])
  p.set_shipbuilding_shuffle('1234');self.assertEqual(p.shipbuilding_shuffle['previous'],before)
  once=p.manifest();p.set_shipbuilding_shuffle('1234');self.assertEqual(p.manifest(),once)
  p.clear_shipbuilding_shuffle();self.assertEqual(p.original_availability,before);self.assertEqual(p.ships,ships);self.assertEqual(p.shipbuilding_shuffle,default())
 def test_presets_include_only_original_ships(self):
  for name in ('Random Shipyards','Fresh World','Full Randomizer','Uncharted Challenge'):
   p=ShipProject(self.p.source);p.add_ship(10);extra=copy.deepcopy(p.ships[25]);apply(p,name,'2026',True)
   self.assertEqual(p.shipbuilding_shuffle['seed'],'2026');self.assertTrue(p.shipbuilding_shuffle['blind']);self.assertEqual(p.ships[25],extra)
   once=p.manifest();apply(p,name,'2026',True);self.assertEqual(p.manifest(),once)
 def test_project_ips_redaction_and_legacy(self):
  p=self.p;p.set_shipbuilding_shuffle('2026',True)
  with tempfile.TemporaryDirectory()as d:
   f=Path(d);p.save_project(f/'p.json');q=ShipProject(p.source);q.load_project(f/'p.json');self.assertEqual(q.manifest(),p.manifest());q.export(f/'mod.sfc')
   self.assertEqual(apply_ips(p.rom,(f/'mod.ips').read_bytes()),q.build()[0]);report=json.loads((f/'mod.changes.json').read_text(encoding='utf-8'))
   self.assertEqual(report['original_availability'],[]);self.assertEqual(report['shipbuilding_shuffle'],dict(seed=None,blind=True))
   q.clear_shipbuilding_shuffle();self.assertEqual(q.original_availability,q.stock_availability);self.assertEqual(q.build()[0],q.rom)
   m=q.manifest();m.pop('library_state',None);m.pop('ship_descriptions',None);m.pop('custom_characters',None);m['version']=18;m.pop('shipbuilding_shuffle');(f/'old.json').write_text(json.dumps(legacy_manifest(m)),encoding='utf-8');q.load_project(f/'old.json');self.assertEqual(q.shipbuilding_shuffle,default())
 def test_manual_availability_replaces_metadata_but_stats_do_not(self):
  p=self.p;p.set_shipbuilding_shuffle('2026',True);p.update(0,dict(hull=31));self.assertTrue(p.shipbuilding_shuffle['blind'])
  p.update(0,dict(ports=[31]));self.assertEqual(p.shipbuilding_shuffle,default())
 def test_restore_rejects_overflow_after_added_ship_edit(self):
  p=self.p
  for i in range(25):p.update(i,dict(ports=[]))
  for i in range(16):p.update(i,dict(ports=[31],industry=0))
  p.set_shipbuilding_shuffle('2026');p.add_ship(10);p.update(25,dict(ports=[31],industry=0));before=p.manifest()
  with self.assertRaises(ValueError):p.clear_shipbuilding_shuffle()
  self.assertEqual(p.manifest(),before)

 def test_invalid_or_impossible_draft_atomic(self):
  p=self.p;before=p.manifest()
  for seed in ('abc','１２３４',1234):
   with self.assertRaises(ValueError):p.set_shipbuilding_shuffle(seed)
   self.assertEqual(p.manifest(),before)
  with self.assertRaises(ValueError):p.set_shipbuilding_shuffle('2026',1)
  for row in p.original_availability:row['industry']=1000
  before=p.manifest()
  with self.assertRaises(ValueError):p.set_shipbuilding_shuffle('2026')
  self.assertEqual(p.manifest(),before)

if __name__=='__main__':unittest.main()
