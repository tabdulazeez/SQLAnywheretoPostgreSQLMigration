# Scheduling Implementation Summary

This document summarizes the scheduling features added to enable hourly cron or Airflow job execution.

## Files Added

### 1. `sync_job.py` - Standalone Sync Job Script
**Purpose**: Main script for scheduled execution via cron or Airflow

**Features**:
- Runs a single sync operation and exits
- Returns proper exit codes for monitoring (0=success, 1=partial, 2=failure, 3=config error)
- Comprehensive logging to file and stdout
- Can be called directly by cron or Airflow
- Handles all errors gracefully

**Usage**:
```bash
python3 sync_job.py
echo $?  # Check exit code
```

### 2. `cron_sync.sh` - Cron Wrapper Script
**Purpose**: Bash wrapper for cron execution

**Features**:
- Loads environment variables from `.env` file
- Sets up proper Python path and working directory
- Creates timestamped log files
- Cleans up old logs (keeps last 30 days)
- Handles exit codes and optional alerting
- Makes cron execution reliable

**Usage**:
```bash
chmod +x cron_sync.sh
./cron_sync.sh
```

**Crontab Entry** (hourly):
```cron
0 * * * * /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/cron_sync.sh
```

### 3. `airflow_dag_example.py` - Airflow DAG Template
**Purpose**: Apache Airflow DAG for orchestrated scheduling

**Features**:
- Pre-configured for hourly execution
- Health check task before sync
- Post-sync validation task
- Email alerts on failure
- Retry logic with exponential backoff
- Two execution options: Python operator or Bash operator
- Comprehensive configuration examples

**Configuration**:
- Update `SYNC_PROJECT_PATH` to your project directory
- Set `ENVIRONMENT_VARS` with database credentials
- Configure email alerts in `default_args`

**Schedule Options**:
- `'0 * * * *'` - Every hour (default)
- `'*/30 * * * *'` - Every 30 minutes
- `'0 */6 * * *'` - Every 6 hours
- `'@hourly'`, `'@daily'`, etc. - Airflow presets

### 4. `health_check.py` - Health Monitoring Script
**Purpose**: Check sync service health for monitoring systems

**Features**:
- Checks if tables have been synced recently
- Configurable max age threshold (default: 2 hours)
- Returns exit codes compatible with monitoring systems (Nagios, Prometheus, etc.)
- Verbose mode for detailed status
- Can be called by external monitoring tools

**Usage**:
```bash
python3 health_check.py --max-age-hours 2
python3 health_check.py --verbose
```

**Exit Codes**:
- 0 = OK: All tables synced recently
- 1 = WARNING: Some tables haven't synced recently
- 2 = CRITICAL: No recent syncs or all tables failed

### 5. `SCHEDULING_GUIDE.md` - Complete Documentation
**Purpose**: Comprehensive guide for scheduling setup

**Contents**:
- Detailed cron setup instructions
- Complete Airflow setup guide
- Monitoring and troubleshooting
- Best practices for production
- Common issues and solutions
- Example monitoring scripts
- Security considerations

### 6. `QUICKSTART_SCHEDULING.md` - Quick Start Guide
**Purpose**: Get scheduling running in under 5 minutes

**Contents**:
- Minimal steps for cron setup
- Minimal steps for Airflow setup
- Verification steps
- Common schedule patterns
- Quick troubleshooting

## Key Features Implemented

### 1. Exit Code System
All scripts return standardized exit codes:
- **0**: Success - All tables synced successfully
- **1**: Partial success - Some tables failed
- **2**: Failure - All tables failed or critical error
- **3**: Configuration error

This enables:
- Monitoring system integration
- Alerting on failures
- Automated retry logic
- Status tracking

### 2. Comprehensive Logging
- Timestamped log files in `logs/` directory
- Structured logging with table names and metrics
- Per-table sync results
- Error stack traces for debugging
- Log rotation (automatic cleanup of old logs)

### 3. Environment Handling
- Loads `.env` file automatically
- Supports environment variable override
- Works in cron's limited environment
- Compatible with Airflow Variables/Connections

