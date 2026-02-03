#!/bin/bash
# Deployment script for macOS using launchd

set -e

echo "==================================================================="
echo "SQL Anywhere to PostgreSQL Sync Service - macOS Deployment"
echo "==================================================================="

# Variables
SERVICE_NAME="com.sync.sqlany-postgres"
PLIST_FILE="deployment/macos-launchd.plist"
INSTALL_PATH="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it first."
    exit 1
fi

echo "✓ Configuration file found"

# Copy plist file to LaunchAgents
echo "Installing service..."
cp "$PLIST_FILE" "$INSTALL_PATH"
echo "✓ Service file installed to $INSTALL_PATH"

# Load the service
echo "Loading service..."
launchctl unload "$INSTALL_PATH" 2>/dev/null || true
launchctl load "$INSTALL_PATH"
echo "✓ Service loaded"

# Start the service
echo "Starting service..."
launchctl start "$SERVICE_NAME"
echo "✓ Service started"

echo ""
echo "==================================================================="
echo "Deployment completed successfully!"
echo "==================================================================="
echo ""
echo "Useful commands:"
echo "  Check status:  launchctl list | grep $SERVICE_NAME"
echo "  View logs:     tail -f sync_service.log"
echo "  Stop service:  launchctl stop $SERVICE_NAME"
echo "  Restart:       launchctl stop $SERVICE_NAME && launchctl start $SERVICE_NAME"
echo "  Uninstall:     launchctl unload $INSTALL_PATH && rm $INSTALL_PATH"
echo ""
