"""Search-free, sectioned help for the editor; no ROM required."""
import tkinter as tk
from tkinter import ttk
import webbrowser
from backend import TOOL_VERSION

REPOSITORY='https://github.com/erich121/uncharted-waters-new-horizons-editor'
SECTIONS={
 'Getting Started':[
  ('Open a ROM','Click Open stock ROM and choose the original USA SNES release as an .sfc, .smc or ZIP file. The editor verifies the ROM before opening it. The source ROM stays unchanged.'),
  ('Create and save a project','Opening a stock ROM creates a new project. Enable the relevant Use custom switch to edit values. Valid edits save into the current project automatically and appear orange when changed from default. Click Save project to save a project file on disk. Open project restores those settings; you must also supply the compatible stock ROM.'),
  ('Export your changes','Click Export ROM and IPS and choose a new output filename. The editor creates a playable ROM, an IPS patch and a changes report. Existing output files are protected from overwriting. Apply the IPS to the original headerless USA ROM when sharing your patch.'),
  ('Test in an emulator','Restart the emulator when changing ROMs. Start a new game for changes to starting characters, town economies and stock. Keep backups of your ROM, project and saves.'),
 ],
 'Features & Settings':[
  ('Ships','Edit the 25 original classes and add up to five new classes. Specifications covers stats, prices, total capacity and starting equipment. Cargo is calculated from the space left after guns and crew. Availability sets new-build ports and required industry; capital requirements must be reachable at their fixed starting industry.'),
  ('Ship portraits','Graphics can reuse a stock visual family or convert an imported PNG into a ship portrait. Review the conversion before accepting it. Custom portraits are stored in the project. Map and battle icons and descriptions follow the original visual family.'),
  ('Mates and fleet captains','Browse portraits, nationality, attributes and skills. Enable custom editing to change verified attributes and starting skills. Story companions keep their original skills, but additional skills can be assigned. The lists show starting roles; some fleet captains can later become mates.'),
  ('World','Port Information is a read-only overview of the current project. Goods, Items and Economy have their own editing pages. Changed goods, shops and economy requirements also update Port Information. Discoveries shows the original catalogue, not which discoveries are active in your save.'),
  ('Gameplay and fleets','Easy Settings has 13 combinable presets. Review the changes before applying; randomized presets offer a four-digit seed and Blind shuffle. Applying again does not stack increases. Overlapping settings use the last preset; unrelated settings stay as they are. Battles contains Fleet Control, which adds manual mate turns, camera focus and a Select-button automation toggle. Under World, Use custom fleets configures national flagship and escort replacements. Custom Fleets is experimental and does not change every fleet.'),
  ('Seed shuffles','Gameplay → World groups random mates, fleet captains, items, goods and original-ship building locations. Checking a setting opens its options and preview; click the active Seed / Edit link to reopen it. Enter four digits (0000–9999) for a repeatable arrangement. Mates and captains have separate seeds and options for names, attributes and skills; mates can also shuffle starting ports.'),
  ('Blind shuffle','Each randomizer popup includes Blind shuffle. Blind mode uses a different arrangement for the same seed and hides the preview. Blind item, goods and original-ship building destinations are also hidden in the World views and exported changes report. Saved projects retain the settings and data needed to reproduce the shuffle.'),
  ('Editing switches and Restore','Use custom switches unlock manual editing; unchecking one does not discard values or disable changes applied by a preset. Orange marks values changed from default. Use the existing Restore controls or section reset menu to reset changes. Reset Gameplay clears its settings and active shuffles.'),
  ('Repair Safeguard','On Ships → Fixes, Repair Safeguard adjusts repair calculations when ship stats or prices change. It is off by default and is saved with the project.'),
 ],
 'Compatibility & Troubleshooting':[
  ('ROM requirements','Only the verified original USA SNES release is supported as input. A supported 512-byte copier header is removed when reading. Exports are headerless. Translations, other regional releases and previously patched ROMs are not supported as source ROMs. No game ROM is included.'),
  ('Projects and exports','A project stores editor settings; it is not a game save or a playable ROM. Export after editing to create a ROM for your emulator. Earlier supported project formats still open. Added ships, imported portraits and certain gameplay patches expand the ROM to 4 MiB.'),
  ('Save files','The editor does not rewrite your .srm save. Existing saves retain initialized character and town data, so use a new game to test those changes. Ship-specification changes may affect existing ships, while used stock can take time to refresh. Do not use emulator save states from another ROM build.'),
  ('Added ship IDs','Once you play a project, keep added ships in the same order. Removing a class renumbers later additions and can reinterpret ship IDs in that mod’s saves. Saves from other expanded-ship mods are not converted.'),
  ('A ship or good is missing','A port must meet the required industry or economy before an offer appears. Capital levels cannot be raised through investment. New-build availability is separate from used stock. Some changes require a new game or refreshed shop stock. Port Information shows the project’s starting values, not your current save.'),
  ('Controls are greyed out','Enable the corresponding Use custom switch to edit manually. Current values remain active even while manual editing is locked. Blind shuffles intentionally hide destinations; reopen the randomizer to change or restore it.'),
  ('Known limitations','Custom ship portraits do not replace map or battle icons. Shuffles exclude story companions and protagonists. Names in hard-coded story dialogue may not follow shuffled names. Experimental battle and fleet settings still need gameplay testing; passing editor checks does not establish full campaign compatibility.'),
  ('Reporting a problem','Include the editor version, the action that caused the problem, any error message and whether you started a new game. Report issues through the GitHub repository linked in About. Do not upload game ROMs.'),
 ],
 'About':[
  ('New Horizons Editor',f'Version {TOOL_VERSION}\n\nCreated and maintained by erich121'),
  ('','GitHub repository'),
  ('','Independent fan-made project. Not affiliated with Koei Tecmo.'),
  ('Acknowledgments','Ship portrait decompression is adapted from Gilmok’s UWNHRando under the MIT License. Image processing and portrait conversion use Pillow. See LICENSE, UWNHRando.LICENSE and Pillow.LICENSE included with the editor.'),
 ]}


