#!/bin/bash

# Cron wrapper script for SQL Anywhere to PostgreSQL sync
# This ensures proper environment setup when running via cron

# Set project directory
PROJECT_DIR="/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration"
cd "$PROJECT_DIR" || exit 1

# Load environment variables from .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
fi

# Set Python path (adjust if needed)
PYTHON_BIN="/usr/local/bin/python3"

# Set log file with timestamp
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CRON_LOG="$LOG_DIR/cron_sync_$TIMESTAMP.log"

# Run sync job and capture exit code
echo "Starting sync job at $(date)" >> "$CRON_LOG"
$PYTHON_BIN "$PROJECT_DIR/sync_job.py" >> "$CRON_LOG" 2>&1
EXIT_CODE=$?

echo "Sync job completed with exit code $EXIT_CODE at $(date)" >> "$CRON_LOG"

# Optional: Send alert on failure
if [ $EXIT_CODE -eq 2 ] || [ $EXIT_CODE -eq 3 ]; then
    echo "CRITICAL: Sync job failed with exit code $EXIT_CODE" >> "$CRON_LOG"
    # Uncomment to send email alert:
    # echo "Sync job failed. Check logs at $CRON_LOG" | mail -s "Sync Job Failed" your-email@example.com
fi

# Clean up old logs (keep last 30 days)
find "$LOG_DIR" -name "cron_sync_*.log" -mtime +30 -delete

exit $EXIT_CODE
