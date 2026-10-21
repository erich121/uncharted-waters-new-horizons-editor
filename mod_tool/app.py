"""Windows editor for25 original ships and up to ten additional hulls."""
import ctypes,sys,json,copy
import diagnostics
if __name__=='__main__':diagnostics.initialize()
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from backend import ShipProject,FIELDS,EDIT_FIELDS,ports,price_from_bars,TOOL_VERSION
from PIL import ImageTk
import portraits
from ui_theme import EditorTheme, SectionCard

LABELS={'name':'Ship name','hull':'Hull strength','turning':'Turning','power':'Sailing power',
    'max_guns':'Maximum guns','min_crew':'Minimum sailors','max_crew':'Maximum crew spaces','price_gold':'Base price in gold bars'}
BUILD_ID='release'
CHANGE_ORANGE='#ef7800'

class ScrollableWindow(ttk.Frame):
    """Keep the whole editor reachable on small or scaled Windows displays."""
    def __init__(self,root,fit_width=False,natural_height=False):
        self.fit_width=fit_width;self.natural_height=natural_height
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
        owner.bind_all('<Button-4>',self.wheel,add='+')
        owner.bind_all('<Button-5>',self.wheel,add='+')
        owner.bind('<FocusIn>',self.focus_visible,add='+')

    def _vertical(self,*args):self.vertical.set(*args)
    def _horizontal(self,*args):
        self.horizontal.set(*args)
        if float(args[1])-float(args[0])>=0.999:self.horizontal.grid_remove()
        else:self.horizontal.grid()
    def resize(self,event=None):
        at_top=self.canvas.yview()[0]<=0.0001
        at_bottom=not at_top and self.canvas.yview()[1]>=0.9999
        at_left=self.canvas.xview()[0]<=0.0001
        width=self.canvas.winfo_width()if self.fit_width else max(self.content.winfo_reqwidth(),self.canvas.winfo_width())
        height=max(self.content.winfo_reqheight(),self.canvas.winfo_height())
        # Let changing World cards resize the embedded frame naturally. A fixed
        # window height can suppress Configure events when requested height grows.
        self.canvas.itemconfigure(self.window,width=width,height=0 if self.natural_height else height)
        self.canvas.configure(scrollregion=(0,0,width,height))
        if at_top:self.canvas.yview_moveto(0)
        elif at_bottom:self.canvas.yview_moveto(1)
        if at_left:self.canvas.xview_moveto(0)
    def wheel(self,event):
        target=str(event.widget);content=str(self.content)
        # The uncovered viewport is a Canvas, not a descendant of its content.
        # Wide World panels leave this surface exposed beside/between cards.
        if event.widget not in (self.canvas,self.vertical,self.horizontal)and target!=content and not target.startswith(content+'.'):return
        if event.widget.winfo_class()=='Listbox':return
        steps=-1 if getattr(event,'num',None)==4 else 1 if getattr(event,'num',None)==5 else -int(event.delta/120)if abs(event.delta)>=120 else (-1 if event.delta>0 else 1)
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
        total_h=int(float(self.canvas.cget('scrollregion').split()[3]))
        for start,size,total,viewport,view,move in [
            (left,widget.winfo_width(),total_w,self.canvas.winfo_width(),self.canvas.xview,self.canvas.xview_moveto),
            (top,widget.winfo_height(),total_h,self.canvas.winfo_height(),self.canvas.yview,self.canvas.yview_moveto)]:
            origin=view()[0]*total
            if start<origin:move(max(0,start-8)/total)
            elif start+size>origin+viewport:move(max(0,start+size+8-viewport)/total)

