"""Execute native ship portrait renderer after original-slot swaps and additions."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from content_library import capture_ship,new_id
from library_project import load_ship
OUT=ROOT/('output/ship-editor/library-preview/native-with-discoveries'if '--with-discoveries'in sys.argv else 'output/ship-editor/library-preview/native');OUT.mkdir(parents=True,exist_ok=True)
results=[]
for added in (0,5):
 p=ShipProject(ROOT/'New Horizons (USA).zip')
 for _ in range(added):p.add_ship(10)
 if '--with-discoveries'in sys.argv:
  import discovery_content as dc
  for slot in (0,97):
   e=dc.capture(p,slot);e['id']=new_id();e['name']='Composed Discovery';dc.load(p,e,slot)
 load_ship(p,capture_ship(p,10),13)
 ids=[10,13]+([25,29]if added else [])
 # Include a unique converted portrait, not just a stock-pointer swap.
 raw=bytes((i*17+31)%256 for i in range(1536));p.set_portrait(13,raw)
 rom=OUT/f'library-{added}.sfc';rom.write_bytes(p.build()[0])
 expected=OUT/f'expected-{added}.bin';expected.write_bytes(b''.join(p.portrait_raw(i)for i in ids))
 lua=r'''local ids=@@IDS@@;local started=false;local n=0;local frames=0
local f=assert(io.open(@@EXPECTED@@,'rb'));local expected=f:read('*a');f:close()
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function nextcase()
 n=n+1;if n>#ids then emu.log('PASS Library native portraits '..#ids);emu.stop(0);return end
 for i=0,63 do w(0x600+i,0)end
 w16(0x601,0x0FFE);w(0x603,0xE0);w16(0x604,3);w16(0x606,3);w16(0x608,ids[n])
 emu.setState({['cpu.pc']=0x3CD0,['cpu.k']=0xC1,['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 local bytes={};for i=0,65535 do bytes[#bytes+1]=string.char(emu.read(i,emu.memType.snesVideoRam))end
 assert(table.concat(bytes):find(expected:sub((n-1)*1536+1,n*1536),1,true),'portrait not in native VRAM '..ids[n])
 emu.log('PASS rendered ship '..ids[n]);nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
emu.addEventCallback(function()frames=frames+1 end,emu.eventType.endFrame)
emu.addMemoryCallback(function()if frames>=60 and not started then started=true;emu.log('START Library renderer');nextcase()end end,emu.callbackType.exec,0xC08000,0xC08000,emu.cpuType.snes)
'''.replace('@@IDS@@','{'+','.join(map(str,ids))+'}').replace('@@EXPECTED@@',json.dumps(expected.as_posix()))
 script=OUT/f'native-{added}.lua';script.write_text(lua,encoding='utf-8')
 run=subprocess.run([str(ROOT/'tools/mesen-agent/runtime/mesen-agent.exe'),str(rom),'--home',str(OUT/f'home-{added}'),'--lua',str(script),'--lua-allow-io','--frames','3000','--timeout','60'],capture_output=True,text=True)
 (OUT/f'events-{added}.jsonl').write_text(run.stdout+run.stderr,encoding='utf-8')
 assert run.returncode==0 and 'PASS Library native portraits'in run.stdout,run.stdout+run.stderr
 results.append(dict(added_ships=added,rendered_ids=ids,status='PASS'))
 print('PASS native render',added,ids,flush=True)
(OUT/'results.json').write_text(json.dumps(dict(status='PASS',cases=results,scope='Original renderer uploads exact portrait tiles after stock slot swaps, a unique custom portrait, and 0/5 added classes. Full gameplay acquisition not covered.'),indent=2),encoding='utf-8')
