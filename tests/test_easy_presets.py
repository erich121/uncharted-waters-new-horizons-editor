import sys,unittest,tempfile,json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,CAPITALS,apply_ips
from easy_presets import PRESETS,RANDOMIZED,plan,apply,preview
from economy import stock,values
from sailors import decode_sailors,ATTRIBUTES
from character_mods import group_settings,group_summary
from item_shops import values as shops,stock as stock_shops
from trade_goods import offers,stock_offers

class EasyPresets(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')
 def test_all_five_pure_repeatable_exportable(self):
  self.assertEqual(len(PRESETS),5)
  for name in PRESETS:
   p=ShipProject(self.p.source);before=p.manifest();draft,lines=preview(p,name,'2026',name in RANDOMIZED)
   self.assertEqual(p.manifest(),before);self.assertTrue(lines)
   apply(p,name,'2026',name in RANDOMIZED);first=p.manifest();apply(p,name,'2026',name in RANDOMIZED)
   self.assertEqual(p.manifest(),first,name);self.assertNotEqual(p.build()[0],p.rom,name)
   self.assertFalse(any((p.custom_ships,p.custom_items,p.custom_goods,p.custom_economy,p.custom_mates,p.custom_captains)))
 def test_economy_preserves_other_fields_and_capitals(self):
  p=self.p;apply(p,'Prosperous World');prosper=values(p.rom,p.economy_edits);apply(p,'Developing World');develop=values(p.rom,p.economy_edits);original=stock(p.rom)
  for a,b,c in zip(prosper,develop,original):
   self.assertEqual(a['economy'],b['economy'])
   self.assertEqual(b['industry'],a['industry']if a['port']in CAPITALS else max(1,(c['industry']*75+50)//100))
  self.assertFalse(p.fleet_difficulty);self.assertEqual(p.ships,p.original)
 def test_people_preserve_earlier_port_stats_and_skill_seeds(self):
  p=self.p;apply(p,'Fresh World','1234',True);a=decode_sailors(p.build()[0]);apply(p,'Unknown Recruits','5678');b=decode_sailors(p.build()[0])
  for x,y in zip(a,b):self.assertEqual(x['name'],y['name']);self.assertEqual(x['starting_port'],y['starting_port'])
  apply(p,'New Faces','9999');c=decode_sailors(p.build()[0])
  for x,y in zip(b,c):
   self.assertEqual(x['starting_port'],y['starting_port']);self.assertEqual(x['skills'],y['skills']);self.assertEqual([x[k]for k in ATTRIBUTES],[y[k]for k in ATTRIBUTES])
  config=p.free_agent_shuffle
  self.assertEqual(group_settings(config,'ports')['seed'],'1234');self.assertTrue(group_settings(config,'ports')['blind'])
  self.assertEqual(group_settings(config,'mate_stats')['seed'],'5678');self.assertEqual(group_settings(config,'names')['seed'],'9999')
  self.assertEqual(group_summary(config,'mates'),'Blind shuffle')
  stock_people=decode_sailors(p.rom)
  for x,y in zip(stock_people,c):
   if x['role']=='Free agent':self.assertEqual(sum(x[k]for k in ATTRIBUTES),sum(y[k]for k in ATTRIBUTES));self.assertEqual(x['skills'].bit_count(),y['skills'].bit_count());self.assertTrue(all(50<=y[k]<=100 for k in ATTRIBUTES))
   if x['role']in ('Protagonist','Story companion'):self.assertEqual(x,y)
 def test_full_randomizer_replaces_targeted_manual_overrides(self):
  p=self.p;p.character_edits=[dict(id=79,field='luck',value=1),dict(id=69,field='luck',value=30)]
  apply(p,'Full Randomizer','2026');self.assertEqual(p.character_edits,[dict(id=69,field='luck',value=30)])
  records=decode_sailors(p.build()[0]);self.assertGreaterEqual(records[79]['luck'],50);self.assertEqual(records[69]['luck'],30)
 def test_items_scopes_combine_without_duplicates_or_drift(self):
  for seed in ('0000','2026','9999'):
   for names in (('Fresh World','Hidden Treasures'),('Hidden Treasures','Fresh World')):
    p=ShipProject(self.p.source);apply(p,names[0],seed,True);before=shops(p.rom,p.item_edits);apply(p,names[1],'1234');after=shops(p.rom,p.item_edits)
    selected=(3,)if names[1]=='Hidden Treasures'else (0,1,2)
    for a,b in zip(before,after):
     for i in set(range(4))-set(selected):self.assertEqual(a[i],b[i])
     used=[i for i in b if i!=255];self.assertEqual(len(used),len(set(used)))
    for slots in ((0,1,2),(3,)):
     self.assertEqual(Counter(r[i]for r in stock_shops(p.rom)for i in slots),Counter(r[i]for r in after for i in slots))
    first=p.manifest();apply(p,names[1],'1234');self.assertEqual(p.manifest(),first)
 def test_goods_combine_with_gates_and_specialties_preserved(self):
  p=self.p;p.set_goods_shuffle('9876','specialty',True);before=offers(p.rom,p.goods_edits)
  apply(p,'Trade Opportunities');lowered=offers(p.rom,p.goods_edits);apply(p,'Fresh World','2026');after=offers(p.rom,p.goods_edits)
  for a,b,c in zip(before,lowered,after):
   self.assertEqual([x for x in b if x['kind']=='Specialty'],[x for x in c if x['kind']=='Specialty'])
   self.assertEqual([(o['kind'],o['economy_required'])for o in b],[(o['kind'],o['economy_required'])for o in c])
   self.assertEqual(len(c),len({o['good']for o in c}))
  self.assertTrue(p.goods_shuffle['blind']);apply(p,'Trade Opportunities');again=p.manifest();apply(p,'Trade Opportunities');self.assertEqual(p.manifest(),again)
 def test_fleets_and_classic_only_touch_their_sections(self):
  p=self.p;apply(p,'Prosperous World');apply(p,'New Faces','2026');before=p.manifest();apply(p,'Classic Plus');after=p.manifest()
  before['fixes']['repair_safeguard']=True;self.assertEqual(before,after)
  apply(p,'Naval Challenge');self.assertTrue(p.fleet_difficulty)
  for nation in p.fleet_rules:self.assertEqual(nation[1],[-1]*4);self.assertEqual(nation[2],[-1]*4);self.assertEqual(nation[3],[10,15,20,-1])
  self.assertFalse(p.fleet_control);self.assertEqual(p.ships,p.original)
 def test_roundtrip_report_and_ips(self):
  p=self.p;apply(p,'Fresh World','1234',True);apply(p,'Unknown Recruits','4567');apply(p,'New Faces','7890');apply(p,'Hidden Treasures','2026')
  with tempfile.TemporaryDirectory()as d:
   path=Path(d);p.save_project(path/'p.json');q=ShipProject(p.source);q.load_project(path/'p.json');self.assertEqual(p.manifest(),q.manifest());q.export(path/'mod.sfc')
   self.assertEqual(apply_ips(p.rom,(path/'mod.ips').read_bytes()),q.build()[0]);report=json.loads((path/'mod.changes.json').read_text(encoding='utf-8'))
   self.assertTrue(report['free_agent_shuffle']['blind']);self.assertEqual(report['goods_edits'],[]);self.assertEqual(report['item_edits'],[])
 def test_unreachable_capital_offer_rejected_before_mutation(self):
  from economy import update
  p=self.p;p.economy_edits=update(p.rom,[],0,industry=1000);i=p.add_ship(10);p.ships[i]['ports']=[0];p.ships[i]['industry']=1000;p.build();before=p.manifest()
  with self.assertRaises(ValueError):preview(p,'Prosperous World')
  self.assertEqual(p.manifest(),before)
  with self.assertRaises(ValueError):apply(p,'Prosperous World')
  self.assertEqual(p.manifest(),before)

 def test_invalid_input_is_atomic(self):
  for name in RANDOMIZED:
   before=self.p.manifest()
   with self.assertRaises(ValueError):apply(self.p,name,'abcd')
   self.assertEqual(self.p.manifest(),before)
  with self.assertRaises(ValueError):apply(self.p,'unknown','2026')

 def test_hard_mode_combines_fleets_and_development(self):
  p=self.p;before=p.manifest();apply(p,'Hard Mode');levels=values(p.rom,p.economy_edits)
  original=stock(p.rom)
  self.assertTrue(p.fleet_difficulty)
  for current,base in zip(levels,original):
   self.assertEqual(current['economy'],base['economy'])
   self.assertEqual(current['industry'],base['industry']if base['port']in CAPITALS else max(1,(base['industry']*75+50)//100))
  for key in set(before)-{'gameplay','economy_edits','library_state'}:self.assertEqual(p.manifest()[key],before[key])

 def test_trade_preset_keeps_locations_and_prices(self):
  p=self.p;apply(p,'Trade & Exploration');new=offers(p.rom,p.goods_edits)
  for actual,base in zip(new,stock_offers(p.rom)):
   self.assertEqual([(o['good'],o['price'],o['kind'])for o in actual],[(o['good'],o['price'],o['kind'])for o in base])
   for a,b in zip(actual,base):self.assertEqual(a['economy_required'],((b['economy_required']*80+500)//1000)*10)
  self.assertEqual(p.ships,p.original);self.assertFalse(p.free_agent_shuffle['enabled'])

 def test_custom_and_added_ships_survive_all_builtins(self):
  from content_library import capture_ship,new_id
  from library_project import load_ship
  p=self.p;entry=capture_ship(p,10);entry['id']=new_id();entry['ship']['name']='Library Ship'
  load_ship(p,entry);p.ships[0]['hull']=99
  before=p.manifest()
  for name in PRESETS:
   apply(p,name,'2026')
   for key in ('edits','added_ships','portraits','ship_descriptions'):
    self.assertEqual(p.manifest()[key],before[key],(name,key))
   for key in ('identities','originals','discoveries'):
    self.assertEqual(p.manifest()['library_state'][key],before['library_state'][key],(name,key))

if __name__=='__main__':unittest.main()
