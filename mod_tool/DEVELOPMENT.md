# Development

Developer instructions for **New Horizons Ship Editor**. For installation and day-to-day use, see [README.md](README.md) and [README.txt](README.txt).

## Requirements

- Windows
- Python 3.12 or later, with Tkinter available
- Pillow (PNG decoding and portrait previews)
- PyInstaller 6 (only needed to build the Windows executable)

The editor uses Python's standard library, Tkinter, and Pillow. Install dependencies with `python -m pip install -r requirements.txt`. No game files are bundled with the source or executable.

## Run from source

From the project directory:

```powershell
python app.py
```

The editor requires the supported original USA SNES ROM when opening a game. It accepts `.sfc`, `.smc`, or a ZIP containing exactly one compatible ROM.

## Run tests

Run the unit tests:

```powershell
python -m unittest discover -s tests -v
```

ROM-backed tests require your own compatible original ROM. To include them, set the `NH_STOCK_ROM` environment variable in PowerShell:

```powershell
$env:NH_STOCK_ROM = "C:\path\to\your\New Horizons (USA).sfc"
python -m unittest discover -s tests -v
```

Run the Tkinter interface smoke test with the same environment variable set:

```powershell
python smoke_test.py
```

The ROM-backed unit tests skip when no stock ROM is available. The GUI smoke test needs a compatible ROM and a working Windows graphical session.

The editor also provides a functional check that drives its real buttons and
list clicks, using temporary project/export files and supplied file-picker
choices. Run it from source or with the packaged executable:

```powershell
python app.py --workflow-test "C:\path\to\New Horizons (USA).sfc" --report "workflow-result.json"
& ".\New Horizons Ship Editor.exe" --workflow-test "C:\path\to\New Horizons (USA).sfc" --report "workflow-result.json"
```

It checks total-capacity editing and read-only calculated cargo, port replacement/multi-selection,
Repair Safeguard on/off persistence, all five additions, save/load, ROM/IPS export, restore/remove and validation
feedback across 640x480, 1100x820, 1440x900, 1672x940, and 1920x1080 windows. A PASS report does not establish a full campaign
playthrough. Test the rebuilt executable as well as the source before release.

### Supported base ROM

The editor validates the original USA game using this **SHA-256** checksum (for the ROM data without a 512-byte copier header):

```text
64bc4707f422661a66618088887e2363a5f896ea683c58984fffd96dd21ab5f0
```

Other regions, revisions, and previously patched ROMs are not supported in v0.3.1. Do not commit or distribute copyrighted ROMs, save files, or extracted game assets.

## Build the Windows executable

Install PyInstaller 6:

```powershell
python -m pip install "pyinstaller>=6,<7"
```

Then run the included build script:

```powershell
.\build.ps1
```

For version `0.3.1`, the script creates a versioned output folder at `dist/v0.3.1/`, containing the executable, accompanying documentation and MIT LICENSE. The script refuses to overwrite an existing version folder.

Test the packaged executable on Windows before publishing it. The presence of a successful build alone does not establish gameplay compatibility.

## Release checklist

1. Update `TOOL_VERSION` in `backend.py` and the `VERSION` file to the **same version number**.
2. Update `README.md`, `README.txt`, and `CHANGELOG.md` for the release.
3. Run the unit tests and Tkinter smoke test using a compatible stock ROM.
4. Build the executable with `build.ps1`, then launch and smoke-test the packaged application.
5. Test representative edits and exports in an emulator. Verify that IPS output reproduces the intended ROM changes.
6. Package the Windows ZIP as `New Horizons Editor vVERSION.zip`, with all
   files inside `New Horizons Editor vVERSION/`. Package source as
   `New Horizons Editor Source vVERSION.zip`, inside a matching named folder.
   Include the release README, changelog, VERSION and MIT LICENSE. Keep
   documentation dates and versions consistent; use the public GitHub project
   and issue links. Generate and verify checksums for the final package.
7. Commit the source and documentation to GitHub. Create a matching tag (for example, `v0.3.1`) and a **GitHub Release**, attaching the Windows ZIP and concise release notes.
8. Keep previously published releases available and unchanged. Publish corrections under a new version number.

The repository's main README describes the latest release. Git tags preserve the source and documentation associated with each older release.

## Scope

Version 0.3.1 edits the supported original ship data and adds up to five
independent hull classes. `expansion.py` compiles the required native hooks,
tables and reset initialization from the supplied stock game; `ports.py`
contains port labels. No ROM data or extracted artwork is bundled.

Stock economy, items, shops, stories and enemy-fleet assignments are retained.
Fleet Control is an optional gameplay adjustment; Repair Safeguard is configurable. The new classes reuse original map/battle graphics; custom portraits can be imported.
Gameplay balance and full-campaign compatibility still require playtesting.

The editor is an independent fan-made tool and does not include game ROMs, extracted artwork, or private research workspace data.

## Portrait storage

Project format 6 embeds base64-encoded 1,536-byte 4bpp portraits by hull ID. Legacy formats 1-5 load with no custom portraits. Export allocates one 4,096-byte slot per hull at file offset 0x280000 + hull ID * 0x1000. The literal-only Koei stream is 1,731 bytes; it is round-trip checked before and after installation. Original hull pointers are updated in the dedicated relative portrait table at 0x2BAA4. Added hull pointers use 0x211200. No data is inserted into the middle of the ROM, and the shared palette and map/battle data remain unchanged. Removing an added ship renumbers its portrait association with its hull record.

The decompressor in portrait_codec.py is adapted from Gilmok/UWNHRando under MIT; retain UWNHRando.LICENSE in redistributions. Pillow has its own license; see Pillow.LICENSE.

## Read-only mate browser (v0.3.1 development)

`sailors.py` decodes the 120 stock records at headerless ROM offset 0x881F3 (50 bytes each). The mate browser shows zero-based IDs 69–113 and 115–119. IDs 69–78 are story companions; the remaining 40 are free agents. ID 114, Hamid Lal, is a fleet captain despite its placement among the later records. Classification is cross-checked with Dirtyferret’s first-hand Sailor List (GameFAQs FAQ 21827). Names and displayed values come from the supplied ROM. No data is copied from a published stat table.

Fields: two 13-byte names (+0, +13), eight attributes (+28..35), navigation/battle levels (+36..37), age (+42), and free-agent starting port (+45). Story companions do not get a guessed port from their 0xFF sentinel. No recruitment flags, portraits, skills, experience, or writes are exposed.

Run `python app.py --mates-test "path/to/stock.sfc" --report "mates-result.json"` to check actual button/list events, filtered IDs, navigation, preserved ship edits, save/export while browsing mates, and five window sizes. Run the same command against the compiled executable before sharing a preview. Existing ship workflow tests remain available with `--workflow-test`.

### Fleet Captains browser

The section previously labeled Enemy Captains is now Fleet Captains. It reads the same stock sailor table, selecting zero-based IDs6..68 and114 (64 records). The 50 mate entries and64 captain entries partition the114 non-protagonists. These are starting roles; some fleet captains can later become mates. No per-captain recruitment flag or guarantee is exposed. Shared read-only detail panels show the same verified attributes, levels and age. Captains' locations are labeled Fleet-dependent rather than mapping their FF location sentinel to a town. Separate searches, selections and list scroll positions are retained for all three views. Extended --mates-test coverage includes Victor Russell38, Hamid Lal114, cross-view preservation and export while viewing captains.

### Compact character layout