def open_help(app):
 existing=getattr(app,'help_dialog',None)
 if existing is not None and existing.winfo_exists():existing.deiconify();existing.lift();return
 dialog=tk.Toplevel(app.root);dialog.title('New Horizons Editor — Help');dialog.geometry('960x660');dialog.minsize(620,400);dialog.transient(app.root)
 app.help_dialog=dialog
 frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Help',font=('Segoe UI',18,'bold')).pack(anchor='w',pady=(0,12))
 footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(12,0));ttk.Button(footer,text='Close',command=dialog.destroy).pack(side='right')
 body=ttk.Frame(frame);body.pack(fill='both',expand=True)
 nav=tk.Listbox(body,width=30,font=('Segoe UI',10),exportselection=False,activestyle='none',borderwidth=0,highlightthickness=0,background='#f0f4f9',foreground='#17243d',selectbackground='#d7e9ff',selectforeground='#123d73')
 nav.pack(side='left',fill='y',padx=(0,16))
 for title in SECTIONS:nav.insert('end',title)
 content=ttk.Frame(body);content.pack(side='left',fill='both',expand=True)
 text=tk.Text(content,wrap='word',font=('Segoe UI',11),background='white',foreground='#17243d',relief='flat',padx=18,pady=14,spacing3=10,width=35,highlightthickness=0)
 bar=ttk.Scrollbar(content,command=text.yview);bar.pack(side='right',fill='y');text.pack(fill='both',expand=True);text.configure(yscrollcommand=bar.set)
 text.tag_configure('title',font=('Segoe UI',17,'bold'),spacing3=18)
 text.tag_configure('heading',font=('Segoe UI',11,'bold'),spacing3=5)
 text.tag_configure('link',foreground='#0869df',underline=True)
 text.tag_bind('link','<Enter>',lambda e:text.configure(cursor='hand2'));text.tag_bind('link','<Leave>',lambda e:text.configure(cursor='xterm'))
 text.tag_bind('link','<Button-1>',lambda e:webbrowser.open(REPOSITORY))
 # Also provide a keyboard-accessible repository link.
 repository=ttk.Button(footer,text='GitHub repository',command=lambda:webbrowser.open(REPOSITORY))
 def show(event=None):
  selection=nav.curselection()
  if not selection:return
  section=list(SECTIONS)[selection[0]];text.configure(state='normal');text.delete('1.0','end');text.insert('end',section+'\n','title')
  for heading,paragraph in SECTIONS[section]:
   if heading:text.insert('end',heading+'\n','heading')
   text.insert('end',paragraph+'\n\n','link'if paragraph=='GitHub repository'else ())
  text.configure(state='disabled');text.yview_moveto(0)
  if section=='About':repository.pack(side='left')
  else:repository.pack_forget()
 nav.bind('<<ListboxSelect>>',show);nav.selection_set(0);nav.activate(0);show()
 dialog.bind('<Escape>',lambda e:dialog.destroy())
 app.help_navigation=nav;app.help_text=text;app.help_repository_button=repository
