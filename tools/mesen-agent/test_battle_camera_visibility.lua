-- Native focus/viewport logic and real manual-entry wrapper. Rendering bodies
-- are stubbed; the native camera routine and coordinate clamping execute.
local cases={}
for _,mate in ipairs({false,true}) do for y=0,31 do for x=0,31 do for _,old in ipairs({{0,0},{17,19},{8,9}}) do
 cases[#cases+1]={x=x,y=y,old=old,mate=mate}
end end end end
for y=0,31 do for x=0,31 do for _,old in ipairs({{0,0},{17,19},{8,9}}) do
 cases[#cases+1]={x=x,y=y,old=old,mate=false,previous='other'}
end end end
for _,xy in ipairs({{0,0},{12,12},{20,20},{31,31}}) do for _,old in ipairs({{0,0},{17,19},{8,9}}) do
 cases[#cases+1]={x=xy[1],y=xy[2],old=old,mate=false,previous='same'}
end end
local current=0;local redraws=0;local transitions=0;local focusCalls=0
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function r16(p)return r(p)+256*r(p+1)end
local function ret()
 local sp=emu.getState()['cpu.sp']
 emu.setState({['cpu.sp']=sp+3,['cpu.pc']=(r16(sp+1)+1)%65536,['cpu.k']=r(sp+3)})
end
for _,address in ipairs({0xC08000,0xCD2A86})do
 emu.addMemoryCallback(ret,emu.callbackType.exec,address,address,emu.cpuType.snes)
end
emu.addMemoryCallback(function()
 local t=cases[current];local sp=emu.getState()['cpu.sp']
 assert(r16(sp+4)==t.old[1]*2 and r16(sp+6)==t.old[2]*2,'native transition lost old camera origin')
 assert(r16(sp+8)==t.cx*2 and r16(sp+10)==t.cy*2,'native transition selected wrong new camera origin')
 transitions=transitions+1;ret()
end,emu.callbackType.exec,0xCD39C1,0xCD39C1,emu.cpuType.snes)
emu.addMemoryCallback(function()
 local t=cases[current]
 assert(r(0xF492)==t.cx and r(0xF493)==t.cy,'redraw uses stale camera origin')
 redraws=redraws+1;ret()
end,emu.callbackType.exec,0xCD2D8F,0xCD2D8F,emu.cpuType.snes)
emu.addMemoryCallback(function()
 assert(cases[current].focus,'unnecessary flagship refocus');focusCalls=focusCalls+1
end,emu.callbackType.exec,0xC1A66B,0xC1A66B,emu.cpuType.snes)
local function nextcase()
 current=current+1
 if current>#cases then emu.log('PASS: '..#cases..' native mate-focus/flagship-visibility camera cases; focus calls='..focusCalls..', transitions='..transitions..', redraws='..redraws);emu.stop(0);return end
 local t=cases[current]
 t.visible=t.x>=t.old[1] and t.x<t.old[1]+15 and t.y>=math.max(t.old[2]-t.x%2,0) and t.y<math.min(t.old[2]+1-t.x%2,19)+12
 t.focus=t.mate or t.previous=='other' or not t.visible
 t.cx=t.focus and math.max(0,math.min(17,t.x-7)) or t.old[1]
 t.cy=t.focus and math.max(0,math.min(19,t.y-6)) or t.old[2]
 w16(0x8F8,t.previous=='other' and 0xA780 or t.previous=='same' and 0xA800 or 0);w16(0x8FA,t.previous and 0x7E or 0)
 w16(0xF461,0xA700);w(0xF463,0x7E);w16(0xA700,t.mate and 0xA780 or 0xA800);w(0xA702,0x7E)
 w(0xF492,t.old[1]);w(0xF493,t.old[2]);w16(0xF464,0xA800);w(0xF466,0x7E)
 w16(0xA804,t.y*32+t.x);w16(0xE806,0x41BB);w16(0xE808,0x25FC)
 emu.setState({['cpu.pc']=0xDC14,['cpu.k']=0xC1,['cpu.sp']=0x600,
 ['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 local t=cases[current]
 assert(r16(0x8F8)==0xA800 and r16(0x8FA)==0x7E,'last manual actor not recorded')
 assert(r(0xF492)==t.cx and r(0xF493)==t.cy,'manual menu opens before refocus')
 assert(emu.getState()['cpu.sp']==0x5FD,'camera wrapper changed manual-entry stack')
 assert(r16(0xF464)==0xA800 and r16(0xA804)==t.y*32+t.x,'camera changed selected ship or its position')
 assert(r16(0xE806)==0x41BB and r16(0xE808)==0x25FC,'camera changed player/captain identity')
 nextcase()
end,emu.callbackType.exec,0xC1D943,0xC1D943,emu.cpuType.snes)
nextcase()
