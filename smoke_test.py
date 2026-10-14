"""Exercise the editor's widgets, selection, project roundtrip and ROM export."""
import sys,tempfile,json,os
from pathlib import Path
import tkinter as tk
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from app import Editor
from backend import ShipProject,decode
root=tk.Tk();root.withdraw()
try:
    app=Editor(root);app.project=ShipProject(Path(os.environ['NH_STOCK_ROM']));app.selected=13
    app.refresh_list();app.show(13);root.update_idletasks()
    assert app.list.size()==25 and app.vars['max_guns'].get()=='40'
    app.vars['max_guns'].set('60');app.vars['price_gold'].set('2.5')
    app.list.selection_clear(0,'end');app.list.selection_set(3);app.pick()
    assert app.project.ships[13]['max_guns']==60 and app.project.ships[13]['price_gold']==25000
    assert app.selected==3 and app.vars['min_crew'].get()=='50'
    app.vars['min_crew'].set('30');app.commit()
    with tempfile.TemporaryDirectory()as folder:
        folder=Path(folder);project=folder/'UI Mod.json';app.project.save_project(project)
        app.project.export(folder/'UI Mod.sfc')
        result=decode((folder/'UI Mod.sfc').read_bytes())
        assert result[13]['max_guns']==60 and result[3]['min_crew']==30
        app.project.load_project(project);app.show(13)
        app.restore();assert app.project.ships[13]==app.project.original[13]
        app.add();assert app.selected==25 and app.list.size()==26
        app.vars['name'].set('UI New Ship');app.industry_var.set('900')
        app.port_list.selection_clear(0,'end');app.port_list.selection_set(31)
        app.extra_vars['capacity'].set('400');app.extra_vars['factory_guns'].set('40');app.extra_vars['factory_crew'].set('50')
        app.commit();assert app.project.ships[25]['ports']==[31] and app.project.ships[25]['factory_cargo']==310
        app.project.save_project(folder/'Expanded.json');app.project.export(folder/'Expanded.sfc')
        app.project.load_project(folder/'Expanded.json');app.show(25)
        assert app.vars['name'].get()=='UI New Ship' and app.industry_var.get()=='900'
        app.remove();assert app.list.size()==25 and len(app.project.ships)==25
    print(json.dumps(dict(status='PASS',ships_in_list=25,selection_commits_edits=True,
        widget_values_exported=True,project_reload=True,restore_selected=True,new_ship_add_port_fit_export_reload_remove=True)))
finally:root.destroy()
