"""Serial frozen-EXE checks with isolated Library/preferences and explicit receipts."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/ship-editor/playable-levels'
EXE=STAGE/'Windows/New Horizons Ship Editor.exe'
ROM=ROOT/'New Horizons (USA).zip'
REAL=Path(os.environ['LOCALAPPDATA'])/'New Horizons Editor'
def snapshot():
 return {str(p.relative_to(REAL)):hashlib.sha256(p.read_bytes()).hexdigest()for p in REAL.rglob('*')if p.is_file()and (p.name.startswith('preferences')or 'Library'in p.parts)}
def main():
 digest=hashlib.sha256(EXE.read_bytes()).hexdigest();before=snapshot()
 for name in ('characters','workflow','library','help'):
  report=STAGE/f'packaged-{name}.json'
  with tempfile.TemporaryDirectory()as folder:
   env=dict(os.environ,LOCALAPPDATA=folder)
   if name=='characters':env['NH_CHARACTERS_SCREENSHOT']=str(STAGE/'Characters.png')
   command=[str(EXE),'--help-test',str(report)]if name=='help'else [str(EXE),'--'+name+'-test',str(ROM),'--report',str(report)]
   result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=300)
   assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
  check=json.loads(report.read_text(encoding='utf-8'))
  assert check['status']=='PASS',check
  assert snapshot()==before,'Real user storage changed during test'
  check.update(exe_sha256=digest,real_library_unchanged=True,real_preferences_unchanged=True)
  report.write_text(json.dumps(check,indent=2)+'\n',encoding='utf-8')
  print('PASS frozen',name,flush=True)
 print('PASS user storage unchanged',flush=True)
if __name__=='__main__':main()
