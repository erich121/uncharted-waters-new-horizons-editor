"""Read-only port information hub and editable port-specific goods availability."""
import tkinter as tk
from tkinter import ttk,messagebox
from ports import PORT_NAMES
from backend import ports
from PIL import Image,ImageTk
from rom_map import port_positions,decode_grid,overview,WIDTH,HEIGHT


def region_names(rom):
    names=[]
    for i in range(13):
        at=742782-512+i*3;ptr=int.from_bytes(rom[at:at+3],'little')-0xc00000
        if not 0<=ptr<len(rom):raise ValueError('Invalid region name pointer.')
        end=rom.find(b'\0',ptr,ptr+64)
        if end<0:raise ValueError('Missing region name terminator.')
        names.append(rom[ptr:end].decode('ascii'))
    return names


def catalogue(rom):
    rows=[];cities=ports(rom);positions=port_positions(rom);regions=region_names(rom)
    for i,name in enumerate(PORT_NAMES):
        row=dict(id=i,name=positions[i]['name'],x=positions[i]['x'],y=positions[i]['y'],kind='Trading port'if i<100 else 'Supply port')
        if i<100:
            town=rom[0x8da7f+i*37:0x8da7f+(i+1)*37]
            row.update(cities[i],economy=int.from_bytes(town[:2],'little'),region=regions[town[33]])
            good=town[26]
            if good==255:row['specialty']='None'
            else:
                from discoveries import read_text
                row['specialty']=read_text(rom,0xb0f07,good).replace('- ','')
        if i>=100:row['region']='Supply ports'
        rows.append(row)
    return rows


class UnlockList(ttk.Frame):
    """Sorted requirements with the starting-value divider between unlocked and locked rows."""
    def __init__(self,parent,title,item_label,metric):
        super().__init__(parent,style='Surface.TFrame',padding=6)
        header=ttk.Frame(self,style='CardHeader.TFrame',padding=5);header.pack(fill='x')
        ttk.Label(header,text=title,style='CardTitle.TLabel').pack(anchor='w')
        self.metric=metric;self.item_label=item_label;self.entries=[];self.current=0;self.fixed=False;self.display_rows=[]
        self.canvas=tk.Canvas(self,width=250,height=50,background='white',highlightthickness=0)
        self.canvas.pack(fill='x');self.canvas.bind('<Configure>',lambda event:self.draw())

    def set_rows(self,entries,current,fixed=False):
        self.entries=sorted(entries,key=lambda row:(row['required'],row['name'].casefold()))
        self.current=current;self.fixed=fixed;self.draw()

    def draw(self):
        c=self.canvas;c.delete('all');width=max(240,c.winfo_width());self.display_rows=[]
        name_x=10;required_x=width*.64;status_x=width-10;y=15
        for x,text,anchor in [(name_x,self.item_label,'w'),(required_x,self.metric,'center'),(status_x,'At start','e')]:
            c.create_text(x,y,text=text,anchor=anchor,fill='#536580',font=('Segoe UI',9,'bold'))
        y+=20;c.create_line(10,y,width-10,y,fill='#d5dfed');y+=8
        divider=False
        def starting_line(y):
            text=f'Starting {self.metric.lower()}: {self.current}'+(' (fixed)'if self.fixed else '')
            c.create_line(10,y+27,width-10,y+27,fill='#2769ad',width=2,tags='starting-line')
            c.create_text(10,y+3,text=text,anchor='nw',fill='#205b9b',font=('Segoe UI',9,'bold'),tags='starting-value')
            self.display_rows.append(dict(kind='starting',value=self.current));return y+35
        for row in self.entries:
            ready=row['required']<=self.current
            if not ready and not divider:y=starting_line(y);divider=True
            item=c.create_text(name_x,y+3,text=row['name'],width=max(90,width*.49-10),anchor='nw',fill='#ef7800'if row.get('changed')else '#162b48',font=('Segoe UI',10))
            height=max(24,c.bbox(item)[3]-y+4)
            c.create_text(required_x,y+height/2,text=str(row['required']),fill='#162b48',font=('Segoe UI',10))
            c.create_text(status_x,y+height/2,text='Ready'if ready else 'Locked',anchor='e',fill='#257447'if ready else '#8c5624',font=('Segoe UI',9))
            c.create_line(10,y+height,width-10,y+height,fill='#edf1f6');y+=height
            self.display_rows.append(dict(row,kind='entry',ready=ready))
        if not divider:y=starting_line(y)
        if not self.entries:
            c.create_text(10,y,text='None listed for this port.',anchor='nw',fill='#536580',font=('Segoe UI',10));y+=28
        c.configure(height=y+5)


