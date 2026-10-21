local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function r16(p)return r(p)+256*r(p+1)end
local function rom(p)return emu.read(p,emu.memType.snesMemory)end
local function rw(p)return rom(p)+256*rom(p+1)end
local cases={}
for kind=1,3 do for _,value in ipairs({0,49,50,74,75,499,500,999,1000,1500,2000})do for roll=0,2 do cases[#cases+1]={kind=kind,value=value,roll=roll}end end end
cases[#cases+1]={kind=1,value=1000,roll=2,preserve=true}
local current=0;local generated=0
local function ret()local sp=emu.getState()['cpu.sp'];emu.setState({['cpu.sp']=sp+3,['cpu.pc']=(r16(sp+1)+1)%65536,['cpu.k']=r(sp+3)})end
emu.addMemoryCallback(function()w16(0x100,cases[current].roll);ret()end,emu.callbackType.exec,0xC10A57,0xC10A57,emu.cpuType.snes)
local function nextcase()
 current=current+1
 if current>#cases then emu.log('PASS: '..#cases..' whole native NPC refill runs; '..generated..' generated ships, national value budgets, tiers, random choices, and loadouts');emu.stop(0);return end
 local t=cases[current]
 for i=0,299 do w(0x7230+i,rom(0xC8CE27+i))end
 for i=0,1624 do w(0x6BD7+i,rom(0xC8C7CE+i))end
 for country=0,6 do w16(0x24C0+country*32,t.value)end
 for id=0,69 do local p=rw(0xCAD030+id*2);for j=0,132 do w(p+j,0)end;w(p+42,255)end
 if t.preserve then local p=rw(0xCAD030+2)+43;for j=0,8 do w(p+j,({9,0,60,70,60,80,7,49,16})[j+1])end end
 w16(0x601,0x0FFE);w(0x603,0xE0)
 emu.setState({['cpu.pc']=t.kind==1 and 0x1666 or t.kind==2 and 0x1837 or 0x1A0E,['cpu.k']=0xC9,['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 local t=cases[current];local table=t.kind==1 and 0xC9EC4D or t.kind==2 and 0xC9EC77 or 0xC9ECA1;local base=t.kind==2 and 48 or 40
 for country=0,6 do
  local tier=math.min(2,math.floor(t.value/500));local packed=rw(table+country*6+tier*2);local template=base+math.floor(packed/2^(4*t.roll))%16
  local spec=0xC8CE27+(template-40)*12;local source=0xC8C7CE+template*25
  local n=0
  for id=0,9 do local p=rw(0xCAD030+(country*10+id)*2)
   for j=0,9 do local f=p+43+j*9
    if math.floor(r(f+8)/16)%4==1 then
     assert((t.kind==1 and id>=1 and id<=4) or(t.kind==2 and id>=5 and id<=6)or(t.kind==3 and id>=7 and id<=9),'wrong fleet category written')
     if t.preserve and country==0 and id==1 and j==0 then
      for k=0,8 do assert(r(f+k)==({9,0,60,70,60,80,7,49,16})[k+1],'existing ship overwritten')end
     else
     assert(r(f+7)==template,'wrong national/tier/random hull')
     assert(r(f+2)==rom(spec+1) and r(f+3)==rom(spec+1),'wrong current/max hull condition')
     assert(r(f+4)==rom(spec+2) and r(f+5)==rom(spec+3),'wrong sailing stats')
     assert(r(f+6)==rom(source+20),'wrong fitted actual guns')
     assert(r16(f)==rw(source+21),'wrong actual crew')
     end
     n=n+1;generated=generated+1
    end
   end
  end
  local budget=5+math.floor(t.value/(t.kind==1 and 50 or 75))
  if t.kind==3 then emu.log(string.format('Third category value%d country%d roll%d count%d',t.value,country,t.roll,n)) else
  local expected=math.min(t.kind==1 and 40 or 20,budget)+(t.preserve and country==0 and 1 or 0)
  assert(n==expected,string.format('case%d country%d kind%d val%d got%d expected%d',current,country,t.kind,t.value,n,expected))
  end
 end
 nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
local frames=0;emu.addEventCallback(function()frames=frames+1;if frames==1500 then local s=emu.getState();emu.log(string.format('STALL case%d PC%02X:%04X',current,s['cpu.k'],s['cpu.pc']));emu.stop(1)end end,emu.eventType.endFrame)
nextcase()
