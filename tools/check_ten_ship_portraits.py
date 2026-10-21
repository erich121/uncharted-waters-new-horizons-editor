"""Reuse the proven native portrait harness for every added slot and discovery chaining."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'tools/check_library_native.py'
source=path.read_text(encoding='utf-8')
source=source.replace('for added in (0,5):','for added in (0,10):')
source=source.replace('ids=[10,13]+([25,29]if added else [])','ids=[10,13]+(list(range(25,35))if added else [])')
source=source.replace("raw=bytes((i*17+31)%256 for i in range(1536));p.set_portrait(13,raw)","raw=bytes((i*17+31)%256 for i in range(1536));p.set_portrait(13,raw)\n for hull in range(25,len(p.ships)):p.set_portrait(hull,__import__('hashlib').shake_256(str(hull).encode('ascii')).digest(1536))")
lines=source.splitlines()
lines=["OUT=ROOT/'output/ship-editor/ten-ships-preview/portraits';OUT.mkdir(parents=True,exist_ok=True)"if line.startswith('OUT=ROOT/')else line for line in lines]
source='\n'.join(lines).replace('0/5 added classes','0/10 added classes')
sys.argv.append('--with-discoveries')
exec(compile(source,str(path)+' [ten ship coverage]','exec'),{'__file__':str(path),'__name__':'__main__'})
