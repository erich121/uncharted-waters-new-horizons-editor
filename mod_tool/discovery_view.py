"""Project discovery browser: current content, fixed locations and Library swaps."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageTk
from ui_theme import SectionCard
CHANGE_ORANGE = '#ef7800'
import discovery_content as content
from discoveries import catalogue, picture


class DiscoveriesPanel:
    def __init__(self, app, scroll_type):
        self.app = app
        self.scroll_type = scroll_type
        self.selected = 0
        self.rows = []
        self.visible = []
        self.original = []
        self.signature = None
        self.left = ttk.Frame(app.sidebar)
        ttk.Label(self.left, text='Discoveries', font=('Segoe UI',12,'bold')).pack(anchor='w', pady=(0,6))
        self.search = tk.StringVar()
        self.search_entry = ttk.Entry(self.left, textvariable=self.search)
        self.search_entry.pack(fill='x', pady=(0,6))
        self.count = ttk.Label(self.left, foreground='#6e7f98', wraplength=250)
        self.count.pack(anchor='w', pady=(0,6))
        box = ttk.Frame(self.left); box.pack(fill='both', expand=True)
        self.list = tk.Listbox(box, exportselection=False, activestyle='none', borderwidth=0,
                              highlightthickness=0, background='white', selectbackground='#205b9b', selectforeground='white')
        self.list.pack(side='left', fill='both', expand=True)
        bar = ttk.Scrollbar(box, command=self.list.yview); bar.pack(side='right', fill='y')
        self.list.configure(yscrollcommand=bar.set)
        self.list.bind('<<ListboxSelect>>', self.pick)
        self.search.trace_add('write', lambda *_: self.refresh_list())
        self.frame = ttk.Frame(app.settings_area)
        self.scroll = scroll_type(self.frame, fit_width=True, natural_height=True)
        body = ttk.Frame(self.scroll.content, padding=8); body.pack(fill='both', expand=True)
        self.custom = tk.BooleanVar(value=False)
        self.custom_box = ttk.Checkbutton(body, text='Use custom values', variable=self.custom, command=self.toggle, state='disabled')
        self.custom_box.pack(anchor='w', pady=(0,6))
        ttk.Label(body, text='Discoveries', font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(body, text='Current project pool · Original locations stay fixed', foreground='#6e7f98').pack(anchor='w', pady=(2,10))
        card = SectionCard(body, 'Current discovery'); card.pack(fill='x')
        self.profile = ttk.Frame(card.body, style='Card.TFrame'); self.profile.pack(fill='x')
        self.picture = ttk.Label(self.profile, style='Card.TLabel')
        self.text = ttk.Frame(self.profile, style='Card.TFrame')
        self.heading = ttk.Label(self.text, text='Open a stock ROM to begin', style='Card.TLabel', font=('Segoe UI',20,'bold'))
        self.heading.pack(anchor='w')
        self.meta = ttk.Label(self.text, style='Hint.Card.TLabel'); self.meta.pack(anchor='w', pady=(4,12))
        self.description = ttk.Label(self.text, style='Card.TLabel', font=('Segoe UI',12), wraplength=600, justify='left')
        self.description.pack(anchor='w', fill='x')
        self.assignment = ttk.Label(card.body, style='Hint.Card.TLabel', wraplength=700)
        self.assignment.pack(anchor='w', pady=(14,4))
        self.actions = ttk.Frame(body); self.actions.pack(fill='x', pady=10)
        self.bulk_button = ttk.Button(self.actions, text='Load all custom discoveries', command=self.load_all)
        self.replace_button = ttk.Button(self.actions, text='Replace from Library…', style='Primary.TButton', command=self.choose_replacement)
        self.save_button = ttk.Button(self.actions, text='Save to Library', command=self.save_to_library)
        self.restore_button = ttk.Button(self.actions, text='Restore original discovery', command=self.restore)
        self.buttons = [self.replace_button, self.bulk_button, self.save_button, self.restore_button]
        self.note = ttk.Label(body, text='This shows all 98 discoveries in the project pool. A new game selects its usual subset; this is not the discovery progress in your save.', foreground='#6e7f98', wraplength=700)
        self.note.pack(anchor='w', pady=(0,8))
        self.profile.bind('<Configure>', self.arrange)
        self.actions.bind('<Configure>', self.arrange)
        self.layout = None
        self.refresh()

    def arrange(self, event=None):
        width = max(200, self.scroll.canvas.winfo_width()-48)
        wide = width >= 650
        if wide != self.layout:
            self.layout = wide
            self.picture.grid_forget(); self.text.grid_forget()
            self.picture.grid(row=0, column=0, sticky='nw', padx=(0,20) if wide else (0,0))
            self.text.grid(row=0 if wide else 1, column=1 if wide else 0, sticky='new', pady=0 if wide else (12,0))
            self.profile.columnconfigure(0, weight=0 if wide else 1)
            self.profile.columnconfigure(1, weight=1 if wide else 0)
        self.heading.configure(wraplength=max(180,width-(220 if wide else 0)))
        self.meta.configure(wraplength=max(180,width-(220 if wide else 0)))
        self.description.configure(wraplength=max(180,width-(220 if wide else 0)))
        self.assignment.configure(wraplength=width); self.note.configure(wraplength=width)
        used = row = col = 0
        for button in self.buttons:
            requested = button.winfo_reqwidth()+8
            if used and used+requested > width:
                row+=1; col=used=0
            button.grid(row=row,column=col,sticky='w',padx=(0,8),pady=(0,6))
            used+=requested; col+=1

    def show(self):
        self.left.pack(fill='both', expand=True); self.frame.pack(fill='both', expand=True)
        self.app.scroll = self.scroll
        self.refresh(); self.app.root.after_idle(self.scroll.resize)

    def hide(self):
        self.left.pack_forget(); self.frame.pack_forget()

    def refresh(self):
        p = self.app.project
        signature = (id(p), p.discovery_rewrites, p.discovery_easy, repr(p.discovery_entries)) if p else None
        if signature != self.signature:
            self.signature = signature
            self.rows = content.rows(p) if p else []
            self.original = catalogue(p.rom) if p else []
        self.refresh_list()

    def toggle(self):
        if self.app.project:
            self.app.project.custom_discoveries = self.custom.get()
            self.refresh()
            self.app.update_status()

    def refresh_list(self):
        self.list.delete(0,'end'); self.visible=[]
        term = self.search.get().strip().casefold()
        p = self.app.project
        changed_slots=content.changed_slots(p) if p else set()
        for row in self.rows:
            slot = row['id']
            if term and term not in f"{slot+1:02d} {row['name']} {self.original[slot]['name']} {row['category']}".casefold():
                continue
            self.visible.append(slot)
            changed = slot in changed_slots
            self.list.insert('end', f"{slot+1:02d}  {row['name']}"+(' *' if changed else ''))
            self.list.itemconfigure('end', foreground=CHANGE_ORANGE if changed else '#17243d')
        if self.visible:
            if self.selected not in self.visible:self.selected=self.visible[0]
            index=self.visible.index(self.selected)
            self.list.selection_set(index); self.list.activate(index); self.list.selection_anchor(index); self.list.see(index)
        self.count.configure(text=f'{len(self.visible)} of {len(self.rows)} discoveries')
        self.render()

    def pick(self, event=None):
        if self.list.curselection():
            self.selected=self.visible[self.list.curselection()[0]]; self.render()

    def render(self):
        p = self.app.project
        enabled = bool(p and self.visible)
        self.custom.set(bool(p and p.custom_discoveries))
        self.custom_box.configure(state='normal' if p else 'disabled')
        for button in self.buttons:button.configure(state='normal' if enabled else 'disabled')
        editing=bool(p and p.custom_discoveries)
        self.replace_button.configure(state='normal' if enabled and editing else 'disabled')
        self.bulk_button.configure(state='normal' if editing else 'disabled')
        if not enabled:
            self.picture.configure(image=''); self.heading.configure(text='No matching discoveries' if p else 'Open a stock ROM to begin')
            self.meta.configure(text=''); self.description.configure(text=''); self.assignment.configure(text=''); return
        slot=self.selected; row=self.rows[slot]
        image=content.picture(p.discovery_entries[slot],6) if slot in p.discovery_entries else picture(p.rom,slot,6)
        self.photo=ImageTk.PhotoImage(image,master=self.app.root); self.picture.configure(image=self.photo)
        self.heading.configure(text=row['name'])
        self.meta.configure(text=f"{row['category']}  ·  Difficulty {row['difficulty']}  ·  {'Custom replacement' if slot in p.discovery_entries else 'Original discovery'}")
        self.description.configure(text=row['description'])
        self.assignment.configure(text=f"Location {slot+1:02d}: {self.original[slot]['name']}  ·  Map position {row['x']}, {row['y']}\nArtwork: exact 32 × 32 game pixels, enlarged for viewing.")
        self.restore_button.configure(state='normal' if editing and slot in p.discovery_entries else 'disabled')
        self.arrange()

    def save_to_library(self):
        if not self.app.project:return
        try:
            self.app.library.refresh()
            if not self.app.library.store:raise ValueError('Library is unavailable.')
            self.app.library.store.archive(content.capture(self.app.project,self.selected))
            self.app.status.configure(text='Discovery saved to Library with its fixed original location.')
        except Exception as error:self.app.fail(error)

    def restore(self):
        p=self.app.project; slot=self.selected
        if not p or not p.custom_discoveries or slot not in p.discovery_entries:return
        if not messagebox.askyesno('Restore original discovery?', f"Restore {self.original[slot]['name']} at location {slot+1:02d}? The outgoing discovery is kept in Library.", parent=self.app.root):return
        try:
            trial=copy.deepcopy(p);trial.discovery_entries.pop(slot);trial.discovery_identities[slot]=content.stock_id(slot);content.state(trial)
            self.app.library.refresh()
            if not self.app.library.store:raise ValueError('Library is unavailable.')
            self.app.library.store.archive(content.capture(p,slot))
            p.discovery_entries,p.discovery_identities=trial.discovery_entries,trial.discovery_identities
            self.app.update_status()
        except Exception as error:self.app.fail(error)

    def choose_replacement(self):
        if not self.app.project or not self.app.project.custom_discoveries:return
        try:
            self.app.library.refresh(); store=self.app.library.store
            if not store:raise ValueError('Library is unavailable.')
            entries=[e for e in store.entries if e['kind']=='discovery' and content.target_slot(e)==self.selected]
            if not entries:
                messagebox.showinfo('No Library alternatives', f"Import or create a Library discovery tied to {self.original[self.selected]['name']} first.", parent=self.app.root);return
            dialog=tk.Toplevel(self.app.root);dialog.title('Replace '+self.rows[self.selected]['name']);dialog.geometry('620x560');dialog.transient(self.app.root);dialog.grab_set()
            body=ttk.Frame(dialog,padding=16);body.pack(fill='both',expand=True)
            ttk.Label(body,text='Choose a stored alternative for this fixed location.').pack(anchor='w',pady=(0,8))
            choices=ttk.Combobox(body,values=[e['name'] for e in entries],state='readonly');choices.pack(fill='x');choices.current(0)
            preview=ttk.Label(body);preview.pack(anchor='w',pady=12)
            description=ttk.Label(body,wraplength=560,justify='left');description.pack(anchor='w',fill='x')
            def show(event=None):
                e=entries[choices.current()];preview.photo=ImageTk.PhotoImage(content.picture(e,5),master=dialog);preview.configure(image=preview.photo);description.configure(text=e['description'])
            choices.bind('<<ComboboxSelected>>',show);show()
            actions=ttk.Frame(body);actions.pack(side='bottom',fill='x',pady=(12,0))
            def load():
                try:
                    self.app.commit();p=self.app.project;slot=self.selected;e=entries[choices.current()]
                    trial=content.prepare_replacements(p,[e])
                    if not messagebox.askyesno('Replace discovery?', f"Replace {self.rows[slot]['name']} with {e['name']} at the original {self.original[slot]['name']} location?",parent=dialog):return
                    store.archive(content.capture(p,slot))
                    p.discovery_entries,p.discovery_identities=trial.discovery_entries,trial.discovery_identities
                    dialog.destroy();self.app.update_status()
                except Exception as error:self.app.fail(error)
            ttk.Button(actions,text='Cancel',command=dialog.destroy).pack(side='right')
            ttk.Button(actions,text='Use discovery',style='Primary.TButton',command=load).pack(side='right',padx=8)
            self.replacement_dialog=dialog;self.replacement_choices=choices
        except Exception as error:self.app.fail(error)

    def load_all(self):
        p=self.app.project
        if not p or not p.custom_discoveries:return
        try:
            self.app.commit();self.app.library.refresh();store=self.app.library.store
            if not store:raise ValueError('Library is unavailable.')
            groups={}
            for entry in store.entries:
                if entry['kind']!='discovery' or entry['id'].startswith('stock-'):continue
                slot=content.target_slot(entry)
                if slot is not None:groups.setdefault(slot,[]).append(entry)
            if not groups:
                messagebox.showinfo('No matching custom discoveries','Import or create custom discoveries with assigned original locations in Library first.',parent=self.app.root);return
            dialog=tk.Toplevel(self.app.root);dialog.title('Load all custom discoveries');dialog.geometry('780x560');dialog.transient(self.app.root);dialog.grab_set()
            frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
            ttk.Label(frame,text=f'{len(groups)} locations have custom Library discoveries. Other locations stay unchanged.\nReview the replacements. Where several alternatives match, choose which one to use.',wraplength=730).pack(anchor='w',pady=(0,12))
            footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(12,0))
            host=ttk.Frame(frame);host.pack(fill='both',expand=True)
            scroll=self.scroll_type(host,fit_width=True,natural_height=True)
            body=ttk.Frame(scroll.content,padding=8);body.pack(fill='both',expand=True);body.columnconfigure(1,weight=1)
            choices={}
            for row,slot in enumerate(sorted(groups)):
                entries=sorted(groups[slot],key=lambda e:(e['name'].casefold(),e['id']))
                groups[slot]=entries
                ttk.Label(body,text=f"{slot+1:02d} {self.original[slot]['name']}\nCurrent: {self.rows[slot]['name']}",wraplength=280).grid(row=row,column=0,sticky='w',padx=(0,16),pady=8)
                combo=ttk.Combobox(body,values=[e['name'] for e in entries],state='readonly',width=28)
                combo.grid(row=row,column=1,sticky='ew',pady=8)
                combo.current(next((i for i,e in enumerate(entries)if e['id']==p.discovery_identities[slot]),0));choices[slot]=combo
            def accept():
                try:
                    if self.app.project is not p:raise ValueError('The current project changed. Reopen this window.')
                    if not p.custom_discoveries:return
                    entries=[groups[slot][choices[slot].current()]for slot in sorted(groups)]
                    trial=content.prepare_replacements(p,entries)
                    store.archive_many([content.capture(p,slot) for slot in sorted(groups)])
                    p.discovery_entries,p.discovery_identities=trial.discovery_entries,trial.discovery_identities
                    dialog.destroy();self.app.update_status()
                except Exception as error:self.app.fail(error)
            ttk.Button(footer,text='Cancel',command=dialog.destroy).pack(side='right')
            ttk.Button(footer,text='Load all custom discoveries',style='Primary.TButton',command=accept).pack(side='right',padx=8)
            self.bulk_dialog=dialog;self.bulk_choices=choices
            self.app.root.after_idle(scroll.resize)
        except Exception as error:self.app.fail(error)
