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

Other regions, revisions, and previously patched ROMs are not supported in v0.3.0. Do not commit or distribute copyrighted ROMs, save files, or extracted game assets.

## Build the Windows executable

Install PyInstaller 6:

```powershell
python -m pip install "pyinstaller>=6,<7"
```

Then run the included build script:

```powershell
.\build.ps1
```

For version `0.3.0`, the script creates a versioned output folder at `dist/v0.3.0/`, containing the executable, accompanying documentation and MIT LICENSE. The script refuses to overwrite an existing version folder.

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
7. Commit the source and documentation to GitHub. Create a matching tag (for example, `v0.3.0`) and a **GitHub Release**, attaching the Windows ZIP and concise release notes.
8. Keep previously published releases available and unchanged. Publish corrections under a new version number.

The repository's main README describes the latest release. Git tags preserve the source and documentation associated with each older release.

## Scope

Version 0.3.0 edits the supported original ship data and adds up to five
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
