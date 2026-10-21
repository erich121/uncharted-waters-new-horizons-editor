"""Gameplay category order, inline controls and correct active scrolling."""
import tkinter as tk,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend import ShipProject

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  app=Editor(root);p=app.project=ShipProject(rom);app.show(0);app.refresh_list();before=p.manifest();errors=[]
  def settle():
   done=tk.BooleanVar(root,value=False);root.after(420,lambda:done.set(True));root.wait_variable(done);root.update()
  def click(widget):
   # Offscreen Tk children may be unmapped; scroll their page position into view first.
   top=0;parent=widget
   while parent!=app.scroll.content:
    top+=parent.winfo_y();parent=parent.master
   height=float(app.scroll.canvas.cget('scrollregion').split()[3])
   app.scroll.canvas.yview_moveto(max(0,top-30)/height);settle()
   app.scroll.focus_visible(SimpleNamespace(widget=widget));settle();x=widget.winfo_width()//2;y=widget.winfo_height()//2
   assert root.winfo_containing(widget.winfo_rootx()+x,widget.winfo_rooty()+y)==widget,('covered',widget)
   widget.event_generate('<ButtonPress-1>',x=x,y=y);widget.event_generate('<ButtonRelease-1>',x=x,y=y);settle()
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
   assert [app.gameplay_notebook.tab(t,'text')for t in app.gameplay_notebook.tabs()]==['Presets','Battles','World','Campaign']
   assert list(app.world_gameplay_sections)==['Fleets','Mates','Items','Trade','Ships','Discoveries']
   assert not hasattr(app,'world_gameplay_notebook')
   for size in ('640x480','1440x900','1672x940'):
    root.geometry(size+'+0+0');app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
    assert app.custom_preset_choice.winfo_ismapped()and app.scroll==app.gameplay_scrollers[0]
    app.gameplay_notebook.select(1);settle();assert app.fleet_check.winfo_ismapped()and app.scroll==app.gameplay_scrollers[1]
    app.gameplay_notebook.select(2);settle();assert app.difficulty_check.winfo_ismapped()and app.scroll==app.gameplay_scrollers[2]
    assert app.difficulty_settings_button.instate(['disabled']);click(app.difficulty_check);assert p.fleet_difficulty and not app.difficulty_settings_button.instate(['disabled'])
    assert app.fleet_dialog.winfo_exists();app.fleet_dialog.destroy();settle();click(app.difficulty_check);assert not p.fleet_difficulty
    assert app.scroll==app.gameplay_scrollers[2]
    click(app.world_gameplay_settings.checks['mates']);assert app.shuffle_dialog.winfo_exists();app.shuffle_dialog.destroy();settle()
    assert app.scroll==app.gameplay_scrollers[2]
    panels=list(app.world_gameplay_sections.values())
    boxes=[(p.winfo_x(),p.winfo_y(),p.winfo_x()+p.winfo_width(),p.winfo_y()+p.winfo_height())for p in panels]
    for i,(x,y,right,bottom)in enumerate(boxes):
     for xx,yy,rr,bb in boxes[i+1:]:assert right<=xx or rr<=x or bottom<=yy or bb<=y,('overlapping cards',size)
    assert app.world_gameplay_columns==1
    if size!='640x480':assert max(box[3]for box in boxes)+20<=app.gameplay_scrollers[2].canvas.winfo_height(),('World cards overflow',size,boxes,app.gameplay_scrollers[2].canvas.winfo_height())

    click(app.world_gameplay_settings.checks['items']);assert app.item_shuffle_dialog.winfo_exists();app.item_shuffle_dialog.destroy();settle()
    app.switch_section('world');app.world.mode.set('Items');app.world.change_mode();settle()
    assert 'read-only'not in app.world.intro.cget('text').lower()and 'read only'not in app.world.intro.cget('text').lower()
    app.world.mode.set('Port Information');app.world.change_mode();settle();assert 'read-only'in app.world.intro.cget('text').lower()
   assert p.manifest()==before and not errors,errors
   # World shuffles mark the data they change, even with manual editing locked.
   from sailors import decode_sailors
   from character_mods import port_shuffle
   from app import CHANGE_ORANGE
   app.switch_section('gameplay');app.gameplay_notebook.select(0);settle()
   p.set_free_agent_shuffle(True,'2026',False);app.reload_project_view();settle()
   assert not p.custom_mates
   assert 'Changed.'in app.section_buttons['mates'].cget('style')
   assert 'Changed.'not in app.section_buttons['gameplay'].cget('style')
   for blind in (False,True):
    p.set_free_agent_shuffle(True,'2026',blind);app.reload_project_view();app.switch_section('mates');settle()
    ports=port_shuffle(p.rom,p.free_agent_shuffle);stock=decode_sailors(p.rom)
    for index,record_id in enumerate(app.mate_rows):
     changed=ports.get(record_id,stock[record_id]['starting_port'])!=stock[record_id]['starting_port']
     assert ('*'in app.list.get(index))==changed
     assert str(app.list.itemcget(index,'foreground'))==(CHANGE_ORANGE if changed else '#17243d')
    moved=next(i for i in app.mate_rows if i in ports and ports[i]!=stock[i]['starting_port'])
    app.show_mate(moved);settle()
    assert str(app.mate_field_widgets['starting_port_name'][1].cget('foreground'))==CHANGE_ORANGE
    if blind:assert app.mate_vars['starting_port_name'].get()=='Hidden (blind shuffle)'
   p.set_free_agent_shuffle(False,'0000');app.reload_project_view();settle()
   assert 'Changed.'not in app.section_buttons['mates'].cget('style')
   assert all('*'not in app.list.get(i)for i in range(app.list.size()))
   p.fleet_control=True;app.update_status();assert 'Changed.'in app.section_buttons['gameplay'].cget('style')
   p.fleet_control=False;app.update_status();assert p.manifest()==before
  report.write_text(json.dumps(dict(status='PASS',gameplay_tabs=['Presets','Battles','World'],world_inline_categories=['Fleets','Mates','Items','Trade','Ships'],dialogs_open_and_cancel=True,one_shared_world_scrollbar=True,responsive_world_cards=True,full_size_world_fits_one_screen=True,items_copy_editable=True,port_information_read_only=True,settings_preserved=True,mate_shuffle_marks_mates_not_gameplay=True,normal_and_blind_row_and_location_colors=True,reset_clears_markers=True,window_sizes=['640x480','1440x900','1672x940']),indent=2),encoding='utf-8')
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
