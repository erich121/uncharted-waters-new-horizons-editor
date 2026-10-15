"""Windows editor for25 original ships and up to five additional hulls."""
import ctypes,sys,json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from backend import ShipProject,FIELDS,EDIT_FIELDS,ports,price_from_bars,TOOL_VERSION
from PIL import ImageTk
import portraits
from ui_theme import EditorTheme

LABELS={'name':'Ship name','hull':'Hull strength','turning':'Turning','power':'Sailing power',
    'max_guns':'Maximum guns','min_crew':'Minimum sailors','max_crew':'Maximum crew spaces','price_gold':'Base price in gold bars'}
BUILD_ID='release'

class ScrollableWindow(ttk.Frame):
    """Keep the whole editor reachable on small or scaled Windows displays."""
    def __init__(self,root):
        super().__init__(root);self.pack(side='left',fill='both',expand=True)
        self.rowconfigure(0,weight=1);self.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,highlightthickness=0,background='#f5f7fb')
        self.canvas.grid(row=0,column=0,sticky='nsew')
        ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview).grid(row=0,column=1,sticky='ns')
        ttk.Scrollbar(self,orient='horizontal',command=self.canvas.xview).grid(row=1,column=0,sticky='ew')
        self.canvas.configure(yscrollcommand=self._vertical,xscrollcommand=self._horizontal)
        # Retain scrollbar widgets for their position feedback.
        self.vertical=self.grid_slaves(row=0,column=1)[0]
        self.horizontal=self.grid_slaves(row=1,column=0)[0]
        self.content=ttk.Frame(self.canvas)
        self.window=self.canvas.create_window((0,0),window=self.content,anchor='nw')
        self.content.bind('<Configure>',self.resize)
        self.canvas.bind('<Configure>',self.resize)
        owner=root.winfo_toplevel()
        owner.bind_all('<MouseWheel>',self.wheel,add='+')
        owner.bind('<FocusIn>',self.focus_visible,add='+')

    def _vertical(self,*args):self.vertical.set(*args)
    def _horizontal(self,*args):
        self.horizontal.set(*args)
        if float(args[1])-float(args[0])>=0.999:self.horizontal.grid_remove()
        else:self.horizontal.grid()
    def resize(self,event=None):
        at_top=self.canvas.yview()[0]<=0.0001
        at_left=self.canvas.xview()[0]<=0.0001
        width=max(self.content.winfo_reqwidth(),self.canvas.winfo_width())
        height=max(self.content.winfo_reqheight(),self.canvas.winfo_height())
        self.canvas.itemconfigure(self.window,width=width,height=height)
        self.canvas.configure(scrollregion=(0,0,width,height))
        if at_top:self.canvas.yview_moveto(0)
        if at_left:self.canvas.xview_moveto(0)
    def wheel(self,event):
        if not str(event.widget).startswith(str(self.content)):return
        if event.widget.winfo_class()in ('Listbox','TCombobox'):return
        steps=-int(event.delta/120)if abs(event.delta)>=120 else (-1 if event.delta>0 else 1)
        if event.state&1:self.canvas.xview_scroll(steps,'units')
        else:self.canvas.yview_scroll(steps,'units')
        return 'break'
    def focus_visible(self,event):
        widget=event.widget
        if not str(widget).startswith(str(self.content))or not widget.winfo_ismapped():return
        # Large containers/lists must not move underneath the pointer on click.
        if widget.winfo_class()not in ('TEntry','TSpinbox','TCombobox','TButton','TCheckbutton','Entry','Button'):return
        self.canvas.update_idletasks()
        left=widget.winfo_rootx()-self.content.winfo_rootx()
        top=widget.winfo_rooty()-self.content.winfo_rooty()
        total_w=int(float(self.canvas.itemcget(self.window,'width')))
        total_h=int(float(self.canvas.itemcget(self.window,'height')))
        for start,size,total,viewport,view,move in [
            (left,widget.winfo_width(),total_w,self.canvas.winfo_width(),self.canvas.xview,self.canvas.xview_moveto),
            (top,widget.winfo_height(),total_h,self.canvas.winfo_height(),self.canvas.yview,self.canvas.yview_moveto)]:
            origin=view()[0]*total
            if start<origin:move(max(0,start-8)/total)
            elif start+size>origin+viewport:move(max(0,start+size+8-viewport)/total)

