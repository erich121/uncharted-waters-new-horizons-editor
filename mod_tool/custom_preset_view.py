"""Select, load and manage complete user presets on the Presets page."""
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from custom_presets import PresetStore,preset_name,prepare,starter,apply_snapshot,summary,description,ORIGINAL_GAME,protected,lock_manual_controls


from app_defaults import preset_descriptions
DESCRIPTIONS={ORIGINAL_GAME:'Untouched original game settings. Edit the loaded project freely; use New preset to save your own version.', **preset_descriptions()}

NOTE='Saved presets stay on this PC. Share a setup with a project file.'


def refresh(app,selected=None):
    if getattr(app,'preset_view_project',None)is not app.project:
        app.preset_view_project=app.project;app.custom_preset_name.set('')
        app.preset_last_choice='';app.preset_loaded_project=None;app.preset_seed_applied=None
        show_loaded_changes(app,['Select a preset to load its settings.'])
    entries={}
    try:
        store=PresetStore();deleted=store.deleted();saved=store.read()
        entries={name:('starter',name)for name in DESCRIPTIONS if name not in deleted or protected(name)}
        for name in sorted(saved,key=str.casefold):
            if protected(name):continue
            existing=next((label for label in entries if label.casefold()==name.casefold()),None)
            if existing is not None:del entries[existing]
            entries[name]=('saved',name)
        app.custom_preset_error=None;app.custom_preset_note.configure(text=NOTE)
    except (ValueError,OSError)as error:
        app.custom_preset_error=str(error);app.custom_preset_note.configure(text=str(error))
    app.preset_entries=entries;app.custom_preset_choice.configure(values=list(entries))
    current=app.custom_preset_name.get()
    if selected is not None:current=next((label for label,value in entries.items()if value==('saved',selected)),current)
    app.custom_preset_name.set(current if current in entries else '')
    kind,name=entries.get(app.custom_preset_name.get(),(None,None))
    app.easy_description.configure(text=DESCRIPTIONS[name]if kind=='starter'else PresetStore().descriptions().get(name,'')if kind else ('Select a preset to load its settings.' if entries else 'No presets saved. Use New preset to create one from your current settings.'))
    app.easy_seed_row.pack_forget()
    if kind=='starter'and name=='Full Randomizer':app.easy_seed_row.pack(before=app.custom_preset_actions,anchor='w',pady=(0,8))
    ready=app.project is not None
    for button in (getattr(app,'ai_export_button',None),getattr(app,'ai_import_button',None)):
        if button is not None:button.configure(state='normal'if ready else 'disabled')
    app.custom_preset_save.configure(state='normal'if ready and not app.custom_preset_error else 'disabled')
    app.custom_preset_choice.configure(state='readonly'if ready and not app.custom_preset_error else 'disabled')
    for control in (app.easy_seed_entry,app.preset_randomize_seed,app.easy_blind_check):control.configure(state='normal'if ready else 'disabled')
    app.custom_preset_update.configure(state='normal'if ready and kind and not protected(name) and not app.custom_preset_error else 'disabled')
    app.custom_preset_delete.configure(state='normal'if kind and not protected(name) and not app.custom_preset_error else 'disabled')
    app.custom_preset_restore.configure(state='normal'if not app.custom_preset_error else 'disabled')


