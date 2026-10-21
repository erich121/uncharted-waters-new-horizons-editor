"""All custom pool art/palettes rendered natively, with ship-loader coexistence."""
import sys,json,base64,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from content_library import new_id
from discovery_content import capture,load,artwork
from discoveries import picture_data
OUT=ROOT/'output/ship-editor/discovery-library-preview/native';OUT.mkdir(parents=True,exist_ok=True)
checks=[]
for added in (0,5):
 p=ShipProject(ROOT/'New Horizons (USA).zip')
 for _ in range(added):p.add_ship(10)
 for i in range(98):
  entry=capture(p,i);entry['id']=new_id();entry['name']='Custom Site '+str(i);entry['description']='A custom discovery description for site '+str(i)+'.'
  entry['tiles']=base64.b64encode(bytes((n*17+i*3)%256 for n in range(512))).decode('ascii')
  palette=b''.join(((i*139+j*233)&32767).to_bytes(2,'little')for j in range(16));entry['palette']=base64.b64encode(palette).decode('ascii')
  load(p,entry,i)
 rom=OUT/f'custom-pool-{added}.sfc';rom.write_bytes(p.build()[0])
 (OUT/f'expected-{added}.bin').write_bytes(b''.join(b''.join(artwork(p.discovery_entries[i]))for i in range(98)))
 lua=(ROOT/'tools/mesen-agent/test_discovery_browser.lua').read_text(encoding='utf-8')
 lua=lua.replace('local cases=@@CASES@@','local cases={}').replace('local root=@@ROOT@@','local root='+json.dumps(OUT.as_posix()+'/'))
 lua=lua.replace("root..'expected.bin'", "root..'expected-"+str(added)+".bin'")
 script=OUT/f'native-{added}.lua';script.write_text(lua,encoding='utf-8')
 r=subprocess.run([str(ROOT/'tools/mesen-agent/runtime/mesen-agent.exe'),str(rom),'--home',str(OUT/f'home-{added}'),'--lua',str(script),'--lua-allow-io','--frames','4000','--timeout','75'],capture_output=True,text=True)
 (OUT/f'events-{added}.jsonl').write_text(r.stdout+r.stderr,encoding='utf-8')
 assert r.returncode==0 and 'PASS: all98 discovery pictures and palettes'in r.stdout,r.stdout+r.stderr
 checks.append(dict(added_ships=added,custom_discoveries=98,exact_vram_and_cgram=True))
 print('PASS 98 custom discovery renders with',added,'added ships',flush=True)
 # Verify project reopening embeds all tiles, palettes and descriptions.
 with tempfile.TemporaryDirectory()as d:
  path=Path(d)/'pool.json';p.save_project(path);q=ShipProject(p.source);q.load_project(path);assert q.build()==p.build()
(OUT/'results.json').write_text(json.dumps(dict(status='PASS',cases=checks,total_custom_native_renders=196,scope='Native renderer/VRAM/CGRAM and portable pool; full village interaction and treasure retrieval remain unverified.'),indent=2),encoding='utf-8')
