import sys,unittest,tempfile,json
from legacy_manifest import legacy_manifest
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,apply_ips
from character_mods import name_shuffle,port_shuffle
from sailors import decode_sailors,ATTRIBUTES,BASE,STRIDE,CAPTAIN_IDS
from trade_goods import offers,stock_offers,seeded_shuffle,TABLE,TOWNS

class SeedShuffles(unittest.TestCase):
 def setUp(self):self.p=ShipProject(ROOT/'New Horizons (USA).zip')
 def test_three_goods_modes_preserve_slots_counts_prices_and_gates(self):
  stock=stock_offers(self.p.rom)
  for mode in ('normal','specialty','all'):
   for seed in ('0000','2026','9999'):
    edits=seeded_shuffle(self.p.rom,seed,mode);self.assertEqual(edits,seeded_shuffle(self.p.rom,seed,mode));rows=offers(self.p.rom,edits);self.assertNotEqual(rows,stock)
    for a,b in zip(stock,rows):
     self.assertEqual([(o['kind'],o['economy_required'])for o in a],[(o['kind'],o['economy_required'])for o in b])
     self.assertEqual(len(b),len({o['good']for o in b}))
     if mode!='all':
      kept='Specialty'if mode=='normal'else 'Regional'
      self.assertEqual([o for o in a if o['kind']==kept],[o for o in b if o['kind']==kept])
    for kind in ('Regional','Specialty'):
     def count(groups):return Counter((o['good'],o['price'])for row in groups for o in row if o['kind']==kind)
     self.assertEqual(count(stock),count(rows))
 def test_goods_blind_modes_roundtrip_and_redacted_report(self):
  for mode in ('normal','specialty','all'):
   normal=seeded_shuffle(self.p.rom,'2026',mode)
   blind=seeded_shuffle(self.p.rom,'2026',mode,True)
   self.assertNotEqual(normal,blind);self.assertEqual(blind,seeded_shuffle(self.p.rom,'2026',mode,True))
   stock=stock_offers(self.p.rom);rows=offers(self.p.rom,blind)
   for a,b in zip(stock,rows):
    self.assertEqual([(o['kind'],o['economy_required'])for o in a],[(o['kind'],o['economy_required'])for o in b])
    self.assertEqual(len(b),len({o['good']for o in b}))
   for kind in ('Regional','Specialty'):
    self.assertEqual(Counter((o['good'],o['price'])for r in stock for o in r if o['kind']==kind),Counter((o['good'],o['price'])for r in rows for o in r if o['kind']==kind))
  self.p.set_goods_shuffle('2026','all',True)
  with tempfile.TemporaryDirectory()as d:
   f=Path(d);self.p.save_project(f/'project.json');q=ShipProject(self.p.source);q.load_project(f/'project.json')
   self.assertEqual(q.manifest(),self.p.manifest());q.export(f/'blind.sfc')
   report=json.loads((f/'blind.changes.json').read_text(encoding='utf-8'))
   self.assertEqual(report['goods_shuffle'],dict(seed=None,mode='all',blind=True));self.assertEqual(report['goods_edits'],[])
   self.assertEqual(apply_ips(q.rom,(f/'blind.ips').read_bytes()),q.build()[0])
   self.assertEqual(q.goods_shuffle['seed'],'2026')

 def test_goods_rom_tables_match_project(self):
  for mode in ('normal','specialty','all'):
   self.p.set_goods_shuffle('2026',mode);out,_=self.p.build()
   for port,row in enumerate(offers(self.p.rom,self.p.goods_edits)):
    regular=[o for o in row if o['kind']=='Regional'];special=next((o for o in row if o['kind']=='Specialty'),None)
    at=TABLE+port*128
    for i,o in enumerate(regular):
     self.assertEqual(out[at+110+i],o['good']);self.assertEqual(out[at+119+i]*10,o['economy_required']);self.assertEqual(int.from_bytes(out[at+92+2*i:at+94+2*i],'little'),o['price'])
    if special:self.assertEqual(out[TOWNS+port*37+26],special['good'])
 def test_people_groups_names_and_stats_are_bounded_and_native_bytes(self):
  stock=decode_sailors(self.p.rom)
  for blind in (False,True):
   self.p.set_free_agent_shuffle(True,'2026',blind,True,True,True,True,False)
   out,_=self.p.build();decoded=decode_sailors(out);mapping=name_shuffle(self.p.rom,self.p.free_agent_shuffle)
   free=[r['id']for r in stock if r['role']=='Free agent']
   for ids in (free,CAPTAIN_IDS):
    
    for part in ('first_name','last_name'):self.assertEqual(Counter(decoded[i][part]for i in ids),Counter(stock[i][part]for i in ids))
    self.assertTrue(any(decoded[i]['name']not in {stock[j]['name']for j in ids}for i in ids))
    for i in ids:self.assertEqual(sum(decoded[i][k]for k in ATTRIBUTES),sum(stock[i][k]for k in ATTRIBUTES))
    for i in ids:
     self.assertEqual(decoded[i]['name'],self.p.character_record(i)['name']);self.assertTrue(all(50<=decoded[i][k]<=100 for k in ATTRIBUTES))
     at=BASE+i*STRIDE;self.assertEqual(out[at+26:at+28],self.p.rom[at+26:at+28]);self.assertEqual(out[at+36:at+STRIDE],self.p.rom[at+36:at+STRIDE])
   for i in range(120):
    if i not in mapping:self.assertEqual(out[BASE+i*STRIDE:BASE+(i+1)*STRIDE],self.p.rom[BASE+i*STRIDE:BASE+(i+1)*STRIDE])
 def test_independent_options_and_manual_override(self):
  for flag in ('names','captain_names','mate_stats','captain_stats'):
   self.p.set_free_agent_shuffle(True,'1234',ports=False,**{flag:True});out,_=self.p.build();decoded=decode_sailors(out)
   for r in decode_sailors(self.p.rom):
    i=r['id'];self.assertEqual(decoded[i]['starting_port'],r['starting_port'])
    if flag.endswith('names'):self.assertEqual([decoded[i][k]for k in ATTRIBUTES],[r[k]for k in ATTRIBUTES])
    if flag.endswith('stats'):self.assertEqual(decoded[i]['name'],r['name'])
  self.p.set_free_agent_shuffle(True,'2026',mate_stats=True,ports=False)
  self.p.update_character(79,{'luck':decode_sailors(self.p.rom)[79]['luck']})
  self.assertEqual(decode_sailors(self.p.build()[0])[79]['luck'],decode_sailors(self.p.rom)[79]['luck'])
  self.p.set_free_agent_shuffle(False,'0000');self.assertEqual(self.p.effective_character_edits(),[])
 def test_roundtrip_ips_and_legacy(self):
  self.p.set_goods_shuffle('2026','all');self.p.set_free_agent_shuffle(True,'2026',True,True,True,True,True)
  with tempfile.TemporaryDirectory()as d:
   f=Path(d);self.p.save_project(f/'p.json');q=ShipProject(self.p.source);q.load_project(f/'p.json');self.assertEqual(q.manifest(),self.p.manifest());q.export(f/'p.sfc');self.assertEqual(apply_ips(q.rom,(f/'p.ips').read_bytes()),(f/'p.sfc').read_bytes())
   m=ShipProject(self.p.source).manifest();m.pop('library_state',None);m.pop('ship_descriptions',None);m.pop('custom_characters',None);m['version']=17;m.pop('shipbuilding_shuffle',None);m.pop('goods_shuffle');(f/'old.json').write_text(json.dumps(legacy_manifest(m)));q.load_project(f/'old.json');self.assertEqual(q.goods_shuffle,dict(seed=None,mode='normal'));self.assertEqual(q.build()[0],q.rom)
 def test_name_parts_repeat_and_legacy_pairs_are_preserved(self):
  stock=decode_sailors(self.p.rom)
  self.p.set_free_agent_shuffle(True,'1234',names=True,captain_names=True,ports=False)
  normal=self.p.build()[0];self.assertEqual(normal,self.p.build()[0])
  self.p.set_free_agent_shuffle(True,'1234',True,names=True,captain_names=True,ports=False)
  self.assertNotEqual(normal,self.p.build()[0])
  self.p.free_agent_shuffle.pop('name_parts')
  records=decode_sailors(self.p.build()[0])
  for i in name_shuffle(self.p.rom,self.p.free_agent_shuffle):self.assertIn(records[i]['name'],{r['name']for r in stock})

 def test_per_character_budget_multiple_seeds_and_legacy(self):
  from character_mods import budget_profile
  stock=decode_sailors(self.p.rom)
  for seed in ('0000','0001','9999'):
   for blind in (False,True):
    self.p.set_free_agent_shuffle(True,seed,blind,mate_stats=True,captain_stats=True,ports=False)
    decoded=decode_sailors(self.p.build()[0])
    for r in stock:
     if r['role']in ('Free agent','Fleet captain'):
      self.assertEqual(sum(decoded[r['id']][k]for k in ATTRIBUTES),sum(r[k]for k in ATTRIBUTES))
      self.assertTrue(all(50<=decoded[r['id']][k]<=100 for k in ATTRIBUTES))
  self.assertEqual(budget_profile(400,'test'),(50,)*8);self.assertEqual(budget_profile(800,'test'),(100,)*8)
  for total in (399,801):
   with self.assertRaises(ValueError):budget_profile(total,'test')
  self.p.free_agent_shuffle.pop('stat_budget');legacy=decode_sailors(self.p.build()[0])
  ids=[r['id']for r in stock if r['role']=='Free agent']
  self.assertEqual(Counter(tuple(legacy[i][k]for k in ATTRIBUTES)for i in ids),Counter(tuple(max(50,min(100,stock[i][k]))for k in ATTRIBUTES)for i in ids))

 def test_independent_skill_shuffles_preserve_count_and_other_bytes(self):
  stock=decode_sailors(self.p.rom)
  for flag,role in [('mate_skills','Free agent'),('captain_skills','Fleet captain')]:
   for blind in (False,True):
    self.p.set_free_agent_shuffle(True,'2026',blind,ports=False,**{flag:True})
    out,_=self.p.build();self.assertEqual(out,self.p.build()[0]);decoded=decode_sailors(out);changed=0
    for r in stock:
     i=r['id'];at=BASE+i*STRIDE
     if r['role']==role:
      self.assertEqual(decoded[i]['skills'].bit_count(),r['skills'].bit_count());self.assertEqual(out[at+48]&224,self.p.rom[at+48]&224)
      self.assertEqual(out[at:at+48],self.p.rom[at:at+48]);self.assertEqual(out[at+49],self.p.rom[at+49]);changed+=decoded[i]['skills']!=r['skills']
     else:self.assertEqual(out[at:at+STRIDE],self.p.rom[at:at+STRIDE])
    self.assertGreater(changed,0)
  self.p.set_free_agent_shuffle(True,'9999',mate_stats=True,captain_stats=True,mate_skills=True,captain_skills=True,names=True,captain_names=True)
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'all.json';self.p.save_project(path);q=ShipProject(self.p.source);q.load_project(path);self.assertEqual(q.build()[0],self.p.build()[0])
  self.p.set_free_agent_shuffle(False,'0000');self.assertEqual(self.p.build()[0],self.p.rom)

 def test_preview_matches_export_without_mutating(self):
  from character_mods import preview_changes
  self.p.set_free_agent_shuffle(True,'2026',names=True,captain_names=True,mate_stats=True,captain_stats=True,mate_skills=True,captain_skills=True)
  before=self.p.manifest();rows=preview_changes(self.p.rom,self.p.character_edits,self.p.free_agent_shuffle)
  labels={label for row in rows for label,old,new in row['changes']}
  self.assertTrue({'Name','Port','Skills','Leadership'}<=labels);self.assertEqual(self.p.manifest(),before)
  stock=decode_sailors(self.p.rom);new=decode_sailors(self.p.build()[0])
  for row in rows:
   for label,a,b in row['changes']:
    if label.lower()in ATTRIBUTES:self.assertEqual((a,b),(stock[row['id']][label.lower()],new[row['id']][label.lower()]))

 def test_separate_mate_captain_options_seeds_and_disable(self):
  from character_mods import configure_group,group_active
  cfg=self.p.free_agent_shuffle
  cfg=configure_group(self.p.rom,cfg,'captains','3456',True,dict(captain_names=True,captain_stats=True,captain_skills=True))
  self.assertFalse(group_active(cfg,'mates'));self.assertTrue(group_active(cfg,'captains'))
  self.p.free_agent_shuffle=cfg;first=decode_sailors(self.p.build()[0]);stock=decode_sailors(self.p.rom)
  free=[r['id']for r in stock if r['role']=='Free agent']
  for i in free:self.assertEqual(first[i],stock[i])
  cfg=configure_group(self.p.rom,cfg,'mates','2026',False,dict(ports=True,names=True,mate_stats=True,mate_skills=True))
  self.p.free_agent_shuffle=cfg;second=decode_sailors(self.p.build()[0])
  for i in CAPTAIN_IDS:self.assertEqual(first[i],second[i])
  cfg=configure_group(self.p.rom,cfg,'captains','1111',False,dict(captain_names=True,captain_stats=True,captain_skills=True))
  self.p.free_agent_shuffle=cfg;third=decode_sailors(self.p.build()[0])
  for i in free:self.assertEqual(second[i],third[i])
  cfg=configure_group(self.p.rom,cfg,'mates',enabled=False);self.p.free_agent_shuffle=cfg;fourth=decode_sailors(self.p.build()[0])
  for i in free:self.assertEqual(fourth[i],stock[i])
  for i in CAPTAIN_IDS:self.assertEqual(fourth[i],third[i])
  cfg=configure_group(self.p.rom,cfg,'captains',enabled=False);self.p.free_agent_shuffle=cfg;self.assertEqual(self.p.build()[0],self.p.rom)
 def test_separate_seed_project_roundtrip_and_blind_report(self):
  from character_mods import configure_group
  self.p.free_agent_shuffle=configure_group(self.p.rom,self.p.free_agent_shuffle,'mates','1234',False,dict(ports=True,names=True))
  self.p.free_agent_shuffle=configure_group(self.p.rom,self.p.free_agent_shuffle,'captains','9876',True,dict(captain_names=True,captain_stats=True,captain_skills=True))
  with tempfile.TemporaryDirectory()as d:
   f=Path(d);self.p.save_project(f/'p.json');q=ShipProject(self.p.source);q.load_project(f/'p.json');self.assertEqual(q.build()[0],self.p.build()[0]);report=q.export(f/'p.sfc');self.assertNotIn('captain_seed',report['free_agent_shuffle'])

 def test_invalid_settings_leave_state_unchanged(self):
  before=self.p.manifest()
  for seed in ('','12','12345','abcd','１２３４',1234):
   with self.assertRaises(ValueError):self.p.set_goods_shuffle(seed,'all')
   self.assertEqual(before,self.p.manifest())
  with self.assertRaises(ValueError):self.p.set_goods_shuffle('1234','bad')
  with self.assertRaises(ValueError):self.p.set_free_agent_shuffle(True,'1234',names=1)
  self.assertEqual(before,self.p.manifest())

if __name__=='__main__':unittest.main()
