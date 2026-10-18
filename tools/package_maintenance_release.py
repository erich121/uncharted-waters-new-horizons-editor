"""Publish an isolated v1.0.1 backport after scope, isolation and test audits."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CHECKS=('item-shuffle','goods-shuffle','presets','help')
MODIFIED={'mod_tool/item_shuffle_view.py','mod_tool/goods_shuffle_view.py','mod_tool/app.py','mod_tool/backend.py','mod_tool/VERSION','mod_tool/README.md','mod_tool/README.txt','mod_tool/CHANGELOG.md','mod_tool/DEVELOPMENT.md'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def normalized(data):return data.decode('utf-8').replace('\r\n','\n')


def main():
    parser=argparse.ArgumentParser()
    for key in ('stage','destination','base-source','dev-snapshot'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();stage=args.stage;destination=args.destination
    exe=stage/'Windows/New Horizons Ship Editor.exe';digest=sha(exe)
    for name in CHECKS:
        data=json.loads((stage/'packaged'/f'{name}.json').read_text(encoding='utf-8'))
        assert data['status']=='PASS'and data['version']=='1.0.1'and data['exe_sha256']==digest
    unit=(stage/'unit-tests.txt').read_text(encoding='utf-8')
    assert 'Ran 50 tests'in unit and '\nOK\n'in unit and 'FAILED'not in unit
    snapshots=json.loads(args.dev_snapshot.read_text(encoding='utf-8'))
    assert all(Path(path).is_file()and sha(Path(path))==expected for path,expected in snapshots.items()),'v1.1-dev changed'
    modified=[]
    with zipfile.ZipFile(args.base_source)as original:
        old={name.split('/',1)[1]:original.read(name)for name in original.namelist()if not name.endswith('/')}
        for relative,content in old.items():
            path=ROOT/relative;assert path.is_file(),relative
            if path.read_bytes()!=content:modified.append(relative)
        assert set(modified)==MODIFIED,modified
        new_backend=(ROOT/'mod_tool/backend.py').read_text(encoding='utf-8')
        assert new_backend.replace("TOOL_VERSION='1.0.1'","TOOL_VERSION='1.0.0'")==normalized(old['mod_tool/backend.py'])
        main=(ROOT/'mod_tool/app.py').read_text(encoding='utf-8')
        for kind in ('item','goods'):
            block=f"    if len(sys.argv)==5 and sys.argv[1]=='--{kind}-shuffle-test'and sys.argv[3]=='--report':\n        from {kind}_shuffle_checks import run\n        run(Editor,sys.argv[2],Path(sys.argv[4]));return\n"
            assert block in main;main=main.replace(block,'',1)
        assert main==normalized(old['mod_tool/app.py']),'Unexpected app change'
    assert (ROOT/'mod_tool/VERSION').read_text().strip()=='1.0.1'
    assert not destination.exists(),'Do not overwrite an existing release'
    destination.mkdir(parents=True)
    windows=destination/'Windows';shutil.copytree(stage/'Windows',windows)
    for name in ('README.md','README.txt','CHANGELOG.md','VERSION','LICENSE','Pillow.LICENSE','UWNHRando.LICENSE'):
        shutil.copy2(ROOT/'mod_tool'/name,windows/name)
    win=destination/'New Horizons Editor Windows v1.0.1.zip'
    source=destination/'New Horizons Editor Source v1.0.1.zip'
    with zipfile.ZipFile(win,'w',zipfile.ZIP_DEFLATED)as z:
        for path in windows.iterdir():z.write(path,'New Horizons Editor v1.0.1/'+path.name)
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('mod_tool','tests','tools'):
            for path in (ROOT/folder).rglob('*'):
                if path.is_file()and not set(path.relative_to(ROOT).parts)&{'__pycache__','build','dist'}and path.suffix not in ('.pyc','.exe','.sfc','.smc','.srm','.zip'):
                    z.write(path,'New Horizons Editor Source v1.0.1/'+path.relative_to(ROOT).as_posix())
    audit=dict(status='PASS',version='1.0.1',base_source_sha256=sha(args.base_source),modified_original_files=sorted(modified),v1_1_dev_unchanged=True,v1_1_dev_files_checked=len(snapshots),rom_patch_logic_unchanged=True,project_format=19,added_ship_limit=5,original_presets=13)
    (destination/'Backport Audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    validation=dict(status='PASS',version='1.0.1',exe_sha256=digest,unit_tests=50,packaged_checks=list(CHECKS),scope='Item/goods shuffle footer fix only, plus version/docs and regression checks. No emulator gameplay run for this UI-only fix.')
    (destination/'Validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    shutil.copytree(stage/'packaged',destination/'Validation reports');shutil.copy2(stage/'unit-tests.txt',destination/'Validation reports/unit-tests.txt')
    (destination/'SHA256SUMS.txt').write_text(''.join(sha(path)+'  '+path.relative_to(destination).as_posix()+'\n'for path in (win,source,windows/exe.name)),encoding='utf-8')
    for path in (win,source):
        with zipfile.ZipFile(path)as z:
            assert z.testzip()is None
            assert not any(name.lower().endswith(('.sfc','.smc','.srm'))for name in z.namelist())
    assert sha(windows/exe.name)==digest
    print(json.dumps(dict(validation,destination=str(destination),v1_1_dev_unchanged=True),indent=2))


if __name__=='__main__':main()
