"""Real Tk pointer/selection checks for character browsers, attributes and port shuffle."""
import json,tempfile
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
from backend import ShipProject

def run(Editor,rom_path,report_path):
    root=tk.Tk();root.attributes('-topmost',True);report_path=Path(report_path);report_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        app=Editor(root);errors=[];clock=1000
        def settle():
            done=tk.BooleanVar(root,value=False)
            root.after(60,lambda:done.set(True));root.wait_variable(done);root.update()
        def auto_settle():
            done=tk.BooleanVar(root,value=False);root.after(420,lambda:done.set(True));root.wait_variable(done);settle()
        def click(widget):
            nonlocal clock
            for _ in range(5):
                widget.winfo_toplevel().attributes('-topmost',True);widget.winfo_toplevel().lift();settle();x=widget.winfo_width()//2;y=widget.winfo_height()//2
                if root.winfo_containing(widget.winfo_rootx()+x,widget.winfo_rooty()+y)==widget:break
            assert widget.winfo_ismapped(),'control is hidden'
            assert root.winfo_containing(widget.winfo_rootx()+x,widget.winfo_rooty()+y)==widget,('control is clipped',str(widget),widget.cget('text')if 'text'in widget.keys()else '',widget.winfo_geometry(),widget.winfo_rootx(),widget.winfo_rooty())
            clock+=1000
            widget.event_generate('<Enter>',x=x,y=y)
            widget.event_generate('<ButtonPress-1>',x=x,y=y,time=clock)
            widget.event_generate('<ButtonRelease-1>',x=x,y=y,time=clock+1);settle()
        with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            root.geometry('1100x820+0+0');settle();root.lift();root.focus_force();settle()
            click(app.nav_buttons[1]);assert app.data_type=='mates'and app.list.size()==0
            with patch('tkinter.filedialog.askopenfilename',return_value=str(Path(rom_path).resolve())):
                click(app.toolbar_buttons[0])
            assert not errors,errors
            assert app.data_type=='mates'and app.list.size()==50
            assert app.mate_heading.cget('text')=='Rocco Alemkel'
            assert app.mate_vars['age'].get()=='65'
            assert app.mate_vars['nationality'].get()=='Portugal'
            assert app.character_photo is not None
            # Keep skill rows on one solid card body, below the separate header.
            assert app.skill_content.cget('style')=='Card.TFrame'
            assert app.skills_note.master==app.skill_content
            for check in app.skill_checks.values():
                assert check.master==app.skill_content and check.cget('style')=='Card.TCheckbutton'
                assert ttk.Style(root).lookup('Card.TCheckbutton','background',('active',))=='white'
            click(app.nav_buttons[0]);app.custom_ships_box.invoke();settle();app.vars['hull'].set('31')
            app.search_var.set('BALSA');settle()
            click(app.nav_buttons[1]);assert app.project.ships[0]['hull']==31
            before=app.project.manifest()
            app.search_entry.insert(0,'PILLY');settle()
            assert app.list.size()==1 and app.mate_rows==[79]
            box=app.list.bbox(0);assert box
            clock+=1000;y=box[1]+box[3]//2
            assert root.winfo_containing(app.list.winfo_rootx()+20,app.list.winfo_rooty()+y)==app.list
            app.list.event_generate('<ButtonPress-1>',x=20,y=y,time=clock)
            app.list.event_generate('<ButtonRelease-1>',x=20,y=y,time=clock+1);settle()
            assert app.mate_selected==79
            assert app.mate_vars['starting_port_name'].get()=='Istanbul'
            assert app.mate_vars['navigation_level'].get()=='60'
            assert not app.add_button.winfo_ismapped()and not app.apply_button.winfo_ismapped()
            assert app.project.manifest()==before,'browsing changed project data'
            app.search_var.set('NO SUCH MATE');settle();assert app.list.size()==0
            click(app.nav_buttons[0]);assert app.search_var.get()=='BALSA'and app.list.size()==1
            assert app.vars['hull'].get()=='31'
            click(app.nav_buttons[1]);assert app.search_var.get()=='NO SUCH MATE'
            root.focus_force();app.search_entry.focus_set();settle()
            app.search_entry.event_generate('<Escape>');settle();assert app.list.size()==50
            with tempfile.TemporaryDirectory()as f:
                f=Path(f);project=f/'Project.json';out=f/'Chosen Name.sfc'
                with patch('tkinter.filedialog.asksaveasfilename',return_value=str(project)):
                    click(app.toolbar_buttons[2])
                reopened=ShipProject(rom_path);reopened.load_project(project)
                assert reopened.ships[0]['hull']==31
                with patch('tkinter.filedialog.asksaveasfilename',return_value=str(out)),patch('tkinter.messagebox.showinfo'):
                    click(app.toolbar_buttons[3])
                assert out.read_bytes()==reopened.build()[0]
                with patch('tkinter.filedialog.askopenfilename',return_value=str(project)),patch('tkinter.messagebox.askyesno',return_value=True):
                    click(app.toolbar_buttons[1])
                assert app.data_type=='mates'and app.list.size()==50
            click(app.nav_buttons[2])
            assert app.nav_buttons[2].cget('text')=='Fleet Captains'
            assert app.data_type=='captains'and app.list.size()==64
            assert app.mate_heading.cget('text')=='Simon Sekeira'
            assert 'later be recruited as mates'in app.mate_note.cget('text')
            app.search_var.set('RUSSELL');settle()
            assert app.mate_rows==[38]and app.list.size()==1
            box=app.list.bbox(0);assert box
            clock+=1000;y=box[1]+box[3]//2
            assert root.winfo_containing(app.list.winfo_rootx()+20,app.list.winfo_rooty()+y)==app.list
            app.list.event_generate('<ButtonPress-1>',x=20,y=y,time=clock)
            app.list.event_generate('<ButtonRelease-1>',x=20,y=y,time=clock+1);settle()
            assert app.captain_selected==38 and app.mate_heading.cget('text')=='Victor Russell'
            assert app.mate_vars['battle_level'].get()=='13'
            assert app.mate_vars['nationality'].get()=='England'
            assert app.character_portrait_key[1]==38
            assert app.mate_vars['starting_port_name'].get()=='Fleet-dependent'
            click(app.nav_buttons[1]);assert app.list.size()==50 and app.mate_selected==79,(app.list.size(),app.mate_selected,app.search_var.get(),errors)
            click(app.nav_buttons[0]);assert app.search_var.get()=='BALSA'and app.vars['hull'].get()=='31'
            click(app.nav_buttons[2]);assert app.search_var.get()=='RUSSELL'and app.captain_selected==38
            assert not app.add_button.winfo_ismapped()and not app.apply_button.winfo_ismapped()
            with tempfile.TemporaryDirectory()as f:
                f=Path(f);project=f/'Captains View.json';out=f/'Captain View Export.sfc'
                with patch('tkinter.filedialog.asksaveasfilename',return_value=str(project)):
                    click(app.toolbar_buttons[2])
                reopened=ShipProject(rom_path);reopened.load_project(project)
                assert reopened.ships[0]['hull']==31
                with patch('tkinter.filedialog.asksaveasfilename',return_value=str(out)),patch('tkinter.messagebox.showinfo'):
                    click(app.toolbar_buttons[3])
                assert out.read_bytes()==reopened.build()[0]
            app.search_var.set('HAMID');settle();assert app.mate_rows==[114]
            box=app.list.bbox(0);assert box;clock+=1000;y=box[1]+box[3]//2
            app.list.event_generate('<ButtonPress-1>',x=20,y=y,time=clock)
            app.list.event_generate('<ButtonRelease-1>',x=20,y=y,time=clock+1);settle()
            assert app.captain_selected==114 and app.character_portrait_key[1]==114
            assert app.mate_vars['nationality'].get()=='Pirate'
            app.search_var.set('NO SUCH CAPTAIN');settle();assert app.list.size()==0
            root.focus_force();app.search_entry.focus_set();settle()
            app.search_entry.event_generate('<Escape>');settle();assert app.list.size()==64
            click(app.nav_buttons[1])
            sizes=['640x480','1100x820','1440x900','1672x940','1920x1080']
            for size in sizes:
                root.geometry(size+'+0+0');settle()
                assert app.list.winfo_height()>=(60 if size=='640x480'else 100),(size,app.list.winfo_height())
                assert app.mate_scroll.winfo_ismapped()
                scale=3 if app.mate_scroll.canvas.winfo_width()>=600 else 2
                assert (app.character_photo.width(),app.character_photo.height())==(40*scale,48*scale)
                assert app.mate_portrait_label.winfo_ismapped()
                assert app.mate_columns==(2 if app.mate_scroll.canvas.winfo_width()-32>=780 else 1)
                assert app.mate_cards.winfo_width()<=900,'character panels spread too far across the page'
                assert app.skill_panel.master==app.mate_cards
                assert app.skill_panel.winfo_width()<=app.mate_cards.winfo_width()
                if size in ('1440x900','1672x940','1920x1080'):
                    assert app.skill_panel.grid_info()['column']==1
                    assert app.skill_panel.winfo_width()==app.mate_panels[1].winfo_width()
                    assert app.skill_checks['cartography'].grid_info()['column']==1
                    assert app.skill_panel.winfo_height()<240,'skills card has excess vertical space'
                assert app.mate_scroll.canvas.xview()[1]==1.0,('character details require horizontal scrolling',size,app.mate_scroll.canvas.winfo_width(),app.mate_scroll.content.winfo_reqwidth(),app.mate_cards.winfo_width(),app.character_header.winfo_reqwidth(),app.sailor_actions.winfo_reqwidth(),app.mate_scroll.canvas.xview(),app.mate_scroll.canvas.cget('scrollregion'),app.mate_scroll.canvas.itemcget(app.mate_scroll.window,'width'))
                if size in ('1440x900','1672x940','1920x1080'):
                    assert app.mate_stat_columns==2,'wide attributes should use two compact groups'
                    assert app.mate_panels[1].winfo_height()<300,'attribute panel is too tall'
                click(app.nav_buttons[0]);assert app.ship_settings.winfo_ismapped()
                click(app.nav_buttons[1]);assert app.mate_settings.winfo_ismapped()
                click(app.nav_buttons[2]);assert app.list.size()==64 and app.mate_settings.winfo_ismapped()
                click(app.nav_buttons[1]);assert app.list.size()==50
                # Every attribute can be scrolled into view at the smallest size.
                canvas=app.mate_scroll.canvas;canvas.yview_moveto(1);settle()
                assert canvas.yview()[1]==1.0,(size,canvas.yview())
                canvas.yview_moveto(0);settle()
            # Edit actual attribute fields and drive the shuffle dialog.
            def find(dialog,label):
                for w in dialog.winfo_children():
                    if w.winfo_class()in ('TButton','TCheckbutton')and w.cget('text')==label:return w
                    result=find(w,label)
                    if result:return result
            def edit_value(widget,text):
                if str(widget).startswith(str(app.mate_scroll.content)):
                    app.mate_scroll.focus_visible(SimpleNamespace(widget=widget));settle()
                for _ in range(5):
                    settle()
                    if root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)==widget:break
                hit=root.winfo_containing(widget.winfo_rootx()+widget.winfo_width()//2,widget.winfo_rooty()+widget.winfo_height()//2)
                assert hit==widget,(str(widget),widget.winfo_ismapped(),widget.winfo_geometry(),str(hit))
                widget.delete(0,'end');widget.insert(0,text);settle()
            def select_character(i):
                app.list.see(i);settle();box=app.list.bbox(i);assert box
                nonlocal clock
                clock+=1000;y=box[1]+box[3]//2
                app.list.event_generate('<ButtonPress-1>',x=20,y=y,time=clock)
                app.list.event_generate('<ButtonRelease-1>',x=20,y=y,time=clock+1);settle()
            app.custom_character_box.invoke();settle()
            app.search_var.set('ROCCO');settle();select_character(0)
            for key in ('gunnery','celestial_navigation'):
                assert app.skill_vars[key].get()and str(app.skill_checks[key].cget('state'))=='disabled'
                app.mate_scroll.focus_visible(SimpleNamespace(widget=app.skill_checks[key]));settle();click(app.skill_checks[key])
                assert app.skill_vars[key].get()
            app.mate_scroll.focus_visible(SimpleNamespace(widget=app.skill_checks['negotiation']));settle();click(app.skill_checks['negotiation'])
            auto_settle()
            assert app.project.character_record(69)['skills']==21
            app.mate_scroll.focus_visible(SimpleNamespace(widget=app.sailor_restore_button));settle();click(app.sailor_restore_button)
            assert app.project.character_record(69)['skills']==20
            app.search_var.set('');settle();select_character(app.mate_rows.index(79))
            app.mate_scroll.focus_visible(SimpleNamespace(widget=app.skill_checks['gunnery']));settle();click(app.skill_checks['gunnery'])
            assert app.mate_selected==79
            edit_value(app.mate_field_widgets['leadership'][1],'100')
            auto_settle()
            assert app.project.character_record(79)['leadership']==100 and app.project.character_record(79)['skills']==27
            edit_value(app.mate_field_widgets['leadership'][1],'101')
            auto_settle();assert not errors and '0 to 100'in app.status.cget('text')
            assert app.project.character_record(79)['leadership']==100
            edit_value(app.mate_field_widgets['leadership'][1],'100')
            def open_mates_shuffle():
                app.switch_section('gameplay');app.gameplay_notebook.select(2);settle()
                target=app.world_gameplay_settings.links['mates'] if __import__('character_mods').group_active(app.project.free_agent_shuffle,'mates')else app.world_gameplay_settings.checks['mates']
                app.gameplay_scroll.focus_visible(SimpleNamespace(widget=target));settle();click(target)
            app.mate_scroll.canvas.yview_moveto(0);settle();open_mates_shuffle()
            click(find(app.shuffle_dialog,'Random seed'))
            assert len(app.shuffle_seed.get())==4 and app.shuffle_seed.get().isascii() and app.shuffle_seed.get().isdigit()
            edit_value(app.shuffle_seed_entry,'12x4')
            before=app.project.manifest();click(find(app.shuffle_dialog,'Apply shuffle'))
            assert errors and 'four digits'in errors[-1][1];errors.clear()
            assert app.project.manifest()==before and app.shuffle_dialog.winfo_exists()
            edit_value(app.shuffle_seed_entry,'1234');assert app.shuffle_preview.size()>=40
            normal_map={e['id']:e['port']for e in app.shuffle_candidates[False]}
            edit_value(app.shuffle_seed_entry,'0001')
            assert {e['id']:e['port']for e in app.shuffle_candidates[False]}!=normal_map
            edit_value(app.shuffle_seed_entry,'1234')
            assert {e['id']:e['port']for e in app.shuffle_candidates[False]}==normal_map
            click(find(app.shuffle_dialog,'Blind shuffle — hide preview'))
            assert app.shuffle_blind.get()and app.shuffle_preview.size()==1
            assert {e['id']:e['port']for e in app.shuffle_candidates[True]}!=normal_map
            assert '→'not in app.shuffle_preview.get(0)
            click(find(app.shuffle_dialog,'Apply shuffle'))
            assert app.project.free_agent_shuffle['enabled']and app.project.free_agent_shuffle['blind']
            assert app.project.free_agent_shuffle['seed']=='1234'
            app.switch_section('mates');settle()
            assert app.mate_vars['starting_port_name'].get()=='Hidden (blind shuffle)'
            click(app.nav_buttons[2]);assert app.captain_selected==114
            app.custom_character_box.invoke();settle()
            edit_value(app.mate_field_widgets['courage'][1],'0')
            for key in ('negotiation','gunnery'):
                assert str(app.skill_checks[key].cget('state'))=='normal'
                app.mate_scroll.focus_visible(SimpleNamespace(widget=app.skill_checks[key]));settle();click(app.skill_checks[key])
            auto_settle()
            assert app.project.character_record(114)['courage']==0 and app.project.character_record(114)['skills']==17
            with tempfile.TemporaryDirectory()as f:
                f=Path(f);project=f/'Characters.json';out=f/'Shuffled Campaign.sfc'
                with patch('tkinter.filedialog.asksaveasfilename',return_value=str(project)):click(app.toolbar_buttons[2])
                loaded=ShipProject(rom_path);loaded.load_project(project)
                assert loaded.character_record(79)['leadership']==100 and loaded.character_record(114)['courage']==0
                assert loaded.character_record(114)['skills']==17 and loaded.character_record(79)['skills']==27
                assert loaded.free_agent_shuffle['blind']and loaded.free_agent_shuffle['enabled']
                with patch('tkinter.filedialog.asksaveasfilename',return_value=str(out)),patch('tkinter.messagebox.showinfo'):
                    click(app.toolbar_buttons[3])
                assert out.read_bytes()==loaded.build()[0]
                with patch('tkinter.filedialog.askopenfilename',return_value=str(project)),patch('tkinter.messagebox.askyesno',return_value=True):
                    click(app.toolbar_buttons[1])
                assert app.mate_vars['courage'].get()=='0'
            app.mate_scroll.focus_visible(SimpleNamespace(widget=app.sailor_restore_button));settle();click(app.sailor_restore_button)
            assert app.project.character_record(114)['courage']==52 and app.project.character_record(114)['skills']==20
            assert app.project.character_record(79)['leadership']==100
            click(app.nav_buttons[1]);app.mate_scroll.canvas.yview_moveto(0);settle()
            assert app.mate_vars['starting_port_name'].get()=='Hidden (blind shuffle)'
            open_mates_shuffle();click(find(app.shuffle_dialog,'Restore stock'));app.switch_section('mates');settle()
            assert not app.project.free_agent_shuffle['enabled']and app.mate_vars['starting_port_name'].get()=='Istanbul'
            assert app.project.character_record(79)['leadership']==100
            # The Gameplay entry uses the same shuffle settings without changing the ship browser.
            click(app.nav_buttons[0]);settle();click(app.gameplay_nav)
            app.gameplay_notebook.select(2);settle()
            assert [app.gameplay_notebook.tab(i,'text')for i in range(3)]==['Presets','Battles','World']
            assert list(app.world_gameplay_sections)==['Fleets','Mates','Items','Trade','Ships','Discoveries']
            app.gameplay_scroll.focus_visible(SimpleNamespace(widget=app.world_gameplay_settings.links['mates']));settle()
            assert app.section=='gameplay'and not app.browser_controls.winfo_ismapped()
            assert str(app.world_nav.cget('state'))!='disabled'
            assert len(app.notebook.tabs())==4
            selected=app.selected;ship=app.vars['name'].get();rows=app.list.get(0,'end')
            open_mates_shuffle()
            edit_value(app.shuffle_seed_entry,'5678')
            if app.shuffle_blind.get():click(find(app.shuffle_dialog,'Blind shuffle — hide preview'))
            click(find(app.shuffle_dialog,'Apply shuffle'))
            assert app.data_type=='ships'and app.selected==selected and app.vars['name'].get()==ship
            assert app.list.get(0,'end')==rows
            assert app.project.free_agent_shuffle['enabled']and not app.project.free_agent_shuffle['blind']and app.project.free_agent_shuffle['seed']=='5678'
            assert '5678'in app.gameplay_randomizer_summary.cget('text')
            open_mates_shuffle()
            assert app.shuffle_seed.get()=='5678'
            click(find(app.shuffle_dialog,'Restore stock'))
            assert not __import__('character_mods').group_active(app.project.free_agent_shuffle,'mates')
            click(app.nav_buttons[0]);assert app.browser_controls.winfo_ismapped()and app.section=='ships'
            assert app.selected==selected and app.vars['name'].get()==ship
            assert app.list.cget('activestyle')=='none'
            before=app.project.manifest();click(app.world_nav);settle()
            assert app.section=='world'and app.world.list.size()==130
            assert app.world.map_photo is not None and app.world.marker is not None
            assert app.world.values['economy'].get()=='780'and app.world.values['industry'].get()=='770'
            for name,pid in [('Bergen',41),('Hekla',100),('Forel',129)]:
                app.world.search.set(name);settle();assert app.world.rows==[pid]
                box=app.world.list.bbox(0);assert box
                clock+=1000;y=box[1]+box[3]//2
                app.world.list.event_generate('<ButtonPress-1>',x=20,y=y,time=clock)
                app.world.list.event_generate('<ButtonRelease-1>',x=20,y=y,time=clock+1);settle()
                assert app.world.selected==pid and name in app.world.map_caption.cget('text')
                assert len(app.world.map_canvas.find_withtag('selected-port'))==4
            assert app.world.values['economy'].get()=='Not applicable'
            app.world.region.set('Northern Europe');app.world.region_box.event_generate('<<ComboboxSelected>>');settle()
            expected=[r['id']for r in app.world.records if r['region']=='Northern Europe']
            assert app.world.rows==expected and len(expected)==15
            assert len(app.world.map_canvas.find_withtag('region-port'))==len(expected)
            assert app.world.values['region'].get()=='Northern Europe'
            app.world.search.set('Bergen');settle();assert app.world.rows==[41]
            assert len(app.world.map_canvas.find_withtag('region-port'))==15
            app.world.region.set('Supply ports');app.world.region_box.event_generate('<<ComboboxSelected>>');settle()
            assert len(app.world.rows)==30 and len(app.world.map_canvas.find_withtag('region-port'))==30
            app.world.region.set('All regions');app.world.region_box.event_generate('<<ComboboxSelected>>');settle()
            assert len(app.world.rows)==130 and not app.world.map_canvas.find_withtag('region-port')
            assert app.project.manifest()==before,'World browsing modified project data'
            for size in sizes:
                root.geometry(size+'+0+0');settle()
                assert app.world.map_canvas.winfo_width()<=422 and app.world.map_canvas.winfo_height()<=212
                assert app.world.list.winfo_height()>=(20 if size=='640x480'else 100)
                assert app.world.scroll.canvas.xview()[1]==1.0
            click(app.nav_buttons[0]);assert app.selected==selected
            assert app.list.get(0,'end')==rows
            assert not errors,errors
        report=dict(status='PASS',gameplay_category_tabs=True,compact_map_and_region_markers=True,world_ports_and_rom_map_marker=True,independent_gameplay_and_world_sections=True,gameplay_shuffle_entry_and_shared_settings=True,selector_underline_removed=True,skill_editing_and_add_only_companion_controls=True,version=__import__('backend').TOOL_VERSION,mates=50,story_companions=10,
            editable_attributes_apply_restore_validation=True,port_shuffle_preview_apply_restore=True,
            blind_shuffle_hides_dialog_and_profile=True,four_digit_seed_reproducible_and_modes_distinct=True,character_and_shuffle_project_export_roundtrip=True,
            native_character_portraits=True,nationality_shown=True,responsive_portrait_size=True,
            compact_character_panels=True,paired_attribute_columns=True,no_character_horizontal_scrolling=True,free_agents=40,fleet_captains=64,captain_recruitment_note=True,
            all_three_searches_and_selections_preserved=True,captain_exception_Hamid=True,
            save_export_from_captains=True,real_navigation_and_list_clicks=True,filtered_id_mapping=True,
            separate_searches=True,ship_edits_preserved=True,browsing_no_project_changes=True,
            save_reopen_export_from_mates=True,window_sizes=sizes)
        report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    except Exception as e:
        report_path.write_text(json.dumps(dict(status='FAIL',error=repr(e)),indent=2),encoding='utf-8');raise
    finally:root.destroy()
