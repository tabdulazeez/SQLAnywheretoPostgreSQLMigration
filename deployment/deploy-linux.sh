#!/bin/bash
# Deployment script for Linux using systemd

set -e

echo "==================================================================="
echo "SQL Anywhere to PostgreSQL Sync Service - Linux Deployment"
echo "==================================================================="

# Variables
SERVICE_NAME="sqlany-postgres-sync"
SERVICE_FILE="deployment/linux-systemd.service"
INSTALL_PATH="/etc/systemd/system/$SERVICE_NAME.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it first."
    exit 1
fi

echo "✓ Configuration file found"

# Update service file with current user
CURRENT_USER=$(logname)
CURRENT_GROUP=$(id -gn $CURRENT_USER)
sed -i "s/your_user/$CURRENT_USER/g" "$SERVICE_FILE"
sed -i "s/your_group/$CURRENT_GROUP/g" "$SERVICE_FILE"

# Copy service file to systemd
echo "Installing service..."
cp "$SERVICE_FILE" "$INSTALL_PATH"
echo "✓ Service file installed to $INSTALL_PATH"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload
echo "✓ Systemd reloaded"

# Enable service
echo "Enabling service..."
systemctl enable "$SERVICE_NAME"
echo "✓ Service enabled"

# Start service
echo "Starting service..."
systemctl start "$SERVICE_NAME"
echo "✓ Service started"

echo ""
echo "==================================================================="
echo "Deployment completed successfully!"
echo "==================================================================="
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status $SERVICE_NAME"
echo "  View logs:     sudo journalctl -u $SERVICE_NAME -f"
echo "  Stop service:  sudo systemctl stop $SERVICE_NAME"
echo "  Restart:       sudo systemctl restart $SERVICE_NAME"
echo "  Disable:       sudo systemctl disable $SERVICE_NAME"
echo "  Uninstall:     sudo systemctl stop $SERVICE_NAME && sudo systemctl disable $SERVICE_NAME && sudo rm $INSTALL_PATH"
echo ""
