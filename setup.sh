#!/bin/bash
#
# Subscription Tracker - Linux Setup Script
# This script installs and configures the Subscription Tracker application
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
INSTALL_DIR="/opt/subscription-tracker"
SERVICE_USER="subtracker"
PORT=5000
CREATE_SERVICE=true

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════╗"
    echo "║     Subscription Tracker - Setup Script    ║"
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

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root or with sudo"
        exit 1
    fi
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        log_info "Found Python $PYTHON_VERSION"
        return 0
    else
        log_error "Python 3 is not installed"
        echo "Please install Python 3.8 or higher:"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "  RHEL/CentOS:   sudo dnf install python3 python3-pip"
        exit 1
    fi
}

install_dependencies() {
    log_info "Checking system dependencies..."
    
    if command -v apt &> /dev/null; then
        apt update -qq
        apt install -y python3-venv python3-pip
    elif command -v dnf &> /dev/null; then
        dnf install -y python3-pip
    elif command -v yum &> /dev/null; then
        yum install -y python3-pip
    fi
}

create_user() {
    if id "$SERVICE_USER" &>/dev/null; then
        log_info "User $SERVICE_USER already exists"
    else
        log_info "Creating service user: $SERVICE_USER"
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
    fi
}

install_app() {
    log_info "Installing application to $INSTALL_DIR..."
    
    # Create directory
    mkdir -p "$INSTALL_DIR"
    
    # Copy files
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cp -r "$SCRIPT_DIR/app" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/run.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/config.py" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
    
    # Create virtual environment
    log_info "Creating Python virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    "$INSTALL_DIR/venv/bin/pip" install gunicorn
    
    # Ensure venv binaries are executable
    chmod +x "$INSTALL_DIR/venv/bin/"*
    
    # Create data directory
    mkdir -p "$INSTALL_DIR/data"
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR/venv/bin"
    chmod 750 "$INSTALL_DIR"
}

create_config() {
    log_info "Creating configuration..."
    
    # Generate secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    cat > "$INSTALL_DIR/.env" << EOF
SECRET_KEY=$SECRET_KEY
DATABASE_PATH=$INSTALL_DIR/data/subscriptions.db
FLASK_ENV=production
PORT=$PORT
EOF
    
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/subscription-tracker.service << EOF
[Unit]
Description=Subscription Tracker
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind 0.0.0.0:$PORT --workers 2 'app:create_app()'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable subscription-tracker
    log_info "Service created and enabled"
}

start_service() {
    log_info "Starting service..."
    systemctl start subscription-tracker
    sleep 2
    
    if systemctl is-active --quiet subscription-tracker; then
        log_info "Service started successfully!"
    else
        log_error "Service failed to start. Check logs with: journalctl -u subscription-tracker"
        exit 1
    fi
}

print_success() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════${NC}"
    echo ""
    echo "  Access the application at:"
    echo -e "  ${BLUE}http://localhost:$PORT${NC}"
    echo ""
    echo "  Useful commands:"
    echo "    Start:   sudo systemctl start subscription-tracker"
    echo "    Stop:    sudo systemctl stop subscription-tracker"
    echo "    Status:  sudo systemctl status subscription-tracker"
    echo "    Logs:    sudo journalctl -u subscription-tracker -f"
    echo ""
    echo "  Data location: $INSTALL_DIR/data/"
    echo ""
}

# Interactive mode
interactive_setup() {
    echo ""
    read -p "Installation directory [$INSTALL_DIR]: " input
    INSTALL_DIR="${input:-$INSTALL_DIR}"
    
    read -p "Port [$PORT]: " input
    PORT="${input:-$PORT}"
    
    read -p "Create systemd service? [Y/n]: " input
    if [[ "$input" =~ ^[Nn] ]]; then
        CREATE_SERVICE=false
    fi
    echo ""
}

# Main
main() {
    print_banner
    check_root
    check_python
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --port)
                PORT="$2"
                shift 2
                ;;
            --no-service)
                CREATE_SERVICE=false
                shift
                ;;
            --non-interactive)
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --dir <path>       Installation directory (default: /opt/subscription-tracker)"
                echo "  --port <port>      Port to run on (default: 5000)"
                echo "  --no-service       Don't create systemd service"
                echo "  --non-interactive  Skip prompts, use defaults"
                echo "  -h, --help         Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check if interactive
    if [ -t 0 ] && [ "$1" != "--non-interactive" ]; then
        interactive_setup
    fi
    
    install_dependencies
    create_user
    install_app
    create_config
    
    if [ "$CREATE_SERVICE" = true ]; then
        create_systemd_service
        start_service
    fi
    
    print_success
}

main "$@"
