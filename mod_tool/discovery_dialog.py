"""Create/edit a Library discovery with exact 32x32 SNES conversion preview."""
import copy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk
from content_library import new_id
from discovery_content import validate, picture, convert_png, capture, bind, target_slot
from discoveries import read_text, catalogue


def open_editor(panel, entry=None):
    app = panel.app
    if not app.project or not panel.store:
        return
    creating = entry is None
    source_slot = max(0, panel.source.current())
    draft = copy.deepcopy(entry if entry else capture(app.project, source_slot))
    if creating or draft['id'].startswith('stock-'):
        draft['id'] = new_id()
    if creating:
        draft['name'] = 'New Discovery'
        draft['description'] = 'Describe your discovery here.'
    dialog = tk.Toplevel(app.root)
    dialog.title('Library — Discovery')
    dialog.geometry(f'720x{max(560,min(720,app.root.winfo_screenheight()-80))}')
    dialog.minsize(520, 560)
    dialog.transient(app.root)
    dialog.grab_set()
    panel.discovery_dialog = dialog
    body = ttk.Frame(dialog, padding=18)
    body.pack(fill='both', expand=True)
    body.columnconfigure(1, weight=1)
    location_label = ttk.Label(body, text='Original location')
    location_label.grid(row=8, column=0, sticky='w', pady=6)
    location = ttk.Combobox(body, values=[f"{r['id']+1:02d} {r['name']}" for r in catalogue(app.project.rom)], state='readonly')
    assigned = target_slot(draft)
    location.current(source_slot if assigned is None else assigned)
    location.grid(row=8, column=1, sticky='ew')
    if not creating and assigned is not None:
        location.configure(state='disabled')
    name = tk.StringVar(value=draft['name'])
    difficulty = tk.StringVar(value=str(draft['difficulty']))
    categories = [read_text(app.project.rom, 0xb0cf7, i) for i in range(7)]
    ttk.Label(body, text='Discovery name').grid(row=0, column=0, sticky='w', padx=(0, 12), pady=6)
    ttk.Entry(body, textvariable=name).grid(row=0, column=1, sticky='ew')
    ttk.Label(body, text='Category').grid(row=1, column=0, sticky='w', pady=6)
    category = ttk.Combobox(body, values=categories, state='readonly')
    category.current(draft['category'])
    category.grid(row=1, column=1, sticky='ew')
    ttk.Label(body, text='Difficulty').grid(row=2, column=0, sticky='w', pady=6)
    ttk.Spinbox(body, from_=0, to=255, textvariable=difficulty).grid(row=2, column=1, sticky='w')
    ttk.Label(body, text='Description (up to 226 characters)').grid(row=3, column=0, columnspan=2, sticky='w', pady=(12, 4))
    description = tk.Text(body, height=5, wrap='word', font=('Segoe UI', 11))
    description.insert('1.0', draft['description'])
    description.grid(row=4, column=0, columnspan=2, sticky='nsew')
    body.rowconfigure(4, weight=1)
    art = ttk.Frame(body)
    art.grid(row=5, column=0, columnspan=2, sticky='w', pady=12)
    preview = ttk.Label(art)
    preview.pack(side='left', padx=(0, 16))
    def refresh():
        preview.photo = ImageTk.PhotoImage(picture(draft, 4), master=dialog)
        preview.configure(image=preview.photo)
    refresh()
    def import_png():
        path = filedialog.askopenfilename(title='Import discovery PNG', filetypes=[('PNG image', '*.png')], parent=dialog)
        if not path:
            return
        try:
            draft.update(convert_png(path))
            refresh()
        except Exception as error:
            messagebox.showerror('Discovery artwork', str(error), parent=dialog)
    ttk.Button(art, text='Import PNG…', command=import_png).pack(anchor='w', pady=(18, 8))
    ttk.Label(art, text='Exact game preview\n32×32 pixels · 15 visible colours', foreground='#6e7f98').pack(anchor='w')
    ttk.Label(body, text='Saved in your Library. Apply it from Discoveries > Replace from Library.\nIt keeps the original location. The game still chooses its usual 50 discoveries.',
              wraplength=640, foreground='#6e7f98').grid(row=6, column=0, columnspan=2, sticky='w', pady=(0, 12))
    actions = ttk.Frame(body)
    actions.grid(row=7, column=0, columnspan=2, sticky='e')
    def save():
        try:
            changed = dict(draft, name=name.get().strip(), description=' '.join(description.get('1.0', 'end').split()), category=category.current(), difficulty=int(difficulty.get()))
            if creating:
                changed.pop('replaces', None); changed['version'] = 1
            changed = bind(changed, location.current())
            existing = next((e for e in panel.store.entries if e['id'] == changed['id']), None)
            if existing and existing != changed and not messagebox.askyesno('Update Library discovery?', 'Update this Library discovery? Projects that use it keep their saved copies.', parent=dialog):
                return
            panel.store.put(changed)
            dialog.destroy()
            panel.reveal_entry(changed['id'])
        except Exception as error:
            messagebox.showerror('Check discovery', str(error), parent=dialog)
    ttk.Button(actions, text='Cancel', command=dialog.destroy).pack(side='left', padx=8)
    save_button = ttk.Button(actions, text='Save to Library', command=save, style='Primary.TButton')
    save_button.pack(side='left')
    panel.discovery_editor = dict(name=name, difficulty=difficulty, category=category, description=description, location=location, import_png=import_png, save=save_button, draft=draft)
    for widget in body.grid_slaves():
        row = int(widget.grid_info()['row'])
        widget.grid_configure(row=0 if widget in (location, location_label) else row+1)
    body.rowconfigure(4, weight=0); body.rowconfigure(5, weight=1)
