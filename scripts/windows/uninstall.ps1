#
# Subscription Tracker - Windows Uninstall Script
# Run: powershell -ExecutionPolicy Bypass -File scripts\windows\uninstall.ps1
#

param(
    [string]$InstallDir = "",
    [switch]$KeepData,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Subscription Tracker - Windows Uninstall

Usage:
    .\uninstall.ps1 [-InstallDir <path>] [-KeepData]

Options:
    -InstallDir    Installation directory (default: auto-detect from script location)
    -KeepData      Keep the database and data directory
    -Help          Show this help
"@
    exit 0
}

$ErrorActionPreference = "Stop"

# Resolve project root
if ([string]::IsNullOrEmpty($InstallDir)) {
    $InstallDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

Write-Host ""
Write-Host "  Subscription Tracker - Uninstall" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Install directory: $InstallDir"
Write-Host ""

$confirm = Read-Host "This will remove the virtual environment and optionally data. Continue? [y/N]"
if ($confirm -notmatch "^[Yy]") {
    Write-Host "Cancelled."
    exit 0
}

# Backup data if requested
$dataDir = Join-Path $InstallDir "data"
if (-Not $KeepData) {
    $keepChoice = Read-Host "Keep the database? [Y/n]"
    if ($keepChoice -notmatch "^[Nn]") {
        $KeepData = $true
    }
}

if ($KeepData -and (Test-Path $dataDir)) {
    $backupDir = Join-Path $env:TEMP "subscription-tracker-backup-$(Get-Date -Format 'yyyyMMddHHmmss')"
    Write-Host "[1/3] Backing up data to $backupDir..." -ForegroundColor Green
    Copy-Item -Path $dataDir -Destination $backupDir -Recurse
    Write-Host "[OK] Data backed up" -ForegroundColor Green
}
else {
    Write-Host "[1/3] Skipping backup" -ForegroundColor Yellow
}

# Remove virtual environment
$venvDir = Join-Path $InstallDir "venv"
if (Test-Path $venvDir) {
    Write-Host "[2/3] Removing virtual environment..." -ForegroundColor Green
    Remove-Item -Path $venvDir -Recurse -Force
    Write-Host "[OK] Virtual environment removed" -ForegroundColor Green
}
else {
    Write-Host "[2/3] No virtual environment found" -ForegroundColor Yellow
}

# Remove data if not keeping
if (-Not $KeepData -and (Test-Path $dataDir)) {
    Write-Host "[3/3] Removing data directory..." -ForegroundColor Green
    Remove-Item -Path $dataDir -Recurse -Force
    Write-Host "[OK] Data removed" -ForegroundColor Green
}
else {
    Write-Host "[3/3] Data directory preserved" -ForegroundColor Yellow
}

# Remove .env
$envFile = Join-Path $InstallDir ".env"
if (Test-Path $envFile) {
    Remove-Item -Path $envFile -Force
}

Write-Host ""
Write-Host "  Uninstall complete!" -ForegroundColor Green
if ($KeepData) {
    Write-Host "  Data backed up to: $backupDir" -ForegroundColor Cyan
}
Write-Host ""
