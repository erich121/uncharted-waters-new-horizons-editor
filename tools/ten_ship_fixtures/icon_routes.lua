-- Actual sea descriptor and battle tile writer; no renderer stubs.
local root='__NH_PROJECT_ROOT__/'
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function r16(p)return r(p)+256*r(p+1)end
local f=assert(io.open(root..'output/ship-sprite-research/rendered-battle/00-none-wram.bin','rb'));local saved=f:read('*a');f:close()
for i=0,#saved-1 do w(i,saved:byte(i+1))end
-- This older rendered checkpoint predates the current reset RAM layout.
-- Initialize immutable extra records as the current ROM's reset code does.
for i=0,517 do w(0x6EC+i,emu.read(0x241400+i,emu.memType.snesPrgRom))end
local cases={}
for class=0,4 do for direction=0,7 do for _,attributes in ipairs({0x2800,0x2A00})do
 cases[#cases+1]={kind='sea',class=class,direction=direction,attributes=attributes}
end end end
for hull=0,38 do for direction=0,5 do for group=0,3 do
 cases[#cases+1]={kind='battle',hull=hull,direction=direction,group=group}
end end end
local current=0
local function call(pc,args)
 w16(0x601,0x0FFE);w(0x603,0xE0)
 for i,v in ipairs(args)do w16(0x604+(i-1)*2,v)end
 emu.setState({['cpu.pc']=pc%65536,['cpu.k']=math.floor(pc/65536),['cpu.sp']=0x600,
 ['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
local function nextcase()
 current=current+1
 if current>#cases then emu.log('PASS:80 sea icon descriptors and936 native battle tile writes; Berrio class4, all39 hulls,6 battle facings,4 fleet groups');emu.stop(0);return end
 local t=cases[current]
 if t.kind=='sea'then call(0xC20FD7,{0,t.class,t.attributes,12,34,t.direction})
 else
  w16(0xA702,0xA800);w(0xA70C,t.direction);w(0xA70F,t.group*64+3)
  w(0xA807,40+t.hull+(t.hull>=35 and 1 or 0))
  call(0xCD0B09,{0xA700,0x7E,0x4000,0x7F,0x4002,0x7F})
 end
end
emu.addMemoryCallback(function()
 local t=cases[current]
 if t.kind=='sea'then
  local base=0xC0+t.class*64+t.direction*4+(t.direction>=4 and 16 or 0)
  assert(r16(0xE939)==(base|t.attributes),'sea tile mismatch')
  assert(r(0xE937)==12 and r(0xE938)==34 and r(0xE93B)==2 and r(0xE93C)==t.class,'sea descriptor changed')
 else
  local class=emu.read(0x213400+t.hull,emu.memType.snesPrgRom)
  local direction=({0,1,3,4,5,7})[t.direction+1]
  local base=0xC0+class*64+direction*4+(direction>=4 and 16 or 0)
  local attributes=t.group<2 and 0x2A00 or 0x2800
  assert(r16(0x14000)==80+t.group*10+3,'battle actor identity mismatch')
  assert(r16(0x14002)==(base|attributes),string.format('battle tile mismatch hull%d direction%d actual%04X expected%04X',t.hull,t.direction,r16(0x14002),(base|attributes)))
 end
 assert(emu.getState()['cpu.sp']==0x603,'native route stack unbalanced')
 nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
nextcase()
