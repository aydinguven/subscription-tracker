#!/bin/bash
#
# Subscription Tracker - User Management Script
# Create, list, edit, and delete users
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default install directory (matches setup.sh)
INSTALL_DIR="${SUBTRACKER_DIR:-/opt/subscription-tracker}"
PYTHON="$INSTALL_DIR/venv/bin/python3"

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════╗"
    echo "║   Subscription Tracker - User Management   ║"
    echo "╚════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_install() {
    if [ ! -d "$INSTALL_DIR" ]; then
        log_error "Installation not found at $INSTALL_DIR"
        echo "Set SUBTRACKER_DIR environment variable or use --dir option"
        exit 1
    fi
    
    if [ ! -f "$PYTHON" ]; then
        log_error "Python virtual environment not found"
        exit 1
    fi
}

run_python() {
    cd "$INSTALL_DIR"
    $PYTHON -c "
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    $1
"
}

create_user() {
    echo ""
    read -p "Username: " username
    
    if [ -z "$username" ]; then
        log_error "Username cannot be empty"
        return 1
    fi
    
    read -p "Display name (optional, press Enter to skip): " display_name
    
    while true; do
        read -s -p "Password: " password
        echo ""
        
        if [ -z "$password" ]; then
            log_error "Password cannot be empty"
            continue
        fi
        
        if [ ${#password} -lt 4 ]; then
            log_error "Password must be at least 4 characters"
            continue
        fi
        
        read -s -p "Confirm password: " password2
        echo ""
        
        if [ "$password" != "$password2" ]; then
            log_error "Passwords do not match"
            continue
        fi
        
        break
    done
    
    read -p "Admin user? [y/N]: " is_admin
    admin_flag="False"
    if [[ "$is_admin" =~ ^[Yy] ]]; then
        admin_flag="True"
    fi
    
    display_name_escaped=$(printf '%s' "$display_name" | sed "s/'/\\\\'/g")
    username_escaped=$(printf '%s' "$username" | sed "s/'/\\\\'/g")
    password_escaped=$(printf '%s' "$password" | sed "s/'/\\\\'/g")
    
    run_python "
existing = User.query.filter_by(username='$username_escaped').first()
if existing:
    print('ERROR: User \"$username_escaped\" already exists')
    sys.exit(1)

user = User(username='$username_escaped', display_name='$display_name_escaped' or None, is_admin=$admin_flag)
user.set_password('$password_escaped')
db.session.add(user)
db.session.commit()

# Seed default categories for the new user
from app import seed_default_categories
seed_default_categories(user.id)

print(f'User \"{user.username}\" created successfully (ID: {user.id})')
"
    
    if [ $? -eq 0 ]; then
        log_info "User created!"
    else
        log_error "Failed to create user"
    fi
}

list_users() {
    echo ""
    run_python "
users = User.query.all()
if not users:
    print('No users found.')
else:
    print(f'{'ID':<6} {'Username':<20} {'Display Name':<25} {'Admin':<8} {'Created'}')
    print('-' * 90)
    for u in users:
        admin = 'Yes' if u.is_admin else 'No'
        display = u.display_name or '-'
        created = u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else '-'
        print(f'{u.id:<6} {u.username:<20} {display:<25} {admin:<8} {created}')
"
    echo ""
}

change_password() {
    echo ""
    read -p "Username: " username
    
    if [ -z "$username" ]; then
        log_error "Username cannot be empty"
        return 1
    fi
    
    while true; do
        read -s -p "New password: " password
        echo ""
        
        if [ -z "$password" ]; then
            log_error "Password cannot be empty"
            continue
        fi
        
        if [ ${#password} -lt 4 ]; then
            log_error "Password must be at least 4 characters"
            continue
        fi
        
        read -s -p "Confirm new password: " password2
        echo ""
        
        if [ "$password" != "$password2" ]; then
            log_error "Passwords do not match"
            continue
        fi
        
        break
    done
    
    username_escaped=$(printf '%s' "$username" | sed "s/'/\\\\'/g")
    password_escaped=$(printf '%s' "$password" | sed "s/'/\\\\'/g")
    
    run_python "
user = User.query.filter_by(username='$username_escaped').first()
if not user:
    print('ERROR: User \"$username_escaped\" not found')
    sys.exit(1)

user.set_password('$password_escaped')
db.session.commit()
print(f'Password updated for \"{user.username}\"')
"
    
    if [ $? -eq 0 ]; then
        log_info "Password changed!"
    else
        log_error "Failed to change password"
    fi
}

edit_user() {
    echo ""
    read -p "Username to edit: " username
    
    if [ -z "$username" ]; then
        log_error "Username cannot be empty"
        return 1
    fi
    
    username_escaped=$(printf '%s' "$username" | sed "s/'/\\\\'/g")
    
    # Check user exists
    run_python "
user = User.query.filter_by(username='$username_escaped').first()
if not user:
    print('ERROR: User \"$username_escaped\" not found')
    sys.exit(1)
print(f'Current display name: {user.display_name or \"(none)\"}')
print(f'Current admin status: {\"Yes\" if user.is_admin else \"No\"}')
" || return 1
    
    read -p "New display name (press Enter to keep current): " display_name
    read -p "Toggle admin status? [y/N]: " toggle_admin
    
    display_name_escaped=$(printf '%s' "$display_name" | sed "s/'/\\\\'/g")
    toggle_flag="False"
    if [[ "$toggle_admin" =~ ^[Yy] ]]; then
        toggle_flag="True"
    fi
    
    run_python "
user = User.query.filter_by(username='$username_escaped').first()
if '$display_name_escaped':
    user.display_name = '$display_name_escaped'
if $toggle_flag:
    user.is_admin = not user.is_admin
db.session.commit()
print(f'User \"{user.username}\" updated (display: {user.display_name}, admin: {user.is_admin})')
"
    
    if [ $? -eq 0 ]; then
        log_info "User updated!"
    else
        log_error "Failed to update user"
    fi
}

delete_user() {
    echo ""
    read -p "Username to delete: " username
    
    if [ -z "$username" ]; then
        log_error "Username cannot be empty"
        return 1
    fi
    
    username_escaped=$(printf '%s' "$username" | sed "s/'/\\\\'/g")
    
    read -p "Are you sure you want to delete user '$username' and ALL their data? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy] ]]; then
        echo "Cancelled."
        return 0
    fi
    
    run_python "
user = User.query.filter_by(username='$username_escaped').first()
if not user:
    print('ERROR: User \"$username_escaped\" not found')
    sys.exit(1)

# Delete user's data
from app.models import Subscription, Payment, Category, PaymentMethod, Settings
Payment.query.filter_by(user_id=user.id).delete()
Subscription.query.filter_by(user_id=user.id).delete()
Category.query.filter_by(user_id=user.id).delete()
PaymentMethod.query.filter_by(user_id=user.id).delete()
Settings.query.filter_by(user_id=user.id).delete()
db.session.delete(user)
db.session.commit()
print(f'User \"{user.username}\" and all associated data deleted')
"
    
    if [ $? -eq 0 ]; then
        log_info "User deleted!"
    else
        log_error "Failed to delete user"
    fi
}

show_menu() {
    echo ""
    echo "What would you like to do?"
    echo ""
    echo "  1) Create user"
    echo "  2) List users"
    echo "  3) Change password"
    echo "  4) Edit user"
    echo "  5) Delete user"
    echo "  6) Exit"
    echo ""
    read -p "Choice [1-6]: " choice
    
    case $choice in
        1) create_user ;;
        2) list_users ;;
        3) change_password ;;
        4) edit_user ;;
        5) delete_user ;;
        6) exit 0 ;;
        *) log_error "Invalid choice" ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)
            INSTALL_DIR="$2"
            PYTHON="$INSTALL_DIR/venv/bin/python3"
            shift 2
            ;;
        --create)
            ACTION="create"
            shift
            ;;
        --list)
            ACTION="list"
            shift
            ;;
        --passwd)
            ACTION="passwd"
            shift
            ;;
        --delete)
            ACTION="delete"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --dir <path>   Installation directory (default: /opt/subscription-tracker)"
            echo "  --create       Create a new user (non-interactive menu)"
            echo "  --list         List all users"
            echo "  --passwd       Change a user's password"
            echo "  --delete       Delete a user"
            echo "  -h, --help     Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Main
print_banner
check_install

if [ -n "$ACTION" ]; then
    case $ACTION in
        create) create_user ;;
        list) list_users ;;
        passwd) change_password ;;
        delete) delete_user ;;
    esac
else
    # Interactive menu loop
    while true; do
        show_menu
    done
fi
