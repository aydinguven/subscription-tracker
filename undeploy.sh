#!/bin/bash
# Subscription Tracker Uninstall Script
# Run as root: sudo bash undeploy.sh

set -e

APP_NAME="subscription-tracker"
APP_USER="subscription-tracker-user"
APP_DIR="/opt/subscription-tracker"

echo "==================================="
echo "  Subscription Tracker Uninstall"
echo "==================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash undeploy.sh)"
    exit 1
fi

echo ""
read -p "This will remove the service and files. Continue? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "[1/4] Stopping and disabling service..."
systemctl stop $APP_NAME 2>/dev/null || true
systemctl disable $APP_NAME 2>/dev/null || true
rm -f /etc/systemd/system/$APP_NAME.service
systemctl daemon-reload

echo "[2/4] Removing application directory..."
rm -rf "$APP_DIR"

echo "[3/4] Removing application user..."
userdel "$APP_USER" 2>/dev/null || true

echo "[4/4] Done!"
echo ""
echo "Subscription Tracker has been uninstalled."
echo "Note: Any data in $APP_DIR/data has been removed."
