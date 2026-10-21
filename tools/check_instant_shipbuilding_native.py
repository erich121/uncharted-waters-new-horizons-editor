"""Zero-day timer tests for stock and ten-added-ship exports."""
import argparse,json
from pathlib import Path
from argparse import Namespace
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'mod_tool'),str(ROOT/'tools/gameplay_test_pack')]
from backend import ShipProject
import run


def main():
    p=argparse.ArgumentParser()
    for key in ('stock','checkpoint','emulator','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);reports=[]
    for count in (0,10):
        for enabled in (False,True):
            project=ShipProject(a.stock)
            for i in range(count):project.add_ship(10)
            project.instant_shipbuilding=enabled
            rom=out/(str(count)+'-'+str(enabled)+'.sfc');rom.write_bytes(project.build()[0])
            cases=[dict(id=i,hull=s['hull'],industry=industry)for i,s in enumerate(project.ships)for industry in (0,500,1000)]
            options=Namespace(emulator=a.emulator.resolve(strict=True),backend='core',frames=2000,timeout=35)
            result=run.run_case(options,rom,out,str(count)+'-'+str(enabled),(ROOT/'tools/mesen-agent/test_instant_shipbuilding.lua').read_text(encoding='utf-8'),
                dict(frames=2000,checkpoint=str(a.checkpoint.resolve(strict=True)),enabled=enabled,cases=cases),
                'Actual timer calculation and stored order days; adjacent record preserved; direct native fixture')
            reports.append(result);print(result['name']+': '+result['status'],flush=True)
    report=dict(status='PASS'if all(r['status']=='PASS'for r in reports)else 'FAIL',native_timer_cases=360,cases=reports)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='PASS'else 1


if __name__=='__main__':raise SystemExit(main())
