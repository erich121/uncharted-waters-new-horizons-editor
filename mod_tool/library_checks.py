"""Windows Library workflow using real Tk controls and isolated storage."""
import json,os,tempfile,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject
from content_library import ContentLibrary,new_id

def run(Editor,rom,report):
 report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 root=tk.Tk();root.attributes('-topmost',True);errors=[];checks=[]
 def settle():
  flag=tk.BooleanVar(root,value=False);root.after(120,lambda:flag.set(True));root.wait_variable(flag);root.update()
 try:
  with tempfile.TemporaryDirectory()as d,patch.dict(os.environ,{'LOCALAPPDATA':d}),patch('tkinter.messagebox.showerror',side_effect=lambda *a,**kw:errors.append(a)),patch('tkinter.messagebox.askyesno',return_value=True):
   app=Editor(root);root.geometry('1440x900+0+0');settle()
   app.switch_section('library');settle();assert app.library.save_button.instate(['disabled'])
   p=app.project=ShipProject(rom);app.selected=0;app.show(0);app.refresh_list();app.update_status();settle()
   app.source.configure(text='Stock USA ROM verified: '+Path(rom).name)
   panel=app.library
   defaults=__import__('copy').deepcopy(panel.store.document())
   assert {e['kind']for e in defaults['entries']}=={'ship','discovery','item'}
   assert len([e for e in defaults['entries']if e['kind']=='ship'])==60
   assert set(defaults['collections'])=={'Stock Ships','Stock Discoveries'}
   assert len(defaults['collections']['Stock Ships'])==25
   assert len(defaults['collections']['Stock Discoveries'])==98
   assert len({e['ship']['name']for e in defaults['entries']if e['kind']=='ship'})==60
   panel.collection.set('Stock Ships');panel.refresh();settle()
   assert panel.list.size()==25
   panel.list.selection_set(0);panel.preview()
   assert panel.delete_button.instate(['disabled'])
   before_stock=__import__('copy').deepcopy(panel.store.document());panel.delete()
   assert panel.store.document()==before_stock
   assert panel.delete_collection_button.instate(['disabled'])
   panel.delete_collection();assert panel.store.document()==before_stock
   panel.collection.set('Stock Discoveries')
   panel.kind.set('Discoveries');panel.change_kind();settle()
   assert panel.list.size()==98 and panel.edit_button.instate(['disabled'])
   assert len(panel.target.cget('values'))==98
   panel.edit_discovery();assert not getattr(panel,'discovery_dialog',None)
   panel.collection.set('All entries')
   panel.kind.set('Items');panel.change_kind();settle()
   assert panel.list.size()==61 and panel.delete_button.instate(['disabled'])
   panel.kind.set('Ships');panel.change_kind();settle()
   panel.collection.set('All entries');panel.refresh()
   checks.append('Only Stock Ships and Stock Discoveries are default collections; all custom content and stock items remain in All entries')
   panel.store.clear();panel.refresh();assert panel.list.size()==0
   panel.use_locations.set(False)
   panel.source.current(10);panel.save_button.invoke();settle();assert panel.list.size()==1
   assert len(ContentLibrary(p.rom,panel.store.root).entries)==1
   p.fleet_rules[0][0][1]=10
   panel.target.current(13);panel.replace_button.invoke();settle()
   assert p.ships[13]['name']=='Galleon'and p.ships[10]['name']=='Sloop'and p.fleet_rules[0][0][1]==13
   checks.append('Original ships archived; slot swap and Custom Fleet identity remapping through controls')
   panel.search.set('Galleon');settle();assert panel.list.size()==1
   with patch('tkinter.simpledialog.askstring',return_value='Royal Trader'):panel.duplicate_button.invoke()
   settle();panel.search.set('Royal');settle();assert panel.list.size()==1
   panel.add_button.invoke();settle();assert len(p.ships)==26 and p.ships[25]['name']=='Royal Trader'
   panel.source.current(25);p.update(25,dict(max_guns=80));app.show(25);panel.save_button.invoke();settle()
   panel.list.selection_clear(0,'end');panel.list.selection_set(0)
   with patch('tkinter.simpledialog.askstring',return_value='My Ships'):panel.save_collection()
   settle();assert panel.collection.get()=='My Ships'
   share=Path(d)/'share.nhlib'
   with patch('tkinter.filedialog.asksaveasfilename',return_value=str(share)):panel.export_file()
   assert share.exists()
   project=Path(d)/'portable.json';p.save_project(project)
   q=ShipProject(rom);q.load_project(project);assert q.build()==p.build()
   checks.append('Duplicate, add, update, collections, export and portable project round trip')
   panel.search.set('');panel.collection.set('All entries')
   p.update(25,dict(ports=[3],industry=600));app.show(25);panel.source.current(25);panel.save_button.invoke();settle()
   saved=next(e for e in panel.store.entries if e['id']==p.ship_identities[25])
   assert saved['availability']==dict(ports=[3],industry=600)
   p.update(25,dict(ports=[4],industry=500));app.show(25)
   panel.search.set('Royal');settle();panel.target.current(25);panel.use_locations.set(True)
   panel.replace_button.invoke();settle()
   assert p.all_offers()[25]==dict(ports=[3],industry=600)
   assert 'Barcelona'in panel.details.cget('text')and '600'in panel.details.cget('text')
   checks.append('Saved ship ports and industry restored through Windows controls')
   for size in ('1440x900','1280x720','1024x768','640x480'):
    root.geometry(size+'+0+0');settle();panel.scroll.canvas.yview_moveto(1);settle()
    assert panel.list.winfo_height()>20,(size,'Library list collapsed')
    assert panel.footer.winfo_rooty()+panel.footer.winfo_height()<=panel.left.winfo_rooty()+panel.left.winfo_height()+1
    if size=='640x480':
     assert panel.actions_button.winfo_ismapped();panel.populate_actions()
    assert panel.add_button.winfo_ismapped()
    assert panel.add_button.winfo_rootx()+panel.add_button.winfo_width()<=root.winfo_rootx()+root.winfo_width(),(size,'action exceeds width')
    app.switch_data('ships');settle();app.switch_section('library');settle()
    checks.append('Library and section switching at '+size)
   root.geometry('1440x900+0+0');settle();panel.scroll.canvas.yview_moveto(0);settle()
   for widget in (panel.replace_button,panel.add_button,panel.save_button):
    assert widget.winfo_rooty()>=panel.scroll.canvas.winfo_rooty()
    assert widget.winfo_rooty()+widget.winfo_height()<=panel.scroll.canvas.winfo_rooty()+panel.scroll.canvas.winfo_height()
    assert root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)==widget,'Desktop Library action is covered'
   checks.append('Desktop load, add and save actions are visible without scrolling')
   try:
    from PIL import ImageGrab
    ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/'Library.png')
   except Exception as error:checks.append('Screen capture unavailable: '+str(error))
   app.switch_data('ships');settle();app.switch_section('gameplay');settle();app.switch_section('world');settle();app.switch_section('library');settle()
   panel.collection.set('My Ships');panel.refresh_list();settle()
   before=panel.store.document();before_project=p.manifest()
   with patch('tkinter.messagebox.askyesno',return_value=False):panel.delete_collection_button.invoke()
   assert panel.store.document()==before
   panel.delete_collection_button.invoke();settle()
   assert 'My Ships'not in panel.store.collections
   assert panel.store.entries==before['entries']and p.manifest()==before_project
   assert 'My Ships'not in ContentLibrary(p.rom,panel.store.root).collections
   assert panel.collection.get()=='All entries'
   checks.append('Delete collection removes only grouping; cancel and project/content preservation verified')
   from content_library import capture_ship
   isolated=Path(d)/'two-windows'
   first=ContentLibrary(p.rom,isolated);second=ContentLibrary(p.rom,isolated)
   editable=capture_ship(p,0);editable['id']=new_id()
   first.put(editable);second.put(capture_ship(p,1))
   assert len(ContentLibrary(p.rom,isolated).entries)==2
   entry=__import__('copy').deepcopy(second.entries[0]);entry['ship']['hull']=41
   first.reload_if_changed();first.put(entry)
   entry['ship']['hull']=42
   try:second.put(entry)
   except ValueError:pass
   else:raise AssertionError('Concurrent Library conflict was not rejected')
   checks.append('Packaged Library merges separate writes and rejects conflicting versions')
   saved_goods=p.goods_shuffle;p.goods_shuffle=dict(seed='6789',mode='all',blind=True)
   app.refresh_active_changes()
   assert '6789'not in app.active_changes_text.cget('text')
   p.goods_shuffle=saved_goods
   checks.append('Blind goods seed hidden in actual Active Changes widget')
   library_before=__import__('copy').deepcopy(panel.store.document())
   assert p.ships[p.fleet_rules[0][0][1]]['name']=='Galleon'
   app.reset_section('ships');settle()
   assert p.fleet_rules[0][0][1]==10 and p.ships[10]['name']=='Galleon'
   assert panel.store.document()==library_before
   checks.append('Ships restore follows original fleet identities and keeps saved Library content')
   app.switch_data('ships');p.custom_ships=True;app.show(0)
   app.add_button.invoke();app.cancel_auto_edit()
   slot=app.selected;entry=capture_ship(p,slot);panel.store.put(entry)
   app.vars['name'].set('Latest Archive')
   assert app.auto_timer is not None
   app.remove_button.invoke()
   assert len(p.ships)==25 and app.auto_timer is None
   assert next(e for e in panel.store.entries if e['id']==entry['id'])==entry
   assert any(e['id']!=entry['id']and e['ship']['name']=='Latest Archive'for e in panel.store.entries)
   checks.append('Remove commits pending edits and preserves an older Library revision')
   app.switch_section('library');settle()
   panel.search.set('no-match-zzzzz');settle()
   with patch('tkinter.filedialog.asksaveasfilename')as picker:panel.export_file()
   picker.assert_not_called()
   menu=root.nametowidget(str(panel.footer_buttons[1].cget('menu')))
   assert menu.entrycget(0,'state')=='disabled'
   panel.populate_actions();assert panel.actions_menu.entrycget(1,'state')=='disabled'
   checks.append('Empty selected export is disabled in both Library menus')
   panel.search.set('');root.focus_force();app.open_search();settle()
   assert root.focus_get()==panel.search_entry
   checks.append('Library Ctrl+F focuses its search field')
   library_path=panel.store.path;valid_bytes=library_path.read_bytes()
   library_path.write_text('{broken',encoding='utf-8');panel.store=None;panel.refresh()
   assert panel.store is None and library_path.read_text(encoding='utf-8')=='{broken'
   library_path.write_bytes(valid_bytes);panel.refresh()
   assert panel.store is not None and panel.error is None and panel.save_button.instate(['!disabled'])
   checks.append('Repaired Library reopens without restarting or replacing unreadable data')
   before_reset=p.manifest()
   panel.clear_library();settle()
   assert panel.store.collections==defaults['collections']
   assert {e['id']:e for e in panel.store.entries}=={e['id']:e for e in defaults['entries']}
   assert p.manifest()==before_reset
   assert panel.store.path.with_suffix('.json.bak').exists()
   panel.store.path.unlink();panel.refresh();settle()
   assert panel.store.collections==defaults['collections']
   assert {e['id']:e for e in panel.store.entries}=={e['id']:e for e in defaults['entries']}
   assert p.manifest()==before_reset
   checks.append('Library Delete restores defaults; missing Library file recreates defaults without changing project')
   assert not errors,errors
  report.write_text(json.dumps(dict(status='PASS',checks=checks,errors=errors),indent=2),encoding='utf-8')
 except Exception as error:
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),checks=checks,errors=errors),indent=2),encoding='utf-8');raise
 finally:root.destroy()
