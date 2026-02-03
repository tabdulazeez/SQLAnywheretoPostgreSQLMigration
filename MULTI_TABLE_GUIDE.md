# Multi-Table Sync Guide

This guide explains how to configure and use the multi-table synchronization feature to sync 74 (or more) tables from SQL Anywhere to PostgreSQL.

## Overview

The multi-table sync service supports:
- ✅ **Parallel Syncing**: Sync multiple tables simultaneously (configurable workers)
- ✅ **Per-Table Configuration**: Different primary keys and timestamp columns per table
- ✅ **Flexible Configuration**: JSON file, environment variables, or comma-separated lists
- ✅ **Selective Sync**: Enable/disable specific tables
- ✅ **Batch Processing**: Optional batch size for large tables
- ✅ **Independent Tracking**: Each table has its own sync metadata

## Configuration Methods

### Method 1: JSON Configuration File (Recommended for 74 Tables)

Create a `tables_config.json` file:

```json
{
  "tables": [
    {
      "name": "employees",
      "primary_key": "id",
      "timestamp_column": "last_modified",
      "enabled": true,
      "batch_size": 1000
    },
    {
      "name": "customers",
      "primary_key": "customer_id",
      "timestamp_column": "updated_at",
      "enabled": true
    },
    {
      "name": "orders",
      "primary_key": "order_id",
      "timestamp_column": "modified_date",
      "enabled": true,
      "batch_size": 5000
    }
    // ... add all 74 tables
  ]
}
```

**Field Descriptions:**
- `name` (required): Table name
- `primary_key` (optional, default: "id"): Primary key column name
- `timestamp_column` (optional, default: "last_modified"): Timestamp column for delta sync
- `enabled` (optional, default: true): Whether to sync this table
- `batch_size` (optional): Process records in batches (useful for large tables)

**Configure in .env:**
```bash
SYNC_CONFIG_FILE=tables_config.json
SYNC_PARALLEL_TABLES=5  # Sync 5 tables at a time
```

### Method 2: Comma-Separated List (Simple, Same Config for All)

For tables with the same structure:

```bash
# .env
SYNC_TABLES=employees,departments,customers,orders,products,inventory
SYNC_PRIMARY_KEY=id
SYNC_TIMESTAMP_COLUMN=last_modified
SYNC_PARALLEL_TABLES=5
```

This syncs all listed tables with the same primary key and timestamp column.

### Method 3: JSON in Environment Variable

For dynamic configuration:

```bash
SYNC_TABLES_JSON='[
  {"name":"employees","primary_key":"id","timestamp_column":"last_modified"},
  {"name":"customers","primary_key":"customer_id","timestamp_column":"updated_at"}
]'
```

### Method 4: Legacy Single Table (Backward Compatible)

```bash
SYNC_TABLE_NAME=employees
SYNC_PRIMARY_KEY=id
SYNC_TIMESTAMP_COLUMN=last_modified
```

## Quick Start for 74 Tables

### 1. Prepare Your Configuration

Use the provided `tables_config.json` as a template and customize it:

```bash
# Edit tables_config.json with your actual table names
nano tables_config.json
```

Update each table entry with:
- Correct table name
- Correct primary key column
- Correct timestamp column
- Enable/disable as needed

### 2. Configure Environment

```bash
cp .env.example .env
nano .env
```

Set:
```bash
SYNC_CONFIG_FILE=tables_config.json
SYNC_PARALLEL_TABLES=10  # Adjust based on your server capacity
SYNC_INTERVAL_SECONDS=60  # Sync every minute
```

### 3. List Configured Tables

Verify your configuration:

```bash
python main.py --list-tables
```

Output:
```
Configured Tables (74 total, 74 enabled)
==================================================================================
Table Name                     Primary Key     Timestamp Column     Enabled
----------------------------------------------------------------------------------
employees                      id              last_modified        ✓ True
departments                    id              last_modified        ✓ True
customers                      customer_id     updated_at           ✓ True
...
```

### 4. Test Sync

Run a one-time sync to test:

```bash
python main.py --once
```

Output:
```
✓ Configuration validated successfully
✓ Loaded 74 enabled tables for sync
✓ Database connections initialized
✓ Multi-table sync service initialized

Starting one-time sync for 74 tables...
======================================================================
...
✓ Sync completed successfully!
  Total tables:        74
  Successful tables:   74
  Total records:       15,234
  Duration:            12.45 seconds

Per-Table Results:
----------------------------------------------------------------------
  ✓ employees                      150 records in   0.45s
  ✓ departments                     25 records in   0.12s
  ✓ customers                      523 records in   1.23s
  ...
```

### 5. Check Status

View sync status for all tables:

```bash
python main.py --status
```

Or for a specific table:

```bash
python main.py --status --table employees
```

### 6. Run as Daemon

Once tested, run continuously:

```bash
python main.py --daemon
```

## Performance Tuning

### Parallel Workers

Adjust based on your database server capacity:

```bash
# Conservative (low server load)
SYNC_PARALLEL_TABLES=3

# Moderate (balanced)
SYNC_PARALLEL_TABLES=5

# Aggressive (high performance, requires good hardware)
SYNC_PARALLEL_TABLES=10
```

**Guidelines:**
- Start with 5 workers
- Monitor CPU and database connections
- Increase if resources are underutilized
- Decrease if you see connection errors or timeouts

### Batch Size

For tables with millions of records, use batch processing:

