# phase 7: builds the venv that gets bundled inside the windows installer.
# run from anywhere - always resolves paths relative to this script's own
# location, the same convention second_brain/config.py uses for the same reason
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$VenvPath = Join-Path $ProjectRoot "venv"

if (Test-Path $VenvPath) {
    Remove-Item -Recurse -Force $VenvPath
}

python -m venv $VenvPath

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

Write-Host "Bundled venv built at $VenvPath"
