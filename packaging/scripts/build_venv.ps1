# builds the portable python runtime that gets bundled inside the windows
# installer. run from anywhere - always resolves paths relative to this
# script's own location, the same convention second_brain/config.py uses
# for the same reason
#
# uses python.org's official embeddable distribution instead of `python -m
# venv` - venvs are not relocatable on windows: Scripts\python.exe is a small
# redirector stub whose target base interpreter path (pyvenv.cfg's `home`) is
# baked in at creation time. that's invisible when building and running on
# the same machine (every local test before this), but breaks completely the
# moment release.yml builds it for real on a github actions runner
# (home = C:\hostedtoolcache\windows\Python\...) and it gets installed on an
# actual user's machine, which does not have that path: the bundled
# interpreter fails immediately with "No Python at
# '"C:\hostedtoolcache\...\python.exe'" - confirmed directly, both by an
# actual installed release failing this way and by reproducing the same
# stub/pyvenv.cfg behavior locally. `venv --copies` does not avoid this
# either - it only changes whether dlls/data files are copied vs symlinked,
# not the launcher stub redirection. the embeddable distribution has no such
# indirection: no pyvenv.cfg, no "home" to go stale - genuinely self-
# contained wherever it ends up on disk
$ErrorActionPreference = "Stop"

# $ErrorActionPreference only governs powershell's own cmdlets/native errors -
# it does NOT turn a non-zero exit code from an external command (pip, an
# embedded python.exe) into a terminating error. found live: a pip install
# failure part-way through (see the claude-agent-sdk pin above) left this
# script printing its own success message and exiting 0 anyway, silently
# shipping an incomplete runtime. every external command below is checked
# explicitly instead of trusting $ErrorActionPreference to cover it
function Assert-LastExitCodeSucceeded([string]$StepDescription) {
    if ($LASTEXITCODE -ne 0) {
        throw "$StepDescription failed (exit code $LASTEXITCODE)"
    }
}

$PythonVersion = "3.11.9"
$EmbedZipUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$VenvPath = Join-Path $ProjectRoot "venv"

if (Test-Path $VenvPath) {
    Remove-Item -Recurse -Force $VenvPath
}
New-Item -ItemType Directory -Force -Path $VenvPath | Out-Null

$EmbedZipPath = Join-Path $env:TEMP "python-embed-$PythonVersion.zip"
Invoke-WebRequest -Uri $EmbedZipUrl -OutFile $EmbedZipPath
Expand-Archive -Path $EmbedZipPath -DestinationPath $VenvPath -Force
Remove-Item $EmbedZipPath

# the embeddable distribution ships with site-packages disabled by default -
# python311._pth restricts sys.path to just the bundled stdlib zip, so
# nothing pip-installs would even be importable without this. uncommenting
# `import site` and pointing it at Lib\site-packages is what makes both pip
# itself and this project's own third-party dependencies loadable at all
#
# _pth restricted mode also disables the things that would normally make
# `python.exe -m second_brain.dashboard.server` (tray_app.py's own launch
# command, run with cwd set to the install directory) find second_brain at
# all: it ignores PYTHONPATH entirely, and -m's usual implicit cwd-prepend
# does not happen either - confirmed directly, ModuleNotFoundError: no
# module named second_brain, even with cwd correctly set to the install
# directory. every path in _pth is resolved relative to this venv folder
# itself (not cwd), so ".." - the project root, where second_brain/ actually
# lives, one level up from this embeddable python - is what makes it
# resolvable at all
$PthFile = Join-Path $VenvPath "python311._pth"
(Get-Content $PthFile) -replace '^#import site$', 'import site' | Set-Content $PthFile
Add-Content $PthFile "Lib\site-packages"
Add-Content $PthFile ".."

$VenvPython = Join-Path $VenvPath "python.exe"

$GetPipPath = Join-Path $env:TEMP "get-pip.py"
Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipPath
& $VenvPython $GetPipPath
Assert-LastExitCodeSucceeded "get-pip.py bootstrap"
Remove-Item $GetPipPath

& $VenvPython -m pip install --upgrade pip
Assert-LastExitCodeSucceeded "pip self-upgrade"
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
Assert-LastExitCodeSucceeded "pip install -r requirements.txt"

Write-Host "Bundled portable Python runtime built at $VenvPath"
