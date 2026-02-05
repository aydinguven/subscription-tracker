#!/bin/bash
# Subscription Tracker Deployment Script
# Run as root: sudo bash deploy.sh [--port PORT]

set -e

# Default configuration
APP_NAME="subscription-tracker"
APP_USER="subscription-tracker-user"
APP_DIR="/opt/subscription-tracker"
SOURCE_DIR="/home/aydin/subscription-tracker"
PORT=5003
DATA_DIR="$APP_DIR/data"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: sudo bash deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT    Port to run on (default: 5003)"
            echo "  --source DIR   Source directory (default: /home/aydin/subscription-tracker)"
            echo "  --help         Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage"
            exit 1
            ;;
    esac
done

echo "==================================="
echo "  Subscription Tracker Deployment"
echo "==================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash deploy.sh)"
    exit 1
fi

# Create application user if not exists
echo "[1/7] Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /bin/false --home-dir "$APP_DIR" "$APP_USER"
    echo "  Created user: $APP_USER"
else
    echo "  User $APP_USER already exists"
fi

# Create application directory
echo "[2/7] Setting up application directory..."
mkdir -p "$APP_DIR"
mkdir -p "$DATA_DIR"

# Copy application files
echo "[3/7] Copying application files..."
cp -r "$SOURCE_DIR/app" "$APP_DIR/"
cp -r "$SOURCE_DIR/config.py" "$APP_DIR/"
cp -r "$SOURCE_DIR/run.py" "$APP_DIR/"
cp -r "$SOURCE_DIR/requirements.txt" "$APP_DIR/"

# Set up Python virtual environment
echo "[4/7] Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
deactivate

# Set ownership and permissions
echo "[5/7] Setting permissions..."
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod -R 755 "$APP_DIR"
chmod -R 700 "$DATA_DIR"

# Create systemd service
echo "[6/7] Creating systemd service..."
cat > /etc/systemd/system/$APP_NAME.service << EOF
[Unit]
Description=Subscription Tracker
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="DATABASE_PATH=$DATA_DIR/subscriptions.db"
Environment="SECRET_KEY=$(openssl rand -hex 32)"
ExecStart=$APP_DIR/venv/bin/gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 2 'app:create_app()'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "[7/7] Enabling and starting service..."
systemctl daemon-reload
systemctl enable $APP_NAME
systemctl start $APP_NAME

# Check status
echo ""
echo "==================================="
echo "  Deployment Complete!"
echo "==================================="
echo ""
echo "Service: $APP_NAME"
echo "Port: $PORT"
echo "User: $APP_USER"
echo "Directory: $APP_DIR"
echo "Data: $DATA_DIR"
echo ""
echo "Commands:"
echo "  Status:  sudo systemctl status $APP_NAME"
echo "  Logs:    sudo journalctl -u $APP_NAME -f"
echo "  Restart: sudo systemctl restart $APP_NAME"
echo "  Stop:    sudo systemctl stop $APP_NAME"
echo ""
echo "Access: http://$(hostname -I | awk '{print $1}'):$PORT"
