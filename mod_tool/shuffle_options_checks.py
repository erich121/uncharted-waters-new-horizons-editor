"""Exercise the seeded Trade and People controls in the real Tk interface."""
import tkinter as tk,json,tempfile
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject

def run(Editor,rom,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  root.geometry('1440x900+0+0');app=Editor(root);p=app.project=ShipProject(rom);app.show(0);app.refresh_list();errors=[]
  def settle():
   done=tk.BooleanVar(root,value=False);root.after(150,lambda:done.set(True));root.wait_variable(done);root.update()
  with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
   app.switch_section('gameplay');app.gameplay_notebook.select(2);settle()
   assert list(app.world_gameplay_sections)==['Fleets','Mates','Items','Trade']
   for mode in ('Shuffle normal goods','Shuffle specialty goods','Shuffle all goods'):
    app.open_goods_seed();settle();before=p.manifest();app.goods_shuffle_seed.set('2026');app.goods_shuffle_mode.set(mode);settle();assert app.goods_shuffle_candidates['edits']
    app.goods_shuffle_buttons[1].invoke();settle();assert p.goods_shuffle['seed']=='2026'and p.goods_edits and not p.custom_goods
    assert 'Changed.'in app.section_buttons['world'].cget('style');assert 'Changed.'not in app.section_buttons['gameplay'].cget('style')
   before=p.manifest();app.open_goods_seed();settle();app.goods_shuffle_seed.set('1234');app.goods_shuffle_buttons[3].invoke();settle();assert before==p.manifest()
   app.open_free_agent_shuffle();settle();app.shuffle_seed.set('2026');app.shuffle_ports_enabled.set(False)
   for v in (app.shuffle_names,app.shuffle_captain_names,app.shuffle_mate_stats,app.shuffle_captain_stats,app.shuffle_mate_skills,app.shuffle_captain_skills):v.set(True)
   settle();app.shuffle_buttons[1].invoke();settle()
   assert all(p.free_agent_shuffle.get(k)for k in ('names','captain_names','mate_stats','captain_stats','mate_skills','captain_skills'))and p.free_agent_shuffle.get('ports')is False
   for section in ('mates','captains'):
    app.switch_section(section);settle();assert 'Changed.'in app.section_buttons[section].cget('style');assert any('*'in app.list.get(i)for i in range(app.list.size()))
   app.switch_section('gameplay');app.gameplay_notebook.select(2);settle()
   for size in ('640x480','1440x900'):
    root.geometry(size+'+0+0');settle();app.open_free_agent_shuffle();settle()
    dialog=app.shuffle_dialog
    for button in app.shuffle_buttons:assert button.winfo_y()+button.winfo_height()<=button.master.winfo_height()
    app.shuffle_buttons[3].invoke();settle()
   with patch('tkinter.messagebox.askyesno',return_value=True):app.reset_section('gameplay')
   settle();assert not p.free_agent_shuffle['enabled']and not p.goods_edits and p.goods_shuffle['seed']is None
   assert 'Changed.'not in app.section_buttons['mates'].cget('style')and 'Changed.'not in app.section_buttons['captains'].cget('style')
   assert not errors,errors
  report.write_text(json.dumps(dict(status='PASS',trade_modes=3,people_options=7,seed='2026',independent_options=True,manual_locks_preserved=True,section_colors=True,cancel_and_reset=True,dialogs_fit=True),indent=2),encoding='utf-8')
 except Exception as e:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(e),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
