-- Isolated native price conversion; no shop transaction or save/load claim.
local loaded=false;local current=0;local c
local function nextcase()
 current=current+1;c=CONFIG.cases[current]
 if not c then finish(true,'Native item base-price and weapon-rank calculations passed');return end
 local at=0xC8EBC7+c.item*23
 for i=0,22 do w(0xB800+i,rom(at+i))end
 w16(0x124,0xB800)
 call(c.rank and 0xC7BC89 or 0xC7D2F4)
end
local hook
hook=emu.addMemoryCallback(guard(function()
 emu.removeMemoryCallback(hook,emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
 local f=assert(io.open(CONFIG.checkpoint,'rb'));local data=f:read('*a');f:close()
 emu.loadSavestate(data);loaded=true
end),emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
on_exec(0xC08000,function()if loaded and current==0 then nextcase()end end)
on_exec(0xC7D30A,function()
 if not c or c.rank then return end
 check(r16(0x100)+r16(0x102)*65536==c.expected,'Native item price mismatch')
 nextcase()
end)
on_exec(0xC7BCBC,function()
 if not c or not c.rank then return end
 check(r16(0x100)==c.expected,'Native weapon rank mismatch')
 nextcase()
end)