The shared Mates/Fleet Captains detail area uses two bounded panels: Profile (role, age, navigation/battle levels, location) and Attributes (the eight core stats). The panel group is limited to 900 pixels, moves to a vertical stack below 780 available pixels, and uses paired four-stat columns when the Attributes panel has at least 440 pixels. Labels/notes wrap to the viewport. --mates-test checks five sizes, bounded panel width, paired stats at desktop sizes, panel height, no horizontal character scrolling, and all existing navigation/persistence checks. No character or ROM data semantics changed.

### Character portraits and nationality

`character_portraits.py` reads all120 stock portraits from the supplied ROM. Faces are40x48 pixels (5x6 4bpp tiles,960 bytes), with nearest-neighbor scaling in the header. A record's +26 word selects either a compressed fixed portrait (bit15 clear) or a tile-composed face (bit15 set). Fixed streams use base0xCD55A and relative-pointer table0x2BCB7, with palette0xAAF00. Composed parts use base0xCD566 and table0x2BA8F; native C1:3007's masks, copy order and C1:F0EC offset tables are reproduced. Palettes at0x1F0AC/+32 match the appropriate composition group. No portrait art or extracted game data is bundled.

Nationality is the low nibble of record+49: Portugal, Spain, Turkey, England, Italy, Holland, Pirate. This is the stock national allegiance group, independent of current national-fleet assignment at+44. It should not be interpreted as a historical birthplace or inferred from the name.

`output/ship-editor/character-art-v0.3.1/native-validation.json` records120 controlled calls through the stock game's C1:3975 portrait dispatcher, comparing960 actual VRAM bytes and32 CGRAM palette bytes per record against editor output. Both fixed and composed paths match. The test runner and Lua fixture remain development-only; no native runtime is required by the distributed editor. Character browser checks also verify image selection, nationality, responsive image sizes, navigation and preserved ship export behavior.

## Character edits and free-agent shuffle (v0.3.1)

Project schema7 adds character_edits (id/field/value entries for eight attributes only, IDs6..119) and free_agent_shuffle (enabled/seed/blind). Formats1..6 load with both features inactive. Character records remain50 bytes. Attribute bytes+28..35 accept integers0..100; names, IDs, flags, skills, portraits, nationality and levels stay protected. Edits are normalized against the stock ROM and validated atomically. Build changes only these bytes and free-agent port byte+45, followed by normal checksum handling. Other ship features compose through the existing exporter.

character_mods.py uses domain-separated SHA256 ordering of the fixed40 stock port slots. Version1 accepts exactly four ASCII digits, including leading zeroes. Seed and mode reproduce the mapping independently of Python random-module versions. Normal and blind have separate hash domains; a collision fallback guarantees distinct modes. Random seed uses OS randomness to choose 0000–9999. Projects persist the seed and mode, not arbitrary port overrides. Blind hides locations in the dialog and profiles; its export report omits destinations. This is discovery concealment, not encryption: a project contains the reproducible seed.

Real Tk --mates-test coverage now exercises attribute entry/apply/restore/rejection, preview, blind hiding, shuffle apply/restore, project reopen and exact exports. tests/test_character_mods.py verifies bounded writes, protected records, all114 editable sailors/8 fields, deterministic slot counts, separate normal/blind permutations, backward compatibility and atomic validation. tools/check_editor_character_changes.py cold-boots plain and five-added-ship/Fleet-Control exports and compares960 native initialized attributes plus40 starting ports per case. This is initialization verification, not a full recruitment or campaign playthrough.


## Fleet Difficulty (v0.3.1, project schema8)

Optional gameplay.fleet_difficulty defaults off. Versions1–7 load it off; schema8 validates the gameplay object and boolean atomically. Shared defaults and original ship stats are unchanged.

mod_tool/fleet_difficulty.py installs guarded template-selection hooks at09199F/091B6F (native heavy refill categories), with helper21A000. Expected native bytes and empty helper space are required. Only tier2, nation0..5, position0, low-flag fleets other than the player qualify. Template50 becomes55 (Galleon to Barge),51 becomes60 (Xebec to Venetian Galeass). All other choices stay native. Target hull durability, fitted guns and crew must each be at least the source values in the project, or that mapping is omitted. Turning/power differences are intentional hull tradeoffs.

No private templates, extra persistent RAM, reset wrappers, stack reservations, or save-format changes are introduced. Native initializer supplies actual hull/sailing stats, fitted guns and actual crew. Existing positions, light pools, pirates and separate script generation paths are unchanged. Ordinary refill can affect a story-involved captain if its fleet meets the guards; full story safety is not established. This is why the option remains experimental.

Validation: tests/test_fleet_difficulty.py covers identity, byte scope, schema7 migration, invalid settings, conflicts, edited-hull downgrade guards, IPS and composition with0/1/5 additions and other options. tools/check_editor_fleet_difficulty.py exercises native helper guards, full refill, stock capture and SRAM-copy save/load, plus camera/input/status regression on the combined export. Snapshot fixtures and controlled RNG do not replace real campaign playtesting. UI workflow checks use hit-tested checkbox clicks at640x480 and project/export/reopen/disable steps. Artifact evidence is under output/ship-editor/fleet-difficulty-v0.3.1.


## Configurable national fleets (v0.3.1, schema9)

Fleet Difficulty now stores gameplay.fleet_rules as six nations × three positions × four source hulls (Carrack9/Galleon10/Xebec11/Venetian Galeass20). -1 is Keep stock; other values are validated existing hull IDs0..29. Stock and stronger-flagship presets are explicit. Schema8 migrates the previous boolean with the old preset; schemas1–7 stay disabled. Invalid rules are rejected before project mutation. Removing an added model clears its references and shifts other references with model IDs.

The same two native heavy-pool hooks remain; light fleets are unchanged. Helper21A000 now computes X=12*nation+4*position+sourceIndex, reads a72-byte template table21A200 and preserves native A8/Y7 return behavior. Guard: top tier2, nation<6, slot<3, no high fleet flags, not player. Table entries255 preserve native choices; other entries are native templates40..69. Ship specs and fitted defaults are never patched by this option. Compile-time resolve skips target hulls with lower hull strength, factory guns or factory crew. Added models use the existing compiler's65..69 default templates, with no new private templates or RAM.

Native tests tools/check_editor_nation_fleets.py exercise default and distinct six-nation/three-role configurations, all five custom models through complete refills, capture/SRAM-copy at both custom-ID endpoints, plus camera/input/status. UI workflow checks edit nation/role choices, inspect skip feedback, cancel changes, reset presets and reach all selectors at640x480. Neither test suite proves full scripted battles or campaign balance. Evidence: output/ship-editor/nation-fleets-v0.3.1.


Fleet presets now include Stock, Stronger flagships, Regional variety and Stronger fleets. All use original hulls only and retain native Venetian Galeass choices. Regional adds an English/Dutch Barge escort, Ottoman galley support and Italian Xebec/Frigate support for native Carrack choices; Iberian escorts stay stock. Stronger fleets upgrades flagship and one escort, leaving the second escort stock. Descriptions update before Load preset; Load resets the draft for all nations, Apply commits, Cancel preserves the project. The dialog reserves a footer before its scrolling body, wraps header text, and exposes all selectors at640x480. Presets are tested through full native refills, including native lighter/pirate preservation.


Preset UI correction: selecting a preset now immediately replaces the draft for all six nations; the redundant Load preset button is removed. Apply commits and Cancel discards. Initial and manually edited state is matched against presets, otherwise labeled Custom settings. Regional description explicitly notes Portugal/Spain match the flagship-only preset. No native rules, template bytes or guard behavior changed. Targeted UI checks verified immediate choices, cancel, apply/reopen, custom detection and Stock selection; full packaged workflow checks cover actual controls. Evidence: output/ship-editor/nation-fleets-preset-fix-v0.3.1.


