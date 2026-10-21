"""Isolated source/frozen checks for the current-project discovery section."""
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch
from PIL import ImageGrab
from backend import ShipProject
from content_library import new_id
from discovery_content import capture


def run(Editor, rom, report):
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
        root=tk.Tk();root.attributes('-topmost',True)
        def settle():
            if root.state()=='iconic':root.deiconify();root.lift()
            flag=tk.BooleanVar(root,value=False);root.after(150,lambda:flag.set(True));root.wait_variable(flag);root.update()
        try:
            root.geometry('1440x900+0+0');app=Editor(root)
            with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**kw:errors.append(a)),patch('tkinter.messagebox.askyesno',return_value=True):
                app.switch_section('discoveries');settle();panel=app.discoveries
                assert not panel.rows and panel.replace_button.instate(['disabled'])
                p=app.project=ShipProject(rom);app.selected=0;app.show(0);app.refresh_list();app.update_status();settle()
                assert panel.list.size()==98 and panel.heading.cget('text')=='Stonehenge'
                order=[key for key in app.section_buttons]
                assert order.index('discoveries')==order.index('ships')+1
                assert panel.description.cget('text')==panel.rows[0]['description']
                assert not p.custom_discoveries and panel.bulk_button.instate(['disabled'])
                panel.custom_box.invoke();settle();assert p.custom_discoveries
                checks.append('Custom checkbox defaults off and unlocks manual replacement controls')
                checks.append('Direct navigation after Ships; all98 current names, artwork and text; safe empty state')
                panel.list.selection_clear(0,'end');panel.list.selection_set(1);panel.list.event_generate('<<ListboxSelect>>');settle()
                assert panel.heading.cget('text')=='Rosetta Stone'
                panel.search.set('Stonehenge');settle();assert panel.list.size()==1 and panel.selected==0
                panel.search.set('no-such-discovery');settle();assert panel.list.size()==0 and panel.replace_button.instate(['disabled'])
                panel.search.set('');settle()
                checks.append('Search, selection, no results and returning to full list')
                app.library.refresh();entry=capture(p,0);entry.update(id=new_id(),name='Avebury test',description='A new description in the current project.')
                app.library.store.put(entry)
                panel.selected=0;panel.render();panel.choose_replacement();settle()
                dialog=panel.replacement_dialog
                def widgets(parent):
                    for child in parent.winfo_children():
                        yield child
                        yield from widgets(child)
                next(w for w in widgets(dialog)if w.winfo_class()=='TButton'and w.cget('text')=='Use discovery').invoke();settle()
                assert p.discovery_entries[0]==entry and panel.heading.cget('text')=='Avebury test'
                assert 'current project'in panel.description.cget('text')
                assert 'Changed'in app.section_buttons['discoveries'].cget('style')
                assert 'Changed'not in app.section_buttons['world'].cget('style')
                checks.append('Choose fixed-location Library alternative; current picture/text and orange section update')
                second=capture(p,1);second.update(id=new_id(),name='Second custom site')
                alternate=dict(entry,id=new_id(),name='Another choice')
                for e in [second,alternate,capture(p,2)]:app.library.store.put(e)
                before=p.manifest();panel.load_all();settle()
                assert set(panel.bulk_choices)=={0,1}
                assert panel.bulk_choices[0].get()==entry['name']
                next(w for w in widgets(panel.bulk_dialog)if w.winfo_class()=='TButton'and w.cget('text')=='Cancel').invoke();settle()
                assert p.manifest()==before
                panel.load_all();settle()
                next(w for w in widgets(panel.bulk_dialog)if w.winfo_class()=='TButton'and w.cget('text')=='Load all custom discoveries').invoke();settle()
                assert p.discovery_entries[0]==entry and p.discovery_entries[1]==second and 2 not in p.discovery_entries
                before_lock=p.build()[0]
                panel.custom_box.invoke();settle()
                assert not p.custom_discoveries and panel.bulk_button.instate(['disabled']) and p.discovery_entries
                assert p.build()[0]==before_lock
                panel.choose_replacement();assert not any(isinstance(w,tk.Toplevel)for w in root.winfo_children())
                assert 'Changed'in app.section_buttons['discoveries'].cget('style')
                panel.custom_box.invoke();settle()
                __import__('discovery_content').load(p,entry,0);__import__('discovery_content').load(p,second,1);app.update_status();settle()
                panel.selected=1;panel.render();panel.restore();settle();panel.selected=0;panel.render()
                checks.append('Bulk matching, duplicate choices, stock exclusion, cancellation, preserved alternatives and locking preserves loaded values; explicit restore keeps outgoing content in Library')

                app.switch_section('library');app.library.kind.set('Discoveries');app.library.change_kind();settle()
                assert not app.library.load_card.winfo_ismapped()
                app.library.kind.set('Ships');app.library.change_kind();settle()
                assert app.library.load_card.winfo_ismapped()
                app.reset_section('world');settle();assert p.discovery_entries[0]==entry
                checks.append('Library discovery loading removed; ship loading retained; World reset keeps discovery edits')
                app.switch_section('ships');app.switch_section('discoveries');settle();assert panel.heading.cget('text')=='Avebury test'
                p.discovery_rewrites=True;app.update_status();settle()
                panel.selected=1;panel.render();assert panel.description.cget('text')==__import__('discovery_rewrites').DESCRIPTIONS[1]
                checks.append('Navigation preserves selection; effective rewritten and custom descriptions are shown')
                p.discovery_rewrites=False;panel.selected=0;app.update_status();settle()
                ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/'Discoveries.png')
                for size in ('1440x900','1280x720','1024x768','800x600','640x480'):
                    root.geometry(size+'+0+0');settle();panel.scroll.canvas.yview_moveto(1);settle()
                    assert panel.list.winfo_height()>20,(size,'list clipped',panel.list.winfo_height())
                    for button in panel.buttons:
                        assert button.winfo_rootx()+button.winfo_width()<=root.winfo_rootx()+root.winfo_width(),(size,'button overflow')
                    assert panel.frame.winfo_ismapped()
                    checks.append('Discovery layout and scrolling at '+size)
                root.geometry('1440x900+0+0');settle()
                panel.restore();settle();assert not p.discovery_entries and panel.heading.cget('text')=='Stonehenge'
                assert any(e['id']==entry['id']for e in app.library.store.entries)
                assert 'Changed'not in app.section_buttons['discoveries'].cget('style')
                checks.append('Restore original keeps outgoing Library copy and clears changed marker')
                assert not errors,errors
            report.write_text(json.dumps(dict(status='PASS',checks=checks,errors=errors),indent=2),encoding='utf-8')
        except Exception as error:
            report.write_text(json.dumps(dict(status='FAIL',error=str(error),checks=checks,errors=errors),indent=2),encoding='utf-8');raise
        finally:
            root.destroy()
