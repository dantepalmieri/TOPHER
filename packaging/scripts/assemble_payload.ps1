# combines the project checkout (source, already containing the bundled venv/ and
# dashboard-frontend/dist/ built by build_venv.ps1 and `npm run build`) with the
# frozen launcher exe into packaging\payload\, the exact directory topher.iss
# copies into the installer as-is
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$PayloadDir = Join-Path $ProjectRoot "packaging\payload"

if (Test-Path $PayloadDir) {
    Remove-Item -Recurse -Force $PayloadDir
}
New-Item -ItemType Directory -Force -Path $PayloadDir | Out-Null

# a fresh CI checkout would never contain .env/.mcp.json/dashboard.db*/
# conversation_history.json in the first place (all gitignored, so
# actions/checkout never creates them) - excluded here explicitly anyway, as
# defense in depth, since this same script also runs against a real local
# working tree during a dry run, where those files legitimately do exist and
# must never end up inside a distributable installer payload
#
# the top-level packaging/ directory is excluded by its full, anchored path,
# not a bare name - a bare "packaging" would also match (and silently strip)
# venv\Lib\site-packages\packaging\, the actual pip package transformers
# depends on, which happens to share the exact same directory name. found via
# this script's own local dry run: the bundled server crashed at import time
# with ModuleNotFoundError: No module named 'packaging' once copied
$TopLevelPackagingDirectory = Join-Path $ProjectRoot "packaging"

# robocopy exit codes 0-7 all mean success (see robocopy's own documentation of
# its exit code bitmask); only 8+ is a real failure
#
# .git is excluded outright - nothing in the installed app can write to its own
# source (self-improvement mode was removed), so there is no reason for the
# installed copy to be a working git repo at all. smaller, faster-to-build payload,
# and one less category of installer fragility (hidden-attribute/wildcard-scan
# handling this project has been bitten by before)
robocopy $ProjectRoot $PayloadDir /E `
    /XD "node_modules" "__pycache__" ".pytest_cache" ".ruff_cache" $TopLevelPackagingDirectory ".claude" ".github" ".git" `
    /XF "*.pyc" "requirements-dev.txt" ".env" "dashboard.db*" `
    | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed while assembling the payload (exit code $LASTEXITCODE)"
}

$LauncherExePath = Join-Path $ProjectRoot "packaging\dist\TopherLauncher.exe"
if (-not (Test-Path $LauncherExePath)) {
    throw "TopherLauncher.exe not found at $LauncherExePath - run freeze_launcher.ps1 first"
}
Copy-Item $LauncherExePath -Destination $PayloadDir

$BundledVenvPath = Join-Path $PayloadDir "venv"
if (-not (Test-Path (Join-Path $BundledVenvPath "python.exe"))) {
    throw "Bundled python runtime not found under the payload - run build_venv.ps1 first"
}

$FrontendDistPath = Join-Path $PayloadDir "dashboard-frontend\dist"
if (-not (Test-Path $FrontendDistPath)) {
    throw "Frontend dist/ not found under the payload - run `npm run build` first"
}

Write-Host "Payload assembled at $PayloadDir"
# robocopy's own success exit codes (1-7) would otherwise become this script's
# exit code too, and a github actions `run:` step treats any non-zero exit as
# a failed step - reset it explicitly now that every check above has passed
exit 0