The Gameplay master checkbox is now labeled Use custom fleet difficulty. It enables the existing saved nation rules/preset; it is not an additional difficulty patch. Experimental status remains in the adjacent description. No backend, project or ROM changes.


Plain-language UI revision: shorter Gameplay descriptions; Original ship / Flagship (ship1) / Second ship / Third ship columns; No change and Apply settings labels. Fleet preview shows choices for ship types actually used by the selected nation’s top-tier pools, with direct guns/crew/hull values and plain skip explanations. Preset rules and generated ROM remain unchanged.


## Fourth ship and disabled settings (v0.3.1, schema10)

Nation rules now have four positions. ROM table21A200 is96 bytes; helper index is16*nation+4*position+sourceIndex. Position>=4 remains native. Schema9 is validated as three positions then gains a No change fourth row; no older saved choices are overwritten. Schema8 and earlier retain prior migration behavior. Presets: Stock and flagship-only retain their scope. Regional moves English/Dutch Barge support and Ottoman galeass support to fourth position, retains mixed Italian second/third choices and adds Italian Carrack-to-Galleon fourth choices. Stronger fleets upgrades flagship, second and fourth; third remains native.

Use custom fleet difficulty now controls Configure nations state and description colours immediately. Both opener and dialog entry refuse access while disabled or no ROM is loaded. Off retains rules. Show/open-project synchronizes the state. Tests cover fourth selection/persistence, disabled opener, schema9 migration,96-byte table layout and native fourth-versus-fifth boundary. Evidence: output/ship-editor/four-ship-fleets-v0.3.1.


## Starting skills (v0.3.1, schema11)

Sailor record+48 low bits:01 Negotiation,02 Accounting,04 Gunnery,08 Cartography,10 Celestial Navigation. Native profile C5:15E8 shifts10 right across the five names stored at CB:0A75..0AA9. Teacher writes OR08 at C8:6D1F, OR10 at C8:77FC and OR04 at C8:7B07. No record+49 nationality or reserved upper bits are modified.

Native teaching gates are separate from preassigned skills. Cartography uses attribute offsets1,2,3 from C8:FE54, each>=75 through C1:FE8E. Celestial uses offsets1,2,3 at FE6D and minimum70/80/70 at FE70. Gunnery uses offsets0,2,4 at FE73 with75/65/80 at FE76. C1:FEAE/FE8E include equality. Accounting/Negotiation training requirements for this USA version are not established here. The editor does not force thresholds or attribute changes. No guidance UI is exposed, per user request.

character_edits now accepts field skills, integer0..31. All non-protagonist mate/captain records are editable; companions69..78 must retain every stock skill bit. Added companion bits may be removed/reset while stock bits stay locked. Apply preserves upper three bits and changes only record+48. Schema11 signals the expanded field set; earlier projects load without skill overrides. Restore character clears selected attribute and skill overrides. Stock names, portraits and recruitment flags are untouched.

Validation: all32 skill combinations against each companion’s add-only policy, bounded byte writes, upper-bit preservation, invalid input atomicity, project/IPS, original bit-name examples. Native cold initialization compares all120 skill bytes in plain and five-added-ship/Fleet-Control/difficulty ROMs. Native CA:1ACC Gunnery predicate is tested across all32 masks with zero attributes, confirming the bit is sufficient for that NPC predicate. This does not prove every skill effect or all story events. Source and Windows character tests exercise companion locked controls, add/remove on free agents/captains, restore, save/reopen/export and five window sizes. Evidence: output/ship-editor/skills-v0.3.1.


## Skills card appearance correction

The skills panel incorrectly placed controls directly on the header-bearing Surface background. It now uses a separate CardHeader and solid white Card body, matching the existing character cards. Checkboxes retain a white background when active or disabled. Character UI checks assert this structure and continue to cover locked companion skills, editing, persistence and responsive scrolling. Evidence: output/ship-editor/skills-card-v0.3.1.


## Compact skills placement

Skills now shares the bounded character-card grid: below Attributes in the right column on wide windows, below the other cards when narrow. The card uses the same Surface/CardHeader/Card styles and padding as Profile and Attributes. Five checkboxes use two columns when at least440px is available, one otherwise. The note wraps within the card. Tests check equal Skills/Attributes widths, wide placement, compact height, responsive scrolling and existing skill behavior at five window sizes. Evidence: output/ship-editor/compact-skills-v0.3.1.


Selector appearance: the shared Ships/Mates/Fleet Captains Listbox now sets activestyle=none to suppress the Windows active-row underline. Selection colours and keyboard bindings are unchanged. Preview evidence: output/ship-editor/selector-style-v0.3.1.


## Gameplay mate shuffle entry

Gameplay now includes Mate starting ports with the existing seeded free-agent shuffle dialog. Both Mates and Gameplay share the same project setting and on/off/blind summary. Applying from Ships refreshes status without calling show_mate or modifying the ship list selection. Both openers are disabled without a ROM. Character workflow now exercises the Gameplay opener, seed persistence, applying/restoring from Ships and both summaries, alongside the underline-free shared selector. Evidence: output/ship-editor/gameplay-shuffle-v0.3.1.


## Gameplay and World sections (internal0.3.1)

Gameplay is now a standalone sidebar section above World and Ships; Ships retains four tabs. Gameplay has its own scroll canvas and Apply action. Browser state remains independent and hidden while viewing global settings. World has a separate searchable130-port list, original economy/industry/specialty/capital data for100 trading towns, and explicit not-applicable values for30 supply ports. It also lists project new-build offers and industry gates (not used-stock guarantees). No world data is editable.

World map is decoded on demand from the supplied ROM using portrait_codec.Decoder:4,050 compressed12x12 blocks expanded through ROM tile quads to2160x1080. World/port code is self-contained in mod_tool/rom_map.py and world.py; no ROM assets are bundled. Verified grid SHA2560e26a098169182a5c0cfa013e91f5e611dd4b3026f66e973e5d42a83f9ec680f. Original130 port positions/names come from22-byte records at577875-512. The viewer colours decoded terrain for clarity; it does not claim to recreate the native map-screen artwork. Selecting any city or supply port draws a marker using original grid coordinates. Resizing retains aspect ratio and marker alignment.

Tests cover exact decoded grid hash, port bounds/counts, native starting values, supply-port absence of economic records, real sidebar navigation, search and selection, map marker updates and five window sizes. Existing Windows ship/fleet and character workflows remain required. Evidence: output/ship-editor/sections-v0.3.1.


## Compact Gameplay tabs and World regions

Gameplay now groups its existing options into Battles, Fleets and Mates tabs, each with its own scroll surface. The shared Apply gameplay changes action remains visible. Text wraps to the available tab width. World map display is capped at420x210 content pixels, half the former840x420 maximum dimensions, and shrinks further on narrow windows.

Region names are read from the13 native string pointers at742782-512. Trading towns use record+33 market-region indices, matching Iberia/Northern Europe/The Mediterranean/etc. This is a trade-region grouping, not an inferred geographic reassignment. The30 supply ports have no such records and are grouped separately. The region chooser filters the left list and marks every region member, independently of text search; the selected port keeps its distinct red marker. All regions returns the full list and single selected-port map view. Region membership is read-only.

Tests check the13-group partition and all130 memberships, Northern Europe15ports, supply30ports, region markers remaining visible during text search, compact map bounds and existing workflows. Evidence: output/ship-editor/regions-v0.3.1.

