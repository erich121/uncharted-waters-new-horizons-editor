"""Nation-by-nation fleet selection dialog; uses project IDs, never names as keys."""
import tkinter as tk
from tkinter import ttk,messagebox
from fleet_difficulty import NATIONS,SOURCES,ROLES,preset,validate_rules,resolve,PRESETS

def open_settings(editor,Scroller):
    if not editor.project or not editor.difficulty_var.get():return
    try:editor.commit()
    except Exception as e:editor.fail(e);return
    project=editor.project;ships=project.ships
    draft=validate_rules(project.fleet_rules,ships)
    dialog=tk.Toplevel(editor.root);dialog.title('Custom Fleets')
    dialog.geometry('1200x700');dialog.minsize(640,480);dialog.transient(editor.root);dialog.grab_set()
    header=ttk.Frame(dialog,padding=14);header.pack(fill='x')
    ttk.Label(header,text='Custom Fleets',font=('Segoe UI',15,'bold')).pack(anchor='w')
    ttk.Label(header,text='Choose ships for each nation’s strongest fleets. No change keeps the game’s choice. Existing ships stay until replaced.',wraplength=900).pack(anchor='w',pady=(4,10))
    bar=ttk.Frame(header);bar.pack(fill='x')
    ttk.Label(bar,text='Nation').pack(side='left',padx=(0,10))
    nation=ttk.Combobox(bar,values=NATIONS,state='readonly',width=17);nation.current(0);nation.pack(side='left')
    middle=ttk.Frame(dialog);middle.pack(fill='both',expand=True,padx=14)
    scroll=Scroller(middle)
    content=ttk.Frame(scroll.content,padding=12);content.pack(fill='both',expand=True)
    for col,text in enumerate(('Original ship',)+ROLES):ttk.Label(content,text=text,font=('Segoe UI',10,'bold')).grid(row=0,column=col,sticky='w',padx=6,pady=8)
    choices=['No change']+[f'{s["id"]+1:02d}  {s["name"]}'+(' (added)'if s['id']>=25 else '')for s in ships]
    combos=[];labels=[];loading=False
    preview=ttk.Label(content,text='',wraplength=880,justify='left')
    def show_preview():
        lines=[]
        available=set()
        for at,base in ((0x9ec77,48),(0x9eca1,40)):
            pos=at+nation.current()*6+4
            packed=int.from_bytes(project.rom[pos:pos+2],'little')
            available.update(base+((packed>>(4*r))&15)-40 for r in range(3))
        for j,source in enumerate(SOURCES):labels[j].configure(foreground='#17243d'if source in available else '#78879a')
        native='These fleets normally use: '+', '.join(ships[i]['name'] for i in sorted(available))+'. Grey rows are not normally used here.'
        for role in range(len(ROLES)):
            for j,source in enumerate(SOURCES):
                target=draft[nation.current()][role][j]
                if target<0 or source not in available:continue
                result,reason=resolve(ships,source,target);s=ships[target]
                note=(' — '+reason)if result is None else ''
                lines.append(f'{ROLES[role]}: {ships[source]["name"]} → {s["name"]} ({s["factory_guns"]} guns, {s["factory_crew"]} crew, hull strength {s["hull"]}){note}')
        preview.configure(text=native+'\n\nYour choices\n'+('\n'.join(lines)if lines else 'No ship changes for this nation.')+'\n\nA ship with a weaker hull, fewer guns or fewer crew will not be used. Speed and turning can differ. Ships 5 onward, smaller fleets, pirates and your fleet keep the game’s choices.')
    def change(*args):
        if loading:return
        for role in range(len(ROLES)):
            for j in range(4):draft[nation.current()][role][j]=combos[j][role].current()-1
        sync_preset();show_preview()
    for j,source in enumerate(SOURCES):
        label=ttk.Label(content,text=ships[source]['name'],width=20);label.grid(row=j+1,column=0,sticky='w',padx=6,pady=12);labels.append(label)
        row=[]
        for role in range(len(ROLES)):
            combo=ttk.Combobox(content,values=choices,state='readonly',width=23)
            combo.grid(row=j+1,column=role+1,sticky='ew',padx=6,pady=12);combo.bind('<<ComboboxSelected>>',change);row.append(combo)
        combos.append(row)
    def show_nation(event=None):
        nonlocal loading
        loading=True
        for j in range(4):
            for role in range(len(ROLES)):combos[j][role].current(draft[nation.current()][role][j]+1)
        loading=False;sync_preset();show_preview();dialog.after_idle(scroll.resize)
    nation.bind('<<ComboboxSelected>>',show_nation)
    preview.grid(row=6,column=0,columnspan=5,sticky='w',pady=(12,4))
    presets=ttk.Frame(header);presets.pack(fill='x',pady=(10,0))
    ttk.Label(presets,text='Preset').pack(side='left',padx=(0,10))
    preset_box=ttk.Combobox(presets,values=[v[0]for v in PRESETS.values()],state='readonly',width=23)
    preset_box.pack(side='left',padx=(0,8))
    preset_note=ttk.Label(header,text='',wraplength=580);preset_note.pack(anchor='w',pady=(6,0))
    def sync_preset():
        for index,(key,value)in enumerate(PRESETS.items()):
            if draft==preset(key):
                preset_box.current(index);preset_note.configure(text=value[1]);return
        preset_box.set('Custom settings');preset_note.configure(text='You have chosen your own ships. Pick a preset to start over.')
    def load_preset(event=None):
        index=preset_box.current()
        if index<0:return
        draft[:]=preset(list(PRESETS)[index]);show_nation()
    preset_box.bind('<<ComboboxSelected>>',load_preset)
    ttk.Label(header,text='A preset changes all six nations. Apply keeps your choices. Cancel discards edits from this window.').pack(anchor='w',pady=(4,0))
    footer=ttk.Frame(dialog,padding=14);footer.pack(side='bottom',fill='x',before=middle)
    def apply():
        try:
            project.fleet_rules=validate_rules(draft,ships)
            editor.update_status();dialog.destroy()
        except Exception as e:messagebox.showerror('Invalid fleet settings',str(e),parent=dialog)
    ttk.Button(footer,text='Apply settings',command=apply,style='Primary.TButton').pack(side='left',padx=(0,8))
    ttk.Button(footer,text='Cancel',command=dialog.destroy).pack(side='left')
    ttk.Label(header,text='To use these choices, turn on “Use custom fleets” on Gameplay.',wraplength=580).pack(anchor='w',pady=(6,0))
    editor.fleet_dialog=dialog;editor.fleet_nation=nation;editor.fleet_choice_widgets=combos
    editor.fleet_preset_box=preset_box;editor.fleet_preset_note=preset_note
    editor.fleet_draft=draft;editor.fleet_preview=preview;editor.fleet_settings_scroll=scroll
    def wrap_header(event):
        for widget in header.winfo_children():
            if widget.winfo_class()=='TLabel':widget.configure(wraplength=max(280,event.width-28))
    header.bind('<Configure>',wrap_header)
    show_nation()
