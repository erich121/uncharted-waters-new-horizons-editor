"""Single-port, regional and information-hub workflow checks."""
import tkinter as tk,json,tempfile,copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend import ShipProject,apply_ips
from economy import stock,values

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  app=Editor(root);root.geometry('1440x900+0+0');app.project=ShipProject(rom);app.project.custom_ships=True;app.show(0);app.refresh_list();app.switch_section('world');w=app.world;p=w.economy_panel
  def settle(ms=80):
   done=tk.BooleanVar(root,value=False);root.after(ms,lambda:done.set(True));root.wait_variable(done);root.update()
  def mode(name):w.mode.set(name);w.change_mode();settle()
  def click(widget):
   app.scroll.focus_visible(SimpleNamespace(widget=widget));settle();x=widget.winfo_width()//2;y=widget.winfo_height()//2
   assert root.winfo_containing(widget.winfo_rootx()+x,widget.winfo_rooty()+y)==widget,('Economy control is covered',str(root.winfo_containing(widget.winfo_rootx()+x,widget.winfo_rooty()+y)),widget.winfo_geometry(),str(app.scroll)==str(w.scroll))
   widget.event_generate('<ButtonPress-1>',x=x,y=y);widget.event_generate('<ButtonRelease-1>',x=x,y=y);settle()
  def edit(widget,text,wait=True):
   app.scroll.focus_visible(SimpleNamespace(widget=widget));settle();widget.delete(0,'end');widget.insert(0,str(text))
   if wait:settle(450)
  errors=[]
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),tempfile.TemporaryDirectory()as directory:
   mode('Economy');assert len(w.rows)==100
   assert p.entries['economy'].instate(['disabled'])and p.restore_region_button.instate(['disabled'])
   click(p.enable_box);assert app.project.custom_economy and not p.entries['economy'].instate(['disabled'])
   w.selected=41;w.details();settle();edit(p.entries['economy'],600);edit(p.entries['industry'],900,False)
   mode('Port Information');w.selected=41;w.details();settle()
   assert w.values['economy'].get()=='600'and w.values['industry'].get()=='900'
   assert w.port_goods.current==600 and w.port_ships.current==900 and not p.winfo_ismapped()
   for g in w.goods_records:
    for source in g['sources']:
     if source['port']==41:assert source['available_at_start']==(source['economy_required']<=600)
   mode('Economy');w.selected=41;w.details();settle()
   assert p.entries['economy'].cget('style')=='Changed.TSpinbox'and 'Changed.'in app.world_nav.cget('style')
   before=copy.deepcopy(app.project.economy_edits)
   edit(p.entries['economy'],'');assert app.project.economy_edits==before
   edit(p.entries['economy'],600)
   with tempfile.TemporaryDirectory()as d:
    path=Path(d)/'economy.json';out=Path(d)/'economy.sfc';app.project.save_project(path);q=ShipProject(rom);q.load_project(path);assert q.economy_edits==app.project.economy_edits
    q.export(out);assert apply_ips(q.rom,out.with_suffix('.ips').read_bytes())==out.read_bytes()
   w.region.set('Northern Europe');w.change_region();settle();ports=p.group();assert len(ports)==15
   w.search.set('Bergen');settle();assert w.rows==[41]
   before=copy.deepcopy(app.project.economy_edits);p.bulk_vars['economy'].set('800');p.preview();settle()
   assert app.project.economy_edits==before and len(p.tree.get_children())==15
   click(p.apply_button)
   current=values(app.project.rom,app.project.economy_edits);original=stock(app.project.rom)
   for port,row in enumerate(current):
    if port in ports:assert row['economy']==800
    else:assert row==original[port]
   assert current[41]['industry']==900
   click(p.restore_button);assert values(app.project.rom,app.project.economy_edits)[41]==original[41]
   before=copy.deepcopy(app.project.economy_edits)
   with patch('tkinter.messagebox.askyesno',return_value=False):click(p.restore_region_button)
   assert app.project.economy_edits==before
   with patch('tkinter.messagebox.askyesno',return_value=True):click(p.restore_region_button)
   assert not app.project.economy_edits
   # Keep a pending edit tied to its old port when choosing another row.
   w.search.set('');settle();w.selected=41;w.details();edit(p.entries['economy'],700,False)
   target=w.rows[0];index=w.rows.index(target);w.list.selection_clear(0,'end');w.list.selection_set(index);w.pick();settle()
   assert w.selected==target and values(app.project.rom,app.project.economy_edits)[41]['economy']==700
   app.switch_section('gameplay');settle()
   with patch('tkinter.messagebox.askyesno',return_value=True):app.restore_defaults_button.invoke()
   app.switch_section('world');mode('Economy');assert not app.project.economy_edits
   for size in ('640x480','1100x820','1672x940'):
    root.geometry(size+'+0+0');settle();app.scroll.focus_visible(SimpleNamespace(widget=p.apply_button));settle()
    assert p.apply_button.winfo_ismapped()and w.list.winfo_height()>=100
    assert w.scroll.canvas.xview()[1]==1.0,(size,'horizontal overflow')
    x=p.apply_button.winfo_rootx()+p.apply_button.winfo_width()//2;y=p.apply_button.winfo_rooty()+p.apply_button.winfo_height()//2
    assert root.winfo_containing(x,y)==p.apply_button,(size,'clipped batch button')
   assert app.project.build()==(app.project.rom,[])and not errors,errors
  report.write_text(json.dumps(dict(status='PASS',automatic_single_port_edits=True,trade_and_ship_unlocks_update=True,information_hub_read_only=True,regional_preview_is_nonmutating=True,whole_region_ignores_search_filter=True,bulk_preserves_other_regions_and_blank_fields=True,restore_port_and_region=True,pending_edit_identity=True,project_rom_ips_roundtrip=True,global_reset=True,responsive_controls=True),indent=2),encoding='utf-8')
 except Exception as error:
  report.write_text(json.dumps(dict(status='FAIL',error=repr(error)),indent=2),encoding='utf-8');raise
 finally:root.destroy()
