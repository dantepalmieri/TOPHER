# builds TopherLauncher.exe - a separate, isolated venv from the one build_venv.ps1
# produces, deliberately: this one only ever gets pystray/pillow/pywin32, never the
# ml-heavy stack, keeping the frozen exe small
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
    # tray_app.py finds second_brain via a runtime sys.path.insert(), not a
    # static import PyInstaller's analyzer can follow - confirmed via its own
    # build output, warn-TopherLauncher.txt: "missing module named
    # second_brain". that means PyInstaller never sees far enough to discover
    # second_brain/config.py's own `from dotenv import load_dotenv`, so
    # dotenv silently never gets bundled no matter what's pip-installed into
    # this build venv - found by actually running the frozen exe from an
    # install-like layout: ModuleNotFoundError: dotenv, immediately on
    # startup. --hidden-import is PyInstaller's documented escape hatch for
    # exactly this shape of problem (a real dependency the static analyzer
    # cannot reach)
    & $LauncherVenvPython -m PyInstaller `
        --onefile `
        --windowed `
        --name TopherLauncher `
        --hidden-import dotenv `
        --distpath $DistPath `
        --workpath (Join-Path $LauncherDir "build") `
        --specpath (Join-Path $LauncherDir "build") `
        tray_app.py
}
finally {
    Pop-Location
}

Write-Host "TopherLauncher.exe built at $(Join-Path $DistPath 'TopherLauncher.exe')"
