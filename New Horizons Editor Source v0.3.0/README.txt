NEW HORIZONS SHIP EDITOR
Version 0.3.0 Beta | October 15, 2026 | Windows

A ship-data editor for the original USA SNES release of
Uncharted Waters: New Horizons.

Edit the original game's 25 ship classes and add up to five new classes.
Save your work as a project, then export a modified ROM for testing or
an IPS patch for sharing.


GETTING STARTED
---------------
1. Extract the entire release ZIP to a folder.
2. Double-click "New Horizons Ship Editor.exe".
   Python is not required.
3. Click "Open stock ROM" and select your original USA game ROM
   (.sfc, .smc, or a ZIP containing exactly one such ROM).
4. Select a ship from the list and change its values.
5. Click "Apply ship changes" or select another ship to keep the edits.
6. To return one ship to its original values, click
   "Restore selected ship".
7. Click "Save project" to save a JSON project you can edit later.
8. Click "Export ROM and IPS", choose a NEW .sfc filename, and test
   the exported game in your SNES emulator.

To reopen a project, first open the original USA ROM, then click
"Open project" and choose your saved .json file.

When the window is smaller, use the vertical/horizontal scrollbars to reach
all controls. The mouse wheel scrolls vertically; Shift + mouse wheel scrolls
horizontally. Tab brings the focused field into view. Ship and port lists
have their own scrollbars.

The editor groups settings into name/price, handling, gun/crew limits,
capacity and starting equipment. Availability has industry and port settings; Graphics contains artwork
settings. Cargo is calculated and read-only. Add/Remove and Apply/Restore stay
visible; lists and settings scroll independently.

ADDING A NEW SHIP
-----------------
1. Select an original ship and click "Add ship (up to 5)" to copy its
   starting specifications into a new, independent class.
2. On "Specifications", set its name, stats, price, total capacity,
   factory guns and factory crew spaces. Remaining capacity becomes cargo.
3. On "Graphics", choose an original visual family.
   This changes the reused graphics and description, not the current stats.
4. Select ports with Ctrl-click and set the minimum industry.
   Port rows show starting industry. Fixed capitals cannot be developed,
   so the editor rejects requirements above their starting industry.
5. Apply changes, save the project and export to a new filename.

New ships may appear occasionally in fresh used stock at eligible ports.
The existing stock cache remains; offers need not update immediately.
New ship classes are not automatically assigned to enemy fleets.
Selected ports are potential building locations; the industry requirement must
be met before the ship appears. Port rows show stock starting industry, not
the current value in your save.
The industry requirement is per ship, not a different value for every port.
Projects saved by earlier editor versions still load; new saves use project format version 6.


WHAT YOU CAN EDIT IN v0.3.0
---------------------------
All 25 original ship classes:

  - Ship name
  - Hull strength
  - Turning
  - Sailing power
  - Maximum guns
  - Minimum sailors
  - Maximum crew spaces
  - Base purchase price
  - Total capacity (cargo is calculated automatically)

Prices are entered in GOLD BARS: 1 bar = 10,000 gold.
For example, 2.5 bars = 25,000 gold.

For up to FIVE added ship classes:

  - All the specifications and base price listed above
  - Total capacity and factory guns / crew spaces
  - Factory cargo, calculated from the remaining capacity
  - Original ship used for the portrait, map/battle graphics and description
  - One or more ports where the ship can be built
  - Minimum industry, shared by all selected ports for that ship

Total capacity is editable; both cargo displays are read-only. Shipyard cargo
is total minus maximum guns and maximum crew spaces, matching the shipyard
screen. Cargo when first built is total minus starting guns and starting crew.
These can differ on stock ships. Changing capacity or allocations recalculates
cargo. Starting guns/crew stay read-only for originals and editable for additions.
Adding ships, changing original availability, importing custom portraits, or enabling Repair Safeguard or Fleet Control expands the exported game to 4 MiB. All original ship entries
remain present. Native construction time follows hull strength and industry.


ORIGINAL SHIP AVAILABILITY
--------------------------
Use Availability to choose new-build ports and minimum industry
for any original ship. Used-ship rules and original artwork stay unchanged.
Starting selections follow the stock game, including existing locked capital
offers. New unreachable capital offers are rejected. Leaving all ports
unselected removes an original ship from new-build offers. Each port supports
up to 16 types, including added ships. Restore selected ship restores stock
specifications and availability. Availability changes require a 4 MiB export.


REPAIR SAFEGUARD
----------------
On the Fixes tab, Repair Safeguard prevents excessive gold or lumber charges
when lowered stats conflict with an existing save. Original rates stay intact.
Uncheck it to keep original repair behavior. The setting is saved with projects
and recorded in exports. Older projects load with it enabled.
Enabled exports use 4 MiB even without new ships. Without additions, original availability changes or either option, exports remain 2 MiB. Save files are not modified.


FLEET CONTROL (EXPERIMENTAL)
----------------------------
On Gameplay, enable Fleet Control (Experimental) for manual mate turns and camera
focus. At the main battle menu, press Select to toggle mate automation, release
it, then press A to dismiss the confirmation. Each battle starts manual;
the flagship remains manual and enemies use their AI. Duel commands remain.
The option is off by default, saved with projects, and off for older projects.
Enabled exports use 4 MiB. Runtime mode is transient; save format is unchanged.
Full scripted-battle and duel playthrough compatibility is still being tested.


