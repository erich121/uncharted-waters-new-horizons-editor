"""Windows editor for25 original ships and up to five additional hulls."""
import ctypes,sys,json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from backend import ShipProject,FIELDS,EDIT_FIELDS,ports,price_from_bars,TOOL_VERSION

LABELS={'name':'Ship name','hull':'Hull strength','turning':'Turning','power':'Sailing power',
    'max_guns':'Maximum guns','min_crew':'Minimum sailors','max_crew':'Maximum crew spaces','price_gold':'Base price in gold bars'}
BUILD_ID='layout4'

class ScrollableWindow(ttk.Frame):
    """Keep the whole editor reachable on small or scaled Windows displays."""
    def __init__(self,root):
        super().__init__(root);self.pack(side='left',fill='both',expand=True)
        self.rowconfigure(0,weight=1);self.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,highlightthickness=0)
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
    def _horizontal(self,*args):self.horizontal.set(*args)
    def resize(self,event=None):
        width=max(self.content.winfo_reqwidth(),self.canvas.winfo_width())
        height=max(self.content.winfo_reqheight(),self.canvas.winfo_height())
        self.canvas.itemconfigure(self.window,width=width,height=height)
        self.canvas.configure(scrollregion=(0,0,width,height))
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
        if widget.winfo_class()not in ('TEntry','TCombobox','TButton','Entry','Button'):return
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
        root.title('New Horizons Ship Editor v'+TOOL_VERSION+' ['+BUILD_ID+']')
        root.geometry(f'{min(1100,max(640,root.winfo_screenwidth()-80))}x{min(820,max(480,root.winfo_screenheight()-120))}')
        root.minsize(640,480)
        root.protocol('WM_DELETE_WINDOW',self.close)
        style=ttk.Style();style.theme_use('vista'if 'vista'in style.theme_names()else 'clam')
        style.configure('TLabel',font=('Segoe UI',10));style.configure('TButton',padding=7)
        top=ttk.Frame(root,padding=(16,12));top.pack(fill='x')
        title=ttk.Frame(top);title.pack(fill='x')
        self.title_label=ttk.Label(title,text='New Horizons Ship Editor',font=('Segoe UI',18,'bold'),wraplength=420);self.title_label.pack(side='left',anchor='w')
        self.build_label=ttk.Label(title,text='v'+TOOL_VERSION+'  •  '+BUILD_ID,foreground='#596579');self.build_label.pack(side='right',anchor='e')
        bar=ttk.Frame(top);bar.pack(fill='x')
        self.toolbar_buttons=[];self.toolbar_layout=None
        for n,(title,call)in enumerate([('Open stock ROM',self.open_rom),('Open project',self.open_project),('Save project',self.save_project),('Export ROM and IPS',self.export),('Help',self.help)]):
            b=ttk.Button(bar,text=title,command=call);b.grid(row=0,column=n,padx=(0,6),pady=8);self.toolbar_buttons.append(b)
        def arrange_toolbar(event):
            row=column=used=0;layout=[]
            for b in self.toolbar_buttons:
                width=b.winfo_reqwidth()+6
                if used and used+width>event.width:row+=1;column=used=0
                layout.append((row,column));used+=width;column+=1
            if layout==self.toolbar_layout:return
            self.toolbar_layout=layout
            for b,(r,c)in zip(self.toolbar_buttons,layout):b.grid(row=r,column=c,sticky='w',padx=(0,6),pady=4)
        bar.bind('<Configure>',arrange_toolbar)
        self.source=ttk.Label(top,text='Open your original USA .sfc, .smc or ZIP to begin.',wraplength=580);self.source.pack(anchor='w',pady=(12,0))
        self.status=ttk.Label(root,text='Open a stock USA ROM to begin.',padding=(16,8),wraplength=580);self.status.pack(side='bottom',fill='x')
        body=ttk.Frame(root,padding=(16,0,16,0));body.pack(fill='both',expand=True)
        left=ttk.Frame(body);left.pack(side='left',fill='y',padx=(0,20))
        remove=ttk.Frame(left);remove.pack(side='bottom',fill='x',pady=(8,0))
        self.remove_button=ttk.Button(remove,text='Remove added ship',command=self.remove);self.remove_button.pack(fill='x')
        self.ships_heading=ttk.Label(left,text='Ships',font=('Segoe UI',12,'bold'));self.ships_heading.pack(anchor='w',pady=(0,6))
        self.add_button=ttk.Button(left,text='Add ship (up to 5)',command=self.add);self.add_button.pack(fill='x',pady=(0,8))
        ship_frame=ttk.Frame(left);ship_frame.pack(fill='both',expand=True)
        self.list=tk.Listbox(ship_frame,width=27,height=25,font=('Segoe UI',10),exportselection=False,
            background='white',foreground='black',selectbackground='#205b9b',selectforeground='white')
        self.list.pack(side='left',fill='both',expand=True);self.list.bind('<<ListboxSelect>>',self.pick)
        ship_scroll=ttk.Scrollbar(ship_frame,command=self.list.yview);ship_scroll.pack(side='right',fill='y');self.list.configure(yscrollcommand=ship_scroll.set)
        settings=ttk.Frame(body);settings.pack(side='left',fill='both',expand=True)
        actions=ttk.Frame(settings);actions.pack(side='bottom',fill='x',pady=(8,0))
        self.apply_button=ttk.Button(actions,text='Apply ship changes',command=self.apply);self.apply_button.grid(row=0,column=0,sticky='w',padx=(0,8),pady=2)
        self.restore_button=ttk.Button(actions,text='Restore selected ship',command=self.restore);self.restore_button.grid(row=0,column=1,sticky='w',pady=2)
        def arrange_actions(event):
            narrow=self.apply_button.winfo_reqwidth()+self.restore_button.winfo_reqwidth()+8>event.width
            self.restore_button.grid(row=1 if narrow else 0,column=0 if narrow else 1,sticky='w',pady=2)
        actions.bind('<Configure>',arrange_actions)
        notebook=ttk.Notebook(settings);self.notebook=notebook;notebook.pack(fill='both',expand=True)
        spec_tab=ttk.Frame(notebook);port_tab=ttk.Frame(notebook)
        notebook.add(spec_tab,text='Specifications');notebook.add(port_tab,text='Availability and graphics')
        self.scrollers=[ScrollableWindow(spec_tab),ScrollableWindow(port_tab)];self.scroll=self.scrollers[0]
        def switch_tab(event):
            self.scroll=self.scrollers[notebook.index('current')];self.scroll.resize()
        notebook.bind('<<NotebookTabChanged>>',switch_tab)
        right=ttk.Frame(self.scrollers[0].content,padding=12);right.pack(fill='both',expand=True)
        availability=ttk.Frame(self.scrollers[1].content,padding=12);availability.pack(fill='both',expand=True)
        self.heading=ttk.Label(right,text='No game loaded',font=('Segoe UI',15,'bold'));self.heading.pack(anchor='w',pady=(0,10))
        self.vars={};self.entries={};self.extra_vars={};self.extra_entries={}
        self.fit_loading=False;self.fit_syncing=False
        def section(parent,title):
            frame=ttk.LabelFrame(parent,text=title,padding=(12,8));frame.pack(fill='x',pady=(0,10));frame.columnconfigure(1,weight=1)
            return frame
        def field(frame,row,key,title,hint,extra=False):
            label=ttk.Frame(frame);label.grid(row=row,column=0,sticky='w',pady=5,padx=(0,16))
            ttk.Label(label,text=title,wraplength=180).pack(anchor='w')
            if hint:ttk.Label(label,text=hint,font=('Segoe UI',8),foreground='#687386',wraplength=180).pack(anchor='w',pady=(1,0))
            v=tk.StringVar();e=ttk.Entry(frame,textvariable=v,width=18,state='disabled');e.grid(row=row,column=1,sticky='w',pady=5)
            (self.extra_vars if extra else self.vars)[key]=v;(self.extra_entries if extra else self.entries)[key]=e
        identity=section(right,'Name and price')
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
        self.fixed=ttk.Label(fit,text='',wraplength=340,foreground='#596579');self.fixed.grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,4))
        field(fit,1,'factory_guns','Starting guns','Spaces fitted when the ship is built',True)
        field(fit,2,'factory_crew','Starting crew spaces','Crew allocation when the ship is built',True)
        for k in ('capacity','factory_guns','factory_crew'):self.extra_vars[k].trace_add('write',lambda *args,key=k:self.sync_fit(key))
        for k in ('max_guns','max_crew'):self.vars[k].trace_add('write',lambda *args,key=k:self.sync_fit(key))
        self.availability_heading=ttk.Label(availability,text='Select an added ship to change its ports.',wraplength=340,font=('Segoe UI',12,'bold'));self.availability_heading.pack(anchor='w',pady=(0,10))
        graphics=section(availability,'Artwork and ship description')
        ttk.Label(graphics,text='Reuse an original ship’s portrait, map/battle icons and description. Your specifications stay unchanged.',wraplength=340).pack(anchor='w')
        self.base_var=tk.StringVar();self.base_combo=ttk.Combobox(graphics,textvariable=self.base_var,state='disabled',width=28);self.base_combo.pack(fill='x',pady=(8,0))
        unlock=section(availability,'Industry requirement')
        ttk.Label(unlock,text='Minimum industry to build this ship',wraplength=340).pack(anchor='w')
        self.industry_var=tk.StringVar();self.industry_entry=ttk.Entry(unlock,textvariable=self.industry_var,state='disabled',width=18);self.industry_entry.pack(anchor='w',pady=6)
        ttk.Label(unlock,text='0-1,000, in steps of 10. Applies to every selected port. Construction time follows hull strength and port industry.',wraplength=340,foreground='#596579').pack(anchor='w')
        locations=section(availability,'Shipyard locations')
        ttk.Label(locations,text='Click to select one port. Ctrl-click to add or remove ports. Fixed capitals cannot be developed.',wraplength=340).pack(anchor='w',pady=(0,6))
        self.port_summary=ttk.Label(locations,text='',wraplength=340);self.port_summary.pack(anchor='w',pady=(0,8))
        port_frame=ttk.Frame(locations);port_frame.pack(fill='both',expand=True)
        self.port_list=tk.Listbox(port_frame,selectmode='extended',exportselection=False,font=('Segoe UI',10),height=12,width=32);self.port_list.pack(side='left',fill='both',expand=True)
        self.port_list.bind('<<ListboxSelect>>',self.show_port_selection)
        scroll=ttk.Scrollbar(port_frame,command=self.port_list.yview);scroll.pack(side='right',fill='y');self.port_list.configure(yscrollcommand=scroll.set)
        self.compact=None
        def resize_density(event):
            if event.widget!=root:return
            compact=event.width<850 or event.height<620
            if compact==self.compact:return
            self.compact=compact
            self.title_label.configure(font=('Segoe UI',14 if compact else 18,'bold'))
            self.build_label.configure(font=('Segoe UI',8 if compact else 10))
            top.configure(padding=(16,6 if compact else 12))
            self.source.configure(font=('Segoe UI',8 if compact else 10))
            self.status.configure(font=('Segoe UI',8 if compact else 10),padding=(16,4 if compact else 8))
            self.ships_heading.configure(font=('Segoe UI',10 if compact else 12,'bold'))
            self.list.configure(width=22 if compact else 27,font=('Segoe UI',9 if compact else 10))
            style.configure('TButton',font=('Segoe UI',9 if compact else 10),padding=(6,3)if compact else 7)
        root.bind('<Configure>',resize_density,add='+')

    def fail(self,e):messagebox.showerror('Check your values',str(e),parent=self.root)
    def refresh_list(self):
        self.loading=True;self.list.delete(0,'end')
        if self.project:
            for i,s in enumerate(self.project.ships):
                changed=i>=25 or any(s[k]!=self.project.original[i][k]for k in EDIT_FIELDS)
                self.list.insert('end',f'{i+1:02d}  {s["name"]}'+('  NEW'if i>=25 else '  *'if changed else ''))
        if self.selected is not None:self.list.selection_set(self.selected);self.list.see(self.selected)
        self.loading=False
    def show(self,i):
        self.selected=i;s=self.project.ships[i]
        if self.displayed_ship!=i:
            for scroll in self.scrollers:scroll.canvas.xview_moveto(0);scroll.canvas.yview_moveto(0)
            self.displayed_ship=i
        self.fit_loading=True
        self.heading.configure(text=s['name'])
        for k in FIELDS:self.entries[k].configure(state='normal');self.vars[k].set(str(s[k]/10000).rstrip('0').rstrip('.')if k=='price_gold'else str(s[k]))
        extra=i>=25
        self.fixed.configure(text='Editable for added ships. Cargo is calculated automatically.'if extra else 'Original starting guns and crew are read-only.')
        for k,v in self.extra_vars.items():
            v.set(str(s['capacity']-s['max_guns']-s['max_crew'])if k=='yard_cargo'else str(s[k]))
            state='readonly'if k in ('factory_cargo','yard_cargo')or(not extra and k in ('factory_guns','factory_crew'))else 'normal'
            self.extra_entries[k].configure(state=state)
        self.fit_loading=False
        self.availability_heading.configure(text=f'New ship: {s["name"]}'if extra else 'Original ship: ports are read-only. Select a NEW ship to edit availability.')
        self.base_combo.configure(values=[f'{n:02d} - {r["name"]}'for n,r in enumerate(self.project.original)],state='readonly'if extra else 'disabled')
        self.base_combo.current(s['base_hull']if extra else i)
        self.industry_var.set(str(s['industry']));self.industry_entry.configure(state='normal'if extra else 'disabled')
        self.port_list.configure(state='normal');self.port_list.delete(0,'end')
        for p in ports(self.project.rom):self.port_list.insert('end',f'{p["name"]} — industry {p["industry"]}'+(' (fixed capital)'if p['capital']else ''))
        if extra:
            for p in s['ports']:self.port_list.selection_set(p)
        else:self.port_list.configure(state='disabled')
        self.show_port_selection()
        self.update_status()
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
        if self.selected>=25:
            try:values['industry']=int(self.industry_var.get())
            except ValueError:raise ValueError('Industry needs a whole number.')
            values['base_hull']=self.base_combo.current();values['ports']=list(self.port_list.curselection())
        self.project.update(self.selected,values)
    def update_status(self):
        n=len({c['id']for c in self.project.changes()})if self.project else 0
        added=len(self.project.ships)-25 if self.project else 0
        self.status.configure(text=f'Edited originals: {n}   |   Added ships: {added}/5   |   Source ROM unchanged')
    def pick(self,event=None):
        if self.loading or not self.project or not self.list.curselection():return
        index=self.list.curselection()[0]
        try:self.commit()
        except Exception as e:self.fail(e);self.list.selection_clear(0,'end');self.list.selection_set(self.selected);return
        self.selected=index;self.refresh_list();self.show(index)
    def apply(self):
        try:self.commit();self.refresh_list();self.show(self.selected)if self.project else None
        except Exception as e:self.fail(e)
    def allow_replace(self):
        if not self.project:return True
        try:self.commit()
        except Exception as e:self.fail(e);return False
        return (not self.project.changes()and len(self.project.ships)==25)or messagebox.askyesno('Leave this project?','Save your project first if you want to keep these edits. Continue?',parent=self.root)
    def open_rom(self):
        path=filedialog.askopenfilename(title='Open original USA ROM',filetypes=[('SNES ROM or ZIP','*.sfc *.smc *.zip'),('All files','*.*')])
        if not path or not self.allow_replace():return
        try:
            project=ShipProject(path);self.project=project;self.selected=0;self.source.configure(text='Stock USA ROM verified: '+Path(path).name+(' (copier header detected)'if project.header else ''))
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
        if self.selected>=25:
            s=self.project.ships[self.selected];base=dict(self.project.original[s['base_hull']])
            base.update(id=s['id'],name=s['name'],base_hull=s['base_hull'],ports=s['ports'],industry=s['industry'])
            base['max_crew']=max(base['max_crew'],((base['factory_crew']+9)//10)*10)
            base['capacity']=base['factory_guns']+base['factory_crew']+base['factory_cargo']
            self.project.ships[self.selected]=base;self.refresh_list();self.show(self.selected);return
        self.project.ships[self.selected]=dict(self.project.original[self.selected]);self.refresh_list();self.show(self.selected)
    def add(self):
        if not self.project:return
        try:
            self.commit();base=self.selected if self.selected<25 else self.project.ships[self.selected]['base_hull']
            self.selected=self.project.add_ship(base);self.refresh_list();self.show(self.selected)
        except Exception as e:self.fail(e)
    def remove(self):
        if not self.project or self.selected is None:return
        try:self.project.remove_ship(self.selected);self.selected=min(self.selected,len(self.project.ships)-1);self.refresh_list();self.show(self.selected)
        except Exception as e:self.fail(e)
    def help(self):
        messagebox.showinfo('Version 0.2 help','Open the ORIGINAL USA ROM. Select an original ship, then Add ship to create an independent hull. Add up to five.\n\nSet stats and factory fit on Specifications. Pick original graphics, ports and the shared industry threshold on Availability and graphics. Starting port industry is shown; unreachable capital offers are rejected. Remaining capacity becomes cargo.\n\nSave a project, then export to a new SFC. The IPS always applies to the original headerless ROM. Version0.1 projects still load.\n\nPrices, materials, bargaining, repair and battle controls otherwise follow stock rules. New ships can appear occasionally in used stock at eligible ports; enemy fleets are not assigned new models. Reused graphics and descriptions are intentional.\n\nUse a normal in-game save after a cold emulator boot, not old save states. Once you start playing, keep new-ship order/IDs stable: removing or reordering added ships can reinterpret hull IDs in that mod’s saves. Your existing campaign mod and its saves are not converted by this tool.',parent=self.root)
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
            report.write_text(json.dumps(dict(status='PASS',build_id=BUILD_ID,ships=30,added_ships=5,tk_widgets_loaded=True,
                sloop_guns=editor.project.ships[13]['max_guns'],price_gold=editor.project.ships[13]['price_gold'],buss_cargo=420,
                exported_rom_sha256=result['output_sha256']),indent=2))
        except Exception as e:
            report.write_text(json.dumps(dict(status='FAIL',error=str(e)),indent=2));raise
        finally:
            if root is not None:root.destroy()
        return
    root=tk.Tk();Editor(root);root.mainloop()

if __name__=='__main__':main()
