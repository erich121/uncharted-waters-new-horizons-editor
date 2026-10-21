"""Functional checks using real editor buttons/list clicks; pickers supply test paths.

No ROM is bundled. This module can run inside the packaged Windows executable.
"""
import json,tempfile,os
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from types import SimpleNamespace
from backend import decode,apply_ips
import portraits

def run(Editor,rom_path,report_path):
    rom_path=Path(rom_path).resolve();report_path=Path(report_path).resolve()
    report_path.parent.mkdir(parents=True,exist_ok=True)
    root=tk.Tk();root.attributes('-topmost',True);errors=[]
    def settle():
        # Native Windows mapping can complete after Tk drains its event queue.
        # Allow one display frame, then still require real hit-tested controls.
        ready=tk.BooleanVar(root,value=False)
        root.after(40,lambda:ready.set(True));root.wait_variable(ready)
        root.tk.call('update')
    event_clock=1000
    try:
        app=Editor(root);root.geometry('640x480+3000+3000');settle()
        settle();settle()
        assert app.scroll.canvas.yview()[0]==0.0,'fresh editor must open at the top'
        assert app.heading.winfo_rooty()>=app.scroll.canvas.winfo_rooty(),'startup heading is clipped'
        assert str(app.apply_button.cget('state'))=='disabled','empty editor must not offer Apply'
        def auto_settle():
            ready=tk.BooleanVar(root,value=False);root.after(420,lambda:ready.set(True));root.wait_variable(ready);settle()
        def button(label):
            nonlocal event_clock
            event_clock+=1000
            def walk(w):
                for c in w.winfo_children():
                    if c.winfo_class()=='TButton'and c.cget('text')==label:return c
                    found=walk(c)
                    if found:return found
            b=walk(root);assert b,label;b.winfo_toplevel().attributes('-topmost',True);b.winfo_toplevel().lift();settle()
            assert b.winfo_ismapped(),(label+' is hidden',root.state(),root.geometry(),b.winfo_geometry(),b.master.winfo_geometry())
            x=b.winfo_width()//2;y=b.winfo_height()//2
            sx=b.winfo_rootx()+x;sy=b.winfo_rooty()+y
            hit=root.winfo_containing(sx,sy)
            for _ in range(5):
                if hit==b:break
                settle();sx=b.winfo_rootx()+x;sy=b.winfo_rooty()+y;hit=root.winfo_containing(sx,sy)
            assert hit==b,(label+' is covered or clipped',str(hit),hit.cget('text')if hit and 'text'in hit.keys()else '',b.winfo_geometry(),b.master.winfo_geometry(),app.toolbar_layout)
            b.event_generate('<Enter>',x=x,y=y,rootx=sx,rooty=sy)
            b.event_generate('<ButtonPress-1>',x=x,y=y,rootx=sx,rooty=sy,time=event_clock)
            b.event_generate('<ButtonRelease-1>',x=x,y=y,rootx=sx,rooty=sy,time=event_clock+1);settle()
        def open_fleets():
            if hasattr(app,'fleet_dialog') and app.fleet_dialog.winfo_exists():return
            link=app.world_gameplay_settings.fleet_link
            app.scroll.focus_visible(SimpleNamespace(widget=link));settle()
            assert root.winfo_containing(link.winfo_rootx()+5,link.winfo_rooty()+5)==link
            link.event_generate('<Button-1>');settle()
        def select_ship(i):
            nonlocal event_clock
            event_clock+=1000
            if root.state()=='iconic':
                root.deiconify();root.lift();settle()
            app.list.see(i);settle();box=app.list.bbox(i);assert box
            # Direct event delivery alone bypasses covering widgets. Verify the
            # target is actually exposed, not just populated in memory.
            app.scroll.canvas.xview_moveto(0)
            assert not str(app.list).startswith(str(app.scroll.content)),'ship list must be outside the settings canvas'
            settle()
            assert root.winfo_containing(app.list.winfo_rootx()+10,app.list.winfo_rooty()+box[1]+box[3]//2)==app.list,'ship list is covered or clipped'
            app.list.event_generate('<ButtonPress-1>',x=10,y=box[1]+box[3]//2,time=event_clock)
            app.list.event_generate('<ButtonRelease-1>',x=10,y=box[1]+box[3]//2,time=event_clock+1);settle()
            assert app.selected==i,(i,app.selected)
        def click_port(i,ctrl=False):
            nonlocal event_clock
            event_clock+=1000
            app.port_list.see(i);settle();box=app.port_list.bbox(i);assert box
            pos=(app.port_list.winfo_rootx(),app.port_list.winfo_rooty())
            app.port_list.event_generate('<FocusIn>');settle()
            assert pos==(app.port_list.winfo_rootx(),app.port_list.winfo_rooty()),'list moved on focus'
            canvas=app.scroll.canvas;canvas.xview_moveto(0)
            top=app.port_list.winfo_rooty()-app.scroll.content.winfo_rooty()+box[1]
            total=float(canvas.cget('scrollregion').split()[3]);origin=canvas.yview()[0]*total
            if top<origin:canvas.yview_moveto(max(0,top-4)/total)
            elif top+box[3]>origin+canvas.winfo_height():canvas.yview_moveto(max(0,top+box[3]+4-canvas.winfo_height())/total)
            settle()
            assert root.winfo_containing(app.port_list.winfo_rootx()+20,app.port_list.winfo_rooty()+box[1]+box[3]//2)==app.port_list,'port row is clipped'
            event='<Control-ButtonPress-1>'if ctrl else '<ButtonPress-1>'
            app.port_list.event_generate(event,x=20,y=box[1]+box[3]//2,time=event_clock)
            app.port_list.event_generate('<ButtonRelease-1>',x=20,y=box[1]+box[3]//2,time=event_clock+1,state=4 if ctrl else 0);settle()
        def enter(widget,text):
            if str(widget).startswith(str(app.scroll.content)):app.scroll.focus_visible(SimpleNamespace(widget=widget))
            settle()
            assert widget.winfo_ismapped(),(str(widget),app.notebook.index('current'),app.scroll.canvas.yview(),app.scroll.canvas.winfo_height(),app.scroll.content.winfo_height(),widget.winfo_rooty(),app.scroll.content.winfo_ismapped())
            assert root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)==widget,'input field is covered or clipped'
            widget.delete(0,'end');widget.insert(0,str(text));settle()
        with tempfile.TemporaryDirectory()as f,patch.dict(os.environ,{'LOCALAPPDATA':str(Path(f)/'appdata')}),patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('tkinter.messagebox.showinfo'),patch('tkinter.messagebox.askyesno',return_value=True):
            f=Path(f)
            with patch('tkinter.filedialog.askopenfilename',return_value=str(rom_path)):button('Open stock ROM')
            assert app.entries['hull'].instate(['disabled'])
            app.custom_ships_box.invoke();settle()
            assert all(card.panel.winfo_manager()=='grid' for card in app.spec_sections), 'all specification panels must always be present'
            assert app.search_frame.winfo_ismapped(),'search should be visible above the list'
            enter(app.search_entry,'GALLEON');assert app.ship_rows==[10,19]
            box=app.list.bbox(0);assert box
            app.list.event_generate('<ButtonPress-1>',x=10,y=box[1]+box[3]//2,time=event_clock+10)
            app.list.event_generate('<ButtonRelease-1>',x=10,y=box[1]+box[3]//2,time=event_clock+11);settle()
            assert app.selected==10 and app.vars['name'].get()=='Galleon','filtered row selected wrong ship'
            enter(app.search_entry,'No matching ship');assert app.list.size()==0
            enter(app.search_entry,'');assert app.list.size()==25 and app.search_frame.winfo_ismapped()
            select_ship(0)
            # Optional visual QA of this same window inside the frozen EXE.
            # The external checker captures only the supplied client rectangle.
            ready=os.environ.get('NH_EDITOR_CAPTURE_READY')
            if ready:
                app.notebook.select(1);root.geometry('1100x820+40+40');root.deiconify();root.lift();settle()
                def signal_capture():
                    Path(ready).write_text(json.dumps(dict(rectangle=[root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height()],
                        title=root.title(),ships=app.list.size(),first_ship=app.list.get(0))),encoding='utf-8')
                root.after(300,signal_capture);root.after(2300,root.quit);root.mainloop()
                root.geometry('640x480+3000+3000');settle()
            # Import through the actual PNG button and conversion dialog.
            app.notebook.select(2);settle()
            png=f/'Custom Portrait.png'
            custom=portraits.encode_tiles([(i*7+i//64)%16 for i in range(3072)])
            portraits.image(custom,app.project.rom,3).save(png)
            def import_png(accept=True):
                previous=app.notebook.index('current');app.notebook.select(2);settle()
                app.scroll.focus_visible(SimpleNamespace(widget=app.import_portrait_button));settle()
                root.after(100,lambda:button('Use portrait'if accept else 'Cancel'))
                with patch('tkinter.filedialog.askopenfilename',return_value=str(png)):button('Import PNG')
                assert not errors,errors
                app.notebook.select(previous);settle()
            import_png(False);assert not app.project.portraits
            import_png();assert app.project.portrait_raw(0)==custom
            assert 'Custom portrait'in app.portrait_note.cget('text')
            portrait_project=f/'Portraits.json';portrait_rom=f/'Portraits.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(portrait_project)):button('Save project')
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(portrait_rom)):button('Export ROM and IPS')
            assert portraits.original_raw(portrait_rom.read_bytes(),0)==custom
            app.scroll.focus_visible(SimpleNamespace(widget=app.restore_portrait_button));settle();button('Restore portrait')
            assert not app.project.portraits
            with patch('tkinter.filedialog.askopenfilename',return_value=str(portrait_project)):button('Open project')
            assert app.project.portrait_raw(0)==custom
            button('Restore selected ship');assert not app.project.portraits
            app.notebook.select(3);settle()
            assert app.notebook.tab(3,'text')=='Fixes'and not app.repair_var.get()
            cb=app.repair_check
            def toggle_fix():
                nonlocal event_clock
                event_clock+=1000;settle()
                x=8;y=cb.winfo_height()//2;sx=cb.winfo_rootx()+x;sy=cb.winfo_rooty()+y
                assert root.winfo_containing(sx,sy)==cb,'repair checkbox is clipped'
                cb.event_generate('<Enter>',x=x,y=y)
                cb.event_generate('<ButtonPress-1>',x=x,y=y,time=event_clock)
                cb.event_generate('<ButtonRelease-1>',x=x,y=y,time=event_clock+1);settle()
            toggle_fix();auto_settle();assert app.project.repair_safeguard
            toggle_fix();assert not app.repair_var.get()
            auto_settle();assert not app.project.repair_safeguard
            off_project=f/'Off Project.json';off_rom=f/'Off Export.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(off_project)):button('Save project')
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(off_rom)):button('Export ROM and IPS')
            assert off_rom.read_bytes()==app.project.rom
            toggle_fix();auto_settle();assert app.project.repair_safeguard
            with patch('tkinter.filedialog.askopenfilename',return_value=str(off_project)):button('Open project')
            assert not app.repair_var.get()and not app.project.repair_safeguard
            toggle_fix();auto_settle();assert app.project.repair_safeguard
            app.notebook.select(0);settle()
            assert not app.fleet_var.get()and not app.project.fleet_control
            button('Gameplay');settle()
            # Exercise native modal controls inside the visible desktop bounds.
            root.geometry('1100x820+40+40');root.deiconify();root.lift();settle()
            assert app.section=='gameplay'and len(app.notebook.tabs())==4
            app.gameplay_notebook.select(1);settle()
            cb=app.fleet_check
            app.scroll.focus_visible(SimpleNamespace(widget=cb));settle()
            toggle_fix();auto_settle();assert app.project.fleet_control
            fleet_project=f/'Fleet Project.json';fleet_rom=f/'Fleet Export.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(fleet_project)):button('Save project')
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(fleet_rom)):button('Export ROM and IPS')
            assert not errors and fleet_rom.read_bytes()[0x1dc14:0x1dc18]==bytes.fromhex('22 00 87 e1')
            toggle_fix();auto_settle();assert not app.project.fleet_control
            with patch('tkinter.filedialog.askopenfilename',return_value=str(fleet_project)):button('Open project')
            assert app.fleet_var.get()and app.project.fleet_control
            app.scroll.focus_visible(SimpleNamespace(widget=cb));settle();toggle_fix();auto_settle()
            assert not app.project.fleet_control
            assert not app.difficulty_var.get()and not app.project.fleet_difficulty
            assert str(app.difficulty_settings_button.cget('state'))=='disabled'
            children=root.winfo_children();app.configure_fleets();assert root.winfo_children()==children
            app.gameplay_notebook.select(2);settle()
            cb=app.difficulty_check
            app.scroll.focus_visible(SimpleNamespace(widget=cb));settle();toggle_fix();auto_settle()
            assert app.project.fleet_difficulty and str(app.difficulty_settings_button.cget('state'))=='normal'
            open_fleets()
            assert app.fleet_dialog.winfo_exists()
            app.fleet_nation.current(3);app.fleet_nation.event_generate('<<ComboboxSelected>>');settle()
            widget=app.fleet_choice_widgets[1][0]
            app.fleet_settings_scroll.focus_visible(SimpleNamespace(widget=widget));settle()
            for _ in range(5):
                settle()
                if root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)==widget:break
            assert root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)==widget,(app.fleet_dialog.geometry(),widget.winfo_geometry(),str(root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)))
            widget.current(15);widget.event_generate('<<ComboboxSelected>>');settle()
            assert 'Not used:'not in app.fleet_preview.cget('text')
            assert app.fleet_draft[3][0][1]==14 and 'Frigate'in app.fleet_preview.cget('text')
            widget.current(16);widget.event_generate('<<ComboboxSelected>>');settle()
            escort=app.fleet_choice_widgets[1][1];escort.current(16);escort.event_generate('<<ComboboxSelected>>');settle()
            fourth=app.fleet_choice_widgets[1][3];fourth.current(16);fourth.event_generate('<<ComboboxSelected>>');settle()
            app.fleet_nation.current(0);app.fleet_nation.event_generate('<<ComboboxSelected>>');settle()
            assert app.fleet_draft[0][1][1]==-1 and app.fleet_draft[3][1][1]==15
            app.fleet_dialog.geometry('640x480');settle()
            for row in app.fleet_choice_widgets:
                for widget in row:
                    app.fleet_settings_scroll.focus_visible(SimpleNamespace(widget=widget));settle()
                    assert root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)==widget,'nation selector clipped'
            button('Apply settings')
            assert app.project.fleet_rules[3][1][1]==15 and app.project.fleet_rules[3][3][1]==15
            open_fleets()
            assert app.fleet_preset_box.get()=='Custom settings'
            app.fleet_preset_box.current(0);app.fleet_preset_box.event_generate('<<ComboboxSelected>>');settle()
            assert all(v==-1 for n in app.fleet_draft for r in n for v in r)
            app.fleet_preset_box.current(2);app.fleet_preset_box.event_generate('<<ComboboxSelected>>');settle()
            assert app.fleet_draft[4][2][0]==14 and 'Portugal and Spain'in app.fleet_preset_note.cget('text')
            assert app.fleet_choice_widgets[1][0].current()==16
            button('Apply settings')
            from fleet_difficulty import preset
            assert app.project.fleet_rules==preset('regional')
            open_fleets()
            assert app.fleet_preset_box.get()=='Regional variety'
            app.fleet_preset_box.current(0);app.fleet_preset_box.event_generate('<<ComboboxSelected>>');settle()
            button('Cancel');assert app.project.fleet_rules==preset('regional')
            cb=app.difficulty_check
            assert app.project.fleet_difficulty and app.difficulty_var.get()
            difficulty_project=f/'Difficulty Project.json';difficulty_rom=f/'Difficulty Export.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(difficulty_project)):button('Save project')
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(difficulty_rom)):button('Export ROM and IPS')
            assert difficulty_rom.read_bytes()[0x9199f:0x919a3]==bytes.fromhex('22 00 a0 e1')
            app.scroll.focus_visible(SimpleNamespace(widget=cb));settle();toggle_fix();auto_settle()
            assert not app.project.fleet_difficulty
            assert str(app.difficulty_settings_button.cget('state'))=='disabled'
            children=root.winfo_children();app.configure_fleets();assert root.winfo_children()==children
            with patch('tkinter.filedialog.askopenfilename',return_value=str(difficulty_project)):button('Open project')
            assert app.project.fleet_difficulty and app.difficulty_var.get()
            assert app.project.fleet_rules[3][3][1]==15
            assert str(app.difficulty_settings_button.cget('state'))=='normal'
            app.scroll.focus_visible(SimpleNamespace(widget=cb));settle();toggle_fix();auto_settle()
            assert not app.project.fleet_difficulty and not errors
            from fleet_difficulty import preset
            app.project.fleet_rules=preset()
            button('Ships');settle()
            select_ship(10);app.notebook.select(1);settle()
            click_port(31);enter(app.industry_entry,900);auto_settle()
            assert not errors and app.project.original_availability[10]==dict(ports=[31],industry=900)
            assert app.project.ships[10]['industry']==app.project.original[10]['industry'],'new gate changed used threshold'
            original_project=f/'Original Offers.json';original_rom=f/'Original Offers.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(original_project)):button('Save project')
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(original_rom)):button('Export ROM and IPS')
            click_port(30);auto_settle()
            with patch('tkinter.filedialog.askopenfilename',return_value=str(original_project)):button('Open project')
            assert app.project.original_availability[10]==dict(ports=[31],industry=900)
            assert list(app.port_list.curselection())==[31]and app.industry_var.get()=='900'
            button('Restore selected ship');assert app.project.original_availability[10]==app.project.stock_availability[10]
            app.notebook.select(0);settle()
            select_ship(3)
            for key in ('yard_cargo','factory_cargo'):
                assert str(app.extra_entries[key].cget('state'))=='readonly'
                before=app.extra_vars[key].get();enter(app.extra_entries[key],999)
                assert app.extra_vars[key].get()==before,'calculated cargo accepted input'
            enter(app.extra_entries['capacity'],660)
            assert app.extra_vars['yard_cargo'].get()=='420'and app.extra_vars['factory_cargo'].get()=='480'
            auto_settle();assert not errors
            assert app.project.ships[3]['capacity']-app.project.ships[3]['max_guns']-app.project.ships[3]['max_crew']==420
            expected_factory=app.project.ships[3]['factory_cargo']
            select_ship(10);button('Add ship (up to 10)');assert app.selected==25
            enter(app.entries['name'],'Port Test Ship');enter(app.extra_entries['capacity'],700+int(app.extra_vars['factory_guns'].get())+int(app.extra_vars['factory_crew'].get()))
            app.notebook.select(1);settle();click_port(31)
            assert list(app.port_list.curselection())==[31]
            enter(app.industry_entry,900);auto_settle()
            assert not errors and app.project.ships[25]['ports']==[31]
            import_png();assert app.project.portraits[25]==custom
            click_port(30,True);assert set(app.port_list.curselection())=={30,31},list(app.port_list.curselection())
            click_port(31);assert list(app.port_list.curselection())==[31]
            auto_settle();assert 'Dublin'in app.port_summary.cget('text')
            for _ in range(9):button('Add ship (up to 10)')
            assert len(app.project.ships)==35
            # Test errors through the same buttons the user clicks.
            button('Add ship (up to 10)');assert len(errors)==1 and 'ten'in errors[-1][1];errors.clear()
            select_ship(25);app.notebook.select(1);settle();click_port(0)
            auto_settle();assert not errors and 'cannot reach'in app.status.cget('text')
            click_port(31);auto_settle();assert not errors
            project=f/'UI Project.json';out=f/'UI Export.sfc'
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(project)):button('Save project')
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(out)):button('Export ROM and IPS')
            assert not errors and decode(out.read_bytes())[3]['factory_cargo']==expected_factory
            assert apply_ips(app.project.rom,out.with_suffix('.ips').read_bytes())==out.read_bytes()
            with patch('tkinter.filedialog.askopenfilename',return_value=str(project)):button('Open project')
            assert not errors and app.project.ships[25]['ports']==[31]and app.project.ships[25]['factory_cargo']==700
            assert app.project.portraits[25]==custom
            art_at=int.from_bytes(out.read_bytes()[0x211200:0x211203],'little')-0xC00000
            assert portraits.Decoder(out.read_bytes()).decode(art_at,1536)==custom
            assert app.repair_var.get()and app.project.repair_safeguard
            assert out.read_bytes()[0x8294a:0x8294e]==bytes.fromhex('22 00 8c e1')
            select_ship(3);button('Restore selected ship');assert app.project.ships[3]==app.project.original[3]
            with patch('tkinter.filedialog.asksaveasfilename',return_value=str(out)):button('Export ROM and IPS')
            assert errors and 'already exists'in errors[-1][1];errors.clear()
            select_ship(34);button('Remove added ship');assert len(app.project.ships)==34
            assert app.library.store.root.is_relative_to(f),'workflow test touched the real Library'
            for size in ('1672x940','1920x1080','1440x900','1100x820','640x480'):
                # Restore a minimized Windows test window before hit-testing.
                if size=='1672x940':root.iconify();settle()
                root.deiconify();root.lift();root.geometry(size+'+0+0');settle();select_ship(27);select_ship(28)
                # A long verified-ROM filename can add a toolbar line at640px.
                # Keep >=3 list rows visible; selection/scrolling are hit-tested.
                assert app.list.winfo_height()>=(50 if root.winfo_height()<620 else 100),'ship list has too little height'
                assert root.winfo_containing(app.restore_button.winfo_rootx()+10,app.restore_button.winfo_rooty()+10)==app.restore_button
                app.notebook.select(0);settle()
                assert app.scroll.canvas.yview()[0]==0.0,'new selection must start at the top'
                assert app.heading.winfo_rooty()>=app.scroll.canvas.winfo_rooty(),'selected ship heading is clipped'
                assert app.entries['hull'].winfo_width()<220,'numeric input stretches across the card'
                if size in ('1440x900','1672x940','1920x1080'):
                    assert app.card_columns==2,'desktop ship settings should keep two stable columns'
                    assert app.spec_sections[0].winfo_rootx()<app.spec_sections[1].winfo_rootx()
                    assert app.scroll.canvas.xview()[1]==1.0,'wide settings should not need horizontal scrolling'
                    bottom=app.scroll.canvas.winfo_rooty()+app.scroll.canvas.winfo_height()
                    for card in app.spec_sections:
                        assert card.panel.winfo_rooty()+card.panel.winfo_height()<=bottom,'main specification panel is clipped at desktop size'
                    assert app.entries['name'].winfo_width()>app.entries['hull'].winfo_width()*1.2,'ship-name input should be wider than numeric inputs'
                    assert .185<=app.sidebar.winfo_width()/root.winfo_width()<=.205,'sidebar proportions differ from reference'
                if size=='640x480':assert app.card_columns==1,'small window must stack cards'
                for index,tab_button in enumerate(app.tab_buttons):
                    assert root.winfo_containing(tab_button.winfo_rootx()+tab_button.winfo_width()//2,tab_button.winfo_rooty()+tab_button.winfo_height()//2)==tab_button,('tab is clipped',size,index)
                    button(tab_button.cget('text'));assert app.notebook.index('current')==index
                app.notebook.select(0);settle()
        report=dict(status='PASS',fourth_ship_edit_and_project_roundtrip=True,disabled_fleet_settings_cannot_open=True,preset_selection_updates_immediately_and_reopen_matches=True,nation_dialog_edit_preview_cancel_presets_and_small_window=True,difficulty_checkbox_export_project_roundtrip=True,reference_sidebar_proportions=True,capacity_and_starting_always_present=True,capacity_and_starting_editable=True,icon_tab_buttons_clickable=True,all_six_ship_panels_visible=True,ship_name_input_wider=True,startup_heading_visible=True,new_selection_starts_at_top=True,numeric_input_width_bounded=True,automatic_ship_and_gameplay_edits=True,empty_editor_apply_disabled=True,reference_layout_responsive_cards=True,all_four_ship_tabs_and_gameplay_section_reachable=True,separate_availability_graphics=True,search_visible_above_list=True,filtered_record_selection=True,clearing_search_restores_list=True,window_sizes=['640x480','1100x820','1440x900','1672x940','1920x1080'],portrait_import_cancel_apply_restore_project_export=True,small_window='640x480',fleet_checkbox_export_project_roundtrip=True,original_ports_industry_export_restore_roundtrip=True,repair_checkbox_on_off_roundtrip=True,repair_enabled_export_verified=True,real_button_callbacks=True,real_button_pointer_events=True,all_used_buttons_exposed=True,real_list_clicks=True,ship_name_click_targets_visible=True,
            calculated_cargo_readonly=True,capacity_updates_both_cargo_displays=True,original_capacity_edit=True,new_ship_port_replace_and_multiselect=True,cargo_port_project_roundtrip=True,
            minimized_test_window_restored=True,full_ten_additions=True,restore_remove=True,invalid_capital_and_eleventh_ship_feedback=True,
            rom_and_ips_verified=True,overwrite_refusal=True)
        report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    except Exception as error:
        import traceback
        report_path.write_text(json.dumps(dict(status='FAIL',error=str(error),traceback=traceback.format_exc(),geometry=root.geometry(),window_state=root.state(),panels=[dict(y=c.panel.winfo_rooty(),height=c.panel.winfo_height())for c in app.spec_sections],viewport_bottom=app.scroll.canvas.winfo_rooty()+app.scroll.canvas.winfo_height()),indent=2),encoding='utf-8')
        raise
    finally:root.destroy()
