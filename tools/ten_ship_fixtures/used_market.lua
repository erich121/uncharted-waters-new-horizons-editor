-- Exercise added used-stock generation, cached filtering and purchase guards.
local cases={}
local function rom(p) return emu.read(p,emu.memType.snesMemory) end
for port=0,99 do
 for n=0,13 do
  local required=rom(0xE40700+n*2)+256*rom(0xE40701+n*2)
  for _,industry in ipairs({math.max(0,required-1),required,1000}) do
   table.insert(cases,{kind='eligible',port=port,id=n+25,industry=industry})
   table.insert(cases,{kind='listing',port=port,id=n+25,industry=industry})
   table.insert(cases,{kind='purchase',port=port,id=n+25,industry=industry})
  end
 end
 for _,industry in ipairs({0,499,650,1000}) do
  for _,scenario in ipairs({{roll=1,pick=0,rare=0},{roll=0,pick=0,rare=0},{roll=0,pick=1,rare=9}}) do
   table.insert(cases,{kind='spawn',port=port,industry=industry,roll=scenario.roll,pick=scenario.pick,rare=scenario.rare})
  end
 end
end
local current=0
local rngCalls=0
local dp={}
local function w(p,v) emu.write(p,v,emu.memType.snesWorkRam) end
local function w16(p,v) w(p,v%256);w(p+1,math.floor(v/256)) end
local function r(p) return emu.read(p,emu.memType.snesWorkRam) end
local function r16(p) return r(p)+256*r(p+1) end
local function allowed(t,id)
 if id<25 or id>=39 then return false end
 local n=id-25;local group=rom(0xC8DA7F+t.port*37+34)
 local required=rom(0xE40700+n*2)+256*rom(0xE40701+n*2)
 return rom(0xE40000+t.port*14+n)==1 and rom(0xE40600+group*14+n)==1 and t.industry>=required
end
local function rtl()
 local sp=emu.getState()['cpu.sp']
 emu.setState({['cpu.sp']=sp+3,['cpu.pc']=(r16(sp+1)+1)%65536,['cpu.k']=r(sp+3)})
end
emu.addMemoryCallback(function()
 local t=cases[current];rngCalls=rngCalls+1;local sp=emu.getState()['cpu.sp'];local bound=r16(sp+4)
 local result=rngCalls==1 and t.roll or rngCalls==2 and t.pick%bound or t.rare
 assert(result<bound,'RNG fixture outside bound');w16(0x100,result);rtl()
end,emu.callbackType.exec,0xC10A57,0xC10A57,emu.cpuType.snes)
local function nextcase()
 current=current+1
 if current>#cases then emu.log('PASS: '..#cases..' used-market generation/eligibility/cache-filter/purchase-guard cases');emu.stop(0);return end
 local t=cases[current];rngCalls=0
 for i=0,517 do w(0x6EC+i,rom(0xE41400+i)) end
 for i=0,36 do w(0x7E88+i,rom(0xC8DA7F+t.port*37+i)) end
 w16(0xE80C,0x7E88);w16(0x7E8C,t.industry);w16(0x2016,t.port)
 for i=0,0x5F do w(0x100+i,(i*7+3)%256);dp[i]=r(0x100+i) end
 for i,id in ipairs({6,8,9,0,18}) do w(0x8CFB+i,id) end
 w(0x8D01,t.port);w(0x8D02,0xA5);w(0x8D03,0x5A)
 w(0x601,0xFE);w(0x602,0x0F);w(0x603,0xE0)
 local pc=0xE14500
 if t.kind=='spawn' then pc=0xE14700
 elseif t.kind=='listing' then pc=0xE14C00;w16(0x124,0x8CFC);w(0x126,0x7E);w(0x8CFC,t.id)
 elseif t.kind=='purchase' then pc=0xE14C40;w16(0x603,t.id) end
 emu.setState({['cpu.pc']=pc%65536,['cpu.k']=math.floor(pc/65536),['cpu.sp']=0x600,
 ['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.a']=t.id or 0x5555,
 ['cpu.x']=0x1234,['cpu.y']=0x5678,['cpu.emulationMode']=false})
end
local function check()
 local t=cases[current];local s=emu.getState();local pc=s['cpu.k']*65536+s['cpu.pc']
 if t.kind=='purchase' then
  assert(pc==(allowed(t,t.id) and 0xC827F3 or 0xC8273C),'purchase guard destination')
  assert(s['cpu.sp']==0x600,'purchase guard leaked stack')
 elseif t.kind=='eligible' then assert(s['cpu.a']==(allowed(t,t.id) and 1 or 0),'eligibility mismatch')
 elseif t.kind=='listing' then assert(s['cpu.a']==(allowed(t,t.id) and t.id or 255),'cached listing mismatch')
 elseif t.kind=='spawn' then
  local expected=9;local pool={}
  for id=25,38 do if allowed(t,id) then table.insert(pool,id) end end
  if t.roll==0 and #pool>0 then
   local candidate=pool[t.pick%#pool+1]
   if candidate~=34 or t.rare==0 then expected=candidate end
  end
  assert(r(0x8CFC)==6 and r(0x8CFD)==8 and r(0x8CFE)==expected,'generated special mismatch')
  assert(r(0x8CFF)==0 and r(0x8D00)==18,'cheap fallback was changed')
  assert(r(0x8D01)==t.port and r(0x8D02)==0xA5 and r(0x8D03)==0x5A,'cache metadata changed')
  for i=0,0x5F do assert(r(0x100+i)==dp[i],'spawn changed caller direct page') end
 end
 assert(s['cpu.x']==0x1234 and s['cpu.y']==0x5678,'caller index registers changed')
 for i=0,517 do assert(r(0x6EC+i)==rom(0xE41400+i),'reserved records changed') end
 nextcase()
end
for _,pc in ipairs({0xE00FFF,0xC827F3,0xC8273C}) do
 emu.addMemoryCallback(check,emu.callbackType.exec,pc,pc,emu.cpuType.snes)
end
nextcase()
