"""Goods shuffle footer visibility, actual clicks and transactional operations."""
import json,tempfile,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject,apply_ips
from goods_shuffle_view import open_shuffle,MODES


def run(Editor,rom,report):
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    root=tk.Tk();root.attributes('-topmost',True)
    try:
        app=Editor(root)
        with patch('tkinter.filedialog.askopenfilename',return_value=str(rom)):app.open_rom()
        p=app.project
        def settle():
            ready=tk.BooleanVar(root,value=False);root.after(90,lambda:ready.set(True));root.wait_variable(ready);root.update()
        def exposed():
            d=app.goods_shuffle_dialog
            for b in app.goods_shuffle_buttons:
                assert b.winfo_ismapped(),b.cget('text')
                x=b.winfo_rootx()+b.winfo_width()//2;y=b.winfo_rooty()+b.winfo_height()//2
                assert d.winfo_rootx()<=x<d.winfo_rootx()+d.winfo_width()
                assert d.winfo_rooty()<=b.winfo_rooty()and b.winfo_rooty()+b.winfo_height()<=d.winfo_rooty()+d.winfo_height(),(b.cget('text'),d.geometry(),b.winfo_geometry())
                assert root.winfo_containing(x,y)==b,(b.cget('text'),'covered')
        clock=1000
        def click(index):
            nonlocal clock
            exposed();b=app.goods_shuffle_buttons[index];clock+=1000
            x=b.winfo_width()//2;y=b.winfo_height()//2
            b.event_generate('<ButtonPress-1>',x=x,y=y,time=clock)
            b.event_generate('<ButtonRelease-1>',x=x,y=y,time=clock+1);settle()
        errors=[]
        with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            before=p.manifest();open_shuffle(app);settle()
            assert [b.cget('text')for b in app.goods_shuffle_buttons]==['Random shuffle','Apply shuffle','Restore goods','Cancel']
            for size in ('700x590','400x380','500x430','900x700'):
                app.goods_shuffle_dialog.geometry(size+'+40+40');settle();exposed()
                assert app.goods_shuffle_preview.winfo_height()>20
            with patch('goods_shuffle_view.random_seed',return_value='9876'):click(0)
            assert app.goods_shuffle_seed.get()=='9876'and p.manifest()==before
            click(3);assert p.manifest()==before and not app.goods_shuffle_dialog.winfo_exists()
            for mode in MODES:
                open_shuffle(app);settle();app.goods_shuffle_mode.set(mode);app.goods_shuffle_seed.set('1234');settle()
                assert app.goods_shuffle_candidates and p.manifest()==before
                app.goods_shuffle_dialog.geometry('400x380+40+40');settle();click(1)
                assert p.goods_shuffle['seed']=='1234'and p.goods_shuffle['mode']==MODES[mode]
                with tempfile.TemporaryDirectory()as folder:
                    path=Path(folder);p.save_project(path/'project.json');q=ShipProject(p.source);q.load_project(path/'project.json')
                    assert q.manifest()==p.manifest();p.export(path/'test.sfc')
                    assert apply_ips(p.rom,(path/'test.ips').read_bytes())==(path/'test.sfc').read_bytes()
                open_shuffle(app);settle();app.goods_shuffle_seed.set('9876');settle();click(3)
                assert p.goods_shuffle['seed']=='1234'
                open_shuffle(app);settle();app.goods_shuffle_dialog.geometry('400x380+40+40');settle();click(2)
                assert p.manifest()==before
            open_shuffle(app);settle();app.goods_shuffle_blind.set(True);settle()
            assert app.goods_shuffle_preview.get(0)=='Blind shuffle: destinations are hidden.'
            click(1);assert p.goods_shuffle['blind']
            open_shuffle(app);settle();click(2);assert p.manifest()==before
            assert not errors,errors
        report.write_text(json.dumps(dict(status='PASS',all_four_buttons_visible=True,real_pointer_clicks=True,window_sizes=['700x590','400x380','500x430','900x700'],random_previews_without_applying=True,cancel_keeps_current_settings=True,three_modes_apply=True,restore_goods=True,blind_mode=True,project_and_rom_ips_roundtrip=True),indent=2),encoding='utf-8')
    except Exception as error:
        import traceback
        report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
    finally:root.destroy()
