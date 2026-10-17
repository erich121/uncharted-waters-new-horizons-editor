"""Verify section navigation, scrollability, About links and no-ROM access."""
import json,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from help_view import REPOSITORY
from backend import TOOL_VERSION

def run(Editor,report):
 root=tk.Tk();root.attributes('-topmost',True);report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
 try:
  app=Editor(root);app.help();dialog=app.help_dialog;root.update()
  titles=['Getting Started','Features & Settings','Compatibility & Troubleshooting','About']
  assert list(app.help_navigation.get(0,'end'))==titles and app.project is None
  app.help();assert app.help_dialog==dialog
  for size in ('640x480','960x660'):
   dialog.geometry(size+'+0+0');root.update()
   for i,title in enumerate(titles):
    nav=app.help_navigation;nav.selection_clear(0,'end');nav.selection_set(i);nav.activate(i);nav.event_generate('<<ListboxSelect>>');root.update()
    text=app.help_text;assert text.get('1.0','1.end')==title and str(text.cget('state'))=='disabled'
    assert text.winfo_width()>200 and text.winfo_height()>150
    assert text.winfo_rootx()+text.winfo_width()<=dialog.winfo_rootx()+dialog.winfo_width()
    before=text.get('1.0','end');text.insert('end','test');assert text.get('1.0','end')==before
    if i in (1,2):text.yview_moveto(1);root.update();assert text.yview()[0]>0
    if i==3:
     assert all(s in before for s in ('New Horizons Editor',f'Version {TOOL_VERSION}','Created and maintained by erich121','GitHub repository','Independent fan-made project. Not affiliated with Koei Tecmo.','UWNHRando','Pillow'))
     assert app.help_repository_button.winfo_ismapped()
     with patch('help_view.webbrowser.open')as browser:
      app.help_repository_button.invoke();browser.assert_called_once_with(REPOSITORY)
    else:assert not app.help_repository_button.winfo_ismapped()
  dialog.destroy();root.update();app.help();root.update();assert app.help_dialog.winfo_exists()and app.help_dialog!=dialog
  app.help_dialog.destroy()
  report.write_text(json.dumps(dict(status='PASS',sections=titles,available_without_rom=True,single_window_reopens=True,read_only_scrollable_content=True,about_text_and_repository=True,window_sizes=['640x480','960x660']),indent=2),encoding='utf-8')
 except Exception as error:
  import traceback
  report.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc()),indent=2),encoding='utf-8');raise
 finally:root.destroy()
