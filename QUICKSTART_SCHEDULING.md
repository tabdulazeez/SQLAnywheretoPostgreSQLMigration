# Quick Start: Hourly Scheduling

This guide will get you up and running with hourly sync scheduling in under 5 minutes.

## Prerequisites

- ✅ Project configured with `.env` file
- ✅ Database connections tested
- ✅ Tables configured in `tables_config.json`
- ✅ Manual sync tested with `python3 main.py --once`

## Option 1: Cron (Simplest)

### 1. Make scripts executable

```bash
cd /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration
chmod +x sync_job.py cron_sync.sh health_check.py
```

### 2. Test the sync job

```bash
python3 sync_job.py
echo "Exit code: $?"
```

Expected output: Exit code 0 (success) or 1 (partial success)

### 3. Schedule hourly cron job

```bash
crontab -e
```

Add this line (runs every hour at minute 0):

```cron
0 * * * * /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh
```

Save and exit.

### 4. Verify cron is scheduled

```bash
crontab -l
```

### 5. Monitor logs

```bash
# Wait for next hour, then check logs
tail -f /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/logs/cron_sync_*.log
```

**Done! Your sync is now running hourly.**

---

## Option 2: Airflow (Advanced)

### 1. Install Airflow

```bash
pip install apache-airflow
airflow db init
```

### 2. Copy DAG file

```bash
AIRFLOW_HOME=~/airflow
mkdir -p $AIRFLOW_HOME/dags
cp airflow_dag_example.py $AIRFLOW_HOME/dags/sqlany_postgres_sync.py
```

### 3. Edit DAG configuration

```bash
nano $AIRFLOW_HOME/dags/sqlany_postgres_sync.py
```

Update these lines:
- `SYNC_PROJECT_PATH` - Set to your project path
- `ENVIRONMENT_VARS` - Add your database credentials
- `default_args['email']` - Add your email for alerts

### 4. Start Airflow

```bash
# Terminal 1: Start webserver
airflow webserver --port 8080

# Terminal 2: Start scheduler
airflow scheduler
```

### 5. Enable DAG

1. Open http://localhost:8080
2. Find `sqlany_to_postgres_sync` DAG
3. Toggle it to "On"
4. Click "Trigger DAG" to test

**Done! Your sync is now running hourly via Airflow.**

---

## Verification

### Check sync status

```bash
python3 main.py --status
```

Expected output:
```
Sync Status for All Tables (74 tables)
==================================================================================
Table Name                     Status     Records    Last Sync           
----------------------------------------------------------------------------------
employees                      ✓ success  1234       2026-02-04 03:00:00
departments                    ✓ success  45         2026-02-04 03:00:01
...
```

### Check health

```bash
python3 health_check.py --verbose
```

Expected output:
```
OK: All 74 tables synced within last 2 hours
```

### View logs

```bash
# Cron logs
tail -f logs/cron_sync_*.log

# Application logs
tail -f sync_service.log

# Airflow logs (if using Airflow)
tail -f ~/airflow/logs/dag_id=sqlany_to_postgres_sync/*/task_id=sync_tables_python/*.log
```

---

## Common Schedules

Edit your crontab (`crontab -e`) or Airflow DAG's `schedule_interval`:

| Frequency | Cron Expression | Airflow Expression |
|-----------|----------------|-------------------|
| Every hour | `0 * * * *` | `'0 * * * *'` or `'@hourly'` |
| Every 30 min | `*/30 * * * *` | `'*/30 * * * *'` |
| Every 2 hours | `0 */2 * * *` | `'0 */2 * * *'` |
| Every 6 hours | `0 */6 * * *` | `'0 */6 * * *'` |
| Daily at 2 AM | `0 2 * * *` | `'0 2 * * *'` or `'@daily'` |
| Business hours | `0 9-17 * * 1-5` | `'0 9-17 * * 1-5'` |

---

## Troubleshooting

### Cron job not running?

```bash
# Check cron service
sudo service cron status  # Linux
# or check system logs on macOS

# Verify crontab
crontab -l

# Test wrapper script manually
./cron_sync.sh

# Check permissions
ls -la cron_sync.sh sync_job.py
```

### Sync failing?

```bash
# Check configuration
python3 -c "from config import Config; Config.validate(); print('OK')"

# Test database connections
python3 test_setup.py

# View detailed logs
tail -100 sync_service.log

# Check specific table status
python3 main.py --status --table employees
```

### Need help?

See the full [SCHEDULING_GUIDE.md](SCHEDULING_GUIDE.md) for detailed troubleshooting and best practices.

---

## Next Steps

1. **Set up monitoring** - Configure alerts for failures
2. **Review logs** - Check sync performance and errors
3. **Optimize** - Adjust `SYNC_PARALLEL_TABLES` for performance
4. **Monitor resources** - Watch CPU, memory, and network usage
5. **Plan maintenance** - Schedule regular health checks

For detailed information, see:
- [SCHEDULING_GUIDE.md](SCHEDULING_GUIDE.md) - Complete scheduling documentation
- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