### 4. Error Handling
- Graceful handling of database connection errors
- Per-table error isolation (one failure doesn't stop others)
- Detailed error messages in logs and metadata
- Retry logic in Airflow DAG

### 5. Monitoring Integration
- Health check script for external monitoring
- Sync metadata table for status queries
- Exit codes for alerting systems
- Detailed metrics in logs

## Scheduling Options

### Option 1: Cron (Recommended for Simple Deployments)

**Pros**:
- Simple setup
- Built into Unix/Linux/macOS
- Low resource usage
- No additional dependencies

**Cons**:
- Limited monitoring
- No built-in retry logic
- Manual log management
- Basic scheduling only

**Best For**:
- Simple hourly/daily syncs
- Single server deployments
- Low complexity requirements

### Option 2: Airflow (Recommended for Production)

**Pros**:
- Advanced orchestration
- Web UI for monitoring
- Built-in retry logic
- Email/Slack alerts
- Task dependencies
- Execution history
- Backfill capabilities

**Cons**:
- More complex setup
- Additional infrastructure
- Higher resource usage
- Learning curve

**Best For**:
- Production environments
- Complex scheduling needs
- Team collaboration
- Advanced monitoring requirements

## Common Schedule Patterns

| Pattern | Cron Expression | Airflow Expression | Use Case |
|---------|----------------|-------------------|----------|
| Every hour | `0 * * * *` | `'0 * * * *'` or `'@hourly'` | Standard sync |
| Every 30 min | `*/30 * * * *` | `'*/30 * * * *'` | Frequent updates |
| Every 2 hours | `0 */2 * * *` | `'0 */2 * * *'` | Moderate frequency |
| Every 6 hours | `0 */6 * * *` | `'0 */6 * * *'` | Low frequency |
| Daily at 2 AM | `0 2 * * *` | `'0 2 * * *'` or `'@daily'` | Nightly batch |
| Business hours | `0 9-17 * * 1-5` | `'0 9-17 * * 1-5'` | Weekday only |

## Monitoring & Alerting

### Built-in Monitoring

1. **Sync Metadata Table**:
   ```sql
   SELECT * FROM sync_metadata WHERE status = 'failed';
   ```

2. **Health Check Script**:
   ```bash
   python3 health_check.py --max-age-hours 2
   ```

3. **Status Command**:
   ```bash
   python3 main.py --status
   ```

### External Monitoring Integration

The health check script can be integrated with:
- **Nagios/Icinga**: Use exit codes for service checks
- **Prometheus**: Export metrics via node_exporter
- **Datadog**: Custom check integration
- **PagerDuty**: Alert on critical failures
- **Email/Slack**: Notifications via cron wrapper

### Recommended Alerts

1. **Critical**: Sync failed (exit code 2 or 3)
2. **Warning**: Partial success (exit code 1)
3. **Warning**: No sync in last 2 hours
4. **Info**: Sync completed successfully

## Production Best Practices

### 1. Security
- ✅ Store credentials in `.env` file (not in code)
- ✅ Use least privilege database accounts
- ✅ Enable SSL/TLS for database connections
- ✅ Restrict file permissions on `.env` and scripts
- ✅ Use Airflow Connections for credential management

### 2. Reliability
- ✅ Implement retry logic (built into Airflow DAG)
- ✅ Monitor sync lag and alert on delays
- ✅ Set execution timeouts
- ✅ Handle partial failures gracefully
- ✅ Test in staging before production

### 3. Performance
- ✅ Adjust `SYNC_PARALLEL_TABLES` for optimal throughput
- ✅ Index timestamp columns in source database
- ✅ Use connection pooling
- ✅ Monitor database load during sync
- ✅ Consider off-peak scheduling for large syncs

### 4. Maintenance
- ✅ Rotate logs regularly (built into cron wrapper)
- ✅ Monitor disk space usage
- ✅ Review sync metrics weekly
- ✅ Update dependencies regularly
- ✅ Document any custom configurations

### 5. Disaster Recovery
- ✅ Backup sync metadata table
- ✅ Document recovery procedures
- ✅ Test restore process
- ✅ Keep configuration in version control
- ✅ Have rollback plan for schema changes

## Testing

### Test Sync Job
```bash
# Test sync job directly
python3 sync_job.py

# Check exit code
echo $?

# Verify logs
tail -f sync_service.log
```

### Test Cron Wrapper
```bash
# Make executable
chmod +x cron_sync.sh

# Run manually
./cron_sync.sh

# Check logs
ls -lh logs/
tail -f logs/cron_sync_*.log
```

### Test Health Check
```bash
# Run health check
python3 health_check.py --verbose

# Test with different thresholds
python3 health_check.py --max-age-hours 1
```

### Test Airflow DAG
```bash
# Validate DAG syntax
python3 airflow_dag_example.py

# Test DAG in Airflow
airflow dags test sqlany_to_postgres_sync 2026-02-04

# Trigger manual run
airflow dags trigger sqlany_to_postgres_sync
```

## Troubleshooting

### Cron Not Running
1. Check cron service: `sudo service cron status`
2. Verify crontab: `crontab -l`
3. Check system logs: `tail -f /var/log/syslog | grep CRON`
4. Test wrapper script manually: `./cron_sync.sh`

### Environment Variables Not Loaded
1. Verify `.env` file exists
2. Check file permissions: `ls -la .env`
3. Test loading: `export $(cat .env | xargs); env | grep SQLANY`
4. Use absolute path in wrapper script

### Sync Failures
1. Check logs: `tail -100 sync_service.log`
2. Verify configuration: `python3 -c "from config import Config; Config.validate()"`
3. Test database connections: `python3 test_setup.py`
4. Check sync status: `python3 main.py --status`

### Airflow Issues
1. Check DAG syntax: `python3 airflow_dag_example.py`
2. Verify DAG appears: `airflow dags list | grep sqlany`
3. Check scheduler logs: `tail -f ~/airflow/logs/scheduler/latest/*.log`
4. Test task: `airflow tasks test sqlany_to_postgres_sync health_check 2026-02-04`

## Migration from Daemon Mode

If you're currently using daemon mode (`python main.py --daemon`), here's how to migrate:

### From Daemon to Cron
1. Stop the daemon: `pkill -f "main.py --daemon"`
2. Set up cron as described above
3. Test cron execution
4. Monitor for one cycle to ensure it works

### From Daemon to Airflow
1. Stop the daemon
2. Install and configure Airflow
3. Deploy the DAG
4. Enable and test the DAG
5. Monitor execution in Airflow UI

### Comparison

| Feature | Daemon Mode | Cron | Airflow |
|---------|-------------|------|---------|
| Setup Complexity | Low | Low | High |
| Monitoring | Logs only | Logs + exit codes | Full UI + alerts |
| Retry Logic | Manual | Manual | Automatic |
| Resource Usage | Continuous | Periodic | Periodic + overhead |
| Scalability | Limited | Good | Excellent |
| Best For | Development | Simple production | Enterprise production |

## Next Steps

1. **Choose Your Scheduler**: Decide between cron (simple) or Airflow (advanced)
2. **Follow Quick Start**: Use `QUICKSTART_SCHEDULING.md` for setup
3. **Configure Monitoring**: Set up health checks and alerts
4. **Test Thoroughly**: Run test syncs before production
5. **Document**: Keep notes on your specific configuration
6. **Monitor**: Watch first few executions closely
7. **Optimize**: Adjust settings based on performance

## Support

For detailed instructions, see:
- [QUICKSTART_SCHEDULING.md](QUICKSTART_SCHEDULING.md) - Quick setup
- [SCHEDULING_GUIDE.md](SCHEDULING_GUIDE.md) - Complete guide
- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design

For issues:
1. Check logs in `sync_service.log` and `logs/`
2. Run `python3 main.py --status`
3. Run `python3 health_check.py --verbose`
4. Review troubleshooting sections in guides
