"""Check native signed item-price conversion and rank calculation in Mesen."""
from argparse import ArgumentParser,Namespace
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'mod_tool'),str(ROOT/'tools/gameplay_test_pack')]
from backend import ShipProject
from items import catalogue,weapon_rank
import run

def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--stock',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--emulator',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    p=ShipProject(a.stock);rows=catalogue(p.rom)
    samples=[0,100,500,1200,3276700]
    p.item_price_edits=[dict(id=row['id'],price_gold=samples[i%len(samples)])for i,row in enumerate(rows)]
    rom=out/'items.sfc';rom.write_bytes(p.build()[0])
    cases=[dict(item=row['id'],expected=samples[i%len(samples)])for i,row in enumerate(rows)]
    for row in rows:
        rank=weapon_rank(p.rom,row['id'])
        if rank:cases.append(dict(item=row['id'],rank=True,expected=('D','C','B','A','\u2605').index(rank)))
    result=run.run_case(Namespace(emulator=a.emulator.resolve(),backend='core',frames=1000,timeout=35),rom,out,'native-calculations',
        (ROOT/'tools/mesen-agent/test_item_prices.lua').read_text(encoding='utf-8'),
        dict(frames=1000,checkpoint=str(a.checkpoint.resolve()),cases=cases),
        'Direct native base-price conversion and weapon-rank calculation; initialized records supplied by fixture. Full shop transactions, bargaining and save/reload not covered.')
    (out/'report.json').write_text(json.dumps(dict(status=result['status'],cases=len(cases),result=result),indent=2),encoding='utf-8')
    print(result['status'],result['reason']);return 0 if result['status']=='PASS'else 1
if __name__=='__main__':raise SystemExit(main())
