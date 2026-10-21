"""Controller-only cold-start confirmation of discovery initializer; no RAM writes."""
from pathlib import Path
import json, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ship-editor/discovery-library-preview/cold-start';OUT.mkdir(parents=True,exist_ok=True)
reports=[]
for delay in (0,):
 out=OUT/f'cold-{delay}';out.mkdir(exist_ok=True)
 steps=[('none',2400),('a',8),('none',240),('a',8),('none',240),('a',8),('none',240),('b',8),('none',180+delay),('a',8),('none',1000)]
 lua=r'''local steps=@@STEPS@@
local frame=0;local before=nil;local finished=false
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function word(p)return r(p)+256*r(p+1)end
emu.addEventCallback(function()frame=frame+1 end,emu.eventType.startFrame)
emu.addEventCallback(function()
 local input={};for _,b in ipairs({'a','b','x','y','l','r','up','down','left','right','start','select'})do input[b]=false end
 local t=frame;for _,s in ipairs(steps)do if t<=s[2]then if s[1]~='none'then input[s[1]]=true end;break end;t=t-s[2]end
 emu.setInput(input,0)
end,emu.eventType.inputPolled)
emu.addMemoryCallback(function()before=word(0xEB0A)+65536*word(0xEB0C);emu.log('INIT '..before..' frame '..frame)end,emu.callbackType.exec,0xC74AC4,0xC74AC4,emu.cpuType.snes)
emu.addMemoryCallback(function()
 assert(before~=nil,'initializer not seen')
 local f=assert(io.open(@@PATH@@,'wb'))
 for i=0,97 do for j=0,6 do f:write(string.char(r(0x8D14+i*7+j)))end end
 f:close()
 emu.log('DONE '..before..' '..(word(0xEB0A)+65536*word(0xEB0C))..' frame '..frame)
 finished=true
end,emu.callbackType.exec,0xC74E9B,0xC74E9B,emu.cpuType.snes)
emu.addEventCallback(function()if finished then emu.stop(0)end end,emu.eventType.endFrame)
'''.replace('@@STEPS@@','{'+','.join('{'+json.dumps(b)+','+str(n)+'}'for b,n in steps)+'}').replace('@@PATH@@',json.dumps((out/'discoveries.bin').as_posix()))
 script=out/'cold.lua';script.write_text(lua,encoding='utf-8')
 home=Path(tempfile.mkdtemp(prefix='home-',dir=out))
 result=subprocess.run([str(ROOT/'tools/mesen-agent/runtime/mesen-agent.exe'),str(ROOT/'output/ship-editor/discovery-library-preview/native/custom-pool-5.sfc'),'--home',str(home),'--lua',str(script),'--lua-allow-io','--frames','5000','--timeout','90'],capture_output=True,text=True)
 (out/'events.jsonl').write_text(result.stdout+result.stderr,encoding='utf-8')
 events=[json.loads(l)for l in result.stdout.splitlines()if l.startswith('{')]
 done=[line for e in events for line in e.get('text','').splitlines() if line.startswith('DONE ')]
 assert result.returncode==0 and done,result.stdout+result.stderr
 _,seed,end,_,frame=done[0].split();state=int(seed);selected=[];extra=[]
 def draw():
  global state
  state=(state*1103515245+12345)&0xffffffff
  return ((state>>16)&32767)%98
 while len(selected)<50:
  i=draw()
  if i not in selected:selected.append(i)
 while len(extra)<10:
  i=draw()
  if i not in selected and i not in extra:extra.append(i)
 data=(out/'discoveries.bin').read_bytes()
 assert state==int(end)
 assert sorted(selected)==[i for i in range(98)if not data[i*7+6]&128]
 assert all(data[i*7+4]==90+j for j,i in enumerate(extra))
 reports.append(dict(delay=delay,frame=int(frame),rng_before=int(seed),rng_after=int(end),selected=selected,secondary=extra,status='PASS'))
 print('PASS cold start delay',delay,'initialization frame',frame,flush=True)
(OUT/'cold-results.json').write_text(json.dumps(dict(status='PASS',cases=reports,scope='One controller-only new game with 98 custom discoveries and five added ships; native 50/10 selector matches independent model.'),indent=2),encoding='utf-8')