class Editor:
    def __init__(self,root):
        self.root=root;self.project=None;self.selected=None;self.loading=False;self.displayed_ship=None
        root.title('New Horizons Editor v'+TOOL_VERSION)
        root.geometry(f'{min(1672,max(640,root.winfo_screenwidth()-80))}x{min(940,max(480,root.winfo_screenheight()-80))}')
        root.minsize(640,480)
        root.protocol('WM_DELETE_WINDOW',self.close)
        style=ttk.Style();style.theme_use('clam')
        root.configure(background='#f5f7fb')
        style.configure('.',font=('Segoe UI',11),background='#f5f7fb',foreground='#17243d')
        style.configure('TFrame',background='#f5f7fb')
        style.configure('TLabel',font=('Segoe UI',11),background='#f5f7fb')
        style.configure('TButton',font=('Segoe UI',10),padding=(12,7),background='#edf1f7',bordercolor='#ccd5e3')
        for widget_style in ('TEntry','TSpinbox','TCombobox'):
            style.configure(widget_style,font=('Segoe UI',11),padding=(7,3),fieldbackground='white',bordercolor='#bdc9da')
        style.map('TButton',background=[('active','#e1eafa')])
        style.configure('Primary.TButton',background='#0864d9',foreground='white',padding=(16,8))
        style.map('Primary.TButton',background=[('active','#0756ba'),('disabled','#dce4ee')],foreground=[('disabled','#78879a')])
        style.configure('Nav.TButton',anchor='w',padding=(14,8),borderwidth=0)
        style.configure('Selected.Nav.TButton',background='#d7e8ff',foreground='#0759b8')
        style.configure('TNotebook',background='#f5f7fb',bordercolor='#d6deeb')
        style.configure('TNotebook.Tab',padding=(16,10),background='#edf1f7')
        style.map('TNotebook.Tab',background=[('selected','#ffffff')],foreground=[('selected','#0563d8')])
        style.configure('TLabelframe',background='#ffffff',bordercolor='#d6deeb',relief='solid')
        style.configure('TLabelframe.Label',font=('Segoe UI',10,'bold'),background='#ffffff',foreground='#19345c')
        style.configure('Card.TFrame',background='#ffffff')
        style.configure('CardBorder.TFrame',background='#d8e1ef')
        style.configure('CardHeader.TFrame',background='#eef3fa')
        style.configure('CardTitle.TLabel',font=('Segoe UI',11,'bold'),background='#eef3fa',foreground='#19345c')
        style.configure('Card.TLabel',font=('Segoe UI',10),background='#ffffff')
        style.configure('Hint.Card.TLabel',background='#ffffff',foreground='#6e7f98',font=('Segoe UI',9))
        self.ui=EditorTheme(root,style)
        top=ttk.Frame(root,padding=(16,12));top.pack(fill='x')
        title=ttk.Frame(top);title.pack(fill='x')
        self.title_label=ttk.Label(title,text='New Horizons Editor',image=self.ui.icon('feather','#194c85',32),compound='left',font=('Segoe UI',20,'bold'),wraplength=420);self.title_label.pack(side='left',anchor='w')
        self.build_label=ttk.Label(title,text='v'+TOOL_VERSION,foreground='#7a8799');self.build_label.pack(side='left',anchor='s',padx=(12,0),pady=(0,3))
        bar=ttk.Frame(top);bar.pack(fill='x')
        self.toolbar_buttons=[];self.toolbar_layout=None
        for n,(title,call)in enumerate([('Open stock ROM',self.open_rom),('Open project',self.open_project),('Save project',self.save_project),('Export ROM and IPS',self.export),('Help',self.help)]):
            symbol=('folder','folder','save','export','help')[n]
            b=ttk.Button(bar,text=title,command=call,image=self.ui.icon(symbol,'#0869df',22),compound='left');b.grid(row=0,column=n,padx=(0,8),pady=8);self.toolbar_buttons.append(b)
        def arrange_toolbar(event):
            wide=event.width>=1220
            available=event.width-450 if wide else event.width
            row=column=used=0;layout=[]
            for b in self.toolbar_buttons:
                width=b.winfo_reqwidth()+6
                if used and used+width>available:row+=1;column=used=0
                layout.append((row,column));used+=width;column+=1
            if (layout,wide)==self.toolbar_layout:return
            self.toolbar_layout=(layout,wide)
            for b,(r,c)in zip(self.toolbar_buttons,layout):b.grid(row=r,column=c,sticky='w',padx=(0,6),pady=4)
            self.source.grid(row=0 if wide else row+1,column=5 if wide else 0,columnspan=1 if wide else 5,sticky='e'if wide else 'w',pady=(4,6))
            bar.columnconfigure(5,weight=1)
        bar.bind('<Configure>',arrange_toolbar)
        self.source=ttk.Label(bar,text='Open your original USA .sfc, .smc or ZIP to begin.',wraplength=430,foreground='#47607d')
        status_panel=tk.Frame(root,background='white',highlightthickness=1,highlightbackground='#d8e2ef');status_panel.pack(side='bottom',fill='x')
        self.status=ttk.Label(status_panel,text='Open a stock USA ROM to begin.',style='Status.TLabel',image=self.ui.icon('stats','#64758c',18),compound='left',padding=(16,8),wraplength=580);self.status.pack(fill='x')
        body=ttk.Frame(root,padding=(16,0,16,0));body.pack(fill='both',expand=True)
        left=ttk.Frame(body,padding=(12,10),style='Sidebar.TFrame',width=320);self.sidebar=left;left.pack(side='left',fill='y',padx=(0,10));left.pack_propagate(False)
        ttk.Label(left,text='Data type',foreground='#546783').pack(anchor='w',pady=(0,6))
        nav=ttk.Frame(left);nav.pack(fill='x',pady=1)
        tk.Frame(nav,background='#0869df',width=3).pack(side='left',fill='y')
        ships_nav=ttk.Button(nav,text='Ships',image=self.ui.icon('ship'),compound='left',style='Selected.Nav.TButton',takefocus=False);ships_nav.pack(side='left',fill='x',expand=True)
        mates_nav=ttk.Button(left,text='Mates',image=self.ui.icon('person','#566579'),compound='left',style='Nav.TButton',state='disabled');mates_nav.pack(fill='x',pady=1)
        captains_nav=ttk.Button(left,text='Enemy Captains',image=self.ui.icon('captain','#566579'),compound='left',style='Nav.TButton',state='disabled');captains_nav.pack(fill='x',pady=(1,8))
        self.nav_buttons=[ships_nav,mates_nav,captains_nav]
        ttk.Separator(left).pack(fill='x',pady=(0,10))
        remove=ttk.Frame(left);remove.pack(side='bottom',fill='x',pady=(8,0))
        self.remove_button=ttk.Button(remove,text='Remove added ship',command=self.remove);self.remove_button.pack(fill='x')
        # This browser can later display character records without adding empty
        # categories to the working ship editor today.
        self.browser=left;self.ship_rows=[];self.search_var=tk.StringVar()
        list_title=ttk.Frame(left);list_title.pack(fill='x',pady=(0,6))
        self.ships_heading=ttk.Label(list_title,text='Ships',font=('Segoe UI',12,'bold'));self.ships_heading.pack(side='left')
        self.add_button=ttk.Button(list_title,text='Add ship (up to 5)',command=self.add,image=self.ui.icon('add','#0876e9',16),compound='left');self.add_button.pack(side='right',padx=(8,0))
        self.search_frame=ttk.Frame(left);self.search_frame.pack(fill='x',pady=(0,6))
        ttk.Label(self.search_frame,text='Search').pack(side='left',padx=(0,6))
        self.search_entry=ttk.Entry(self.search_frame,textvariable=self.search_var,width=18)
        self.search_entry.configure(font=('Segoe UI',10))
        self.search_entry.pack(side='left',fill='x',expand=True)
        self.search_var.trace_add('write',lambda *args:self.refresh_list())
        self.search_entry.bind('<Escape>',lambda e:self.clear_search())
        root.bind('<Control-f>',lambda e:self.open_search())
        ship_frame=ttk.Frame(left);ship_frame.pack(fill='both',expand=True)
        self.list=tk.Listbox(ship_frame,width=27,height=25,font=('Segoe UI',10),exportselection=False,
            background='white',foreground='black',selectbackground='#205b9b',selectforeground='white')
        self.list.pack(side='left',fill='both',expand=True);self.list.bind('<<ListboxSelect>>',self.pick)
        ship_scroll=ttk.Scrollbar(ship_frame,command=self.list.yview);ship_scroll.pack(side='right',fill='y');self.list.configure(yscrollcommand=ship_scroll.set)
        settings=ttk.Frame(body);settings.pack(side='left',fill='both',expand=True)
        actions=ttk.Frame(settings);actions.pack(side='bottom',fill='x',pady=(8,0))
        self.apply_button=ttk.Button(actions,text='Apply ship changes',command=self.apply,style='Primary.TButton',image=self.ui.icon('check','white',22),compound='left');self.apply_button.grid(row=0,column=0,sticky='w',padx=(0,12),pady=2)
        self.restore_button=ttk.Button(actions,text='Restore selected ship',command=self.restore,image=self.ui.icon('restore','#243c60',20),compound='left');self.restore_button.grid(row=0,column=1,sticky='w',pady=2)
        def arrange_actions(event):
            narrow=self.apply_button.winfo_reqwidth()+self.restore_button.winfo_reqwidth()+8>event.width
            self.restore_button.grid(row=1 if narrow else 0,column=0 if narrow else 1,sticky='w',pady=2)
        actions.bind('<Configure>',arrange_actions)
        self.tab_bar=ttk.Frame(settings);self.tab_bar.pack(fill='x')
        notebook=ttk.Notebook(settings,style='Editor.TNotebook');self.notebook=notebook;notebook.pack(fill='both',expand=True)
        spec_tab=ttk.Frame(notebook);port_tab=ttk.Frame(notebook);art_tab=ttk.Frame(notebook);fix_tab=ttk.Frame(notebook);gameplay_tab=ttk.Frame(notebook)
        notebook.add(spec_tab,text='Specifications');notebook.add(port_tab,text='Availability');notebook.add(art_tab,text='Graphics');notebook.add(fix_tab,text='Fixes');notebook.add(gameplay_tab,text='Gameplay')
        self.tab_buttons=[];self.tab_lines=[]
        for index,(label,symbol)in enumerate((('Specifications','stats'),('Availability','calendar'),('Graphics','image'),('Fixes','wrench'),('Gameplay','game'))):
            tab=ttk.Frame(self.tab_bar);tab.pack(side='left')
            button=ttk.Button(tab,text=label,image=self.ui.icon(symbol,'#54647b'),compound='left',style='Tab.TButton',command=lambda i=index:notebook.select(i))
            button.pack(fill='x');self.tab_buttons.append(button)
            underline=tk.Frame(tab,height=3,background='#f5f7fb');underline.pack(fill='x');self.tab_lines.append(underline)
        self.scrollers=[ScrollableWindow(tab)for tab in (spec_tab,port_tab,art_tab,fix_tab,gameplay_tab)];self.scroll=self.scrollers[0]
        def switch_tab(event):
            self.scroll=self.scrollers[notebook.index('current')]
            for i,button in enumerate(self.tab_buttons):
                active=i==notebook.index('current');button.configure(style='Active.Tab.TButton'if active else 'Tab.TButton')
                button.configure(image=''if getattr(self,'compact',None)=='compact'else self.ui.icon(('stats','calendar','image','wrench','game')[i],'#0869df'if active else '#54647b'))
                self.tab_lines[i].configure(background='#0869df'if active else '#f5f7fb')
            # Invalidate the canvas item after tab mapping so Tk remaps its child.
            scroll=self.scroll
            def remap():
                scroll.canvas.move(scroll.window,1,0);scroll.canvas.move(scroll.window,-1,0)
                scroll.resize()
            root.after_idle(remap)
        notebook.bind('<<NotebookTabChanged>>',switch_tab)
        right=ttk.Frame(self.scrollers[0].content,padding=12);right.pack(fill='both',expand=True)
        availability=ttk.Frame(self.scrollers[1].content,padding=12);availability.pack(fill='both',expand=True)
        art_page=ttk.Frame(self.scrollers[2].content,padding=12);art_page.pack(fill='both',expand=True)
        self.graphics_heading=ttk.Label(art_page,text='Ship graphics',font=('Segoe UI',15,'bold'));self.graphics_heading.pack(anchor='w',pady=(0,12))
        self.heading=ttk.Label(right,text='No game loaded',font=('Segoe UI',16,'bold'));self.heading.pack(anchor='w',pady=(0,4))
        self.record_heading=ttk.Label(right,text='Ship ID: —',foreground='#6e7f98');self.record_heading.pack(anchor='w',pady=(0,10))
        self.cards=ttk.Frame(right);self.cards.pack(fill='x');self.spec_sections=[];self.card_columns=None;self.field_labels=[];self.field_hints=[]
        self.card_stacks=[ttk.Frame(self.cards),ttk.Frame(self.cards)]
        for stack in self.card_stacks:stack.columnconfigure(0,weight=1)
        self.vars={};self.entries={};self.extra_vars={};self.extra_entries={}
        self.fit_loading=False;self.fit_syncing=False
        def section(parent,title):
            panel=ttk.Frame(self.cards if parent==right else parent,style='Surface.TFrame',padding=1)
            header=ttk.Frame(panel,style='CardHeader.TFrame',padding=(12,10));header.pack(fill='x',padx=8)
            symbol={'Name and price':'coins','Hull and handling':'anchor','Guns and crew limits':'guns','Quick info':'info','Capacity and calculated cargo':'ship','Starting equipment':'wrench'}.get(title,'image')
            ttk.Label(header,text=title,image=self.ui.icon(symbol),compound='left',style='CardTitle.TLabel').pack(anchor='w')
            frame=ttk.Frame(panel,style='Card.TFrame',padding=(18,12));frame.pack(fill='both',expand=True,padx=8,pady=(0,8))
            frame.panel=panel
            if parent==right:self.spec_sections.append(frame)
            else:panel.pack(fill='x',pady=(0,12))
            frame.columnconfigure(1,weight=1)
            return frame
        def field(frame,row,key,title,hint,extra=False):
            label=ttk.Label(frame,text=title,wraplength=180,style='Card.TLabel');label.grid(row=row*2,column=0,sticky='w',padx=(0,16),pady=(4,0));self.field_labels.append(label)
            v=tk.StringVar()
            if key=='name':e=ttk.Entry(frame,textvariable=v,width=17,state='disabled')
            else:
                bounds={'price_gold':(.001,32,.001),'hull':(1,100,1),'power':(1,100,1),'turning':(1,100,1),'max_guns':(0,150,1),'max_crew':(10,500,10),'min_crew':(1,255,1),'capacity':(1,2000,1)}
                low,high,step=bounds.get(key,(0,2000,1))
                # Computed cargo remains a read-only display rather than a spinner.
                e=ttk.Entry(frame,textvariable=v,width=14,state='disabled')if key in ('yard_cargo','factory_cargo')else ttk.Spinbox(frame,textvariable=v,width=12,state='disabled',from_=low,to=high,increment=step)
            e.configure(font=('Segoe UI',11))
            e.grid(row=row*2,column=1,sticky='ew'if key=='name'else 'w',pady=(4,0))
            if hint:
                hint_label=ttk.Label(frame,text=hint,style='Hint.Card.TLabel',wraplength=260);hint_label.grid(row=row*2+1,column=1,sticky='w',pady=(2,8));self.field_hints.append(hint_label)
            (self.extra_vars if extra else self.vars)[key]=v;(self.extra_entries if extra else self.entries)[key]=e
        identity=section(right,'Name and price')
        self.identity_card=identity
        field(identity,0,'name','Ship name','1-17 English characters')
        field(identity,1,'price_gold','Base price (gold bars)','1 bar = 10,000 gold')
        handling=section(right,'Hull and handling')
        for row,(key,title,hint)in enumerate([('hull','Hull strength','Durability: 1-100'),('power','Sailing power','Speed: 1-100'),('turning','Turning','Maneuverability: 1-100')]):field(handling,row,key,title,hint)
        limits=section(right,'Guns and crew limits')
        for row,(key,title,hint)in enumerate([('max_guns','Maximum guns','0-150; at least starting guns'),('max_crew','Maximum crew spaces','10-500, in steps of 10'),('min_crew','Minimum sailors','Crew needed to sail: 1-255')]):field(limits,row,key,title,hint)
        space=section(right,'Capacity and calculated cargo')
        field(space,0,'capacity','Total capacity','Shared by guns, crew and cargo: 1-2,000',True)
        field(space,1,'yard_cargo','Shipyard cargo','Calculated: total - maximum guns - maximum crew',True)
        field(space,2,'factory_cargo','Cargo when first built','Calculated: total - starting guns - starting crew',True)
        fit=section(right,'Starting equipment')
        self.fixed=ttk.Label(fit,text='',wraplength=300,style='Hint.Card.TLabel');self.fixed.grid(row=6,column=0,columnspan=2,sticky='w',pady=(8,4))
        field(fit,0,'factory_guns','Starting guns','Spaces fitted when the ship is built',True)
        field(fit,1,'factory_crew','Starting crew spaces','Crew allocation when the ship is built',True)
        quick=section(right,'Quick info');self.quick_vars={}
        for row,(key,label)in enumerate((('index','Record index'),('kind','Record type'),('family','Original family'))):
            ttk.Label(quick,text=label,style='Card.TLabel').grid(row=row*2,column=0,sticky='w',padx=(0,12),pady=5)
            self.quick_vars[key]=tk.StringVar(value='—')
            ttk.Label(quick,textvariable=self.quick_vars[key],style='Card.TLabel',wraplength=180).grid(row=row*2,column=1,sticky='w',pady=5)
            ttk.Separator(quick).grid(row=row*2+1,column=0,columnspan=2,sticky='ew')
        ttk.Label(quick,text='Cargo is calculated from capacity and the space allocated to guns and crew.',style='Hint.Card.TLabel',wraplength=300).grid(row=6,column=0,columnspan=2,sticky='w',pady=(12,4))
        self.spec_sections=[identity,handling,limits,quick,space,fit]
        def arrange_cards(event=None):
            columns=2 if self.scrollers[0].canvas.winfo_width()>=900 else 1
            if columns==self.card_columns:return
            self.card_columns=columns
            for label in self.field_labels:label.configure(wraplength=180 if columns==2 else 110)
            for label in self.field_hints:label.configure(wraplength=260 if columns==2 else 150)
            self.entries['name'].configure(width=24 if columns==2 else 17)
            self.cards.columnconfigure(0,weight=1,uniform='cards')
            self.cards.columnconfigure(1,weight=1 if columns==2 else 0,uniform='cards'if columns==2 else '')
            self.card_stacks[0].grid(row=0,column=0,sticky='new',padx=(0,12)if columns==2 else 0)
            if columns==2:self.card_stacks[1].grid(row=0,column=1,sticky='new')
            else:self.card_stacks[1].grid_remove()
            for index,card in enumerate(self.spec_sections):
                card.columnconfigure(0,minsize=getattr(self,'label_column_width',164)if columns==2 else 110)
                card.panel.grid_forget()
                card.panel.grid(in_=self.card_stacks[index%columns],row=index//columns,column=0,sticky='ew',pady=(0,10))
            self.scrollers[0].resize()
        self.arrange_cards=arrange_cards
        self.scrollers[0].canvas.bind('<Configure>',arrange_cards,add='+');root.after_idle(arrange_cards)
        for k in ('capacity','factory_guns','factory_crew'):self.extra_vars[k].trace_add('write',lambda *args,key=k:self.sync_fit(key))
        for k in ('max_guns','max_crew'):self.vars[k].trace_add('write',lambda *args,key=k:self.sync_fit(key))
        self.availability_heading=ttk.Label(availability,text='Select an added ship to change its ports.',wraplength=340,font=('Segoe UI',12,'bold'));self.availability_heading.pack(anchor='w',pady=(0,10))
        graphics=section(art_page,'Artwork and ship description')
        ttk.Label(graphics,text='Reuse an original ship’s portrait, map/battle icons and description. Your specifications stay unchanged.',wraplength=340).pack(anchor='w')
        self.base_var=tk.StringVar();self.base_combo=ttk.Combobox(graphics,textvariable=self.base_var,state='disabled',width=28);self.base_combo.pack(fill='x',pady=(8,0))
        self.base_combo.bind('<<ComboboxSelected>>',lambda e:self.show_portrait())
        artwork=section(art_page,'Ship portrait')
        self.portrait_label=ttk.Label(artwork,text='Open a ROM to view its portrait.');self.portrait_label.pack(anchor='w')
        self.portrait_note=ttk.Label(artwork,text='',wraplength=340,foreground='#596579');self.portrait_note.pack(anchor='w',pady=6)
        self.import_portrait_button=ttk.Button(artwork,text='Import PNG',command=self.import_portrait,state='disabled');self.import_portrait_button.pack(anchor='w',pady=2)
        self.restore_portrait_button=ttk.Button(artwork,text='Restore portrait',command=self.restore_portrait,state='disabled');self.restore_portrait_button.pack(anchor='w',pady=2)
        ttk.Label(artwork,text='Converts to 64x48 pixels and the game’s 16 colors. Map and battle icons follow the original visual family.',wraplength=340).pack(anchor='w',pady=(6,0))
        unlock=section(availability,'Industry requirement')
        ttk.Label(unlock,text='Minimum industry to build this ship (new only)',wraplength=340).pack(anchor='w')
        self.industry_var=tk.StringVar();self.industry_entry=ttk.Entry(unlock,textvariable=self.industry_var,state='disabled',width=18);self.industry_entry.pack(anchor='w',pady=6)
        ttk.Label(unlock,text='0-1,000, in steps of 10. Applies to every selected port. Construction time follows hull strength and port industry.',wraplength=340,foreground='#596579').pack(anchor='w')
        locations=section(availability,'Shipyard locations')
        ttk.Label(locations,text='New-build locations only; used-ship rules stay unchanged. Click for one port; Ctrl-click for more. Fixed capitals cannot be developed.',wraplength=340).pack(anchor='w',pady=(0,6))
        self.port_summary=ttk.Label(locations,text='',wraplength=340);self.port_summary.pack(anchor='w',pady=(0,8))
        port_frame=ttk.Frame(locations);port_frame.pack(fill='both',expand=True)
        self.port_list=tk.Listbox(port_frame,selectmode='extended',exportselection=False,font=('Segoe UI',10),height=12,width=32);self.port_list.pack(side='left',fill='both',expand=True)
        self.port_list.bind('<<ListboxSelect>>',self.show_port_selection)
        scroll=ttk.Scrollbar(port_frame,command=self.port_list.yview);scroll.pack(side='right',fill='y');self.port_list.configure(yscrollcommand=scroll.set)
        fixes=ttk.Frame(self.scrollers[3].content,padding=16);fixes.pack(fill='both',expand=True)
        self.repair_var=tk.BooleanVar(value=True)
        self.repair_check=ttk.Checkbutton(fixes,text='Repair Safeguard',variable=self.repair_var,state='disabled')
        self.repair_check.pack(anchor='w',pady=(0,8))
        ttk.Label(fixes,text='Prevents excessive repair charges when ship stats are lowered and an existing save is loaded. Keeps original gold and lumber repair rates.',wraplength=340).pack(anchor='w')
        ttk.Label(fixes,text='Applies to the whole exported game. Enabled exports use a 4 MB ROM, including projects without added ships.',wraplength=340,foreground='#596579').pack(anchor='w',pady=(12,0))
        gameplay=ttk.Frame(self.scrollers[4].content,padding=16);gameplay.pack(fill='both',expand=True)
        self.fleet_var=tk.BooleanVar(value=False)
        self.fleet_check=ttk.Checkbutton(gameplay,text='Fleet Control (Experimental)',variable=self.fleet_var,state='disabled');self.fleet_check.pack(anchor='w',pady=(0,8))
        ttk.Label(gameplay,text='Control your mates’ ships in battle, with the camera following each ship’s turn. Press Select at the main battle command menu to toggle mate automation; press A to close the confirmation.',wraplength=340).pack(anchor='w')
        ttk.Label(gameplay,text='Full campaign compatibility is still being tested. Each battle starts in manual mode; your flagship stays manual and enemies keep their AI. Duel commands remain available. Enabled exports use 4 MB.',wraplength=340,foreground='#596579').pack(anchor='w',pady=(12,0))
        self.compact=None
        def resize_density(event):
            if event.widget!=root:return
            sidebar_width=max(210,min(420,int(event.width*.196)))if event.width>=1050 else 210
            self.sidebar.configure(width=sidebar_width)
            density='compact'if event.width<900 or event.height<620 else 'large'if event.width>=1500 and event.height>=900 else 'medium'
            if density==self.compact:return
            self.compact=density;compact=density=='compact';large=density=='large'
            self.label_column_width=190 if large else 164
            self.title_label.configure(font=('Segoe UI',14 if compact else 22 if large else 20,'bold'))
            self.title_label.configure(image=self.ui.icon('feather','#194c85',20 if compact else 32))
            self.build_label.configure(font=('Segoe UI',8 if compact else 10))
            top.configure(padding=(16,6 if compact else 12))
            self.source.configure(font=('Segoe UI',8 if compact else 10))
            self.status.configure(font=('Segoe UI',8 if compact else 10),padding=(16,4 if compact else 8))
            self.status.configure(image=self.ui.icon('stats','#64758c',14 if compact else 18))
            self.ships_heading.configure(font=('Segoe UI',10 if compact else 12,'bold'))
            self.list.configure(width=1,font=('Segoe UI',9 if compact else 11 if large else 10))
            style.configure('TButton',font=('Segoe UI',9 if compact else 11 if large else 10),padding=(5,2)if compact else (14,9))
            style.configure('Primary.TButton',padding=(10,4)if compact else (16,8))
            style.configure('Nav.TButton',font=('Segoe UI',8 if compact else 11),padding=(8,1)if compact else (16,10))
            style.configure('Tab.TButton',font=('Segoe UI',8 if compact else 12 if large else 11),padding=(4,7)if compact else (18,11))
            for i,button in enumerate(self.tab_buttons):button.configure(image=''if compact else self.ui.icon(('stats','calendar','image','wrench','game')[i],'#0869df'if i==self.notebook.index('current')else '#54647b'))
            for i,button in enumerate(self.toolbar_buttons):button.configure(image=''if compact else self.ui.icon(('folder','folder','save','export','help')[i],'#0869df'))
            for i,button in enumerate(self.nav_buttons):button.configure(image=self.ui.icon(('ship','person','captain')[i],'#194c85',16 if compact else 22))
            self.apply_button.configure(image=''if compact else self.ui.icon('check','white',22))
            self.restore_button.configure(image=''if compact else self.ui.icon('restore','#243c60',20))
            self.add_button.configure(image=''if compact else self.ui.icon('add','#0876e9',16))
            style.configure('Sidebar.TLabel',font=('Segoe UI',9 if compact else 11))
            for widget_style in ('TEntry','TSpinbox','TCombobox'):
                style.configure(widget_style,font=('Segoe UI',10 if compact else 12 if large else 11),padding=(5,3)if compact else (8,4)if large else (7,4))
            for key,entry in {**self.entries,**self.extra_entries}.items():
                entry.configure(font=('Segoe UI',10 if compact else 12 if large else 11))
                if key!='name':entry.configure(width=12 if compact else 18 if large else 16)
            self.search_entry.configure(font=('Segoe UI',9 if compact else 11))
            style.configure('Card.TLabel',font=('Segoe UI',10 if compact else 12 if large else 11))
            style.configure('Hint.Card.TLabel',font=('Segoe UI',9 if not large else 10))
            style.configure('CardTitle.TLabel',font=('Segoe UI',11 if compact else 12,'bold'))
            self.identity_card.configure(padding=(18,12,18,40)if large else (18,12))
            for card in self.spec_sections:card.columnconfigure(0,minsize=self.label_column_width if self.card_columns==2 else 110)
        root.bind('<Configure>',resize_density,add='+')
        def sidebar_colors(widget):
            for child in widget.winfo_children():
                if child.winfo_class()=='TLabel'and not child.cget('style'):child.configure(style='Sidebar.TLabel')
                elif child.winfo_class()=='TFrame'and not child.cget('style'):child.configure(style='SidebarContent.TFrame')
                sidebar_colors(child)
        sidebar_colors(left)
        for card in self.spec_sections+[graphics,artwork,unlock,locations]:
            def whiten(widget):
                for child in widget.winfo_children():
                    if child.winfo_class()=='TLabel'and not child.cget('style'):child.configure(style='Card.TLabel')
                    elif child.winfo_class()=='TFrame'and not child.cget('style'):child.configure(style='Card.TFrame')
                    whiten(child)
            whiten(card)
        for button in (self.add_button,self.remove_button,self.apply_button,self.restore_button):button.configure(state='disabled')
        # Establish a predictable first view after Tk has mapped and sized the
        # cards. Subsequent user scrolling and tab positions are left alone.
        def initial_view():
            self.card_columns=None;self.arrange_cards();root.update_idletasks()
            for scroll in self.scrollers:
                scroll.resize();scroll.canvas.xview_moveto(0);scroll.canvas.yview_moveto(0)
        root.after(100,initial_view)

    def fail(self,e):messagebox.showerror('Check your values',str(e),parent=self.root)
    def open_search(self):
        self.search_entry.focus_set();self.search_entry.selection_range(0,'end')
        return 'break'
    def clear_search(self):
        self.search_var.set('');self.list.focus_set()
        if self.selected in self.ship_rows:self.list.see(self.ship_rows.index(self.selected))
        return 'break'
    def refresh_list(self):
        self.loading=True;view=self.list.yview();self.list.delete(0,'end');self.ship_rows=[]
        if self.project:
            for i,s in enumerate(self.project.ships):
                if self.search_var.get().strip().casefold()not in s['name'].casefold():continue
                changed=i>=25 or i in self.project.portraits or any(s[k]!=self.project.original[i][k]for k in EDIT_FIELDS)or self.project.original_availability[i]!=self.project.stock_availability[i]
                self.ship_rows.append(i)
                self.list.insert('end',f'{i+1:02d}  {s["name"]}'+('  NEW'if i>=25 else '  *'if changed else ''))
        if self.selected in self.ship_rows:self.list.selection_set(self.ship_rows.index(self.selected))
        if view:self.list.yview_moveto(view[0])
        self.loading=False
    def show(self,i):
        self.selected=i;s=self.project.ships[i]
        for button in (self.add_button,self.apply_button,self.restore_button):button.configure(state='normal')
        self.remove_button.configure(state='normal'if i>=25 else 'disabled')
        if self.displayed_ship!=i:
            for scroll in self.scrollers:scroll.canvas.xview_moveto(0);scroll.canvas.yview_moveto(0)
            self.displayed_ship=i
        self.fit_loading=True
        self.repair_check.configure(state='normal');self.repair_var.set(self.project.repair_safeguard)
        self.fleet_check.configure(state='normal');self.fleet_var.set(self.project.fleet_control)
        self.heading.configure(text=s['name'])
        self.graphics_heading.configure(text=s['name']+' — Graphics')
        self.record_heading.configure(text=f'Ship ID: {i+1:02d}')
        family=self.project.original[s['base_hull']if i>=25 else i]['name']
        self.quick_vars['index'].set(f'{i+1:02d} (0x{i:02X})')
        self.quick_vars['kind'].set('Added ship'if i>=25 else 'Original ship')
        self.quick_vars['family'].set(family)
        for k in FIELDS:self.entries[k].configure(state='normal');self.vars[k].set(str(s[k]/10000).rstrip('0').rstrip('.')if k=='price_gold'else str(s[k]))
        extra=i>=25
        self.fixed.configure(text='Editable for added ships. Cargo is calculated automatically.'if extra else 'Original starting guns and crew are read-only.')
        for k,v in self.extra_vars.items():
            v.set(str(s['capacity']-s['max_guns']-s['max_crew'])if k=='yard_cargo'else str(s[k]))
            state='readonly'if k in ('factory_cargo','yard_cargo')or(not extra and k in ('factory_guns','factory_crew'))else 'normal'
            self.extra_entries[k].configure(state=state)
        self.fit_loading=False
        self.availability_heading.configure(text=f'New-build availability: {s["name"]}')
        self.base_combo.configure(values=[f'{n:02d} - {r["name"]}'for n,r in enumerate(self.project.original)],state='readonly'if extra else 'disabled')
        self.base_combo.current(s['base_hull']if extra else i)
        self.import_portrait_button.configure(state='normal');self.show_portrait()
        offer=s if extra else self.project.original_availability[i]
        self.industry_var.set(str(offer['industry']));self.industry_entry.configure(state='normal')
        self.port_list.configure(state='normal');self.port_list.delete(0,'end')
        for p in ports(self.project.rom):self.port_list.insert('end',f'{p["name"]} — industry {p["industry"]}'+(' (fixed capital)'if p['capital']else ''))
        for p in offer['ports']:self.port_list.selection_set(p)
        self.show_port_selection()
        self.update_status()
    def show_portrait(self):
        if not self.project or self.selected is None:return
        i=self.selected
        raw=self.project.portrait_raw(i)
        if i>=25 and i not in self.project.portraits and self.base_combo.current()>=0:
            raw=portraits.original_raw(self.project.rom,self.base_combo.current())
        self.portrait_photo=ImageTk.PhotoImage(portraits.image(raw,self.project.rom,3),master=self.root)
        self.portrait_label.configure(image=self.portrait_photo,text='')
        custom=i in self.project.portraits
        self.portrait_note.configure(text='Custom portrait — exact game pixels.'if custom else 'Original portrait — exact game pixels.')
        self.restore_portrait_button.configure(state='normal'if custom else 'disabled')
    def import_portrait(self):
        if not self.project or self.selected is None:return
        path=filedialog.askopenfilename(title='Import ship portrait',filetypes=[('PNG image','*.png')],parent=self.root)
        if not path:return
        try:
            raw,size=portraits.convert_png(path,self.project.rom)
            ship_id=self.selected
            preview=tk.Toplevel(self.root);preview.title('Portrait preview');preview.transient(self.root)
            preview.geometry(f'+{self.root.winfo_rootx()+30}+{self.root.winfo_rooty()+30}')
            frame=ttk.Frame(preview,padding=16);frame.pack(fill='both',expand=True)
            ttk.Label(frame,text=self.project.ships[ship_id]['name'],font=('Segoe UI',12,'bold')).pack(anchor='w')
            photo=ImageTk.PhotoImage(portraits.image(raw,self.project.rom,5),master=preview)
            ttk.Label(frame,image=photo).pack(pady=10)
            ttk.Label(frame,text=f'Source: {size[0]}x{size[1]} → game: 64x48, 16 colors.\nThis preview shows exactly what will be installed.\nTransparent pixels use the game’s background color.',wraplength=320).pack(anchor='w')
            actions=ttk.Frame(frame);actions.pack(fill='x',pady=(12,0))
            def accept():
                self.project.set_portrait(ship_id,raw);preview.destroy()
                self.show_portrait();self.refresh_list();self.update_status()
            ttk.Button(actions,text='Use portrait',command=accept).pack(side='left',padx=(0,8))
            ttk.Button(actions,text='Cancel',command=preview.destroy).pack(side='left')
            preview.update_idletasks();preview.grab_set();preview.focus_set();self.root.wait_window(preview)
        except Exception as e:self.fail(e)
    def restore_portrait(self):
        if not self.project or self.selected is None:return
        self.project.restore_portrait(self.selected);self.show_portrait();self.refresh_list();self.update_status()
    def show_port_selection(self,event=None):
        selected=self.port_list.curselection()
        names=[ports(self.project.rom)[p]['name']for p in selected]if self.project else []
        self.port_summary.configure(text='Selected ports: '+(', '.join(names)if names else 'none'))
    def sync_fit(self,changed):
        if self.fit_loading or self.fit_syncing or self.project is None:return
        try:
            used=int(self.extra_vars['factory_guns'].get())+int(self.extra_vars['factory_crew'].get())
            maximum=int(self.vars['max_guns'].get())+int(self.vars['max_crew'].get())
            self.fit_syncing=True
            total=int(self.extra_vars['capacity'].get())
            self.extra_vars['factory_cargo'].set(str(total-used))
            self.extra_vars['yard_cargo'].set(str(total-maximum))
        except ValueError:pass
        finally:self.fit_syncing=False
    def commit(self):
        if self.project is None or self.selected is None:return
        values={}
        for k in FIELDS:
            value=self.vars[k].get().strip()
            if k=='name':values[k]=value
            elif k=='price_gold':values[k]=price_from_bars(value)
            else:
                try:values[k]=int(value)
                except ValueError:raise ValueError(f'{LABELS[k]} needs a whole number.')
        for k,v in self.extra_vars.items():
            if k=='capacity'or(self.selected>=25 and k in ('factory_guns','factory_crew')):
                try:values[k]=int(v.get())
                except ValueError:raise ValueError(k.replace('_',' ')+' needs a whole number.')
        if self.selected is not None:
            try:values['industry']=int(self.industry_var.get())
            except ValueError:raise ValueError('Industry needs a whole number.')
            if self.selected>=25:values['base_hull']=self.base_combo.current()
            values['ports']=list(self.port_list.curselection())
        self.project.update(self.selected,values)
        self.project.repair_safeguard=self.repair_var.get();self.project.fleet_control=self.fleet_var.get()
    def update_status(self):
        n=len({c['id']for c in self.project.changes()}|{c['id']for c in self.project.availability_changes()}|{i for i in self.project.portraits if i<25})if self.project else 0
        added=len(self.project.ships)-25 if self.project else 0
        self.status.configure(text=f'Edited originals: {n}   |   Added ships: {added}/5   |   Source ROM unchanged')
    def pick(self,event=None):
        if self.loading or not self.project or not self.list.curselection():return
        index=self.ship_rows[self.list.curselection()[0]]
        try:self.commit()
        except Exception as e:
            self.fail(e);self.list.selection_clear(0,'end')
            if self.selected in self.ship_rows:self.list.selection_set(self.ship_rows.index(self.selected))
            return
        self.selected=index;self.refresh_list();self.show(index)
    def apply(self):
        try:self.commit();self.refresh_list();self.show(self.selected)if self.project else None
        except Exception as e:self.fail(e)
    def allow_replace(self):
        if not self.project:return True
        try:self.commit()
        except Exception as e:self.fail(e);return False
        return (not self.project.changes()and not self.project.availability_changes()and not self.project.portraits and len(self.project.ships)==25 and self.project.repair_safeguard and not self.project.fleet_control)or messagebox.askyesno('Leave this project?','Save your project first if you want to keep these edits. Continue?',parent=self.root)
    def open_rom(self):
        path=filedialog.askopenfilename(title='Open original USA ROM',filetypes=[('SNES ROM or ZIP','*.sfc *.smc *.zip'),('All files','*.*')])
        if not path or not self.allow_replace():return
        try:
            project=ShipProject(path);self.project=project;self.selected=0;self.source.configure(text='Stock USA ROM verified: '+Path(path).name+(' (copier header detected)'if project.header else ''))
            self.source.configure(image=self.ui.icon('check','#12a16c',20),compound='left')
            self.refresh_list();self.show(0)
        except Exception as e:self.fail(e)
    def open_project(self):
        if not self.project:messagebox.showinfo('Open the game first','Open the original USA ROM, then open your project.',parent=self.root);return
        path=filedialog.askopenfilename(title='Open ship project',filetypes=[('Ship projects','*.json')])
        if not path or not self.allow_replace():return
        try:self.project.load_project(path);self.selected=min(self.selected,len(self.project.ships)-1);self.refresh_list();self.show(self.selected)
        except Exception as e:self.fail(e)
    def save_project(self):
        if not self.project:return
        try:
            self.commit();path=filedialog.asksaveasfilename(title='Save ship project',defaultextension='.json',initialfile='My Ship Mod.nhmod.json',filetypes=[('Ship project','*.json')])
            if path:self.project.save_project(path);self.refresh_list();self.update_status()
        except Exception as e:self.fail(e)
    def export(self):
        if not self.project:return
        try:
            self.commit();path=filedialog.asksaveasfilename(title='Export a NEW game file',defaultextension='.sfc',initialfile='New Horizons - My Ships.sfc',filetypes=[('Patched SNES ROM','*.sfc')])
            if not path:return
            self.project.export(path);self.refresh_list();self.update_status()
            messagebox.showinfo('Export complete','Created the new .sfc, .ips and .changes.json files.\n\nThe IPS applies to the original unheadered USA ROM. The exported SFC is already patched. Test your changes in your emulator.',parent=self.root)
        except Exception as e:self.fail(e)
    def restore(self):
        if not self.project or self.selected is None:return
        self.project.restore_portrait(self.selected)
        if self.selected>=25:
            s=self.project.ships[self.selected];base=dict(self.project.original[s['base_hull']])
            base.update(id=s['id'],name=s['name'],base_hull=s['base_hull'],ports=s['ports'],industry=s['industry'])
            base['max_crew']=max(base['max_crew'],((base['factory_crew']+9)//10)*10)
            base['capacity']=base['factory_guns']+base['factory_crew']+base['factory_cargo']
            self.project.ships[self.selected]=base;self.refresh_list();self.show(self.selected);return
        import copy
        self.project.original_availability[self.selected]=copy.deepcopy(self.project.stock_availability[self.selected])
        self.project.ships[self.selected]=dict(self.project.original[self.selected]);self.refresh_list();self.show(self.selected)
    def add(self):
        if not self.project:return
        try:
            self.commit();base=self.selected if self.selected<25 else self.project.ships[self.selected]['base_hull']
            self.selected=self.project.add_ship(base);self.search_var.set('');self.refresh_list();self.list.see(self.ship_rows.index(self.selected));self.show(self.selected)
        except Exception as e:self.fail(e)
    def remove(self):
        if not self.project or self.selected is None:return
        try:self.project.remove_ship(self.selected);self.selected=min(self.selected,len(self.project.ships)-1);self.refresh_list();self.show(self.selected)
        except Exception as e:self.fail(e)
    def help(self):
        messagebox.showinfo('Version '+TOOL_VERSION+' help','Open the ORIGINAL USA ROM. Select an original ship, then Add ship to create an independent hull. Add up to five.\n\nSet stats and factory fit on Specifications. Pick ports and industry on Availability for original or added ships. Original new-build changes do not affect used offers. Import PNG on Graphics converts and previews custom portraits for original or added ships. Portraits are embedded in saved projects. Restore portrait resets only the picture. Map/battle icons and descriptions follow the original visual family. Starting port industry is shown; unreachable capital offers are rejected. Remaining capacity becomes cargo.\n\nFixes: Repair Safeguard prevents overcharges after lowering stats. Its setting is saved in the project; enabled exports use 4 MB.\n\nSave a project, then export to a new SFC. The IPS always applies to the original headerless ROM. Version0.1 projects still load.\n\nFleet Control on Gameplay adds manual mate turns, camera focus and a Select automation toggle. Other prices, materials and bargaining follow stock rules. New ships can appear occasionally in used stock at eligible ports; enemy fleets are not assigned new models. Reused graphics and descriptions are intentional.\n\nUse a normal in-game save after a cold emulator boot, not old save states. Once you start playing, keep new-ship order/IDs stable: removing or reordering added ships can reinterpret hull IDs in that mod’s saves. Your existing campaign mod and its saves are not converted by this tool.',parent=self.root)
    def close(self):
        if self.allow_replace():self.root.destroy()

def main():
    try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:pass
    if len(sys.argv)==5 and sys.argv[1]=='--workflow-test'and sys.argv[3]=='--report':
        from ui_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--self-test'and sys.argv[3]=='--report':
        report=Path(sys.argv[4]);report.parent.mkdir(parents=True,exist_ok=True);root=None
        try:
            root=tk.Tk();root.withdraw();editor=Editor(root)
            assert root.title()=='New Horizons Editor v'+TOOL_VERSION
            editor.project=ShipProject(sys.argv[2]);editor.selected=13;editor.refresh_list();editor.show(13)
            root.update_idletasks();assert editor.list.size()==25
            editor.vars['max_guns'].set('60');editor.vars['price_gold'].set('2.5');editor.commit()
            editor.show(3);editor.extra_vars['capacity'].set('600');editor.commit()
            for base in (6,10,13,3,16):editor.project.add_ship(base)
            editor.selected=29;editor.refresh_list();editor.show(29);root.update_idletasks();assert editor.list.size()==30
            editor.vars['name'].set('Fifth Test Ship');editor.industry_var.set('900')
            editor.port_list.selection_clear(0,'end');editor.port_list.selection_set(31);editor.commit()
            exported=report.parent/'Self Test Mod.sfc';result=editor.project.export(exported)
            data=exported.read_bytes();assert len(data)==0x400000 and data[0x2100fa+4*12]==90 and data[0x214000+31*5+4]==1
            assert int.from_bytes(data[0x8cbb6+3*25+23:0x8cbb6+3*25+25],'little')==420
            report.write_text(json.dumps(dict(status='PASS',build_id=BUILD_ID,window_title=root.title(),ships=30,added_ships=5,tk_widgets_loaded=True,
                sloop_guns=editor.project.ships[13]['max_guns'],price_gold=editor.project.ships[13]['price_gold'],buss_cargo=420,
                exported_rom_sha256=result['output_sha256']),indent=2))
        except Exception as e:
            report.write_text(json.dumps(dict(status='FAIL',error=str(e)),indent=2));raise
        finally:
            if root is not None:root.destroy()
        return
    root=tk.Tk();Editor(root);root.mainloop()

if __name__=='__main__':main()
