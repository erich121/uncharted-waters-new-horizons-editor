"""Small Windows editor for original25 stock-ROM ships."""
import ctypes,sys,json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from backend import ShipProject,FIELDS,price_from_bars,TOOL_VERSION

LABELS={'name':'Ship name','hull':'Hull strength','turning':'Turning','power':'Sailing power',
    'max_guns':'Maximum guns','min_crew':'Minimum sailors','max_crew':'Maximum crew spaces','price_gold':'Base price in gold bars'}

class Editor:
    def __init__(self,root):
        self.root=root;self.project=None;self.selected=None;self.loading=False
        root.title('New Horizons Ship Editor v'+TOOL_VERSION);root.geometry('1050x700');root.minsize(950,650)
        root.protocol('WM_DELETE_WINDOW',self.close)
        style=ttk.Style();style.theme_use('vista'if 'vista'in style.theme_names()else 'clam')
        style.configure('TLabel',font=('Segoe UI',10));style.configure('TButton',padding=7)
        top=ttk.Frame(root,padding=16);top.pack(fill='x')
        ttk.Label(top,text='New Horizons Ship Editor',font=('Segoe UI',19,'bold')).pack(anchor='w')
        ttk.Label(top,text='Version '+TOOL_VERSION+'   •   Original USA game   •   25 stock ships').pack(anchor='w',pady=(4,10))
        bar=ttk.Frame(top);bar.pack(fill='x')
        for title,call in [('Open stock ROM',self.open_rom),('Open project',self.open_project),('Save project',self.save_project),('Export ROM and IPS',self.export),('Help',self.help)]:
            ttk.Button(bar,text=title,command=call).pack(side='left',padx=(0,6))
        self.source=ttk.Label(top,text='Open your original USA .sfc, .smc or ZIP to begin.');self.source.pack(anchor='w',pady=(12,0))
        body=ttk.Frame(root,padding=(16,0));body.pack(fill='both',expand=True)
        left=ttk.Frame(body);left.pack(side='left',fill='y',padx=(0,20))
        self.list=tk.Listbox(left,width=27,height=25,font=('Segoe UI',10),exportselection=False)
        self.list.pack(fill='y',expand=True);self.list.bind('<<ListboxSelect>>',self.pick)
        right=ttk.Frame(body);right.pack(side='left',fill='both',expand=True)
        self.heading=ttk.Label(right,text='No game loaded',font=('Segoe UI',15,'bold'));self.heading.grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,12))
        self.vars={};self.entries={}
        hints={'name':'1–17 English characters','hull':'1–100','turning':'1–100','power':'1–100','max_guns':'0–150; not below factory guns','min_crew':'1–255','max_crew':'10–500; multiples of 10','price_gold':'1 bar = 10,000 gold; steps of 0.001 bar'}
        for n,k in enumerate(FIELDS,1):
            ttk.Label(right,text=LABELS[k]).grid(row=n,column=0,sticky='w',pady=7,padx=(0,15))
            self.vars[k]=tk.StringVar();entry=ttk.Entry(right,textvariable=self.vars[k],width=22,state='disabled');entry.grid(row=n,column=1,sticky='w');self.entries[k]=entry
            ttk.Label(right,text=hints[k],foreground='#555555',wraplength=245).grid(row=n,column=2,sticky='w',padx=(12,0))
        controls=ttk.Frame(right);controls.grid(row=9,column=0,columnspan=3,sticky='w',pady=12)
        ttk.Button(controls,text='Apply ship changes',command=self.apply).pack(side='left',padx=(0,8))
        ttk.Button(controls,text='Restore selected ship',command=self.restore).pack(side='left')
        self.fixed=ttk.Label(right,text='',wraplength=610);self.fixed.grid(row=10,column=0,columnspan=3,sticky='w',pady=8)
        ttk.Label(right,text='Version 1 keeps capacity, factory compartments, portraits and shipyard availability unchanged.',wraplength=610,foreground='#555555').grid(row=11,column=0,columnspan=3,sticky='w',pady=8)
        self.status=ttk.Label(root,text='Your source ROM and saves are never overwritten.',padding=16);self.status.pack(fill='x')

    def fail(self,e):messagebox.showerror('Check your values',str(e),parent=self.root)
    def refresh_list(self):
        self.loading=True;self.list.delete(0,'end')
        if self.project:
            for i,s in enumerate(self.project.ships):
                changed=any(s[k]!=self.project.original[i][k]for k in FIELDS)
                self.list.insert('end',f'{i+1:02d}  {s["name"]}'+('  *'if changed else ''))
        if self.selected is not None:self.list.selection_set(self.selected);self.list.see(self.selected)
        self.loading=False
    def show(self,i):
        self.selected=i;s=self.project.ships[i]
        self.heading.configure(text=s['name'])
        for k in FIELDS:self.entries[k].configure(state='normal');self.vars[k].set(str(s[k]/10000).rstrip('0').rstrip('.')if k=='price_gold'else str(s[k]))
        self.fixed.configure(text=f"Read-only: total capacity {s['capacity']}   •   Factory fit {s['factory_guns']} guns / {s['factory_crew']} crew spaces / {s['factory_cargo']} cargo\nIndustry requirement {s['industry']}")
        self.update_status()
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
        self.project.update(self.selected,values)
    def update_status(self):
        n=len({c['id']for c in self.project.changes()})if self.project else 0
        self.status.configure(text=f'{n} modified ships. Source ROM and saves untouched. Export creates a new ROM, IPS and change report.')
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
        return not self.project.changes()or messagebox.askyesno('Leave this project?','Save your project first if you want to keep these edits. Continue?',parent=self.root)
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
        try:self.project.load_project(path);self.refresh_list();self.show(self.selected)
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
        self.project.ships[self.selected]=dict(self.project.original[self.selected]);self.refresh_list();self.show(self.selected)
    def help(self):
        messagebox.showinfo('Version 1 help','1. Open the ORIGINAL USA New Horizons ROM or ZIP.\n2. Select a ship and edit its values. Changes apply when selecting another ship or exporting.\n3. Save a project to keep your settings.\n4. Export to a new filename and test the SFC in your emulator.\n\nPrices are reference prices in gold bars; material, port prices and bargaining still use the stock rules. Maximum crew means compartment limit, not hired sailors. Existing saves can retain old fitted compartments and condition.\n\nThis first version does not install our expanded ships, artwork, battle controls or material patches. Patched games are deliberately rejected. You can close the app without changing the game.',parent=self.root)
    def close(self):
        if self.allow_replace():self.root.destroy()

def main():
    try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:pass
    if len(sys.argv)==5 and sys.argv[1]=='--self-test'and sys.argv[3]=='--report':
        report=Path(sys.argv[4]);report.parent.mkdir(parents=True,exist_ok=True);root=None
        try:
            root=tk.Tk();root.withdraw();editor=Editor(root)
            editor.project=ShipProject(sys.argv[2]);editor.selected=13;editor.refresh_list();editor.show(13)
            root.update_idletasks();assert editor.list.size()==25
            editor.vars['max_guns'].set('60');editor.vars['price_gold'].set('2.5');editor.commit()
            exported=report.parent/'Self Test Mod.sfc';result=editor.project.export(exported)
            report.write_text(json.dumps(dict(status='PASS',ships=25,tk_widgets_loaded=True,
                sloop_guns=editor.project.ships[13]['max_guns'],price_gold=editor.project.ships[13]['price_gold'],
                exported_rom_sha256=result['output_sha256']),indent=2))
        except Exception as e:
            report.write_text(json.dumps(dict(status='FAIL',error=str(e)),indent=2));raise
        finally:
            if root is not None:root.destroy()
        return
    root=tk.Tk();Editor(root);root.mainloop()

if __name__=='__main__':main()