EXPORT FILES
------------
Each export creates three files with the name you choose:

  My Ships.sfc           Modified, headerless ROM for emulator testing
  My Ships.ips           IPS patch for the ORIGINAL HEADERLESS USA ROM
  My Ships.changes.json  Changes, checksums, and validation information

The exported .sfc is already patched; do not apply the IPS to it again.
Share the .ips patch, NOT the modified ROM, when distributing your changes.

The editor does not overwrite your source ROM or save-game files.
It also refuses to overwrite existing export files. When you save over
an existing JSON project, the prior project is backed up as .json.bak.
JSON projects store your edits, not the ROM itself.


SUPPORTED GAME VERSION
----------------------
This beta supports ONLY the original USA ROM revision that matches
this SHA-256 checksum after any 512-byte copier header is removed:

64bc4707f422661a66618088887e2363a5f896ea683c58984fffd96dd21ab5f0

Accepted inputs:
  - Original USA .sfc or .smc ROM
  - The same ROM with a 512-byte copier header
  - ZIP archive containing exactly one compatible .sfc or .smc ROM

Not accepted:
  - Previously patched or modified ROMs
  - Other regions or revisions
  - ZIP archives with multiple ROM files

Any accepted copier header is removed from the exported .sfc.
IPS patches must be applied to the original HEADERLESS USA ROM.


EDITING LIMITS
--------------
  Ship name         1-17 printable ASCII characters; no percent sign (%)
  Hull strength     1-100
  Turning           1-100
  Sailing power     1-100
  Maximum guns      0-150; cannot be reduced below factory-fitted guns
  Minimum sailors   1-255; cannot exceed maximum crew
  Maximum crew      10-500, in multiples of 10; cannot be reduced
                    below the factory crew allocation
  Base price        0.001-32 bars (10-320,000 gold), in 0.001-bar steps
  Shipyard cargo    Nonnegative; total minus maximum gun/crew spaces
  Factory cargo     Nonnegative; total minus factory gun/crew allocations
  Total capacity    1-2,000; must cover maximum gun and crew spaces

Additional limits for NEW ships:

  Added classes     1-5; IDs 25-29, keeping all 25 original classes
  Total capacity    1-2,000
  Factory guns      Must fit the maximum gun limit and total capacity
  Factory crew      Must fit the min/max crew limits and total capacity
  Minimum industry  0-1,000, in multiples of 10
  Ports             At least one compatible port; unreachable capital
                    requirements are rejected

Original stock values that fall outside some new-edit limits are left
intact unless you modify those fields. The editor checks new values
before saving or exporting.


LIMITATIONS AND TESTING
-----------------------
This beta adds up to five ship classes and edits existing ship data.
It does NOT:

  - Import custom map/battle sprites
  - Change factory guns or crew allocations of the original 25 ship classes
  - Assign the new ships to enemy fleets
  - Edit items, shops, stories or encounters
  - Read patched games or convert saves from other expanded-ship mods

Added classes reuse original map/battle artwork and descriptions; portraits can be replaced. The exporter installs
the engine hooks needed for the additional records, graphics and stock lists.
Other gameplay rules remain stock; separate campaign patches are not included.

Purchase prices still follow the game's original material, port,
resale, and bargaining rules. Ships already owned in a saved game may
keep their existing condition and fitted layout. Data changes can also
affect enemy ships that use the same ship-class tables.

The exporter validates data and checks that its IPS patch reconstructs
the output ROM. Release checks passed for stock-ROM edits, projects,
the packaged Windows application, added-ship records, new/used stock,
capture, normal SRAM save/load, construction timers, map/battle icon
selection, cold boot and all five actual shipyard portrait previews.

These checks use controlled fixtures. Construction pickup, normal voyages
and complete campaign compatibility have NOT been fully playtested.
Keep your original ROM and saves backed up, and test your changes in an
emulator before committing to a long playthrough.

SAVE COMPATIBILITY
------------------
Restart the emulator after changing ROMs. Use a normal in-game save or
start a new game; do not load an emulator save state from another ROM.

Once you play a project, keep the added ships in the SAME ORDER. Removing
a class renumbers later additions and can reinterpret their hull IDs in
that mod's saves. Rename or edit an existing addition instead of removing
and recreating it after playing. The editor does not convert saves made
with other expanded-ship mods.


PROJECT, LICENSE, AND DISCLAIMER
--------------------------------
Project page and downloads:
https://github.com/erich121/uncharted-waters-new-horizons-editor

Report bugs or request features:
https://github.com/erich121/uncharted-waters-new-horizons-editor/issues

Source code license: MIT (see LICENSE).

Ship portrait decompression is adapted from Gilmok's UWNHRando,
used under the MIT License. See UWNHRando.LICENSE.
https://github.com/Gilmok/UWNHRando

Image processing and portrait conversion use Pillow. See Pillow.LICENSE.

This is an unofficial fan-created tool and is not affiliated with or
endorsed by KOEI or Koei Tecmo. No game ROM is included. You must
supply your own legally obtained compatible game ROM.

CUSTOM SHIP PORTRAITS
On Graphics, Import PNG converts a picture to 64x48 pixels and the original 16-color palette. Review the exact preview and click Use portrait or Cancel. Transparent pixels use the game background color. Restore portrait resets only the artwork. Converted pictures are embedded in projects; exports with custom portraits use 4 MiB. Map/battle icons follow the original visual family.
