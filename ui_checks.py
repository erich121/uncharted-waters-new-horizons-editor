"""Functional checks using real editor buttons/list clicks; pickers supply test paths.

No ROM is bundled. This module can run inside the packaged Windows executable.
"""
import json,tempfile,os
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from types import SimpleNamespace
from backend import decode,apply_ips

def run(Editor,rom_path,report_path):
    rom_path=Path(rom_path).resolve();report_path=Path(report_path).resolve()
    report_path.parent.mkdir(parents=True,exist_ok=True)
    root=tk.Tk();errors=[]
    event_clock=1000
    try:
        app=Editor(root);root.geometry('640x480+3000+3000');root.update()
        def button(label):
            nonlocal event_clock
            event_clock+=1000
            def walk(w):
                for c in w.winfo_children():
                    if c.winfo_class()=='TButton'and c.cget('text')==label:return c
                    found=walk(c)
                    if found:return found
            b=walk(root);assert b,label;root.update()
            assert b.winfo_ismapped(),label+' is hidden'
            x=b.winfo_width()//2;y=b.winfo_height()//2
            sx=b.winfo_rootx()+x;sy=b.winfo_rooty()+y
            assert root.winfo_containing(sx,sy)==b,label+' is covered or clipped'
            b.event_generate('<Enter>',x=x,y=y,rootx=sx,rooty=sy)
            b.event_generate('<ButtonPress-1>',x=x,y=y,rootx=sx,rooty=sy,time=event_clock)
            b.event_generate('<ButtonRelease-1>',x=x,y=y,rootx=sx,rooty=sy,time=event_clock+1);root.update()
        def select_ship(i):
            nonlocal event_clock
            event_clock+=1000
            app.list.see(i);root.update();box=app.list.bbox(i);assert box
            # Direct event delivery alone bypasses covering widgets. Verify the
            # target is actually exposed, not just populated in memory.
            app.scroll.canvas.xview_moveto(0)
            assert not str(app.list).startswith(str(app.scroll.content)),'ship list must be outside the settings canvas'
            root.update()
            assert root.winfo_containing(app.list.winfo_rootx()+10,app.list.winfo_rooty()+box[1]+box[3]//2)==app.list,'ship list is covered or clipped'
            app.list.event_generate('<ButtonPress-1>',x=10,y=box[1]+box[3]//2,time=event_clock)
            app.list.event_generate('<ButtonRelease-1>',x=10,y=box[1]+box[3]//2,time=event_clock+1);root.update()
            assert app.selected==i,(i,app.selected)
        def click_port(i,ctrl=False):
            nonlocal event_clock
            event_clock+=1000
            app.port_list.see(i);root.update();box=app.port_list.bbox(i);assert box
            pos=(app.port_list.winfo_rootx(),app.port_list.winfo_rooty())
            app.port_list.event_generate('<FocusIn>');root.update()
            assert pos==(app.port_list.winfo_rootx(),app.port_list.winfo_rooty()),'list moved on focus'
            canvas=app.scroll.canvas;canvas.xview_moveto(0)
            top=app.port_list.winfo_rooty()-app.scroll.content.winfo_rooty()+box[1]
            total=float(canvas.itemcget(app.scroll.window,'height'));origin=canvas.yview()[0]*total
            if top<origin:canvas.yview_moveto(max(0,top-4)/total)
            elif top+box[3]>origin+canvas.winfo_height():canvas.yview_moveto(max(0,top+box[3]+4-canvas.winfo_height())/total)
            root.update()
            assert root.winfo_containing(app.port_list.winfo_rootx()+20,app.port_list.winfo_rooty()+box[1]+box[3]//2)==app.port_list,'port row is clipped'
            event='<Control-ButtonPress-1>'if ctrl else '<ButtonPress-1>'
            app.port_list.event_generate(event,x=20,y=box[1]+box[3]//2,time=event_clock)
            app.port_list.event_generate('<ButtonRelease-1>',x=20,y=box[1]+box[3]//2,time=event_clock+1,state=4 if ctrl else 0);root.update()
        def enter(widget,text):
            if str(widget).startswith(str(app.scroll.content)):app.scroll.focus_visible(SimpleNamespace(widget=widget))
            root.update()
            assert widget.winfo_ismapped()
            assert root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)==widget,'input field is covered or clipped'
            widget.delete(0,'end');widget.insert(0,str(text));root.update()
        with tempfile.TemporaryDirectory()as f,patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('tkinter.messagebox.showinfo'),patch('tkinter.messagebox.askyesno',return_value=True):
            f=Path(f)
            with patch('tkinter.filedialog.askopenfilename',return_value=str(rom_path)):button('Open stock ROM')
            # Optional visual QA of this same window inside the frozen EXE.
            # The external checker captures only the supplied client rectangle.
            ready=os.environ.get('NH_EDITOR_CAPTURE_READY')
            if ready:
                root.geometry('1100x820+40+40');root.deiconify();root.lift();root.update()
                def signal_capture():
                    Path(ready).write_text(json.dumps(dict(rectangle=[root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height()],
                        title=root.title(),ships=app.list.size(),first_ship=app.list.get(0))),encoding='utf-8')
                root.after(300,signal_capture);root.after(2300,root.quit);root.mainloop()
                root.geometry('640x480+3000+3000');root.update()
            select_ship(3)
            for key in ('yard_cargo','factory_cargo'):
                assert str(app.extra_entries[key].cget('state'))=='readonly'
                before=app.extra_vars[key].get();enter(app.extra_entries[key],999)
                assert app.extra_vars[key].get()==before,'calculated cargo accepted input'
            enter(app.extra_entries['capacity'],660)
            assert app.extra_vars['yard_cargo'].get()=='420'and app.extra_vars['factory_cargo'].get()=='480'
            button('Apply ship changes');assert not errors
            assert app.project.ships[3]['capacity']-app.project.ships[3]['max_guns']-app.project.ships[3]['max_crew']==420
            expected_factory=app.project.ships[3]['factory_cargo']
            select_ship(10);button('Add ship (up to 5)');assert app.selected==25
            enter(app.entries['name'],'Port Test Ship');enter(app.extra_entries['capacity'],700+int(app.extra_vars['factory_guns'].get())+int(app.extra_vars['factory_crew'].get()))
            app.notebook.select(1);root.update();click_port(31)
            assert list(app.port_list.curselection())==[31]
            enter(app.industry_entry,900);button('Apply ship changes')
            assert not errors and app.project.ships[25]['ports']==[31]
            click_port(30,True);assert set(app.port_list.curselection())=={30,31},list(app.port_list.curselection())
            click_port(31);assert list(app.port_list.curselection())==[31]
            button('Apply ship changes');assert 'Dublin'in app.port_summary.cget('text')
            for _ in range(4):button('Add ship (up to 5)')
            assert len(app.project.ships)==30
            # Test errors through the same buttons the user clicks.
            button('Add ship (up to 5)');assert len(errors)==1 and 'five'in errors[-1][1];errors.clear()
            select_ship(25);app.notebook.select(1);root.update();click_port(0)
            button('Apply ship changes');assert errors and 'cannot reach'in errors[-1][1];errors.clear()
            click_port(31);button('Apply ship changes');assert not errors
            project=f/'UI Project.json';out=f/'UI Export.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(project)):button('Save project')
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(out)):button('Export ROM and IPS')
            assert not errors and decode(out.read_bytes())[3]['factory_cargo']==expected_factory
            assert apply_ips(app.project.rom,out.with_suffix('.ips').read_bytes())==out.read_bytes()
            with patch('tkinter.filedialog.askopenfilename',return_value=str(project)):button('Open project')
            assert not errors and app.project.ships[25]['ports']==[31]and app.project.ships[25]['factory_cargo']==700
            select_ship(3);button('Restore selected ship');assert app.project.ships[3]==app.project.original[3]
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(out)):button('Export ROM and IPS')
            assert errors and 'already exists'in errors[-1][1];errors.clear()
            select_ship(29);button('Remove added ship');assert len(app.project.ships)==29
        report=dict(status='PASS',small_window='640x480',real_button_callbacks=True,real_button_pointer_events=True,all_used_buttons_exposed=True,real_list_clicks=True,ship_name_click_targets_visible=True,
            calculated_cargo_readonly=True,capacity_updates_both_cargo_displays=True,original_capacity_edit=True,new_ship_port_replace_and_multiselect=True,cargo_port_project_roundtrip=True,
            full_five_additions=True,restore_remove=True,invalid_capital_and_sixth_ship_feedback=True,
            rom_and_ips_verified=True,overwrite_refusal=True)
        report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    finally:root.destroy()
