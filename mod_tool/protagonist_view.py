"""Playable starting profiles with bounded attribute/skill editing."""
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from sailors import decode_sailors, ATTRIBUTES, SKILLS
from character_portraits import portrait
from sailors import LEVEL_FIELDS

# Editorial campaign summaries; numerical values and portraits come from the ROM.
SUMMARIES = (
    'A young Portuguese explorer following his father’s legacy. His journey combines exploration, discoveries and encounters across the world.',
    'A Spanish sailor turned pirate. Her search for revenge draws her into naval battles and the mystery behind her family’s fate.',
    'An English privateer serving his country at sea. His campaign centres on naval warfare and rivalry with Spain.',
    'A Dutch cartographer travelling to map the world. Exploration and charting unfamiliar seas drive his journey.',
    'An Italian adventurer seeking discoveries and fortune. His travels take him far from home in search of remarkable places.',
    'A young Ottoman merchant seeking a better life. Trade, negotiation and building a business are central to his story.',
)


def characters(rom):
    return [dict(row, description=SUMMARIES[row['id']]) for row in decode_sailors(rom)[:6]]


class CharactersPanel:
    def __init__(self, app, scroll_type):
        self.app = app
        self.loading = False
        self.timer = None
        self.project = None
        self.signature = None
        self.rows = []
        self.rom = None
        self.selected = 0
        self.photo = None
        self.left = ttk.Frame(app.sidebar)
        ttk.Label(self.left, text='Characters', font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 6))
        box = ttk.Frame(self.left)
        box.pack(fill='both', expand=True)
        self.list = tk.Listbox(box, exportselection=False, activestyle='none', height=6, font=('Segoe UI', 10),
                              borderwidth=0, highlightthickness=0, background='white',
                              selectbackground='#0864d9', selectforeground='white')
        self.list.pack(side='left', fill='both', expand=True)
        bar = ttk.Scrollbar(box, command=self.list.yview)
        bar.pack(side='right', fill='y')
        self.list.configure(yscrollcommand=bar.set)
        self.list.bind('<<ListboxSelect>>', self.pick)
        self.frame = ttk.Frame(app.settings_area)
        self.scroll = scroll_type(self.frame, fit_width=True, natural_height=True)
        body = ttk.Frame(self.scroll.content, padding=8)
        body.pack(fill='both', expand=True)
        self.custom = tk.BooleanVar(value=False)
        self.custom_box = ttk.Checkbutton(body,text='Use custom values',variable=self.custom,command=self.toggle,state='disabled')
        self.custom_box.pack(anchor='w',pady=(0,6))
        self.heading = ttk.Label(body, text='Playable Characters', font=('Segoe UI', 20, 'bold'))
        self.heading.pack(anchor='w')
        ttk.Label(body, text='Starting stats, levels and skills • Start a new game to use edits', foreground='#6e7f98').pack(anchor='w', pady=(2, 6))
        profile = ttk.Frame(body, style='Card.TFrame', padding=6)
        profile.pack(fill='x', pady=(0, 6))
        self.picture = ttk.Label(profile, style='Card.TLabel')
        self.picture.grid(row=0, column=0, rowspan=3, sticky='nw', padx=(0, 16))
        profile.columnconfigure(1, weight=1)
        self.details = ttk.Label(profile, style='Card.TLabel')
        self.details.grid(row=0, column=1, sticky='nw')
        self.description = ttk.Label(profile, style='Card.TLabel', wraplength=500)
        self.description.grid(row=1, column=1, sticky='nw', pady=(10, 0))
        def arrange_profile(event):
            narrow = event.width < 420
            self.picture.grid_configure(row=0, column=0, rowspan=1 if narrow else 3)
            self.details.grid_configure(row=1 if narrow else 0, column=0 if narrow else 1, pady=(4,0) if narrow else 0)
            self.description.grid_configure(row=2 if narrow else 1, column=0 if narrow else 1)
            self.details.configure(wraplength=max(150,event.width-36 if narrow else event.width-180))
            self.description.configure(wraplength=max(150,event.width-36 if narrow else event.width-180))
        profile.bind('<Configure>', arrange_profile)
        self.stats_card = ttk.Labelframe(body, text='Starting attributes and levels', padding=6)
        self.stats_card.pack(fill='x', pady=(0, 6))
        self.values = {}
        self.variables = {}
        self.attribute_labels = {}
        self.edit_fields=LEVEL_FIELDS+ATTRIBUTES
        for i, key in enumerate(self.edit_fields):
            row, col = divmod(i, 2)
            label = ttk.Label(self.stats_card, text=key.replace('_',' ').capitalize(), style='Card.TLabel')
            label.grid(row=row, column=col*2, sticky='w', pady=1)
            self.attribute_labels[key] = label
            variable=tk.StringVar()
            self.variables[key]=variable
            value = ttk.Spinbox(self.stats_card,from_=1 if key in LEVEL_FIELDS else 0,to=100,width=5,textvariable=variable,state='disabled')
            variable.trace_add('write',self.schedule)
            value.grid(row=row, column=col*2+1, sticky='e', padx=(12, 20), pady=1)
            self.values[key] = value
        for col in (0, 2): self.stats_card.columnconfigure(col, weight=1)
        def arrange_stats(event):
            narrow = event.width < 460
            for i,key in enumerate(self.edit_fields):
                row,col = (i,0) if narrow else divmod(i,2)
                self.attribute_labels[key].grid_configure(row=row,column=col*2)
                self.values[key].grid_configure(row=row,column=col*2+1)
            self.stats_card.columnconfigure(2,weight=0 if narrow else 1)
        self.stats_card.bind('<Configure>',arrange_stats)
        self.fixed_luck=tk.BooleanVar(value=False)
        self.fixed_luck_box=ttk.Checkbutton(self.stats_card,text='Use fixed starting luck',variable=self.fixed_luck,state='disabled',style='Card.TCheckbutton')
        self.fixed_luck_box.grid(row=10,column=0,columnspan=4,sticky='w',pady=(4,0))
        ttk.Label(self.stats_card,text='Otherwise the game rolls Luck from 40 to 100.',style='Hint.Card.TLabel',wraplength=300).grid(row=11,column=0,columnspan=4,sticky='w',pady=(2,0))
        self.fixed_luck.trace_add('write',self.schedule)
        skills = ttk.Labelframe(body, text='Starting skills', padding=6)
        skills.pack(fill='x')
        self.skill_vars={};self.skill_checks={}
        for i,(key,label,bit) in enumerate(SKILLS):
            variable=tk.BooleanVar(value=False);self.skill_vars[key]=variable
            button=ttk.Checkbutton(skills,text=label,variable=variable,state='disabled',style='Card.TCheckbutton')
            button.grid(row=i//2,column=i%2,sticky='w',padx=(0,16),pady=1)
            self.skill_checks[key]=button;variable.trace_add('write',self.schedule)
        def arrange_skills(event):
            columns=1 if event.width<460 else 2
            for i,(key,_,_)in enumerate(SKILLS):self.skill_checks[key].grid_configure(row=i//columns,column=i%columns)
        skills.bind('<Configure>',arrange_skills)
        self.restore_button=ttk.Button(body,text='Restore selected character',command=self.restore,state='disabled')
        self.restore_button.pack(anchor='w',pady=(6,0))

    def show(self):
        self.left.pack(fill='both', expand=True)
        self.frame.pack(fill='both', expand=True)
        self.app.scroll = self.scroll
        self.refresh()
        self.app.root.after_idle(self.scroll.resize)

    def hide(self):
        self.left.pack_forget()
        self.frame.pack_forget()

    def snapshot(self):
        if not self.app.project:return None
        return (self.app.project.custom_characters,tuple(tuple(self.app.project.character_record(i)[k]for k in self.edit_fields+('skills',))for i in range(6)),tuple(e['id']for e in self.app.project.character_edits if e['id']<6 and e['field']=='luck'))

    def refresh(self):
        project=self.app.project
        if project is not self.project:
            self.cancel();self.project=project;self.rom=project.rom if project else None
            self.rows=characters(self.rom)if project else []
            self.signature=None
        signature=self.snapshot()
        if signature!=self.signature:
            self.signature=signature
            if self.rows:self.render()
        self.custom_box.configure(state='normal'if project else 'disabled')
        self.sync_colors()

    def pick(self, event=None):
        if self.list.curselection():
            selected=self.list.curselection()[0]
            try:self.commit()
            except ValueError as error:
                self.app.status.configure(text='Finish editing: '+str(error));self.refresh_list();return
            self.selected=selected;self.render()

    def refresh_list(self):
        self.list.delete(0,'end')
        for row in self.rows:
            changed=any(e['id']==row['id']for e in self.app.project.character_edits)
            self.list.insert('end',row['name']+('  *'if changed else ''))
            self.list.itemconfigure('end',foreground='#ef7800'if changed else '#17243d',selectforeground='#ef7800'if changed else 'white',selectbackground='#ffe2c0'if changed else '#0864d9')
        if self.rows:
            self.list.selection_set(self.selected);self.list.activate(self.selected);self.list.selection_anchor(self.selected)

    def render(self):
        self.cancel();self.loading=True
        row=dict(self.app.project.character_record(self.selected),description=SUMMARIES[self.selected])
        self.heading.configure(text=row['name'])
        self.details.configure(text=f"{row['nationality']} • Age {row['age']}")
        self.description.configure(text=row['description'])
        self.photo=ImageTk.PhotoImage(portrait(self.rom,row['id'],scale=3))
        self.picture.configure(image=self.photo)
        for key,variable in self.variables.items():variable.set(str(row[key]))
        for key,_,bit in SKILLS:self.skill_vars[key].set(bool(row['skills']&bit))
        self.fixed_luck.set(any(e['id']==self.selected and e['field']=='luck'for e in self.app.project.character_edits))
        self.custom.set(self.app.project.custom_characters)
        self.loading=False;self.refresh_list();self.sync_colors()

    def sync_colors(self):
        if not self.app.project:return
        row=self.app.project.character_record(self.selected);stock=self.rows[self.selected]
        enabled=self.app.project.custom_characters
        for key,widget in self.values.items():
            changed=row[key]!=stock[key]or(key=='luck'and self.fixed_luck.get())
            widget.configure(state='normal'if enabled and(key!='luck'or self.fixed_luck.get())else 'disabled',style='Changed.TSpinbox'if changed else 'TSpinbox')
        for key,_,bit in SKILLS:
            self.skill_checks[key].configure(state='normal'if enabled else 'disabled',style='Changed.Card.TCheckbutton'if (row['skills']^stock['skills'])&bit else 'Card.TCheckbutton')
        self.restore_button.configure(state='normal'if enabled else 'disabled')
        self.fixed_luck_box.configure(state='normal'if enabled else 'disabled',style='Changed.Card.TCheckbutton'if self.fixed_luck.get()else 'Card.TCheckbutton')

    def schedule(self,*args):
        if self.loading or not self.app.project or not self.app.project.custom_characters:return
        self.sync_colors();self.cancel();self.timer=self.app.root.after(350,self.automatic)

    def cancel(self):
        if self.timer is not None:self.app.root.after_cancel(self.timer);self.timer=None

    def commit(self):
        self.cancel()
        if self.app.section!='characters' or self.loading or not self.app.project or self.project is not self.app.project or not self.app.project.custom_characters:return
        values={}
        for key,variable in self.variables.items():
            if key=='luck'and not self.fixed_luck.get():continue
            try:values[key]=int(variable.get())
            except ValueError:raise ValueError(key.capitalize()+' needs a whole number from 0 to 100.')
        values['skills']=sum(bit for key,_,bit in SKILLS if self.skill_vars[key].get())
        self.app.project.update_character(self.selected,values)
        if not self.fixed_luck.get():self.app.project.character_edits=[e for e in self.app.project.character_edits if not(e['id']==self.selected and e['field']=='luck')]
        self.signature=self.snapshot();self.refresh_list();self.sync_colors()

    def automatic(self):
        self.timer=None
        try:self.commit();self.app.update_status()
        except ValueError as error:self.app.status.configure(text='Finish editing: '+str(error))

    def toggle(self):
        if not self.app.project:return
        wanted=self.custom.get()
        try:self.commit()
        except ValueError as error:
            self.custom.set(self.app.project.custom_characters);self.app.fail(error);return
        self.app.project.custom_characters=wanted;self.signature=self.snapshot();self.sync_colors();self.app.update_status()

    def restore(self):
        if not self.app.project or not self.app.project.custom_characters:return
        self.cancel();self.app.project.character_edits=[e for e in self.app.project.character_edits if e['id']!=self.selected]
        self.signature=self.snapshot();self.render();self.app.update_status()