Windows test harness placement corrected: native pointer checks now raise the tested window before hit testing, and fleet modal checks run inside desktop bounds. Previously off-screen or covered test windows caused false clipping failures. No pointer assertions were bypassed. Gameplay categories remain tabs on the right after the user withdrew the sidebar-placement suggestion.

Gameplay additionally reserves a fourth World tab, disabled until an actual world-changing feature is implemented. Existing World sidebar remains the active port/map browser. No trade shuffle or other world edit is enabled by this UI addition.


## Read-only discovery browser

World now switches between Ports and Discoveries using the left selector. Each mode keeps its selected record and search. Discoveries hides the trade-region chooser, port economic card and shipyard offers. Only its selected discovery marker is drawn; port/region dots are suppressed. Returning to Ports restores the region and its markers.

Stock USA records: position table584459-512,7-byte stride; name pointer table980297-512,99 three-byte entries. There are98 nonempty named entries0..97; the final stock slot98 has a blank name and zero coordinates and is not listed. Names strip native ESC+command layout pairs. Stonehenge=(168,270), Moai=(1574,888). Every displayed location is bounds checked against2160x1080.

The catalogue is not a save-availability list. Native C5:022A resolves7-byte runtime records at WRAM8D14. C9:6026 checks flags+6 bit80; C9:603F also checks40, which C9:606A sets after its discovery condition succeeds. The preserved Ernst gameplay fixture has50 records with bit80 clear and48 set, with all bit40 clear. This supports the user’s50-active observation for that fixture; new-game sampling/selection has not been fully traced. No save is read by the browser and it makes no per-playthrough availability claim.

Validation: five world/discovery unit tests; focused native Windows World workflow covering mode switching, real list-row pointer hits, both endpoint discoveries, single-marker rendering, restored port-region markers, remembered mode state, five window sizes, unchanged project and identical ROM export. Evidence: output/ship-editor/discoveries-v0.3.1.


### Native discovery pictures, descriptions and requirements

Description pointer table0xEBE62; category label pointers0xB0CF7, selected using native record+6 low3bits. Native display C9:D789 calls C1:3D7C with the discovery id. C1:3D7C..3E4C maps graphic index25+ROM[0x9FB49+id] and palette ROM[0x9FBAD+id]+1. The shared graphics origin is the three-byte pointer at0xCD556; relative pointers at0x2BAA4. Each discovery picture is32x32 SNES4bpp,512bytes. Palette source0xAA8E0+32*palette. Picture_data caches98 decodes; UI shows an exact nearest-neighbour128x128 preview. Never substitute approximate art.

Difficulty is record+5. Native reveal comparison C9:DB72..DBE3 calculates score=(floor(Intuition*7/20)+floor(Luck*3/20)+village_friendship)&255 and requires score strictly greater than difficulty, via C1:FE12. Protagonist attributes read at+31 and+35 from pointer7E:E808; village friendship at7E:FDE9. No fixed Navigation Level is used in this comparison. UI shows category, original description, difficulty and required score=difficulty+1, with plain explanation. Other encounter conditions (enabled discovery, sailors, prior discovery flags, hazards) remain separate; the score alone is not a guarantee of all encounter eligibility.

Native test tools/check_editor_discovery_native.py +tools/mesen-agent/test_discovery_browser.lua calls the original renderer for all98 pictures and checks exact512-byte VRAM content plus32-byte CGRAM palette. It also executes490 reveal-comparison cases around difficulty boundaries and with mixed attributes. All passed. Test ROM/SRAM is private and not packaged. Native evidence: output/ship-editor/discoveries-v0.3.1/native/results.json. This validates dispatch/upload and the comparison, not complete village encounters.

## World Goods preview — 2026-10-16

World now has Ports / Discoveries / Goods with independent search and selection. Goods combines all 46 native commodity names with regional market offers and town specialties. Required economy and starting availability are shown per source; a checkbox filters locked sources. No project or ROM changes are made. Map and details sit beside each other when wide, stack when narrow; the map remains compact. All group markers are red, and a single source keeps the target. Selecting a selling-port row focuses its target.

Focused Windows checks exercise all three views at 640×480 through 1920×1080, search/selection persistence, source filtering, marker colours, source-row selection, and unchanged exports. Three new source-data tests cover every native offer and economy boundaries. Mesen Lua directly checks 439 native comparison cases across all 13 regional markets and 67 specialty towns; this does not test live stock quantities or full transactions. Reproducible tools: tools/check_editor_goods_native.py and tools/mesen-agent/test_goods_browser.lua.

## Port unlock lists — 2026-10-16

World Ports now puts port information beneath the map, with two compact requirement lists on the right: Goods sold (economy) and Ships built (industry). Lists sort by requirement then name, insert one blue starting-value divider after all ready entries, and label each entry Ready or Locked. Fixed capitals are explicitly marked. Goods reuse verified regional/specialty catalogue sources; ships use project.all_offers() so original availability edits and additive ships are reflected. Supply ports hide both lists. No ROM, save, or project mutations occur during browsing.

Extended World checks compare both lists for all130 ports against catalogue/project sources, test divider placement, supply-port hiding, original ship edits and added-ship refresh, then exercise all World views at five window sizes and confirm browsing leaves project/export unchanged. Native gate code is unchanged; previous439 Mesen economy comparison cases remain applicable.

## World Items — 2026-10-16

Added a fourth World mode, Items, with independent search/selection, original picture and description, selling-port rows, hours, red multi-port markers and a single-source target. Catalogue includes the61 item IDs actually stocked in towns, excluding unstocked/placeholder/quest-only records. Ports also have an Items sold list with regular shop hours and04:00–05:59 early offers. No economy/industry requirement is invented for equipment shops.

Three focused data tests passed. Mesen direct-routine tests compare all61 decoded item pictures and palettes to native VRAM/CGRAM and all2400 town/hour shop lists to source slots. Windows World checks retain port/goods/discovery coverage, add Items pictures, descriptions, sources, hours and all-port item lists, with five tested window sizes. Native tests do not simulate payment or a full shop UI. Reproducible scripts: tools/check_editor_items_native.py and tools/mesen-agent/test_items_browser.lua.

## World scrolling correction — 2026-10-16

Reproduced a mouse-wheel dead area over the uncovered ScrollableWindow viewport: eight wheel events over a card advanced yview, but the same events over the viewport Canvas left yview at0. The handler only accepted content descendants, excluding the viewport and its scrollbars. It now accepts those surfaces as well, with exact descendant path boundaries. Listbox/Combobox exclusions remain. The shared fix also covers other editor scrolling panels.

Extended World regression checks send wheel events over the outer viewport, a goods card canvas and the scrollbar, reach the end of overflowing port pages, verify Items sold is visible, and scroll upward again. Fully fitting pages correctly need no scrolling. Existing five-size World and unchanged-export checks remain.

The first compiled regression run additionally exposed stale World scroll geometry after switching modes: yview reported(0,1) while Items sold extended below the viewport. This was a real second bug, not just a wheel exclusion. World now opts into a natural embedded-frame height, allowing requested content-height changes to trigger Configure and refresh the scroll region. Other editor panels retain their fixed minimum-height behaviour. Focus visibility uses the scroll-region height so the natural-height canvas window's zero/automatic height is handled correctly. Corrected source tests passed all five sizes, including actual downward/upward scrolling and item visibility.

Corrected packaged Windows EXE passed the full World workflow with viewport/card/scrollbar wheel checks and Items sold reachability at all five sizes. Tested binary copied with matching SHA256 to Testing/v0.3.1-world-scroll; the failed earlier test build was not delivered.

## v0.4.0 Beta — compact and consistent World layout

