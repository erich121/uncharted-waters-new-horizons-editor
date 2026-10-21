"""Run each test module in an isolated process, including its Tk/user state."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report-dir', type=Path, default=ROOT/'output/editor-regression')
parser.add_argument('--timeout', type=int, default=180, help='Seconds allowed per test module')
args = parser.parse_args()
if args.timeout < 1:
    parser.error('--timeout must be positive')
args.report_dir.mkdir(parents=True, exist_ok=True)
child = """import sys, ctypes, unittest, faulthandler
from pathlib import Path
root=Path.cwd()
sys.path[:0]=[str(root/'mod_tool'),str(root/'tests')]
try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError,OSError):pass
faulthandler.dump_traceback_later(max(1,int(sys.argv[2])*2//3))
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(sys.argv[1]))
faulthandler.cancel_dump_traceback_later()
sys.exit(0 if result.wasSuccessful() else 1)
"""
results = []
for path in sorted((ROOT/'tests').glob('test_*.py')):
    log = args.report_dir/(path.stem+'.txt')
    with tempfile.TemporaryDirectory() as folder, log.open('w', encoding='utf-8') as stream:
        try:
            result = subprocess.run([sys.executable,'-u','-c',child,path.stem,str(args.timeout)], cwd=ROOT,
                                    env=dict(os.environ,LOCALAPPDATA=folder), stdout=stream, stderr=stream,
                                    timeout=args.timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 'TIMEOUT'
    text = log.read_text(encoding='utf-8', errors='replace')
    count = re.search(r'Ran (\d+) tests?', text)
    row = dict(module=path.stem,status='PASS' if code==0 else 'FAIL',exit_code=code,
               tests=int(count[1]) if count else 0)
    results.append(row)
    (args.report_dir/'summary.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(row), flush=True)
print(json.dumps(dict(tests=sum(r['tests'] for r in results),failed_modules=[r['module'] for r in results if r['status']!='PASS'])))
sys.exit(0 if all(r['status']=='PASS' for r in results) else 1)
