# builds TopherLauncher.exe - a separate, isolated venv from the one build_venv.ps1
# produces, deliberately: this one only ever gets pystray/pillow/pywin32, never the
# ml-heavy stack, keeping the frozen exe small. this venv is never shipped (only
# used locally/in-ci to run pyinstaller, then discarded), so the portability
# problem build_venv.ps1's own comment describes does not apply here
$ErrorActionPreference = "Stop"

# $ErrorActionPreference does not turn a failed external command's exit code
# into a terminating error - see build_venv.ps1's own Assert-LastExitCodeSucceeded
# comment for why this matters; every external command below is checked
# explicitly for the same reason
function Assert-LastExitCodeSucceeded([string]$StepDescription) {
    if ($LASTEXITCODE -ne 0) {
        throw "$StepDescription failed (exit code $LASTEXITCODE)"
    }
}

$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$LauncherDir = Join-Path $ProjectRoot "packaging\launcher"
$LauncherVenvPath = Join-Path $LauncherDir "_build_venv"

if (Test-Path $LauncherVenvPath) {
    Remove-Item -Recurse -Force $LauncherVenvPath
}

python -m venv $LauncherVenvPath
Assert-LastExitCodeSucceeded "python -m venv"

$LauncherVenvPython = Join-Path $LauncherVenvPath "Scripts\python.exe"
& $LauncherVenvPython -m pip install --upgrade pip
Assert-LastExitCodeSucceeded "pip self-upgrade"
& $LauncherVenvPython -m pip install -r (Join-Path $LauncherDir "requirements-launcher.txt")
Assert-LastExitCodeSucceeded "pip install -r requirements-launcher.txt"

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
    Assert-LastExitCodeSucceeded "PyInstaller"
}
finally {
    Pop-Location
}

Write-Host "TopherLauncher.exe built at $(Join-Path $DistPath 'TopherLauncher.exe')"