class WorldBrowser:
    def __init__(self,editor,ScrollableWindow):
        self.editor=editor;self.view='Ports';self.mode=tk.StringVar(value='Port Information');self.selections={'Economy':0,'Ports':0,'Discoveries':0,'Goods':0,'Items':0};self.searches={'Economy':'','Ports':'','Discoveries':'','Goods':'','Items':''};self.port_records=[];self.discovery_records=[];self.goods_records=[];self.item_records=[];self.good_port_selected=None;self.selected=0;self.rom=None;self.records=[];self.rows=[];self.map_image=None;self.map_photo=None;self.map_scaled_size=None;self.marker=None
        self.browser=ttk.Frame(editor.sidebar,style='SidebarContent.TFrame')
        self.mode_box=ttk.Combobox(self.browser,textvariable=self.mode,values=['Port Information','Discoveries','Goods','Items','Economy'],state='readonly',width=15)
        self.mode_box.pack(fill='x',pady=(0,6));self.mode_box.bind('<<ComboboxSelected>>',self.change_mode)
        self.search=tk.StringVar();entry=ttk.Entry(self.browser,textvariable=self.search);entry.pack(fill='x',pady=(0,6));self.search_entry=entry
        body=ttk.Frame(self.browser);body.pack(fill='both',expand=True)
        self.list=tk.Listbox(body,exportselection=False,activestyle='none',font=('Segoe UI',10),background='white',foreground='black',selectbackground='#205b9b',selectforeground='white',width=1,height=8)
        self.list.pack(side='left',fill='both',expand=True)
        scrollbar=ttk.Scrollbar(body,command=self.list.yview);scrollbar.pack(side='right',fill='y');self.list.configure(yscrollcommand=scrollbar.set)
        self.list.bind('<<ListboxSelect>>',self.pick);self.search.trace_add('write',lambda *args:self.filter())
        self.settings=ttk.Frame(editor.settings_area);self.scroll=ScrollableWindow(self.settings,fit_width=True,natural_height=True)
        page=ttk.Frame(self.scroll.content,padding=(16,8));page.pack(fill='both',expand=True)
        self.heading=ttk.Label(page,text='World',font=('Segoe UI',18,'bold'));self.heading.pack(anchor='w',pady=(0,4))
        self.intro=tk.Label(page,text='Starting values from the original ROM • Read-only',foreground='#6e7f98',background='#f5f7fb',font=('Segoe UI',10),height=2,anchor='nw',justify='left',wraplength=300);self.intro.pack(anchor='w',pady=(0,2))
        self.edit_controls=ttk.Frame(page,height=30);self.edit_controls.pack(fill='x');self.edit_controls.pack_propagate(False)
        self.columns=ttk.Frame(page);self.columns.pack(anchor='center',fill='x')
        self.map_panel=ttk.Frame(self.columns);self.detail_panel=ttk.Frame(self.columns)
        self.map_panel.grid(row=0,column=0,sticky='new');self.detail_panel.grid(row=0,column=1,sticky='new',padx=(20,0))
        self.layout_key=None
        self.map_toolbar=ttk.Frame(self.map_panel,height=70);self.map_toolbar.pack(fill='x');self.map_toolbar.pack_propagate(False)
        self.map_scope=ttk.Label(self.map_toolbar,text='',foreground='#6e7f98',wraplength=280)
        region_bar=ttk.Frame(self.map_toolbar);self.region_bar=region_bar;region_bar.pack(anchor='w',pady=(0,10))
        ttk.Label(region_bar,text='Region').pack(anchor='w')
        self.region=tk.StringVar(value='All regions')
        self.last_region='All regions'
        self.region_box=ttk.Combobox(region_bar,textvariable=self.region,values=['All regions'],state='readonly',width=23)
        self.region_box.pack(anchor='w',pady=(4,0));self.region_box.bind('<<ComboboxSelected>>',self.change_region)
        self.map_caption=tk.Label(self.map_panel,text='ROM world map',font=('Segoe UI',11,'bold'),height=2,wraplength=300,anchor='w',justify='left',background='#f5f7fb',foreground='#17243d');self.map_caption.pack(anchor='w',pady=(0,6))
        self.map_canvas=tk.Canvas(self.map_panel,width=420,height=210,background='#205374',highlightthickness=1,highlightbackground='#d5dfed');self.map_canvas.pack(anchor='w',pady=(0,6))
        self.map_canvas.bind('<Configure>',lambda event:self.draw_map())
        ttk.Label(self.map_panel,text='Map and locations decoded from your ROM.',wraplength=300,foreground='#6e7f98').pack(anchor='w',pady=(0,12))
        card=ttk.Frame(self.map_panel,style='Surface.TFrame',padding=8);self.port_card=card;card.pack(anchor='w',fill='x')
        header=ttk.Frame(card,style='CardHeader.TFrame',padding=8);header.pack(fill='x');ttk.Label(header,text='Port information',style='CardTitle.TLabel').pack(anchor='w')
        content=ttk.Frame(card,style='Card.TFrame',padding=12);content.pack(fill='x');self.values={};self.value_labels={}
        for i,(key,label) in enumerate((('kind','Port type'),('region','Region'),('capital','Capital'),('economy','Starting economy'),('industry','Starting industry'),('specialty','Trade specialty'))):
            ttk.Label(content,text=label,style='Card.TLabel').grid(row=i,column=0,sticky='w',padx=(0,16),pady=3)
            value=tk.StringVar(value='—');self.values[key]=value
            widget=ttk.Label(content,textvariable=value,style='Card.TLabel',wraplength=170);widget.grid(row=i,column=1,sticky='w',pady=3);self.value_labels[key]=widget
        self.port_lists=ttk.Frame(self.detail_panel)
        self.port_goods=UnlockList(self.port_lists,'Goods sold — ★ Specialty','Good','Economy')
        self.port_ships=UnlockList(self.port_lists,'Ships built — project settings','Ship','Industry')
        self.port_items=ttk.Frame(self.port_lists,style='Surface.TFrame',padding=6)
        item_header=ttk.Frame(self.port_items,style='CardHeader.TFrame',padding=5);item_header.pack(fill='x')
        ttk.Label(item_header,text='Items sold',style='CardTitle.TLabel').pack(anchor='w')
        self.port_items_body=ttk.Frame(self.port_items,style='Card.TFrame',padding=8);self.port_items_body.pack(fill='x')
        self.port_item_rows=[];self.port_dashboard=False
        self.discovery_card=ttk.Frame(self.detail_panel,style='Surface.TFrame',padding=8)
        discovery_header=ttk.Frame(self.discovery_card,style='CardHeader.TFrame',padding=8);discovery_header.pack(fill='x')
        ttk.Label(discovery_header,text='Discovery information',style='CardTitle.TLabel').pack(anchor='w')
        discovery_body=ttk.Frame(self.discovery_card,style='Card.TFrame',padding=12);discovery_body.pack(fill='x')
        self.discovery_picture=ttk.Label(discovery_body,style='Card.TLabel');self.discovery_picture.pack(side='left',anchor='n',padx=(0,16),pady=(0,8))
        self.discovery_photo=None;self.discovery_picture_key=None
        self.discovery_summary=ttk.Label(discovery_body,style='Card.TLabel',wraplength=260);self.discovery_summary.pack(anchor='w',pady=(0,8))
        self.discovery_description=ttk.Label(discovery_body,style='Card.TLabel',wraplength=260);self.discovery_description.pack(anchor='w',pady=(0,8))
        self.discovery_requirement=ttk.Label(discovery_body,text='Finding it depends on Intuition, Luck and village friendship. No fixed navigation level is checked in this reveal calculation.',style='Hint.Card.TLabel',wraplength=260);self.discovery_requirement.pack(anchor='w')
        self.goods_controls=ttk.Frame(self.map_toolbar)
        self.include_locked=tk.BooleanVar(value=True)
        self.locked_check=ttk.Checkbutton(self.goods_controls,text='Include locked sources',variable=self.include_locked,command=self.refresh_goods)
        self.locked_check.pack(anchor='w')
        self.goods_card=ttk.Frame(self.detail_panel,style='Surface.TFrame',padding=8)
        goods_header=ttk.Frame(self.goods_card,style='CardHeader.TFrame',padding=8);goods_header.pack(fill='x')
        self.goods_title=ttk.Label(goods_header,text='Selling ports',style='CardTitle.TLabel');self.goods_title.pack(anchor='w')
        goods_body=ttk.Frame(self.goods_card,style='Card.TFrame',padding=12);goods_body.pack(fill='both',expand=True)
        self.goods_summary=ttk.Label(goods_body,style='Card.TLabel',wraplength=300);self.goods_summary.pack(anchor='w',pady=(0,8))
        self.item_profile=ttk.Frame(goods_body,style='Card.TFrame')
        self.item_meta=ttk.Label(self.item_profile,style='Card.TLabel',justify='left');self.item_meta.pack(side='left',padx=12)
        self.item_picture=ttk.Label(self.item_profile,style='Card.TLabel');self.item_photo=None;self.item_picture_key=None
        self.item_description=ttk.Label(goods_body,style='Hint.Card.TLabel',wraplength=300);self.item_description.pack(anchor='w',pady=(0,8))
        sellers=ttk.Frame(goods_body,style='Card.TFrame');sellers.pack(fill='both',expand=True)
        self.goods_tree=ttk.Treeview(sellers,columns=('port','economy','start'),show='headings',height=8,selectmode='browse')
        for key,title,width in [('port','Port',130),('economy','Economy',70),('start','At start',75)]:
            self.goods_tree.heading(key,text=title);self.goods_tree.column(key,width=width,minwidth=45,stretch=True)
        self.goods_tree.pack(side='left',fill='both',expand=True)
        goods_scroll=ttk.Scrollbar(sellers,command=self.goods_tree.yview);goods_scroll.pack(side='right',fill='y');self.goods_tree.configure(yscrollcommand=goods_scroll.set)
        self.goods_tree.bind('<<TreeviewSelect>>',self.pick_selling_port)
        self.goods_tree.tag_configure('changed',foreground='#ef7800',background='#fff5e9')
        self.custom_goods_var=tk.BooleanVar(value=False)
        self.goods_enable_box=ttk.Checkbutton(self.edit_controls,text='Use custom values',variable=self.custom_goods_var,command=self.toggle_custom_goods,state='disabled')
        self.goods_edit_frame=ttk.Frame(goods_body,style='Card.TFrame',padding=(0,10))
        self.goods_edit_loading=False;self.goods_edit_timer=None;self.goods_pending=None;self.goods_signature=None
        self.goods_port=tk.StringVar();self.goods_gate=tk.StringVar(value='0')
        ttk.Label(self.goods_edit_frame,text='Port',style='Card.TLabel').grid(row=0,column=0,sticky='w')
        self.goods_port_box=ttk.Combobox(self.goods_edit_frame,textvariable=self.goods_port,state='readonly',width=23)
        self.goods_port_box.grid(row=0,column=1,sticky='ew',padx=(8,0))
        self.goods_port_box.bind('<<ComboboxSelected>>',self.select_edit_port)
        ttk.Label(self.goods_edit_frame,text='Required economy',style='Card.TLabel').grid(row=1,column=0,sticky='w',pady=8)
        self.goods_gate_box=ttk.Spinbox(self.goods_edit_frame,textvariable=self.goods_gate,from_=0,to=2550,increment=10,width=8)
        self.goods_gate_box.grid(row=1,column=1,sticky='w',padx=(8,0))
        buttons=ttk.Frame(self.goods_edit_frame,style='Card.TFrame');buttons.grid(row=2,column=0,columnspan=2,sticky='w')
        self.add_good_button=ttk.Button(buttons,text='Add port',command=self.add_good_port);self.add_good_button.pack(side='left')
        self.remove_good_button=ttk.Button(buttons,text='Remove port',command=self.remove_good_port);self.remove_good_button.pack(side='left',padx=5)
        self.restore_good_button=ttk.Button(self.goods_edit_frame,text='Restore this good',command=self.restore_good);self.restore_good_button.grid(row=3,column=0,columnspan=2,sticky='w',pady=(8,0))
        self.goods_edit_hint=ttk.Label(self.goods_edit_frame,text='Economy changes apply automatically. Add ports with free slots. Prices use stock references. Test with a new game.',style='Hint.Card.TLabel',wraplength=300)
        self.goods_edit_hint.grid(row=4,column=0,columnspan=2,sticky='w',pady=(8,0))
        self.goods_edit_frame.columnconfigure(1,weight=1)
        self.goods_gate.trace_add('write',self.schedule_goods_gate)
        self.note=ttk.Label(self.detail_panel,text='Open a stock USA ROM to view port information.',wraplength=320,foreground='#6e7f98');self.note.pack(anchor='w',pady=4)
        self.ships=ttk.Label(self.detail_panel,text='',wraplength=320);self.ships.pack_forget()
        from economy_view import EconomyPanel
        self.economy_panel=EconomyPanel(self)
        from item_shop_view import ItemShopPanel
        self.item_editor=ItemShopPanel(self,goods_body)
        self.edit_controls.configure(height=max(w.winfo_reqheight()for w in (self.goods_enable_box,self.economy_panel.enable_box,self.item_editor.enable_box))+2)
        self.scroll.canvas.bind('<Configure>',lambda event:self.wrap(event.width),add='+')
        self.scroll.content.bind('<Configure>',lambda event:self.schedule_discovery_fit(),add='+')
    def wrap(self,width):
        available=max(260,width-32);dashboard=self.view=='Ports'and available>=960
        discovery=self.view=='Discoveries'
        wide=available>=820 and not discovery
        bounded=min(900,available)if discovery else min(1450,available)if dashboard else min(1100,available)if wide else min(520,available)
        map_width=min(bounded,640)if discovery else 300 if available>=960 else 420 if wide else min(420,bounded)
        detail_width=bounded-map_width-20 if wide else bounded
        self.map_toolbar.configure(height=1 if discovery else 70)
        self.map_caption.configure(height=1 if discovery else 2)
        self.intro.configure(height=1 if discovery else 2)
        self.edit_controls.configure(height=1 if discovery else max(w.winfo_reqheight()for w in (self.goods_enable_box,self.economy_panel.enable_box,self.item_editor.enable_box))+2)
        key=(bounded,wide,dashboard,self.view)
        changed_layout=key!=self.layout_key
        if changed_layout:
            self.layout_key=key;self.port_dashboard=dashboard
            self.columns.grid_anchor('n'if discovery else 'nw')
            self.columns.columnconfigure(0,minsize=map_width if wide else bounded)
            self.columns.columnconfigure(1,minsize=detail_width if wide else 0)
            self.detail_panel.grid_forget()
            self.detail_panel.grid(row=0 if wide else 1,column=1 if wide else 0,sticky='new',padx=(20,0)if wide else 0,pady=(0,0)if wide else (12,0))
            self.layout_port_lists()
        self.map_canvas.pack_configure(anchor='center'if discovery else 'w')
        self.map_caption.pack_configure(anchor='center'if discovery else 'w')
        self.schedule_discovery_fit()
        self.map_caption.configure(wraplength=map_width)
        self.intro.configure(wraplength=bounded)
        if not discovery or changed_layout:self.map_canvas.configure(width=max(200,map_width-2))
        text_width=max(180,detail_width-48-(144 if discovery else 0))
        for label in (self.discovery_summary,self.discovery_description,self.discovery_requirement,self.goods_summary,self.item_description):label.configure(wraplength=text_width)
        if hasattr(self,'economy_panel'):
            for label in self.economy_panel.winfo_children():
                if label.winfo_class()=='TLabel':label.configure(wraplength=max(180,text_width-24))
        self.note.configure(wraplength=max(200,detail_width));self.ships.configure(wraplength=max(200,detail_width))

    def schedule_discovery_fit(self):
        if self.view!='Discoveries':return
        if getattr(self,'discovery_fit_timer',None) is not None:self.editor.root.after_cancel(self.discovery_fit_timer)
        self.discovery_fit_timer=self.editor.root.after(30,self.fit_discovery)

    def fit_discovery(self):
        self.discovery_fit_timer=None
        if self.view!='Discoveries' or not self.settings.winfo_ismapped():return
        canvas=self.map_canvas
        if (canvas.winfo_height()!=canvas.winfo_reqheight() or
                self.scroll.content.winfo_height()!=self.scroll.content.winfo_reqheight()):
            self.schedule_discovery_fit()
            return
        # Requested canvas height changes before its parents have propagated
        # their new requests. Mixing those values makes the map oscillate.
        # Measure both from the same completed geometry pass instead.
        other=max(0,self.scroll.content.winfo_height()-canvas.winfo_height())
        height=max(80,min(450,self.scroll.canvas.winfo_height()-other-16))
        width=max(160,min(900,self.scroll.canvas.winfo_width()-34,height*2-2))
        if abs(int(canvas.cget('width'))-width)>2:
            canvas.configure(width=width)
            self.schedule_discovery_fit()

    def layout_port_lists(self):
        for widget in (self.port_goods,self.port_ships,self.port_items):widget.grid_forget()
        self.port_lists.columnconfigure(0,weight=1,minsize=0)
        self.port_lists.columnconfigure(1,weight=1 if self.port_dashboard else 0,minsize=0)
        if self.port_dashboard:
            self.port_goods.grid(row=0,column=0,sticky='new',padx=(0,12),pady=(0,12))
            self.port_items.grid(row=1,column=0,sticky='new',padx=(0,12))
            self.port_ships.grid(row=0,column=1,rowspan=2,sticky='new')
        else:
            self.port_goods.grid(row=0,column=0,sticky='ew',pady=(0,12))
            self.port_ships.grid(row=1,column=0,sticky='ew',pady=(0,12))
            self.port_items.grid(row=2,column=0,sticky='ew')

    def hide(self):self.browser.pack_forget();self.settings.pack_forget()
    def show(self):
        self.browser.pack(fill='both',expand=True);self.settings.pack(fill='both',expand=True);self.editor.scroll=self.scroll;self.refresh()
    def refresh(self):
        project=self.editor.project
        if project and self.rom is not project.rom:
            self.rom=project.rom;self.port_records=catalogue(project.rom);self.stock_port_records=[dict(row)for row in self.port_records]
            from discoveries import catalogue as discovery_catalogue
            self.discovery_records=__import__('discovery_content').rows(project)
            from goods import catalogue as goods_catalogue
            self.goods_records=goods_catalogue(project.rom);self.stock_goods_records=self.goods_records
            from items import catalogue as item_catalogue
            self.item_records=item_catalogue(project.rom)
            self.records=self.record_sets()[self.view]
            self.region_box.configure(values=['All regions']+region_names(project.rom)+['Supply ports']);self.filter();self.map_image=overview(decode_grid(project.rom));self.map_scaled_size=None
        if project:
            signature=(id(project),repr(project.goods_edits),repr(project.goods_shuffle),repr(project.economy_edits),project.custom_economy,project.custom_goods,repr(project.item_edits),repr(project.discovery_entries),project.discovery_rewrites,project.discovery_easy,repr(project.item_price_edits))
            if signature!=self.goods_signature:
                from item_shops import catalogue as edited_items
                self.item_records=edited_items(project.rom,project.item_edits)
                from items import catalogue as stock_items
                self.stock_item_records=stock_items(project.rom)
                from item_prices import price
                for row in self.item_records:row['price_gold']=price(project,row['id'])
                self.changed_items={r['id']for r,original in zip(self.item_records,self.stock_item_records)if r['sources']!=original['sources']or r['price_gold']!=original['price_gold']}
                from trade_goods import catalogue as edited_catalogue,offers
                self.goods_draft_records=edited_catalogue(project.economy_rom(),project.goods_edits)
                self.goods_records=edited_catalogue(project.economy_rom(),project.goods_edits)
                from economy import values as economy_values
                for row in economy_values(project.rom,project.economy_edits):
                    self.port_records[row['port']].update(economy=row['economy'],industry=row['industry'])
                self.changed_economies={r['port']for r in project.economy_edits}
                current=offers(project.rom,project.goods_edits)
                names={g['id']:g['name']for g in self.goods_records}
                for port,row in enumerate(current):
                    specialty=next((o for o in row if o['kind']=='Specialty'),None)
                    self.port_records[port]['specialty']=names[specialty['good']]if specialty else 'None'
                self.changed_goods={g['id']for g,stock in zip(self.goods_records,self.stock_goods_records)if g['sources']!=stock['sources']}
                self.goods_signature=signature;self.records=self.record_sets()[self.view];self.filter()
        self.intro.configure(text='Project item shops • Selling ports and offer times'if self.view=='Items'else 'Edit starting goods economy and shipbuilding industry • Single port or whole region'if self.view=='Economy'else 'Project goods availability • Edit selling ports and economy requirements'if self.view=='Goods'else 'Current project overview • Read-only'if self.view=='Ports'else 'Current project discovery pool • Edit content in the Discoveries section')
        self.details()
    def filter(self):
        self.list.delete(0,'end');self.rows=[]
        discovery_changes=__import__('discovery_content').changed_slots(self.editor.project)if self.view=='Discoveries'and self.editor.project else set()
        for row in self.records:
            if (self.view not in ('Ports','Economy')or self.region.get()=='All regions'or row['region']==self.region.get())and self.search.get().strip().casefold()in row['name'].casefold():
                self.rows.append(row['id']);changed=(self.view=='Discoveries'and row['id']in discovery_changes)or(self.view=='Items'and row['id']in getattr(self,'changed_items',set()))or(self.view=='Goods'and row['id']in getattr(self,'changed_goods',set()))or(self.view in ('Ports','Economy')and row['id']in getattr(self,'changed_economies',set()))
                self.list.insert('end',f"{row['id']+1:03d}  {row['name']}"+('  *'if changed else ''))
                if changed:self.list.itemconfigure('end',foreground='#ef7800',background='#fff5e9',selectforeground='#ef7800',selectbackground='#ffe2c0')
        if self.selected in self.rows:
            index=self.rows.index(self.selected);self.list.selection_set(index);self.list.activate(index);self.list.selection_anchor(index)
    def record_sets(self):
        if self.editor.project:self.discovery_records=__import__('discovery_content').rows(self.editor.project)
        return {'Economy':self.port_records[:100],'Ports':self.port_records,'Discoveries':self.discovery_records,'Goods':getattr(self,'goods_draft_records',self.goods_records),'Items':self.item_records}

    def change_mode(self,event=None):
        self.selections[self.view]=self.selected;self.searches[self.view]=self.search.get()
        if not self.commit_edits():
            self.mode.set('Port Information'if self.view=='Ports'else self.view);return
        self.view='Ports'if self.mode.get()=='Port Information'else self.mode.get();self.records=self.record_sets()[self.view];self.good_port_selected=None
        if self.view=='Economy'and self.region.get()=='Supply ports':self.region.set('All regions')
        self.last_region=self.region.get()
        if self.editor.project:self.region_box.configure(values=['All regions']+region_names(self.editor.project.rom)+(['Supply ports']if self.view=='Ports'else []))
        self.selected=self.selections[self.view];self.search.set(self.searches[self.view]);self.filter()
        self.goods_enable_box.pack_forget();self.economy_panel.enable_box.pack_forget();self.item_editor.enable_box.pack_forget()
        if self.view=='Economy':self.economy_panel.enable_box.pack(anchor='w')
        elif self.view=='Items':self.item_editor.enable_box.pack(anchor='w')
        for widget in (self.region_bar,self.goods_controls,self.port_card,self.discovery_card,self.goods_card,self.port_lists,self.map_scope,self.economy_panel):widget.pack_forget()
        if self.view in ('Ports','Economy'):
            self.region_bar.pack(anchor='w',pady=(0,10));self.port_card.pack(anchor='w',fill='x')
            if self.view=='Economy':self.economy_panel.pack(before=self.note,fill='both',expand=True)
        elif self.view=='Discoveries':
            self.map_scope.configure(text='Selected discovery')
            self.discovery_card.pack(before=self.note,anchor='w',fill='x')
        else:
            if self.view=='Goods':self.goods_controls.pack(anchor='w',pady=8)
            else:
                self.map_scope.configure(text='Item shop locations');self.map_scope.pack(anchor='w',pady=8)
            self.goods_card.pack(before=self.note,anchor='w',fill='both',expand=True)
        self.wrap(self.scroll.canvas.winfo_width());self.details();self.scroll.canvas.yview_moveto(0);self.editor.update_status()

    def change_region(self,event=None):
        if not self.commit_edits():self.region.set(self.last_region);return
        self.last_region=self.region.get()
        self.search.set('');self.filter()
        if self.rows and self.selected not in self.rows:
            self.selected=self.rows[0];self.filter()
        self.details();self.scroll.canvas.yview_moveto(0)

    def pick(self,event=None):
        selection=self.list.curselection()
        if not selection:return
        selected=self.rows[selection[0]]
        if not self.commit_edits():self.filter();return
        self.selected=selected;self.good_port_selected=None
        if selected in self.rows:
            index=self.rows.index(selected);self.list.selection_clear(0,'end');self.list.selection_set(index);self.list.activate(index);self.list.selection_anchor(index)
        self.details();self.scroll.canvas.yview_moveto(0)
    def details(self):
        if not self.records:return
        row=next(row for row in self.records if row['id']==self.selected);self.heading.configure(text=row['name']);self.draw_map()
        if self.view in ('Goods','Items'):
            self.refresh_goods();return
        if self.view=='Discoveries':
            from discoveries import picture
            key=(id(self.rom),row['id'],repr(self.editor.project.discovery_entries.get(row['id'])))
            if key!=self.discovery_picture_key:
                self.discovery_photo=ImageTk.PhotoImage(__import__('discovery_content').picture(self.editor.project.discovery_entries[row['id']])if row['id']in self.editor.project.discovery_entries else picture(self.rom,row['id']),master=self.discovery_picture);self.discovery_picture.configure(image=self.discovery_photo);self.discovery_picture_key=key
            self.discovery_summary.configure(text=row['category']+' • Difficulty: '+str(row['difficulty'])+'\nRequired discovery score: '+str(row['required_score'])+' or higher')
            self.discovery_description.configure(text=row['description'])
            self.note.configure(text='Current project discovery pool. Availability varies between games; this does not show which discoveries are enabled or already found in your save.')
            self.ships.configure(text='');self.schedule_discovery_fit();return
        for key,value in self.values.items():value.set(('Yes'if row['capital']else 'No')if key=='capital'and 'capital'in row else str(row.get(key,'Not applicable')))
        if self.goods_hidden():self.values['specialty'].set('Hidden by blind shuffle')
        for key,widget in self.value_labels.items():widget.configure(foreground='#ef7800'if row.get(key)!=self.stock_port_records[row['id']].get(key)else '#17243d')
        if self.view=='Economy':
            self.economy_panel.show(self.selected);self.note.configure(text='Edit starting levels here; Port Information reflects the result. Save/export explicitly. Existing saves keep their town levels.');self.ships.configure(text='');return
        if self.selected>=100:
            self.port_lists.pack_forget();self.port_item_rows=[]
            self.note.configure(text='Supply ports do not use trading-town economy, industry or specialty records.');self.ships.configure(text='');return
        self.note.configure(text='Blue line: starting value. Ready entries above; locked entries below. '+('This capital cannot raise economy or industry through investment. 'if row['capital']else '')+'Project starting values; save not read. Goods stock varies. Ships: new builds only.')
        project=self.editor.project
        goods=[dict(id=good['id'],name=('★ 'if source['kind']=='Specialty'else '')+good['name'],required=source['economy_required'],changed=source not in self.stock_goods_records[good['id']]['sources'])for good in self.goods_records for source in good['sources']if source['port']==self.selected]
        if self.goods_hidden():goods=[];self.note.configure(text=self.note.cget('text')+' Goods hidden by blind shuffle.')
        offers=[dict(id=ship['id'],name=ship['name'],required=offer['industry'])for ship,offer in zip(project.ships,project.all_offers())if self.selected in offer['ports']]
        if __import__('shipbuilding_shuffle').hidden(project):offers=[o for o in offers if o['id']>=25];self.note.configure(text=self.note.cget('text')+' Original ship building locations hidden by blind shuffle.')
        self.port_goods.set_rows(goods,row['economy'],row['capital']);self.port_ships.set_rows(offers,row['industry'],row['capital'])
        self.layout_port_lists();self.port_lists.pack(before=self.note,fill='x')
        self.port_item_rows=[]if self.items_hidden()else [dict(id=item['id'],name=item['name'],**source)for item in self.item_records for source in item['sources']if source['port']==self.selected]
        for child in self.port_items_body.winfo_children():child.destroy()
        for i,item in enumerate(sorted(self.port_item_rows,key=lambda item:(item['rare'],item['name']))):
            original=next(r for r in self.stock_item_records if r['id']==item['id'])['sources']
            changed=not any(source['port']==self.selected and source['slot']==item['slot']for source in original)
            ink='#ef7800'if changed else '#17243d'
            ttk.Label(self.port_items_body,text=item['name'],foreground=ink,style='Card.TLabel',font=('Segoe UI',10),wraplength=150).grid(row=i,column=0,sticky='w',padx=(0,12),pady=3)
            ttk.Label(self.port_items_body,text=item['hours'],foreground=ink,style='Card.TLabel',font=('Segoe UI',10)).grid(row=i,column=1,sticky='e',pady=3)
        self.port_items_body.columnconfigure(0,weight=1)
        if not self.port_item_rows:ttk.Label(self.port_items_body,text='Hidden by blind item shuffle.'if self.items_hidden()else 'No item shop stock listed.',style='Card.TLabel').grid(sticky='w')
        self.ships.configure(text='')

    def goods_hidden(self):
        p=self.editor.project
        return bool(p and p.goods_shuffle['seed']is not None and p.goods_shuffle.get('blind',False))

    def items_hidden(self):
        p=self.editor.project
        return bool(p and p.item_seed is not None and p.item_blind)

    def good_sources(self):
        if self.view not in ('Goods','Items')or not self.records:return []
        if self.view=='Items'and self.items_hidden()or self.view=='Goods'and self.goods_hidden():return []
        good=next(row for row in self.records if row['id']==self.selected)
        return [source for source in good['sources']if self.view=='Items'or self.include_locked.get()or source['available_at_start']]

    def refresh_goods(self):
        if self.view not in ('Goods','Items')or not self.records:return
        is_item=self.view=='Items';sources=self.good_sources();start=sum(source.get('available_at_start',True)for source in sources)
        self.goods_title.configure(text='Item shops'if is_item else 'Selling ports')
        self.goods_tree.heading('economy',text='Hours'if is_item else 'Economy');self.goods_tree.heading('start',text='Offer'if is_item else 'At start')
        self.goods_tree.column('economy',width=110 if is_item else 70)
        row=next(r for r in self.records if r['id']==self.selected)
        self.item_description.configure(text=row['description']if is_item else '')
        if is_item:
            from items import picture
            key=(id(self.rom),row['id'])
            if key!=self.item_picture_key:
                self.item_photo=ImageTk.PhotoImage(picture(self.rom,row['id']),master=self.item_picture);self.item_picture.configure(image=self.item_photo);self.item_picture_key=key
            from item_prices import price
            rank=__import__('items').weapon_rank(self.rom,row['id'])
            self.item_meta.configure(text='Base price: '+__import__('currency').item_price(price(self.editor.project,row['id']))+(f'\nWeapon rank: {rank}'if rank else ''))
            self.item_picture.pack(side='left',before=self.item_meta)
            self.item_profile.pack(before=self.item_description,anchor='w',pady=(0,8))
        else:self.item_profile.pack_forget()
        if is_item:self.goods_edit_frame.pack_forget();self.goods_enable_box.pack_forget();self.item_editor.pack(fill='x');self.item_editor.show()
        else:self.item_editor.pack_forget();self.goods_enable_box.pack(anchor='w');self.goods_edit_frame.pack(fill='x')
        self.goods_tree.delete(*self.goods_tree.get_children())
        for source in sources:
            port=self.port_records[source['port']]
            self.goods_tree.insert('','end',iid=str(port['id']),values=(port['name'],source['hours'],'Early only'if source['rare']else 'Regular')if is_item else (port['name'],source['economy_required'],'Yes'if source['available_at_start']else 'No'))
        if is_item:
            original=next(r for r in self.stock_item_records if r['id']==self.selected)['sources']
            for source in sources:
                if source not in original:self.goods_tree.item(str(source['port']),tags=('changed',))
        if not is_item:
            original=next(g for g in self.stock_goods_records if g['id']==self.selected)['sources']
            for source in sources:
                if source not in original:self.goods_tree.item(str(source['port']),tags=('changed',))
        if self.good_port_selected is not None and self.goods_tree.exists(str(self.good_port_selected)):self.goods_tree.selection_set(str(self.good_port_selected))
        self.goods_summary.configure(text=f'{len(sources)} selling ports • Regular and early-morning offers'if is_item else f'{len(sources)} selling ports • {start} available at game start\nEconomy column shows the required economy.')
        self.note.configure(text='Project shop stock. Early-only offers appear from 02:00 until before 03:00. Regular offers follow shop opening hours. This lists shop items, not quest rewards or other ways to obtain items. Use a new game for changed stock. Your save is not read.'if is_item else 'Project selling locations. Nine regular goods and one specialty per port. Added offers keep native pricing rules using stock base-price references. Use a new game for specialty changes; saved stock may take time to refresh.')
        self.ships.configure(text='')
        if self.good_port_selected not in [source['port']for source in sources]:self.good_port_selected=None
        if is_item and self.items_hidden():
            self.item_editor.pack_forget();self.item_editor.enable_box.configure(state='disabled')
            self.goods_summary.configure(text='Blind shuffle: selling locations are hidden.')
            self.note.configure(text='Item destinations are hidden in Items and Port Information. Open Gameplay - World - Item seed shuffle to change or restore the shuffle.')
        if not is_item and self.goods_hidden():
            self.goods_edit_frame.pack_forget();self.goods_enable_box.pack_forget()
            self.goods_summary.configure(text='Blind shuffle: selling locations are hidden.')
            self.note.configure(text='Goods destinations are hidden in Goods and Port Information. Open Gameplay → World → Use random goods to change or restore the shuffle.')
        self.sync_goods_editor()
        self.draw_map()

    def pick_selling_port(self,event=None):
        selected=self.goods_tree.selection()
        if selected:
            if self.view=='Goods'and int(selected[0])!=self.good_port_selected and not self.commit_edits():
                if self.good_port_selected is not None and self.goods_tree.exists(str(self.good_port_selected)):self.goods_tree.selection_set(str(self.good_port_selected))
                else:self.goods_tree.selection_remove(*selected)
                return
            self.good_port_selected=int(selected[0])
            if self.view=='Goods'and self.goods_tree.exists(selected[0])and self.goods_tree.selection()!=selected:self.goods_tree.selection_set(selected[0])
            if self.view=='Items':self.item_editor.show()
            else:self.sync_goods_editor()
            self.draw_map()

    def sync_goods_editor(self):
        if self.view!='Goods' or not self.editor.project:return
        self.goods_edit_loading=True
        self.goods_enable_box.configure(state='disabled'if self.goods_hidden()else 'normal')
        self.custom_goods_var.set(self.editor.project.custom_goods);enabled=self.editor.project.custom_goods and not self.goods_hidden()
        self.goods_port_box.configure(state='readonly'if enabled else 'disabled')
        self.goods_gate_box.configure(state='normal'if enabled else 'disabled')
        self.restore_good_button.configure(state='normal'if enabled else 'disabled')
        self.goods_port_box.configure(values=[p['name']for p in self.port_records[:100]])
        port=self.good_port_selected
        if port is None:port=self.goods_port_box.current()
        if port is None or port<0:port=0
        self.goods_port_box.current(port)
        source=next((o for o in next(g for g in self.records if g['id']==self.selected)['sources']if o['port']==port),None)
        draft=self.goods_pending
        value=draft[2]if draft and draft[:2]==(port,self.selected)else str(source['economy_required']if source and not self.goods_hidden()else 0)
        self.goods_gate.set(value)
        stock=next(g for g in self.stock_goods_records if g['id']==self.selected)['sources']
        self.goods_gate_box.configure(style='Changed.TSpinbox'if source and source not in stock else 'TSpinbox')
        self.add_good_button.configure(state='normal'if enabled and not source else 'disabled')
        self.remove_good_button.configure(state='normal'if enabled and source else 'disabled')
        self.goods_edit_loading=False

    def toggle_custom_goods(self):
        if not self.editor.project or self.goods_hidden():return
        wanted=self.custom_goods_var.get()
        if not self.commit_edits():self.custom_goods_var.set(self.editor.project.custom_goods);return
        self.editor.project.custom_goods=wanted;self.editor.update_status()

    def select_edit_port(self,event=None):
        port=self.goods_port_box.current()
        if not self.commit_edits():self.sync_goods_editor();return
        self.good_port_selected=port
        if self.goods_tree.exists(str(port)):self.goods_tree.selection_set(str(port))
        else:self.goods_tree.selection_remove(*self.goods_tree.selection())
        self.sync_goods_editor();self.draw_map()

    def schedule_goods_gate(self,*args):
        if self.goods_edit_loading or self.view!='Goods'or not self.editor.project or not self.editor.project.custom_goods or self.goods_hidden():return
        if self.goods_edit_timer is not None:self.editor.root.after_cancel(self.goods_edit_timer)
        # Capture the identity; changing the selected good cannot retarget an edit.
        port=self.goods_port_box.current();good=self.selected;value=self.goods_gate.get()
        self.goods_pending=(port,good,value)
        self.goods_edit_timer=self.editor.root.after(350,self.flush_goods_gate)

    def cancel_goods_edit(self):
        if self.goods_edit_timer is not None:self.editor.root.after_cancel(self.goods_edit_timer)
        self.goods_edit_timer=None;self.goods_pending=None

    def commit_edits(self):
        try:self.item_editor.flush(strict=True);self.flush_goods_gate(strict=True);self.economy_panel.flush(strict=True)
        except ValueError as error:self.editor.fail(error);return False
        return True

    def flush_goods_gate(self,strict=False):
        if self.goods_pending is None:return
        if self.goods_edit_timer is not None:self.editor.root.after_cancel(self.goods_edit_timer)
        self.goods_edit_timer=None
        port,good,value=self.goods_pending
        project=self.editor.project
        if not project or not project.custom_goods or self.goods_hidden():self.goods_pending=None;return
        from trade_goods import offers,change
        if not 0<=port<100 or not any(o['good']==good for o in offers(project.rom,project.goods_edits)[port]):self.goods_pending=None;return
        try:
            edits=change(project.rom,project.goods_edits,port,good,int(value))
        except ValueError:
            error=ValueError('Goods requirements must be whole numbers from 0 to 2550 in steps of 10. Correct the entry or use Restore good.')
            if strict:raise error
            self.editor.status.configure(text='Finish editing: '+str(error));return
        self.goods_pending=None;project.goods_shuffle=dict(seed=None,mode='normal');project.goods_edits=edits;self.editor.update_status()

    def add_good_port(self):
        project=self.editor.project
        if not project or not project.custom_goods or self.view!='Goods'or self.goods_hidden():return
        try:
            from trade_goods import change
            project.goods_edits=change(project.rom,project.goods_edits,self.goods_port_box.current(),self.selected,int(self.goods_gate.get()));project.goods_shuffle=dict(seed=None,mode='normal')
            self.good_port_selected=self.goods_port_box.current();self.editor.update_status()
        except ValueError as error:messagebox.showerror('Goods availability',str(error),parent=self.editor.root)

    def remove_good_port(self):
        project=self.editor.project
        if not project or not project.custom_goods or self.view!='Goods'or self.goods_hidden():return
        if not self.commit_edits():return
        from trade_goods import change
        project.goods_edits=change(project.rom,project.goods_edits,self.goods_port_box.current(),self.selected,remove=True);project.goods_shuffle=dict(seed=None,mode='normal')
        self.editor.update_status()

    def restore_good(self):
        project=self.editor.project
        if not project or not project.custom_goods or self.view!='Goods'or self.goods_hidden():return
        self.cancel_goods_edit()
        try:
            from trade_goods import offers,stock_offers,validate
            stock=stock_offers(project.rom);current=offers(project.rom,project.goods_edits)
            for port,row in enumerate(current):
                row[:]=[o for o in row if o['good']!=self.selected]+[o for o in stock[port]if o['good']==self.selected]
                # Preserve native slot ordering when restoring the last change.
                order={o['good']:i for i,o in enumerate(stock[port])}
                row.sort(key=lambda o:order.get(o['good'],100+o['good']))
            project.goods_edits=validate(project.rom,[dict(port=p,offers=row)for p,row in enumerate(current)]);project.goods_shuffle=dict(seed=None,mode='normal')
            self.editor.update_status()
        except ValueError as error:messagebox.showerror('Restore good',str(error),parent=self.editor.root)

    def draw_map(self):
        if self.map_image is None or not self.records:return
        canvas=self.map_canvas;width=max(1,canvas.winfo_width()-2);height=max(1,width//2)
        if int(canvas.cget('height'))!=height:canvas.configure(height=height)
        scale=min(width/WIDTH,height/HEIGHT);size=(max(1,round(WIDTH*scale)),max(1,round(HEIGHT*scale)))
        if size!=self.map_scaled_size:
            self.map_photo=ImageTk.PhotoImage(self.map_image.resize(size,Image.Resampling.NEAREST),master=canvas);self.map_scaled_size=size
        canvas.delete('all');left=(width-size[0])/2+1;top=(height-size[1])/2+1
        canvas.create_image(left,top,anchor='nw',image=self.map_photo)
        row=next(row for row in self.records if row['id']==self.selected)
        if self.view in ('Goods','Items'):members=[self.port_records[source['port']]for source in self.good_sources()]
        else:members=[port for port in self.records if self.view in ('Ports','Economy')and port['region']==self.region.get()]
        marker_ports=members if self.view not in ('Goods','Items')or len(members)!=1 else []
        for port in marker_ports:
            px=left+port['x']*size[0]/WIDTH;py=top+port['y']*size[1]/HEIGHT
            tag='item-port'if self.view=='Items'else 'goods-port'if self.view=='Goods'else 'region-port'
            canvas.create_oval(px-2,py-2,px+2,py+2,fill='#ee4035',outline='white',width=1,tags=(tag,f"port-{port['id']}"))
        target=row if self.view not in ('Goods','Items')else next((port for port in members if port['id']==self.good_port_selected),members[0]if len(members)==1 else None)
        self.marker=None
        if target:
            x=left+target['x']*size[0]/WIDTH;y=top+target['y']*size[1]/HEIGHT;self.marker=(x,y)
            marker_tag='selected-discovery'if self.view=='Discoveries'else 'selected-port'
            canvas.create_oval(x-6,y-6,x+6,y+6,outline='white',width=3,tags=marker_tag)
            canvas.create_oval(x-4,y-4,x+4,y+4,outline='#ee4035',width=2,tags=marker_tag)
            canvas.create_line(x-10,y,x+10,y,fill='#ee4035',width=1,tags=marker_tag)
            canvas.create_line(x,y-10,x,y+10,fill='#ee4035',width=1,tags=marker_tag)
        prefix=(str(len(members))+' selling ports — ')if self.view in ('Goods','Items')else ((self.region.get()+' — '+str(len(members))+' ports\n')if members else 'ROM world map — ')
        self.map_caption.configure(text=prefix+row['name'])

