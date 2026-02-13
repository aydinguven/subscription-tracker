#
# Subscription Tracker - Windows Update Script
# Run: powershell -ExecutionPolicy Bypass -File scripts\windows\update.ps1
#

param(
    [string]$SourceDir = "",
    [string]$InstallDir = "",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Subscription Tracker - Windows Update

Usage:
    .\update.ps1 [-SourceDir <path>] [-InstallDir <path>]

Options:
    -SourceDir     Git repository directory (default: auto-detect from script location)
    -InstallDir    Installation directory (default: same as source)
    -Help          Show this help
"@
    exit 0
}

$ErrorActionPreference = "Stop"

# Resolve project root
$ScriptRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if ([string]::IsNullOrEmpty($SourceDir)) {
    $SourceDir = $ScriptRoot
}

if ([string]::IsNullOrEmpty($InstallDir)) {
    $InstallDir = $SourceDir
}

Write-Host ""
Write-Host "  Subscription Tracker - Update" -ForegroundColor Cyan
Write-Host ""

# Step 1: Pull latest
Write-Host "[1/3] " -ForegroundColor Green -NoNewline
Write-Host "Pulling latest changes..."
Push-Location $SourceDir
try {
    git pull
}
catch {
    Write-Host "[WARN] Git pull failed (not a git repo or no remote)" -ForegroundColor Yellow
}
Pop-Location

# Step 2: Update dependencies
Write-Host "[2/3] " -ForegroundColor Green -NoNewline
Write-Host "Updating dependencies..."
$pipPath = Join-Path $InstallDir "venv\Scripts\pip.exe"

if (Test-Path $pipPath) {
    & $pipPath install -r (Join-Path $SourceDir "requirements.txt") --quiet
    Write-Host "[OK] Dependencies updated" -ForegroundColor Green
}
else {
    Write-Host "[WARN] Virtual environment not found. Run setup.ps1 first." -ForegroundColor Yellow
}

# Step 3: Restart (inform user)
Write-Host "[3/3] " -ForegroundColor Green -NoNewline
Write-Host "Update complete!"
Write-Host ""
Write-Host "  If running as a service, restart it manually." -ForegroundColor Yellow
Write-Host "  If running with run.py, stop and restart the server."
Write-Host ""
