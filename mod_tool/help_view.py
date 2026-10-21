"""Search-free, sectioned help for the editor; no ROM required."""
import tkinter as tk
from tkinter import ttk
import webbrowser
from backend import TOOL_VERSION

REPOSITORY='https://github.com/erich121/uncharted-waters-new-horizons-editor'
SECTIONS={'Getting Started': [('Open your game',
                      'Choose Open stock ROM and select the original USA game as an .sfc, .smc or ZIP file. '
                      'The editor checks the file and remembers its location. Your original ROM stays '
                      'unchanged.'),
                     ('Edit your setup',
                      'Choose a section on the left. Turn on Use custom values to edit its fields. Valid '
                      'edits apply automatically after a short pause. Orange marks values that differ from '
                      'the original game.'),
                     ('Save your work',
                      'Save project creates a JSON file containing your settings and selected custom '
                      'content. To continue later, open the stock ROM, then choose Open project. Editing on '
                      'screen does not save the project file automatically.'),
                     ('Create a playable game',
                      'Choose Export ROM and IPS and use a new filename. Open the exported .sfc file in your '
                      'emulator. The .ips file is a patch you can share; it applies to the original USA ROM '
                      'without a copier header. The .changes.json file lists your changes.'),
                     ('Choose a starting point',
                      'Gameplay > Presets offers ready-made setups and your saved presets. Selecting one '
                      'immediately replaces the current setup. Choose Original Game for untouched game '
                      'settings. You can edit that setup and save it under a new name.')],
 'Features & Settings': [('Ships',
                          'Edit the 25 original ship types and add up to ten more. Specifications contains '
                          'stats, price, total capacity and starting equipment. Cargo is the space left '
                          'after guns and crew. Availability sets building ports and required industry. A '
                          'shipyard can offer at most 16 new ship types.'),
                         ('Ship pictures and descriptions',
                          'Ships > Graphics lets you import a portrait and edit the shipyard description. '
                          'Review the converted picture before accepting it. The portrait is stored with '
                          'your project and Library entry. Map and battle icons use the original ship '
                          'family. Descriptions allow up to 226 printable English characters, without %.'),
                         ('Library entries and collections',
                          'An entry is one saved ship, discovery or item setup. A collection groups existing '
                          'entries; Save collection does not make copies. The default groups are Stock Ships '
                          'and Stock Discoveries. Other supplied content is available under All entries.'),
                         ('Copy or delete Library content',
                          'Original entries are protected. To make your own copy, select an original and '
                          'click Duplicate below its details. The copy can be deleted even if its name is '
                          'unchanged. Delete from Library removes the selected user entry. Delete collection '
                          'removes only the grouping and keeps its entries.'),
                         ('Use and share your Library',
                          'Save to Library stores the current project version. Import and Export share '
                          '.nhlib files. Ships include stats, portraits, descriptions, ports and industry. '
                          'When loading a ship, choose whether to use its saved ports and industry. Items '
                          'keep their price and selling ports. A project keeps its own copies; later Library '
                          'edits do not change it.'),
                         ('Discoveries',
                          'The Discoveries section shows your current pool of 98 discoveries. Enable Use '
                          'custom values, then use Replace from Library to choose an alternative for the '
                          'selected location. Load all custom discoveries lets you review matching '
                          'alternatives together. Other locations stay unchanged. Restore original discovery '
                          'keeps the outgoing version in your Library.'),
                         ('Create a discovery',
                          'Use Library > Discoveries to create, edit, import or export alternatives. Each '
                          'alternative is tied to an original discovery location. PNG conversion produces a '
                          '32 x 32 picture with up to 15 visible colours. Apply saved alternatives from the '
                          'main Discoveries section. The game still selects its usual 50 discoveries and ten '
                          'treasure locations.'),
                         ('Characters, mates and captains',
                          'Characters contains the six playable starting profiles. Mates and Fleet Captains '
                          'show their portraits, nationality, attributes and skills. Enable Use custom '
                          'values to edit. Story companions can gain skills while keeping their original '
                          'ones. Character starting levels and attributes are separate settings. Use a new '
                          'game to test starting changes.'),
                         ('Port information and World editing',
                          'World > Port Information shows the current setup. Edit selling ports and '
                          'requirements in Goods or Items. Edit starting goods economy and shipbuilding '
                          'industry in Economy, for one port or a whole region. These edits update Port '
                          'Information. The map and values describe your project, not your current game '
                          'save.'),
                         ('Presets',
                          'Selecting a preset replaces all current project settings; presets do not stack. '
                          'New preset saves the whole setup with a name and optional description. Update '
                          'replaces the selected saved setup and lets you change its description. Delete '
                          'removes a preset without changing your current setup. Original Game cannot be '
                          'overwritten or deleted.'),
                         ('Preset seeds and restoring presets',
                          'The provided Full Randomizer gets a fresh four-digit seed when selected. '
                          'Randomize seed reshuffles it again. Saved custom presets keep their saved seeds. '
                          'Restore original presets brings back the supplied presets and removes your '
                          'updates to those presets. Other saved presets and the current setup stay '
                          'unchanged.'),
                         ('Randomizers',
                          'Gameplay > World contains randomizer checkboxes for mates, fleet captains, items, '
                          'goods and shipbuilding. Turn one on to open its options and preview. Click its '
                          'seed or Edit link to reopen it. A four-digit seed from 0000 to 9999 gives the '
                          'same result with the same starting settings. Shipbuilding shuffles the original '
                          '25 ship types.'),
                         ('Blind shuffle',
                          'Choose Blind shuffle to hide the results. It uses a different arrangement from a '
                          'normal shuffle with the same seed. Hidden destinations also stay hidden in the '
                          'relevant World views and changes report. Projects retain the information needed '
                          'to reproduce the setup.'),
                         ('Battles and Custom Fleets',
                          "Gameplay > Battles has Fleet Control, which lets you control your mates' ships. "
                          'Select switches automation during battle. Gameplay > World > Fleets has Custom '
                          'Fleets, where you choose flagship and escort replacements, including weaker ships. These gameplay options '
                          'are experimental; test them in your emulator.'),
                         ('Campaign',
                          'Gameplay > Campaign can extend the deadline to January 1572, set starting money '
                          'from 0 to 25 gold bars, or make new ship orders ready immediately. One gold bar '
                          'equals 10,000 gold. Starting money applies to new games. Existing ship orders '
                          'keep their saved waiting time. Normal story events and other game-over conditions '
                          'still apply.'),
                         ('Discovery options',
                          'Gameplay > World > Discoveries can use rewritten descriptions for the original '
                          'discoveries or set all discovery difficulties to 10. Rewritten descriptions keep '
                          'the original pictures and locations. Custom replacements keep their own '
                          'descriptions.'),
                         ('Locks and Restore controls',
                          'Use custom values unlocks editing. Turning it off keeps your current values '
                          'active. Restore controls return values to the original game. Right-click a '
                          'section for Restore to defaults. Reset Gameplay clears gameplay options and '
                          'active shuffles while keeping ship settings and Repair Safeguard. Restore all '
                          'settings to default resets the current project; your Library and saved files stay '
                          'unchanged.'),
                         ('Repair Safeguard',
                          'Ships > Fixes contains Repair Safeguard. It prevents certain edited ship values '
                          'from producing excessive repair charges. It starts off and is saved with your '
                          'project.'),
                         ('Reset the Library',
                          'Right-click Library and choose Delete to reset it after confirmation. This '
                          'removes your stored entries and collections, then restores the supplied content '
                          'and the two stock collections. Copies already loaded in your project stay '
                          'unchanged.')],
 'Compatibility & Troubleshooting': [('Which ROM works?',
                                      'Use the original USA SNES release. The editor accepts its supported '
                                      '512-byte copier header and removes it from exports. Translations, '
                                      'other regions and already-patched ROMs cannot be used as the source. '
                                      'No game ROM is included.'),
                                     ('Project, ROM or save file?',
                                      'A project JSON file stores editor settings. An exported .sfc file is '
                                      'the playable game. An .srm file is your in-game save. The editor does '
                                      'not rewrite your .srm file. Supply the stock ROM when opening someone '
                                      "else's project; selected custom content is included in that project."),
                                     ('Continue an existing game',
                                      'Starting character values and town settings may already be stored in '
                                      'your save. Start a new game to test those changes. Some ship changes '
                                      'affect existing ships, and used stock may take time to refresh. '
                                      'Restart the emulator after replacing a ROM. Use a normal in-game save '
                                      'rather than an emulator state made with another ROM version.'),
                                     ('Keep ship slots stable',
                                      'Once you start playing a modified game, keep added ships in the same '
                                      'order. Removing or swapping types can make a save refer to a '
                                      'different ship. Saves from other expanded-ship mods are not '
                                      'converted. Some features expand exported ROMs to 4 MiB; your emulator '
                                      'must support that size.'),
                                     ('Why is Delete grey?',
                                      'Original Library entries cannot be deleted. Click Duplicate to create '
                                      'a separate user copy, then delete that copy. Adding an original to a '
                                      'collection only groups it; it remains the protected original. Use '
                                      'Delete collection to remove a user-created grouping.'),
                                     ('Why are editing controls grey?',
                                      'Turn on Use custom values for that section. Values loaded from a '
                                      'preset still apply while editing is locked. Blind shuffles hide '
                                      'destinations on purpose; reopen the randomizer to change its '
                                      'options.'),
                                     ('Why is a ship or good missing?',
                                      'Check the required industry or goods economy. Capital levels cannot '
                                      'be raised by investment. New-build offers and used ships are separate '
                                      'lists. Some changes need a new game or refreshed stock. Port '
                                      'Information shows starting project values, not investment progress in '
                                      'your save.'),
                                     ('Saving and export problems',
                                      'Correct incomplete or invalid fields before saving or leaving the '
                                      'section. Choose a new export filename if any output file already '
                                      'exists. Project saves keep a backup of the last valid file. If '
                                      'another editor window changed the Library, select Library again to '
                                      'refresh before retrying.'),
                                     ('Known limits',
                                      'Portrait changes affect shipyard pictures, not map or battle icons. '
                                      'Some names in story dialogue are fixed. Character shuffles preserve '
                                      'protected story roles. Experimental battle settings still need '
                                      'gameplay testing; successful editor checks do not prove every story '
                                      'event works.'),
                                     ('Report a problem',
                                      'Use the GitHub repository in About. Include the editor version, what '
                                      'you clicked, the error message and whether you started a new game. A '
                                      'screenshot helps with layout problems. Use Open log folder below and '
                                      'include editor.log and native-crash.log if present. Logs may contain '
                                      'local file paths; review them before sharing. Do not upload game ROMs.')],
 'About': [('New Horizons Editor', f'Version {TOOL_VERSION}\n\nCreated and maintained by erich121'),
           ('', 'GitHub repository'),
           ('', 'Independent fan-made project. Not affiliated with Koei Tecmo.'),
           ('Acknowledgments',
            "Ship portrait decompression is adapted from Gilmok's UWNHRando under the MIT License. Picture "
            'conversion uses Pillow. See the included LICENSE, UWNHRando.LICENSE and Pillow.LICENSE files.')]}


def open_help(app):
 existing=getattr(app,'help_dialog',None)
 if existing is not None and existing.winfo_exists():existing.deiconify();existing.lift();return
 dialog=tk.Toplevel(app.root);dialog.title('New Horizons Editor — Help');dialog.geometry('960x660');dialog.minsize(620,400);dialog.transient(app.root)
 app.help_dialog=dialog
 frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
 ttk.Label(frame,text='Help',font=('Segoe UI',18,'bold')).pack(anchor='w',pady=(0,12))
 footer=ttk.Frame(frame);footer.pack(side='bottom',fill='x',pady=(12,0));ttk.Button(footer,text='Close',command=dialog.destroy).pack(side='right')
 from diagnostics import open_log_folder
 ttk.Button(footer,text='Open log folder',command=lambda:open_log_folder(dialog)).pack(side='right',padx=(0,8))
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
