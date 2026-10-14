# Development

Developer instructions for **New Horizons Ship Editor**. For installation and day-to-day use, see [README.md](README.md) and [README.txt](README.txt).

## Requirements

- Windows
- Python 3.12 or later, with Tkinter available
- PyInstaller 6 (only needed to build the Windows executable)

The editor itself uses Python's standard library and Tkinter. No game files are bundled with the source or executable.

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

### Supported base ROM

The editor validates the original USA game using this **SHA-256** checksum (for the ROM data without a 512-byte copier header):

```text
64bc4707f422661a66618088887e2363a5f896ea683c58984fffd96dd21ab5f0
```

Other regions, revisions, and previously patched ROMs are not supported in v0.1.0. Do not commit or distribute copyrighted ROMs, save files, or extracted game assets.

## Build the Windows executable

Install PyInstaller 6:

```powershell
python -m pip install "pyinstaller>=6,<7"
```

Then run the included build script:

```powershell
.\build.ps1
```

For version `0.1.0`, the script creates a versioned output folder at `dist/v0.1.0/`, containing the executable and accompanying documentation. The script refuses to overwrite an existing version folder.

Test the packaged executable on Windows before publishing it. The presence of a successful build alone does not establish gameplay compatibility.

## Release checklist

1. Update `TOOL_VERSION` in `backend.py` and the `VERSION` file to the **same version number**.
2. Update `README.md`, `README.txt`, and `CHANGELOG.md` for the release.
3. Run the unit tests and Tkinter smoke test using a compatible stock ROM.
4. Build the executable with `build.ps1`, then launch and smoke-test the packaged application.
5. Test representative edits and exports in an emulator. Verify that IPS output reproduces the intended ROM changes.
6. Package the Windows download ZIP with its version-specific `README.txt`; generate and verify checksums for the final package.
7. Commit the source and documentation to GitHub. Create a matching tag (for example, `v0.1.0`) and a **GitHub Release**, attaching the Windows ZIP and concise release notes.
8. Keep previously published releases available and unchanged. Publish corrections under a new version number.

The repository's main README describes the latest release. Git tags preserve the source and documentation associated with each older release.

## Scope

Version 0.1.0 edits existing ship data only; it does not add new ship classes or alter the game's engine. Gameplay balance and full-campaign compatibility remain matters for emulator testing.

The editor is an independent fan-made tool and does not include game ROMs, extracted artwork, or private research workspace data.
