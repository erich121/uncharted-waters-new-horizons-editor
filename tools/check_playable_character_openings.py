"""Cold controller-only openings for all six edited playable characters."""
import concurrent.futures
import json
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'mod_tool'))
from backend import ShipProject
from sailors import ATTRIBUTES
OUT=ROOT/'output/ship-editor/playable-levels/native'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=ShipProject(ROOT/'New Horizons (USA).zip')
    for i in range(6):p.update_character(i,dict(**{key:50+(i*7+j*11)%51 for j,key in enumerate(ATTRIBUTES)},navigation_level=[1,100,25,75,50,99][i],battle_level=[100,1,75,25,99,50][i],skills=[0,31,1,4,16,8][i]))
    for _ in range(10):p.add_ship(10)
    p.fleet_control=True;p.repair_safeguard=True
    rom=OUT/'edited-protagonists.sfc';rom.write_bytes(p.build()[0]);p.save_project(OUT/'edited-protagonists.json')
    def run(hero):
        folder=OUT/str(hero);folder.mkdir(exist_ok=True)
        steps=[('none',2400),('a',8),('none',240),('a',8),('none',240),('right',8),('none',12),('a',8),('none',240)]
        for _ in range(hero%3):steps += [('right',8),('none',24)]
        if hero>=3:steps += [('down',8),('none',24)]
        steps += [('a',8),('none',240),('a',8),('none',240),('b',8),('none',180),('a',8),('none',540)]
        steps += [('a',8),('none',72)]*40
        frames=sum(n for _,n in steps)+60
        lua=r'''local steps=@@STEPS@@;local frame=0;local commands=0;local initialized=false
local hero=@@HERO@@
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function word(p)return r(p)+256*r(p+1)end
local function pr(p)return emu.read(p,emu.memType.snesPrgRom)end
local function verify()
 for id=0,5 do
  for offset=28,37 do assert(r(0x25FC+id*50+offset)==pr(0x881F3+id*50+offset),'Opening overwrote attribute/level '..id..'/'..offset..' frame '..frame)end
  assert(r(0x25FC+id*50+48)==pr(0x881F3+id*50+48),'Opening overwrote skills '..id..' frame '..frame)
 end
end
emu.addMemoryCallback(function()commands=commands+1 end,emu.callbackType.exec,0xC9B779,0xC9B779,emu.cpuType.snes)
emu.addEventCallback(function()frame=frame+1 end,emu.eventType.startFrame)
emu.addEventCallback(function()
 local input={};for _,key in ipairs({'a','b','x','y','up','down','left','right','l','r','start','select'})do input[key]=false end
 local n=frame;for _,s in ipairs(steps)do if n<=s[2]then if s[1]~='none'then input[s[1]]=true end;break end;n=n-s[2]end
 emu.setInput(input,0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 if frame==60 then verify();initialized=true end
 if initialized and frame%120==0 then verify()end
 if frame==@@FRAMES@@ then
  verify();assert(r(0x25FB)==hero,'Wrong protagonist selected: '..r(0x25FB)..' expected '..hero)
  assert(word(0xE808)==0x25FC+hero*50,'Active actor pointer is wrong')
  assert(commands>10,'Opening scene did not execute')
  local f=assert(io.open(@@IMAGE@@,'wb'));f:write(emu.takeScreenshot());f:close()
  f=assert(io.open(@@REPORT@@,'w'));f:write(string.format('{"hero":%d,"frames":%d,"script_commands":%d,"port":%d,"stats_preserved":true,"skills_preserved":true,"levels_preserved":true}',hero,frame,commands,word(0x2016)));f:close()
  emu.log('PASS edited playable opening '..hero..' commands '..commands..' frames '..frame);emu.stop(0)
 end
end,emu.eventType.endFrame)
'''.replace('@@STEPS@@','{'+','.join('{'+json.dumps(b)+','+str(n)+'}'for b,n in steps)+'}').replace('@@HERO@@',str(hero)).replace('@@FRAMES@@',str(frames)).replace('@@IMAGE@@',json.dumps((folder/'opening.png').as_posix())).replace('@@REPORT@@',json.dumps((folder/'receipt.json').as_posix()))
        script=folder/'opening.lua';script.write_text(lua,encoding='utf-8')
        home=tempfile.mkdtemp(prefix='home-',dir=folder)
        result=subprocess.run([sys.executable,str(ROOT/'tools/gameplay_test_pack/core_host.py'),str(rom),'--runtime',str(ROOT/'tools/mesen-agent/runtime'),'--home',home,'--lua',str(script),'--frames',str(frames+100),'--timeout','140','--screenshot',str(folder/'last-frame.png')],capture_output=True,text=True,timeout=155)
        log=result.stdout+result.stderr;(folder/'events.jsonl').write_text(log,encoding='utf-8')
        assert result.returncode==0 and 'PASS edited playable opening'in log,log
        receipt=json.loads((folder/'receipt.json').read_text());receipt['status']='PASS'
        print('PASS opening',hero,receipt['script_commands'],flush=True)
        return receipt
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(run,range(6)))
    (OUT/'results.json').write_text(json.dumps(dict(status='PASS',cases=results,scope='Six cold starts using controller input only, through initial story dialogue. All66 edited stat/skill/level fields compared throughout; not full campaigns or a proof of every later event.'),indent=2),encoding='utf-8')

if __name__=='__main__':main()
