"""Serial packaged checks, isolated from the user's Library, presets and preferences."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/ship-editor/custom-presets'
EXE=STAGE/'Windows/New Horizons Ship Editor.exe'
REAL=Path(os.environ['LOCALAPPDATA'])/'New Horizons Editor'


def snapshot():
    return {str(p.relative_to(REAL)):hashlib.sha256(p.read_bytes()).hexdigest()for p in REAL.rglob('*')if p.is_file()}


def main():
    before=snapshot();digest=hashlib.sha256(EXE.read_bytes()).hexdigest()
    for name in ('custom-presets','presets','workflow','characters','library','help'):
        report=STAGE/f'packaged-{name}.json'
        report.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory()as folder:
            env=dict(os.environ,LOCALAPPDATA=folder)
            if name=='custom-presets':env['NH_CUSTOM_PRESET_SCREENSHOT']=str(STAGE/'Custom Presets.png')
            args=[str(EXE),'--help-test',str(report)]if name=='help'else [str(EXE),'--'+name+'-test',str(ROOT/'New Horizons (USA).zip'),'--report',str(report)]
            result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=300)
            assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
        check=json.loads(report.read_text(encoding='utf-8'));assert check['status']=='PASS',check
        assert snapshot()==before,'Actual user storage changed'
        check.update(exe_sha256=digest,real_user_storage_unchanged=True)
        report.write_text(json.dumps(check,indent=2)+'\n',encoding='utf-8')
        print('PASS frozen '+name,flush=True)
    # A deliberately invalid automation input must report failure and exit,
    # rather than leave a PyInstaller crash popup waiting for the user.
    with tempfile.TemporaryDirectory()as folder:
        failed=Path(folder)/'expected-failure.json'
        result=subprocess.run([str(EXE),'--custom-presets-test',str(Path(folder)/'missing.sfc'),'--report',str(failed)],env=dict(os.environ,LOCALAPPDATA=folder),capture_output=True,text=True,timeout=30)
        assert result.returncode==1 and json.loads(failed.read_text(encoding='utf-8'))['status']=='FAIL'
    assert snapshot()==before
    (STAGE/'packaged-test-failure.json').write_text(json.dumps(dict(status='PASS',exe_sha256=digest,real_user_storage_unchanged=True,automation_failure_exits_without_popup=True),indent=2)+'\n',encoding='utf-8')
    print('PASS frozen test-failure exits cleanly',flush=True)
    print('PASS actual user storage unchanged',flush=True)


if __name__=='__main__':main()
