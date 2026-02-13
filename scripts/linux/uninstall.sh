#!/bin/bash
#
# Subscription Tracker - Uninstall Script
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

INSTALL_DIR="/opt/subscription-tracker"
SERVICE_USER="subtracker"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo "This will remove Subscription Tracker from your system."
read -p "Do you want to keep the database? [Y/n]: " keep_data

# Stop and disable service
if systemctl is-active --quiet subscription-tracker 2>/dev/null; then
    echo "Stopping service..."
    systemctl stop subscription-tracker
fi

if systemctl is-enabled --quiet subscription-tracker 2>/dev/null; then
    echo "Disabling service..."
    systemctl disable subscription-tracker
fi

# Remove service file
if [ -f /etc/systemd/system/subscription-tracker.service ]; then
    echo "Removing systemd service..."
    rm /etc/systemd/system/subscription-tracker.service
    systemctl daemon-reload
fi

# Backup or remove data
if [[ ! "$keep_data" =~ ^[Nn] ]]; then
    if [ -d "$INSTALL_DIR/data" ]; then
        BACKUP_DIR="/tmp/subscription-tracker-backup-$(date +%Y%m%d%H%M%S)"
        echo "Backing up data to $BACKUP_DIR..."
        mkdir -p "$BACKUP_DIR"
        cp -r "$INSTALL_DIR/data" "$BACKUP_DIR/"
        echo -e "${GREEN}Data backed up to: $BACKUP_DIR${NC}"
    fi
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
fi

# Remove user
if id "$SERVICE_USER" &>/dev/null; then
    echo "Removing service user..."
    userdel "$SERVICE_USER" 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}Subscription Tracker has been uninstalled.${NC}"
