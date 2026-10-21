-- Owned allocation hook: all 35 IDs, with the native stack below reserved RAM.
local current=-1
local function w(p,v) emu.write(p,v,emu.memType.snesWorkRam) end
local function w16(p,v) w(p,v%256);w(p+1,math.floor(v/256)) end
local function r(p) return emu.read(p,emu.memType.snesWorkRam) end
local function r16(p) return r(p)+256*r(p+1) end
local function rom(p) return emu.read(p,emu.memType.snesMemory) end
local function nextcase()
 current=current+1
 if current==39 then emu.log('PASS: 39 owned allocation hooks');emu.stop(0);return end
 for i=0,517 do w(0x6EC+i,rom(0xE41400+i)) end
 for i=0,24 do w(0x6BD7+i,0xAA) end
 w(0x6BD7+18,current)
 w(0x601,0xFE);w(0x602,0x0F);w(0x603,0xE0);w16(0x615,current)
 w16(0x124,current<25 and 0x6BD7 or 0x6EC+(current-25)*25)
 w16(0x126,0x6BD7);w16(0x128,0x7230);w16(0x7231,30)
 emu.setState({['cpu.pc']=0x0E00,['cpu.k']=0xE0,['cpu.sp']=0x600,
 ['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 assert(r(0x6BD7+18)==current,'ship ID overwritten')
 for i=0,24 do
  local expected=i==18 and current or 0xAA
  if current>=25 and i>=20 then expected=rom(0xE41400+(current-25)*25+i) end
  assert(r(0x6BD7+i)==expected,string.format('ship %d byte %d',current,i))
 end
 assert(emu.getState()['cpu.a']==30,'durability replay changed')
 for i=0,517 do assert(r(0x6EC+i)==rom(0xE41400+i),'reserved record was overwritten') end
 nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
nextcase()
