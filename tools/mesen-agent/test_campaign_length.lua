-- Direct native year-rollover boundary tests. No calendar/aging routine stubs.
local current=0;local loaded=false;local oldAges={}
local function nextcase()
 current=current+1
 local c=CONFIG.cases[current]
 if not c then finish(true,'All '..#CONFIG.cases..' native annual deadline/aging boundary cases');return end
 w(0x25FB,c.hero)
 w(0xA05A,c.before);w(0xA05B,11);w(0xA05C,30);w(0x2013,11);w(0x9F04,0)
 for i=0,119 do oldAges[i]=r(0x25FC+i*50+42)end
 call(0xC100C8)
end
local hook
hook=emu.addMemoryCallback(guard(function()
 emu.removeMemoryCallback(hook,emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
 local f=assert(io.open(CONFIG.checkpoint,'rb'));local data=f:read('*a');f:close()
 emu.loadSavestate(data);loaded=true
end),emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
on_exec(0xC08000,function()if loaded and current==0 then nextcase()end end)
on_exec(0xE00FFF,function()
 local c=CONFIG.cases[current]
 check(r(0xA05A)==c.before+1,'Year did not advance')
 check(r(0x9F04)==c.gameover,'Wrong deadline outcome for year '..(c.before+1502)..' hero '..c.hero)
 for i=0,119 do check(r(0x25FC+i*50+42)==(oldAges[i]+1)%256,'Character aging changed at '..i)end
 check(r(0x2013)==0,'January rollover stopped working')
 nextcase()
end)
