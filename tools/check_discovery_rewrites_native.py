"""Repeat the native Stonehenge village Search with original and rewritten text.

Requires a private Mesen Agent sailing checkpoint from an initialized stock fleet.
Fixture setup enables Stonehenge, supplies food and sets ship position/stats. The
menu and encounter execute normally after setup; this is not a sailing-route test.
"""
import argparse
from argparse import Namespace
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'mod_tool'),str(ROOT/'tools/gameplay_test_pack')]
from backend import ShipProject
from discoveries import catalogue
from discovery_rewrites import DESCRIPTIONS
import run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--emulator',type=Path,required=True)
    parser.add_argument('--library',type=Path,help='Also test Library content replacing slot 01 in the same native village fixture.')
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    checkpoint=args.checkpoint.resolve(strict=True)
    reports=[]
    for enabled in ((False,True,'library') if args.library else (False,True)):
        project=ShipProject(args.stock);project.discovery_rewrites=enabled
        name='library'if enabled=='library'else 'rewritten'if enabled else 'original'
        if enabled=='library':
            from content_library import ContentLibrary
            from discovery_content import prepare_replacements
            import tempfile
            project.discovery_rewrites=False
            with tempfile.TemporaryDirectory() as temporary:
                entries, _ = ContentLibrary(project.rom, temporary).read(args.library)
            project=prepare_replacements(project,entries)
            if 0 not in project.discovery_entries:raise ValueError('Native fixture requires a slot 01 replacement.')
        rom=out/(name+'.sfc')
        rom.write_bytes(project.build()[0])
        expected=project.discovery_entries[0]['description']if enabled=='library'else DESCRIPTIONS[0]if enabled else catalogue(project.rom)[0]['description']
        config=dict(checkpoint=str(checkpoint),frames=3000,expected=expected,rewritten=enabled is True)
        options=Namespace(emulator=args.emulator.resolve(strict=True),backend='core',frames=3000,timeout=45)
        result=run.run_case(options,rom,out,name,
                            (ROOT/'tools/mesen-agent/test_discovery_rewrites.lua').read_text(encoding='utf-8'),config,
                            'Controlled Stonehenge village Search, text rendering and dismissal; no sailing route')
        reports.append(result)
        print(result['name']+': '+result['status']+' — '+result['reason'],flush=True)
    report=dict(status='PASS'if all(r['status']=='PASS'for r in reports)else 'FAIL',
                fixture_checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),cases=reports,
                scope='Seeded Stonehenge village menu, native Search, found flag and exact text; controller dismissal, menu return and Sail exit. Not travel from London or a cold save reload.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='PASS'else 1


if __name__=='__main__':
    raise SystemExit(main())
