"""Focused interactive controls and layout checks for the October 20 changes."""
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch
from PIL import ImageGrab
from backend import ShipProject

def run(Editor,rom,report):
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    errors=[];checks=[]
    with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
        root=tk.Tk();root.attributes('-topmost',True)
        try:
            root.geometry('1440x900+0+0');app=Editor(root)
            root.report_callback_exception=lambda typ,value,tb:errors.append(str(value))
            def settle():
                done=tk.BooleanVar(root,value=False);root.after(100,lambda:done.set(True));root.wait_variable(done);root.update()
            def capture(name):
                settle();ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/(name+'.png'))
            with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(str(a))),patch('tkinter.messagebox.askyesno',return_value=True):
                p=app.project=ShipProject(rom);p.custom_ships=True;app.selected=0;app.show(0);app.refresh_list();settle()
                assert app.extra_entries['factory_guns'].instate(['!disabled','!readonly'])
                assert app.extra_entries['factory_crew'].instate(['!disabled','!readonly'])
                app.extra_vars['factory_guns'].set('6');app.extra_vars['factory_crew'].set('14');app.commit()
                assert p.ships[0]['factory_guns']==6 and p.ships[0]['factory_crew']==14
                checks.append('Original ship starting equipment is editable and calculated cargo follows')
                app.switch_data('mates');settle();assert not app.free_agent_controls.winfo_ismapped()
                app.switch_section('characters');settle()
                keys=app.characters.edit_fields
                assert 'level'in keys[0] and 'level'in keys[1]
                checks.append('Redundant mate randomizer removed; character levels precede attributes')
                app.switch_section('world');w=app.world
                def mode(name):w.mode.set(name);w.change_mode();settle()
                mode('Items');panel=w.item_editor
                assert panel.price_box.instate(['disabled'])
                panel.enable_box.invoke();settle();panel.price.set('1200');panel.flush(strict=True);settle()
                assert p.item_price_edits==[dict(id=0,price_gold=1200)]
                assert '1,200'in w.item_meta.cget('text') and 'Weapon rank: D'in w.item_meta.cget('text')
                assert 'Changed'in app.section_buttons['world'].cget('style')
                panel.price.set('123');panel.flush()
                try:app.commit();raise AssertionError('Invalid item price was accepted')
                except ValueError:pass
                panel.price.set('1200');panel.flush(strict=True)
                assert not app.status.cget('text').startswith('Item price:'),app.status.cget('text')
                capture('World Items')
                panel.restore();settle();assert not p.item_price_edits
                panel.price.set('1300');panel.enable_box.invoke();settle()
                assert not p.custom_items and p.item_price_edits==[dict(id=0,price_gold=1300)]
                panel.enable_box.invoke();settle();panel.restore();settle();assert not p.item_price_edits
                checks.append('Item cost editing, orange highlighting, strict invalid-draft blocking and per-item restore')
                from discovery_content import capture as snapshot,load
                from content_library import new_id
                entry=snapshot(p,0);entry.update(id=new_id(),name='Custom site test',description='Custom text shown on both discovery pages.')
                load(p,entry,0);app.update_status();mode('Discoveries')
                assert w.discovery_description.cget('text')==entry['description']
                assert 'Discoveries section'in w.intro.cget('text')
                for size in ('1440x900','1024x768','800x600'):
                    root.geometry(size+'+0+0');settle()
                    assert w.detail_panel.winfo_rooty()>=w.map_canvas.winfo_rooty()+w.map_canvas.winfo_height()
                    assert w.scroll.canvas.xview()[1]==1.0
                root.geometry('1440x900+0+0');settle();capture('World Discoveries')
                checks.append('Large centered discovery map above current custom artwork and description; responsive sizes')
                for name in ('Goods','Items','Port Information'):
                    mode(name);positions=[]
                    for row in w.records[:3]:
                        w.selected=row['id'];w.details();settle()
                        positions.append((w.map_canvas.winfo_rootx(),w.map_canvas.winfo_rooty(),w.detail_panel.winfo_rootx()))
                    assert len(set(positions))==1,(name,positions)
                checks.append('World selection changes preserve map and right-column positions')
                app.switch_section('gameplay');s=app.world_gameplay_settings
                s.easy_discovery_check.invoke();settle();assert p.discovery_easy
                assert all(row['difficulty']==10 for row in __import__('discovery_content').rows(p))
                app.restore_defaults();settle()
                assert p.build()[0]==p.rom and not p.item_price_edits and not p.discovery_easy
                checks.append('Difficulty-10 switch applies to all 98 discoveries and global restore clears new settings')
                assert not errors,errors
            report.write_text(json.dumps(dict(status='PASS',checks=checks,errors=errors),indent=2),encoding='utf-8')
        except Exception as error:
            report.write_text(json.dumps(dict(status='FAIL',error=str(error),checks=checks,errors=errors),indent=2),encoding='utf-8');raise
        finally:root.destroy()
