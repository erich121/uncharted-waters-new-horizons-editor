NEW HORIZONS SHIP EDITOR
Version 0.1.0 Beta | October 14, 2026 | Windows

A ship-data editor for the original USA SNES release of
Uncharted Waters: New Horizons.

Change the original game's 25 ship classes, save your work as a project,
and export a modified ROM for testing or an IPS patch for sharing.


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


WHAT YOU CAN EDIT IN v0.1.0
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

Prices are entered in GOLD BARS: 1 bar = 10,000 gold.
For example, 2.5 bars = 25,000 gold.

Some other ship information is displayed for reference but cannot be
changed in this release.


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

Original stock values that fall outside some new-edit limits are left
intact unless you modify those fields. The editor checks new values
before saving or exporting.


LIMITATIONS AND TESTING
-----------------------
This is an initial beta focused on existing ship data. It does NOT:

  - Add new ship classes
  - Edit total capacity or factory compartment allocations
  - Change portraits, shipyard inventories, or industry requirements
  - Modify the game engine, encounters, or other gameplay systems

Purchase prices still follow the game's original material, port,
resale, and bargaining rules. Ships already owned in a saved game may
keep their existing condition and fitted layout. Data changes can also
affect enemy ships that use the same ship-class tables.

The exporter validates data and checks that its IPS patch reconstructs
the output ROM, but complete gameplay compatibility has NOT been
verified. Keep your original ROM and saves backed up, and test your
changes in an emulator before committing to a long playthrough.


PROJECT, LICENSE, AND DISCLAIMER
--------------------------------
Project page and downloads:
https://github.com/erich121/uncharted-waters-new-horizons-editor

Report bugs or request features:
https://github.com/erich121/uncharted-waters-new-horizons-editor/issues

Source code license: MIT (see LICENSE in the GitHub repository).

This is an unofficial fan-created tool and is not affiliated with or
endorsed by KOEI or Koei Tecmo. No game ROM is included. You must
supply your own legally obtained compatible game ROM.
