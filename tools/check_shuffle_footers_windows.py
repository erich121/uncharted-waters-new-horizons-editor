"""Serial checks for the item and goods shuffle footers, with all user storage isolated."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/ship-editor/item-shuffle-footer'
EXE=STAGE/'Windows/New Horizons Ship Editor.exe'
REAL=Path(os.environ['LOCALAPPDATA'])/'New Horizons Editor'
CHECKS=('item-shuffle','goods-shuffle')


def snapshot():
    return {str(p.relative_to(REAL)):hashlib.sha256(p.read_bytes()).hexdigest()for p in REAL.rglob('*')if p.is_file()}


def main():
    before=snapshot();digest=hashlib.sha256(EXE.read_bytes()).hexdigest()
    for name in CHECKS:
        report=STAGE/f'packaged-{name}.json';report.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory()as folder:
            env=dict(os.environ,LOCALAPPDATA=folder)
            args=[str(EXE),'--help-test',str(report)]if name=='help'else [str(EXE),'--'+name+'-test',str(ROOT/'New Horizons (USA).zip'),'--report',str(report)]
            result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=300)
            assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
        check=json.loads(report.read_text(encoding='utf-8'));assert check['status']=='PASS',check
        assert snapshot()==before,'Actual user storage changed'
        check.update(exe_sha256=digest,real_user_storage_unchanged=True)
        report.write_text(json.dumps(check,indent=2)+'\n',encoding='utf-8')
        print('PASS frozen '+name,flush=True)
    print('PASS actual user storage unchanged',flush=True)


if __name__=='__main__':main()
