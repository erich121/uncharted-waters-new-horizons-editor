"""Ship-building checkbox, preview, blind hiding, reset and added-hull isolation."""
import tkinter as tk,json,copy
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject,TOOL_VERSION

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  app=Editor(root);root.geometry('1440x900+0+0');p=app.project=ShipProject(rom);p.add_ship(10);p.custom_ships=True;p.set_goods_shuffle('1234');extra=copy.deepcopy(p.ships[25]);app.show(0);app.refresh_list();app.update_status();w=app.world_gameplay_settings;errors=[]
  def settle():
   ready=tk.BooleanVar(value=False);root.after(100,lambda:ready.set(True));root.wait_variable(ready);root.update()
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('tkinter.messagebox.askyesno',return_value=True):
   app.switch_section('gameplay');app.gameplay_notebook.select(2);settle()
   assert w.checks['shipbuilding'].cget('text')=='Use ship building randomizer'and 'Ships'in app.world_gameplay_sections
   before=p.manifest();w.checks['shipbuilding'].invoke();settle();app.shipbuilding_shuffle_seed.set('2026');settle()
   assert app.shipbuilding_shuffle_preview.size()==75 and p.manifest()==before
   app.shipbuilding_shuffle_buttons[3].invoke();settle();assert p.manifest()==before and not w.variables['shipbuilding'].get()
   w.open('shipbuilding');settle();app.shipbuilding_shuffle_seed.set('2026');app.shipbuilding_shuffle_blind.set(True);settle()
   assert app.shipbuilding_shuffle_preview.size()==1 and 'hidden'in app.shipbuilding_shuffle_preview.get(0)
   app.shipbuilding_shuffle_dialog.geometry('460x360+0+0');settle();assert app.shipbuilding_shuffle_buttons[1].winfo_ismapped()
   app.shipbuilding_shuffle_buttons[1].invoke();settle();assert w.variables['shipbuilding'].get()and 'Blind'in w.links['shipbuilding'].cget('text')
   assert p.ships[25]==extra and p.goods_shuffle['seed']=='1234'
   app.switch_section('ships');app.show(0);settle();assert not app.port_list.curselection()and 'hidden'in app.port_summary.cget('text')
   offers=copy.deepcopy(p.original_availability);app.commit();assert p.original_availability==offers and p.shipbuilding_shuffle['blind']
   app.show(25);settle();assert app.port_list.curselection()==(0,)
   app.switch_section('world');app.world.mode.set('Port Information');app.world.change_mode();app.world.selected=0;app.world.details();settle()
   assert all(row['id']>=25 for row in app.world.port_ships.entries)and any(row['id']==25 for row in app.world.port_ships.entries)
   app.switch_section('gameplay');app.gameplay_notebook.select(2);settle();w.links['shipbuilding'].event_generate('<Button-1>');settle();assert app.shipbuilding_shuffle_blind.get()
   app.shipbuilding_shuffle_buttons[2].invoke();settle();assert p.original_availability==p.stock_availability and p.shipbuilding_shuffle['seed']is None and p.ships[25]==extra
   p.set_shipbuilding_shuffle('2026');app.reload_project_view();app.reset_section('gameplay');settle();assert p.original_availability==p.stock_availability and p.ships[25]==extra and p.shipbuilding_shuffle['seed']is None
   assert root.title()=='New Horizons Editor v'+TOOL_VERSION and 'Beta'not in app.build_label.cget('text')
   assert not errors,errors
  report.write_text(json.dumps(dict(status='PASS',version=TOOL_VERSION,checkbox_and_seed_links=True,preview_apply_cancel_restore=True,blind_preview_and_world_and_ship_locations_hidden=True,added_ships_preserved=True,blind_commit_does_not_erase_ports=True,reset_gameplay_restores_previous=True,small_popup_buttons_accessible=True),indent=2),encoding='utf-8')
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
