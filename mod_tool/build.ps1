param([string]$PythonExecutable='python')
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
    $taskVersion=(Get-Content -LiteralPath VERSION -Raw).Trim()
    $taskDestination=Join-Path $PSScriptRoot "dist\v$taskVersion"
    if (Test-Path -LiteralPath $taskDestination) { throw "Version $taskVersion already exists. Increment VERSION for another release." }
    $taskReadme=Join-Path (Split-Path -Parent $PSScriptRoot) 'README.md'
    $taskAssets=@('app-logo.png','default-settings.json','default-presets.json','default-library.json','previous-library-defaults.json')
    $taskDocuments=@($taskReadme,'CHANGELOG.md','VERSION','LICENSE','UWNHRando.LICENSE','Pillow.LICENSE','THIRD-PARTY-NOTICES.txt')
    foreach ($taskFile in ($taskDocuments + ($taskAssets | ForEach-Object { Join-Path $PSScriptRoot "assets/$_" }))) {
        if (-not (Test-Path -LiteralPath $taskFile -PathType Leaf)) { throw "Required release file missing: $taskFile" }
    }
    $taskBuildArguments=@('-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','New Horizons Ship Editor','--icon',(Join-Path $PSScriptRoot 'assets/app.ico'),'--version-file',(Join-Path $PSScriptRoot 'windows-version.txt'))
    foreach ($taskAsset in $taskAssets) {
        $taskBuildArguments+=@('--add-data',((Join-Path $PSScriptRoot "assets/$taskAsset")+';assets'))
    }
    $taskBuildArguments+=@('--paths','.','--distpath',$taskDestination,'--workpath','build\pyinstaller','--specpath','build','app.py')
    & $PythonExecutable @taskBuildArguments
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    Copy-Item -LiteralPath $taskDocuments -Destination $taskDestination
} finally { Pop-Location }
