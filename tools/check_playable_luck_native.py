"""Exercise conditional fixed Luck, all actor IDs, and native register/stack ABI."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
OUT=ROOT/'output/ship-editor/playable-preview/luck-native'


def main():
    OUT.mkdir(parents=True,exist_ok=True);results=[]
    for added in (0,10):
        p=ShipProject(ROOT/'New Horizons (USA).zip')
        for _ in range(added):p.add_ship(10)
        for i,value in [(0,50),(2,0),(5,100)]:p.update_character(i,dict(luck=value))
        if added:
            import discovery_content as dc
            dc.load(p,dc.capture(p,0),0)
            import ship_descriptions as sd
            sd.set_text(p,34,'An independent ship description.')
            p.fleet_control=True;p.repair_safeguard=True
        rom=OUT/f'luck-{added}.sfc';rom.write_bytes(p.build()[0])
        lua=r'''local current=-1;local frames=0;local started=false
local fixed={[0]=50,[2]=0,[5]=100};local rolls={0,40,50,100,255}
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function nextcase()
 current=current+1
 if current==1280 then emu.log('PASS 1280 fixed/native Luck cases, all256 actor IDs, unchanged draw, stack, flags, X, A high byte');emu.stop(0);return end
 local id=math.floor(current/5);local roll=rolls[current%5+1]
 w(0x25FB,id);w16(0x10C,0x1800);w16(0x100,0x3400+roll);w(0x1823,0xCC)
 emu.setState({['cpu.pc']=0x4E61,['cpu.k']=0xC7,['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x65,['cpu.a']=0xABCD,['cpu.x']=0x1234,['cpu.y']=0x4321,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 local id=math.floor(current/5);local roll=rolls[current%5+1];local expected=fixed[id]or roll
 assert(r(0x1823)==expected,'Luck result mismatch '..current)
 assert(r(0x100)==roll and r(0x101)==0x34,'Native random result modified')
 local s=emu.getState()
 assert(s['cpu.sp']==0x600 and s['cpu.x']==0x1234 and s['cpu.y']==0x23,'Register/stack mismatch')
 assert(s['cpu.a']==0xAB00+expected and s['cpu.ps']==0x65,'Accumulator or flags mismatch')
 nextcase()
end,emu.callbackType.exec,0xC74E68,0xC74E68,emu.cpuType.snes)
emu.addEventCallback(function()frames=frames+1 end,emu.eventType.endFrame)
emu.addMemoryCallback(function()if frames>=60 and not started then started=true;nextcase()end end,emu.callbackType.exec,0xC08000,0xC08000,emu.cpuType.snes)
'''
        script=OUT/f'luck-{added}.lua';script.write_text(lua,encoding='utf-8')
        run=subprocess.run([str(ROOT/'tools/mesen-agent/runtime/mesen-agent.exe'),str(rom),'--home',str(OUT/f'home-{added}'),'--lua',str(script),'--frames','3000','--timeout','55'],capture_output=True,text=True,timeout=65)
        log=run.stdout+run.stderr;(OUT/f'events-{added}.jsonl').write_text(log,encoding='utf-8')
        assert run.returncode==0 and 'PASS 1280 fixed/native Luck' in log and 'lua_error'not in log,log
        results.append(dict(status='PASS',added=added,cases=1280));print('PASS Luck ABI',added,flush=True)
    (OUT/'results.json').write_text(json.dumps(dict(status='PASS',cases=results),indent=2),encoding='utf-8')

if __name__=='__main__':main()
