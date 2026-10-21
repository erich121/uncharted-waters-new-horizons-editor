# Testing the editor

Editor tests require your own verified original USA ROM. For the full suite, place `New Horizons (USA).zip` in the source root. Some editor checks also accept `NH_STOCK_ROM`. Never commit or distribute the ROM or your saves.

Install the test dependencies and run the tests:

```sh
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests
```

GUI tests open real windows; run them in one process at a time. They use temporary settings folders.

Build the Windows executable from the source root with PowerShell:

```powershell
.\mod_tool\build.ps1
python tools/smoke_windows_build.py "mod_tool/dist/v1.1.0/New Horizons Ship Editor.exe" "New Horizons (USA).zip" --report-dir output/windows-smoke
```

The smoke test opens the editor, checks bundled presets, saves and reopens a project, exports ROM/IPS files, and checks the ten-added-ship preset workflow. Use a new report directory each time. These editor checks do not replace gameplay testing in an emulator.

Native emulator research tools also require a separately installed Mesen test runtime and local fixtures. Emulator binaries, ROMs and save snapshots are not included with this release. Historical mod research tests and their private fixtures are maintained separately from the editor release. `tools/check_editor_ten_ships.py` supplies the project root to its Lua templates before running them.
