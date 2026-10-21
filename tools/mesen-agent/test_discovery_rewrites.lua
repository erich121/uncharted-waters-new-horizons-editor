-- Controlled Stonehenge village fixture. Only setup writes RAM/CPU state.
-- Search, discovery rewards, description rendering and menu return run natively.
local loaded,started=false,false
local phase='setup';local since=0;local detailSeen=false;local returned=false
local hook
hook=emu.addMemoryCallback(guard(function()
 emu.removeMemoryCallback(hook,emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
 local f=assert(io.open(CONFIG.checkpoint,'rb'));local state=f:read('*a');f:close()
 emu.loadSavestate(state);loaded=true
end),emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
on_exec(0xC08000,function()
 if not loaded or started then return end
 started=true
 check(r(0x25FB)<6,'Fixture needs an initialized playable character')
 -- Enable Stonehenge as an undiscovered site, with no other pool changes.
 local source=0xC8E90B
 for j=0,6 do w(0x8D14+j,rom(source+j))end
 w(0x8D14+6,r(0x8D14+6)&7)
 check(r16(0x8D14)==168 and r16(0x8D16)==270,'Wrong village: expected Stonehenge near London')
 w(0x8FCE,0)
 local fleet=r16(0xE806);local hero=r16(0xE808)
 check(fleet>=0x41BB and fleet<0x6619 and hero>=0x25FC and hero<0x41BB,'Invalid initialized fleet/character pointers')
 w16(fleet,168*24);w16(fleet+2,270*18)
 w(hero+31,100);w(hero+35,100)
 w16(0x6619,100);w16(0x6619+2,100)
 -- Native village menu entry; no native search or rendering routine is replaced.
 phase='menu';since=frame
 call(0xC9E369,0)
end)
on_exec(0xC9DAF7,function()
 check(phase=='menu','Search entered unexpectedly')
 check(r(0x8FCE)==0,'Village selection changed')
 phase='exploring';since=frame
end)
on_exec(0xC9D8CC,function()
 check(phase=='exploring','Description reached without native Search')
 local cell=r16(0x100)+r(0x102)*65536
 check(cell==0xCEBE62,'Wrong discovery description pointer-table cell')
 local ptr=rom(cell)+rom(cell+1)*256+rom(cell+2)*65536
 for i=1,#CONFIG.expected do check(rom(ptr+i-1)==CONFIG.expected:byte(i),'Description byte mismatch at '..i)end
 check(rom(ptr+#CONFIG.expected)==0,'Description has no final terminator')
 if CONFIG.rewritten then check(ptr==0xF38000,'Rewritten text not in dedicated storage')end
end)
on_exec(0xC9D8DF,function()
 detailSeen=true;phase='description';since=frame
 check((r(0x8D14+6)&0x20)~=0,'Native discovery did not set its found flag')
end)
on_exec(0xC9E425,function()
 if detailSeen and not returned then
  check(r(0x8FCE)==0,'Village lost after discovery dismissal')
  returned=true;phase='returned';since=frame
 end
end)
on_exec(0xE00FFF,function()
 check(detailSeen and returned,'Village returned without completed description and menu cycle')
 finish(true,'Native Stonehenge Search, exact description bytes, found flag, controller dismissal, menu return and Sail exit')
end)
emu.addEventCallback(guard(function()
 local elapsed=frame-since
 local keys={a=false,b=false,down=false,up=false}
 if phase=='menu' then keys.down=elapsed>=350 and elapsed<358;keys.a=elapsed>=390 and elapsed<398
 elseif phase=='exploring' then keys.a=elapsed%90<8
 elseif phase=='description' then keys.a=elapsed>=100 and elapsed<108
 elseif phase=='returned' then keys.up=elapsed>=70 and elapsed<78;keys.a=elapsed>=110 and elapsed%90<8 end
 emu.setInput(keys,0)
end),emu.eventType.inputPolled)
on_frame(function()
 local elapsed=frame-since
 if phase=='menu'and elapsed==300 then screenshot('village-menu')end
 if phase=='description'and elapsed==35 then screenshot('stonehenge-description')end
 if phase=='returned'and elapsed==45 then screenshot('village-after-discovery')end
end)
