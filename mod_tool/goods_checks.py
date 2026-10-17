"""Editable Goods and read-only Port Information integration checks."""
import json,tkinter as tk,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from backend import ShipProject,apply_ips
from trade_goods import TOWNS

def run(Editor,rom,report):
    root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    try:
        app=Editor(root);root.geometry('1672x940+0+0');app.project=ShipProject(rom);app.project.custom_ships=True;app.show(0);app.refresh_list();app.switch_section('world');world=app.world
        def settle(ms=80):
            done=tk.BooleanVar(root,value=False);root.after(ms,lambda:done.set(True));root.wait_variable(done);root.update()
        def mode(name):world.mode.set(name);world.change_mode();settle()
        def button(widget):
            app.scroll.focus_visible(SimpleNamespace(widget=widget));settle()
            x=widget.winfo_width()//2;y=widget.winfo_height()//2
            assert root.winfo_containing(widget.winfo_rootx()+x,widget.winfo_rooty()+y)==widget,'Goods control is covered'
            widget.event_generate('<ButtonPress-1>',x=x,y=y);widget.event_generate('<ButtonRelease-1>',x=x,y=y);settle()
        errors=[]
        with tempfile.TemporaryDirectory()as directory,patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            assert world.mode.get()=='Port Information'
            mode('Goods');world.selected=10;world.details();settle()
            assert world.goods_gate_box.instate(['disabled'])and world.add_good_button.instate(['disabled'])
            button(world.goods_enable_box);assert app.project.custom_goods
            assert len(world.good_sources())==3
            world.goods_port_box.current(4);world.select_edit_port();world.goods_gate.set('500');button(world.add_good_button)
            assert len(world.good_sources())==4 and app.project.goods_edits
            assert '*'in world.list.get(world.rows.index(10))and 'Changed.'in app.world_nav.cget('style')
            assert world.goods_tree.item('4','tags')==('changed',)
            mode('Port Information');world.selected=4;world.details();settle()
            sugar=next(o for o in world.port_goods.entries if o['id']==10)
            assert sugar['required']==500 and world.port_goods.current==world.port_records[4]['economy']
            assert sugar['changed']and all(not o['changed']for o in world.port_goods.entries if o['id']!=10)
            assert not world.goods_edit_frame.winfo_ismapped(),'Port Information must not expose editing controls'
            mode('Goods');world.selected=10;world.details();world.goods_port_box.current(4);world.select_edit_port()
            world.goods_gate_box.delete(0,'end');world.goods_gate_box.insert(0,'600')
            world.goods_port_box.current(48);world.select_edit_port();settle()
            sources=next(g for g in world.goods_records if g['id']==10)['sources']
            assert next(s for s in sources if s['port']==4)['economy_required']==600
            assert next(s for s in sources if s['port']==48)['economy_required']==200
            world.goods_gate_box.delete(0,'end');world.goods_gate_box.insert(0,'300');settle(450)
            path=Path(directory)/'goods.json';app.project.save_project(path)
            other=ShipProject(rom);other.load_project(path);assert other.goods_edits==app.project.goods_edits
            output=Path(directory)/'goods.sfc';other.export(output)
            assert apply_ips(other.rom,output.with_suffix('.ips').read_bytes())==output.read_bytes()
            assert output.read_bytes()[TOWNS+48*37+27]==30
            button(world.restore_good_button);assert not app.project.goods_edits and len(world.good_sources())==3
            world.goods_port_box.current(0);world.select_edit_port();button(world.add_good_button)
            assert errors and 'full'in errors[-1][1].lower()and not app.project.goods_edits;errors.clear()
            world.goods_port_box.current(4);world.select_edit_port();button(world.add_good_button)
            button(world.remove_good_button);assert not any(s['port']==4 for s in world.good_sources())
            button(world.restore_good_button);assert not app.project.goods_edits
            assert app.project.build()==(app.project.rom,[])
            world.goods_port_box.current(4);world.select_edit_port();button(world.add_good_button)
            app.switch_section('gameplay');settle()
            with patch('tkinter.messagebox.askyesno',return_value=True):app.restore_defaults_button.invoke()
            app.switch_section('world');mode('Goods');world.selected=10;world.details();settle()
            assert not app.project.goods_edits and len(world.good_sources())==3
            assert not errors,errors
        report.write_text(json.dumps(dict(status='PASS',sugar_port_add_remove=True,automatic_economy_changes=True,port_information_read_only_and_updates=True,edited_row_and_section_markers=True,pending_edit_stays_with_its_original_port=True,restore_good=True,full_port_rejected_without_replacement=True,project_roundtrip_and_rom_ips=True),indent=2),encoding='utf-8')
    except Exception as error:
        report.write_text(json.dumps(dict(status='FAIL',error=repr(error)),indent=2),encoding='utf-8');raise
    finally:root.destroy()