Internal version advanced from0.3.1 to0.4.0 Beta as requested. Wide Ports view uses map/port information at left, goods and items in the middle, and ships at right. Compact rows preserve labels and requirement dividers, smaller windows retain natural-height scrolling. The map uses the same dimensions/anchor and reserved controls/caption height across all four World modes at each window size.

Specialty strings now use the same control-aware decoder and hyphenation cleanup as commodity names. All100 trading-port specialties are tested against the Goods catalogue.

Clock correction:7E:A05D is a HALF-HOUR tick, not an hour. Native shop slots4/5 mean02:00/02:30, closing before03:00. The earlier04:00–05:59 labels and claims were wrong. Native clock text at CD:07AE..07E5 uses tick/2 for hours and(tick%2)*30 for minutes. Source labels now show02:00–02:59. Mesen shop cases expanded to48 ticks×100 towns=4800, all passed, along with61 exact native pictures/palettes. The earlier2400 cases covered only half the day, despite being described as24 hours. No game clock/stock logic was changed.

The native specialty is shown both in Port information and with a star in the Goods sold list; the header explains the star. World checks compare the marked row to the specialty string for every trading port.

Packaged v0.4.0 Beta Preview passed the full World workflow, every stock trading-port layout at1440×900/1672×940/1920×1080, stable map position/size across all four views, smaller-window scrolling, all-port specialty markers and unchanged exports. Copied tested EXE with matching SHA256 to Testing/v0.4.0-world-layout.

## v0.4.0 Beta — card edge artifact

User confirmed short horizontal marks at the left/right edges of white cards. The rounded Surface image included an explicit full-width separator at template row44, leaving visible stubs outside the inset header/body widgets. Removed that stroke; retained background fills, rounding, border and identical template dimensions/nine-slice geometry. Pixel inspection confirms neither side contains the darker stroke. This changes only card painting, not layout or ROM data.

## v0.4.0 Beta — Ships density and automatic edits

Scope refined by user to Ships only; Mates, Fleet Captains, World and Gameplay layouts retained. Ship Specifications uses three columns at wide sizes so all six cards fit; two/one columns remain below the breakpoint. Numeric fields stay bounded, hints span the card on three-column layouts, excessive identity-card padding is removed. Availability and Graphics put related cards side by side in wide windows, stack when narrow. A geometry stacking issue caught by real pointer tests was fixed by lifting panels above their layout holders; deferred resize corrects requested-size updates on reflow.

Valid ship field/availability edits, character attributes/skills and gameplay checkboxes update the in-memory project automatically after350ms. Invalid/incomplete values retain last-valid project data and show a status message without popup interruptions. Programmatic record loads suspend observers. Apply controls are hidden; Restore remains. Fleet customization retains its independent draft and Apply settings/Cancel, as requested. Portrait preview and seeded shuffle remain explicit operations. Saving/exporting remain explicit. Existing record markers refresh automatically.

Gameplay sidebar now lists enabled options and counts of changed ships, additions, custom portraits and edited characters, beneath section navigation. Focused automatic-edit checks passed ship/character dirty markers, restore, incomplete input, gameplay toggle persistence and summary updates. Existing ship workflow passes export/IPS reconstruction and custom fleet apply/cancel. Character workflow also exercises automatic attribute/skill edits.

Final packaged Windows EXE passed --auto-test and --workflow-test, including all six ship cards at large sizes, real portrait/port button clicks, automatic edits/markers/restore, custom fleet draft Apply/Cancel, five sizes and export/IPS reconstruction. Source --mates-test passed character/skill/shuffle/export regression checks. Copied tested EXE with matching SHA256 to Testing/v0.4.0-ships-and-auto-edit.

## v0.4.0 Beta — Undo, reset sections and changed-value colour

Bounded 100-state in-memory history snapshots only mutable project data (ships, availability, portraits, character edits, shuffle, fixes and fleet choices), never source ROM bytes. update_status records distinct committed states; new ROM objects start a new history. Undo flushes a valid pending auto-edit, cancels debounce, restores a prior snapshot and reloads the current view without creating a new history step. Existing selected-record Restore controls remain.

Right-click section menus offer confirmed Reset section; World is disabled. Ship reset restores original specifications/offers/portraits, removes added classes, and clears only fleet references to those removed IDs. Character resets affect the corresponding starting-role IDs only. Gameplay has an additional Reset all gameplay button; it disables Fleet Control/custom fleets/shuffle and restores preset fleet choices, preserving ship data, Repair Safeguard and character edits. Every reset is undoable. Orange ttk field/check styles and port-list foreground compare against original ROM values; added classes are highlighted as new. Global footer supplies Undo and a colour legend.

User renamed fleet difficulty to Custom Fleets throughout UI/help/docs/errors, with Use custom fleets on the checkbox. Existing project keys and ROM behavior remain compatible.

Final packaged Windows --auto-test PASS: automatic edits, invalid input preservation, stock/edited styles, Undo, cancelled reset, each section reset isolation and full snapshot recovery, visible gameplay reset, context menu command wiring, read-only World and minimum-window Undo visibility. Source --workflow-test PASS: five sizes, actual exposed pointer targets, five additions, ports/portraits, custom fleet drafts, project round trips and ROM/IPS verification. Reports in output/ship-editor/undo-section-reset.

## v0.4.0 Beta — brighter orange markers; Undo removed

Supersedes the Undo feature described above: user requested removal, so the button, snapshot history and Undo logic are removed. Existing record Restore and confirmed section resets remain. Gameplay button is now Reset Gameplay.

Changed value colour is #ef7800. Edited/new ship rows and edited mate/captain rows use orange text with light orange backgrounds; selected edited rows retain orange text. Section buttons/icons show orange for changed contents, refreshing after edit, Restore/reset, navigation and density changes. World stays unmarked/read-only. Ship section includes Repair Safeguard because it differs from stock; this option is enabled by default in the editor.

Expanded automatic checks cover orange row and selection colours, ship/mate section styles, marker clearing after Restore, independent section resets and cancellation. Final Windows preview and source checks pass. Reports and build under output/ship-editor/bright-orange.

User subsequently requested a global Restore all settings to default control at the bottom of Gameplay’s Active changes column. The sidebar area expands vertically to anchor this button at its bottom. It has a separate explicit confirmation describing removed ships/portraits/character edits and resets every mutable project setting to editor defaults (Repair Safeguard enabled). It cancels pending edit timers before resetting, retains source/project file identity and never writes saved files. Reset Gameplay and record/section Restore controls remain independent. Automatic checks cover cancel/confirm and exact default data.

Legend wording is now Orange = changed from default. Repair Safeguard highlighting compares against its enabled editor default, so a freshly loaded/default-reset project has no orange section markers. Ship and character data continue to compare against original ROM values.

## v0.4.0 Beta — character reset persistence, keyboard list selection and default repair option

Reproduced stale hidden character data after restoring all defaults: clearing character_edits alone was insufficient because data_type retains the previous character browser while section is Gameplay. reload_project_view refreshed character variables only when the character section was visible; switching back called commit_character on stale variables and recreated the edit. Fix: always refresh the retained character browser after resets and allow commit_character only when its actual section is Mates/Fleet Captains. Regression edits both visible character categories, resets from Gameplay, navigates back, checks stock fields/cleared asterisks/normal section colour, then commits and checks manifest and built-ROM sailor bytes. The pre-fix case failed on recreated character_edits; the fixed source case passes.

