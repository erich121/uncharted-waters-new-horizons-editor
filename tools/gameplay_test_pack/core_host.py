"""Windows-only development host for the existing Mesen Agent core.

Reapplies MaximumSpeed after ROM load. Lua owns its frame deadline and receipts.
Uses the same native core/API as AgentCli; no emulated game memory is patched.
"""
import argparse
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import time
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--home',type=Path,required=True)
    p.add_argument('--lua',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=55)
    p.add_argument('--frames',type=int,default=10000,help='Documented Lua budget; harness enforces it')
    p.add_argument('--screenshot',type=Path,required=True)
    args=p.parse_args()
    if os.name!='nt':raise RuntimeError('Development native host currently supports Windows only')
    runtime=args.runtime.resolve(strict=True);args.home.mkdir(parents=True,exist_ok=True)
    directory=os.add_dll_directory(str(runtime))
    core=c.WinDLL(str(runtime/'MesenCore.dll'))
    def bind(name,ret,types):
        f=getattr(core,name);f.restype=ret;f.argtypes=types;return f
    init=bind('InitDll',None,[])
    initialize=bind('InitializeEmu',None,[c.c_char_p,c.c_void_p,c.c_void_p,c.c_bool,c.c_bool,c.c_bool,c.c_bool])
    defaults=bind('AgentInitializeHeadlessDefaults',None,[])
    pause=bind('Pause',None,[])
    flag=bind('SetEmulationFlag',None,[c.c_int,c.c_bool])
    load=bind('LoadRom',c.c_bool,[c.c_char_p,c.c_char_p])
    init_debug=bind('InitializeDebugger',None,[])
    running=bind('IsRunning',c.c_bool,[])
    paused=bind('IsExecutionStopped',c.c_bool,[])
    cpu=bind('AgentGetPrimaryCpuType',c.c_int,[])
    step=bind('Step',None,[c.c_int,c.c_uint,c.c_int])
    lua_access=bind('AgentSetLuaAccess',None,[c.c_bool,c.c_bool,c.c_uint])
    load_script=bind('LoadScript',c.c_int,[c.c_char_p,c.c_char_p,c.c_char_p,c.c_int])
    errors=bind('GetScriptErrorCount',c.c_uint,[c.c_int])
    script_log=bind('GetScriptLog',None,[c.c_int,c.c_void_p,c.c_uint])
    screenshot=bind('AgentSaveScreenshot',c.c_bool,[c.c_char_p])
    stop=bind('Stop',None,[]);release=bind('Release',None,[])
    stop_code=bind('GetStopCode',c.c_int,[])
    version=bind('GetMesenVersion',c.c_uint,[])
    init();initialize(str(args.home.resolve()).encode(),None,None,True,True,True,True)
    try:
        defaults();pause();flag(16,True)
        if not load(str(args.rom.resolve()).encode(),None):raise RuntimeError('Core rejected ROM')
        init_debug();deadline=time.monotonic()+args.timeout
        while not paused():
            if time.monotonic()>=deadline:raise TimeoutError('Initial debugger pause')
            time.sleep(.001)
        v=version()
        print(json.dumps(dict(event='loaded',mesen_version=f'{v>>16}.{v>>8&255}.{v&255}',
                              runtime_sha256=hashlib.sha256((runtime/'MesenCore.dll').read_bytes()).hexdigest(),
                              backend='development-core-host')),flush=True)
        lua_access(True,False,5)
        script=args.lua.resolve()
        sid=load_script(script.name.encode(),str(script.parent).encode(),script.read_bytes(),-1)
        if sid<0:raise RuntimeError('Could not load Lua script')
        flag(4,True)
        step(cpu(),args.frames,6)
        timed_out=False
        while running():
            if errors(sid):break
            if time.monotonic()>=deadline:timed_out=True;break
            # A restored checkpoint may reset emulator-side speed state.
            flag(4,True)
            time.sleep(.005)
        code=4 if timed_out else 5 if errors(sid) else stop_code()
        buf=c.create_string_buffer(262144);script_log(sid,buf,len(buf))
        print(json.dumps(dict(event='lua_log',error_count=errors(sid),text=buf.value.decode('utf-8','replace'))),flush=True)
        screenshot(str(args.screenshot.resolve()).encode())
        print(json.dumps(dict(event='summary',ok=code==0,stop_code=code,timed_out=timed_out)),flush=True)
        return code
    finally:
        stop();release();directory.close()


if __name__=='__main__':sys.exit(main())
