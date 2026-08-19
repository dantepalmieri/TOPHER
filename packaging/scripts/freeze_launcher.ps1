# phase 7: builds TopherLauncher.exe - a separate, isolated venv from the one
# build_venv.ps1 produces, deliberately: this one only ever gets pystray/pillow/
# pywin32/dotenv, never the ml-heavy stack, keeping the frozen exe small
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$LauncherDir = Join-Path $ProjectRoot "packaging\launcher"
$LauncherVenvPath = Join-Path $LauncherDir "_build_venv"

if (Test-Path $LauncherVenvPath) {
    Remove-Item -Recurse -Force $LauncherVenvPath
}

python -m venv $LauncherVenvPath

$LauncherVenvPython = Join-Path $LauncherVenvPath "Scripts\python.exe"
& $LauncherVenvPython -m pip install --upgrade pip
& $LauncherVenvPython -m pip install -r (Join-Path $LauncherDir "requirements-launcher.txt")

$DistPath = Join-Path $ProjectRoot "packaging\dist"
New-Item -ItemType Directory -Force -Path $DistPath | Out-Null

Push-Location $LauncherDir
try {
    & $LauncherVenvPython -m PyInstaller `
        --onefile `
        --windowed `
        --name TopherLauncher `
        --distpath $DistPath `
        --workpath (Join-Path $LauncherDir "build") `
        --specpath (Join-Path $LauncherDir "build") `
        tray_app.py
}
finally {
    Pop-Location
}

Write-Host "TopherLauncher.exe built at $(Join-Path $DistPath 'TopherLauncher.exe')"
