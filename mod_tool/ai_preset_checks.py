"""Frozen executable smoke check for AI-authored preset creation."""
import copy
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch
from PIL import ImageGrab


def run(Editor,rom,report):
    from custom_presets import PresetStore,prepare
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    root=tk.Tk();root.attributes('-topmost',True);checks=[];errors=[]
    def settle():
        flag=tk.BooleanVar(root,value=False);root.after(100,lambda:flag.set(True));root.wait_variable(flag);root.update()
    def capture(name):
        ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/name)
    try:
        with tempfile.TemporaryDirectory()as temporary,patch.dict(os.environ,LOCALAPPDATA=temporary),patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('tkinter.messagebox.askyesno',return_value=True):
            app=Editor(root);root.geometry('1440x900+0+0');settle()
            assert app.ai_export_button.instate(['disabled'])
            assert app.load_rom(rom);app.project.custom_ships=True;app.show(10);settle()
            assert app.export_preset_name is None
            before_crew=dict(app.project.ships[10])
            app.vars['max_crew'].set('10')
            try:app.commit()
            except ValueError:pass  # Minimum sailors has not yet been lowered.
            else:raise AssertionError('Crew capacity below minimum sailors was accepted')
            app.vars['max_crew'].set(str(before_crew['max_crew']));app.commit();app.cancel_auto_edit()
            assert int(app.extra_vars['factory_crew'].get())==before_crew['factory_crew']
            app.vars['min_crew'].set('1');app.vars['max_crew'].set('50');app.commit();app.cancel_auto_edit();settle()
            assert app.project.ships[10]['factory_crew']==50 and app.extra_vars['factory_crew'].get()=='50'
            assert int(app.extra_vars['factory_cargo'].get())==before_crew['capacity']-before_crew['factory_guns']-50
            app.restore();app.cancel_auto_edit();settle()
            assert app.project.ships[10]==app.project.original[10]
            app.project.custom_ships=False;app.show(10);app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
            checks.append('Lower crew capacity trims starting crew, frees cargo, accepts minimum one and restores stock')
            assert float(app.entries['max_guns'].cget('to'))==200
            assert float(app.extra_entries['capacity'].cget('to'))==2000
            assert float(app.entries['max_crew'].cget('to'))==500
            assert float(app.extra_entries['factory_guns'].cget('to'))==200
            assert float(app.extra_entries['factory_crew'].cget('to'))==500
            from content_library import ContentLibrary,capture_ship
            import portraits
            library=ContentLibrary(app.project.rom);entry=capture_ship(app.project,10)
            entry['ship']['name']='Private Art Name';entry['description']='A private Library design description.'
            raw=portraits.encode_tiles([(i*7+i//64)%16 for i in range(3072)])
            entry['portrait']=portraits.pack({0:raw})[0]['tiles'];library.put(entry)
            before=copy.deepcopy(app.project.manifest())
            for size in ('1440x900','1100x820','640x480'):
                root.geometry(size+'+0+0');settle()
                for button in (app.ai_export_button,app.ai_import_button):
                    app.scroll.focus_visible(SimpleNamespace(widget=button));settle()
                    if root.winfo_containing(button.winfo_rootx()+button.winfo_width()//2,button.winfo_rooty()+button.winfo_height()//2)!=button:
                        capture('AI controls failure.png')
                        raise AssertionError((size,'AI button clipped',button.winfo_rootx(),button.winfo_rooty(),button.winfo_width(),button.winfo_height(),app.scroll.canvas.cget('scrollregion'),app.scroll.canvas.yview()))
                checks.append('AI controls reachable at '+size)
            root.geometry('1440x900+0+0');settle();app.scroll.focus_visible(SimpleNamespace(widget=app.ai_export_button));settle();capture('Presets.png')
            app.ai_export_button.invoke();settle();app.ai_exchange_buttons['Copy for AI'].invoke()
            exported=json.loads(root.clipboard_get());assert exported['version']==2
            assert 'Private Art Name'not in root.clipboard_get()and 'A private Library design description.'not in root.clipboard_get()
            assert all(set(row)=={'art','source','family'}for row in exported['guide']['artwork'])
            assert 'independent ship designs'in ' '.join(exported['guide']['instructions'])
            assert 'image_png_base64'not in root.clipboard_get();capture('AI Export.png')
            target=Path(temporary)/'AI guide.json'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(target)):app.ai_exchange_buttons['Save file'].invoke()
            assert json.loads(target.read_text(encoding='utf-8'))==exported
            app.ai_exchange_dialog.destroy()
            guide=exported['guide'];assert guide['remaining_ship_slots']==10
            available=[p['port']for p in guide['ports']if p['shipyard']for _ in range(p['shipyard_spaces'])]
            additions=[dict(name=f'AI Hull {i+1}',art='A11',ports=[available[i]],industry=0,description=f'An ocean-going ship number {i+1}.')for i in range(10)]
            additions[0].update(maximum_guns=200,starting_guns=200,crew_capacity=500,total_capacity=2000)
            artwork=next(r for r in guide['artwork']if r['source']=='Library');additions[0]['art']=artwork['art']
            response={k:v for k,v in exported.items()if k!='guide'}
            response.update(name='AI Naval Trial',description='A sample translated preset with ten added ships.',add_ships=additions,edit_ships=[dict(ship='Galleon',price_bars=7.5,maximum_guns=200,crew_capacity=500,total_capacity=2000)],gameplay=dict(repair_safeguard=True))
            app.ai_import_button.invoke();settle();root.clipboard_clear();root.clipboard_append(json.dumps(response));app.ai_exchange_buttons['Paste'].invoke();app.ai_exchange_buttons['Review preset'].invoke();settle();capture('AI Review.png')
            assert '75000'in app.ai_review_text.get('1.0','end')
            assert 'AI Hull 10'in app.ai_review_text.get('1.0','end')
            assert 'An ocean-going ship number 10.'in app.ai_review_text.get('1.0','end')
            app.ai_review_cancel.invoke();settle();assert not PresetStore().read()
            target.write_text(json.dumps(response),encoding='utf-8')
            with patch('tkinter.filedialog.askopenfilename',return_value=str(target)):app.ai_exchange_buttons['Open file'].invoke()
            app.ai_exchange_buttons['Review preset'].invoke();settle();app.ai_review_save.invoke();settle()
            assert app.project.manifest()==before
            assert app.export_preset_name is None  # Saving an AI draft has not loaded its settings.
            saved=prepare(app.project,PresetStore().read()['AI Naval Trial']);assert saved.ships[10]['price_gold']==75000 and saved.repair_safeguard
            assert len(saved.ships)==35 and len(app.project.ships)==25
            assert saved.ships[10]['max_guns']==saved.ships[25]['max_guns']==saved.ships[25]['factory_guns']==200
            assert saved.ships[10]['capacity']==saved.ships[25]['capacity']==2000
            assert saved.ships[10]['max_crew']==saved.ships[25]['max_crew']==500
            assert saved.portrait_raw(25)==raw
            library.clear()
            checks.append('Clipboard and file roundtrips; cancel preserves storage; import saves without applying')
            app.custom_preset_name.set('AI Naval Trial');app.custom_preset_choice.event_generate('<<ComboboxSelected>>');settle()
            assert app.project.ships[10]['price_gold']==75000
            assert len(app.project.ships)==35 and app.project.ships[34]['name']=='AI Hull 10'
            assert app.project.portrait_raw(25)==raw
            assert app.export_preset_name=='AI Naval Trial'
            # Browsing a different preset must not rename the currently loaded setup.
            app.custom_preset_name.set('Classic Plus')
            rom_target=Path(temporary)/'AI Naval Trial.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(rom_target))as save_dialog,patch('tkinter.messagebox.showinfo'):
                app.export()
            assert save_dialog.call_args.kwargs['initialfile']=='AI Naval Trial.sfc'
            assert rom_target.exists()and rom_target.with_suffix('.ips').exists()and rom_target.with_suffix('.changes.json').exists()
            assert rom_target.read_bytes()==saved.build()[0]
            assert app.load_rom(rom);assert app.export_preset_name is None
            with patch('tkinter.filedialog.asksaveasfilename',return_value='')as save_dialog:app.export()
            assert save_dialog.call_args.kwargs['initialfile']=='New Horizons Modified.sfc'
            checks.append('Loaded preset names exported ROM/IPS/report; browsing or saving drafts does not rename it; loading a ROM clears the name')
            checks.append('AI appends ten ships; review includes specs/ports/text; save preserves current roster; load activates all 35')
            checks.append('Short artwork codes resolve matching families; Library artwork stays embedded after local deletion')
            assert not errors,errors
        report.write_text(json.dumps(dict(status='PASS',checks=checks,errors=errors),indent=2),encoding='utf-8')
    except Exception as error:
        report.write_text(json.dumps(dict(status='FAIL',checks=checks,error=str(error),errors=errors),indent=2),encoding='utf-8');raise
    finally:
        for callback in root.tk.call('after','info'):root.after_cancel(callback)
        root.destroy()
