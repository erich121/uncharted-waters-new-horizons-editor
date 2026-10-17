import sys,unittest,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,apply_ips
from economy import *
from world import catalogue
class EconomyTests(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip');self.p.custom_economy=True;self.p.custom_goods=True
 def test_exact_default_and_word_only_edits(self):
  self.assertEqual(self.p.build(),(self.p.rom,[]));self.p.economy_edits=update(self.p.rom,[],41,economy=501,industry=702)
  built,_=self.p.build();allowed={TOWNS+41*37+n for n in (0,1,4,5)}|set(range(0xffdc,0xffe0))
  self.assertEqual(len(built),len(self.p.rom));self.assertTrue(all(a==b or i in allowed for i,(a,b)in enumerate(zip(built,self.p.rom))))
  self.assertEqual(int.from_bytes(built[TOWNS+41*37:TOWNS+41*37+2],'little'),501)
 def test_bulk_region_only_and_modes(self):
  ports=[r['id']for r in catalogue(self.p.rom)[:100]if r['region']=='Northern Europe'];original=stock(self.p.rom)
  for mode,e,i in [('Set to',900,800),('Add',-50,300),('Scale %',150,50)]:
   edits=bulk(self.p.rom,[],ports,mode,economy=e,industry=i);rows=values(self.p.rom,edits)
   for p,row in enumerate(rows):
    if p not in ports:self.assertEqual(row,original[p])
    else:
     for key,amount in [('economy',e),('industry',i)]:
      old=original[p][key];expected=amount if mode=='Set to'else old+amount if mode=='Add'else (old*amount+50)//100
      self.assertEqual(row[key],min(1000,max(1,expected)))
  edits=bulk(self.p.rom,[],ports,'Add',economy=1000)
  self.assertTrue(all(values(self.p.rom,edits)[p]['industry']==original[p]['industry']for p in ports))
 def test_validation_and_restore(self):
  for p,e in [(100,100),(True,100),(0,0),(0,1001),(0,1.5),(0,True)]:
   with self.assertRaises(ValueError):update(self.p.rom,[],p,economy=e)
  edits=update(self.p.rom,[],0,economy=900);self.assertEqual(update(self.p.rom,edits,0,economy=stock(self.p.rom)[0]['economy']),[])
 def test_project_and_legacy_atomic(self):
  self.p.economy_edits=update(self.p.rom,[],0,economy=900)
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'project.json';self.p.save_project(path);q=ShipProject(self.p.source);q.load_project(path);self.assertEqual(q.economy_edits,self.p.economy_edits)
   m=self.p.manifest();m['economy_edits'][0]['industry']=1001;path.write_text(json.dumps(m));before=q.manifest()
   with self.assertRaises(ValueError):q.load_project(path)
   self.assertEqual(q.manifest(),before)
   m=self.p.manifest();m['version']=12;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle',None);m.pop('item_special_only',None);m.pop('item_blind',None);m.pop('item_special',None);m.pop('item_seed',None);m.pop('custom_items',None);m.pop('item_edits',None);m.pop('custom_ships',None);m.pop('custom_goods',None);m.pop('custom_economy',None);m.pop('custom_mates',None);m.pop('custom_captains',None);m.pop('economy_edits');path.write_text(json.dumps(m));q.load_project(path);self.assertEqual(q.economy_edits,[])
 def test_compose_with_ships_goods_and_edited_capital(self):
  from trade_goods import change
  self.p.economy_edits=update(self.p.rom,[],0,economy=900,industry=1000)
  new=self.p.add_ship(10);self.p.update(new,dict(industry=950,ports=[0]));self.p.goods_edits=change(self.p.rom,[],4,10,500)
  self.p.repair_safeguard=True;built,_=self.p.build();self.assertEqual(len(built),0x400000)
  self.assertEqual(int.from_bytes(built[TOWNS+4:TOWNS+6],'little'),1000)
  self.p.economy_edits=update(self.p.rom,self.p.economy_edits,0,industry=500);self.p.build()
  self.p.economy_edits=[];self.p.update(new,dict(name='Kept locked ship'));self.p.build()
  with self.assertRaises(ValueError):self.p.update(new,dict(industry=1000))
  self.p.economy_edits=update(self.p.rom,[],0,economy=900)
  with self.assertRaises(ValueError):self.p.update(new,dict(industry=1000))
if __name__=='__main__':unittest.main()
