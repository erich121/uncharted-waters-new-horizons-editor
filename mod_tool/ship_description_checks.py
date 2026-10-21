"""Exercise description editing, locking, restores and portable content in Tk."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from backend import ShipProject
from content_library import ContentLibrary,capture_ship
import ship_descriptions as sd


def run(Editor,rom_path,report_path):
    report_path=Path(report_path);report_path.parent.mkdir(parents=True,exist_ok=True)
    root=None;result=dict(status='FAIL')
    try:
        with tempfile.TemporaryDirectory()as folder,patch.dict(os.environ,LOCALAPPDATA=folder):
            folder=Path(folder);root=tk.Tk();errors=[]
            root.report_callback_exception=lambda *args:errors.append(str(args))
            app=Editor(root);app.project=ShipProject(rom_path);app.selected=10;app.show(10);app.refresh_list()
            def settle(delay=80):
                done=tk.BooleanVar(root,False);root.after(delay,lambda:done.set(True));root.wait_variable(done);root.update()
                assert not errors,errors
            def enter(text):
                app.description_text.delete('1.0','end');app.description_text.insert('1.0',text);settle(450)
            settle()
            assert app.description_text.cget('state')=='disabled'
            assert app.description_text.get('1.0','end-1c')==sd.stock_text(app.project.rom,10)
            app.custom_ships_box.invoke();settle()
            assert app.description_text.cget('state')=='normal'
            enter('A sturdy trader for distant voyages.')
            assert app.project.ship_descriptions=={10:'A sturdy trader for distant voyages.'}
            assert '*'in app.list.get(10) and app.description_text.cget('foreground')=='#ef7800'
            app.notebook.select(2);settle()
            for size in ('640x480','1440x900'):
                root.geometry(size+'+0+0');settle()
                assert app.description_text.winfo_width()>100
                assert app.description_text.winfo_rootx()+app.description_text.winfo_width()<=app.scroll.canvas.winfo_rootx()+app.scroll.canvas.winfo_width()+2
                app.scroll.canvas.yview_moveto(1);settle();assert app.scroll.canvas.yview()[1]>.99
            root.geometry('1440x900+0+0');app.scroll.canvas.yview_moveto(0);settle()
            if os.environ.get('NH_DESCRIPTION_SCREENSHOT'):
                from PIL import ImageGrab
                ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(os.environ['NH_DESCRIPTION_SCREENSHOT'])
            library=ContentLibrary(app.project.rom,folder/'Library');entry=capture_ship(app.project,10);library.put(entry)
            library.export_file(folder/'ships.nhlib');shared,_=library.read(folder/'ships.nhlib')
            assert shared[0]['description']=='A sturdy trader for distant voyages.'
            app.project.save_project(folder/'project.json');before=app.project.build()
            copy=ShipProject(rom_path);copy.load_project(folder/'project.json');assert copy.build()==before
            app.custom_ships_box.invoke();settle();assert app.description_text.cget('state')=='disabled'
            assert app.project.ship_descriptions
            app.custom_ships_box.invoke();settle()
            enter('x'*227);assert app.project.ship_descriptions[10]=='A sturdy trader for distant voyages.'
            assert 'Finish editing:'in app.status.cget('text')
            stats=dict(app.project.ships[10]);app.restore_description_button.invoke();settle()
            assert app.project.ship_descriptions=={} and app.project.ships[10]==stats
            assert app.project.build()==(app.project.rom,[])
            app.project.add_ship(10);app.project.add_ship(10);app.show(25);app.refresh_list();settle()
            enter('A quick merchant ship.')
            app.show(26);app.refresh_list();settle();enter('A slow, heavily armed ship.')
            assert sd.text(app.project,25)!=sd.text(app.project,26)
            result=dict(status='PASS',automatic_edits=True,independent_added_text=True,stock_defaults=True,
                        project_and_library_roundtrip=True,locked_values_retained=True,invalid_input_guard=True,
                        restore_text_preserves_stats=True,small_and_desktop_layout=True)
    except Exception as error:
        result['error']=str(error);raise
    finally:
        report_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        if root is not None:root.destroy()
