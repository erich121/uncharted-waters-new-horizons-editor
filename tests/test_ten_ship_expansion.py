"""Permanent boundaries for ten additions, regional unions and portable content."""
import copy,json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,apply_ips
from content_library import capture_ship,ContentLibrary
from library_project import load_ship
from availability import layout

class TenShipTests(unittest.TestCase):
 def setUp(self):
  source=Path(os.environ.get('NH_STOCK_ROM',ROOT/'New Horizons (USA).zip'))
  if not source.exists():self.skipTest('Needs stock USA ROM.')
  self.p=ShipProject(source)
 def fill(self):
  for n in range(10):
   i=self.p.add_ship(10);self.p.update(i,dict(ports=[3 if n%2 else 31],industry=100+n*50,name=f'New Type {n+1}'))
 def test_all_ten_project_ips_portraits_fleets_discoveries(self):
  self.fill();self.p.fleet_control=True;self.p.repair_safeguard=True;self.p.fleet_difficulty=True
  self.p.fleet_rules[0][0][1]=34
  for i in (25,34):self.p.set_portrait(i,bytes((n+i)%256 for n in range(1536)))
  import discovery_content as dc
  e=dc.capture(self.p,0);e['name']='Test Site';dc.load(self.p,e,0)
  before=self.p.manifest()
  with self.assertRaisesRegex(ValueError,'ten'):self.p.add_ship()
  self.assertEqual(self.p.manifest(),before)
  with tempfile.TemporaryDirectory()as d:
   d=Path(d);path=d/'project.json';self.p.save_project(path)
   q=ShipProject(self.p.source);q.load_project(path)
   self.assertEqual(q.manifest(),self.p.manifest());self.assertEqual(q.build(),self.p.build())
   out=d/'ten.sfc';q.export(out)
   self.assertEqual(apply_ips(q.rom,out.with_suffix('.ips').read_bytes()),out.read_bytes())
   self.assertEqual(out.stat().st_size,0x400000)
 def test_regional_union35_and_per_town_limit16(self):
  self.fill()
  for i in range(35):self.p.update(i,dict(ports=[(0,3,6)[i%3]],industry=0))
  rom,_=self.p.build();stock,bitmap,industry,gate,stride=layout(35)
  self.assertEqual(stride,64)
  for i in range(35):self.assertEqual(rom[bitmap+(0,3,6)[i%3]*35+i],1)
  self.assertEqual(set(rom[stock:stock+35]),set(range(35)))
  self.assertEqual(rom[stock+35:stock+64],b'\xff'*29)
  self.assertEqual(rom[industry:industry+70],b'\0'*70)
  for i in range(16):self.p.update(i,dict(ports=[31],industry=0))
  before=self.p.manifest()
  with self.assertRaisesRegex(ValueError,'16-ship'):self.p.update(16,dict(ports=[31],industry=0))
  self.assertEqual(self.p.manifest(),before)
 def test_tenth_library_roundtrip_remove_and_reference(self):
  self.fill();self.p.fleet_rules[0][0][1]=34
  e=capture_ship(self.p,34)
  with tempfile.TemporaryDirectory()as d:
   lib=ContentLibrary(self.p.rom,Path(d)/'a');lib.put(e);path=Path(d)/'ten.nhlib';lib.export_file(path)
   other=ContentLibrary(self.p.rom,Path(d)/'b');other.import_file(path)
   load_ship(self.p,other.entries[0],33,use_locations=True)
   self.assertEqual(self.p.fleet_rules[0][0][1],33)
   self.assertEqual(self.p.all_offers()[33],e['availability'])
   self.p.remove_ship(25);self.assertEqual(self.p.fleet_rules[0][0][1],32)
   self.p.build()
 def test_default_add_avoids_full_port_and_invalid_layout(self):
  for _ in range(10):self.p.add_ship()
  self.assertEqual(len(self.p.ships),35);self.p.validate_offer_counts();self.p.build()
  for n in (24,36,True):
   with self.assertRaises(ValueError):layout(n)
 def test_small_exports_retain_previous_compiler_bytes(self):
  # Pin compatibility to the exact production source used by the capacity audit.
  path=ROOT/'output/ship-capacity-research/editor-2026-10-17/audited-expansion.py.txt'
  if not path.exists():self.skipTest('Historical comparison source is local research evidence.')
  old={};exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),old)
  from expansion import make_fleet
  r=self.p.ships[10]
  for count in (1,5):
   ships=[dict(id=25+n,name=f'Type {n}',base_hull=10,industry_required=0,base_durability=r['hull'],turning=r['turning'],power=r['power'],max_crew=r['max_crew'],min_crew=r['min_crew'],total_capacity=r['capacity'],max_guns=r['max_guns'],price_units=r['price_gold']//10,default=dict(guns=r['factory_guns'],crew_space=r['factory_crew'],cargo_space=r['factory_cargo']),stock_ports=[3],stock_groups=[0])for n in range(count)]
   self.assertEqual(make_fleet(self.p.rom,dict(ships=ships))[0],old['make_fleet'](self.p.rom,dict(ships=ships))[0])

if __name__=='__main__':unittest.main()
