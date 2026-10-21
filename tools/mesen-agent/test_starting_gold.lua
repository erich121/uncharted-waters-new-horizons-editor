-- Initializer and exact opening-money command checks; unrelated rewards remain native.
local loaded=false;local current=0;local c;local stage
local function w24(p,v)w16(p,v%65536);w(p+2,math.floor(v/65536))end
local function nextcase()
 current=current+1;c=CONFIG.cases[current]
 if not c then finish(true,'All '..#CONFIG.cases..' native starting-wallet and opening-grant cases');return end
 w(0x25FB,c.hero);w16(0x25F4,1234);w16(0x25F6,0)
 if c.kind=='init'then
  w24(0x9F1D,0x7EB800)
  call(0xC74EA7)
 elseif c.kind=='loaded-story'then
  stage='load';call(0xC99CBA)
 else
  -- Native E4 handler's variable address workspace; the actual preceding
  -- command is present in the decoded script buffer, exactly as at runtime.
  local var=c.match and 0 or 1
  local bytes={0x0C,var,0x13,0x88,0xE4,var}
  for i,v in ipairs(bytes)do w(0x1B000+i-1,v)end
  w24(0x9F39,0x7FB006);w24(0x9F28,0x7EB400)
  w16(0xB400+2*var,5000)
  call(0xC985D2,var)
 end
end
local hook
hook=emu.addMemoryCallback(guard(function()
 emu.removeMemoryCallback(hook,emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
 local f=assert(io.open(CONFIG.checkpoint,'rb'));local data=f:read('*a');f:close();emu.loadSavestate(data);loaded=true
end),emu.callbackType.exec,0,0xFFFFFF,emu.cpuType.snes)
on_exec(0xC08000,function()if loaded and current==0 then nextcase()end end)
-- E4's normal balance-popup follows the real wallet writes. Stop at its entry
-- only for this isolated function test; no game outcome/money logic is skipped.
on_exec(0xC9863B,function()
 if c and (c.kind=='story'or c.kind=='loaded-story')then
  local amount=r16(0x25F4)+65536*r16(0x25F6)
  check(amount==c.expected,'Story money mismatch for hero '..c.hero..': '..amount)
  nextcase()
 end
end)
on_exec(0xE00FFF,function()
 if c.kind=='loaded-story'and stage=='load'then
  local at=c.hero==3 and 0x143 or 0x37A
  local expected={0x0C,0,0x13,0x88,0xE4,0}
  for i,v in ipairs(expected)do check(r(0x10000+at+i-1)==v,'Wrong ROM-loaded initial money command')end
  w24(0x9F36,0x7F0000);w24(0x9F39,0x7F0000+at);w16(0x9F2E,at)
  w24(0x9F28,0x7EB400);w16(0xA251,0)
  stage='vm';call(0xC9B708);return
 end
 check(c.kind=='init','Unexpected function return')
 local amount=r16(0x25F4)+65536*r16(0x25F6)
 check(amount==c.expected,'New-game money mismatch for hero '..c.hero..': '..amount)
 nextcase()
end)
