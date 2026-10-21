-- Native SRAM save/copy/load, with14 owned models and existing private75.
local root='__NH_PROJECT_ROOT__/'
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function rom(p)return emu.read(p,emu.memType.snesMemory)end
local f=assert(io.open(root..'output/scenario-research/ernst-final-grant/ernst-final-grant-wram.bin','rb'));local snapshot=f:read('*a');f:close()
for i=0,#snapshot-1 do w(i,snapshot:byte(i+1))end
for n=0,13 do for i=0,24 do w(0x6BD7+n*25+i,rom(0xE41400+n*25+i))end end
local lead=0x53EA+43;local values={200,0,95,95,45,65,80,75,19}
for i,v in ipairs(values)do w(lead+i-1,v)end
local phase=0
local function call(pc,arg)
 w16(0x601,0x0FFE);w(0x603,0xE0);w16(0x604,arg or 0)
 emu.setState({['cpu.pc']=pc%65536,['cpu.k']=math.floor(pc/65536),['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 if phase==0 then
  phase=1;for i=0x2000,0x7EEF do w(i,0xAA)end
  for i=0x6D0,0x8F1 do w(i,0xAA)end
  call(0xE41800)
 elseif phase==1 then phase=2;call(0xC7518B,1)
 else
  for n=0,13 do for i=0,24 do assert(r(0x6BD7+n*25+i)==rom(0xE41400+n*25+i),'owned model reload mismatch '..n..' byte'..i)end end
  for i=0,517 do assert(r(0x6EC+i)==rom(0xE41400+i),'immutable records corrupted on load')end
  for i=0,24 do assert(r(0x6D0+i)==rom(0xE41700+i),'private75 reset failed')end
  for i,v in ipairs(values)do assert(r(lead+i-1)==v,'existing private75 fleet record changed on reload')end
  emu.log('PASS: native SRAM save/load preserves14 owned ship types/compartments and existing NPC75 fleet; reset restores518 record bytes and300-man enemy default');emu.stop(0)
 end
end,emu.callbackType.exec,0xE00FFF,0xE00FFF,emu.cpuType.snes)
call(0xC7518B,0)