```json
{
  "name": "large_table",
  "primary_key": "id",
  "timestamp_column": "last_modified",
  "batch_size": 10000
}
```

**Batch Size Guidelines:**
- Small tables (<10K rows): No batch size needed
- Medium tables (10K-100K rows): batch_size = 5000
- Large tables (100K-1M rows): batch_size = 10000
- Very large tables (>1M rows): batch_size = 50000

### Sync Interval

Adjust based on data freshness requirements:

```bash
# Real-time (every 30 seconds)
SYNC_INTERVAL_SECONDS=30

# Near real-time (every 2 minutes)
SYNC_INTERVAL_SECONDS=120

# Periodic (every 5 minutes)
SYNC_INTERVAL_SECONDS=300
```

## Advanced Features

### Selective Table Sync

Disable specific tables without removing them from config:

```json
{
  "name": "archived_data",
  "primary_key": "id",
  "timestamp_column": "last_modified",
  "enabled": false
}
```

### Sequential vs Parallel Sync

By default, tables sync in parallel. For testing or debugging, you can modify the code to sync sequentially:

```python
# In daemon.py or when calling sync_all()
result = self.sync_service.sync_all(parallel=False)
```

### Per-Table Monitoring

Monitor specific tables:

```bash
# Watch logs for a specific table
tail -f sync_service.log | grep "\[employees\]"

# Check status for specific table
python main.py --status --table employees
```

## Troubleshooting

### Issue: Too Many Database Connections

**Symptoms**: "Too many connections" errors

**Solution**: Reduce parallel workers
```bash
SYNC_PARALLEL_TABLES=3
```

### Issue: Some Tables Failing

**Symptoms**: Partial sync success

**Solution**: Check logs for specific table errors
```bash
python main.py --status
# Look for failed tables

# Check specific table
python main.py --status --table failed_table_name
```

### Issue: Slow Sync Performance

**Symptoms**: Sync takes too long

**Solutions**:
1. Increase parallel workers (if resources available)
2. Add batch_size for large tables
3. Add indexes on timestamp columns
4. Check network latency between databases

### Issue: Memory Usage Too High

**Symptoms**: High memory consumption

**Solutions**:
1. Reduce parallel workers
2. Add batch_size to process records in smaller chunks
3. Reduce sync interval to process fewer records per sync

## Example: Complete 74-Table Setup

### 1. tables_config.json

```json
{
  "tables": [
    {"name": "employees", "primary_key": "id", "timestamp_column": "last_modified"},
    {"name": "departments", "primary_key": "id", "timestamp_column": "last_modified"},
    {"name": "customers", "primary_key": "customer_id", "timestamp_column": "updated_at"},
    // ... all 74 tables
  ]
}
```

### 2. .env

```bash
# Database Configuration
SQLANY_HOST=sqlany-server.company.com
SQLANY_PORT=2638
SQLANY_DATABASE=production_db
SQLANY_USER=sync_user
SQLANY_PASSWORD=secure_password

POSTGRES_HOST=postgres-server.company.com
POSTGRES_PORT=5432
POSTGRES_DATABASE=analytics_db
POSTGRES_USER=sync_user
POSTGRES_PASSWORD=secure_password

# Sync Configuration
SYNC_INTERVAL_SECONDS=60
SYNC_PARALLEL_TABLES=8
SYNC_CONFIG_FILE=tables_config.json

# Logging
LOG_LEVEL=INFO
LOG_FILE=sync_service.log
```

### 3. Run Commands

```bash
# Test configuration
python main.py --list-tables

# Test sync
python main.py --once

# Check results
python main.py --status

# Deploy as daemon
python main.py --daemon
```

## Monitoring Dashboard

Create a simple monitoring script:

```bash
#!/bin/bash
# monitor_sync.sh

while true; do
  clear
  echo "==================================================================="
  echo "Multi-Table Sync Monitor - $(date)"
  echo "==================================================================="
  python main.py --status
  sleep 30
done
```

Run it:
```bash
chmod +x monitor_sync.sh
./monitor_sync.sh
```

## Best Practices

1. **Start Small**: Test with 5-10 tables first, then scale to 74
2. **Monitor Resources**: Watch CPU, memory, and database connections
3. **Use Indexes**: Ensure timestamp columns are indexed in both databases
4. **Log Rotation**: Set up log rotation for `sync_service.log`
5. **Alerting**: Monitor for failed syncs and set up alerts
6. **Backup**: Always backup before first sync
7. **Test Recovery**: Test that sync resumes correctly after restart
8. **Document**: Keep track of which tables are synced and why

## Migration from Single Table

If you're upgrading from single-table sync:

1. **Backup** your current `.env` file
2. **Create** `tables_config.json` with all tables
3. **Update** `.env` to use `SYNC_CONFIG_FILE`
4. **Test** with `python main.py --list-tables`
5. **Run** `python main.py --once` to test
6. **Deploy** `python main.py --daemon`

The service maintains backward compatibility, so existing metadata is preserved.

## Summary

For 74 tables:
- ✅ Use `tables_config.json` for configuration
- ✅ Set `SYNC_PARALLEL_TABLES=5-10` based on resources
- ✅ Use `batch_size` for large tables
- ✅ Monitor with `--status` and logs
- ✅ Start with `--once`, then deploy with `--daemon`

The multi-table sync service is designed to handle dozens of tables efficiently with minimal configuration!
