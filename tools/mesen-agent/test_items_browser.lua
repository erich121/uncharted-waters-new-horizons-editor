local root=@@ROOT@@
local ids=@@IDS@@
local f=assert(io.open(root..'expected.bin','rb'));local expected=f:read('*a');f:close()
local current=0;local stage='images';local frames=0;local done=false
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function r16(p)return r(p)+256*r(p+1)end
local function memory(mt,size)
 local b={};for i=0,size-1 do b[#b+1]=string.char(emu.read(i,mt))end;return table.concat(b)
end
local function nextcase()
 current=current+1
 if stage=='images'and current>#ids then emu.log(#ids..' native item pictures passed');stage='shops';current=1 end
 if stage=='shops'and current>4800 then done=true;emu.log('4800 native shop lists passed');emu.stop(0);return end
 w16(0x601,0x0FFE);w(0x603,0xE0)
 local pc=0xC13D7C
 if stage=='images'then w16(0x604,3);w16(0x606,3);w16(0x608,ids[current]+100)
 else
  pc=0xC70D39;w(0x2016,math.floor((current-1)/48));w(0xA05D,(current-1)%48)
  for i=0,7 do w16(0xA060+i*2,0xFFFF)end
 end
 emu.setState({['cpu.pc']=pc%65536,['cpu.k']=math.floor(pc/65536),['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 if current==0 or done then return end
 if stage=='images'then
  local raw=expected:sub((current-1)*544+1,(current-1)*544+512)
  local pal=expected:sub((current-1)*544+513,(current-1)*544+544)
  assert(memory(emu.memType.snesVideoRam,65536):find(raw,1,true),'native item tiles mismatch '..ids[current])
  assert(memory(emu.memType.snesCgRam,512):find(pal,1,true),'native item palette mismatch '..ids[current])
 else
  local city=math.floor((current-1)/48);local hour=(current-1)%48;local want={}
  local slots=hour>=4 and hour<6 and 4 or 3
  for slot=0,slots-1 do local id=r(0x7E88+city*37+29+slot);if id~=255 then want[#want+1]=id end end
  assert(r16(0x100)==#want,'shop count mismatch '..current)
  for i,id in ipairs(want)do assert(r16(0xA060+(i-1)*2)==id,'shop item mismatch '..current)end
 end
 nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
emu.addMemoryCallback(function()
 if current==0 and frames>=60 then
  for i=0,2299 do w(0x8FD0+i,emu.read(0xC8EBC7+i,emu.memType.snesMemory))end
  for i=0,3699 do w(0x7E88+i,emu.read(0xC8DA7F+i,emu.memType.snesMemory))end
  nextcase()
 end
end,emu.callbackType.exec,0xC08000,0xC08000,emu.cpuType.snes)
emu.addEventCallback(function()frames=frames+1 end,emu.eventType.endFrame)
