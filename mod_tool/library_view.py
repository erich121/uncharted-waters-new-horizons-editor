"""Library browser: managed user snapshots, portable import/export, safe swaps."""
import copy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import ImageTk
from content_library import ContentLibrary, capture_ship, new_id, protected_collection
from library_project import load_ship
from ui_theme import SectionCard


class LibraryPanel:
    def __init__(self, app, scroll_type):
        self.app = app
        self.store = None
        self.error = None
        self.rom = None
        self.rows = []
        style = ttk.Style(app.root)
        style.configure('LibraryAction.TButton', font=('Segoe UI',9), padding=(6,2))
        style.configure('LibraryAction.TMenubutton', font=('Segoe UI',9), padding=(6,2))
        style.map('Library.TCombobox', fieldbackground=[('disabled', '#f3f6fa'), ('readonly', 'white')])
        self.left = ttk.Frame(app.sidebar)
        self.library_heading=ttk.Label(self.left, text='Library', font=('Segoe UI',12,'bold'))
        self.library_heading.pack(anchor='w',pady=(0,6))
        self.kind=tk.StringVar(value='Ships')
        self.kind_box=ttk.Combobox(self.left,textvariable=self.kind,values=['Ships','Discoveries','Items'],state='readonly',style='Library.TCombobox')
        self.kind_box.pack(fill='x',pady=(0,6));self.kind_box.bind('<<ComboboxSelected>>',lambda _:self.change_kind())
        self.hide_stock = tk.BooleanVar(value=False)
        self.hide_stock_check = ttk.Checkbutton(self.left, text='Hide stock content', variable=self.hide_stock, command=self.refresh_list)
        self.hide_stock_check.pack(fill='x',pady=(0,6))
        self.search = tk.StringVar()
        search = ttk.Entry(self.left, textvariable=self.search)
        self.search_entry = search
        search.pack(fill='x', pady=(0, 6))
        self.search.trace_add('write', lambda *_: self.refresh_list())
        self.collection = tk.StringVar(value='All entries')
        self.collections = ttk.Combobox(self.left, textvariable=self.collection, state='readonly', values=['All entries'],style='Library.TCombobox')
        self.collections.pack(fill='x', pady=(0, 6))
        self.collections.bind('<<ComboboxSelected>>', lambda _: self.refresh_list())
        footer=ttk.Frame(self.left);footer.pack(side='bottom',fill='x');self.footer=footer
        footer.columnconfigure(0,weight=1);footer.columnconfigure(1,weight=1)
        box = ttk.Frame(self.left);self.list_frame=box
        box.pack(fill='both', expand=True)
        self.list = tk.Listbox(box, exportselection=False, selectmode='extended', background='white', borderwidth=0,
                               highlightthickness=0, selectbackground='#0864d9', selectforeground='white')
        self.list.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(box, command=self.list.yview)
        scrollbar.pack(side='right', fill='y')
        self.list.configure(yscrollcommand=scrollbar.set)
        self.list.bind('<<ListboxSelect>>', lambda _: self.preview())
        self.list.bind('<Control-a>',lambda e:(self.list.selection_set(0,'end'),self.preview(),'break')[-1])
        self.footer_buttons=[]
        for col,(title,action)in enumerate([('Import…',self.import_file),('Export…',self.export_file)]):
            if col==1:
                button=ttk.Menubutton(footer,text=title,style='LibraryAction.TMenubutton')
                menu=tk.Menu(button,tearoff=False)
                menu.add_command(label='Export selected content…',command=self.export_file)
                menu.add_command(label='Export whole Library…',command=lambda:self.export_file(True))
                button.configure(menu=menu)
            else:button=ttk.Button(footer,text=title,command=action,style='LibraryAction.TButton')
            button.grid(row=0,column=col,sticky='ew',pady=(2,0),padx=(0,3)if col==0 else (3,0))
            self.footer_buttons.append(button)
        button=ttk.Button(footer,text='Save collection…',command=self.save_collection,style='LibraryAction.TButton')
        button.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(2,0));self.footer_buttons.append(button)
        self.delete_collection_button=ttk.Button(footer,text='Delete collection…',command=self.delete_collection,style='LibraryAction.TButton')
        self.delete_collection_button.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(2,0));self.footer_buttons.append(self.delete_collection_button)
        self.actions_button=ttk.Menubutton(footer,text='Library actions',style='LibraryAction.TMenubutton')
        self.actions_menu=tk.Menu(self.actions_button,tearoff=False,postcommand=self.populate_actions)
        self.actions_button.configure(menu=self.actions_menu)
        self.small_controls=None
        self.left.bind('<Configure>',self.resize_controls)

        self.frame = ttk.Frame(app.settings_area)
        self.scroll = scroll_type(self.frame, fit_width=True, natural_height=True)
        body = ttk.Frame(self.scroll.content, padding=12)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='Content Library', font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        self.intro = ttk.Label(body, text='Save and reuse ships, discoveries and item settings.', foreground='#6e7f98', wraplength=650)
        self.intro.pack(anchor='w', pady=(4, 6))
        self.notice = ttk.Label(body, text='Open a stock USA ROM to use your Library.', foreground='#6e7f98', wraplength=650)
        self.notice.pack(anchor='w', pady=(0, 10))
        self.main = ttk.Frame(body)
        self.main.pack(fill='x', pady=(0, 10))
        self.card = SectionCard(self.main, 'Stored ship')
        self.card.grid(row=0, column=0, sticky='new')
        preview = ttk.Frame(self.card.body, style='Card.TFrame')
        preview.pack(fill='x')
        self.picture = ttk.Label(preview, style='Card.TLabel')
        info = ttk.Frame(preview, style='Card.TFrame')
        preview.columnconfigure(1, weight=1)
        self.heading = ttk.Label(info, text='Your Library is empty', style='Card.TLabel', font=('Segoe UI', 16, 'bold'))
        self.heading.pack(anchor='w', pady=(0, 6))
        self.ship_summary = ttk.Label(info, style='Card.TLabel')
        self.ship_summary.pack(anchor='w', pady=(0, 4))
        self.family = ttk.Label(info, style='Hint.Card.TLabel')
        self.family.pack(anchor='w')
        self.stats = ttk.Frame(self.card.body, style='Card.TFrame')
        self.stats.pack(fill='x', pady=8)
        self.stat_values = {}
        self.stat_groups = []
        groups = [
            ('Sailing', [('hull','Hull strength'),('power','Sailing power'),('turning','Turning')]),
            ('Guns & crew limits', [('max_guns','Maximum guns'),('min_crew','Minimum sailors'),('max_crew','Crew spaces')]),
            ('Starting fit', [('factory_guns','Guns'),('factory_crew','Crew spaces'),('factory_cargo','Cargo')]),
        ]
        for title, fields in groups:
            group = SectionCard(self.stats, title)
            group.body.columnconfigure(0,weight=1)
            for index,(key,label) in enumerate(fields):
                ttk.Label(group.body,text=label,style='Card.TLabel',font=('Segoe UI',10)).grid(row=index*2,column=0,sticky='w',pady=6)
                variable=tk.StringVar(value='—')
                ttk.Label(group.body,textvariable=variable,style='Card.TLabel',font=('Segoe UI',11,'bold')).grid(row=index*2,column=1,sticky='e',padx=(8,0),pady=6)
                self.stat_values[key]=variable
                if index<2:ttk.Separator(group.body).grid(row=index*2+1,column=0,columnspan=2,sticky='ew')
            self.stat_groups.append(group)
        self.cargo_summary=ttk.Label(self.stats,style='Hint.Card.TLabel')
        self.build_title=ttk.Label(self.card.body,text='Shipbuilding',style='Card.TLabel',font=('Segoe UI',11,'bold'))
        self.build_title.pack(anchor='w',pady=(4,4))
        self.details = ttk.Label(self.card.body, text='Save a ship from your project or import a content file.', style='Card.TLabel', wraplength=300)
        self.details.pack(anchor='w', pady=(2, 8))
        self.description_title = ttk.Label(self.card.body, text='Shipyard description', style='Card.TLabel', font=('Segoe UI', 10, 'bold'))
        self.description_title.pack(anchor='w', pady=(0, 4))
        self.description = ttk.Label(self.card.body, style='Card.TLabel', wraplength=300)
        self.description.pack(anchor='w', pady=(0, 10))
        row = ttk.Frame(self.card.body, style='Card.TFrame')
        self.entry_actions = row
        row.pack(fill='x')
        self.duplicate_button = ttk.Button(row, text='Duplicate', command=self.duplicate)
        self.duplicate_button.pack(side='left')
        self.delete_button = ttk.Button(row, text='Delete from Library', command=self.delete)
        self.delete_button.pack(side='right', padx=(8, 0))
        self.edit_button=ttk.Button(row,text='Edit discovery…',command=self.edit_discovery)
        self.load_card = SectionCard(self.main, 'Use in this project')
        load_card = self.load_card.body
        self.load_card.grid(row=0, column=1, sticky='new', padx=(12, 0))
        self.target_label=ttk.Label(load_card,text='Target slot',style='Card.TLabel');self.target_label.pack(anchor='w',pady=(0,4))
        self.target = ttk.Combobox(load_card, state='readonly', width=18, style='Library.TCombobox')
        self.target.pack(fill='x', pady=(0, 8))
        self.use_locations = tk.BooleanVar(value=True)
        self.locations_check = ttk.Checkbutton(load_card, text='Use saved ports and industry', variable=self.use_locations, style='Card.TCheckbutton')
        self.locations_check.pack(anchor='w', pady=(0, 8))
        self.replace_button = ttk.Button(load_card, text='Load into selected slot…', style='Primary.TButton', command=lambda: self.load(False))
        self.replace_button.pack(fill='x', pady=(0, 6))
        self.add_button = ttk.Button(load_card, text='Add as a new ship', command=lambda: self.load(True))
        self.add_button.pack(fill='x')
        self.load_hint = ttk.Label(load_card, text='Turn off to keep the current ship’s build ports. Test replacements in a new game.',
                  style='Hint.Card.TLabel', wraplength=240)
        self.load_hint.pack(anchor='w', fill='x', pady=(10, 0))
        # arrange_preview owns wrapping for this label. A second Configure
        # handler using the label's width can alternate with the card's width,
        # repeatedly changing its height and starving Tk's event loop.
        self.save_card = SectionCard(self.main, 'Save a project ship')
        self.save_card.grid(row=1, column=1, sticky='new', padx=(12, 0), pady=(10, 0))
        save_card = self.save_card.body
        self.source = ttk.Combobox(save_card, state='readonly', width=25, style='Library.TCombobox')
        self.source.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.save_button = ttk.Button(save_card, text='Save to Library', command=self.save_ship)
        self.save_button.grid(row=0, column=1)
        self.create_button = ttk.Button(save_card, text='Create discovery…', command=self.create_discovery)
        self.create_button.grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.create_button.grid_remove()
        save_card.columnconfigure(0, weight=1)
        self.layout = None
        def arrange_preview(event=None):
            width = max(240, self.scroll.canvas.winfo_width() - 24)
            wide = width >= 980
            preview_width = int((width - 12) * .72) if wide else width
            content_width = max(200, preview_width - 44)
            hero_wide = content_width >= 380
            for col in (0, 1):
                self.main.columnconfigure(col, weight=(18 if col == 0 else 7) if wide else (1 if col == 0 else 0), uniform='library' if wide else '')
            self.main.rowconfigure(1, weight=1 if wide else 0)
            self.card.grid_configure(row=0, column=0, rowspan=1 if self.is_discovery() else 2 if wide else 1)
            self.load_card.grid_configure(row=0 if wide else 1, column=1 if wide else 0, padx=(12, 0) if wide else 0, pady=(0, 0) if wide else (10, 0))
            self.save_card.grid_configure(row=1 if wide else 2, column=1 if wide else 0, padx=(12, 0) if wide else 0, pady=(10, 0))
            if self.is_discovery():
                self.load_card.grid_remove()
                self.save_card.grid_configure(row=0 if wide else 1,pady=0 if wide else (10,0))
            self.picture.grid(row=0, column=0, sticky='nw', padx=(0, 12) if hero_wide else 0)
            info.grid(row=0 if hero_wide else 1, column=1 if hero_wide else 0, sticky='nw', pady=(0, 0) if hero_wide else (8, 0))
            preview.columnconfigure(1, weight=1 if hero_wide else 0)
            preview.columnconfigure(0, weight=0 if hero_wide else 1)
            for label in (self.heading, self.ship_summary, self.family):label.configure(wraplength=max(160, content_width - (144 if self.is_discovery()or self.is_item() else 204) if hero_wide else content_width))
            for label in (self.details, self.description):label.configure(wraplength=content_width)
            self.intro.configure(wraplength=width);self.notice.configure(wraplength=width)
            self.load_hint.configure(wraplength=max(200, width - preview_width - 56) if wide else content_width)
            save_width = width - preview_width - 56 if wide else content_width
            stacked = save_width < 360
            self.source.grid_configure(row=0, column=0, columnspan=2 if stacked else 1, padx=0 if stacked else (0, 8))
            self.save_button.grid_configure(row=1 if stacked else 0, column=0 if stacked else 1, sticky='w', pady=(8, 0) if stacked else 0)
            if self.is_discovery():self.create_button.grid_configure(row=2 if stacked else 1, column=0)
            columns = 3 if content_width >= 610 else 2 if content_width >= 450 else 1
            for col in range(3):self.stats.columnconfigure(col,weight=1 if col<columns else 0,uniform='library-stats' if col<columns else '')
            for index,group in enumerate(self.stat_groups):
                group.grid(row=index//columns,column=index%columns,sticky='new',padx=(0,8) if index%columns<columns-1 else 0,pady=(0,8))
            self.cargo_summary.grid(row=(len(self.stat_groups)+columns-1)//columns,column=0,columnspan=columns,sticky='w',pady=(0,4))
            self.layout = (wide, columns)
            self.scroll.resize()
        self.scroll.canvas.bind('<Configure>', arrange_preview, add='+')
        self.arrange_preview = arrange_preview
        self.app.root.after_idle(arrange_preview)

    def show(self):
        self.left.pack(fill='both', expand=True)
        self.frame.pack(fill='both', expand=True)
        self.refresh()
        self.app.scroll = self.scroll
        self.app.root.after_idle(self.scroll.resize)

    def hide(self):
        self.left.pack_forget()
        self.frame.pack_forget()

    def refresh(self):
        p = self.app.project
        if p is not None and (self.rom is not p.rom or self.store is None):
            self.rom = p.rom
            try:
                self.store = ContentLibrary(p.rom)
                self.store.initialize_presets(p.source)
                self.store.migrate_bundled_defaults(p.source)
                self.error = None
            except Exception as error:
                # Never replace an unreadable Library with an empty one.
                self.store = None
                self.error = str(error)
        elif self.store is not None:
            try:
                if p is not None:
                    self.store.initialize_presets(p.source)
                    self.store.migrate_bundled_defaults(p.source)
                self.store.reload_if_changed()
                self.error = None
            except (ValueError, OSError) as error:
                self.error = str(error)
        values = [f'{i+1:02d}  {s["name"]}' for i, s in enumerate(p.ships)] if p else []
        if p and self.is_item():
            self.item_ids=[r['id']for r in __import__('items').catalogue(p.rom)]
            values=[r['name']for r in __import__('items').catalogue(p.rom)]
        if p and self.is_discovery():values=[f'{i+1:02d}  {s["name"]}'for i,s in enumerate(__import__('discovery_content').rows(p))]
        for box in (self.source, self.target):
            index = box.current()
            box.configure(values=values)
            if values:
                box.current(min(max(index, 0), len(values)-1))
        enabled = p is not None and self.store is not None
        self.save_button.configure(state='normal' if enabled else 'disabled')
        if self.error:
            self.notice.configure(text='Library could not be opened: ' + self.error)
        elif self.store:
            self.notice.configure(text=f'{sum(e["kind"]==self.entry_kind() for e in self.store.entries)} stored '+('discoveries'if self.is_discovery()else 'items'if self.is_item()else 'ships')+' · Originals are protected. Duplicate one to make your own copy.')
        self.refresh_list()

    def selected(self):
        return [self.rows[i] for i in self.list.curselection() if i < len(self.rows)]

    def refresh_list(self):
        if getattr(self, 'changing_kind', False):
            return
        previous = {e['id'] for e in self.selected()}
        self.list.delete(0, 'end')
        self.rows = []
        if self.store:
            self.collections.configure(values=['All entries'] + sorted(self.store.collections))
            allowed = self.store.collections.get(self.collection.get())
            for entry in sorted(self.store.entries, key=lambda e:self.entry_name(e).casefold()):
                if entry['kind']!=self.entry_kind():continue
                if self.hide_stock.get() and entry['id'].startswith('stock-'):continue
                if self.search.get().strip().casefold() not in self.entry_name(entry).casefold() or allowed is not None and entry['id'] not in allowed:
                    continue
                self.rows.append(entry)
                self.list.insert('end', self.entry_name(entry))
                if entry['id'] in previous:
                    self.list.selection_set(len(self.rows)-1)
        if self.rows and not self.list.curselection():
            self.list.selection_set(0)
        self.preview()

    def preview(self):
        entries = self.selected()
        enabled = bool(entries and self.app.project and self.store)
        self.create_button.configure(state='normal'if self.app.project and self.store else 'disabled')
        self.edit_button.configure(state='normal'if enabled and not entries[0]['id'].startswith('stock-') else 'disabled')
        self.delete_collection_button.configure(state='normal'if self.store and self.collection.get()in self.store.collections and not protected_collection(self.collection.get()) else 'disabled')
        for button in (self.duplicate_button, self.replace_button, self.add_button):
            button.configure(state='normal' if enabled else 'disabled')
        self.delete_button.configure(state='normal' if enabled and not entries[0]['id'].startswith('stock-') else 'disabled')
        export_menu = self.app.root.nametowidget(str(self.footer_buttons[1].cget('menu')))
        export_menu.entryconfigure(0, state='normal' if entries and self.store else 'disabled')
        if not entries:
            self.heading.configure(text='No discovery selected' if self.is_discovery() else 'No item selected'if self.is_item()else 'No ship selected')
            self.details.configure(text='Save content from your project or import a Library file.')
            self.picture.configure(image='')
            for widget in (self.stats, self.ship_summary, self.family, self.description_title, self.description, self.build_title):widget.pack_forget()
            return
        entry = entries[0]
        if self.is_discovery():
            self.preview_discovery(entry);return
        if self.is_item():
            self.preview_item(entry);return
        s = entry['ship']
        offer = entry.get('availability')
        self.locations_check.configure(state='normal' if offer is not None else 'disabled')
        from ports import PORT_NAMES
        availability = ('Build ports: ' + (', '.join(PORT_NAMES[p] for p in offer['ports']) or 'None') + f"\nRequired industry: {offer['industry']}" if offer is not None else f"Required industry: {s['industry']}\nBuild ports not stored in this older entry; project assignments will be kept.")
        description=entry.get('description',__import__('ship_descriptions').stock_text(self.app.project.rom,entry['family']))
        from portraits import unpack, image
        raw = unpack([dict(id=0, tiles=entry['portrait'])], 1)[0]
        self.photo = ImageTk.PhotoImage(image(raw, self.app.project.rom, 3))
        self.picture.configure(image=self.photo)
        self.heading.configure(text=s['name'])
        self.ship_summary.configure(text=f"Base price: {s['price_gold']/10000:g} gold bars   ·   Total capacity: {s['capacity']}",font=('Segoe UI',11,'bold'))
        self.family.configure(text='Map and battle style: ' + self.app.project.original[entry['family']]['name'])
        self.ship_summary.pack(after=self.heading, anchor='w', pady=(0, 4))
        self.family.pack(after=self.ship_summary, anchor='w')
        self.stats.pack(before=self.details, fill='x', pady=(12,4))
        self.build_title.pack(before=self.details,anchor='w',pady=(4,4))
        self.cargo_summary.configure(text=f"Cargo at maximum guns and crew: {s['capacity']-s['max_guns']-s['max_crew']}")
        for key, variable in self.stat_values.items():variable.set(str(s[key]))
        self.details.configure(text=availability)
        self.description_title.pack(before=self.entry_actions, anchor='w', pady=(0, 4))
        self.description.configure(text=description)
        self.description.pack(before=self.entry_actions, anchor='w', pady=(0, 10))

    def clear_library(self):
        self.refresh()
        if not self.store:return
        if not messagebox.askyesno('Delete Library?', 'Reset the Library to its supplied content?\n\nYour saved entries and collections will be removed. Stock Ships, Stock Discoveries and the supplied custom content will be restored.\n\nYour current project stays unchanged.', parent=self.app.root):return
        try:
            self.store.restore_presets(self.app.project.source);self.collection.set('All entries');self.search.set('');self.refresh()
            self.app.status.configure(text='Default Library restored. Current project unchanged.')
        except Exception as error:self.app.fail(error)

    def save_ship(self):
        if not self.store or not self.app.project or self.source.current() < 0:
            return
        try:
            self.app.commit()
            slot = self.source.current()
            entry = __import__('item_library').capture(self.app.project,self.item_ids[slot])if self.is_item()else __import__('discovery_content').capture(self.app.project,slot)if self.is_discovery()else capture_ship(self.app.project, slot)
            old = next((e for e in self.store.entries if e['id'] == entry['id']), None)
            if old and old != entry and entry['id'].startswith('stock-'):
                entry['id'] = new_id()
                old = None
            if old and old != entry and not messagebox.askyesno('Update Library version?', 'Update this Library entry with your current settings? Other projects keep their saved copies.', parent=self.app.root):
                return
            self.store.put(entry)
            if self.entry_kind()=='ship':self.app.project.ship_identities[slot] = entry['id']
            self.reveal_entry(entry['id'])
        except Exception as error:
            self.app.fail(error)

    def load(self, added):
        if self.is_discovery():return
        if self.is_item():self.load_item();return
        if not self.selected() or not self.app.project:
            return
        try:
            self.app.commit()
            p = self.app.project
            entry = self.selected()[0]
            slot = None if added else self.target.current()
            trial = copy.deepcopy(p)
            # The confirmation explicitly approves redirecting displaced choices.
            use_locations = self.use_locations.get()
            target = load_ship(trial, entry, slot, replace_fleet=True, use_locations=use_locations)
            archive = None if added else capture_ship(p, slot)
            refs = 0 if added else sum(i == slot for nation in p.fleet_rules for role in nation for i in role)
            message = ('Add ' + entry['ship']['name'] + ' as a new ship?' if added else
                       f"Load {entry['ship']['name']} into slot {slot+1:02d}?\n\n{p.ships[slot]['name']} will be preserved in the Library.\nCustom Fleet references follow ships moved between slots. If the outgoing ship leaves the project, its {refs} custom fleet choices will use the incoming ship.\n\nStock fleets and existing saves use ROM slots. Test this change with a new game.")
            message += '\n\n' + ('Use saved build ports and required industry.' if use_locations and 'availability' in entry else 'Keep project build ports and required industry.')
            if not messagebox.askyesno('Load Library ship', message, parent=self.app.root):
                return
            if archive:
                self.store.archive(archive)
            load_ship(p, entry, slot, replace_fleet=True, use_locations=use_locations)
            self.app.selected = target
            self.app.reload_project_view()
            self.refresh()
        except Exception as error:
            self.app.fail(error)

    def reveal_entry(self, identity):
        """Keep newly saved content visible, even under restrictive filters."""
        allowed = self.store.collections.get(self.collection.get())
        if allowed is not None and identity not in allowed:
            self.collection.set('All entries')
        self.search.set('')
        if identity.startswith('stock-'):
            self.hide_stock.set(False)
        self.refresh()
        for index, entry in enumerate(self.rows):
            if entry['id'] == identity:
                self.list.selection_clear(0, 'end')
                self.list.selection_set(index)
                self.list.activate(index)
                self.list.see(index)
                self.preview()
                break

    def duplicate(self):
        if not self.selected():
            return
        try:
            entry = copy.deepcopy(self.selected()[0])
            entry['id'] = new_id()
            name = simpledialog.askstring('Duplicate entry', 'Name for the copy:', initialvalue=self.entry_name(entry), parent=self.app.root)
            if not name:
                return
            if self.is_discovery()or self.is_item():entry['name']=name
            else:entry['ship']['name'] = name
            self.store.put(entry)
            self.reveal_entry(entry['id'])
        except Exception as error:
            self.app.fail(error)

    def restore_original(self, slot):
        try:
            self.refresh()
            if not self.store:
                raise ValueError('The Library must be available to preserve the outgoing ship.')
            p = self.app.project
            if not messagebox.askyesno('Restore original ship?', 'Preserve this ship in the Library and restore the original ship? Custom Fleet choices using the outgoing ship will use the restored original. If the original is elsewhere in the project, the two ships will swap.', parent=self.app.root):
                return
            from library_project import restore_ship
            restore_ship(p, slot, archive=self.store.archive)
            self.app.reload_project_view()
        except Exception as error:
            self.app.fail(error)

    def delete(self):
        if not self.selected() or self.selected()[0]['id'].startswith('stock-'):
            return
        identity = self.selected()[0]['id']
        if not messagebox.askyesno('Delete Library entry?', 'Delete this copy from the Library? Projects that use it keep their own copies.', parent=self.app.root):
            return
        old = copy.deepcopy((self.store.entries, self.store.collections))
        try:
            self.store.entries = [e for e in self.store.entries if e['id'] != identity]
            self.store.collections = {k: [i for i in v if i != identity] for k, v in self.store.collections.items()}
            self.store.save()
            self.refresh()
        except Exception as error:
            self.store.entries, self.store.collections = old
            self.app.fail(error)

    def save_collection(self):
        if not self.selected():
            return
        name = simpledialog.askstring('Save collection', 'Name this group (Ctrl or Shift selects several entries):', parent=self.app.root)
        if not name or not name.strip() or len(name) > 80:
            return
        if name == 'All entries' or protected_collection(name):
            self.app.fail(ValueError('Choose another collection name.'))
            return
        if name in self.store.collections and not messagebox.askyesno('Replace collection?', 'Replace the entries in this collection with your current selection?', parent=self.app.root):
            return
        previous = copy.deepcopy(self.store.collections)
        try:
            self.store.collections[name] = [e['id'] for e in self.selected()]
            self.store.save()
            self.collection.set(name)
            self.refresh()
        except Exception as error:
            self.store.collections = previous
            self.app.fail(error)

    def delete_collection(self):
        if not self.store or self.collection.get() not in self.store.collections or protected_collection(self.collection.get()):
            return
        name=self.collection.get()
        if not messagebox.askyesno('Delete collection?',f'Delete the collection "{name}"?\nIts entries will remain in the Library.',parent=self.app.root):
            return
        previous=copy.deepcopy(self.store.collections)
        try:
            del self.store.collections[name]
            self.store.save()
            self.collection.set('All entries')
            self.refresh()
        except Exception as error:
            self.store.collections=previous
            self.app.fail(error)

    def import_file(self):
        if not self.store:
            return
        path = filedialog.askopenfilename(title='Import Library content', filetypes=[('New Horizons Library', '*.nhlib')], parent=self.app.root)
        if not path:
            return
        try:
            entries, collections = self.store.read(path)
            if not messagebox.askyesno('Import content?', f'Import {len(entries)} entries and {len(collections)} collections?\nExisting versions of these entries may be updated. Your projects keep their own copies.', parent=self.app.root):
                return
            self.store.import_file(path, replace=True)
            self.refresh()
        except Exception as error:
            self.app.fail(error)

    def export_file(self, all_entries=False):
        if not self.store:
            return
        identities = None if all_entries else [e['id'] for e in self.selected()]
        if identities == []:
            self.app.status.configure(text='Select Library content to export first.')
            return
        path = filedialog.asksaveasfilename(title='Export whole Library' if all_entries else 'Export selected content', defaultextension='.nhlib', filetypes=[('New Horizons Library', '*.nhlib')], parent=self.app.root)
        if path:
            try:
                self.store.export_file(path, identities)
            except Exception as error:
                self.app.fail(error)

    def is_item(self):return self.kind.get()=='Items'

    def is_discovery(self):
        return self.kind.get() == 'Discoveries'

    def resize_controls(self,event=None):
        small=self.app.root.winfo_height()<820
        if self.small_controls==small:return
        self.small_controls=small
        if small:
            self.library_heading.pack_forget();self.collections.pack_forget()
            for button in self.footer_buttons:button.grid_remove()
            self.actions_button.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(4,0))
        else:
            self.actions_button.grid_remove()
            for button in self.footer_buttons:button.grid()
            self.library_heading.pack(before=self.kind_box,anchor='w',pady=(0,6))
            self.collections.pack(before=self.list_frame,fill='x',pady=(0,6))

    def populate_actions(self):
        menu=self.actions_menu;menu.delete(0,'end')
        menu.add_command(label='Import content…',command=self.import_file)
        menu.add_command(label='Export selected content…',command=self.export_file,state='normal'if self.store and self.selected()else 'disabled')
        menu.add_command(label='Export whole Library…',command=lambda:self.export_file(True))
        menu.add_command(label='Save selection as collection…',command=self.save_collection)
        menu.add_command(label='Delete collection…',command=self.delete_collection,state='normal'if self.store and self.collection.get()in self.store.collections and not protected_collection(self.collection.get()) else 'disabled')
        collections=tk.Menu(menu,tearoff=False)
        def choose(name):self.collection.set(name);self.refresh_list()
        for name in ['All entries']+(sorted(self.store.collections)if self.store else []):
            collections.add_command(label=name,command=lambda n=name:choose(n))
        menu.add_cascade(label='View collection',menu=collections)

    def entry_kind(self):
        return 'item'if self.is_item()else 'discovery' if self.is_discovery() else 'ship'

    @staticmethod
    def entry_name(entry):
        return entry['ship']['name']if entry['kind']=='ship'else entry['name']

    def change_kind(self):
        # Clearing search invokes its trace synchronously. Do not preview the
        # new content kind using the old ship/discovery/item dropdown values.
        self.changing_kind = True
        try:
            self.arrange_kind()
        finally:
            self.changing_kind = False
        self.refresh()
        self.arrange_preview()

    def arrange_kind(self):
        self.search.set('')
        self.source.set('')
        self.target.set('')
        self.target.pack(before=self.locations_check,fill='x',pady=(0,8))if self.locations_check.winfo_manager()else self.target.pack(before=self.replace_button,fill='x',pady=(0,8))
        self.target_label.pack(before=self.target,anchor='w',pady=(0,4))
        self.add_button.pack(before=self.load_hint,fill='x')
        self.locations_check.configure(text='Use saved ports and industry')
        self.load_card.set_title('Use in this project')
        if self.is_item():
            self.target_label.pack_forget();self.target.pack_forget();self.add_button.pack_forget()
            self.locations_check.configure(text='Use saved selling ports',state='normal');self.locations_check.pack(before=self.replace_button,anchor='w',pady=(0,8))
            self.save_card.set_title('Save a project item');self.card.set_title('Stored item')
            self.create_button.grid_remove();self.edit_button.pack_forget()
            self.replace_button.configure(text='Load item settings')
            self.load_hint.configure(text='Updates the original item’s price and, optionally, selling ports. Full shops are never overwritten. Pictures and descriptions stay original.')
        elif self.is_discovery():
            self.locations_check.pack_forget()
            self.save_card.set_title('Save a project discovery');self.card.set_title('Stored discovery')
            self.create_button.grid()
            self.edit_button.pack(side='left', padx=8)
            self.add_button.configure(text='Load selected discoveries…')
            self.replace_button.configure(text='Load discovery…')
            self.load_hint.configure(text='Each discovery is tied to an original game location. Import/export shares Library entries with that assignment. Select several to load them together; one alternative per location. Use a new game to test changes.')
        else:
            self.locations_check.pack(before=self.replace_button, anchor='w', pady=(0, 8))
            self.save_card.set_title('Save a project ship');self.card.set_title('Stored ship')
            self.create_button.grid_remove()
            self.edit_button.pack_forget()
            self.add_button.configure(text='Add as a new ship')
            self.replace_button.configure(text='Load into selected slot…')
            self.target.configure(state='readonly')
            self.load_hint.configure(text='Turn off to keep the current ship’s build ports. Test replacements in a new game.')

    def preview_discovery(self, entry):
        from discovery_content import picture
        from discoveries import read_text
        self.photo = ImageTk.PhotoImage(picture(entry, 4))
        self.picture.configure(image=self.photo)
        self.heading.configure(text=entry['name'])
        for widget in (self.stats, self.ship_summary, self.family, self.description_title, self.description, self.build_title):widget.pack_forget()
        category = read_text(self.app.project.rom, 0xb0cf7, entry['category'])
        self.details.configure(text=f"Category: {category}   •   Difficulty: {entry['difficulty']}\n\n{entry['description']}\n\nArtwork: 32×32 pixels / 15 visible colours; exact game preview.")
        self.add_button.configure(state='normal' if len(self.selected()) > 1 else 'disabled')
        from discovery_content import target_slot
        slot = target_slot(entry)
        if slot is not None:
            self.target.current(slot)
            self.target.configure(state='disabled')
            from discoveries import catalogue
            self.details.configure(text=self.details.cget('text')+f"\n\nReplaces: {slot+1:02d} {catalogue(self.app.project.rom)[slot]['name']} (fixed location).")
        else:
            self.target.configure(state='readonly')
            self.details.configure(text=self.details.cget('text')+'\n\nOlder entry: use Edit discovery to assign its original location.')
        self.edit_button.configure(state='disabled' if entry['id'].startswith('stock-') else 'normal')

    def create_discovery(self):
        from discovery_dialog import open_editor
        open_editor(self)

    def edit_discovery(self):
        if self.selected() and not self.selected()[0]['id'].startswith('stock-'):
            from discovery_dialog import open_editor
            open_editor(self, self.selected()[0])


    def preview_item(self,entry):
        from items import catalogue,picture,weapon_rank
        from currency import item_price
        from ports import PORT_NAMES
        item=entry['item_id'];row=next(r for r in catalogue(self.app.project.rom)if r['id']==item)
        self.photo=ImageTk.PhotoImage(picture(self.app.project.rom,item,4));self.picture.configure(image=self.photo)
        self.heading.configure(text=entry['name'])
        for widget in (self.stats,self.family,self.description_title,self.description,self.build_title):widget.pack_forget()
        self.ship_summary.configure(text='Base price: '+item_price(entry['price_gold']),font=('Segoe UI',11,'bold'))
        self.ship_summary.pack(after=self.heading,anchor='w',pady=(0,4))
        rank=weapon_rank(self.app.project.rom,item)
        sources='\n'.join(PORT_NAMES[s['port']]+(' — Early morning'if s['early']else ' — Regular')for s in entry['sources'])or 'Not sold at any port.'
        self.details.configure(text=f"Original item: {row['name']}"+(f'  •  Weapon rank: {rank}'if rank else '')+f"\n\n{row['description']}\n\nSelling ports:\n{sources}")
        self.add_button.configure(state='disabled')
        self.replace_button.configure(state='normal'if len(self.selected())==1 else 'disabled')

    def load_item(self):
        if len(self.selected())!=1 or not self.app.project or not self.store:return
        try:
            self.app.commit()
            from item_library import prepare,capture,apply
            entry=self.selected()[0];trial=prepare(self.app.project,entry,self.use_locations.get())
            if not messagebox.askyesno('Load item settings?',f"Apply {entry['name']} to its original item? Other items are kept. Use a new game to test starting prices and shops.",parent=self.app.root):return
            self.store.archive(capture(self.app.project,entry['item_id']))
            apply(self.app.project,trial);self.app.reload_project_view();self.refresh()
        except Exception as error:self.app.fail(error)
