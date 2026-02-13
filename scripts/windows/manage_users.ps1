#
# Subscription Tracker - Windows User Management Script
# Run: powershell -ExecutionPolicy Bypass -File scripts\windows\manage_users.ps1
#

param(
    [string]$ProjectDir = "",
    [ValidateSet("create", "list", "passwd", "edit", "delete", "")]
    [string]$Action = "",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Subscription Tracker - User Management

Usage:
    .\manage_users.ps1 [-Action <action>] [-ProjectDir <path>]

Actions:
    create    Create a new user
    list      List all users
    passwd    Change a user's password
    edit      Edit a user
    delete    Delete a user

Options:
    -ProjectDir    Project root directory (default: auto-detect)
    -Help          Show this help
"@
    exit 0
}

$ErrorActionPreference = "Stop"

# Resolve project root
if ([string]::IsNullOrEmpty($ProjectDir)) {
    $ProjectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

$pythonExe = Join-Path $ProjectDir "venv\Scripts\python.exe"

if (-Not (Test-Path $pythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at $ProjectDir\venv" -ForegroundColor Red
    Write-Host "  Run setup.ps1 first to create the virtual environment."
    exit 1
}

function Invoke-Python($code) {
    $fullCode = @"
import sys, os
sys.path.insert(0, '$($ProjectDir -replace '\\', '\\\\')') 
os.chdir('$($ProjectDir -replace '\\', '\\\\')')
from app import create_app, db
from app.models import User
app = create_app()
with app.app_context():
    $code
"@
    & $pythonExe -c $fullCode
    return $LASTEXITCODE
}

function New-AppUser {
    Write-Host ""
    $username = Read-Host "Username"
    if ([string]::IsNullOrEmpty($username)) {
        Write-Host "[ERROR] Username cannot be empty" -ForegroundColor Red
        return
    }
    
    $displayName = Read-Host "Display name (optional)"
    
    do {
        $pass = Read-Host "Password" -AsSecureString
        $passPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass))
        
        if ($passPlain.Length -lt 4) {
            Write-Host "  Password must be at least 4 characters" -ForegroundColor Red
            continue
        }
        
        $pass2 = Read-Host "Confirm password" -AsSecureString
        $pass2Plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass2))
        
        if ($passPlain -ne $pass2Plain) {
            Write-Host "  Passwords do not match" -ForegroundColor Red
            continue
        }
        break
    } while ($true)
    
    $isAdmin = Read-Host "Admin user? [y/N]"
    $adminFlag = if ($isAdmin -match "^[Yy]") { "True" } else { "False" }
    $dispArg = if ($displayName) { $displayName } else { "" }
    
    $code = @"
    from app import seed_default_categories
    existing = User.query.filter_by(username='$username').first()
    if existing:
        print('ERROR: User "$username" already exists')
        sys.exit(1)
    user = User(username='$username', display_name='$dispArg' or None, is_admin=$adminFlag)
    user.set_password('$passPlain')
    db.session.add(user)
    db.session.commit()
    seed_default_categories(user.id)
    print(f'User "{username}" created successfully (ID: {user.id})')
"@
    
    Invoke-Python $code
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] User created!" -ForegroundColor Green
    }
}

function Get-AppUsers {
    Write-Host ""
    $code = @"
    users = User.query.all()
    if not users:
        print('No users found.')
    else:
        print(f"{'ID':<6} {'Username':<20} {'Display Name':<25} {'Admin':<8} {'Created'}")
        print('-' * 90)
        for u in users:
            admin = 'Yes' if u.is_admin else 'No'
            display = u.display_name or '-'
            created = u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else '-'
            print(f'{u.id:<6} {u.username:<20} {display:<25} {admin:<8} {created}')
"@
    Invoke-Python $code
    Write-Host ""
}

