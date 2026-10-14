param([string]$PythonExecutable='python')
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
    $taskVersion=(Get-Content -LiteralPath VERSION -Raw).Trim()
    $taskDestination=Join-Path $PSScriptRoot "dist\v$taskVersion"
    if (Test-Path -LiteralPath $taskDestination) { throw "Version $taskVersion already exists. Increment VERSION for another release." }
    & $PythonExecutable -m PyInstaller --noconfirm --clean --onefile --windowed --name 'New Horizons Ship Editor' --paths . --distpath $taskDestination --workpath 'build\pyinstaller' --specpath build app.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    Copy-Item -LiteralPath README.txt,CHANGELOG.md,VERSION,LICENSE -Destination $taskDestination
} finally { Pop-Location }