Repeated Tk Down events reproduced selection sticking at row 2: refresh_list deletes/repopulates rows and restored selection but not Tk's active/anchor indices. select_browser_row now restores selection, active row and anchor together everywhere the editor restores a browser selection. Actual KeyPress/KeyRelease tests verify repeated Down/Up steps and matching detail records for Ships/Mates/Fleet Captains. Pre-fix test failed on second Down; fixed source passes.

Per user, fresh-project Repair Safeguard is now Off, as are the initial checkbox and global reset value. Changed-section and field comparisons use Off as the default, and the clean-project replacement check matches it. Explicit saved project settings still load unchanged; legacy v1/v2 import behavior retained. A completely default project builds byte-for-byte stock. Repair unit tests and automatic UI regressions exercise these paths; full Windows workflow explicitly turns the option on before its existing on/off/export checks.

Final packaged Windows --auto-test and --workflow-test passed. Confirmed reset/navigate does not restore character edits, cleared section markers, real repeated key events, Repair Safeguard default Off, default stock build equality, project persistence and all existing editing/export checks. Five repair unit tests pass, including explicit default-Off assertion. Delivered hash-verified preview under Testing/v0.4.0-reset-and-navigation.

## v0.4.0 Beta — editable Goods; Port Information hub

World selector now displays Port Information while preserving internal Ports identifiers. Goods supports adding/removing trading ports, automatic economy-gate edits, selected-good restore, orange markers and World/global reset. Port Information is read-only and consumes the same current-project catalogue, updating specialty, goods requirements, readiness and map sources. Captured debounce identities prevent edits from moving to another good/port; synchronizing Treeview and port-combo selection fixes queued selection events retargeting later edits. A fixed two-line intro keeps the map position identical across World views; full existing World workflow passes all stock ports at wide sizes and five responsive sizes.

trade_goods.py stores validated per-port offer overrides, preserving stock kinds/base prices for existing offers. Additions choose a positive median stock base-price reference, never overwrite an existing offer, and enforce nine regular slots plus one specialty. Shared regional valuations and region IDs remain native. Export duplicates each port’s native 128-byte market record into reserved expansion space and patches only the player market setup pointer. Unedited cloned records remain byte-identical, including unused bytes. Changed specialties alone alter town ROM records; existing SRAM is not rewritten. New game required for specialty changes; normal market quantities/prices/transactions/save cycles are not yet fully independently tested.

Project format12 adds goods_edits with atomic validation and older1–11 imports defaulting to none. All-features compilation passes (five hulls, portrait, character, fleet control, custom fleets and repair with goods). Legacy test fixtures now omit goods_edits when emulating earlier schemas; availability delta test allows the stock-to-expanded ROM size header change with Repair Safeguard default Off.

Native Mesen checks:100 per-port market pointers,1827 economy boundary cases,300 actual market-list constructions (all100 towns at economy0/500/1000) pass. Goods GUI test uses actual pointer-hit controls for add/remove/restore, automatic gate changes, pending-edit identity, port hub refresh, stock-capacity rejection, project persistence, exact IPS reconstruction and global reset. Reports/tools under output/ship-editor/goods-edit and tools/check_editor_goods_edit.py.

Final validation:70 relevant unit tests (39 ship,31 character/fleet/goods), full World workflow and all-stock-port layouts at five sizes,100 native pointers/1827 economy gates/300 market-list constructions, packaged Windows Goods checks and automatic-edit/reset/keyboard checks passed. Final Goods check additionally verifies only the modified good is orange in Port Information. Copied final hash-verified preview into Testing/v0.4.0-goods-editor; prior builds retained. Full buy/sell/save cycles remain a stated testing limitation.

## v0.4.0 Beta — World Economy view

New World Economy view lists100 trading ports (no supply-port records) with regional filtering and map grouping. Automatic individual Trade economy/Shipbuilding industry edits use native1–1000 words. Region batch operations Set to/Add/Scale % preview current/after values; blank fields preserve a statistic, search never changes the targeted region, and commits are atomic. Whole-number scaling rounds half-up and clamps1–1000. Restore port/region preserve other data; World/global resets also clear economy edits.

Model economy.py validates/normalizes only differences from stock, provides projected town data and writes only town+0 economy/+4 industry words. Economy-only ROMs stay2MiB. Project schema13 adds economy_edits, parses atomically before dependent ship offer validation, and supports1–12 without economy overrides. Port Information values/dividers/unlocks, Goods At start flags, and ship Availability port levels all use projected current-project stats. Neither source ROM nor saved-town SRAM is modified in place. Capitals remain fixed under native investment rules. Existing offer assignments survive level reductions/restoration even if locked; validation of new assignments still uses current project levels. Additive compiler keeps its normal capital guard by default; the project compiler permits retained locked offers.

Single-port debounce captures its port identity and flushes before navigation/save/export; reset cancels it. World pick captures the requested selection before flushing, so refresh cannot retarget the click. Startup hidden ship notebook changes now resize their own canvas without overwriting the active World scroll reference; actual pointer-hit tests exposed that issue. Economy cards wrap and shrink for small windows; Port Information and other World layouts retain their existing map position.

Validation:71 relevant model/unit tests plus the extended economy dependency/reset case passed; full existing World workflow and all stock port layouts passed five sizes. Mesen native checks load the edited exported town records and verify100 trade economy gates plus100 actual shipyard industry unlock menus with UI stubs. Not a full new-game playthrough or save reload. Economy GUI checks cover actual exposed pointer controls, automatic edits/invalid input, read-only hub, both unlock lines, group preview/search scope, isolation/blank values, restore/cancel, pending identity, global reset, project/ROM/IPS roundtrip and small windows.

Capital dependency verification: new assignments are constrained by projected current industry even if only trade economy was edited. Existing assignments are grandfathered when levels are lowered or region economics restored, preventing reset from leaving an invalid project; the native gate still hides locked offers. Added regression confirms an unchanged locked ship can be retained while raising its requirement beyond current capital industry is rejected.

Final Windows Economy workflow passed on the delivered executable, including no horizontal overflow and hit-tested batch buttons at640×480/1100×820/1672×940. Windows Goods and automatic-edit/reset/navigation checks passed on the preceding build; final code change tightens new capital-assignment validation and is covered by the extended economy unit tests. Final hash-verified executable and validation receipts copied to Testing/v0.4.0-port-economy; prior previews preserved.

Economy presentation follow-up: rename Trade economy to Goods economy in both field groups; regional preview headers are Goods and Shipbuilding, preserving both After columns. Center all preview values and headings. Rebalance column widths so the longer Shipbuilding title remains readable at the existing minimum window width. Data identifiers and calculations unchanged.


2026-10-16: Custom editing gates (format14). Economy, goods, mates and captains have independent default-off flags. All mutation controls and handler paths are guarded. Disabled drafts persist but are filtered from exported patches; goods/economy information hub reflects only enabled changes. Existing formats infer enable flags from edits. Pending typed changes are flushed before disabling. Companion original skill locks retained. Regional headers centered and renamed Goods/Shipbuilding; single-port field renamed Goods economy. Added custom_controls_checks UI/export/persistence/reset checks. 71 regression unit tests and native economy/shipyard/market checks pass. Packaged UI verification recorded separately.
Packaged Windows custom-controls, goods and economy GUI checks all PASS. Includes real pointer-hit checks on goods/economy editing buttons and responsive economy controls. Copied preview to Google Drive Testing/v0.4.0-custom-editing-controls; executable SHA256 4c5d060ac4aff50d4b7316acb4d8d17ad643bb323a06e0409fdd0acf997ea8cf. Native results cover routine-level behavior, not a full campaign.