function Set-AppUserPassword {
    Write-Host ""
    $username = Read-Host "Username"
    if ([string]::IsNullOrEmpty($username)) {
        Write-Host "[ERROR] Username cannot be empty" -ForegroundColor Red
        return
    }
    
    do {
        $pass = Read-Host "New password" -AsSecureString
        $passPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass))
        
        if ($passPlain.Length -lt 4) {
            Write-Host "  Password must be at least 4 characters" -ForegroundColor Red
            continue
        }
        
        $pass2 = Read-Host "Confirm new password" -AsSecureString
        $pass2Plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass2))
        
        if ($passPlain -ne $pass2Plain) {
            Write-Host "  Passwords do not match" -ForegroundColor Red
            continue
        }
        break
    } while ($true)
    
    $code = @"
    user = User.query.filter_by(username='$username').first()
    if not user:
        print('ERROR: User "$username" not found')
        sys.exit(1)
    user.set_password('$passPlain')
    db.session.commit()
    print(f'Password updated for "{user.username}"')
"@
    
    Invoke-Python $code
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Password changed!" -ForegroundColor Green
    }
}

function Edit-AppUser {
    Write-Host ""
    $username = Read-Host "Username to edit"
    if ([string]::IsNullOrEmpty($username)) {
        Write-Host "[ERROR] Username cannot be empty" -ForegroundColor Red
        return
    }
    
    # Show current info
    $code = @"
    user = User.query.filter_by(username='$username').first()
    if not user:
        print('ERROR: User "$username" not found')
        sys.exit(1)
    print(f'Current display name: {user.display_name or "(none)"}')
    print(f'Current admin status: {"Yes" if user.is_admin else "No"}')
"@
    Invoke-Python $code
    if ($LASTEXITCODE -ne 0) { return }
    
    $newDisplay = Read-Host "New display name (Enter to keep current)"
    $toggleAdmin = Read-Host "Toggle admin status? [y/N]"
    $toggleFlag = if ($toggleAdmin -match "^[Yy]") { "True" } else { "False" }
    
    $code = @"
    user = User.query.filter_by(username='$username').first()
    if '$newDisplay':
        user.display_name = '$newDisplay'
    if $toggleFlag:
        user.is_admin = not user.is_admin
    db.session.commit()
    print(f'User "{user.username}" updated (display: {user.display_name}, admin: {user.is_admin})')
"@
    
    Invoke-Python $code
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] User updated!" -ForegroundColor Green
    }
}

function Remove-AppUser {
    Write-Host ""
    $username = Read-Host "Username to delete"
    if ([string]::IsNullOrEmpty($username)) {
        Write-Host "[ERROR] Username cannot be empty" -ForegroundColor Red
        return
    }
    
    $confirm = Read-Host "Delete user '$username' and ALL their data? [y/N]"
    if ($confirm -notmatch "^[Yy]") {
        Write-Host "Cancelled."
        return
    }
    
    $code = @"
    from app.models import Subscription, Payment, Category, PaymentMethod, Settings
    user = User.query.filter_by(username='$username').first()
    if not user:
        print('ERROR: User "$username" not found')
        sys.exit(1)
    Payment.query.filter_by(user_id=user.id).delete()
    Subscription.query.filter_by(user_id=user.id).delete()
    Category.query.filter_by(user_id=user.id).delete()
    PaymentMethod.query.filter_by(user_id=user.id).delete()
    Settings.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    print(f'User "{user.username}" and all associated data deleted')
"@
    
    Invoke-Python $code
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] User deleted!" -ForegroundColor Green
    }
}

function Show-Menu {
    Write-Host ""
    Write-Host "  ╔════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║   Subscription Tracker - User Management   ║" -ForegroundColor Cyan
    Write-Host "  ╚════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1) Create user"
    Write-Host "  2) List users"
    Write-Host "  3) Change password"
    Write-Host "  4) Edit user"
    Write-Host "  5) Delete user"
    Write-Host "  6) Exit"
    Write-Host ""
    $choice = Read-Host "Choice [1-6]"
    
    switch ($choice) {
        "1" { New-AppUser }
        "2" { Get-AppUsers }
        "3" { Set-AppUserPassword }
        "4" { Edit-AppUser }
        "5" { Remove-AppUser }
        "6" { exit 0 }
        default { Write-Host "[ERROR] Invalid choice" -ForegroundColor Red }
    }
}

# Main
if (-Not [string]::IsNullOrEmpty($Action)) {
    switch ($Action) {
        "create" { New-AppUser }
        "list" { Get-AppUsers }
        "passwd" { Set-AppUserPassword }
        "edit" { Edit-AppUser }
        "delete" { Remove-AppUser }
    }
}
else {
    while ($true) {
        Show-Menu
    }
}
