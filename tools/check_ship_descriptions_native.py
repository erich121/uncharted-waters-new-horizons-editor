"""Run native message lookup/formatting for stock and independent shipyard text."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
import ship_descriptions as sd
OUT=ROOT/'output/ship-editor/descriptions-preview/native'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    for added in (0,10):
        project=ShipProject(ROOT/'New Horizons (USA).zip')
        for _ in range(added):project.add_ship(10)
        for i in range(len(project.ships)):
            sd.set_text(project,i,('Ship %02d: '%i)+'A'*(217 if i==len(project.ships)-1 else 20+i))
        if added:
            import discovery_content as dc
            entry=dc.capture(project,0);dc.load(project,entry,0)
            project.fleet_control=True;project.repair_safeguard=True
        data=project.build()[0];rom=OUT/f'descriptions-{added}.sfc';rom.write_bytes(data)
        cases=[]
        for i in range(len(project.ships)):cases.append((sd.FIRST_ID+i,sd.text(project,i).encode('ascii')))
        # Exercise every original ship message independently of its overridden slot.
        for i in range(25):
            mid=int.from_bytes(project.rom[0x8fb3f+i*2:0x8fb41+i*2],'little')
            at=int.from_bytes(project.rom[sd.PRIMARY+mid*3:sd.PRIMARY+mid*3+3],'little')-0xc00000
            cases.append((mid,project.rom[at:project.rom.index(b'\0',at)]))
        for i in (0,467):
            at=int.from_bytes(project.rom[sd.SECONDARY+i*3:sd.SECONDARY+i*3+3],'little')-0xc00000
            raw=project.rom[at:project.rom.index(b'\0',at)]
            if b'%'not in raw and len(raw)<=226:cases.append((900+i,raw))
        expected=OUT/f'expected-{added}.bin';expected.write_bytes(b''.join(raw.ljust(256,b'\0')for _,raw in cases))
        lua=r'''local started=false;local frames=0;local n=0;local mode=0
local ids=@@IDS@@
local f=assert(io.open(@@EXPECTED@@,'rb'));local expected=f:read('*a');f:close()
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function nextcase()
 n=n+1
 if n>#ids then
  n=1;mode=mode+1
  if mode==2 then emu.log('PASS native ship descriptions '..(#ids*2)..' lookups, both presenters, stock fallback, buffer and stack guards');emu.stop(0);return end
 end
 for i=0,255 do w(0xA273+i,0xCC)end
 w(0xA272,0xA5);w(0xA373,0x5A)
 w16(0x601,0x0FFE);w(0x603,0xE0)
 w16(0x604,3);w16(0x606,ids[n]);w16(0x608,0);w16(0x60A,0)
 emu.setState({['cpu.pc']=mode==0 and 0x75CF or 0x752C,['cpu.k']=0xC1,['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
local function check()
 local raw=expected:sub((n-1)*256+1,n*256);local length=assert(raw:find('\0',1,true))-1
 for i=1,length do assert(r(0xA273+i-1)==raw:byte(i),'Text mismatch '..n..' byte '..i)end
 assert(r(0xA273+length)==0,'Missing terminator')
 assert(r(0xA272)==0xA5 and r(0xA373)==0x5A,'Buffer overrun')
 assert(emu.getState()['cpu.sp']==0x600,'Stack imbalance')
 nextcase()
end
-- Stop before presentation/input; lookup and native formatter ran unmodified.
emu.addMemoryCallback(function()if mode==0 then check()end end,emu.callbackType.exec,0xC1765B,0xC1765B,emu.cpuType.snes)
emu.addMemoryCallback(function()if mode==1 then check()end end,emu.callbackType.exec,0xC175BE,0xC175BE,emu.cpuType.snes)
emu.addEventCallback(function()frames=frames+1 end,emu.eventType.endFrame)
emu.addMemoryCallback(function()if frames>=60 and not started then started=true;nextcase()end end,emu.callbackType.exec,0xC08000,0xC08000,emu.cpuType.snes)
'''.replace('@@IDS@@','{'+','.join(str(i)for i,_ in cases)+'}').replace('@@EXPECTED@@',json.dumps(expected.as_posix()))
        script=OUT/f'native-{added}.lua';script.write_text(lua,encoding='utf-8')
        result=subprocess.run([str(ROOT/'tools/mesen-agent/runtime/mesen-agent.exe'),str(rom),'--home',str(OUT/f'home-{added}'),'--lua',str(script),'--lua-allow-io','--frames','3000','--timeout','55'],capture_output=True,text=True)
        log=result.stdout+result.stderr;(OUT/f'events-{added}.jsonl').write_text(log,encoding='utf-8')
        assert result.returncode==0 and 'PASS native ship descriptions' in log and 'lua_error'not in log,log
        results.append(dict(added=added,cases=len(cases)*2,status='PASS'))
        print('PASS native descriptions',added,len(cases)*2,flush=True)
    (OUT/'results.json').write_text(json.dumps(dict(status='PASS',cases=results,scope='Native message lookup and formatter, both presenters; rendering/input tail intercepted, not a played shipyard transaction.'),indent=2),encoding='utf-8')

if __name__=='__main__':main()