2026-10-16 clarification: The four custom checkboxes are manual editing locks ONLY. Earlier export-gating behavior was incorrect and removed. Current values always participate in build/export, ship availability validation, Port Information and orange change markers. Model updates (including future Gameplay presets) remain allowed while UI controls are locked. Updated checks compare export bytes before/after each toggle and apply preset-style model changes with every lock off. This supersedes the earlier disabled-drafts semantics.
Orange markers now compare data to the stock ROM independently of editing locks. Disabled Changed styles retain orange foreground; Port Information shows orange economy/industry/specialty values. UI checks assert locked orange controls, list asterisks, section markers, preset-style updates with locks off, identical export bytes when toggling locks, and project persistence. 71 regression tests passed after semantic correction.
Corrected Windows executable passed custom-controls UI/export checks, including disabled orange fields and unchanged ROM bytes across editing-lock toggles. Preview delivered in Google Drive Testing/v0.4.0-manual-edit-locks.

2026-10-16: Added ships manual lock, top-of-page World editing switches, native four-slot item editing, six Easy Settings presets and item shuffle (regular/both/early only; four-digit seed; distinct blind domain). Blind source information hidden in Items and Port Information, changes report redacted. Item data patches town bytes29..32 only plus checksum, without a code hook; existing saves retain town stock. Project schema17 stores flags/slots/seed metadata. Native probe: 100 edited town stocks x48 half-hour ticks =4800 shop list cases and61 unchanged native item picture comparisons PASS. Eight item/preset/shuffle unit tests PASS; 71 existing model regressions PASS before final metadata additions. GUI and packaged checks recorded in output reports. Discoveries layout left unchanged at user request.

Final unit run:79 tests PASS (71 existing +8 new item/preset/shuffle tests), including three modes, normal/blind seed domains, preservation of regular/early multisets, unchanged empty slots, no duplicate town offers, repeatability, atomic invalid seeds, project round trip and blind changes-report redaction. Native100-town edited stock runner passed4800 half-hour list cases and61 original picture comparisons. Tests do not establish full purchase/payment or complete save-load gameplay.
World layout regression: added checkbox header exposed a 3px Lisbon overflow at1440x900 (another port was taller). Tightened page/heading/note/header spacing, retained original map controls. Focused all100-port check now worst731px vs739px available at1440x900. Packaged World checks rerun after rebuild.
Final GUI: all5 World sizes and100 wide port dashboards PASS. Final executable ship export self-test PASS in a unique test output directory. Earlier repeat in a reused directory correctly refused to overwrite Self Test Mod.sfc; harness now uses fresh test directory. Preview EXE copied/hash-verified in Google Drive Testing/v0.4.0-items-and-easy-settings.

2026-10-16 full shuffle testing: seed2026,40 free agents + regular/special items, normal/blind. Exact historical test-profile baseline hashes reproduced. Shuffle changes confined to expected data+checksum. Fresh native initialization:440 bytes x4 checkpoints x2 modes PASS. Fresh normal-save/Continue:440 bytes each mode PASS. Native shops9600 cases +122 item-picture comparisons PASS. Both four-ship battle rounds PASS; native repair/resale/fleet-toggle tests PASS. Public test scripts unchanged; private copies explicitly retargeted and harness corrections documented. Final construction/transactions in full-shuffle report. No editor/ROM implementation changes made during this run.

Full-shuffle run final status PASS: output/gameplay-test-pack/full-shuffle-2026-10-16-01/FULL-SHUFFLE-RESULTS.md. Completed68 days, collection, normal save/cold reload, sale/refit/repair branches. Initial invalid-harness attempts retained and explained; no game code or public test fixture guards were changed.

2026-10-16 UI refinement: Gameplay top-level tabs now Easy Settings, Battles, World, in that order. World holds nested Fleets/Mates/Items pages, each with its own scroll canvas. Active scroll selection follows both notebook levels. World Items intro now reflects editable shop data instead of the fallback read-only text. Project schema and ROM behavior unchanged. Updated UI fixture tab references and added gameplay_layout_checks for order, dialogs, unchanged settings and small/full-size scrolling.
Packaged Windows gameplay-layout and items-edit checks PASS. Layout/dialogs/nested scrolling tested at640x480,1440x900,1672x940. Six presets, normal/blind item shuffle dialog, items editing, project/IPS round trip and default reset passed. Settings unchanged by layout navigation. Preview copied with verified executable hash to Testing/v0.4.0-gameplay-tabs.

2026-10-16 correction to Gameplay World: user requested inline categories rather than subtabs. Removed inner notebook and separate inner scroll canvases. Fleets/Mates/Items are white cards with category headers on one shared World scroll canvas. Top-level Easy Settings/Battles/World unchanged. Updated dialog/navigation checks to verify all inline sections and pointer reachability on small and full-size windows. This supersedes the nested-tab layout notes above. No project/ROM data changes.

Random mate starting-port changes highlight Mates and affected mate entries, including blind shuffles. Gameplay highlighting reflects battle and custom fleet settings.

2026-10-16 seeded Trade and People options: project schema18 adds goods_shuffle {seed,mode}; legacy1–17 default to off. Existing free_agent_shuffle accepts optional ports=False, names, captain_names, mate_stats and captain_stats flags. SHA256 role-specific name/profile permutations keep fixed character IDs. Native name records are two fixed 13-byte fields, copied as a 26-byte pair; no pointer relocation. Only the 40 free agents and 64 fleet captain records participate in their respective groups. Profiles cover only eight attributes; values clamp to50–100, preserving whole profile grouping after clamping. Manual attribute edits override shuffled profiles, including explicit stock-value overrides. Trade uses the existing verified per-port market patch: deterministic constrained swaps of good/base-price pairs within Regional and/or Specialty groups; economy gates and kinds stay in their original slots. No duplicates, lost commodities or new slots. Manual goods edits clear seed metadata. GUI has four inline World cards; no nested tabs. Added test_seed_shuffles and shuffle-options-test. check_editor_goods_edit.py now accepts --shuffle/--seed/--people for repeatable native Mesen market checks. Limit: full trading transactions, long campaigns, and dialogue that embeds literal historical names remain gameplay checks.

2026-10-16 name correction: new shuffles independently permute first and last names, with separate SHA256 domains. Each 13-byte native field is copied without length or pointer changes. The optional name_parts flag selects v2; missing/false preserves the previous paired-name algorithm for old projects. Lists, previews and profile headings use the exact projected full name. Tests verify first/last multisets separately, new combinations, normal/blind repeatability, native bytes and legacy paired outputs.

2026-10-16 stat-budget correction: new stat shuffles redistribute each individual record’s original eight-attribute sum, with every result50–100. Stock free-agent minimum total418 and captain minimum495 make this feasible for every eligible record. A DP composition counter and seeded weighted sampling choose bounded allocations with exact sums. Domain includes role, record ID, seed and normal/blind mode. Optional stat_budget=True selects v2; missing/false preserves the older profile shuffle for reproducible prior projects. Manual edits still override shuffled values. Tests cover every eligible character across seeds/modes, native bytes, bounds400/800, invalid totals, project/IPS reload, and legacy behavior.

2026-10-16 skill shuffle: optional mate_skills/captain_skills select deterministic per-record low-five-bit skill masks with the native popcount. Group/ID/seed/blind domains are separate from names, ports and stats. Upper3 bits, companion/protagonist records and other fields are preserved. Effective preview/ROM compilation share the same generated edits; manual edits override. Added native-byte, popcount, determinism, combined project/reload and reset coverage.

People shuffle dialog footer is packed before the expandable preview so the extra skill options cannot hide Apply/Restore/Cancel. Source GUI regression passed after detecting and correcting this layout issue.