def create_controls(app,parent):
    ttk.Label(parent,text='Custom presets',font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(0,8))
    ttk.Label(parent,text='Selecting a preset replaces all project settings. Your Library stays unchanged.',wraplength=620).pack(anchor='w',pady=(0,8))
    app.custom_preset_name=tk.StringVar()
    app.custom_preset_choice=ttk.Combobox(parent,textvariable=app.custom_preset_name,state='readonly',width=32)
    app.custom_preset_choice.pack(anchor='w',pady=(0,8))
    app.custom_preset_choice.bind('<<ComboboxSelected>>',lambda e:select_preset(app))
    app.easy_description=ttk.Label(parent,wraplength=620);app.easy_description.pack(anchor='w',pady=(0,10))
    app.easy_seed=tk.StringVar(value='0000');app.easy_blind=tk.BooleanVar(value=False)
    app.easy_seed_row=ttk.Frame(parent)
    row=ttk.Frame(app.easy_seed_row);row.pack(anchor='w')
    ttk.Label(row,text='Four-digit seed').pack(side='left',padx=(0,8))
    app.easy_seed_entry=ttk.Entry(row,textvariable=app.easy_seed,width=8);app.easy_seed_entry.pack(side='left')
    app.easy_seed_entry.bind('<Return>',lambda event:seed_changed(app))
    app.easy_seed_entry.bind('<FocusOut>',lambda event:seed_changed(app))
    app.preset_randomize_seed=ttk.Button(row,text='Randomize seed',command=lambda:randomize_seed(app));app.preset_randomize_seed.pack(side='left',padx=8)
    app.easy_blind_check=ttk.Checkbutton(app.easy_seed_row,text='Blind shuffle',variable=app.easy_blind,command=lambda:seed_changed(app));app.easy_blind_check.pack(anchor='w',pady=(6,0))
    buttons=app.custom_preset_actions=ttk.Frame(parent);buttons.pack(fill='x')
    app.custom_preset_save=ttk.Button(buttons,text='New preset',command=lambda:save(app))
    app.custom_preset_delete=ttk.Button(buttons,text='Delete',command=lambda:delete(app))
    app.custom_preset_update=ttk.Button(buttons,text='Update',command=lambda:update(app))
    def arrange(event=None):
        columns=3 if buttons.winfo_width()>=420 else 2
        for i,button in enumerate((app.custom_preset_save,app.custom_preset_update,app.custom_preset_delete)):
            button.grid(row=i//columns,column=i%columns,sticky='w',padx=(0,8),pady=(0,6))
    buttons.bind('<Configure>',arrange);arrange()
    app.custom_preset_restore=ttk.Button(parent,text='Restore original presets',command=lambda:restore(app));app.custom_preset_restore.pack(anchor='w',pady=(10,0))
    app.custom_preset_note=ttk.Label(parent,text=NOTE,wraplength=620,foreground='#6e7f98');app.custom_preset_note.pack(anchor='w',pady=(8,0))
    summary_box=ttk.Frame(parent);summary_box.pack(fill='x',pady=(12,0))
    ttk.Label(summary_box,text='Changes from last selection',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(0,6))
    text_box=ttk.Frame(summary_box);text_box.pack(fill='x')
    app.preset_loaded_changes=tk.Text(text_box,height=3,wrap='word',font=('Segoe UI',10),background='white',foreground='#17243d',relief='flat',padx=10,pady=8,width=30,state='disabled')
    bar=ttk.Scrollbar(text_box,command=app.preset_loaded_changes.yview);bar.pack(side='right',fill='y')
    app.preset_loaded_changes.pack(fill='x');app.preset_loaded_changes.configure(yscrollcommand=bar.set)
    show_loaded_changes(app,['Select a preset to load its settings.'])
    app.easy_preset=app.custom_preset_name;app.easy_choice=app.custom_preset_choice
    from ai_preset_view import controls
    controls(app,parent)
    refresh(app)


def save(app):
    edit_preset(app,False)


def update(app):
    edit_preset(app,True)


def edit_preset(app,updating=False):
    if not app.project:return
    selected=app.preset_entries.get(app.custom_preset_name.get())
    if updating and (not selected or protected(selected[1])):return
    try:app.commit();app.cancel_auto_edit()
    except ValueError as error:app.fail(error);return
    project=app.project;before=project.manifest()
    name=selected[1]if updating else ''
    initial=DESCRIPTIONS[name]if updating and selected[0]=='starter'else PresetStore().descriptions().get(name,'')
    dialog=tk.Toplevel(app.root);dialog.title('Update preset'if updating else 'New preset');dialog.geometry('540x410');dialog.minsize(400,360);dialog.transient(app.root);dialog.grab_set()
    frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
    footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(12,0))
    ttk.Label(frame,text='Update preset with all current settings?'if updating else 'Save all current settings as new preset?',wraplength=480,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(0,14))
    ttk.Label(frame,text='Name').pack(anchor='w')
    name_var=tk.StringVar(value=name);entry=ttk.Entry(frame,textvariable=name_var,state='readonly'if updating else 'normal');entry.pack(fill='x',pady=(4,12))
    ttk.Label(frame,text='Description (optional)').pack(anchor='w')
    text=tk.Text(frame,height=5,wrap='word',font=('Segoe UI',10),width=30);text.pack(fill='both',expand=True,pady=(4,0));text.insert('1.0',initial)
    def accept():
        try:
            if app.project is not project or project.manifest()!=before:raise ValueError('Current settings changed. Close this window and try again.')
            chosen=preset_name(name_var.get());notes=description(text.get('1.0','end-1c'))
            store=PresetStore();exists=any(n.casefold()==chosen.casefold()for n in app.preset_entries)
            if not updating and exists and not messagebox.askyesno('Replace preset?',f'Replace “{chosen}” with all current settings?',parent=dialog):return
            store.save(chosen,project,replace=updating or exists,description_text=notes)
            app.export_preset_name=chosen;app.preset_last_choice=chosen;app.preset_loaded_project=project
            app.preset_seed_applied=(id(project),app.easy_seed.get(),app.easy_blind.get())
            dialog.destroy();refresh(app,chosen);app.status.configure(text=('Preset updated: 'if updating else 'Preset saved: ')+chosen)
        except (ValueError,OSError)as error:messagebox.showerror('Could not save preset',str(error),parent=dialog)
    button=ttk.Button(footer,text='Update preset'if updating else 'Save preset',style='Primary.TButton',command=accept);button.pack(side='left')
    cancel=ttk.Button(footer,text='Cancel',command=dialog.destroy);cancel.pack(side='left',padx=8)
    dialog.bind('<Escape>',lambda e:dialog.destroy())
    app.preset_editor_dialog=dialog;app.preset_editor_name=name_var;app.preset_editor_description=text;app.preset_editor_save=button;app.preset_editor_cancel=cancel
    entry.focus_set()


