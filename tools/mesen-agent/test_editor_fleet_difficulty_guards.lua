-- Isolated helper ABI/guards. No native generator or battle bodies stubbed.
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function r16(p)return r(p)+256*r(p+1)end
local cases={}
for tier=0,2 do for _,nation in ipairs({0,1,2,3,4,5,6,7,255})do for _,slot in ipairs({0,1,2,3,4,9})do
for _,flags in ipairs({0,1,16,128})do for player=0,1 do for _,template in ipairs({49,50,51,55,60,65,69})do
 cases[#cases+1]={tier=tier,nation=nation,slot=slot,flags=flags,player=player,template=template}
end end end end end end
local current=0
local function nextcase()
 current=current+1
 if current>#cases then emu.log('PASS: '..#cases..' difficulty tier/nation/position/flags/player/template guards and ABI cases');emu.stop(0);return end
 local t=cases[current]
 w16(0x601,0x0FFE);w(0x603,0xE0);w16(0x606,t.tier);w16(0x608,t.nation);w16(0x60C,t.slot)
 w16(0x126,0x1800);w16(0x1829,t.flags);w16(0xE806,t.player==1 and 0x1800 or 0x2000);w16(0x100,t.template)
 emu.setState({['cpu.pc']=0xA000,['cpu.k']=0xE1,['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false,['cpu.x']=0x1234})
end
emu.addMemoryCallback(function()
 local t=cases[current];local expected=t.template
 if t.tier==2 and t.nation<6 and t.slot==0 and t.flags<16 and t.player==0 then
  if expected==50 then expected=55 elseif expected==51 then expected=60 end
 end
 assert(r16(0x100)==expected,'wrong difficulty selection, case'..current)
 local state=emu.getState()
 assert(state['cpu.sp']==0x603,'unbalanced stack');assert(state['cpu.x']==0x1234,'changed X')
 assert(state['cpu.y']==7 and state['cpu.ps']&0x20~=0,'native A8/Y store contract lost')
 nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
nextcase()
