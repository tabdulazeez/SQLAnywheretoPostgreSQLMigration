# Scheduling Guide: Cron & Airflow

This guide explains how to schedule the SQL Anywhere to PostgreSQL sync service to run hourly using either **cron** or **Apache Airflow**.

## Table of Contents
- [Overview](#overview)
- [Option 1: Cron Scheduling](#option-1-cron-scheduling)
- [Option 2: Airflow Scheduling](#option-2-airflow-scheduling)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

The sync service can be scheduled to run automatically at regular intervals. Two main options are available:

1. **Cron** - Simple, lightweight, built into Unix/Linux systems
2. **Airflow** - Advanced orchestration with monitoring, retries, and alerting

### Exit Codes

The `sync_job.py` script returns the following exit codes for monitoring:

| Exit Code | Status | Description |
|-----------|--------|-------------|
| 0 | Success | All tables synced successfully |
| 1 | Partial Success | Some tables failed, but at least one succeeded |
| 2 | Failure | All tables failed or critical error occurred |
| 3 | Configuration Error | Missing or invalid configuration |

---

## Option 1: Cron Scheduling

### Prerequisites

1. Unix/Linux/macOS system with cron installed
2. Python 3.7+ installed
3. Project dependencies installed (`pip install -r requirements.txt`)
4. `.env` file configured with database credentials

### Setup Steps

#### 1. Make the sync job executable

```bash
cd /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration
chmod +x sync_job.py
```

#### 2. Test the sync job manually

```bash
python3 sync_job.py
echo "Exit code: $?"
```

Verify that:
- The script runs without errors
- Exit code is 0 (success) or 1 (partial success)
- Logs are written to the configured log file

#### 3. Create a cron wrapper script (recommended)

Create a wrapper script to handle environment setup:

```bash
cat > /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh << 'EOF'
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
EOF

chmod +x /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh
```

#### 4. Configure cron job

Edit your crontab:

```bash
crontab -e
```

Add one of the following entries:

**Run every hour at minute 0:**
```cron
0 * * * * /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh
```

**Run every 30 minutes:**
```cron
*/30 * * * * /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh
```

**Run every 2 hours:**
```cron
0 */2 * * * /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh
```

**Run every hour during business hours (9 AM - 5 PM, Mon-Fri):**
```cron
0 9-17 * * 1-5 /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh
```

#### 5. Verify cron job is scheduled

```bash
crontab -l
```

#### 6. Monitor cron execution

Check cron logs:
```bash
# macOS
tail -f /var/log/system.log | grep cron

# Linux
tail -f /var/log/syslog | grep CRON
```

Check sync job logs:
```bash
tail -f /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/logs/cron_sync_*.log
```

### Cron Best Practices

1. **Use absolute paths** - Cron has a limited PATH environment
2. **Redirect output** - Capture stdout and stderr to log files
3. **Set environment variables** - Cron doesn't load your shell profile
4. **Test the wrapper script** - Run it manually before scheduling
5. **Monitor logs** - Set up log rotation and monitoring
6. **Handle failures** - Implement alerting for critical failures

---

## Option 2: Airflow Scheduling

### Prerequisites

1. Apache Airflow installed and configured
2. Python 3.7+ with project dependencies
3. Access to Airflow web UI and DAGs folder

### Setup Steps

#### 1. Install Airflow (if not already installed)

```bash
# Install Airflow (example for Airflow 2.x)
pip install apache-airflow

# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

#### 2. Copy DAG file to Airflow

```bash
# Find your Airflow DAGs folder
AIRFLOW_HOME=$(airflow config get-value core dags_folder)
echo "Airflow DAGs folder: $AIRFLOW_HOME"

# Copy the example DAG
cp /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/airflow_dag_example.py \
   $AIRFLOW_HOME/sqlany_postgres_sync_dag.py
```

#### 3. Configure the DAG

Edit `$AIRFLOW_HOME/sqlany_postgres_sync_dag.py`:

```python
# Update project path
SYNC_PROJECT_PATH = '/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration'

# Update environment variables with your credentials
ENVIRONMENT_VARS = {
    'SQLANY_HOST': 'your-sqlany-host',
    'SQLANY_DATABASE': 'your-database',
    # ... etc
}

# Update email for alerts
default_args = {
    'email': ['your-email@example.com'],
    'email_on_failure': True,
}
```

#### 4. Install dependencies in Airflow environment

```bash
# Activate Airflow's Python environment (if using virtualenv)
source ~/airflow-venv/bin/activate

# Install sync service dependencies
cd /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration
pip install -r requirements.txt
```

#### 5. Start Airflow services

```bash
# Start Airflow webserver (in one terminal)
airflow webserver --port 8080

# Start Airflow scheduler (in another terminal)
airflow scheduler
```

#### 6. Enable the DAG in Airflow UI

1. Open browser to `http://localhost:8080`
2. Login with your admin credentials
3. Find the DAG: `sqlany_to_postgres_sync`
4. Toggle the DAG to "On" state
5. Trigger a manual run to test

#### 7. Monitor DAG execution

- **Airflow UI**: View task logs, execution history, and metrics
- **Task Logs**: Click on task instances to view detailed logs
- **Email Alerts**: Configure SMTP in `airflow.cfg` for email notifications

### Airflow Configuration Options

#### Change Schedule Interval

Edit the DAG file and modify `schedule_interval`:

```python
# Hourly (default)
schedule_interval='0 * * * *'

# Every 30 minutes
schedule_interval='*/30 * * * *'

# Every 6 hours
schedule_interval='0 */6 * * *'

# Daily at 2 AM
schedule_interval='0 2 * * *'

# Using Airflow presets
schedule_interval='@hourly'  # or @daily, @weekly, @monthly
```

#### Configure Retries

```python
default_args = {
    'retries': 3,  # Number of retries
    'retry_delay': timedelta(minutes=5),  # Delay between retries
    'retry_exponential_backoff': True,  # Exponential backoff
}
```

#### Set Execution Timeout

```python
default_args = {
    'execution_timeout': timedelta(hours=2),  # Max execution time
}
```

### Using Airflow Variables (Recommended)

Instead of hardcoding credentials in the DAG, use Airflow Variables:

```python
from airflow.models import Variable

# In your DAG
SQLANY_HOST = Variable.get("sqlany_host")
SQLANY_PASSWORD = Variable.get("sqlany_password", default_var=None)
```

Set variables via UI or CLI:
```bash
airflow variables set sqlany_host "your-host"
airflow variables set sqlany_password "your-password"
```

### Using Airflow Connections (Most Secure)

Store database connections securely:

```bash
# Add SQL Anywhere connection
airflow connections add 'sqlany_conn' \
    --conn-type 'generic' \
    --conn-host 'your-host' \
    --conn-port 2638 \
    --conn-login 'your-user' \
    --conn-password 'your-password' \
    --conn-schema 'your-database'

# Add PostgreSQL connection
airflow connections add 'postgres_conn' \
    --conn-type 'postgres' \
    --conn-host 'your-host' \
    --conn-port 5432 \
    --conn-login 'your-user' \
    --conn-password 'your-password' \
    --conn-schema 'your-database'
```

---

## Monitoring & Troubleshooting

### Check Sync Status

```bash
# View current status of all tables
python3 main.py --status

# View status of specific table
python3 main.py --status --table employees
```

### Query Sync Metadata

```sql
-- PostgreSQL: Check last sync times
SELECT 
    table_name,
    last_sync_timestamp,
    last_sync_completed_at,
    records_synced,
    status,
    EXTRACT(EPOCH FROM (NOW() - last_sync_completed_at)) / 3600 as hours_since_sync
FROM sync_metadata
ORDER BY last_sync_completed_at DESC;

-- Find failed syncs
SELECT * FROM sync_metadata WHERE status = 'failed';

-- Check sync lag
SELECT 
    table_name,
    NOW() - last_sync_completed_at as sync_lag
FROM sync_metadata
WHERE status = 'success'
ORDER BY sync_lag DESC;
```

### Common Issues

#### Issue: Cron job not running

**Solutions:**
1. Check cron service is running: `sudo service cron status`
2. Verify crontab entry: `crontab -l`
3. Check system logs: `tail -f /var/log/syslog | grep CRON`
4. Ensure script has execute permissions: `chmod +x cron_sync.sh`

#### Issue: Environment variables not loaded

**Solutions:**
1. Use absolute path to `.env` file in wrapper script
2. Explicitly export variables in cron wrapper
3. Source `.env` file: `export $(cat .env | xargs)`

#### Issue: Python module not found

**Solutions:**
1. Use absolute path to Python interpreter
2. Set PYTHONPATH in wrapper script: `export PYTHONPATH=/path/to/project`
3. Install dependencies in system Python or specify virtualenv

#### Issue: Database connection timeout

**Solutions:**
1. Increase connection timeout in database configuration
2. Check network connectivity from cron/Airflow server
3. Verify firewall rules allow database connections
4. Use connection pooling settings in `database.py`

#### Issue: Airflow DAG not appearing

**Solutions:**
1. Check DAG file syntax: `python3 sqlany_postgres_sync_dag.py`
2. Verify file is in correct DAGs folder
3. Check Airflow scheduler logs: `tail -f ~/airflow/logs/scheduler/latest/*.log`
4. Refresh DAGs in UI or restart scheduler

---

## Best Practices

### 1. Logging

- **Rotate logs** - Use logrotate or custom cleanup scripts
- **Structured logging** - Include timestamps, table names, record counts
- **Log levels** - Use INFO for normal operations, ERROR for failures
- **Centralized logging** - Send logs to centralized system (ELK, Splunk, etc.)

### 2. Monitoring

- **Set up alerts** - Email/Slack notifications on failures
- **Track metrics** - Monitor sync duration, record counts, error rates
- **Dashboard** - Create monitoring dashboard (Grafana, Datadog, etc.)
- **Health checks** - Implement endpoint for external monitoring

### 3. Error Handling

- **Retry logic** - Implement retries for transient failures
- **Partial failures** - Continue syncing other tables if one fails
- **Error notifications** - Alert on critical failures immediately
- **Graceful degradation** - Handle database unavailability

### 4. Performance

- **Parallel execution** - Sync multiple tables concurrently
- **Batch processing** - Use appropriate batch sizes for large tables
- **Indexing** - Ensure timestamp columns are indexed
- **Connection pooling** - Reuse database connections

### 5. Security

- **Credentials** - Never hardcode credentials in code
- **Environment variables** - Use `.env` files or secret management
- **Least privilege** - Use database accounts with minimal permissions
- **Encryption** - Use SSL/TLS for database connections
- **Audit logs** - Track who runs syncs and when

### 6. Maintenance

- **Regular testing** - Test sync jobs in staging environment
- **Backup strategy** - Backup before major syncs
- **Schema changes** - Handle DDL changes gracefully
- **Capacity planning** - Monitor disk space and database growth
- **Documentation** - Keep runbooks and troubleshooting guides updated

---

## Example Monitoring Scripts

### Check if sync is running on schedule

```bash
#!/bin/bash
# check_sync_schedule.sh

# Check if last sync was within expected interval (e.g., 2 hours)
EXPECTED_INTERVAL_HOURS=2

LAST_SYNC=$(psql -h localhost -U postgres -d your_db -t -c \
    "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(last_sync_completed_at))) / 3600 FROM sync_metadata WHERE status='success'")

if (( $(echo "$LAST_SYNC > $EXPECTED_INTERVAL_HOURS" | bc -l) )); then
    echo "WARNING: Last successful sync was $LAST_SYNC hours ago"
    exit 1
else
    echo "OK: Last sync was $LAST_SYNC hours ago"
    exit 0
fi
```

### Alert on failed tables

```bash
#!/bin/bash
# alert_failed_tables.sh

FAILED_COUNT=$(psql -h localhost -U postgres -d your_db -t -c \
    "SELECT COUNT(*) FROM sync_metadata WHERE status='failed'")

if [ "$FAILED_COUNT" -gt 0 ]; then
    FAILED_TABLES=$(psql -h localhost -U postgres -d your_db -t -c \
        "SELECT string_agg(table_name, ', ') FROM sync_metadata WHERE status='failed'")
    
    echo "ALERT: $FAILED_COUNT tables failed to sync: $FAILED_TABLES"
    # Send alert (email, Slack, PagerDuty, etc.)
    exit 1
else
    echo "OK: All tables synced successfully"
    exit 0
fi
```

---

## Additional Resources

- [Cron Documentation](https://man7.org/linux/man-pages/man5/crontab.5.html)
- [Crontab Guru](https://crontab.guru/) - Cron schedule expression editor
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

---

## Support

For issues or questions:
1. Check logs in `sync_service.log` or `logs/` directory
2. Run `python3 main.py --status` to check sync status
3. Review this guide's troubleshooting section
4. Check project documentation in `README.md`
