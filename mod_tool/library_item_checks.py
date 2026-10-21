"""Functional Library item, currency and discovery dashboard checks."""
import json,os,tempfile,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from PIL import ImageGrab
from backend import ShipProject

def run(Editor,rom,report):
 report=Path(report);report.parent.mkdir(parents=True,exist_ok=True);errors=[];checks=[]
 with tempfile.TemporaryDirectory()as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
  root=tk.Tk();app=Editor(root);root.geometry('1440x900+0+0')
  root.report_callback_exception=lambda typ,value,tb:errors.append(str(value))
  def settle():
   done=tk.BooleanVar(root,value=False);root.after(180,lambda:done.set(True));root.wait_variable(done);root.update()
  def screenshot(name):
   ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(report.parent/(name+'.png'))
  try:
   with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(str(a))),patch('tkinter.messagebox.askyesno',return_value=True):
    p=app.project=ShipProject(rom);app.selected=0;app.refresh_list();app.show(0);settle()
    app.switch_section('library');lib=app.library
    for kind in ('Items','Ships','Discoveries','Items'):
     lib.kind.set(kind);lib.change_kind();settle()
    lib.source.current(0);lib.save_ship();settle();assert len(lib.selected())==1
    assert lib.selected()[0]['kind']=='item' and lib.selected()[0]['item_id']==0
    assert not lib.target.winfo_ismapped() and lib.replace_button.winfo_ismapped()
    entry=lib.selected()[0].copy();entry['id']=__import__('content_library').new_id();entry['price_gold']=50000
    lib.store.put(entry);lib.refresh();index=next(i for i,e in enumerate(lib.rows)if e['id']==entry['id']);lib.list.selection_clear(0,'end');lib.list.selection_set(index);lib.preview();lib.load_item();settle()
    assert __import__('item_prices').price(p,0)==50000
    assert '5 gold bars'in lib.ship_summary.cget('text')
    screenshot('Library Items');checks.append('Items Library save, preview, load and switching among all three kinds')
    app.switch_section('world');w=app.world;w.mode.set('Items');w.change_mode();settle();panel=w.item_editor
    assert panel.price.get()=='5' and panel.price_unit=='bars'
    panel.enable_box.invoke();settle();panel.price.set('6.25');panel.flush(strict=True);settle()
    assert __import__('item_prices').price(p,0)==62500 and '6.25 gold bars'in w.item_meta.cget('text')
    screenshot('Item price bars');checks.append('Gold bar editing and World item prices preserve exact gold amounts')
    w.mode.set('Discoveries');w.change_mode();settle()
    dimensions=[]
    for size in ('1280x720','1440x900','1920x1080'):
     root.geometry(size+'+0+0');settle();settle()
     for slot in (0,37,97):
      w.selected=slot;w.details();settle();settle()
      actual=w.scroll.canvas.winfo_height();needed=w.scroll.content.winfo_reqheight()
      dimensions.append((size,slot,needed,actual))
      assert needed<=actual,(size,slot,'discovery dashboard overflows',needed,actual,'map',w.map_canvas.winfo_height(),w.map_canvas.winfo_reqheight(),w.map_canvas.cget('width'),'panel',w.map_panel.winfo_reqheight(),'detail',w.detail_panel.winfo_reqheight())
     if size=='1440x900':screenshot('World Discoveries')
    checks.append(dict(discovery_layouts=dimensions))
    with patch('tkinter.messagebox.askyesno',return_value=False)as prompt:
     app.restore_defaults();message=prompt.call_args.args[1]
     assert 'Your Library, saved presets'in message and 'save games will not be changed'in message
    app.switch_section('gameplay');settle()
    settings=app.world_gameplay_settings
    texts=[]
    def walk(widget):
     try:texts.append(widget.cget('text'))
     except tk.TclError:pass
     for child in widget.winfo_children():walk(child)
    walk(settings.frame if hasattr(settings,'frame')else app.settings_area)
    assert 'Use rewritten original discovery descriptions'in texts
    assert not any('More informative, adventurous text'in text for text in texts if isinstance(text,str))
    checks.append('Clear reset confirmation and concise discovery checkbox')
    assert not errors,errors
   report.write_text(json.dumps(dict(status='PASS',checks=checks,errors=errors),indent=2),encoding='utf-8')
  except Exception as error:
   report.write_text(json.dumps(dict(status='FAIL',error=str(error),checks=checks,errors=errors),indent=2),encoding='utf-8');raise
  finally:root.destroy()
