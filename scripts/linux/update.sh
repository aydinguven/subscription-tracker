#!/bin/bash
# Subscription Tracker Update Script
# Run as root: sudo bash update.sh

set -e

APP_NAME="subscription-tracker"
APP_DIR="/opt/subscription-tracker"
SOURCE_DIR="/home/aydin/subscription-tracker"

echo "==================================="
echo "  Subscription Tracker Update"
echo "==================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash update.sh)"
    exit 1
fi

# Pull latest from git
echo "[1/4] Pulling latest changes..."
cd "$SOURCE_DIR"
git pull

# Copy updated files
echo "[2/4] Copying updated files..."
cp -r "$SOURCE_DIR/app" "$APP_DIR/"
cp "$SOURCE_DIR/config.py" "$APP_DIR/"
cp "$SOURCE_DIR/run.py" "$APP_DIR/"
cp "$SOURCE_DIR/requirements.txt" "$APP_DIR/"
cp "$SOURCE_DIR/scripts/linux/manage_users.sh" "$APP_DIR/"
chmod +x "$APP_DIR/manage_users.sh"

# Update dependencies if requirements changed
echo "[3/4] Updating dependencies..."
cd "$APP_DIR"
source venv/bin/activate
pip install -r requirements.txt --quiet
deactivate

# Fix permissions
chown -R subscription-tracker-user:subscription-tracker-user "$APP_DIR"

# Restart service
echo "[4/4] Restarting service..."
systemctl restart $APP_NAME

echo ""
echo "Update complete!"
systemctl status $APP_NAME --no-pager
