"""Clipboard/file exchange and reviewed creation of AI-authored presets."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import ai_presets
from custom_presets import PresetStore, summary
from file_safety import atomic_write


def controls(app,parent):
    from ui_theme import SectionCard
    panel=SectionCard(parent,'AI Presets',clean=True);panel.pack(fill='x',pady=(18,0));card=panel.body
    ttk.Label(card,text='Copy the guide to an AI chat and describe your setup. Import its JSON reply to save a preset, then select the preset to load it.',wraplength=620,style='Card.TLabel').pack(anchor='w')
    ttk.Label(card,text='The AI can add up to ten ships using existing game or Library pictures. The guide includes blind-shuffle results. No AI account is connected to this app.',wraplength=620,style='Card.TLabel',foreground='#52647b').pack(anchor='w',pady=(6,10))
    actions=ttk.Frame(card,style='Card.TFrame');actions.pack(fill='x')
    app.ai_export_button=ttk.Button(actions,text='Copy guide for AI',command=lambda:exchange(app,False),state='disabled');app.ai_export_button.grid(row=0,column=0,sticky='w',padx=(0,8),pady=3)
    app.ai_import_button=ttk.Button(actions,text='Import AI response',command=lambda:exchange(app,True),state='disabled');app.ai_import_button.grid(row=0,column=1,sticky='w',pady=3)
    actions.bind('<Configure>',lambda e:app.ai_import_button.grid_configure(row=1 if e.width<330 else 0,column=0 if e.width<330 else 1))


def exchange(app,importing):
    if not app.project:return
    try:app.commit();app.cancel_auto_edit()
    except ValueError as error:app.fail(error);return
    project=app.project;base=ai_presets.fingerprint(project)
    try:payload=''if importing else ai_presets.export(project)
    except (ValueError,OSError)as error:app.fail(error);return
    dialog=tk.Toplevel(app.root);dialog.title('Import AI response'if importing else 'Copy guide for AI')
    dialog.geometry('820x620');dialog.minsize(480,360);dialog.transient(app.root);dialog.grab_set()
    frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
    footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(10,0))
    ttk.Label(frame,text='Paste the AI response or open its JSON file. Review before saving.'if importing else 'Copy this into an AI chat, then add your request. Ask it to return the preset JSON.',wraplength=720).pack(anchor='w',pady=(0,10))
    if not importing:
        ttk.Label(frame,text='Art codes let the AI reuse existing pictures. The editor checks the settings before you save the preset.',wraplength=720,foreground='#52647b').pack(anchor='w',pady=(0,10))
    frame.bind('<Configure>',lambda event:[child.configure(wraplength=max(180,event.width-32))for child in frame.winfo_children()if child.winfo_class()=='TLabel'])
    box=ttk.Frame(frame);box.pack(fill='both',expand=True)
    text=tk.Text(box,wrap='none',font=('Consolas',10),undo=True,width=30,height=10)
    text.grid(row=0,column=0,sticky='nsew');box.rowconfigure(0,weight=1);box.columnconfigure(0,weight=1)
    vertical=ttk.Scrollbar(box,command=text.yview);vertical.grid(row=0,column=1,sticky='ns')
    horizontal=ttk.Scrollbar(box,orient='horizontal',command=text.xview);horizontal.grid(row=1,column=0,sticky='ew')
    text.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set);text.insert('1.0',payload)
    if not importing:text.configure(state='disabled')
    def fail(error):messagebox.showerror('AI preset',str(error),parent=dialog)
    def copy_text():
        try:app.root.clipboard_clear();app.root.clipboard_append(payload);app.status.configure(text='AI preset guide copied. Paste it into an AI chat and add your request.')
        except tk.TclError as error:fail(error)
    def save_file():
        path=filedialog.asksaveasfilename(parent=dialog,title='Save AI preset guide',defaultextension='.json',initialfile='AI Preset Guide.json',filetypes=[('JSON','*.json')])
        if not path:return
        try:
            target=Path(path).resolve()
            if target==project.source.resolve()or(project.project_path and target==Path(project.project_path).resolve())or target.suffix.lower()!='.json':raise ValueError('Choose a separate .json file for the AI guide.')
            atomic_write(target,(payload+'\n').encode('utf-8'))
        except (ValueError,OSError)as error:fail(error)
    def paste():
        try:
            value=app.root.clipboard_get()
            if len(value)>ai_presets.MAX_TEXT:raise ValueError('Clipboard text is too large.')
            text.delete('1.0','end');text.insert('1.0',value)
        except (tk.TclError,ValueError)as error:fail(error)
    def open_file():
        path=filedialog.askopenfilename(parent=dialog,title='Open AI preset response',filetypes=[('JSON','*.json'),('Text','*.txt')])
        if not path:return
        try:
            target=Path(path)
            if target.stat().st_size>ai_presets.MAX_TEXT:raise ValueError('AI preset file is too large.')
            value=target.read_text(encoding='utf-8-sig');text.delete('1.0','end');text.insert('1.0',value)
        except (OSError,UnicodeError,ValueError)as error:fail(error)
    def review():
        try:
            if app.project is not project or ai_presets.fingerprint(project)!=base:raise ValueError('Current settings changed. Close this window and export again.')
            name,notes,candidate=ai_presets.candidate(project,text.get('1.0','end-1c'))
            review_dialog(app,dialog,project,base,name,notes,candidate)
        except (ValueError,OSError)as error:fail(error)
    buttons=[('Paste',paste),('Open file',open_file),('Review preset',review)]if importing else [('Copy for AI',copy_text),('Save file',save_file)]
    app.ai_exchange_buttons={}
    for i,(label,command)in enumerate(buttons):
        button=ttk.Button(footer,text=label,command=command);button.grid(row=0,column=i,sticky='w',padx=(0,6));app.ai_exchange_buttons[label]=button
    ttk.Button(footer,text='Close',command=dialog.destroy).grid(row=1,column=0,sticky='w',pady=(6,0))
    dialog.bind('<Escape>',lambda e:dialog.destroy())
    app.ai_exchange_dialog=dialog;app.ai_exchange_text=text


def review_dialog(app,exchange,project,base,name,notes,candidate):
    dialog=tk.Toplevel(exchange);dialog.title('Review AI preset — '+name);dialog.geometry('800x580');dialog.minsize(480,360);dialog.transient(exchange);dialog.grab_set()
    frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
    footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(10,0))
    ttk.Label(frame,text=name,font=('Segoe UI',16,'bold'),wraplength=700).pack(anchor='w')
    box=ttk.Frame(frame);box.pack(fill='both',expand=True,pady=(10,0))
    text=tk.Text(box,wrap='word',font=('Segoe UI',11),width=30,height=10);text.pack(side='left',fill='both',expand=True)
    scroll=ttk.Scrollbar(box,command=text.yview);scroll.pack(side='right',fill='y');text.configure(yscrollcommand=scroll.set)
    text.insert('1.0',(notes+'\n\n'if notes else '')+'Changes from the exported setup:\n\n'+'\n\n'.join(summary(project,candidate))+'\n\nSaving adds this preset to the list. Your current setup will not change.');text.configure(state='disabled')
    def cancel():dialog.destroy();exchange.grab_set()
    def save():
        try:
            if app.project is not project or ai_presets.fingerprint(project)!=base:raise ValueError('Settings changed. Close this preview and export again.')
            from custom_preset_view import refresh
            refresh(app)
            exists=any(n.casefold()==name.casefold()for n in app.preset_entries)
            if exists and not messagebox.askyesno('Replace preset?',f'Replace the saved preset “{name}”? Current settings stay unchanged.',parent=dialog):return
            PresetStore().save(name,candidate,replace=exists,description_text=notes)
            dialog.destroy();exchange.destroy();refresh(app);app.status.configure(text='AI preset saved: '+name+'. Select it from the preset list to load it.')
        except (ValueError,OSError)as error:messagebox.showerror('Could not save AI preset',str(error),parent=dialog)
    accept=ttk.Button(footer,text='Save preset',style='Primary.TButton',command=save);accept.pack(side='left')
    cancel_button=ttk.Button(footer,text='Cancel',command=cancel);cancel_button.pack(side='left',padx=8)
    dialog.protocol('WM_DELETE_WINDOW',cancel);dialog.bind('<Escape>',lambda e:cancel())
    app.ai_review_dialog=dialog;app.ai_review_save=accept;app.ai_review_cancel=cancel_button;app.ai_review_text=text
