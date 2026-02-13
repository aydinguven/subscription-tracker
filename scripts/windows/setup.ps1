#
# Subscription Tracker - Windows Setup Script
# Run: powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1
#

param(
    [string]$InstallDir = ".\",
    [int]$Port = 5000,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Subscription Tracker - Windows Setup

Usage:
    .\setup.ps1 [-InstallDir <path>] [-Port <port>]

Options:
    -InstallDir    Installation directory (default: current directory)
    -Port          Port to run on (default: 5000)
    -Help          Show this help message
"@
    exit 0
}

$ErrorActionPreference = "Stop"

function Write-Banner {
    Write-Host ""
    Write-Host "  ╔════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║   Subscription Tracker - Windows Setup     ║" -ForegroundColor Cyan
    Write-Host "  ╚════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step($step, $message) {
    Write-Host "[$step] " -ForegroundColor Green -NoNewline
    Write-Host $message
}

function Write-Success($message) {
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $message
}

function Write-Warn($message) {
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $message
}

# Resolve project root (two levels up from scripts/windows/)
$ScriptRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$InstallDir = (Resolve-Path $InstallDir -ErrorAction SilentlyContinue) ?? $InstallDir

Write-Banner

# Step 1: Check Python
Write-Step "1/5" "Checking Python installation..."
try {
    $pythonVersion = & python --version 2>&1
    Write-Success "Found $pythonVersion"
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/"
    Write-Host "  Make sure to check 'Add Python to PATH' during installation"
    exit 1
}

# Step 2: Create virtual environment
Write-Step "2/5" "Creating Python virtual environment..."
$venvPath = Join-Path $InstallDir "venv"

if (-Not (Test-Path $venvPath)) {
    & python -m venv $venvPath
    Write-Success "Virtual environment created at $venvPath"
} else {
    Write-Success "Virtual environment already exists"
}

# Step 3: Install dependencies
Write-Step "3/5" "Installing Python dependencies..."
$pipPath = Join-Path $venvPath "Scripts\pip.exe"
$requirementsPath = Join-Path $ScriptRoot "requirements.txt"

& $pipPath install --upgrade pip --quiet
& $pipPath install -r $requirementsPath --quiet
Write-Success "Dependencies installed"

# Step 4: Create data directory
Write-Step "4/5" "Setting up data directory..."
$dataDir = Join-Path $InstallDir "data"
if (-Not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}
Write-Success "Data directory: $dataDir"

# Step 5: Create .env config
Write-Step "5/5" "Creating configuration..."
$envPath = Join-Path $InstallDir ".env"

if (-Not (Test-Path $envPath)) {
    $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
    $dbPath = Join-Path $dataDir "subscriptions.db"
    
    @"
SECRET_KEY=$secretKey
DATABASE_PATH=$dbPath
FLASK_ENV=production
PORT=$Port
"@ | Set-Content -Path $envPath -Encoding UTF8
    
    Write-Success "Configuration created at $envPath"
} else {
    Write-Success "Configuration already exists"
}

# Create initial admin user
Write-Host ""
$createAdmin = Read-Host "Create initial admin user? [Y/n]"
if ($createAdmin -ne "n" -and $createAdmin -ne "N") {
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    
    $adminUser = Read-Host "Admin username [admin]"
    if ([string]::IsNullOrEmpty($adminUser)) { $adminUser = "admin" }
    
    $adminDisplay = Read-Host "Admin display name (optional)"
    
    do {
        $adminPass = Read-Host "Admin password" -AsSecureString
        $adminPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass))
        
        if ($adminPassPlain.Length -lt 4) {
            Write-Host "  Password must be at least 4 characters" -ForegroundColor Red
            continue
        }
        
        $adminPass2 = Read-Host "Confirm password" -AsSecureString
        $adminPass2Plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass2))
        
        if ($adminPassPlain -ne $adminPass2Plain) {
            Write-Host "  Passwords do not match" -ForegroundColor Red
            continue
        }
        break
    } while ($true)
    
    $displayArg = if ($adminDisplay) { $adminDisplay } else { "" }
    
    $pyScript = @"
import sys, os
sys.path.insert(0, '$($ScriptRoot -replace '\\', '\\\\')') 
os.chdir('$($ScriptRoot -replace '\\', '\\\\')')
from app import create_app, db, seed_default_categories
from app.models import User
app = create_app()
with app.app_context():
    user = User(username='$adminUser', display_name='$displayArg' or None, is_admin=True)
    user.set_password('$adminPassPlain')
    db.session.add(user)
    db.session.commit()
    seed_default_categories(user.id)
    print(f'Admin user "{user.username}" created (ID: {user.id})')
"@
    
    & $pythonExe -c $pyScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Admin user created!"
    } else {
        Write-Warn "Failed to create admin user. Use manage_users.ps1 later."
    }
}

# Print success
Write-Host ""
Write-Host "  ════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "  ════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  To start the development server:"
Write-Host "    .\venv\Scripts\python.exe run.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To start with Waitress (production):"
Write-Host "    .\venv\Scripts\pip.exe install waitress" -ForegroundColor Cyan
Write-Host "    .\venv\Scripts\waitress-serve.exe --port=$Port app:create_app()" -ForegroundColor Cyan
Write-Host ""
Write-Host "  User management:"
Write-Host "    powershell -File scripts\windows\manage_users.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Data location: $dataDir"
Write-Host ""
