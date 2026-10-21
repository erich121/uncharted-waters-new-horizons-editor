"""Native 6/10-added transactions, lists, graphics, capture and SRAM fixtures.

Fixtures are controlled native calls, not a complete normal campaign.
Requires the local research WRAM snapshots and original USA ROM.
"""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject,ports
OUT=ROOT/'output/ship-editor/ten-ships-preview/native'
FIX=ROOT/'tools/ten_ship_fixtures'

def run(path,body,name):
 # Start all fixture setup at a stable boundary, after native initialization.
 lua='local frames=0;local started=false\nlocal function fixture()\n'+body+'\nend\nemu.addEventCallback(function()frames=frames+1 end,emu.eventType.endFrame)\nemu.addMemoryCallback(function()if frames>=60 and not started then started=true;fixture()end end,emu.callbackType.exec,0xc08000,0xc08000,emu.cpuType.snes)\n'
 if name in ('camera','select'):
  # These established synthetic fixtures stub C0:8000 themselves. Wrapping
  # their execution in a callback at that address re-enters the callback list.
  lua=body
 lua=lua.replace('__NH_PROJECT_ROOT__/',ROOT.as_posix()+'/')
 script=OUT/(name+'.lua');script.write_text(lua,encoding='utf-8')
 p=subprocess.run([str(ROOT/'tools/mesen-agent/runtime/mesen-agent.exe'),str(path),'--home',str(OUT/(name+'-home')),'--lua',str(script),'--lua-allow-io','--frames','3000','--timeout','55'],capture_output=True,text=True)
 log=p.stdout+'\n'+p.stderr;(OUT/(name+'.log')).write_text(log,encoding='utf-8')
 assert p.returncode==0 and 'PASS' in log and 'lua_error' not in log,log
 messages=[json.loads(l)for l in p.stdout.splitlines()if l.startswith('{')]
 passes=[line for e in messages for line in e.get('text','').splitlines()if line.startswith('PASS')]
 result=dict(name=name,status='PASS',messages=passes);print(json.dumps(result),flush=True);return result

def reset(body):
 return body.replace('for i=0,517 do w(0x6EC+i,rom(0xE41400+i)) end','for i=0,369 do w(0x780+i,rom(0xE10000+i)) end').replace('for i=0,517 do w(0x6EC+i,rom(0xE41400+i))end','for i=0,369 do w(0x780+i,rom(0xE10000+i))end').replace("for i=0,517 do assert(r(0x6EC+i)==rom(0xE41400+i),'reserved records changed') end","for i=0,369 do assert(r(0x780+i)==rom(0xE10000+i),'reserved records changed') end")

def fleet_checks(path,p):
 from fleet_difficulty import SOURCES,resolve
 choices='local choices={'+','.join(f'[{n}]={{'+','.join(f'[{role}]={{'+','.join(f'[{source+40}]={target}'for source,t in zip(SOURCES,row)if(target:=resolve(p.ships,source,t)[0])is not None)+'}'for role,row in enumerate(nation))+'}'for n,nation in enumerate(p.fleet_rules))+'}\n'
 guard=(ROOT/'tools/mesen-agent/test_editor_fleet_difficulty_guards.lua').read_text(encoding='utf-8')
 guard=choices+guard.replace('t.slot==0','t.slot<4').replace('if expected==50 then expected=55 elseif expected==51 then expected=60 end','expected=choices[t.nation][t.slot][t.template]or expected').replace('{49,50,51,55,60,65,69}','{49,50,51,55,60,65,66,67,68,69,70,71,72,73,74}')
 results=[run(path,guard,'fleet-guards')]
 body=(ROOT/'tools/mesen-agent/test_npc_fleet_generation.lua').read_text(encoding='utf-8')
 body=body.replace('local spec=0xC8CE27+(template-40)*12;local source=0xC8C7CE+template*25','')
 body=body.replace('for i=0,299 do w(0x7230+i,rom(0xC8CE27+i))end','for i=0,369 do w(0x780+i,rom(0xE10000+i))end\n for i=0,299 do w(0x7230+i,rom(0xC8CE27+i))end')
 a=body.index("     assert(r(f+7)==template");b=body.index('\n     end',a)
 body=body[:a]+'''     local selected=template
     if t.kind~=1 and tier==2 and country<6 and j<4 then selected=choices[country][j][template]or template end
     local expected=specs[selected]
     assert(r(f+7)==selected,'wrong fleet hull case'..current)
     assert(r(f+2)==expected[1]and r(f+3)==expected[1],'wrong hull condition')
     assert(r(f+4)==expected[2]and r(f+5)==expected[3],'wrong sailing stats')
     assert(r(f+6)==expected[4]and r16(f)==expected[5],'wrong fitted guns/crew')'''+body[b:]
 specs='local specs={'+','.join(f'[{s["id"]+40}]={{{s["hull"]},{s["turning"]},{s["power"]},{s["factory_guns"]},{s["factory_crew"]}}}'for s in p.ships)+'}\n'
 results.append(run(path,choices+specs+body,'fleet-refill'))
 return results

