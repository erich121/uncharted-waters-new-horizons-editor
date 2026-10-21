local loaded=false;local current=0
local function nextcase()
 current=current+1;local c=CONFIG.cases[current]
 if not c then finish(true,'All '..#CONFIG.cases..' native ship construction timers');return end
 local spec=c.id<25 and 0x7230+c.id*12 or 0x87A+(c.id-25)*12
 w(spec+1,c.hull);w16(0x12E,spec);w16(0xE80C,0x7E88);w16(0x7E8C,c.industry)
 w(0x7EAB,255);w(0x7EAC,0xDD)
 emu.setState({['cpu.pc']=0x2463,['cpu.k']=0xC8,['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
local hook
hook=emu.addMemoryCallback(guard(function()
 emu.removeMemoryCallback(hook,emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
 local f=assert(io.open(CONFIG.checkpoint,'rb'));local data=f:read('*a');f:close();emu.loadSavestate(data);loaded=true
end),emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
on_exec(0xC08000,function()if loaded and current==0 then nextcase()end end)
on_exec(0xC824B2,function()
 local c=CONFIG.cases[current]
 local expected=CONFIG.enabled and 0 or math.floor((100-math.floor(c.industry/50))*c.hull/100)
 check(r(0x7EAB)==expected,'Wrong construction days for hull '..c.id)
 check(r(0x7EAC)==0xDD,'Adjacent order record changed')
 nextcase()
end)