def restore(app):
    if not messagebox.askyesno('Restore original presets?','Restore the bundled presets? This brings back deleted presets and removes your updates to them. Original Game is always kept. Other saved presets and your current settings stay unchanged.',parent=app.root):return
    try:
        PresetStore().restore_provided();refresh(app)
        app.status.configure(text='Original presets restored. Current settings unchanged.')
    except (ValueError,OSError)as error:app.fail(error)


def delete(app):
    selected=app.preset_entries.get(app.custom_preset_name.get())
    if not selected or protected(selected[1]):return
    name=selected[1]
    if not messagebox.askyesno('Delete custom preset?',f'Delete “{name}”? Your current settings will stay as they are.',parent=app.root):return
    try:PresetStore().delete(name,provided=selected[0]=='starter');refresh(app);app.status.configure(text='Custom preset deleted: '+name)
    except (ValueError,OSError)as error:app.fail(error)



def show_loaded_changes(app,lines):
    box=app.preset_loaded_changes
    box.configure(state='normal',height=min(6,max(3,len(lines)*2-1)));box.delete('1.0','end')
    box.insert('1.0','\n\n'.join(lines));box.configure(state='disabled');box.yview_moveto(0)


def full_randomizer_selected(app):
    return app.preset_entries.get(app.custom_preset_name.get())==('starter','Full Randomizer')


def fresh_seed(app):
    from character_mods import random_seed
    old=app.easy_seed.get();seed=random_seed()
    if seed==old:seed=f'{(int(seed)+1)%10000:04d}'
    app.easy_seed.set(seed)


def select_preset(app):
    previous=getattr(app,'preset_last_choice','');old_seed=app.easy_seed.get()
    if full_randomizer_selected(app):fresh_seed(app)
    if not load_selected(app):
        app.easy_seed.set(old_seed);app.custom_preset_name.set(previous);refresh(app)


def randomize_seed(app):
    if not app.project or not full_randomizer_selected(app):return
    old_seed=app.easy_seed.get();fresh_seed(app)
    if not load_selected(app):app.easy_seed.set(old_seed)


def seed_changed(app,strict=False):
    if getattr(app,'preset_loading',False)or not app.project or not full_randomizer_selected(app)or getattr(app,'preset_loaded_project',None)is not app.project:return
    signature=(id(app.project),app.easy_seed.get(),app.easy_blind.get())
    if signature==getattr(app,'preset_seed_applied',None):return
    from character_mods import validate_seed
    try:validate_seed(app.easy_seed.get())
    except ValueError as error:
        if strict:raise
        app.status.configure(text='Preset seed: enter exactly four digits, then press Enter.');return
    load_selected(app,strict=strict)


def load_selected(app,strict=False):
    if not app.project or getattr(app,'preset_loading',False):return False
    app.preset_loading=True
    try:
        app.commit();app.cancel_auto_edit()
        project=app.project;kind,name=app.preset_entries[app.custom_preset_name.get()]
        if kind=='starter':candidate=starter(project,name,app.easy_seed.get(),app.easy_blind.get())
        else:
            data=PresetStore().read()
            if name not in data:raise ValueError('That custom preset no longer exists.')
            candidate=prepare(project,data[name])
        lock_manual_controls(candidate)
        lines=summary(project,candidate)
        apply_snapshot(project,candidate);app.export_preset_name=name
        app.preset_last_choice=name;app.preset_loaded_project=project
        app.preset_seed_applied=(id(project),app.easy_seed.get(),app.easy_blind.get())
        app.reload_project_view();show_loaded_changes(app,lines)
        app.status.configure(text='Preset loaded: '+name+'. All project settings replaced.')
        return True
    except (ValueError,OSError,KeyError)as error:
        if strict:raise ValueError('Could not load preset: '+str(error))from error
        app.fail(error);return False
    finally:app.preset_loading=False