Gameplay World layout: compact boxes use two columns on wide screens and one scrolling column on narrow screens. One shared note covers seeds/new-game requirements; each box has a brief description and aligned controls/status. Detailed shuffle rules remain in their dialogs. Active seed statuses are orange. No project or ROM patch changes.

2026-10-16 Gameplay World correction: replaced overview buttons/descriptions with a single-column checkbox settings menu. WorldSettings wraps existing backend operations with guarded synchronization, per-group seed debounce/flush, invalid active seed export validation, reset cancellation and project-load handling. Mates/captains have seven independent toggles and one shared seed; Items/Trade have enable toggles, scope selectors and seeds. Preview dialogs remain optional. Ordinary World goods/item edits are preserved when shuffle is already off. No ROM patch/schema changes. Added world-settings-test for automatic application, concurrent seed edits, invalid export guards, load sync, resets and manual goods retention.

2026-10-16 user correction: retain compact checkbox rows, but move all shuffle settings back into review/apply popups. Buttons are Configure shuffle…; Fleets uses Configure fleets…. WorldSettings now only synchronizes master checkboxes/status and opens existing dialogs; checking an inactive shuffle opens a draft, Cancel/window close resets the checkbox to actual project state, and unchecking restores that active shuffle. No inline seed/debounce logic remains. Added preview_changes to compare proposed native character records with stock without mutating ROM/project, including names/ports/all attributes/skills. Mates popup now shows actual before/after rows for every enabled kind, with horizontal scrolling for long skill lists. Updated world-settings-test covers all dialogs, draft safety, apply/cancel/window close, disable and preserved manual World edits. No native patch or schema changes.

2026-10-16 clarified UI: four family-level checkboxes, exact labels Use random mates / Use random fleet captains / Use random items / Use random cargo. Mates and captains use separate group-specific popup options, previews and seeds. Added optional captain_seed/captain_blind/captain_name_parts/captain_stat_budget config fields, defaulting to prior shared values for legacy replay. configure_group freezes the other family before changing a group; disabled configurations normalize inactive default ports to false so enabling captains cannot enable mate ports. Native generators resolve per-family settings; no assembly changes. Split previews filter records to their own role group. Tests cover independent results/seeds/disable, native/project roundtrip, blind export redaction and actual checkbox-to-popup flows. Cargo means trade goods, not ship capacity.

2026-10-16 removed visible right-side configuration buttons from Gameplay World. Checkboxes open initial configuration; active summary labels are underlined, keyboard-focusable links with mouse/Return/Space bindings. Blind labels omit seeds. Custom fleets now opens when checked and has its own active Edit link. Existing command handles remain unmounted for shared app state hooks. Updated popup/layout checks use checkboxes and active links instead of the removed buttons. No ROM/project changes.

2026-10-16: Blind shuffle is available in all four Gameplay World randomizer popups. Cargo adds an optional goods_shuffle.blind boolean in schema18 (false omitted for existing-project compatibility), a separate deterministic blind RNG domain, hidden selling locations/map markers/Port Information specialty and goods rows, locked manual goods controls while blind, and redacted seed/destinations in exported changes reports. Saved projects retain configuration for reproduction; blind mode hides editor previews, not the project/ROM data. Normal goods seed output remains unchanged. Source popup checks and25 focused unit tests PASS, including three cargo modes, retained offer counts/prices/gates, project roundtrip, IPS reconstruction and export redaction. Packaged checks recorded separately.

2026-10-16: Replaced the long Help message box with four-section navigation and read-only scrollable content. Help works without a ROM, reuses its existing window, and includes current features, save/ROM limitations, About version/creator/disclaimer, repository link and acknowledgments. Focused help_checks covers navigation, small and normal windows, scroll access, read-only text, required About text, mocked repository launch, close/reopen and no-ROM use. No ROM logic changed.

2026-10-16: Version advanced to0.8.0 Beta. Gameplay World uses Use random goods and a Goods section heading. Updated Help and current documentation terminology; stock ship cargo remains named Cargo. VERSION, backend version and About derive consistent release metadata. No project schema or ROM algorithm change.

2026-10-16: Easy Settings now contains12 play-style/modular presets with pure draft plans, current-to-proposed preview, Apply/Cancel and seeded/blind controls. Presets preserve unrelated values and manual editing locks. Optional per-option settings within format18 character config preserve exact prior algorithms/seeds when layering names, ports, stats and skills; explicit World character dialogs replace their selected group, with a notice. Normal legacy configs replay unchanged. Partial item presets preserve outside slots and redistribute only the selected stock pool to avoid collisions; normal-goods presets preserve specialties and current slot gates. Prosperous World uses125% goods/110% industry; Developing World sets noncapital industry75% stock, preserves capitals/economy; Trade Opportunities uses80% stock-slot gates rounded to10, preserving additional nonstock slots. Naval Challenge changes flagship/fourth position only; Regional Fleets reuses existing regional rules. No new ROM hooks or persistent game RAM.42 focused unit tests and source UI preview/cancel/apply checks PASS. Combined Prosperous World + blind Uncharted Challenge + Trade Opportunities native Mesen probe passed100 pointers,1824 economy-boundary cases and300 market list cases; not full campaign/transaction verification.

Final preset validation:43 unit tests PASS. Preset drafts and Apply validate a copied project build before mutation. An economy preset that would newly lock an existing capital ship offer is rejected before any changes, covered by a regression test. Earlier editable World economy behavior is unchanged. Final preset ROM compared byte-for-byte with the Mesen-probed combined ROM. Seed and Blind controls use separate rows for narrow windows. Final packaged reports recorded separately.

2026-10-16: Version1.0.0, project format19. Original-25 shipbuilding shuffle permutes stock port groups using deterministic constrained bipartite matching, preserving per-port counts and per-model industry. Existing native locked-capital entries grandfathered; new locked-capital assignments excluded. No safe match rejects atomically. Added ships unchanged. Backup of pre-first-shuffle availability persists; disable/Restore previous/Reset Gameplay restores it, checking16-offer menu cap after added-ship edits. Manual original-availability edits clear metadata; stats edits retain it. Blind mode hides original ship destinations in popup, ship port selector, Port Information and changes report; project retains data. Random Shipyards added as13th preset and included in Fresh/Full/Uncharted. No new ROM hooks; existing availability compiler used. Native Mesen13772 shipyard-list/industry cases PASS across0/5 additions, normal/blind and combined preset, with UI rendering stubbed. First broad regression exposed schema19 key recognition and a pre-existing map_app/world import collision in shared test discovery; key whitelist fixed, atlas test group isolated. All171 tests then passed; final restore overflow test/checks recorded in release reports.

Final1.0.0 regression:172 tests PASS (editor modules plus isolated atlas group), including restore overflow rejection without mutation. Packaged shipbuilding and13-preset checks PASS. Native shipyard probe13772 cases PASS; remaining final UI reports are attached to the release folder.


## 1.0.1 maintenance backport - October 18, 2026

Based solely on the provided v1.0.0 source archive. Reserve item/goods shuffle action footers before expanding previews and give buttons an initial grid layout. Both dialogs wrap Random shuffle, Apply shuffle, Restore items/goods and Cancel at small widths. Goods hint is shortened so the preview remains usable at 400x380. No randomization algorithm, ROM patch logic, project schema, presets or feature limits changed. Added --item-shuffle-test and --goods-shuffle-test paths exercise actual clicks, four sizes, all modes, blind/cancel/restore and project/ROM/IPS roundtrips. The v1.1-dev source and release are separate and remain unchanged.
