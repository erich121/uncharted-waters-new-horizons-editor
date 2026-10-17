"""Focused pointer/selection checks for the World browser."""
import json,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from backend import ShipProject


def run(Editor,rom_path,report_path):
    root=tk.Tk();root.attributes('-topmost',True);report_path=Path(report_path);report_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        app=Editor(root);root.geometry('1100x820+0+0');clock=1000
        def settle():
            ready=tk.BooleanVar(value=False);root.after(70,lambda:ready.set(True));root.wait_variable(ready);root.update()
        def click(widget):
            nonlocal clock
            widget.winfo_toplevel().lift();settle();x=widget.winfo_width()//2;y=widget.winfo_height()//2
            assert root.winfo_containing(widget.winfo_rootx()+x,widget.winfo_rooty()+y)==widget,('covered control',str(widget))
            clock+=1000;widget.event_generate('<ButtonPress-1>',x=x,y=y,time=clock);widget.event_generate('<ButtonRelease-1>',x=x,y=y,time=clock+1);settle()
        errors=[]
        with patch('tkinter.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
            settle();click(app.world_nav);assert app.world.list.size()==0
            with patch('tkinter.filedialog.askopenfilename',return_value=str(Path(rom_path).resolve())):click(app.toolbar_buttons[0])
            world=app.world;before=app.project.manifest()
            assert len(world.port_records)==130 and len(world.discovery_records)==98
            # All port lists must agree with the same goods sources and project offers used elsewhere.
            for port in world.port_records:
                world.selected=port['id'];world.details()
                if port['id']>=100:
                    assert not world.port_lists.winfo_manager()
                    continue
                expected_goods={(g['id'],s['economy_required'])for g in world.goods_records for s in g['sources']if s['port']==port['id']}
                expected_ships={(s['id'],o['industry'])for s,o in zip(app.project.ships,app.project.all_offers())if port['id']in o['ports']}
                specialty=port['specialty']
                marked=[r['name'][2:]for r in world.port_goods.entries if r['name'].startswith('★ ')]
                assert marked==([]if specialty=='None'else [specialty])
                expected_items={(item['id'],s['slot'],s['hours'])for item in world.item_records for s in item['sources']if s['port']==port['id']}
                assert {(r['id'],r['slot'],r['hours'])for r in world.port_item_rows}==expected_items
                for panel,expected,metric in [(world.port_goods,expected_goods,'economy'),(world.port_ships,expected_ships,'industry')]:
                    assert {(r['id'],r['required'])for r in panel.entries}==expected
                    assert panel.current==port[metric]and panel.fixed==port['capital']
                    divider=next(i for i,r in enumerate(panel.display_rows)if r['kind']=='starting')
                    assert all(r['ready']for r in panel.display_rows[:divider])
                    assert all(not r['ready']for r in panel.display_rows[divider+1:])
                    assert len(panel.canvas.find_withtag('starting-line'))==1
            world.selected=0;world.details();settle()
            # A changed ship requirement/name must refresh in the port view without reloading the ROM.
            ship_id=world.port_ships.entries[0]['id'];original_ship=app.project.ships[ship_id].copy()
            original_offer=app.project.original_availability[ship_id].copy()
            app.project.update(ship_id,dict(name='Port List Test',industry=0))
            world.refresh();assert any(r['name']=='Port List Test'and r['required']==0 for r in world.port_ships.entries)
            app.project.ships[ship_id]=original_ship;app.project.original_availability[ship_id]=original_offer;world.refresh()
            added=app.project.add_ship();world.refresh()
            assert any(r['id']==added for r in world.port_ships.entries)
            app.project.remove_ship(added);world.refresh()
            assert all(r['id']!=added for r in world.port_ships.entries)
            def choose_mode(name):
                world.mode_box.current(['Ports','Discoveries','Goods','Items'].index(name));world.mode_box.event_generate('<<ComboboxSelected>>');settle()
            def pick_name(name,expected_id):
                nonlocal clock
                world.search.set(name);settle();assert expected_id in world.rows
                box=world.list.bbox(world.rows.index(expected_id));assert box
                x=20;y=box[1]+box[3]//2
                assert root.winfo_containing(world.list.winfo_rootx()+x,world.list.winfo_rooty()+y)==world.list
                clock+=1000;world.list.event_generate('<ButtonPress-1>',x=x,y=y,time=clock);world.list.event_generate('<ButtonRelease-1>',x=x,y=y,time=clock+1);settle()
                assert world.selected==expected_id
            world.region.set('Northern Europe');world.region_box.event_generate('<<ComboboxSelected>>');settle()
            pick_name('Bergen',41);assert len(world.map_canvas.find_withtag('region-port'))==15
            assert all(world.map_canvas.itemcget(item,'fill')=='#ee4035'for item in world.map_canvas.find_withtag('region-port'))
            choose_mode('Discoveries');assert world.list.size()==98
            assert not world.region_box.winfo_ismapped()and not world.port_card.winfo_ismapped()
            for name,i in [('Stonehenge',0),('Moai',97)]:
                pick_name(name,i)
                assert name in world.map_caption.cget('text')
                assert world.discovery_card.winfo_ismapped()and world.discovery_photo is not None
                assert (world.discovery_photo.width(),world.discovery_photo.height())==(128,128)
                assert world.discovery_description.cget('text')
                assert 'Required discovery score:'in world.discovery_summary.cget('text')
                assert len(world.map_canvas.find_withtag('selected-discovery'))==4
                assert not world.map_canvas.find_withtag('selected-port')and not world.map_canvas.find_withtag('region-port')
                item=world.map_canvas.find_withtag('selected-discovery')[0];coords=world.map_canvas.coords(item)
                assert abs((coords[0]+coords[2])/2-world.marker[0])<.01
                assert abs((coords[1]+coords[3])/2-world.marker[1])<.01
            assert 'save'in world.note.cget('text')and not world.ships.cget('text')
            choose_mode('Ports');assert world.selected==41 and world.search.get()=='Bergen'
            assert world.region.get()=='Northern Europe'and len(world.map_canvas.find_withtag('region-port'))==15
            assert world.port_card.winfo_ismapped()and world.region_box.winfo_ismapped()and not world.discovery_card.winfo_ismapped()
            choose_mode('Discoveries');assert world.selected==97 and world.search.get()=='Moai'
            choose_mode('Goods');assert world.list.size()==46 and world.goods_card.winfo_ismapped()
            assert not world.region_box.winfo_ismapped()and not world.discovery_card.winfo_ismapped()
            pick_name('Silk',17)
            assert len(world.good_sources())==1 and len(world.map_canvas.find_withtag('selected-port'))==4
            assert not world.map_canvas.find_withtag('goods-port')
            pick_name('Porcelain',42)
            sources=world.good_sources();assert len(sources)==22
            assert len(world.goods_tree.get_children())==22
            assert len(world.map_canvas.find_withtag('goods-port'))==22
            assert all(world.map_canvas.itemcget(item,'fill')=='#ee4035'for item in world.map_canvas.find_withtag('goods-port'))
            click(world.locked_check);assert not world.include_locked.get()
            assert len(world.good_sources())<22 and all(s['available_at_start']for s in world.good_sources())
            assert len(world.goods_tree.get_children())==len(world.good_sources())
            row=world.goods_tree.get_children()[0];box=world.goods_tree.bbox(row)
            assert box
            world.goods_tree.event_generate('<ButtonPress-1>',x=box[0]+20,y=box[1]+box[3]//2,time=clock+1000)
            world.goods_tree.event_generate('<ButtonRelease-1>',x=box[0]+20,y=box[1]+box[3]//2,time=clock+1001);settle();clock+=2000
            assert world.good_port_selected==int(row)and len(world.map_canvas.find_withtag('selected-port'))==4
            choose_mode('Ports');assert world.selected==41 and world.search.get()=='Bergen'
            choose_mode('Goods');assert world.selected==42 and world.search.get()=='Porcelain'
            choose_mode('Items');assert world.list.size()==61 and not world.locked_check.winfo_ismapped()
            for name,item_id in [('Cat',25),('Pocket Watch',23)]:
                pick_name(name,item_id)
                assert world.item_picture.winfo_ismapped()and world.item_description.cget('text')
                assert (world.item_photo.width(),world.item_photo.height())==(128,128)
                assert len(world.goods_tree.get_children())==len(world.good_sources())
                assert all(world.goods_tree.item(str(s['port']),'values')[1]==s['hours']for s in world.good_sources())
            assert len(world.map_canvas.find_withtag('selected-port'))==4 and not world.map_canvas.find_withtag('item-port')
            choose_mode('Goods');assert not world.item_picture.winfo_ismapped()and world.selected==42
            choose_mode('Items');assert world.selected==23 and world.search.get()=='Pocket Watch'
            sizes=['640x480','1100x820','1440x900','1672x940','1920x1080']
            for size in sizes:
                root.geometry(size+'+0+0');settle()
                map_position=None
                for mode in ['Goods','Items','Ports','Discoveries']:
                    choose_mode(mode);settle()
                    assert world.scroll.canvas.xview()[1]==1.0,(size,mode,'horizontal scroll')
                    assert world.columns.winfo_width()<=world.scroll.canvas.winfo_width()-20,(size,mode,world.columns.winfo_width(),world.scroll.canvas.winfo_width())
                    assert world.map_canvas.winfo_width()<=422 and world.map_canvas.winfo_height()<=212
                    assert world.list.winfo_height()>=100
                    position=(world.map_canvas.winfo_rootx(),world.map_canvas.winfo_rooty(),world.map_canvas.winfo_width(),world.map_canvas.winfo_height())
                    if map_position is None:map_position=position
                    else:assert position==map_position,(size,mode,'map jumped',position,map_position)
                    if mode=='Ports'and world.port_dashboard:
                        for port_id in range(100):
                            world.selected=port_id;world.details();root.update_idletasks()
                            assert world.scroll.content.winfo_reqheight()<=world.scroll.canvas.winfo_height(),(size,port_id,'port dashboard overflows',world.scroll.content.winfo_reqheight(),world.scroll.canvas.winfo_height())
                        world.selected=41;world.details();settle()
                    if mode=='Ports':
                        assert world.port_goods.winfo_ismapped()and world.port_ships.winfo_ismapped()
                        for panel in [world.port_goods,world.port_ships]:
                            assert panel.canvas.winfo_width()<=world.scroll.canvas.winfo_width()-20
                            assert panel.canvas.bbox('all')[3]<=int(panel.canvas.cget('height'))
                            assert panel.canvas.bbox('starting-value')[3]<panel.canvas.coords(panel.canvas.find_withtag('starting-line')[0])[1]
                        # Wheel over both a card and the uncovered right-side viewport.
                        # Being mapped alone does not mean the items are reachable.
                        for surface in [world.scroll.canvas,world.port_goods.canvas,world.scroll.vertical]:
                            canvas=world.scroll.canvas;canvas.yview_moveto(0);settle()
                            if canvas.yview()==(0.0,1.0):
                                assert world.port_items.winfo_rooty()+world.port_items.winfo_height()<=canvas.winfo_rooty()+canvas.winfo_height(),(size,'scroll range omits items',canvas.cget('scrollregion'),world.scroll.content.winfo_reqheight(),world.port_items.winfo_rooty(),world.port_items.winfo_height(),canvas.winfo_rooty(),canvas.winfo_height())
                                continue # The complete port page already fits this viewport.
                            for i in range(100):
                                surface.event_generate('<MouseWheel>',delta=-120);root.update()
                                if canvas.yview()[1]>=.9999:break
                            assert canvas.yview()[0]>0 and canvas.yview()[1]>=.9999,(size,'wheel locked',str(surface),canvas.yview())
                            top=canvas.winfo_rooty();bottom=top+canvas.winfo_height()
                            assert top<=world.port_items.winfo_rooty()and world.port_items.winfo_rooty()+world.port_items.winfo_height()<=bottom,(size,'item list unreachable')
                            surface.event_generate('<MouseWheel>',delta=120);settle()
                            assert canvas.yview()[1]<.9999,(size,'wheel up locked')
                        canvas.yview_moveto(0);settle()
                    else:assert not world.port_goods.winfo_ismapped()and not world.port_ships.winfo_ismapped()
                    if int(size.split('x')[0])>=1440:
                        assert world.detail_panel.winfo_x()>world.map_panel.winfo_x()+world.map_panel.winfo_width()
            assert app.project.manifest()==before and not errors,(errors,'browsing modified project')
            assert app.project.build()[0]==ShipProject(rom_path).build()[0]
        report=dict(status='PASS',stable_world_map_position=True,all_stock_ports_fit_wide_windows=True,world_wheel_over_viewport_cards_and_scrollbar=True,port_items_reachable=True,shop_items=61,item_pictures_and_descriptions=True,item_port_lists_and_hours=True,port_goods_and_ship_requirements=True,all_port_sources_match_catalogue=True,starting_value_dividers=True,project_ship_edits_refresh=True,supply_port_lists_hidden=True,native_discovery_pictures_and_information=True,ports=130,named_discoveries=98,goods=46,goods_sources_and_locked_filter=True,goods_port_selection=True,group_markers_red=True,single_source_crosshair=True,compact_responsive_layout=True,mode_search_and_selection_preserved=True,only_selected_discovery_on_map=True,port_region_markers_restored=True,project_and_export_unchanged=True,window_sizes=sizes)
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
    except Exception as e:
        report_path.write_text(json.dumps(dict(status='FAIL',error=repr(e)),indent=2),encoding='utf-8');raise
    finally:root.destroy()
