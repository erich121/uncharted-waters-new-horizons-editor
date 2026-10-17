import sys,unittest,copy,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,apply_ips
from trade_goods import *

class GoodsEdits(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip');self.p.custom_goods=True
 def test_stock_exact_and_unchanged_neighbour(self):
  self.assertEqual(self.p.build(),(self.p.rom,[]))
  self.p.goods_edits=change(self.p.rom,[],4,10,500)
  current=offers(self.p.rom,self.p.goods_edits);stock=stock_offers(self.p.rom)
  for port in range(100):
   if port!=4:self.assertEqual(current[port],stock[port])
  built,_=self.p.build()
  for port in range(100):
   region=self.p.rom[TOWNS+port*37+33]
   if port!=4:self.assertEqual(built[TABLE+port*128:TABLE+(port+1)*128],self.p.rom[MARKETS+region*128:MARKETS+(region+1)*128])
  self.assertEqual(built[MARKETS:MARKETS+13*128],self.p.rom[MARKETS:MARKETS+13*128])
 def test_specialty_changes_only_its_town(self):
  self.p.goods_edits=change(self.p.rom,[],48,10,300);built,_=self.p.build()
  self.assertEqual(built[TOWNS+48*37+27],30)
  for port in range(100):
   if port!=48:self.assertEqual(built[TOWNS+port*37:TOWNS+(port+1)*37],self.p.rom[TOWNS+port*37:TOWNS+(port+1)*37])
 def test_invalid_capacity_duplicates_and_economy(self):
  with self.assertRaises(ValueError):change(self.p.rom,[],0,10,0)
  for value in (-10,1,2551,'500',True):
   with self.assertRaises(ValueError):change(self.p.rom,[],4,10,value)
  row=stock_offers(self.p.rom)[4];row.append(copy.deepcopy(row[0]))
  with self.assertRaises(ValueError):validate(self.p.rom,[dict(port=4,offers=row)])
 def test_restore_gate_and_remove(self):
  edits=change(self.p.rom,[],48,10,300);edits=change(self.p.rom,edits,48,10,200);self.assertEqual(edits,[])
  edits=change(self.p.rom,[],4,10,500);edits=change(self.p.rom,edits,4,10,remove=True);self.assertEqual(edits,[])
 def test_project_roundtrip_atomic_and_legacy(self):
  self.p.goods_edits=change(self.p.rom,[],4,10,500)
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'project.json';self.p.save_project(path);other=ShipProject(self.p.source);other.load_project(path);self.assertEqual(other.goods_edits,self.p.goods_edits)
   m=self.p.manifest();m['goods_edits'][0]['offers'][0]['price']=0;path.write_text(json.dumps(m));before=other.manifest()
   with self.assertRaises(ValueError):other.load_project(path)
   self.assertEqual(other.manifest(),before)
   m=self.p.manifest();m.pop('goods_edits');m['version']=11;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle',None);m.pop('item_special_only',None);m.pop('item_blind',None);m.pop('item_special',None);m.pop('item_seed',None);m.pop('custom_items',None);m.pop('item_edits',None);m.pop('custom_ships',None);m.pop('custom_goods',None);m.pop('custom_economy',None);m.pop('custom_mates',None);m.pop('custom_captains',None);m.pop('economy_edits',None);path.write_text(json.dumps(m));other.load_project(path);self.assertEqual(other.goods_edits,[])
 def test_all_editor_features_compose(self):
  for base in (0,3,10,13,16):self.p.add_ship(base)
  self.p.goods_edits=change(self.p.rom,[],4,10,500);self.p.fleet_control=True;self.p.fleet_difficulty=True;self.p.repair_safeguard=True
  self.p.set_portrait(25,self.p.portrait_raw(25));self.p.update_character(79,dict(leadership=50))
  built,_=self.p.build();self.assertEqual(len(built),0x400000);self.assertEqual(built[SITE:SITE+4],bytes.fromhex('22 00 b2 e2'))
  self.assertEqual(sum(built)&65535,int.from_bytes(built[0xffde:0xffe0],'little'))
if __name__=='__main__':unittest.main()
