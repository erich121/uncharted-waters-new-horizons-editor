local root=@@ROOT@@
local cases=@@CASES@@

local f=assert(io.open(root..'expected.bin','rb'));local expected=f:read('*a');f:close()
local current=-1;local stage='images';local frames=0
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function memory(mt,size)
 local b={};for i=0,size-1 do b[#b+1]=string.char(emu.read(i,mt))end;return table.concat(b)
end
local function start(pc)
 emu.setState({['cpu.pc']=pc%65536,['cpu.k']=math.floor(pc/65536),['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
local function nextcase()
 current=current+1
 if stage=='images'and current>=98 then stage='requirements';current=0;emu.log('PASS: all98 discovery pictures and palettes match native rendering')end
 if stage=='images'then
  w16(0x601,0x0FFE);w(0x603,0xE0);w16(0x604,3);w16(0x606,3);w16(0x608,current)
  start(0xC13D7C)
 else
  if current>=#cases then emu.log('PASS: '..#cases..' native discovery score boundary cases');emu.stop(0);return end
  local t=cases[current+1]
  w16(0xE808,0x25FC);w(0x25FC+31,t.intuition);w(0x25FC+35,t.luck);w16(0xFDE9,t.friendship)
  w16(0x124,0x8D14);w(0x8D14+5,t.difficulty)
  start(0xC9DB72)
 end
end
emu.addMemoryCallback(function()
 if stage~='images'or current<0 then return end
 local raw=expected:sub(current*544+1,current*544+512)
 local pal=expected:sub(current*544+513,current*544+544)
 assert(memory(emu.memType.snesVideoRam,65536):find(raw,1,true),'native tiles mismatch '..current)
 assert(memory(emu.memType.snesCgRam,512):find(pal,1,true),'native palette mismatch '..current)
 nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
emu.addMemoryCallback(function()
 if stage~='requirements'then return end
 local t=cases[current+1];assert(emu.read(0x100,emu.memType.snesWorkRam)==t.expected,'score mismatch '..current)
 nextcase()
end,emu.callbackType.exec,0xC9DBE3,0xC9DBE3,emu.cpuType.snes)
emu.addMemoryCallback(function()if current<0 and frames>=60 then nextcase()end end,emu.callbackType.exec,0xC08000,0xC08000,emu.cpuType.snes)
emu.addEventCallback(function()frames=frames+1 end,emu.eventType.endFrame)
