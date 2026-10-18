"""Validate v1.0.1 separately; every GUI process uses temporary user storage."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--rom',type=Path,required=True);parser.add_argument('--reports',type=Path,required=True)
    args=parser.parse_args();args.reports.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(args.exe.read_bytes()).hexdigest()
    for name in ('item-shuffle','goods-shuffle','presets','help'):
        report=args.reports/(name+'.json');report.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory()as folder:
            command=[str(args.exe),'--help-test',str(report)]if name=='help'else [str(args.exe),'--'+name+'-test',str(args.rom),'--report',str(report)]
            result=subprocess.run(command,env=dict(os.environ,LOCALAPPDATA=folder),capture_output=True,text=True,timeout=180)
            assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
        data=json.loads(report.read_text(encoding='utf-8'));assert data['status']=='PASS',data
        data.update(version='1.0.1',exe_sha256=digest,isolated_user_storage=True)
        report.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        print('PASS v1.0.1 Windows '+name,flush=True)


if __name__=='__main__':main()
