"""Exercise a built Windows editor using a locally supplied stock ROM."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('rom', type=Path)
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    exe, rom, destination = (p.resolve() for p in (args.exe, args.rom, args.report_dir))
    for path in (exe, rom):
        if not path.is_file():
            parser.error(f'File not found: {path}')
    destination.mkdir(parents=True, exist_ok=False)
    results = []
    for name in ('help', 'presets', 'workflow', 'ai-presets'):
        report = destination / name / 'report.json'
        report.parent.mkdir()
        command = ([str(exe), '--help-test', str(report)] if name == 'help' else
                   [str(exe), f'--{name}-test', str(rom), '--report', str(report)])
        try:
            with tempfile.TemporaryDirectory() as profile:
                run = subprocess.run(command, env=dict(os.environ, LOCALAPPDATA=profile),
                                     capture_output=True, timeout=300)
            (report.parent / 'stdout.txt').write_bytes(run.stdout)
            (report.parent / 'stderr.txt').write_bytes(run.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            result = dict(check=name, status=data.get('status'), exit_code=run.returncode)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            result = dict(check=name, status='FAIL', error=str(error))
        results.append(result)
        (destination / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(f"{name}: {result['status']}", flush=True)
        if result['status'] != 'PASS' or result.get('exit_code') != 0:
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
