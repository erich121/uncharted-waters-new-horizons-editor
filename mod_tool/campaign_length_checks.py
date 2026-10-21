"""Isolated source/frozen workflow for the 50-year campaign option."""
import json,os,tempfile
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
from PIL import ImageGrab
from backend import ShipProject
from campaign_length import OFFSET,EXTENDED


def run(Editor,rom,report):
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    with tempfile.TemporaryDirectory(prefix='campaign-ui-')as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
        root=tk.Tk()
        try:
            root.geometry('1440x900+0+0');app=Editor(root)
            def settle():
                done=tk.BooleanVar(root,value=False);root.after(150,lambda:done.set(True));root.wait_variable(done);root.update()
            with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('tkinter.messagebox.askyesno',return_value=True):
                w=app.world_gameplay_settings
                assert w.campaign_check.instate(['disabled'])
                p=app.project=ShipProject(rom);app.selected=0;app.show(0);app.refresh_list();app.update_status()
                app.source.configure(text='Stock USA ROM verified: '+Path(rom).name)
                app.switch_section('gameplay');app.gameplay_notebook.select(3);settle()
                assert [app.gameplay_notebook.tab(t,'text')for t in app.gameplay_notebook.tabs()]==['Presets','Battles','World','Campaign']
                assert not w.campaign_var.get()
                w.campaign_check.invoke();settle()
                assert p.fifty_year_campaign and 'Changed'in app.section_buttons['gameplay'].cget('style')
                assert '50-year campaign'in app.active_changes_text.cget('text')
                assert p.build()[0][OFFSET:OFFSET+3]==EXTENDED
                assert not w.gold_enabled.get()and w.gold_entry.instate(['disabled'])
                w.gold_check.invoke();settle();assert p.starting_gold==5000
                w.gold_amount.set('25');app.commit();settle()
                assert p.starting_gold==250000 and w.gold_entry.instate(['!disabled'])
                w.gold_entry.event_generate('<MouseWheel>',delta=120);settle();assert w.gold_amount.get()=='25'
                w.gold_amount.set('25.0001')
                try:app.commit()
                except ValueError:pass
                else:raise AssertionError('Above-cap starting gold was accepted')
                assert p.starting_gold==250000
                w.gold_amount.set('25');app.commit();settle()
                checks.append('Starting gold checkbox, disabled input, 25-bar cap, wheel safety and invalid-draft protection')
                w.instant_check.invoke();settle();assert p.instant_shipbuilding
                from instant_shipbuilding import OFFSET as TIMER,INSTANT
                assert p.build()[0][TIMER:TIMER+2]==INSTANT
                checks.append('Instant shipbuilding checkbox exports zero-day timer')
                app.gameplay_scroll.canvas.yview_moveto(1);settle()
                ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/'50-year campaign.png')
                checks.append('Default Off; loaded-ROM checkbox exports extended deadline and marks Gameplay orange')
                w.gold_check.invoke();settle();assert p.starting_gold is None and w.gold_entry.instate(['disabled'])
                w.instant_check.invoke();settle();assert not p.instant_shipbuilding
                w.campaign_check.invoke();settle();assert not p.fifty_year_campaign and p.build()[0]==p.rom
                checks.append('Off restores exact stock ROM')
                w.campaign_check.invoke();w.gold_check.invoke();w.instant_check.invoke();settle()
                app.reset_section('world');settle();assert p.fifty_year_campaign and p.starting_gold==250000 and p.instant_shipbuilding
                app.reset_section('gameplay');settle();assert not p.fifty_year_campaign and not w.campaign_var.get()and p.starting_gold is None and not p.instant_shipbuilding
                checks.append('World-data reset preserves campaign choice; Reset Gameplay clears it')
                w.campaign_check.invoke();settle();app.restore_defaults();settle()
                assert not p.fifty_year_campaign and p.build()[0]==p.rom and not errors,errors
                checks.append('Restore all defaults clears option')
            report.write_text(json.dumps(dict(status='PASS',checks=checks),indent=2)+'\n',encoding='utf-8')
        except Exception as e:
            report.write_text(json.dumps(dict(status='FAIL',error=str(e),checks=checks),indent=2)+'\n',encoding='utf-8');raise
        finally:root.destroy()
