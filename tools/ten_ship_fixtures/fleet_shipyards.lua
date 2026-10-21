-- Real shipyard stock/gating routine; UI calls are stubbed at their boundaries.
local cases={}
for group=0,10 do
 for _,industry in ipairs({0,199,200,499,500,549,550,649,650,799,800,899,900,949,950,999,1000}) do
  table.insert(cases,{group=group,industry=industry,port=0})
 end
end
for port=0,99 do
 local group=emu.read(0xC8DA7F+port*37+34,emu.memType.snesMemory)
 for _,industry in ipairs({0,199,200,499,500,549,550,649,650,799,800,899,900,949,950,999,1000}) do
  table.insert(cases,{group=group,industry=industry,port=port})
 end
end
local current=0
-- Actual fixed-capital industry values, not only synthetic threshold levels.
for _,port in ipairs({0,1,2,8,29,33,77}) do
 local address=0xC8DA7F+port*37
 local industry=emu.read(address+4,emu.memType.snesMemory)+256*emu.read(address+5,emu.memType.snesMemory)
 table.insert(cases,{port=port,industry=industry,group=emu.read(address+34,emu.memType.snesMemory)})
end
local seen=false
local function w(p,v) emu.write(p,v,emu.memType.snesWorkRam) end
local function w16(p,v) w(p,v%256);w(p+1,math.floor(v/256)) end
local function r(p) return emu.read(p,emu.memType.snesWorkRam) end
local function r16(p) return r(p)+256*r(p+1) end
local function rom(p) return emu.read(p,emu.memType.snesMemory) end
local function rtl()
 local sp=emu.getState()['cpu.sp']
 emu.setState({['cpu.sp']=sp+3,['cpu.pc']=(r16(sp+1)+1)%65536,['cpu.k']=r(sp+3)})
end
emu.addMemoryCallback(rtl,emu.callbackType.exec,0xC24A5B,0xC24A5B,emu.cpuType.snes)
emu.addMemoryCallback(function()
 local t=cases[current];local sp=emu.getState()['cpu.sp'];local expected={}
 for i=0,15 do
  local id=rom(0xE00B00+t.group*16+i)
  if id~=255 then
   local address=id<25 and 0xC8CE27+id*12 or 0xE4155E+(id-25)*12
   local allowed=id<25 or rom(0xE40000+t.port*14+id-25)==1
   if allowed and rom(address)*10<=t.industry then table.insert(expected,id+40+(id>=35 and 1 or 0)) end
  end
 end
 assert(r16(sp+4)==0x28E,'wrong menu')
 assert(r16(sp+6)==#expected,string.format('group %d industry %d: count expected %d got %d',t.group,t.industry,#expected,r16(sp+6)))
 for i,id in ipairs(expected) do assert(r16(0xA060+(i-1)*2)==id,'wrong regional hull entry') end
 seen=true;w16(0x100,0xFFFF);rtl()
end,emu.callbackType.exec,0xC2843B,0xC2843B,emu.cpuType.snes)
local function nextcase()
 current=current+1
 if current>#cases then emu.log('PASS: '..#cases..' regional industry boundary cases');emu.stop(0);return end
 local t=cases[current];seen=false
 w(0x601,0xFE);w(0x602,0x0F);w(0x603,0xE0)
 for i=0,517 do w(0x6EC+i,rom(0xE41400+i)) end
 for i=0,299 do w(0x7230+i,rom(0xC8CE27+i)) end
 for i=0,36 do w(0x7E88+i,rom(0xC8DA7F+i)) end
 w16(0xE80C,0x7E88);w16(0x7E8C,t.industry);w(0x7E88+34,t.group)
 w16(0x2016,t.port)
 emu.setState({['cpu.pc']=0x2128,['cpu.k']=0xC8,['cpu.sp']=0x600,
 ['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 assert(seen,'shipyard menu was not reached');nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
nextcase()