def main():
 OUT.mkdir(parents=True,exist_ok=True);results=[]
 for count in (6,10):
  p=ShipProject(ROOT/'New Horizons (USA).zip')
  for n in range(count):
   i=p.add_ship(10);p.update(i,dict(name=f'Type {n+1}',ports=[31 if n%2 else 3],industry=100+n*50))
  p.fleet_control=True;p.repair_safeguard=True;p.fleet_difficulty=True;p.fleet_rules[0][0][1]=25+count-1
  if count==10:
   import discovery_content as dc
   for slot in (0,97):
    e=dc.capture(p,slot);e['name']='Composed Site';dc.load(p,e,slot)
   for i in range(25,35):p.set_portrait(i,p.portrait_raw(i))
  path=OUT/f'{count}-added.sfc';path.write_bytes(p.build()[0]);p.save_project(OUT/f'{count}-added.json')
  body=reset((FIX/'used_market.lua').read_text(encoding='utf-8'))
  for old,new in [('for n=0,13 do',f'for n=0,{count-1} do'),('id>=39',f'id>={25+count}'),('for id=25,38 do',f'for id=25,{24+count} do'),('0xE40700','0xE14480'),('0xE40701','0xE14481'),('0xE40600','0xE14400'),('0xE40000','0xE14000'),('t.port*14',f't.port*{count}'),('group*14',f'group*{count}'),('if candidate~=34 or t.rare==0 then expected=candidate end','expected=candidate')]:body=body.replace(old,new)
  results.append(run(path,body,f'used-{count}'))
  # A tenth-ship-only pool proves generic hull34 has no inherited extra rarity.
  if count==10:
   body2=body.replace('for port=0,99 do','for port=3,3 do').replace('for n=0,9 do','for n=9,9 do').replace('for id=25,34 do','for id=34,34 do')
   body2=body2.replace('local candidate=pool[t.pick%#pool+1]','local candidate=pool[t.pick%#pool+1]')
   # Filter helper results to the tenth model; leave native code unchanged by
   # using a separate export with the first9 offered in another region.
   q=ShipProject(p.source);q.load_project(OUT/'10-added.json')
   for i in range(25,34):q.update(i,dict(ports=[18],industry=1000))
   q.update(34,dict(ports=[3],industry=100))
   special=OUT/'tenth-only-used.sfc';special.write_bytes(q.build()[0])
   results.append(run(special,body2,'used-tenth-no-rarity'))
  offers=p.all_offers();catalog=ports(p.rom);cases=[]
  for port in catalog:
   group=port['group'];wanted={i for i,o in enumerate(offers)if any(t['group']==group and t['id']in o['ports']for t in catalog)}
   base=[i for i in p.rom[0x8fae7+group*8:0x8faef+group*8]if i in wanted]
   order=base+sorted(wanted-set(base))
   for industry in (0,99,100,299,300,499,500,549,550,799,800,999,1000):
    cases.append(dict(group=group,port=port['id'],industry=industry,expected=[i+40 for i in order if port['id']in offers[i]['ports']and offers[i]['industry']<=industry]))
  fixture=(FIX/'fleet_shipyards.lua').read_text(encoding='utf-8');body=fixture[fixture.index('local current=0'):]
  a=body.index('-- Actual fixed-capital');b=body.index('local seen=false',a);body=body[:a]+body[b:]
  a=body.index(' for i=0,15 do');b=body.index(' assert(r16(sp+4)',a);body=body[:a]+' expected=t.expected\n'+body[b:]
  prefix='local cases='+json.dumps(cases).replace(':','=').replace('"','').replace('[','{').replace(']','}')+'\n'
  results.append(run(path,prefix+reset(body),f'shipyards-{count}'))
  allocation=reset((FIX/'fleet_allocation.lua').read_text(encoding='utf-8')).replace('current==39',f'current=={25+count}').replace('0x6EC+(current-25)*25','0x780+(current-25)*25').replace('0xE41400','0xE10000').replace("for i=0,517 do assert(r(0x6EC+i)==rom(0xE10000+i),'reserved record was overwritten') end","for i=0,369 do assert(r(0x780+i)==rom(0xE10000+i),'reserved record was overwritten') end").replace('39 owned allocation',f'{25+count} owned allocation')
  results.append(run(path,allocation,f'allocation-{count}'))
  capture=reset((FIX/'capture_all.lua').read_text(encoding='utf-8'))
  capture=capture.replace('current==15',f'current=={count}').replace('current>=15',f'current>={count}')
  capture='\n'.join(l for l in capture.splitlines()if '0x6D0'not in l)
  capture=capture.replace('expected=current<14 and 0xE41400+current*25 or 0xE41700','expected=0xE10000+current*25').replace('local template=current<10 and 65+current or current<14 and 66+current or 75','local template=65+current').replace("for i=0,517 do assert(r(0x6EC+i)==rom(0xE41400+i),'capture damaged immutable record')end","for i=0,369 do assert(r(0x780+i)==rom(0xE10000+i),'capture damaged immutable record')end").replace('all14 added hulls plus private75',f'all{count} added hulls')
  results.append(run(path,capture,f'capture-{count}'))
  save=(FIX/'save_reload.lua').read_text(encoding='utf-8').replace('for n=0,13 do',f'for n=0,{count-1} do').replace('0xE41400','0xE10000').replace('0xE41800','0xE13000').replace('for i=0x6D0,0x8F1 do','for i=0x780,0x8F1 do').replace("for i=0,517 do assert(r(0x6EC+i)==rom(0xE10000+i),'immutable records corrupted on load')end","for i=0,369 do assert(r(0x780+i)==rom(0xE10000+i),'immutable records corrupted on load')end").replace('80,75,19','80,50,19')
  save='\n'.join(l for l in save.splitlines()if '0x6D0'not in l).replace('preserves14 owned ship types/compartments and existing NPC75 fleet; reset restores518 record bytes and300-man enemy default',f'preserves{count} owned ship types/compartments and original NPC fleet; reset restores370 bytes')
  results.append(run(path,save,f'save-{count}'))
  icons=(FIX/'icon_routes.lua').read_text(encoding='utf-8').replace('for i=0,517 do w(0x6EC+i,emu.read(0x241400+i,emu.memType.snesPrgRom))end','for i=0,369 do w(0x780+i,emu.read(0x210000+i,emu.memType.snesPrgRom))end').replace('for class=0,4 do','for class=0,3 do').replace('for hull=0,38 do',f'for hull=0,{24+count} do').replace('40+t.hull+(t.hull>=35 and 1 or 0)','40+t.hull').replace('PASS:80 sea icon descriptors and936 native battle tile writes; Berrio class4, all39 hulls,6 battle facings,4 fleet groups',f'PASS:64 sea descriptors and{(25+count)*24} battle tile writes; all{25+count} hulls')
  results.append(run(path,icons,f'icons-{count}'))
 # Exercise a35-type regional union with <=12 offers at each of three towns.
 for i in range(35):p.update(i,dict(ports=[(0,3,6)[i%3]],industry=0))
 stress=OUT/'regional-union35.sfc';stress.write_bytes(p.build()[0]);offers=p.all_offers();cases=[]
 for port in catalog:
  group=port['group'];wanted={i for i,o in enumerate(offers)if any(t['group']==group and t['id']in o['ports']for t in catalog)}
  base=[i for i in p.rom[0x8fae7+group*8:0x8faef+group*8]if i in wanted];order=base+sorted(wanted-set(base))
  for industry in (0,1000):cases.append(dict(group=group,port=port['id'],industry=industry,expected=[i+40 for i in order if port['id']in offers[i]['ports']]))
 prefix='local cases='+json.dumps(cases).replace(':','=').replace('"','').replace('[','{').replace(']','}')+'\n'
 results.append(run(stress,prefix+reset(body),'regional-union35'))
 # Runtime input/camera checks against the composed ten-addition export.
 path=OUT/'10-added.sfc'
 for label,name in [('camera','test_battle_camera_visibility.lua'),('select','test_battle_auto_input.lua')]:
  results.append(run(path,(ROOT/'tools/mesen-agent'/name).read_text(encoding='utf-8'),label))
 q=ShipProject(p.source);q.load_project(OUT/'10-added.json');results.extend(fleet_checks(path,q))
 report=dict(status='PASS',checks=results,scope='Controlled native shipyard/used generation and purchase guards, owned allocation, real capture creator, SRAM copy/load, icon routines, camera/Select. Not normal construction pickup/full campaign or rendered battle victory.')
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
