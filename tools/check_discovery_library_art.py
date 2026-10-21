"""Check all 98 native picture/palette renders after applying a Library replacements."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'mod_tool'))
from backend import ShipProject
from discovery_content import capture, artwork
from discovery_content import prepare_replacements
from content_library import ContentLibrary
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--emulator', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    results = []
    for added in (0, 10):
        folder = out/str(added); folder.mkdir()
        p = ShipProject(args.stock)
        for _ in range(added): p.add_ship(10)
        with tempfile.TemporaryDirectory() as temporary:
            entries, _ = ContentLibrary(p.rom, temporary).read(args.library)
        p = prepare_replacements(p, entries)
        rom = folder/'test.sfc'; rom.write_bytes(p.build()[0])
        entries = [capture(p, i) for i in range(98)]
        (folder/'expected.bin').write_bytes(b''.join(b''.join(artwork(e)) for e in entries))
        lua = (ROOT/'tools/mesen-agent/test_discovery_browser.lua').read_text(encoding='utf-8')
        lua = lua.replace('@@ROOT@@', json.dumps(folder.as_posix()+'/')).replace('@@CASES@@', '{}')
        script = folder/'test.lua'; script.write_text(lua, encoding='utf-8')
        result = subprocess.run([str(args.emulator.resolve()), str(rom), '--home', str(folder/'home'), '--lua', str(script), '--lua-allow-io', '--frames', '4000', '--timeout', '75'], capture_output=True, text=True, timeout=90)
        log = result.stdout+result.stderr; (folder/'events.jsonl').write_text(log, encoding='utf-8')
        assert result.returncode == 0 and 'PASS: all98 discovery pictures and palettes' in log, log
        results.append(dict(added_ships=added, pictures=98, status='PASS'))
        print('PASS: 98 exact native pictures/palettes with', added, 'added ships', flush=True)
    (out/'report.json').write_text(json.dumps(dict(status='PASS', cases=results), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
