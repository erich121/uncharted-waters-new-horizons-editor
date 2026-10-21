"""Compare original item images and all hourly shop lists using Mesen Lua."""
import sys,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from items import catalogue,picture_data
out=ROOT/'output/ship-editor/discovery-library-preview/items-composition';out.mkdir(parents=True,exist_ok=True)
p=ShipProject(ROOT/'New Horizons (USA).zip');(out/'native-probe.sfc').write_bytes((ROOT/'output/ship-editor/discovery-library-preview/native/custom-pool-5.sfc').read_bytes());rows=catalogue(p.rom)
(out/'expected.bin').write_bytes(b''.join(b''.join(picture_data(p.rom,row['id']))for row in rows))
lua=(ROOT/'tools/mesen-agent/test_items_browser.lua').read_text(encoding='utf-8').replace('@@ROOT@@',json.dumps(out.as_posix()+'/')).replace('@@IDS@@','{'+','.join(str(row['id'])for row in rows)+'}')
script=out/'verify-native.lua';script.write_text(lua,encoding='utf-8')
run=subprocess.run([str(ROOT/'tools/mesen-agent/runtime/mesen-agent.exe'),str(out/'native-probe.sfc'),'--home',str(out/'home'),'--lua',str(script),'--lua-allow-io','--frames','3000','--timeout','90'],capture_output=True,text=True)
(out/'events.jsonl').write_text(run.stdout+run.stderr,encoding='utf-8');events=[json.loads(line)for line in run.stdout.splitlines()if line.startswith('{')]
logs='\n'.join(e.get('text','')for e in events)
assert run.returncode==0 and any(e.get('event')=='summary'and e.get('ok')for e in events)and '4800 native shop lists passed'in logs and '61 native item pictures passed'in logs,run.stdout+run.stderr
report=dict(status='PASS',item_pictures=61,native_vram_and_palette_match=True,hourly_shop_cases=4800,scope='Original picture dispatcher and shop stock selection at all100 towns and48 half-hour ticks; not purchase payment or full shop UI.')
(out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