class Editor:
    def __init__(self,root):
        self.auto_loading=False;self.auto_timer=None
        self.section='ships';self.data_type='ships';self.mate_selected=None;self.captain_selected=None;self.mate_rows=[];self.browser_searches={'ships':'','mates':'','captains':''};self.browser_views={'ships':0.0,'mates':0.0,'captains':0.0}
        self.root=root;self.project=None;self.selected=None;self.loading=False;self.displayed_ship=None
        diagnostics.attach_editor(self)
        root.title('New Horizons Editor v'+TOOL_VERSION)
        from app_branding import Branding
        self.branding=Branding(root)
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
        # Remove value-changing class bindings before window-scroll handlers run.
        # This also covers controls created later in dialogs.
        for control in ('TSpinbox','Spinbox','TCombobox'):
            for event in ('<MouseWheel>','<Button-4>','<Button-5>'):root.unbind_class(control,event)
        self.ui.surface('ShipOverview.TFrame','ShipOverview','white','#d5dfed',8)
        style.configure('ShipHint.Card.TLabel',foreground='#52647b',font=('Segoe UI',10),background='white')
        for base in ('Ship.TEntry','Ship.TSpinbox'):style.configure(base,padding=(7,1))
        for name in ('Changed.Nav.TButton','Selected.Changed.Nav.TButton'):
            style.configure(name,foreground=CHANGE_ORANGE,background='#fff0df')
            style.map(name,foreground=[('active',CHANGE_ORANGE)],background=[('active','#ffe2c0')])
        for base in ('TEntry','TSpinbox','Ship.TEntry','Ship.TSpinbox','TCombobox','TCheckbutton','Card.TCheckbutton'):
            style.configure('Changed.'+base,foreground=CHANGE_ORANGE)
            style.map('Changed.'+base,foreground=[('disabled',CHANGE_ORANGE),('readonly',CHANGE_ORANGE)])
        top=ttk.Frame(root,padding=(16,12));top.pack(fill='x')
        title=ttk.Frame(top);title.pack(fill='x')
        self.title_label=ttk.Label(title,text='New Horizons Editor',image=self.branding.photo(32),compound='left',font=('Segoe UI',20,'bold'),wraplength=420);self.title_label.pack(side='left',anchor='w')
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
        self.status=ttk.Label(status_panel,text='Open a stock USA ROM to begin.',style='Status.TLabel',image=self.ui.icon('stats','#64758c',18),compound='left',padding=(16,3),wraplength=580);self.status.pack(side='left',fill='x',expand=True)
        ttk.Label(status_panel,text='Orange = differs from original game',foreground=CHANGE_ORANGE,style='Status.TLabel').pack(side='right',padx=8)
        body=ttk.Frame(root,padding=(16,0,16,0));body.pack(fill='both',expand=True)
        left=ttk.Frame(body,padding=(12,10),style='Sidebar.TFrame',width=320);self.sidebar=left;left.pack(side='left',fill='y',padx=(0,10));left.pack_propagate(False)
        self.sections_label=ttk.Label(left,text='Sections',foreground='#546783');self.sections_label.pack(anchor='w',pady=(0,3))
        self.gameplay_nav=ttk.Button(left,text='Gameplay',image=self.ui.icon('game','#566579'),compound='left',style='Nav.TButton',command=lambda:self.switch_section('gameplay'));self.gameplay_nav.pack(fill='x',pady=1)
        self.world_nav=ttk.Button(left,text='World',image=self.ui.icon('anchor','#566579'),compound='left',style='Nav.TButton',command=lambda:self.switch_section('world'));self.world_nav.pack(fill='x',pady=1)
        self.library_nav=ttk.Button(left,text='Library',image=self.ui.icon('folder','#566579'),compound='left',style='Nav.TButton',command=lambda:self.switch_section('library'));self.library_nav.pack(fill='x',pady=0)
        nav=ttk.Frame(left);nav.pack(fill='x',pady=1)
        self.nav_strip=tk.Frame(nav,background='#0869df',width=3);self.nav_strip.pack(side='left',fill='y')
        ships_nav=ttk.Button(nav,text='Ships',image=self.ui.icon('ship'),compound='left',style='Selected.Nav.TButton',takefocus=False,command=lambda:self.switch_data('ships'));ships_nav.pack(side='left',fill='x',expand=True)
        mates_nav=ttk.Button(left,text='Mates',image=self.ui.icon('person','#566579'),compound='left',style='Nav.TButton',command=lambda:self.switch_data('mates'));mates_nav.pack(fill='x',pady=1)
        captains_nav=ttk.Button(left,text='Fleet Captains',image=self.ui.icon('captain','#566579'),compound='left',style='Nav.TButton',command=lambda:self.switch_data('captains'));captains_nav.pack(fill='x',pady=0)
        self.characters_nav=ttk.Button(left,text='Characters',image=self.ui.icon('person','#566579'),compound='left',style='Nav.TButton',command=lambda:self.switch_section('characters'))
        self.characters_nav.pack(fill='x',before=mates_nav)
        self.discoveries_nav=ttk.Button(left,text='Discoveries',image=self.ui.icon('anchor','#566579'),compound='left',style='Nav.TButton',command=lambda:self.switch_section('discoveries'))
        self.discoveries_nav.pack(fill='x',before=self.characters_nav)
        self.library_nav.pack_configure(after=captains_nav)
        self.nav_buttons=[ships_nav,mates_nav,captains_nav]
        self.section_buttons=dict(gameplay=self.gameplay_nav,world=self.world_nav,ships=ships_nav,discoveries=self.discoveries_nav,characters=self.characters_nav,mates=mates_nav,captains=captains_nav,library=self.library_nav)
        for key,button in self.section_buttons.items():
            button.bind('<Button-3>',lambda event,section=key:self.section_menu(event,section))
        self.nav_separator=ttk.Separator(left);self.nav_separator.pack(fill='x',pady=(4,6))
        self.browser_controls=ttk.Frame(left,style='SidebarContent.TFrame');self.browser_controls.pack(fill='both',expand=True)
        browser=self.browser_controls
        remove=ttk.Frame(browser);remove.pack(side='bottom',fill='x',pady=(8,0))
        self.remove_button=ttk.Button(remove,text='Remove added ship',command=self.remove);self.remove_button.pack(fill='x')
        # This browser can later display character records without adding empty
        # categories to the working ship editor today.
        self.browser=left;self.ship_rows=[];self.search_var=tk.StringVar()
        list_title=ttk.Frame(browser);list_title.pack(fill='x',pady=(0,6))
        self.ships_heading=ttk.Label(list_title,text='Ships',font=('Segoe UI',12,'bold'));self.ships_heading.pack(side='left')
        self.add_button=ttk.Button(list_title,text='Add ship (up to 10)',command=self.add,image=self.ui.icon('add','#0876e9',16),compound='left');self.add_button.pack(side='right',padx=(8,0))
        self.search_frame=ttk.Frame(browser);self.search_frame.pack(fill='x',pady=(0,6))
        ttk.Label(self.search_frame,text='Search').pack(side='left',padx=(0,6))
        self.search_entry=ttk.Entry(self.search_frame,textvariable=self.search_var,width=18)
        self.search_entry.configure(font=('Segoe UI',10))
        self.search_entry.pack(side='left',fill='x',expand=True)
        self.search_var.trace_add('write',lambda *args:self.refresh_list())
        self.search_entry.bind('<Escape>',lambda e:self.clear_search())
        root.bind('<Control-f>',lambda e:self.open_search())
        ship_frame=ttk.Frame(browser);ship_frame.pack(fill='both',expand=True)
        self.list=tk.Listbox(ship_frame,width=27,height=25,font=('Segoe UI',10),exportselection=False,activestyle='none',
            background='white',foreground='black',selectbackground='#205b9b',selectforeground='white')
        self.list.pack(side='left',fill='both',expand=True);self.list.bind('<<ListboxSelect>>',self.pick)
        ship_scroll=ttk.Scrollbar(ship_frame,command=self.list.yview);ship_scroll.pack(side='right',fill='y');self.list.configure(yscrollcommand=ship_scroll.set)
        self.settings_area=ttk.Frame(body);self.settings_area.pack(side='left',fill='both',expand=True)
        settings=ttk.Frame(self.settings_area);self.ship_settings=settings;settings.pack(fill='both',expand=True)
        actions=ttk.Frame(settings);actions.pack(side='bottom',fill='x',pady=(8,0))
        self.apply_button=ttk.Button(actions,text='Apply ship changes',command=self.apply,style='Primary.TButton',image=self.ui.icon('check','white',22),compound='left')
        ttk.Label(actions,text='Changes apply automatically',foreground='#6e7f98').grid(row=0,column=0,sticky='w',padx=(0,12))
        self.restore_button=ttk.Button(actions,text='Restore selected ship',command=self.restore,image=self.ui.icon('restore','#243c60',20),compound='left');self.restore_button.grid(row=0,column=1,sticky='w',pady=2)
        def arrange_actions(event):
            narrow=230+self.restore_button.winfo_reqwidth()+8>event.width
            self.restore_button.grid(row=1 if narrow else 0,column=0 if narrow else 1,sticky='w',pady=2)
        actions.bind('<Configure>',arrange_actions)
        self.actions_frame=actions
        self.custom_ships_var=tk.BooleanVar(value=False)
        self.custom_ships_box=ttk.Checkbutton(settings,text='Use custom values',variable=self.custom_ships_var,command=self.toggle_custom_ships,state='disabled')
        self.custom_ships_box.pack(anchor='w',pady=(8,10))
        self.tab_bar=ttk.Frame(settings);self.tab_bar.pack(fill='x')
        notebook=ttk.Notebook(settings,style='Editor.TNotebook');self.notebook=notebook;notebook.pack(fill='both',expand=True)
        spec_tab=ttk.Frame(notebook);port_tab=ttk.Frame(notebook);art_tab=ttk.Frame(notebook);fix_tab=ttk.Frame(notebook)
        notebook.add(spec_tab,text='Specifications');notebook.add(port_tab,text='Availability');notebook.add(art_tab,text='Graphics');notebook.add(fix_tab,text='Fixes')
        self.tab_buttons=[];self.tab_lines=[]
        for index,(label,symbol)in enumerate((('Specifications','stats'),('Availability','calendar'),('Graphics','image'),('Fixes','wrench'))):
            tab=ttk.Frame(self.tab_bar);tab.pack(side='left')
            button=ttk.Button(tab,text=label,image=self.ui.icon(symbol,'#54647b'),compound='left',style='Tab.TButton',command=lambda i=index:notebook.select(i))
            button.pack(fill='x');self.tab_buttons.append(button)
            underline=tk.Frame(tab,height=3,background='#f5f7fb');underline.pack(fill='x');self.tab_lines.append(underline)
        self.scrollers=[ScrollableWindow(tab,fit_width=True,natural_height=True)for tab in (spec_tab,port_tab,art_tab,fix_tab)];self.scroll=self.scrollers[0]
        def switch_tab(event):
            scroll=self.scrollers[notebook.index('current')]
            if self.section=='ships':self.scroll=scroll
            for i,button in enumerate(self.tab_buttons):
                active=i==notebook.index('current');button.configure(style='Active.Tab.TButton'if active else 'Tab.TButton')
                button.configure(image=''if getattr(self,'compact',None)=='compact'else self.ui.icon(('stats','calendar','image','wrench','game')[i],'#0869df'if active else '#54647b'))
                self.tab_lines[i].configure(background='#0869df'if active else '#f5f7fb')
            # Invalidate the canvas item after tab mapping so Tk remaps its child.
            def remap():
                scroll.canvas.move(scroll.window,1,0);scroll.canvas.move(scroll.window,-1,0)
                scroll.resize()
            root.after_idle(remap)
        notebook.bind('<<NotebookTabChanged>>',switch_tab)
        right=ttk.Frame(self.scrollers[0].content,padding=12);right.pack(fill='both',expand=True)
        availability=ttk.Frame(self.scrollers[1].content,padding=12);availability.pack(fill='both',expand=True)
        art_page=ttk.Frame(self.scrollers[2].content,padding=12);art_page.pack(fill='both',expand=True)
        self.graphics_heading=ttk.Label(art_page,text='Ship graphics',font=('Segoe UI',15,'bold'));self.graphics_heading.pack(anchor='w',pady=(0,12))
        self.ship_overview=ttk.Frame(right,style='ShipOverview.TFrame',padding=14)
        self.ship_overview.pack(fill='x',pady=(0,12))
        self.spec_portrait=ttk.Label(self.ship_overview,text='Ship portrait',style='Card.TLabel',anchor='center',width=16)
        self.spec_portrait.grid(row=0,column=0,rowspan=2,sticky='nw',padx=(0,16))
        self.ship_intro=ttk.Frame(self.ship_overview,style='Card.TFrame')
        self.ship_intro.grid(row=0,column=1,sticky='nw')
        self.heading=ttk.Label(self.ship_intro,text='Choose a ship',style='Card.TLabel',font=('Segoe UI',19,'bold'));self.heading.pack(anchor='w')
        self.record_heading=ttk.Label(self.ship_intro,text='Open a stock ROM to begin.',style='ShipHint.Card.TLabel');self.record_heading.pack(anchor='w',pady=(4,0))
        self.ship_family=ttk.Label(self.ship_intro,text='Portraits and icons follow the visual family.',style='ShipHint.Card.TLabel')
        self.ship_family.pack(anchor='w',pady=(2,0))
        self.ship_overview.columnconfigure(1,weight=1)
        self.cards=ttk.Frame(right);self.cards.pack(fill='x');self.spec_sections=[];self.card_columns=None;self.field_labels=[];self.field_hints=[];self.ship_fields=[];self.card_layout=None
        self.card_stacks=[ttk.Frame(self.cards)for _ in range(2)]
        for stack in self.card_stacks:stack.columnconfigure(0,weight=1)
        self.vars={};self.entries={};self.extra_vars={};self.extra_entries={}
        self.fit_loading=False;self.fit_syncing=False
        def section(parent,title):
            symbol={'Name and price':'coins','Hull and handling':'anchor','Guns and crew limits':'guns','Quick info':'info','Capacity and calculated cargo':'ship','Starting equipment':'wrench','Industry requirement':'wrench','Shipyard locations':'anchor','Shipyard description':'info','Repair protection':'wrench'}.get(title,'image')
            panel=SectionCard(self.cards if parent==right else parent,'Capacity and cargo'if title=='Capacity and calculated cargo'else title,clean=True)
            panel.title_label.configure(image=self.ui.icon(symbol),compound='left')
            frame=panel.body;frame.configure(padding=(12,2))
            frame.panel=panel
            if parent==right:self.spec_sections.append(frame)
            else:panel.pack(fill='x',pady=(0,12))
            frame.columnconfigure(2,weight=1)
            return frame
        def field(frame,row,key,title,hint,extra=False):
            label=ttk.Label(frame,text=title,wraplength=136,style='Card.TLabel',font=('Segoe UI',11));label.grid(row=row*2,column=0,sticky='w',padx=(0,12));self.field_labels.append(label)
            v=tk.StringVar()
            if key=='name':e=ttk.Entry(frame,textvariable=v,width=17,state='disabled')
            else:
                bounds={'price_gold':(.001,32,.001),'hull':(1,100,1),'power':(1,100,1),'turning':(1,100,1),'max_guns':(0,200,1),'factory_guns':(0,200,1),'factory_crew':(1,500,1),'max_crew':(10,500,10),'min_crew':(1,255,1),'capacity':(1,2000,1)}
                low,high,step=bounds.get(key,(0,2000,1))
                # Computed cargo remains a read-only display rather than a spinner.
                e=ttk.Entry(frame,textvariable=v,width=14,state='disabled')if key in ('yard_cargo','factory_cargo')else ttk.Spinbox(frame,textvariable=v,width=12,state='disabled',from_=low,to=high,increment=step)
            e.configure(font=('Segoe UI',11))
            e.configure(style='Ship.TSpinbox'if e.winfo_class()=='TSpinbox'else 'Ship.TEntry')
            e.grid(row=row*2,column=1,columnspan=2 if key=='name'else 1,sticky='ew'if key=='name'else 'w',pady=3)
            hint_label=None
            if hint:
                hint_label=ttk.Label(frame,text=hint,style='ShipHint.Card.TLabel',wraplength=180);hint_label.grid(row=row*2,column=2,sticky='w',padx=(8,0));self.field_hints.append(hint_label)
            self.ship_fields.append((key,row,label,e,hint_label))
            (self.extra_vars if extra else self.vars)[key]=v;(self.extra_entries if extra else self.entries)[key]=e
        identity=ttk.Frame(self.ship_overview,style='Card.TFrame')
        identity.grid(row=0,column=2,rowspan=2,sticky='new',padx=(20,0))
        self.identity_card=identity
        field(identity,0,'name','Ship name','1–17 English characters')
        field(identity,1,'price_gold','Price (gold bars)','1 bar = 10,000 gold')
        handling=section(right,'Hull and handling')
        for row,(key,title,hint)in enumerate([('hull','Hull strength','1–100'),('power','Sailing power','1–100'),('turning','Turning','1–100')]):field(handling,row,key,title,hint)
        limits=section(right,'Guns and crew limits')
        for row,(key,title,hint)in enumerate([('max_guns','Maximum guns','0–200'),('max_crew','Crew capacity','10–500, step 10'),('min_crew','Minimum sailors','1–255')]):field(limits,row,key,title,hint)
        space=section(right,'Capacity and calculated cargo')
        field(space,0,'capacity','Total capacity','1–2,000',True)
        field(space,1,'yard_cargo','Shipyard cargo','Total − max guns − max crew',True)
        field(space,2,'factory_cargo','Starting cargo','Total − starting guns − crew',True)
        fit=section(right,'Starting equipment')
        self.fixed=ttk.Label(fit,text='',wraplength=400,style='ShipHint.Card.TLabel');self.fixed.grid(row=4,column=0,columnspan=3,sticky='w',pady=(6,2))
        field(fit,0,'factory_guns','Starting guns','Gun spaces',True)
        field(fit,1,'factory_crew','Crew spaces','Reserved for sailors',True)
        self.spec_sections=[handling,limits,space,fit]
        def arrange_cards(event=None):
            width=self.scrollers[0].canvas.winfo_width()
            columns=2 if width>=820 else 1
            card_width=(width-24-(12 if columns==2 else 0))//columns
            body_width=max(220,card_width-44)
            inline=body_width>=440
            layout=(columns,inline,body_width)
            if layout==self.card_layout:return
            self.card_layout=layout
            self.card_columns=columns
            wide_header=width>=820
            identity.grid_configure(row=1 if wide_header else 2,column=1 if wide_header else 0,columnspan=1 if wide_header else 2,rowspan=1,sticky='w',padx=0,pady=(8,0))
            identity.columnconfigure(0,minsize=0,weight=0)
            identity.columnconfigure(1,weight=0)
            identity.columnconfigure(2,weight=0)
            self.ship_intro.columnconfigure(0,weight=1)
            for label in (self.heading,self.record_heading,self.ship_family):label.configure(wraplength=max(140,width-(260 if wide_header else 210)))
            if self.project and self.selected is not None and getattr(self,'spec_portrait_scale',None)!=(3 if wide_header else 2):self.show_portrait()
            for key,row,label,entry,hint in self.ship_fields:
                label.configure(wraplength=136)
                if key in ('name','price_gold'):
                    col=0 if key=='name'else 1
                    label.grid_configure(row=0 if wide_header else row*2,column=col if wide_header else 0,columnspan=1,padx=(0,20)if wide_header else (0,12),pady=0)
                    entry.grid_configure(row=1 if wide_header else row*2,column=col if wide_header else 1,columnspan=1,sticky='w',padx=(0,20)if wide_header else 0)
                    hint.grid_configure(row=2 if wide_header else row*2+1,column=col if wide_header else 1,columnspan=1,padx=0,pady=0,sticky='w')
                    hint.configure(wraplength=240 if key=='name'else 180)
                    continue
                if hint:
                    same_row=inline and key not in ('name','price_gold')
                    hint.configure(wraplength=max(85,body_width-280)if same_row else max(140,body_width-148))
                    hint.grid_configure(row=row*2 if same_row else row*2+1,column=2 if same_row else 1,columnspan=1 if same_row else 2,padx=(8,0)if same_row else 0,pady=0 if same_row else (0,3))
            self.entries['name'].configure(width=28 if wide_header else 20)
            for key,entry in {**self.entries,**self.extra_entries}.items():
                if key!='name':entry.configure(width=10)
            for index,stack in enumerate(self.card_stacks):
                self.cards.columnconfigure(index,weight=1 if index<columns else 0,uniform='cards'if index<columns else '')
                if index<columns:stack.grid(row=0,column=index,sticky='new',padx=(0,12)if index<columns-1 else 0)
                else:stack.grid_remove()
            order=[0,1,2,3]
            for index,number in enumerate(order):
                card=self.spec_sections[number]
                card.columnconfigure(0,minsize=136)
                card.panel.grid_forget()
                card.panel.grid(in_=self.card_stacks[index%columns],row=index//columns,column=0,sticky='ew',pady=(0,8))
            self.fixed.configure(wraplength=body_width)
            self.scrollers[0].resize();root.after_idle(self.scrollers[0].resize)
        self.arrange_cards=arrange_cards
        self.scrollers[0].canvas.bind('<Configure>',arrange_cards,add='+');root.after_idle(arrange_cards)
        for k in ('capacity','factory_guns','factory_crew'):self.extra_vars[k].trace_add('write',lambda *args,key=k:self.sync_fit(key))
        for k in ('max_guns','max_crew'):self.vars[k].trace_add('write',lambda *args,key=k:self.sync_fit(key))
        self.availability_heading=ttk.Label(availability,text='Select an added ship to change its ports.',wraplength=340,font=('Segoe UI',12,'bold'));self.availability_heading.pack(anchor='w',pady=(0,10))
        graphics=section(art_page,'Original ship family')
        ttk.Label(graphics,text='Sets the map/battle icons and default portrait and description. Custom text and specifications stay with this ship.',wraplength=340).pack(anchor='w')
        self.base_var=tk.StringVar();self.base_combo=ttk.Combobox(graphics,textvariable=self.base_var,state='disabled',width=28);self.base_combo.pack(fill='x',pady=(8,0))
        self.base_combo.bind('<<ComboboxSelected>>',lambda e:self.show_portrait())
        description=section(art_page,'Shipyard description')
        self.description_text=tk.Text(description,width=30,height=5,wrap='word',font=('Segoe UI',10),borderwidth=0,highlightthickness=1,highlightbackground='#bdc9da',highlightcolor='#0869df',state='disabled',undo=True)
        self.description_text.pack(fill='x',pady=(0,6))
        self.description_hint=ttk.Label(description,text='What the shipyard worker says. 1–226 English characters; no %.',wraplength=340,foreground='#596579');self.description_hint.pack(anchor='w')
        self.restore_description_button=ttk.Button(description,text='Use original description',command=self.restore_description,state='disabled');self.restore_description_button.pack(anchor='w',pady=(6,0))
        def description_modified(event):
            if self.description_text.edit_modified():
                self.description_text.edit_modified(False)
                self.schedule_auto_edit()
        self.description_text.bind('<<Modified>>',description_modified)
        artwork=section(art_page,'Ship portrait')
        self.portrait_label=ttk.Label(artwork,text='Open a ROM to view its portrait.');self.portrait_label.pack(anchor='center',pady=(8,4))
        self.portrait_note=ttk.Label(artwork,text='',wraplength=340,foreground='#596579');self.portrait_note.pack(anchor='center',pady=6)
        portrait_actions=ttk.Frame(artwork,style='Card.TFrame');portrait_actions.pack(anchor='center',pady=(4,8))
        self.import_portrait_button=ttk.Button(portrait_actions,text='Import PNG',command=self.import_portrait,state='disabled');self.import_portrait_button.grid(row=0,column=0,padx=(0,8))
        self.restore_portrait_button=ttk.Button(portrait_actions,text='Restore portrait',command=self.restore_portrait,state='disabled');self.restore_portrait_button.grid(row=0,column=1)
        ttk.Label(artwork,text='Converts to 64x48 pixels and the game’s 16 colors. Map and battle icons follow the original visual family.',wraplength=340).pack(anchor='w',pady=(6,0))
        unlock=section(availability,'Industry requirement')
        ttk.Label(unlock,text='Minimum industry to build this ship (new only)',wraplength=340).pack(anchor='w')
        self.industry_var=tk.StringVar();self.industry_entry=ttk.Entry(unlock,textvariable=self.industry_var,state='disabled',width=18);self.industry_entry.pack(anchor='w',pady=6)
        ttk.Label(unlock,text='0-1,000, in steps of 10. Applies to every selected port. Construction time follows hull strength and port industry.',wraplength=340,foreground='#596579').pack(anchor='w')
        locations=section(availability,'Shipyard locations')
        ttk.Label(locations,text='New-build locations only; used-ship rules stay unchanged. Click for one port; Ctrl-click for more. Fixed capitals cannot be developed.',wraplength=340).pack(anchor='w',pady=(0,6))
        self.port_summary=ttk.Label(locations,text='',wraplength=340);self.port_summary.pack(anchor='w',pady=(0,8))
        port_frame=ttk.Frame(locations);port_frame.pack(fill='both',expand=True)
        self.port_list=tk.Listbox(port_frame,selectmode='extended',exportselection=False,font=('Segoe UI',10),height=14,width=1,activestyle='none',highlightthickness=0,borderwidth=0,background='white',selectbackground='#205b9b',selectforeground='white');self.port_list.pack(side='left',fill='both',expand=True)
        self.port_list.bind('<<ListboxSelect>>',self.show_port_selection)
        self.port_list_locked=True
        def protect_port_selection(event):
            if not self.port_list_locked:return
            if event.type==tk.EventType.KeyPress:
                moves={'Up':(-1,'units'),'Down':(1,'units'),'Prior':(-1,'pages'),'Next':(1,'pages')}
                if event.keysym in moves:self.port_list.yview_scroll(*moves[event.keysym])
                elif event.keysym=='Home':self.port_list.yview_moveto(0)
                elif event.keysym=='End':self.port_list.yview_moveto(1)
                elif event.keysym in ('Tab','ISO_Left_Tab'):return
            return 'break'
        for event in ('<ButtonPress-1>','<ButtonRelease-1>','<B1-Motion>','<B1-Leave>','<B1-Enter>','<KeyPress>'):self.port_list.bind(event,protect_port_selection)
        scroll=ttk.Scrollbar(port_frame,command=self.port_list.yview);scroll.pack(side='right',fill='y');self.port_list.configure(yscrollcommand=scroll.set)
        self.ship_secondary_layouts=[]
        for page,scroll,panels in [(availability,self.scrollers[1],[locations.panel,unlock.panel]),(art_page,self.scrollers[2],[artwork.panel,graphics.panel,description.panel])]:
            holder=ttk.Frame(page);holder.pack(fill='x')
            for panel in panels:panel.pack_forget()
            def arrange_secondary(event=None,holder=holder,scroll=scroll,panels=panels):
                columns=2 if scroll.canvas.winfo_width()>=850 else 1
                holder.columnconfigure(0,weight=1 if len(panels)==3 or columns==1 else 2,uniform='secondary')
                holder.columnconfigure(1,weight=1 if columns==2 else 0,uniform='secondary'if columns==2 else '')
                for index,panel in enumerate(panels):
                    row=(0 if index<2 else 1)if columns==2 else index
                    column=(0 if index==0 else 1)if columns==2 else 0
                    panel.grid_forget();panel.grid(in_=holder,row=row,column=column,rowspan=2 if columns==2 and len(panels)==3 and index==0 else 1,sticky='new',padx=(0,12)if columns==2 and index==0 else 0,pady=(0,10));panel.lift(holder)
                    proportion=(2/3 if index==0 else 1/3)if columns==2 and len(panels)==2 else 1/columns
                    def wrap(parent):
                        for child in parent.winfo_children():
                            if child.winfo_class()=='TLabel':child.configure(wraplength=max(120,int((scroll.canvas.winfo_width()-36)*proportion)-48))
                            wrap(child)
                    wrap(panel)
                scroll.resize();root.after_idle(scroll.resize)
            scroll.canvas.bind('<Configure>',arrange_secondary,add='+');root.after_idle(arrange_secondary)
            self.ship_secondary_layouts.append((holder,panels))
        fixes_page=ttk.Frame(self.scrollers[3].content,padding=12);fixes_page.pack(fill='both',expand=True)
        fixes=section(fixes_page,'Repair protection')
        self.repair_var=tk.BooleanVar(value=False)
        self.repair_check=ttk.Checkbutton(fixes,text='Repair Safeguard',variable=self.repair_var,state='disabled')
        self.repair_check.pack(anchor='w',pady=(0,8))
        ttk.Label(fixes,text='Prevents excessive repair charges when ship stats are lowered and an existing save is loaded. Keeps original gold and lumber repair rates.',wraplength=340).pack(anchor='w')
        ttk.Label(fixes,text='Applies to the whole exported game. Enabled exports use a 4 MB ROM, including projects without added ships.',wraplength=340,foreground='#596579').pack(anchor='w',pady=(12,0))
        self.gameplay_settings=ttk.Frame(self.settings_area)
        gameplay_actions=ttk.Frame(self.gameplay_settings);gameplay_actions.pack(side='bottom',fill='x',pady=(8,0))
        self.gameplay_apply_button=ttk.Button(gameplay_actions,text='Apply gameplay changes',command=self.apply_gameplay,style='Primary.TButton',state='disabled');ttk.Label(gameplay_actions,text='Changes apply automatically',foreground='#6e7f98').pack(anchor='w')
        self.gameplay_reset_button=ttk.Button(gameplay_actions,text='Reset Gameplay',command=lambda:self.reset_section('gameplay'),state='disabled');self.gameplay_reset_button.pack(side='right',padx=8)
        self.gameplay_notebook=ttk.Notebook(self.gameplay_settings)
        self.gameplay_notebook.pack(fill='both',expand=True)
        self.gameplay_scrollers=[];gameplay_pages={};world_pages={};self.world_gameplay_sections={}
        def make_gameplay_page(parent):
            scroll=ScrollableWindow(parent,fit_width=True)
            page=ttk.Frame(scroll.content,padding=16);page.pack(fill='both',expand=True)
            def fit(event):
                if hasattr(page,'world_cards'):return
                def wrap_labels(parent):
                    for widget in parent.winfo_children():
                        if widget.winfo_class()=='TLabel':widget.configure(wraplength=max(150,min(620,event.width-64)))
                        wrap_labels(widget)
                wrap_labels(page)
            scroll.canvas.bind('<Configure>',fit,add='+')
            return scroll,page
        for label in ('Presets','Battles','World','Campaign'):
            tab=ttk.Frame(self.gameplay_notebook);self.gameplay_notebook.add(tab,text=label)
            scroll,page=make_gameplay_page(tab);self.gameplay_scrollers.append(scroll);gameplay_pages[label]=page
            if label=='World':
                page.configure(padding=10);page.world_cards=[]
                self.world_gameplay_hint=ttk.Label(page,text='Review shuffles before applying. Starting-world and character changes require a new game.',foreground='#596579')
                self.world_gameplay_hint.grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,8))
                for category in ('Fleets','Mates','Items','Trade','Ships','Discoveries'):
                    panel=ttk.Frame(page,style='Surface.TFrame',padding=1)
                    header=ttk.Frame(panel,style='Card.TFrame',padding=(10,1));header.pack(fill='x')
                    ttk.Label(header,text='Goods'if category=='Trade'else category,style='Card.TLabel',font=('Segoe UI',10,'bold')).pack(anchor='w')
                    content=ttk.Frame(panel,style='Card.TFrame',padding=(10,5));content.pack(fill='both',expand=True)
                    world_pages[category]=content;self.world_gameplay_sections[category]=panel;page.world_cards.append(panel)
                def layout_world(event=None,page=page,scroll=scroll):
                    width=scroll.canvas.winfo_width();columns=1
                    self.world_gameplay_columns=columns
                    for col in (0,1):page.columnconfigure(col,weight=1 if col<columns else 0,uniform='world'if col<columns else '')
                    self.world_gameplay_hint.grid_configure(columnspan=columns)
                    self.world_gameplay_hint.configure(wraplength=max(180,width-40))
                    wrap=max(160,(width-20)//columns-44)
                    for i,panel in enumerate(page.world_cards):
                        panel.grid(row=1+i//columns,column=i%columns,sticky='nsew',padx=(0,8)if columns==2 and i%2==0 else 0,pady=(0,3))
                        def labels(parent):
                            for widget in parent.winfo_children():
                                if widget.winfo_class()=='TLabel':widget.configure(wraplength=wrap)
                                labels(widget)
                        labels(panel)
                    self.root.after_idle(scroll.resize)
                scroll.canvas.bind('<Configure>',layout_world,add='+')
                self.root.after_idle(layout_world)
        from custom_preset_view import create_controls
        create_controls(self,gameplay_pages['Presets'])
        self.gameplay_scrollers[0].natural_height=True
        self.gameplay_scroll=self.gameplay_scrollers[0]
        def gameplay_tab_changed(event=None):
            index=self.gameplay_notebook.index('current')
            self.gameplay_scroll=self.gameplay_scrollers[index]
            if self.section=='gameplay':self.scroll=self.gameplay_scroll
            self.root.after_idle(self.gameplay_scroll.resize)
        self.gameplay_notebook.bind('<<NotebookTabChanged>>',gameplay_tab_changed)
        gameplay=gameplay_pages['Battles']
        ttk.Label(gameplay,text='Battle control',font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(0,12))
        self.fleet_var=tk.BooleanVar(value=False)
        self.fleet_check=ttk.Checkbutton(gameplay,text='Fleet Control (Experimental)',variable=self.fleet_var,state='disabled');self.fleet_check.pack(anchor='w',pady=(0,8))
        ttk.Label(gameplay,text='Control all your ships in sea battles. The camera follows the ship taking its turn. At the battle menu, press Select to turn automatic control for your mates on or off. Press A to continue.',wraplength=340).pack(anchor='w')
        ttk.Label(gameplay,text='Each battle starts with manual control. You always control your flagship. Experimental: story battles still need testing.',wraplength=340,foreground='#596579').pack(anchor='w',pady=(12,0))
        from world_gameplay_settings import WorldSettings
        world_pages['Campaign']=gameplay_pages['Campaign']
        self.world_gameplay_settings=WorldSettings(self,world_pages)
        self.difficulty_var.trace_add('write',lambda *args:self.sync_difficulty_state())
        self.sync_difficulty_state()
        self.compact=None
        def resize_density(event):
            if event.widget!=root:return
            sidebar_width=max(210,min(420,int(event.width*.196)))if event.width>=1050 else 210
            self.sidebar.configure(width=sidebar_width)
            density='compact'if event.width<900 or event.height<620 else 'large'if event.width>=1500 and event.height>=900 else 'medium'
            compact_nav=event.height<850
            if density==self.compact and getattr(self,'compact_nav',None)==compact_nav:return
            self.compact_nav=compact_nav
            self.compact=density;compact=density=='compact';large=density=='large'
            self.sidebar.configure(padding=(12,4)if compact else (12,10))
            self.nav_separator.pack_configure(pady=(0,4)if compact else (0,10))
            if compact:self.sections_label.pack_forget()
            else:self.sections_label.pack(before=self.gameplay_nav,anchor='w',pady=(0,6))
            self.label_column_width=190 if large else 164
            self.title_label.configure(font=('Segoe UI',14 if compact else 22 if large else 20,'bold'))
            self.title_label.configure(image=self.branding.photo(20 if compact else 32))
            self.build_label.configure(font=('Segoe UI',8 if compact else 10))
            top.configure(padding=(16,6 if compact else 12))
            self.source.configure(font=('Segoe UI',8 if compact else 10))
            self.status.configure(font=('Segoe UI',8 if compact else 10),padding=(16,1 if compact else 3))
            self.status.configure(image=self.ui.icon('stats','#64758c',14 if compact else 18))
            self.ships_heading.configure(font=('Segoe UI',10 if compact else 12,'bold'))
            self.list.configure(width=1,font=('Segoe UI',9 if compact else 11 if large else 10))
            style.configure('TButton',font=('Segoe UI',9 if compact else 11 if large else 10),padding=(5,2)if compact else (14,9))
            style.configure('Primary.TButton',padding=(10,4)if compact else (16,8))
            style.configure('Nav.TButton',font=('Segoe UI',9 if compact or compact_nav else 11),padding=(8,0)if compact or compact_nav else (12,4))
            style.configure('Tab.TButton',font=('Segoe UI',8 if compact else 12 if large else 11),padding=(4,7)if compact else (18,11))
            for i,button in enumerate(self.tab_buttons):button.configure(image=''if compact else self.ui.icon(('stats','calendar','image','wrench','game')[i],'#0869df'if i==self.notebook.index('current')else '#54647b'))
            for i,button in enumerate(self.toolbar_buttons):button.configure(image=''if compact else self.ui.icon(('folder','folder','save','export','help')[i],'#0869df'))
            for key,button in self.section_buttons.items():button.configure(image=self.ui.icon(dict(ships='ship',mates='person',captains='captain',gameplay='game',world='anchor',library='folder',characters='person',discoveries='anchor')[key],'#194c85',16 if compact else 22))
            self.apply_button.configure(image=''if compact else self.ui.icon('check','white',22))
            self.restore_button.configure(image=''if compact else self.ui.icon('restore','#243c60',20))
            self.add_button.configure(image=''if compact else self.ui.icon('add','#0876e9',16))
            style.configure('Sidebar.TLabel',font=('Segoe UI',9 if compact else 11))
            for widget_style in ('TEntry','TSpinbox','TCombobox'):
                style.configure(widget_style,font=('Segoe UI',10 if compact else 12 if large else 11),padding=(5,3)if compact else (8,4)if large else (7,4))
            for key,entry in {**self.entries,**self.extra_entries}.items():
                entry.configure(font=('Segoe UI',10 if compact else 11))
                if key!='name':entry.configure(width=10)
            self.search_entry.configure(font=('Segoe UI',9 if compact else 11))
            style.configure('Card.TLabel',font=('Segoe UI',10 if compact else 12 if large else 11))
            style.configure('Hint.Card.TLabel',font=('Segoe UI',9 if not large else 10))
            style.configure('CardTitle.TLabel',font=('Segoe UI',11 if compact else 12,'bold'))
            for card in self.spec_sections:card.columnconfigure(0,minsize=136)
            self.refresh_section_colors()
        root.bind('<Configure>',resize_density,add='+')
        def sidebar_colors(widget):
            for child in widget.winfo_children():
                if child.winfo_class()=='TLabel'and not child.cget('style'):child.configure(style='Sidebar.TLabel')
                elif child.winfo_class()=='TFrame'and not child.cget('style'):child.configure(style='SidebarContent.TFrame')
                sidebar_colors(child)
        sidebar_colors(left)
        for card in self.spec_sections+[identity,graphics,description,artwork,unlock,locations,fixes]:
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
            self.card_layout=None;self.arrange_cards();root.update_idletasks()
            for scroll in self.scrollers:
                scroll.resize();scroll.canvas.xview_moveto(0);scroll.canvas.yview_moveto(0)
        self.create_mate_browser()
        from world import WorldBrowser
        self.world=WorldBrowser(self,ScrollableWindow)
        from discovery_view import DiscoveriesPanel
        self.discoveries=DiscoveriesPanel(self,ScrollableWindow)
        from library_view import LibraryPanel
        self.library=LibraryPanel(self,ScrollableWindow)
        from protagonist_view import CharactersPanel
        self.characters=CharactersPanel(self,ScrollableWindow)
        self.active_changes=ttk.Frame(self.sidebar,style='SidebarContent.TFrame')
        ttk.Label(self.active_changes,text='Active changes',style='Sidebar.TLabel',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(8,6))
        self.active_changes_text=ttk.Label(self.active_changes,text='Open a stock ROM to begin.',style='Sidebar.TLabel',foreground='#205b9b',wraplength=180,justify='left');self.active_changes_text.pack(anchor='w')
        restore_area=ttk.Frame(self.active_changes,style='SidebarContent.TFrame');restore_area.pack(side='bottom',fill='x')
        self.restore_defaults_button=ttk.Button(restore_area,text='Restore all settings\nto default',command=self.restore_defaults,state='disabled');self.restore_defaults_button.pack(fill='x',pady=(4,2))
        ttk.Label(restore_area,text='Does not affect Library data',foreground='#6e7f98',font=('Segoe UI',8)).pack(pady=(0,3))
        self.sidebar.bind('<Configure>',lambda event:self.active_changes_text.configure(wraplength=max(150,event.width-28),font=('Segoe UI',9 if event.width<240 else 10)),add='+')
        root.after(100,initial_view)
        for key,variable in self.vars.items():variable.trace_add('write',self.schedule_auto_edit)
        for key,variable in self.extra_vars.items():
            if key not in ('yard_cargo','factory_cargo'):variable.trace_add('write',self.schedule_auto_edit)
        for variable in [self.industry_var,self.base_var,self.repair_var,self.fleet_var,self.difficulty_var]:variable.trace_add('write',self.schedule_auto_edit)
        from sailors import ATTRIBUTES
        for key in ATTRIBUTES:self.mate_vars[key].trace_add('write',self.schedule_auto_edit)
        for variable in self.skill_vars.values():variable.trace_add('write',self.schedule_auto_edit)

    def create_mate_browser(self):
        self.mate_settings=ttk.Frame(self.settings_area)
        self.mate_scroll=ScrollableWindow(self.mate_settings,fit_width=True)
        self.mate_scroll.pack(fill='both',expand=True)
        page=ttk.Frame(self.mate_scroll.content,padding=16);page.pack(fill='both',expand=True)
        self.character_header=ttk.Frame(page);self.character_header.pack(fill='x',pady=(0,12))
        self.mate_portrait_label=ttk.Label(self.character_header,text='');self.mate_portrait_label.pack(side='left',anchor='n',padx=(0,16))
        self.character_title=ttk.Frame(self.character_header);self.character_title.pack(side='left',fill='both',expand=True)
        self.character_portrait_key=None;self.character_photo=None
        self.mate_heading=ttk.Label(self.character_title,text='Mates',font=('Segoe UI',18,'bold'),wraplength=480)
        self.mate_heading.pack(anchor='w',pady=(0,6))
        self.mate_subheading=ttk.Label(self.character_title,text='Open a stock USA ROM to view its mates.',wraplength=480)
        self.mate_subheading.pack(anchor='w',pady=(0,12))
        self.custom_character_var=tk.BooleanVar(value=False)
        self.custom_character_box=ttk.Checkbutton(page,text='Use custom values',variable=self.custom_character_var,command=self.toggle_custom_characters,state='disabled')
        self.custom_character_box.pack(anchor='w',pady=(0,10))
        self.mate_vars={};self.mate_field_widgets={}
        self.mate_cards=ttk.Frame(page);self.mate_cards.pack(anchor='w')
        self.mate_panels=[]
        groups=[('Profile',[('role','Starting role'),('nationality','Nationality'),('age','Starting age'),
                 ('navigation_level','Navigation level'),('battle_level','Battle level'),('starting_port_name','Starting location')]),
                ('Attributes',[(k,k.replace('_',' ').capitalize()) for k in
                 ('leadership','seamanship','knowledge','intuition','courage','swordsmanship','charm','luck')])]
        for title,fields in groups:
            panel=ttk.Frame(self.mate_cards,style='Surface.TFrame',padding=8)
            header=ttk.Frame(panel,style='CardHeader.TFrame',padding=(8,8));header.pack(fill='x')
            ttk.Label(header,text=title,style='CardTitle.TLabel').pack(anchor='w')
            content=ttk.Frame(panel,style='Card.TFrame',padding=(12,10));content.pack(fill='both',expand=True)
            for key,label in fields:
                name=ttk.Label(content,text=label,style='Card.TLabel',wraplength=0 if title=='Attributes'else 120)
                value=tk.StringVar(value='—');self.mate_vars[key]=value
                number=ttk.Spinbox(content,textvariable=value,from_=0,to=100,width=5,state='disabled')if title=='Attributes'else ttk.Label(content,textvariable=value,style='Card.TLabel',wraplength=150)
                self.mate_field_widgets[key]=(name,number)
            self.mate_panels.append(panel)
        from sailors import SKILLS
        self.skill_panel=ttk.Frame(self.mate_cards,style='Surface.TFrame',padding=8)
        skill_header=ttk.Frame(self.skill_panel,style='CardHeader.TFrame',padding=(8,8));skill_header.pack(fill='x')
        ttk.Label(skill_header,text='Skills',style='CardTitle.TLabel').pack(anchor='w')
        self.skill_content=ttk.Frame(self.skill_panel,style='Card.TFrame',padding=(12,10));self.skill_content.pack(fill='both',expand=True)
        self.skill_vars={};self.skill_checks={}
        for key,label,bit in SKILLS:
            variable=tk.BooleanVar(value=False);self.skill_vars[key]=variable
            check=ttk.Checkbutton(self.skill_content,text=label,variable=variable,state='disabled',style='Card.TCheckbutton')
            self.skill_checks[key]=check
        self.skills_note=ttk.Label(self.skill_content,text='Load a ROM to view skills.',wraplength=700,style='Hint.Card.TLabel')
        self.skills_note.grid(sticky='w',pady=(8,0))
        self.sailor_actions=ttk.Frame(page);self.sailor_actions.pack(anchor='w',pady=(0,6))
        self.sailor_apply_button=ttk.Button(self.sailor_actions,text='Apply character changes',command=self.apply_character,state='disabled')
        ttk.Label(self.sailor_actions,text='Changes apply automatically',foreground='#6e7f98').pack(anchor='w',pady=(0,4))
        self.sailor_restore_button=ttk.Button(self.sailor_actions,text='Restore character',command=self.restore_character,state='disabled')
        self.sailor_restore_button.pack(side='left')
        self.free_agent_controls=ttk.Frame(self.character_title)
        self.randomizer_button=ttk.Button(self.free_agent_controls,text='Configure random mates…',command=lambda:self.open_free_agent_shuffle('mates'),state='disabled')
        # Randomization is configured only in Gameplay > World.
        self.randomizer_summary=ttk.Label(self.free_agent_controls,text='Port shuffle: off',wraplength=360)
        self.randomizer_summary.pack(anchor='w',pady=(4,0))
        self.mate_note=ttk.Label(page,text='Stock starting values • Read-only\nStory companions join through their campaigns. Free agents can move, and stats can change during play. Existing saves are not read by the editor.',wraplength=560,foreground='#6e7f98')
        self.mate_note.pack(anchor='w',pady=(12,0))
        self.mate_columns=None;self.mate_layout=None
        def arrange(event=None):
            width=max(260,min(900,self.mate_scroll.canvas.winfo_width()-32))
            self.show_character_portrait()
            header_width=max(120,width-(136 if self.mate_scroll.canvas.winfo_width()>=600 else 96))
            self.mate_heading.configure(wraplength=header_width)
            self.mate_subheading.configure(wraplength=header_width)
            self.mate_note.configure(wraplength=width)
            self.randomizer_summary.configure(wraplength=header_width)
            columns=2 if width>=780 else 1
            profile_width=int((width-12)*.40)if columns==2 else width
            stats_width=width-profile_width-12 if columns==2 else width
            attribute_fields=[self.mate_field_widgets[k]for k,_ in groups[1][1]]
            pair_width=max(label.winfo_reqwidth()+value.winfo_reqwidth()+12 for label,value in attribute_fields)
            stat_columns=2 if stats_width>=max(440,pair_width*2+60) else 1
            layout=(width,columns,stat_columns)
            if layout==self.mate_layout:return
            self.mate_layout=layout;self.mate_columns=columns;self.mate_stat_columns=stat_columns
            self.mate_cards.columnconfigure(0,minsize=profile_width,weight=0)
            self.mate_cards.columnconfigure(1,minsize=stats_width+12 if columns==2 else 0,weight=0)
            for index,panel in enumerate(self.mate_panels):
                panel.grid_forget()
                panel.grid(row=0 if columns==2 else index,column=index if columns==2 else 0,
                           rowspan=2 if columns==2 and index==0 else 1,sticky='new',padx=(12,0)if columns==2 and index==1 else 0,pady=(0,10))
            self.skill_panel.grid(row=1 if columns==2 else 2,column=1 if columns==2 else 0,sticky='new',
                                  padx=(12,0)if columns==2 else 0,pady=(0,10))
            skill_width=stats_width if columns==2 else width
            skill_columns=2 if skill_width>=440 else 1
            self.skills_note.configure(wraplength=max(180,skill_width-48))
            for index,check in enumerate(self.skill_checks.values()):
                check.grid(row=index//skill_columns,column=index%skill_columns,sticky='w',
                           padx=(0,20)if skill_columns==2 and index%2==0 else 0,pady=1)
            self.skills_note.grid(row=(len(self.skill_checks)+skill_columns-1)//skill_columns,column=0,columnspan=skill_columns,sticky='w',pady=(6,0))
            for group,(_,fields) in enumerate(groups):
                for index,(key,_) in enumerate(fields):
                    pair=index//4 if group==1 and stat_columns==2 else 0
                    row=index%4 if group==1 and stat_columns==2 else index
                    label,value=self.mate_field_widgets[key]
                    label.grid_forget();value.grid_forget()
                    label.grid(row=row,column=pair*2,sticky='w',padx=(20 if pair else 0,12),pady=4)
                    value.grid(row=row,column=pair*2+1,sticky='e'if group else 'w',pady=4)
                    if group==0:value.configure(wraplength=max(100,profile_width-175))
            self.root.after_idle(self.mate_scroll.resize)
        self.mate_scroll.canvas.bind('<Configure>',arrange,add='+')
        arrange()

    def show_character_portrait(self):
        if not self.project or self.data_type=='ships':return
        record_id=self.character_selection()
        if record_id is None:return
        scale=3 if self.mate_scroll.canvas.winfo_width()>=600 else 2
        key=(id(self.project.rom),record_id,scale)
        if key==self.character_portrait_key:return
        from character_portraits import portrait
        self.character_photo=ImageTk.PhotoImage(portrait(self.project.rom,record_id,scale),master=self.root)
        self.mate_portrait_label.configure(image=self.character_photo,text='')
        self.character_portrait_key=key

    def toggle_custom_characters(self):
        if not self.project or self.data_type not in ('mates','captains'):return
        wanted=self.custom_character_var.get()
        if self.auto_timer is not None:self.root.after_cancel(self.auto_timer);self.auto_timer=None
        try:self.commit_character()
        except ValueError as error:self.custom_character_var.set(getattr(self.project,'custom_'+self.data_type));self.fail(error);return
        setattr(self.project,'custom_'+self.data_type,wanted);self.show_mate(self.character_selection());self.refresh_list();self.update_status()

    def commit_character(self):
        if not self.project or self.section not in ('mates','captains')or not getattr(self.project,'custom_'+self.section)or self.character_selection()is None:return
        from sailors import ATTRIBUTES,SKILLS
        values={}
        for key in ATTRIBUTES:
            try:values[key]=int(self.mate_vars[key].get())
            except ValueError:raise ValueError(key.capitalize()+' needs a whole number from 0 to 100.')
        values['skills']=sum(bit for key,label,bit in SKILLS if self.skill_vars[key].get())
        self.project.update_character(self.character_selection(),values)

    def apply_character(self):
        try:self.commit_character();self.refresh_list();self.update_status()
        except Exception as e:self.fail(e)

    def restore_character(self):
        if not self.project or self.data_type=='ships'or not getattr(self.project,'custom_'+self.data_type):return
        i=self.character_selection()
        if i is None:return
        self.cancel_auto_edit()
        try:self.project.restore_character(i)
        except ValueError as error:self.fail(error);return
        self.show_mate(i);self.refresh_list();self.update_status()

    def open_shipbuilding_seed(self):
        from shipbuilding_shuffle_view import open_shuffle
        open_shuffle(self)

    def open_goods_seed(self):
        from goods_shuffle_view import open_shuffle
        open_shuffle(self)

    def open_free_agent_shuffle(self,group='all'):
        from people_shuffle_view import open_shuffle
        open_shuffle(self,group)

    def sync_shuffle_state(self):
        option=self.project.free_agent_shuffle if self.project else None
        from character_mods import group_active,group_summary
        active=option is not None and group_active(option,'mates')
        text='Off'
        if active:
            text=group_summary(option,'mates')
        for button in (self.randomizer_button,self.gameplay_randomizer_button):
            button.configure(state='normal'if self.project else 'disabled')
        self.randomizer_summary.configure(text=text,foreground=CHANGE_ORANGE if active else '#596579')

    def sync_difficulty_state(self):
        enabled=self.project is not None and self.difficulty_var.get()
        self.difficulty_settings_button.configure(state='normal'if enabled else 'disabled')
        self.difficulty_description.configure(foreground='#17243d'if enabled else '#78879a')
        self.difficulty_note.configure(foreground='#596579'if enabled else '#78879a')

    def configure_fleets(self):
        if not self.project or not self.difficulty_var.get():return
        from fleet_settings import open_settings
        open_settings(self,ScrollableWindow)

    def apply_gameplay(self):
        try:self.commit();self.update_status()
        except Exception as e:self.fail(e)

    def switch_section(self,kind):
        diagnostics.LOGGER.info('Select section: %s',kind)
        if kind not in ('gameplay','world','library','characters','discoveries'):return self.switch_data(kind)
        if self.section==kind:return
        try:
            if self.project:self.commit()
        except Exception as e:self.fail(e);return
        self.section=kind
        for key,button in self.section_buttons.items():button.configure(style='Selected.Nav.TButton'if key==kind else 'Nav.TButton')
        self.nav_strip.configure(background='#f0f4f9')
        self.browser_controls.pack_forget()
        self.ship_settings.pack_forget();self.mate_settings.pack_forget();self.gameplay_settings.pack_forget()
        self.world.hide();self.library.hide();self.characters.hide();self.discoveries.hide();self.active_changes.pack_forget()
        if kind=='gameplay':
            self.active_changes.pack(fill='both',expand=True)
            self.gameplay_settings.pack(fill='both',expand=True)
            self.scroll=self.gameplay_scroll
            self.root.after_idle(self.gameplay_scroll.resize)
        elif kind=='library':self.library.show()
        elif kind=='characters':self.characters.show()
        elif kind=='discoveries':self.discoveries.show()
        else:self.world.show()
        self.update_status()

    def switch_data(self,kind):
        diagnostics.LOGGER.info('Select data: %s',kind)
        if kind==self.data_type and self.section==kind:return
        try:
            if self.project:self.commit()
        except Exception as e:self.fail(e);return
        self.browser_searches[self.data_type]=self.search_var.get()
        self.browser_views[self.data_type]=self.list.yview()[0]
        self.data_type=kind;self.section=kind
        self.gameplay_settings.pack_forget();self.world.hide();self.library.hide();self.characters.hide();self.discoveries.hide();self.active_changes.pack_forget()
        self.browser_controls.pack(fill='both',expand=True)
        self.scroll=self.scrollers[self.notebook.index('current')]
        for key,button in self.section_buttons.items():
            button.configure(style='Selected.Nav.TButton'if key==kind else 'Nav.TButton')
        self.nav_strip.configure(background='#0869df'if kind=='ships'else '#f0f4f9')
        self.ship_settings.pack_forget();self.mate_settings.pack_forget()
        if kind!='ships':
            self.add_button.pack_forget();self.remove_button.pack_forget()
            self.mate_settings.pack(fill='both',expand=True)
        else:
            self.add_button.pack(side='right',padx=(8,0));self.remove_button.pack(fill='x')
            self.ship_settings.pack(fill='both',expand=True)
        self.ships_heading.configure(text={'ships':'Ships','mates':'Mates','captains':'Fleet Captains'}[kind])
        self.search_var.set(self.browser_searches[kind]);self.refresh_list()
        if self.project:
            if kind!='ships':self.show_mate(self.character_selection())
            else:self.show(self.selected)
        self.list.yview_moveto(self.browser_views[kind])
        if not self.project and kind!='ships':
            self.mate_heading.configure(text='Fleet Captains'if kind=='captains'else 'Mates')
            self.mate_subheading.configure(text='Open a stock USA ROM to view its sailors.')
        self.update_status()

    def character_selection(self):
        return self.captain_selected if self.data_type=='captains'else self.mate_selected

    def character_records(self):
        from sailors import mates,fleet_captains
        rows=(fleet_captains if self.data_type=='captains'else mates)(self.project.rom)
        from character_mods import shuffled_names
        from sailors import decode_sailors
        mapping=shuffled_names(self.project.rom,self.project.free_agent_shuffle)
        for row in rows:
            row.update(mapping.get(row['id'],{}))
        return rows

    def refresh_mate_list(self):
        view=self.list.yview()
        self.loading=True;self.list.delete(0,'end');self.mate_rows=[]
        if self.project:
            query=self.search_var.get().strip().casefold()
            from character_mods import port_shuffle,shuffled_names
            names=shuffled_names(self.project.rom,self.project.free_agent_shuffle)
            ports=port_shuffle(self.project.rom,self.project.free_agent_shuffle)
            from sailors import decode_sailors
            stock_names=decode_sailors(self.project.rom)
            for row in self.character_records():
                if query not in row['name'].casefold():continue
                changed=any(e['id']==row['id']for e in self.project.effective_character_edits())or ports.get(row['id'],row['starting_port'])!=row['starting_port']or row['name']!=stock_names[row['id']]['name']
                self.mate_rows.append(row['id']);self.list.insert('end',row['name']+('  *'if changed else ''))
                self.color_browser_row(changed)
        selected=self.character_selection()
        if selected in self.mate_rows:self.select_browser_row(self.mate_rows.index(selected))
        if view:self.list.yview_moveto(view[0])
        self.loading=False

    def show_mate(self,record_id):
        if not self.project:return
        self.auto_loading=True
        records=self.character_records()
        record=next((r for r in records if r['id']==record_id),records[0])
        record=self.project.character_record(record['id'])
        changed=self.character_selection()!=record['id']
        if self.data_type=='captains':self.captain_selected=record['id']
        else:self.mate_selected=record['id']
        self.show_character_portrait()
        self.mate_heading.configure(text=record['name'])
        self.mate_subheading.configure(text=record['role']+' • Starting role'+('; some captains can later become mates.'if self.data_type=='captains'else ''))
        self.mate_note.configure(text='Starting values • Attributes and skills editable. A new game is required for testing.\n'+('Some fleet captains can later be recruited as mates. This list shows starting roles, not current employment or individual recruitment eligibility.'if self.data_type=='captains'else 'Story companions join through their campaigns. Free agents can move and stats can grow. Captains who may later become mates are listed under Fleet Captains.'))
        from sailors import ATTRIBUTES
        enabled=getattr(self.project,'custom_'+self.data_type)
        self.custom_character_var.set(enabled);self.custom_character_box.configure(state='normal',text='Use custom values')
        for key in ATTRIBUTES:self.mate_field_widgets[key][1].configure(state='normal'if enabled else 'disabled')
        from sailors import SKILLS
        original=self.project.rom[0x881F3+record['id']*50+48]&31
        companion=record['role']=='Story companion'
        for key,label,bit in SKILLS:
            self.skill_vars[key].set(bool(record['skills']&bit))
            self.skill_checks[key].configure(state='disabled'if not enabled or companion and original&bit else 'normal')
        self.skills_note.configure(text=('Original companion skills are locked. You can add other skills.'if companion else 'Tick the skills this character should start with.')+' Start a new game to use changes.')
        self.sailor_apply_button.configure(state='normal'if enabled else 'disabled');self.sailor_restore_button.configure(state='normal'if enabled else 'disabled')
        self.free_agent_controls.pack_forget()
        # Random mate settings are available under Gameplay > World.
        self.randomizer_button.configure(state='normal')
        option=self.project.free_agent_shuffle
        self.randomizer_summary.configure(text=('Port shuffle: blind'if option['blind']else 'Port shuffle: on')if option['enabled']else 'Port shuffle: off')
        for key,value in self.mate_vars.items():
            value.set(str(record[key])if record[key]is not None else 'Fleet-dependent'if self.data_type=='captains'else 'Story-dependent')
        self.list.selection_clear(0,'end')
        selected=self.character_selection()
        if selected in self.mate_rows:self.select_browser_row(self.mate_rows.index(selected))
        if record['role']=='Free agent'and option['enabled']and option.get('ports',True)and __import__('character_mods').group_settings(option,'ports')['blind']:
            self.mate_vars['starting_port_name'].set('Hidden (blind shuffle)')
        if changed:self.mate_scroll.canvas.yview_moveto(0)
        self.root.after_idle(self.mate_scroll.resize);self.auto_loading=False;self.refresh_edit_colors()

    def schedule_auto_edit(self,*args):
        if self.auto_loading or self.fit_loading or self.fit_syncing or not self.project:return
        if self.auto_timer is not None:self.root.after_cancel(self.auto_timer)
        self.auto_timer=self.root.after(350,self.auto_edit)

    def auto_edit(self):
        self.auto_timer=None
        if self.auto_loading or not self.project:return
        try:
            if self.section=='gameplay':
                self.project.repair_safeguard=self.repair_var.get()
                self.project.fleet_control=self.fleet_var.get()
                self.project.fleet_difficulty=self.difficulty_var.get()
            elif self.section in ('mates','captains'):self.commit_character()
            elif self.section=='ships':self.commit()
            else:return
        except (ValueError,TypeError)as error:
            self.status.configure(text='Finish editing: '+str(error));return
        self.refresh_list();self.update_status()
        if self.section=='ships'and self.selected is not None:
            name=self.project.ships[self.selected]['name']
            self.heading.configure(text=name);self.graphics_heading.configure(text=name+' — Graphics')

    def fail(self,e):
        diagnostics.LOGGER.warning('Action failed; section=%s',self.section,exc_info=(type(e),e,e.__traceback__))
        messagebox.showerror('Check your values',str(e),parent=self.root)
    def open_search(self):
        if self.section=='gameplay':return 'break'
        entry=self.discoveries.search_entry if self.section=='discoveries'else self.library.search_entry if self.section=='library'else self.world.search_entry if self.section=='world'else self.search_entry
        entry.focus_set();entry.selection_range(0,'end')
        return 'break'
    def clear_search(self):
        self.search_var.set('');self.list.focus_set()
        rows=self.mate_rows if self.data_type!='ships'else self.ship_rows
        selected=self.character_selection()if self.data_type!='ships'else self.selected
        if selected in rows:self.list.see(rows.index(selected))
        return 'break'
    def select_browser_row(self,index):
        self.list.selection_set(index)
        # Tk keyboard navigation follows the active row, not just the selection.
        # Rebuilding the list resets active/anchor to row zero unless restored.
        self.list.activate(index);self.list.selection_anchor(index)

    def color_browser_row(self,changed):
        self.list.itemconfigure('end',foreground=CHANGE_ORANGE if changed else '#17243d',
            background='#fff5e9'if changed else 'white',
            selectforeground=CHANGE_ORANGE if changed else 'white',
            selectbackground='#ffe2c0'if changed else '#205b9b')

    def refresh_section_colors(self):
        from sailors import MATE_IDS,CAPTAIN_IDS
        from fleet_difficulty import preset
        project=self.project
        changed=dict.fromkeys(self.section_buttons,False)
        if project:
            changed['characters']=any(e['id']<6 for e in project.effective_character_edits())
            changed['ships']=bool(project.ship_descriptions or project.changes()or project.availability_changes()or len(project.ships)>25 or project.portraits or project.repair_safeguard)
            from character_mods import port_shuffle,free_agent_rows,shuffled_names
            ports=port_shuffle(project.rom,project.free_agent_shuffle);names=shuffled_names(project.rom,project.free_agent_shuffle)
            from sailors import decode_sailors
            stock_names=decode_sailors(project.rom)
            changed['mates']=any(e['id']in MATE_IDS for e in project.effective_character_edits())or any(ports[r['id']]!=r['starting_port']for r in free_agent_rows(project.rom))or any(i in MATE_IDS and v['name']!=stock_names[i]['name']for i,v in names.items())
            changed['captains']=any(e['id']in CAPTAIN_IDS for e in project.effective_character_edits())or any(i in CAPTAIN_IDS and v['name']!=stock_names[i]['name']for i,v in names.items())
            changed['discoveries']=bool(__import__('discovery_content').changed_slots(project))
            changed['world']=bool(project.item_edits or project.item_price_edits or project.goods_edits or project.economy_edits)
            changed['gameplay']=bool(project.instant_shipbuilding or project.starting_gold is not None or project.fifty_year_campaign or project.fleet_control or project.fleet_difficulty or project.fleet_rules!=preset())
        icons=dict(ships='ship',mates='person',captains='captain',gameplay='game',world='anchor',library='folder',characters='person',discoveries='anchor')
        for key,button in self.section_buttons.items():
            selected=key==self.section
            button.configure(style=('Selected.'if selected else '')+('Changed.'if changed[key]else '')+'Nav.TButton',
                image=self.ui.icon(icons[key],CHANGE_ORANGE if changed[key]else '#194c85',16 if self.compact=='compact'else 22))
        if self.section=='ships':self.nav_strip.configure(background=CHANGE_ORANGE if changed['ships']else '#0869df')

    def refresh_list(self):
        if self.data_type!='ships':
            self.refresh_mate_list();return
        self.loading=True;view=self.list.yview();self.list.delete(0,'end');self.ship_rows=[]
        if self.project:
            for i,s in enumerate(self.project.ships):
                if self.search_var.get().strip().casefold()not in s['name'].casefold():continue
                changed=i>=25 or i in self.project.ship_descriptions or i in self.project.portraits or any(s[k]!=self.project.original[i][k]for k in EDIT_FIELDS)or self.project.original_availability[i]!=self.project.stock_availability[i]
                self.ship_rows.append(i)
                self.list.insert('end',f'{i+1:02d}  {s["name"]}'+('  NEW'if i>=25 else '  *'if changed else ''))
                self.color_browser_row(changed)
        if self.selected in self.ship_rows:self.select_browser_row(self.ship_rows.index(self.selected))
        if view:self.list.yview_moveto(view[0])
        self.loading=False
    def open_item_seed(self):
        if not self.project:return
        from item_shuffle_view import open_shuffle
        open_shuffle(self)

    def refresh_easy_preset(self):
        from custom_preset_view import refresh
        refresh(self)

    def apply_easy_preset(self):
        from custom_preset_view import load_selected
        load_selected(self)

    def toggle_custom_ships(self):
        if not self.project:return
        wanted=self.custom_ships_var.get()
        if self.auto_timer is not None:self.root.after_cancel(self.auto_timer);self.auto_timer=None
        try:self.commit()
        except ValueError as error:self.custom_ships_var.set(self.project.custom_ships);self.fail(error);return
        self.project.custom_ships=wanted;self.show(self.selected)

    def show(self,i):
        self.auto_loading=True
        self.selected=i;s=self.project.ships[i]
        self.custom_ships_box.configure(state='normal');self.custom_ships_var.set(self.project.custom_ships)
        for button in (self.add_button,self.apply_button,self.restore_button):button.configure(state='normal')
        self.remove_button.configure(state='normal'if i>=25 else 'disabled')
        if i>=25:self.remove_button.pack(fill='x')
        else:self.remove_button.pack_forget()
        if self.displayed_ship!=i:
            for scroll in self.scrollers:scroll.canvas.xview_moveto(0);scroll.canvas.yview_moveto(0)
            self.displayed_ship=i
        self.fit_loading=True
        self.repair_check.configure(state='normal');self.repair_var.set(self.project.repair_safeguard)
        self.fleet_check.configure(state='normal');self.fleet_var.set(self.project.fleet_control)
        self.difficulty_check.configure(state='normal');self.difficulty_var.set(self.project.fleet_difficulty)
        self.sync_difficulty_state()
        self.heading.configure(text=s['name'])
        self.graphics_heading.configure(text=s['name']+' — Graphics')
        kind='Added ship'if i>=25 else 'Library ship'if i in self.project.library_bases else 'Original ship'
        self.record_heading.configure(text=f'{kind} · Ship ID {i+1:02d}')
        family=self.project.original[self.project.library_bases.get(i,s['base_hull']if i>=25 else i)]['name']
        self.ship_family.configure(text='Visual family: '+family)
        for k in FIELDS:self.entries[k].configure(state='normal');self.vars[k].set(str(s[k]/10000).rstrip('0').rstrip('.')if k=='price_gold'else str(s[k]))
        extra=i>=25
        self.fixed.configure(text='Edit starting guns and crew spaces. Cargo is calculated from the remaining capacity.')
        for k,v in self.extra_vars.items():
            v.set(str(s['capacity']-s['max_guns']-s['max_crew'])if k=='yard_cargo'else str(s[k]))
            state='readonly'if k in ('factory_cargo','yard_cargo')else 'normal'
            self.extra_entries[k].configure(state=state)
        self.fit_loading=False
        self.show_description()
        self.availability_heading.configure(text=f'New-build availability: {s["name"]}')
        self.base_combo.configure(values=[f'{n:02d} - {r["name"]}'for n,r in enumerate(self.project.original)],state='readonly'if extra else 'disabled')
        self.base_combo.current(self.project.library_bases.get(i,s['base_hull']if extra else i))
        self.import_portrait_button.configure(state='normal');self.show_portrait()
        offer=s if extra else self.project.original_availability[i]
        self.industry_var.set(str(offer['industry']));self.industry_entry.configure(state='normal')
        self.port_list.configure(state='normal');self.port_list.delete(0,'end')
        for p in ports(self.project.economy_rom()):self.port_list.insert('end',f'{p["name"]} — industry {p["industry"]}'+(' (fixed capital)'if p['capital']else ''))
        for p in offer['ports']:self.port_list.selection_set(p)
        self.show_port_selection()
        if offer['ports'] and not(i<25 and __import__('shipbuilding_shuffle').hidden(self.project)):self.port_list.see(offer['ports'][0])
        if not self.project.custom_ships:
            for widget in [*self.entries.values(),*self.extra_entries.values(),self.base_combo,self.industry_entry,self.add_button,self.remove_button,self.apply_button,self.restore_button,self.import_portrait_button,self.restore_portrait_button]:widget.configure(state='disabled')
        if i<25 and __import__('shipbuilding_shuffle').hidden(self.project):
            self.port_list.selection_clear(0,'end');self.port_list.configure(state='disabled');self.industry_entry.configure(state='readonly'if self.project.custom_ships else 'disabled');self.show_port_selection()
        self.update_status();self.auto_loading=False
    def show_description(self):
        import ship_descriptions as sd
        self.description_text.configure(state='normal')
        self.description_text.delete('1.0','end');self.description_text.insert('1.0',sd.text(self.project,self.selected))
        self.description_text.edit_modified(False);self.description_text.edit_reset()
        self.description_text.configure(state='normal'if self.project.custom_ships else 'disabled',background='white'if self.project.custom_ships else '#edf1f7')
        self.restore_description_button.configure(state='normal'if self.project.custom_ships else 'disabled')

    def restore_description(self):
        if not self.project or not self.project.custom_ships:return
        self.cancel_auto_edit();self.project.ship_descriptions.pop(self.selected,None)
        self.auto_loading=True;self.show_description();self.auto_loading=False
        self.refresh_list();self.update_status()

    def show_portrait(self):
        if not self.project or self.selected is None:return
        i=self.selected
        raw=self.project.portrait_raw(i)
        if i>=25 and i not in self.project.portraits and self.base_combo.current()>=0:
            raw=portraits.original_raw(self.project.rom,self.base_combo.current())
        self.portrait_photo=ImageTk.PhotoImage(portraits.image(raw,self.project.rom,4),master=self.root)
        self.portrait_label.configure(image=self.portrait_photo,text='')
        self.spec_portrait_scale=3 if self.scrollers[0].canvas.winfo_width()>=820 else 2
        self.spec_portrait_photo=ImageTk.PhotoImage(portraits.image(raw,self.project.rom,self.spec_portrait_scale),master=self.root)
        self.spec_portrait.configure(image=self.spec_portrait_photo,text='',width='')
        custom=i in self.project.portraits
        self.portrait_note.configure(text='Custom portrait — exact game pixels.'if custom else 'Original portrait — exact game pixels.')
        self.restore_portrait_button.configure(state='normal'if custom and self.project.custom_ships else 'disabled')
    def import_portrait(self):
        if not self.project or not self.project.custom_ships:return
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
        if not self.project or not self.project.custom_ships:return
        if not self.project or self.selected is None:return
        if self.selected in self.project.library_bases:
            self.library.restore_original(self.selected);return
        self.project.ship_descriptions.pop(self.selected,None)
        self.project.restore_portrait(self.selected);self.show_portrait();self.refresh_list();self.update_status()
    def show_port_selection(self,event=None):
        hidden=self.project and self.selected is not None and self.selected<25 and __import__('shipbuilding_shuffle').hidden(self.project)
        selected=self.port_list.curselection()
        # Disabled Tk lists suppress selection colors. Keep the widget drawable
        # and scrollable, with selection-changing input blocked while locked.
        self.port_list_locked=bool(hidden or self.project is None or not self.project.custom_ships)
        if hidden:
            self.port_list.configure(state='normal');self.port_list.selection_clear(0,'end')
        self.port_list.configure(state='disabled'if hidden else 'normal',selectbackground='#dbeafe'if self.port_list_locked else '#205b9b')
        if hidden:self.port_summary.configure(text='Building locations hidden by blind shuffle.');return
        names=[ports(self.project.rom)[p]['name']for p in selected]if self.project else []
        summary=', '.join(names)if len(names)<=4 else f'{len(names)} ports selected · highlighted in the list below'
        self.port_summary.configure(text='Selected ports: '+(summary if names else 'none'))
        if event is not None:self.schedule_auto_edit()
    def sync_fit(self,changed):
        if self.fit_loading or self.fit_syncing or self.project is None:return
        try:
            self.fit_syncing=True
            if changed=='max_crew'and self.selected is not None:
                maximum_crew=int(self.vars['max_crew'].get());starting=int(self.extra_vars['factory_crew'].get())
                previous=self.project.ships[self.selected]
                if 10<=maximum_crew<=500 and maximum_crew>=int(self.vars['min_crew'].get()) and maximum_crew%10==0 and maximum_crew!=previous['max_crew']and starting==previous['factory_crew']and starting>maximum_crew:
                    self.extra_vars['factory_crew'].set(str(maximum_crew))
            used=int(self.extra_vars['factory_guns'].get())+int(self.extra_vars['factory_crew'].get())
            maximum=int(self.vars['max_guns'].get())+int(self.vars['max_crew'].get())
            total=int(self.extra_vars['capacity'].get())
            self.extra_vars['factory_cargo'].set(str(total-used))
            self.extra_vars['yard_cargo'].set(str(total-maximum))
        except ValueError:pass
        finally:self.fit_syncing=False
    def commit(self):
        from custom_preset_view import seed_changed
        seed_changed(self,strict=True)
        if hasattr(self,'characters'):self.characters.commit()
        if hasattr(self,'world_gameplay_settings'):self.world_gameplay_settings.flush()
        self.world.flush_goods_gate(strict=True);self.world.economy_panel.flush(strict=True);self.world.item_editor.flush(strict=True)
        self.commit_character()
        if self.project is None or self.selected is None:return
        self.project.repair_safeguard=self.repair_var.get();self.project.fleet_control=self.fleet_var.get();self.project.fleet_difficulty=self.difficulty_var.get()
        if not self.project.custom_ships:return
        values={}
        for k in FIELDS:
            value=self.vars[k].get().strip()
            if k=='name':values[k]=value
            elif k=='price_gold':values[k]=price_from_bars(value)
            else:
                try:values[k]=int(value)
                except ValueError:raise ValueError(f'{LABELS[k]} needs a whole number.')
        for k,v in self.extra_vars.items():
            if k in ('capacity','factory_guns','factory_crew'):
                try:values[k]=int(v.get())
                except ValueError:raise ValueError(k.replace('_',' ')+' needs a whole number.')
        if self.selected is not None:
            try:values['industry']=int(self.industry_var.get())
            except ValueError:raise ValueError('Industry needs a whole number.')
            if self.selected>=25:values['base_hull']=self.base_combo.current()
            if self.selected>=25 or not __import__('shipbuilding_shuffle').hidden(self.project):values['ports']=list(self.port_list.curselection())
        import ship_descriptions as sd
        description=sd.validate(' '.join(self.description_text.get('1.0','end-1c').split()))
        follow_default=self.selected not in self.project.ship_descriptions and description==sd.default_text(self.project,self.selected)
        self.project.update(self.selected,values)
        # Keep calculated/read-only fields aligned with the committed record,
        # including after an incomplete lower-capacity edit is corrected.
        loading=self.fit_loading;self.fit_loading=True
        try:
            fitted=self.project.ships[self.selected]
            for key,value in (('factory_crew',fitted['factory_crew']),('factory_cargo',fitted['factory_cargo']),
                              ('yard_cargo',fitted['capacity']-fitted['max_guns']-fitted['max_crew'])):
                if self.extra_vars[key].get()!=str(value):self.extra_vars[key].set(str(value))
        finally:self.fit_loading=loading
        if not follow_default:sd.set_text(self.project,self.selected,description)
        elif description!=sd.default_text(self.project,self.selected):
            self.auto_loading=True;self.show_description();self.auto_loading=False
        self.project.repair_safeguard=self.repair_var.get();self.project.fleet_control=self.fleet_var.get();self.project.fleet_difficulty=self.difficulty_var.get()
    def refresh_active_changes(self):
        if not self.project:
            self.active_changes_text.configure(text='Open a stock ROM to begin.');return
        project=self.project;lines=[]
        for enabled,label in [(project.instant_shipbuilding,'Instant shipbuilding'),(project.fifty_year_campaign,'50-year campaign'),(project.discovery_easy,'Discovery difficulty: 10'),(project.discovery_rewrites,'Rewritten discovery descriptions'),(project.repair_safeguard,'Repair Safeguard'),(project.fleet_control,'Fleet Control'),(project.fleet_difficulty,'Custom Fleets'),(project.item_seed is not None,'Item seed shuffle'+(' (blind)'if project.item_blind else ' ('+project.item_seed+')'if project.item_seed else '')),(project.free_agent_shuffle['enabled'],'People seed shuffle'+(' (blind)'if project.free_agent_shuffle['blind']else ''))]:
            if enabled:lines.append('• '+label)
        if project.starting_gold is not None:lines.append('• Starting gold: '+__import__('starting_gold').bars(project.starting_gold)+' bars')
        if project.goods_shuffle['seed']is not None:lines.append('• Goods shuffle: '+project.goods_shuffle['mode']+(' (blind)'if project.goods_shuffle.get('blind',False)else ' ('+project.goods_shuffle['seed']+')'))
        if project.free_agent_shuffle.get('mate_skills'):lines.append('• Mate skills shuffled')
        if project.free_agent_shuffle.get('captain_skills'):lines.append('• Fleet captain skills shuffled')
        if project.free_agent_shuffle.get('mate_stats'):lines.append('• Mate stats shuffled')
        if project.free_agent_shuffle.get('captain_stats'):lines.append('• Fleet captain stats shuffled')
        if project.free_agent_shuffle.get('names'):lines.append('• Mate names shuffled')
        if project.free_agent_shuffle.get('captain_names'):lines.append('• Fleet captain names shuffled')
        edited=len(set(project.ship_descriptions)|{r['id']for r in project.changes()}|{r['id']for r in project.availability_changes()})
        for count,label in [(edited,'Ships edited'),(len(project.ships)-25,'Ships added'),(len(project.economy_edits),'Port economies edited'),(len(project.goods_edits),'Goods ports edited'),(len(project.item_edits),'Item ports edited'),(len(project.item_price_edits),'Item costs edited'),(len(project.discovery_entries),'Discoveries replaced'),(len(project.portraits),'Custom portraits'),(len({r['id']for r in project.effective_character_edits()}),'Characters edited')]:
            if count:lines.append(f'• {label}: {count}')
        self.active_changes_text.configure(text='\n'.join(lines)if lines else 'No active changes.',wraplength=max(150,self.sidebar.winfo_width()-28))

    def cancel_auto_edit(self):
        if hasattr(self,'characters'):self.characters.cancel()
        if hasattr(self,'world_gameplay_settings'):self.world_gameplay_settings.cancel(discard=True)
        if self.auto_timer is not None:self.root.after_cancel(self.auto_timer);self.auto_timer=None

    def reload_project_view(self):
        self.auto_loading=True
        self.selected=min(self.selected or 0,len(self.project.ships)-1)
        self.show(self.selected)
        if self.data_type in ('mates','captains'):self.show_mate(self.character_selection())
        self.refresh_list();self.update_status();self.auto_loading=False

    def section_menu(self,event,section):
        menu=tk.Menu(self.root,tearoff=False)
        if section=='library':
            self.library.refresh()
            menu.add_command(label='Delete',state='normal'if self.project and self.library.store else 'disabled',command=self.library.clear_library)
        else:
            menu.add_command(label='Restore to defaults',state='normal'if self.project else 'disabled',command=lambda:self.reset_section(section))
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
        return 'break'

    def restore_defaults(self):
        if not self.project:return
        detail='Reset the current project to the original game settings?\n\nAll project edits will be removed, including added ships, custom discoveries, character and world edits, shuffles, and gameplay options.\n\nYour Library, saved presets, saved project files, exported ROMs, and save games will not be changed.\n\nChanges are saved to the project file only when you choose Save project.'
        if not messagebox.askyesno('Restore all settings to default',detail,parent=self.root):return
        self.cancel_auto_edit();self.world.economy_panel.cancel()
        self.world.cancel_goods_edit();self.world.item_editor.cancel()
        project=self.project
        project.ships=copy.deepcopy(project.original);project.ship_identities=[__import__('content_library').stock_id(i)for i in range(25)];project.library_bases={};project.ship_descriptions={};project.original_availability=copy.deepcopy(project.stock_availability);project.shipbuilding_shuffle=__import__('shipbuilding_shuffle').default()
        project.discovery_easy=False;project.instant_shipbuilding=False;project.starting_gold=None;project.fifty_year_campaign=False;project.discovery_easy=False;project.discovery_rewrites=False;project.discovery_entries={};project.discovery_identities=[__import__('discovery_content').stock_id(i)for i in range(98)]
        project.custom_discoveries=False;project.custom_ships=False;project.portraits={};project.character_edits=[];project.custom_mates=False;project.custom_captains=False;project.custom_characters=False;project.item_blind=False;project.item_special=False;project.item_special_only=False;project.item_seed=None;project.item_price_edits=[];project.item_edits=[];project.custom_items=False;project.goods_edits=[];project.economy_edits=[];project.custom_economy=False;project.custom_goods=False
        project.goods_shuffle=dict(seed=None,mode='normal')
        project.free_agent_shuffle=dict(enabled=False,blind=False,seed='0000')
        from fleet_difficulty import preset
        project.fleet_rules=preset();project.fleet_control=False;project.fleet_difficulty=False;project.repair_safeguard=False
        self.reload_project_view()

    def reset_section(self,section):
        if not self.project:return
        label={'ships':'Ships','mates':'Mates','captains':'Fleet Captains','characters':'Characters','discoveries':'Discoveries','gameplay':'Gameplay','world':'World data'}[section]
        detail={'discoveries':'Restore the original discovery pool and descriptions. Saved Library alternatives are kept.', 'characters':'Restore all six playable characters’ original stats and skills. Other sections are kept.','world':'Restore all port economies and shipbuilding industry, goods locations and requirements, and item shop locations and costs. Goods and item shuffles are turned off. Discovery replacements, ships, character edits, fleet settings, Library content and presets are kept.','ships':'Restore all original ships, availability and portraits, and remove added ships. Fleet choices follow restored original ships; choices using removed custom ships return to No change.',
                'mates':'Restore manual mate attribute and skill edits. People seed shuffle options are kept.',
                'captains':'Restore manual captain attribute and skill edits. People seed shuffle options are kept.',
                'gameplay':'Turn off Fleet Control, custom fleets, people shuffle and active goods/item seed shuffles, and optional campaign/discovery settings, and restore the default fleet choices. Ship settings, Repair Safeguard and character edits are kept.'}[section]
        if not messagebox.askyesno('Reset '+label,detail+'\n\nReset this section?' ,parent=self.root):return
        self.cancel_auto_edit();self.auto_edit()
        project=self.project
        if section=='discoveries':
            project.custom_discoveries=False
            project.discovery_easy=False;project.discovery_rewrites=False;project.discovery_entries={};project.discovery_identities=[__import__('discovery_content').stock_id(i)for i in range(98)]
        elif section=='world':
            self.world.economy_panel.cancel()
            self.world.cancel_goods_edit();self.world.item_editor.cancel()
            project.goods_shuffle=dict(seed=None,mode='normal')
            project.item_blind=False;project.item_special=False;project.item_special_only=False;project.item_seed=None;project.item_price_edits=[];project.item_edits=[];project.custom_items=False;project.goods_edits=[];project.economy_edits=[];project.custom_economy=False;project.custom_goods=False
        elif section=='ships':
            from library_project import restore_stock_ships
            restore_stock_ships(project)
        elif section in ('mates','captains','characters'):
            from sailors import MATE_IDS,CAPTAIN_IDS,PROTAGONIST_IDS
            ids=PROTAGONIST_IDS if section=='characters'else MATE_IDS if section=='mates'else CAPTAIN_IDS
            project.character_edits=[e for e in project.character_edits if e['id']not in ids];setattr(project,'custom_'+section,False)
        else:
            try:project.clear_shipbuilding_shuffle()
            except ValueError as error:self.fail(error);return
            from fleet_difficulty import preset
            project.discovery_easy=False;project.instant_shipbuilding=False;project.starting_gold=None;project.fifty_year_campaign=False;project.discovery_rewrites=False;project.fleet_control=False;project.fleet_difficulty=False
            project.fleet_rules=preset();project.free_agent_shuffle=dict(enabled=False,blind=False,seed='0000')
            if project.goods_shuffle['seed']is not None:
                project.goods_edits=[];project.goods_shuffle=dict(seed=None,mode='normal')
            if project.item_seed is not None:
                project.item_edits=[];project.item_seed=None;project.item_blind=False;project.item_special=False;project.item_special_only=False
        self.reload_project_view()

    def refresh_edit_colors(self):
        if not self.project:return
        def color(widget,changed,base=None):
            base=base or ('TSpinbox'if widget.winfo_class()=='TSpinbox'else 'TEntry')
            if widget in self.entries.values()or widget in self.extra_entries.values():base='Ship.'+base
            widget.configure(style=('Changed.'if changed else '')+base)
        if self.selected is not None:
            i=self.selected;ship=self.project.ships[i];stock=self.project.original[i if i<25 else ship['base_hull']]
            for key,widget in self.entries.items():color(widget,i>=25 or ship[key]!=stock[key])
            for key,widget in self.extra_entries.items():
                value=ship['capacity']-ship['max_guns']-ship['max_crew']if key=='yard_cargo'else ship[key]
                normal=stock['capacity']-stock['max_guns']-stock['max_crew']if key=='yard_cargo'else stock[key]
                color(widget,i>=25 or value!=normal)
            offer=ship if i>=25 else self.project.original_availability[i]
            changed=i>=25 or offer['industry']!=self.project.stock_availability[i]['industry']
            color(self.industry_entry,changed)
            port_color=CHANGE_ORANGE if i>=25 or offer['ports']!=self.project.stock_availability[i]['ports']else '#17243d'
            self.port_list.configure(foreground=port_color,selectforeground=port_color if self.port_list_locked else 'white')
        if self.section in ('mates','captains')and self.character_selection()is not None:
            from sailors import decode_sailors,ATTRIBUTES,SKILLS
            stock=decode_sailors(self.project.rom)[self.character_selection()];record=self.project.character_record(stock['id'])
            self.mate_field_widgets['starting_port_name'][1].configure(foreground=CHANGE_ORANGE if record['starting_port']!=stock['starting_port']else '#17243d')
            self.mate_heading.configure(foreground=CHANGE_ORANGE if record['name']!=stock['name']else '#17243d')
            for key in ATTRIBUTES:color(self.mate_field_widgets[key][1],record[key]!=stock[key])
            for key,label,bit in SKILLS:color(self.skill_checks[key],bool((record['skills']^stock['skills'])&bit),'Card.TCheckbutton')
        if self.project:
            changed=self.selected in self.project.ship_descriptions
            self.description_text.configure(foreground=CHANGE_ORANGE if changed else '#17243d')
        for widget,enabled in [(self.repair_check,self.project.repair_safeguard),(self.fleet_check,self.project.fleet_control),(self.difficulty_check,self.project.fleet_difficulty)]:
            color(widget,enabled,'Inline.Card.TCheckbutton'if widget==self.difficulty_check else 'TCheckbutton')

    def update_status(self):
        from custom_preset_view import refresh as refresh_custom_presets
        refresh_custom_presets(self)
        self.gameplay_goods_shuffle_button.configure(state='normal'if self.project else 'disabled')
        self.gameplay_item_shuffle_button.configure(state='normal'if self.project else 'disabled')
        self.refresh_edit_colors();self.refresh_section_colors()
        self.gameplay_reset_button.configure(state='normal'if self.project else 'disabled')
        self.restore_defaults_button.configure(state='normal'if self.project else 'disabled')
        self.sync_shuffle_state()
        self.world_gameplay_settings.sync()
        self.gameplay_apply_button.configure(state='normal'if self.project else 'disabled')
        if self.section=='discoveries':
            self.discoveries.refresh();self.status.configure(text='Discoveries: current project pool • Fixed original locations • New game recommended');return
        if self.section=='characters':
            self.characters.refresh();self.status.configure(text='Characters: six playable protagonists • Starting stats and skills • New game required');return
        if self.section=='library':
            self.library.refresh();self.status.configure(text='Library: reusable user content • Projects contain independent copies');return
        if self.section=='world':
            self.world.refresh()
            if self.world.view=='Economy':self.status.configure(text='Economy: starting goods economy and shipbuilding industry • Regional batch preview before applying');return
            if self.world.view=='Items':self.status.configure(text='Items: edit selling ports and regular or early-morning offers • Port Information updates automatically');return
            if self.world.view=='Goods':self.status.configure(text='Goods: edit selling ports and required economy • Port Information updates automatically');return
            self.status.configure(text=('World: '+self.world.view+' catalogue • Read-only'if self.world.view in ('Discoveries','Goods','Items')else 'Port Information: current project • Read-only')if self.project else 'Open a stock USA ROM to view the world.');return
        if self.section=='gameplay':
            self.refresh_active_changes()
            self.status.configure(text='Gameplay settings apply to the whole exported game.'if self.project else 'Open a stock USA ROM to begin.');return
        if self.data_type!='ships':
            self.status.configure(text=(('Fleet Captains: 64'if self.data_type=='captains'else 'Mates: 50')+'   |   Edited characters: '+str(len({e['id']for e in self.project.character_edits}))if self.project else 'Open a stock USA ROM to view sailors.'));return
        n=len({i for i in self.project.ship_descriptions if i<25}|{c['id']for c in self.project.changes()}|{c['id']for c in self.project.availability_changes()}|{i for i in self.project.portraits if i<25})if self.project else 0
        added=len(self.project.ships)-25 if self.project else 0
        characters=len({e['id']for e in self.project.character_edits})if self.project else 0
        self.status.configure(text=f'Edited originals: {n}   |   Added ships: {added}/10   |   Edited sailors: {characters}   |   Source ROM unchanged')
    def pick(self,event=None):
        if self.data_type!='ships':
            if not self.loading and self.project and self.list.curselection():
                i=self.mate_rows[self.list.curselection()[0]]
                try:self.commit_character()
                except Exception as e:
                    self.fail(e);self.list.selection_clear(0,'end')
                    if self.character_selection()in self.mate_rows:self.select_browser_row(self.mate_rows.index(self.character_selection()))
                    return
                self.show_mate(i);self.refresh_list();self.update_status()
            return
        if self.loading or not self.project or not self.list.curselection():return
        index=self.ship_rows[self.list.curselection()[0]]
        try:self.commit()
        except Exception as e:
            self.fail(e);self.list.selection_clear(0,'end')
            if self.selected in self.ship_rows:self.select_browser_row(self.ship_rows.index(self.selected))
            return
        self.selected=index;self.refresh_list();self.show(index)
    def apply(self):
        try:self.commit();self.refresh_list();self.show(self.selected)if self.project else None
        except Exception as e:self.fail(e)
    def allow_replace(self):
        if not self.project:return True
        try:self.commit()
        except Exception as e:self.fail(e);return False
        return (not self.project.discovery_easy and not self.project.item_price_edits and not self.project.instant_shipbuilding and self.project.starting_gold is None and not self.project.fifty_year_campaign and not self.project.custom_discoveries and not self.project.discovery_rewrites and not self.project.ship_descriptions and not self.project.discovery_entries and not self.project.item_edits and not self.project.custom_items and not self.project.custom_ships and not self.project.custom_characters and not self.project.custom_mates and not self.project.custom_captains and not self.project.custom_goods and not self.project.custom_economy and not self.project.economy_edits and not self.project.goods_edits and not self.project.changes()and not self.project.availability_changes()and not self.project.portraits and not self.project.character_edits and not self.project.free_agent_shuffle['enabled'] and len(self.project.ships)==25 and not self.project.repair_safeguard and not self.project.fleet_control and not self.project.fleet_difficulty and self.project.fleet_rules==__import__('fleet_difficulty').preset())or messagebox.askyesno('Leave this project?','Save your project first if you want to keep these edits. Continue?',parent=self.root)
    def open_rom(self):
        from preferences import last_rom
        previous=last_rom()
        options=dict(initialdir=str(Path(previous).parent))if previous and Path(previous).parent.is_dir()else {}
        path=filedialog.askopenfilename(title='Open original USA ROM',filetypes=[('SNES ROM or ZIP','*.sfc *.smc *.zip'),('All files','*.*')],**options)
        if not path or not self.allow_replace():return
        self.load_rom(path)

    def restore_last_rom(self):
        # Startup only: never replace an already opened or edited project.
        if self.project is not None:return
        from preferences import last_rom
        path=last_rom()
        if path:self.load_rom(path,automatic=True)

    def load_rom(self,path,automatic=False):
        try:
            from app_defaults import startup_project
            project=startup_project(path);self.project=project;self.export_preset_name=None;self.selected=0;self.source.configure(text='Stock USA ROM verified: '+Path(path).name+(' (copier header detected)'if project.header else ''))
            self.source.configure(image=self.ui.icon('check','#12a16c',20),compound='left')
            self.show(0);self.refresh_list()
            if self.data_type!='ships':self.show_mate(self.character_selection())
            from preferences import remember_rom
            if not remember_rom(path):self.status.configure(text='ROM loaded. Could not remember its path for next time.')
            return True
        except Exception as e:
            if automatic:
                self.source.configure(text='Last ROM unavailable or invalid. Open a stock USA ROM to continue.',image='')
                self.status.configure(text='Automatic ROM loading skipped. Choose Open stock ROM.')
            else:self.fail(e)
            return False
    def open_project(self):
        if not self.project:messagebox.showinfo('Open the game first','Open the original USA ROM, then open your project.',parent=self.root);return
        path=filedialog.askopenfilename(title='Open ship project',filetypes=[('Ship projects','*.json')])
        if not path or not self.allow_replace():return
        try:
            self.project.load_project(path);self.export_preset_name=None;self.selected=min(self.selected,len(self.project.ships)-1);self.refresh_list();self.show(self.selected)
            if self.data_type!='ships':self.show_mate(self.character_selection())
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
            from custom_presets import export_filename
            self.commit();path=filedialog.asksaveasfilename(title='Export a NEW game file',defaultextension='.sfc',initialfile=export_filename(getattr(self,'export_preset_name',None)),filetypes=[('Patched SNES ROM','*.sfc')])
            if not path:return
            self.project.export(path);self.refresh_list();self.update_status()
            messagebox.showinfo('Export complete','Created the new .sfc, .ips and .changes.json files.\n\nThe IPS applies to the original unheadered USA ROM. The exported SFC is already patched. Test your changes in your emulator.',parent=self.root)
        except Exception as e:self.fail(e)
    def restore(self):
        if not self.project or not self.project.custom_ships:return
        if not self.project or self.selected is None:return
        if self.selected in self.project.library_bases:
            self.library.restore_original(self.selected);return
        try:
            from library_project import restore_ship
            restore_ship(self.project,self.selected)
            self.refresh_list();self.show(self.selected)
        except Exception as error:self.fail(error)
    def add(self):
        if not self.project or not self.project.custom_ships:return
        if not self.project:return
        try:
            self.commit();base=self.selected if self.selected<25 else self.project.ships[self.selected]['base_hull']
            self.selected=self.project.add_ship(base);self.search_var.set('');self.refresh_list();self.list.see(self.ship_rows.index(self.selected));self.show(self.selected)
        except Exception as e:self.fail(e)
    def remove(self):
        if not self.project or not self.project.custom_ships:return
        if not self.project or self.selected is None:return
        try:
            self.commit()
            if any(self.selected in role for nation in self.project.fleet_rules for role in nation):raise ValueError('A Custom Fleet uses this ship. Choose another ship in Custom Fleets before removing it.')
            self.library.refresh()
            if self.library.store is None:raise ValueError('The Library must be available to preserve the outgoing ship.')
            self.library.store.archive(__import__('content_library').capture_ship(self.project,self.selected))
            self.cancel_auto_edit()
            self.project.remove_ship(self.selected);self.selected=min(self.selected,len(self.project.ships)-1);self.refresh_list();self.show(self.selected)
        except Exception as e:self.fail(e)
    def help(self):
        diagnostics.LOGGER.info('Open Help; section=%s',self.section)
        from help_view import open_help
        open_help(self)
    def close(self):
        if self.allow_replace():self.root.destroy()

def main():
    try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:pass
    if len(sys.argv)==5 and sys.argv[1]=='--library-items-test'and sys.argv[3]=='--report':
        from library_item_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--requested-changes-test'and sys.argv[3]=='--report':
        from requested_change_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--ai-presets-test'and sys.argv[3]=='--report':
        from ai_preset_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--ship-descriptions-test'and sys.argv[3]=='--report':
        from ship_description_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--startup-test'and sys.argv[3]=='--report':
        from startup_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--campaign-length-test'and sys.argv[3]=='--report':
        from campaign_length_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--discoveries-test'and sys.argv[3]=='--report':
        from discovery_view_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--discovery-rewrites-test'and sys.argv[3]=='--report':
        from discovery_rewrite_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--discovery-library-test'and sys.argv[3]=='--report':
        from discovery_library_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--characters-test'and sys.argv[3]=='--report':
        from protagonist_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--library-test'and sys.argv[3]=='--report':
        from library_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--ship-layout-test'and sys.argv[3]=='--report':
        from ship_layout_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--shipbuilding-test'and sys.argv[3]=='--report':
        from shipbuilding_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--custom-presets-test'and sys.argv[3]=='--report':
        from custom_preset_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--presets-test'and sys.argv[3]=='--report':
        from preset_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==3 and sys.argv[1]=='--help-test':
        from help_checks import run
        run(Editor,Path(sys.argv[2]));return
    if len(sys.argv)==5 and sys.argv[1]=='--world-settings-test'and sys.argv[3]=='--report':
        from world_settings_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--goods-shuffle-test'and sys.argv[3]=='--report':
        from goods_shuffle_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--item-shuffle-test'and sys.argv[3]=='--report':
        from item_shuffle_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--shuffle-options-test'and sys.argv[3]=='--report':
        from shuffle_options_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--gameplay-layout-test'and sys.argv[3]=='--report':
        from gameplay_layout_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--items-edit-test'and sys.argv[3]=='--report':
        from item_edit_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--custom-controls-test'and sys.argv[3]=='--report':
        from custom_controls_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--economy-test'and sys.argv[3]=='--report':
        from economy_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--goods-test'and sys.argv[3]=='--report':
        from goods_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--auto-test'and sys.argv[3]=='--report':
        from auto_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--world-test'and sys.argv[3]=='--report':
        from world_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--mates-test'and sys.argv[3]=='--report':
        from mate_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--workflow-test'and sys.argv[3]=='--report':
        from ui_checks import run
        run(Editor,sys.argv[2],Path(sys.argv[4]));return
    if len(sys.argv)==5 and sys.argv[1]=='--self-test'and sys.argv[3]=='--report':
        report=Path(sys.argv[4]);report.parent.mkdir(parents=True,exist_ok=True);root=None
        try:
            root=tk.Tk();root.withdraw();editor=Editor(root)
            assert root.title()=='New Horizons Editor v'+TOOL_VERSION
            editor.project=ShipProject(sys.argv[2]);editor.project.custom_ships=True;editor.selected=13;editor.refresh_list();editor.show(13)
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
    root=tk.Tk();editor=Editor(root);root.after_idle(editor.restore_last_rom);root.mainloop()

if __name__=='__main__':
    try:main()
    except Exception:
        # Automation assertions have report files and a nonzero exit status.
        # Keep the frozen crash popup for normal editor failures only.
        if len(sys.argv)>1 and sys.argv[1].startswith('--')and sys.argv[1].endswith('-test'):
            diagnostics.LOGGER.exception('Automated check failed')
            import traceback
            if sys.stderr is not None:traceback.print_exc()
            sys.exit(1)
        raise

