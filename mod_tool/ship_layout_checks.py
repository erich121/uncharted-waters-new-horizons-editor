"""Ship presentation and edit reachability at real Windows viewport sizes."""
import json
import os
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import ImageGrab


def run(Editor, rom, report):
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    checks, errors = [], []

    def settle(ms=100):
        ready = tk.BooleanVar(root, value=False)
        root.after(ms, lambda: ready.set(True))
        root.wait_variable(ready)
        root.update()

    def exposed(widget):
        app.scroll.focus_visible(SimpleNamespace(widget=widget))
        settle()
        x = widget.winfo_rootx() + widget.winfo_width() // 2
        y = widget.winfo_rooty() + widget.winfo_height() // 2
        assert root.winfo_containing(x, y) == widget, ('Covered field', str(widget), root.geometry(), (x,y), app.scroll.canvas.yview(),app.scroll.canvas.cget('scrollregion'),app.scroll.content.winfo_height(),app.scroll.content.winfo_reqheight())

    try:
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, LOCALAPPDATA=temporary), patch('tkinter.messagebox.showerror', side_effect=lambda *a, **k: errors.append(a)):
            app = Editor(root)
            root.geometry('1440x900+0+0')
            assert app.load_rom(rom)
            app.notebook.select(1);settle()
            for ship in (0,10,17):
                app.show(ship);settle()
                expected=set(app.project.original_availability[ship]['ports'])
                assert set(app.port_list.curselection())==expected
                assert app.port_list_locked
                assert app.port_list.cget('selectbackground')=='#dbeafe'
                app.port_list.event_generate('<ButtonPress-1>',x=10,y=2);app.port_list.event_generate('<ButtonRelease-1>',x=10,y=2)
                app.port_list.event_generate('<Control-KeyPress-a>');settle()
                assert set(app.port_list.curselection())==expected,'Locked list allowed a selection change'
                if expected:
                    port=app.project.original_availability[ship]['ports'][0]
                    assert app.port_list.bbox(port), 'First building port should be visible'
                    box=app.port_list.bbox(port)
                    x=app.port_list.winfo_rootx()+app.port_list.winfo_width()-8
                    y=app.port_list.winfo_rooty()+box[1]+box[3]//2
                    assert ImageGrab.grab().getpixel((x,y))[:3]==(219,234,254),'Disabled build-port highlight is not drawn'
            app.show(17);settle()
            ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/'Availability locked.png')
            checks.append('Stock build ports visibly highlighted while locked; first port visible')
            app.custom_ships_box.invoke()
            assert not app.port_list_locked and app.port_list.cget('selectbackground')=='#205b9b'
            app.project.set_shipbuilding_shuffle('0123',True);app.show(17);settle()
            assert not app.port_list.curselection()
            assert str(app.port_list.cget('state'))=='disabled'
            app.project.clear_shipbuilding_shuffle();app.show(0);app.notebook.select(0)
            checks.append('Editing restores normal selection; blind shuffle reveals no location colors')
            settle()
            for size in ('1440x900', '1672x940', '1920x1000', '1280x720', '1100x820', '640x480'):
                root.geometry(size + '+0+0')
                settle()
                app.scroll.canvas.yview_moveto(0)
                settle()
                assert all(card.panel.winfo_manager() == 'grid' for card in app.spec_sections)
                assert app.scroll.canvas.xview()[1] == 1.0, (size, 'horizontal overflow')
                if size in ('1440x900', '1672x940', '1920x1000'):
                    assert app.card_columns == 2
                    bottom = app.scroll.canvas.winfo_rooty() + app.scroll.canvas.winfo_height()
                    for card in app.spec_sections:
                        assert card.panel.winfo_rooty() + card.panel.winfo_height() <= bottom, (size, 'card clipped', card.panel.title_label.cget('text'), card.panel.winfo_rooty()+card.panel.winfo_height(), bottom)
                if size == '640x480':
                    assert app.card_columns == 1
                assert app.list.winfo_height() >= (50 if size == '640x480' else 100)
                for widget in (app.entries['name'], app.entries['hull'], app.extra_entries['capacity'], app.extra_entries['factory_crew']):
                    exposed(widget)
                assert str(app.extra_entries['yard_cargo'].cget('state')) == 'readonly'
                assert str(app.extra_entries['factory_cargo'].cget('state')) == 'readonly'
                exposed(app.restore_button)
                checks.append('Portrait overview, four stat cards, cargo/starting fields and restore reachable at ' + size)

            root.geometry('1440x900+0+0')
            app.show(10)
            settle()
            before = app.project.ships[10]['hull']
            app.vars['hull'].set(str(before - 1))
            settle(450)
            assert app.project.ships[10]['hull'] == before - 1
            assert 'Changed.' in app.entries['hull'].cget('style')
            app.restore_button.invoke()
            settle()
            assert app.project.ships[10]['hull'] == before
            app.scroll.canvas.yview_moveto(0)
            settle()
            ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(report.parent/'Ships.png')
            assert app.spec_portrait.cget('image'), 'Specifications must display the selected ship portrait'
            expected=__import__('portraits').image(app.project.portrait_raw(10),app.project.rom,app.spec_portrait_scale)
            for x,y in ((0,0),(64,48),(100,70)):
                assert tuple(root.tk.call(str(app.spec_portrait_photo),'get',x,y))==expected.getpixel((x,y))
            for index,name in ((1,'Availability'),(2,'Graphics'),(3,'Fixes')):
                app.notebook.select(index);settle()
                app.scroll.canvas.yview_moveto(0);settle()
                assert app.scroll.canvas.xview()[1]==1.0
                ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/(name+'.png'))
            app.notebook.select(0);settle()
            checks.append('Edit, changed-state highlight and restore preserved')

            app.add_button.invoke()
            settle()
            assert app.selected == 25
            assert app.extra_entries['factory_guns'].instate(['!disabled'])
            assert app.extra_entries['factory_crew'].instate(['!disabled'])
            app.extra_vars['capacity'].set('900')
            app.commit()
            ship = app.project.ships[25]
            assert int(app.extra_vars['factory_cargo'].get()) == 900 - ship['factory_guns'] - ship['factory_crew']
            for index, widget in ((1, app.industry_entry), (2, app.import_portrait_button), (3, app.repair_check)):
                app.notebook.select(index)
                settle()
                exposed(widget)
            checks.append('Added ship starting fit and calculated cargo preserved; all ship tabs reachable')
            root.geometry('640x480+0+0');app.notebook.select(0);settle()
            app.scroll.canvas.yview_moveto(0);settle()
            hull=app.vars['hull'].get();start=app.scroll.canvas.yview()
            app.entries['hull'].event_generate('<MouseWheel>',delta=-120);settle()
            assert app.vars['hull'].get()==hull,'Wheel changed a ship value'
            assert app.scroll.canvas.yview()!=start,'Wheel over numeric field did not scroll the panel'
            for widget in [*app.entries.values(),*app.extra_entries.values()]:
                before=widget.get()
                for delta in (-120,120):widget.event_generate('<MouseWheel>',delta=delta);settle()
                assert widget.get()==before,'Wheel changed an input'
            app.notebook.select(2);settle();app.scroll.canvas.yview_moveto(0);settle()
            before=app.base_combo.get();start=app.scroll.canvas.yview()
            app.base_combo.event_generate('<MouseWheel>',delta=-120);settle()
            assert app.base_combo.get()==before,'Wheel changed ship family'
            assert app.scroll.canvas.yview()!=start,'Wheel over dropdown did not scroll the panel'
            checks.append('Wheel over numeric inputs and dropdowns scrolls the panel without changing values')
            from tkinter import ttk
            popup=tk.Toplevel(root);popup.geometry('300x180+0+0')
            spin=ttk.Spinbox(popup,from_=1,to=10);spin.set('5');spin.pack()
            legacy=tk.Spinbox(popup,from_=1,to=10);legacy.delete(0,'end');legacy.insert(0,'5');legacy.pack()
            combo=ttk.Combobox(popup,values=['A','B'],state='readonly');combo.current(0);combo.pack();settle()
            for widget in (spin,legacy,combo):
                before=widget.get()
                for delta in (-120,120):widget.event_generate('<MouseWheel>',delta=delta);settle()
                assert widget.get()==before,'Wheel changed a popup input'
            popup.destroy()
            checks.append('Controls created later in popups also ignore wheel value changes')
            assert not errors, errors
        report.write_text(json.dumps(dict(status='PASS', checks=checks, errors=errors), indent=2), encoding='utf-8')
    except Exception as error:
        try:ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(report.parent/'Layout problem.png')
        except Exception:pass
        panels=[dict(title=card.panel.title_label.cget('text'),y=card.panel.winfo_rooty(),height=card.panel.winfo_height())for card in app.spec_sections]if 'app'in locals()else []
        report.write_text(json.dumps(dict(status='FAIL', error=str(error), checks=checks, errors=errors,panels=panels), indent=2), encoding='utf-8')
        raise
    finally:
        for callback in root.tk.call('after', 'info'):
            root.after_cancel(callback)
        root.destroy()
