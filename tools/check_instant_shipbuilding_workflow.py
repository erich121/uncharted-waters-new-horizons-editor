"""Repeat the pinned custom-ship order/pickup workflow with no construction wait."""
from pathlib import Path
import sys,json,struct,subprocess
from argparse import Namespace,ArgumentParser
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'mod_tool'),str(ROOT/'tools/gameplay_test_pack')]
import run,instant_shipbuilding
from shipyard_workflow import actions,equal,owned_checks
parser=ArgumentParser(description='Controller-only order and immediate pickup using the pinned one-added Lisbon fixture; no lodge rest.')
for key in ('rom','checkpoint','emulator','out'):parser.add_argument('--'+key,type=Path,required=True)
options=parser.parse_args()
out=options.out.resolve();out.mkdir(parents=True,exist_ok=False)
raw=options.rom.read_bytes()
assert run.sha(raw)=='fba483173c69c3a2e82071276c3697bbbec00aeba82fc1e32c7de1fb8245cffd'
data=bytearray(raw);instant_shipbuilding.install(data,True);data[0xffdc:0xffe0]=b'\xff\xff\0\0';check=sum(data)&65535;struct.pack_into('<HH',data,0xffdc,check^65535,check)
rom=out/'private-instant-pickup.sfc';rom.write_bytes(data)
args=Namespace(emulator=options.emulator.resolve(strict=True),backend='core',frames=12000,timeout=90)
state=options.checkpoint.resolve(strict=True)
records=[]
def stage(name,steps):
 global state
 steps=steps+[dict(kind='checkpoint')]
 result=run.run_case(args,rom,out,name,'run_workflow(CONFIG.workflow)',dict(frames=args.frames,workflow=dict(checkpoint=str(state),steps=steps)),'Normal controller order/pickup with assertions; only ROM zero-day timer changed')
 records.append(result);(out/'report.json').write_text(json.dumps(dict(status='RUNNING'if result['status']=='PASS'else 'FAIL',cases=records),indent=2))
 print(name,result['status'],result['reason'],flush=True)
 assert result['status']=='PASS'
 state=out/name/('checkpoint-'+str(len(steps))+'.mss')
steps=[dict(kind='assert',checks=[equal(0x2016,0),equal(0x25F4,1000000,4),equal(0x7EAB,255)])]
for phase in json.loads((run.HERE/'cases/lisbon-order-inputs.json').read_text()):steps+=phase['steps']
steps += [dict(kind='assert',checks=owned_checks()+[equal(0x25F4,940000,4),equal(0x7EAB,0),equal(0x7EAC,1),equal(0x41F6,255)]),dict(kind='capture')]
stage('order',steps)
stage('exit-order',actions('b:8,none:60,down:40,none:240'))
cmd=[sys.executable,str(run.HERE/'walk.py'),'--rom',str(rom),'--emulator',str(args.emulator),'--checkpoint',str(state),'--out',str(out/'return-shipyard'),'--door','2','--backend','core']
r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);print(r.stdout,r.stderr,flush=True);assert r.returncode==0
state=out/'return-shipyard/walk/checkpoint.mss'
steps=[dict(kind='assert',checks=[equal(0x7EAB,0),equal(0x41F6,255)])]
steps+=actions('up:24,none:24,a:8,none:120,a:8,none:100,a:8,none:160,a:8,none:160,a:8,none:180,a:8,none:180')
steps += [dict(kind='assert',checks=owned_checks()+[equal(0x7EAB,255),equal(0x41F6,1),equal(0x25F4,940000,4)]),dict(kind='capture')]
stage('collect',steps)
(out/'report.json').write_text(json.dumps(dict(status='PASS',cases=records,scope='Normal order/payment and pickup of one custom ship without lodge rest; isolated known Lisbon fixture, not every hull/port'),indent=2))
