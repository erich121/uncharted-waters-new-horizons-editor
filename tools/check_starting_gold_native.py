"""Check all six native new-game wallet paths and guarded opening assignments."""
import argparse,json
from argparse import Namespace
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'mod_tool'),str(ROOT/'tools/gameplay_test_pack')]
from backend import ShipProject
import run


def main():
    p=argparse.ArgumentParser()
    for key in ('stock','checkpoint','emulator','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);reports=[]
    for value in (None,0,5000,100000,250000):
        project=ShipProject(a.stock);project.starting_gold=value
        rom=out/(str(value)+'.sfc');rom.write_bytes(project.build()[0])
        cases=[]
        for hero in range(6):
            cases.append(dict(kind='init',hero=hero,expected=1234 if value is None else value))
            for match in (True,False):
                expected=value if value is not None and hero in (3,4)and match else 5000
                cases.append(dict(kind='story',hero=hero,match=match,expected=expected))
        for hero in (3,4):cases.append(dict(kind='loaded-story',hero=hero,expected=5000 if value is None else value))
        options=Namespace(emulator=a.emulator.resolve(strict=True),backend='core',frames=2000,timeout=35)
        result=run.run_case(options,rom,out,'gold-'+str(value),(ROOT/'tools/mesen-agent/test_starting_gold.lua').read_text(encoding='utf-8'),
            dict(frames=2000,checkpoint=str(a.checkpoint.resolve(strict=True)),cases=cases),
            'Direct native initialization and E4 opening-grant guard tests; popup skipped after verified writes; not all six complete introductions')
        reports.append(result);print(str(value)+': '+result['status']+' '+result['reason'],flush=True)
    report=dict(status='PASS'if all(r['status']=='PASS'for r in reports)else 'FAIL',native_cases=100,cases=reports)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='PASS'else 1


if __name__=='__main__':raise SystemExit(main())
