"""Native annual deadline tests at the original and extended campaign boundaries."""
import argparse,json
from argparse import Namespace
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'mod_tool'),str(ROOT/'tools/gameplay_test_pack')]
from backend import ShipProject
import run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('stock','checkpoint','emulator','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for enabled in (False,True):
        project=ShipProject(a.stock);project.fifty_year_campaign=enabled
        rom=out/('50-years.sfc'if enabled else 'stock.sfc');rom.write_bytes(project.build()[0])
        limit=70 if enabled else 52
        cases=[dict(hero=hero,before=year,gameover=0x10 if year+1>limit else 0)
               for hero in range(6)for year in (21,51,52,53,69,70,71)]
        options=Namespace(emulator=a.emulator.resolve(strict=True),backend='core',frames=3000,timeout=45)
        result=run.run_case(options,rom,out,'50-years'if enabled else 'stock',
            (ROOT/'tools/mesen-agent/test_campaign_length.lua').read_text(encoding='utf-8'),
            dict(frames=3000,checkpoint=str(a.checkpoint.resolve(strict=True)),cases=cases),
            'Native annual rollover, original/extended deadline and all 120 sailor age increments; direct routine setup, not a complete campaign')
        reports.append(result);print(result['name']+': '+result['status']+' '+result['reason'],flush=True)
    report=dict(status='PASS'if all(r['status']=='PASS'for r in reports)else 'FAIL',cases=reports,
                native_boundary_cases=84,scope='Native C100C8 annual processing with initialized state and controlled date/hero; not 50 years of gameplay')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='PASS'else 1


if __name__=='__main__':raise SystemExit(main())
