"""Windows discovery Library creation, conversion, collections and pool workflow."""
import copy
import json
import os
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageGrab
from backend import ShipProject
from content_library import new_id, ContentLibrary
from discovery_content import capture, rows


def run(Editor, rom, report):
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    checks, errors = [], []
    def settle():
        flag = tk.BooleanVar(root, value=False)
        root.after(100, lambda: flag.set(True))
        root.wait_variable(flag)
        root.update()
    try:
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'LOCALAPPDATA': d}), patch('tkinter.messagebox.showerror', side_effect=lambda *a, **k: errors.append(a)), patch('tkinter.messagebox.askyesno', return_value=True):
            app = Editor(root)
            p = app.project = ShipProject(rom)
            app.selected = 0
            app.show(0)
            app.source.configure(text='Stock USA ROM verified: '+Path(rom).name)
            app.refresh_list()
            root.geometry('1440x900+0+0')
            app.switch_section('library')
            panel = app.library
            panel.store.clear();panel.refresh()  # This workflow explicitly starts from a blank Library.
            panel.kind.set('Discoveries')
            panel.change_kind()
            settle()
            assert panel.list.size() == 0
            panel.create_button.invoke()
            settle()
            editor = panel.discovery_editor
            editor['name'].set('Test Island')
            editor['description'].delete('1.0', 'end')
            editor['description'].insert('1.0', 'A custom island with artwork imported through the converter.')
            editor['difficulty'].set('75')
            png = Path(d)/'island.png'
            image = Image.new('RGB', (64, 64))
            image.putdata([((x*17)%256, (x*5)%256, (x*3)%256) for x in range(4096)])
            image.save(png)
            with patch('tkinter.filedialog.askopenfilename', return_value=str(png)):
                editor['import_png']()
            editor['save'].invoke()
            settle()
            assert panel.list.size() == 1
            assert not panel.load_card.winfo_ismapped()
            app.switch_section('discoveries');settle()
            app.discoveries.custom_box.invoke();settle()
            app.discoveries.selected=0;app.discoveries.render();app.discoveries.choose_replacement();settle()
            def descendants(parent):
                for child in parent.winfo_children():
                    yield child
                    yield from descendants(child)
            dialog=app.discoveries.replacement_dialog
            next(w for w in descendants(dialog) if w.winfo_class()=='TButton' and w.cget('text')=='Use discovery').invoke();settle()
            assert p.discovery_entries[0]['name']=='Test Island'
            app.switch_section('library');settle()
            checks.append('Create/convert in Library; replace through dedicated Discoveries section only')
            share_one = Path(d)/'one.nhlib'
            panel.store.export_file(share_one, [p.discovery_entries[0]['id']])
            other_one = ContentLibrary(p.rom, Path(d)/'one-library')
            other_one.import_file(share_one)
            assert other_one.entries[0]['replaces'] == 'stock-discovery:00'
            checks.append('Library import/export preserves fixed original location')
            panel.store.put(capture(p,2));panel.refresh();settle()
            stored=len(panel.store.entries);before=p.manifest()
            assert any(e['id'].startswith('stock-') for e in panel.rows)
            panel.hide_stock_check.invoke();settle()
            assert panel.rows and not any(e['id'].startswith('stock-') for e in panel.rows)
            panel.kind.set('Ships');panel.change_kind();settle()
            from content_library import capture_ship
            ship=capture_ship(p,0);panel.store.put(ship)
            custom_ship=copy.deepcopy(ship);custom_ship['id']=new_id();custom_ship['ship']['name']='Custom test ship';panel.store.put(custom_ship)
            panel.refresh();settle();assert [e['id']for e in panel.rows]==[custom_ship['id']]
            panel.hide_stock_check.invoke();settle();assert len(panel.rows)==2
            assert p.manifest()==before
            panel.kind.set('Discoveries');panel.change_kind();settle()
            checks.append('Hide stock content filters ships and discoveries without deleting data or changing project')
            app.switch_section('world')
            app.world.mode.set('Discoveries')
            app.world.change_mode()
            app.world.selected = 0
            app.world.details()
            settle()
            assert app.world.heading.cget('text') == 'Test Island'
            assert 'custom island' in app.world.discovery_description.cget('text')
            checks.append('World information hub shows project discovery data and artwork')
            app.switch_section('library')
            entries = []
            for i in range(100):
                entry = capture(p, i%98)
                entry.update(id=new_id(), name=f'Custom Site {i:03d}')
                entries.append(entry)
            panel.store.entries.extend(entries)
            panel.store.save()
            panel.search.set('Custom Site')
            panel.refresh()
            settle()
            assert panel.list.size() == 100
            panel.list.selection_clear(0, 'end')
            panel.list.selection_set(0, 97)
            panel.preview()
            assert panel.add_button.instate(['!disabled'])
            with patch('tkinter.simpledialog.askstring', return_value='Custom Pool'):
                panel.save_collection()
            from discovery_content import prepare_replacements
            trial=prepare_replacements(p,entries[:98])
            p.discovery_entries,p.discovery_identities=trial.discovery_entries,trial.discovery_identities
            assert len(p.discovery_entries)==98 and rows(p)[0]['name']=='Custom Site 000'
            project = Path(d)/'discovery-project.json'
            p.save_project(project)
            q = ShipProject(rom)
            q.load_project(project)
            assert q.build() == p.build()
            share = Path(d)/'collection.nhlib'
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(share)):
                panel.export_file()
            other = ContentLibrary(p.rom, Path(d)/'other')
            other.import_file(share)
            assert len(other.entries) == 98 and 'Custom Pool' in other.collections
            checks.append('Choose 98 from 100, save collection, load pool, share collection, reopen portable project')
            for size in ('1440x900', '1280x720', '1024x768', '640x480'):
                root.geometry(size+'+0+0')
                settle()
                assert panel.list.winfo_height() > 20
                assert panel.footer.winfo_rooty()+panel.footer.winfo_height() <= panel.left.winfo_rooty()+panel.left.winfo_height()+1
                if size == '640x480':
                    assert panel.actions_button.winfo_ismapped()
                    panel.populate_actions()
                panel.scroll.canvas.yview_moveto(1)
                settle()
                assert not panel.load_card.winfo_ismapped()
                checks.append('Discovery Library layout at '+size)
            root.geometry('1440x900+0+0')
            settle()
            panel.scroll.canvas.yview_moveto(0)
            settle()
            ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(report.parent/'Discovery Library.png')
            app.reset_section('discoveries')
            settle()
            assert not p.discovery_entries and p.build()[0] == p.rom
            checks.append('Restore all originals while preserving custom pool in Library')
            assert not errors, errors
        report.write_text(json.dumps(dict(status='PASS', checks=checks, errors=errors), indent=2), encoding='utf-8')
    except Exception as error:
        report.write_text(json.dumps(dict(status='FAIL', error=str(error), checks=checks, errors=errors), indent=2), encoding='utf-8')
        raise
    finally:
        root.destroy()
