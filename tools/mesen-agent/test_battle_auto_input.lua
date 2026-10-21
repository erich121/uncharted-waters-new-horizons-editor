-- Native toggle helper execution; native input and message rendering stubbed.
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function r16(p)return r(p)+256*r(p+1)end
local function ret()
 local sp=emu.getState()['cpu.sp']
 emu.setState({['cpu.sp']=sp+3,['cpu.pc']=(r16(sp+1)+1)%65536,['cpu.k']=r(sp+3)})
end
local cases={}
local keys={0,0x2000,0x10,0x20,0x30,0x2010,0x2020,0x2030}
for mode=0,1 do for latch=0,1 do for menu=0,1 do for _,held in ipairs(keys)do
 cases[#cases+1]={mode=mode,latch=latch,menu=menu,held=held}
end end end end
local current=0;local notices=0;local finished=false
local function nextcase()
 current=current+1
 if current>#cases then
  finished=true;emu.log('PASS: '..#cases..' native input/mode/debounce/guard cases');emu.stop(0);return
 end
 local t=cases[current];t.notice=0
 w16(0x8F2,t.mode);w16(0x8F4,t.latch);w16(0x8F6,t.menu);w16(0xB56,t.held)
 w16(0xF464,0xA800);w(0xF466,0x7E);w16(0xE806,0x41BB)
 w16(0x601,0x0FFE);w(0x603,0xE0);w16(0x604,0x1357)
 emu.setState({['cpu.pc']=0x88D0,['cpu.k']=0xE1,['cpu.sp']=0x600,
 ['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 assert(r16(emu.getState()['cpu.sp']+4)==0x1357,'input wrapper changed native argument')
 w16(0x100,0x8000);ret()
end,emu.callbackType.exec,0xC219C9,0xC219C9,emu.cpuType.snes)
emu.addMemoryCallback(function()
 cases[current].notice=cases[current].notice+1;ret()
end,emu.callbackType.exec,0xE18940,0xE18940,emu.cpuType.snes)
emu.addMemoryCallback(function()
 if finished then return end
 local t=cases[current];local held=t.held>=0x2000;local toggle=held and t.menu==1 and t.latch==0
 assert(r16(0x8F2)==(toggle and 1-t.mode or t.mode),'wrong toggle mode')
 local expectedLatch=not held and 0 or (t.menu==1 and 1 or t.latch)
 assert(r16(0x8F4)==expectedLatch,'wrong release latch')
 assert(t.notice==(toggle and 1 or 0),'unexpected acknowledgement')
 assert(r16(0x100)==((held and t.menu==1)and 0 or 0x8000),'input result not preserved/consumed')
 assert(emu.getState()['cpu.sp']==0x603,'unbalanced helper stack')
 assert(r16(0x8F6)==t.menu,'guard changed')
 assert(r16(0xF464)==0xA800 and r16(0xE806)==0x41BB,'actor identity changed')
 nextcase()
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
nextcase()
