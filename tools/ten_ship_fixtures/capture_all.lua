-- Real capture creator for all14 added models and private enemy template75.
local root='__NH_PROJECT_ROOT__/'
local function w(p,v)emu.write(p,v%256,emu.memType.snesWorkRam)end
local function w16(p,v)w(p,v);w(p+1,math.floor(v/256))end
local function r(p)return emu.read(p,emu.memType.snesWorkRam)end
local function r16(p)return r(p)+256*r(p+1)end
local function rom(p)return emu.read(p,emu.memType.snesMemory)end
local f=assert(io.open(root..'output/scenario-research/ernst-final-grant/ernst-final-grant-wram.bin','rb'));local snap=f:read('*a');f:close()
for i=0,#snap-1 do w(i,snap:byte(i+1))end
local fleet=r16(0xE806)+43;local current=-1;local expected=nil;local actualcrew=nil
local function nextcase()
 current=current+1
 if current==15 then emu.log('PASS: real capture creator for all14 added hulls plus private75; identities/compartments/guns/crew and immutable records intact');emu.stop(0);return end
 for i=0,517 do w(0x6EC+i,rom(0xE41400+i))end
 for i=0,24 do w(0x6D0+i,rom(0xE41700+i))end
 for i=0,299 do w(0x7230+i,rom(0xC8CE27+i))end
 for i=0,9 do for j=0,8 do w(fleet+i*9+j,0)end end
 for i=0,39 do w(0x6BD7+i*25+18,255)end
 expected=current<14 and 0xE41400+current*25 or 0xE41700
 actualcrew=rom(expected+21)+256*rom(expected+22)
 local template=current<10 and 65+current or current<14 and 66+current or 75
 local values={actualcrew%256,math.floor(actualcrew/256),95,95,45,65,rom(expected+20),template,19}
 for i,v in ipairs(values)do w(0x1800+i-1,v)end
 w16(0x601,0x0FFE);w(0x603,0xE0);w16(0x604,0x1800);w16(0x606,39)
 emu.setState({['cpu.pc']=0x17F3,['cpu.k']=0xC3,['cpu.sp']=0x600,['cpu.d']=0x100,['cpu.dbr']=0x7E,['cpu.ps']=0x04,['cpu.emulationMode']=false})
end
emu.addMemoryCallback(function()
 if current>=15 then return end
 assert(r(0x6BD7+18)==rom(expected+18),'capture lost hull identity case'..current)
 for i=20,24 do assert(r(0x6BD7+i)==rom(expected+i),'capture default mismatch case'..current..' byte'..i)end
 assert(r(fleet+6)==rom(expected+20),'captured installed guns changed')
 assert(r16(fleet)==math.floor(actualcrew/5),'captured survivor rule changed')
 for i=0,517 do assert(r(0x6EC+i)==rom(0xE41400+i),'capture damaged immutable record')end
 for i=0,24 do assert(r(0x6D0+i)==rom(0xE41700+i),'capture damaged private75')end
 nextcase()
end,emu.callbackType.exec,0xC319A4,0xC319A4,emu.cpuType.snes)
nextcase()
