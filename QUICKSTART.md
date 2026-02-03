# Quick Start Guide

This guide will help you get the SQL Anywhere to PostgreSQL sync service up and running quickly.

## Prerequisites

- Python 3.7 or higher
- SQL Anywhere database with a table to sync
- PostgreSQL database
- Network access to both databases

## Step 1: Install Dependencies

```bash
cd /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration
pip install -r requirements.txt
```

## Step 2: Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your database credentials:
   ```bash
   nano .env  # or use your preferred editor
   ```

3. Update these critical settings:
   - `SQLANY_DATABASE`, `SQLANY_USER`, `SQLANY_PASSWORD`
   - `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
   - `SYNC_TABLE_NAME` - the table you want to sync
   - `SYNC_PRIMARY_KEY` - the primary key column name
   - `SYNC_TIMESTAMP_COLUMN` - the column tracking last modification

## Step 3: Prepare Your Tables

### SQL Anywhere (Source)

Your source table must have:
- A primary key column
- A timestamp column that updates on modifications

Example:
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    department VARCHAR(100),
    last_modified TIMESTAMP DEFAULT CURRENT TIMESTAMP
);

-- Add trigger to update last_modified on changes
CREATE TRIGGER update_employees_timestamp
BEFORE UPDATE ON employees
FOR EACH ROW
BEGIN
    SET NEW.last_modified = CURRENT TIMESTAMP;
END;
```

### PostgreSQL (Target)

Create the same table structure in PostgreSQL:
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    department VARCHAR(100),
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The sync service will automatically create the `sync_metadata` table.

## Step 4: Test Your Setup

Run the test script to verify everything is configured correctly:

```bash
python test_setup.py
```

This will check:
- ✓ Configuration validation
- ✓ Database connectivity
- ✓ Table structure
- ✓ Required columns

## Step 5: Run Your First Sync

### Option A: Single Sync (Recommended for Testing)

```bash
python main.py --once
```

This will:
1. Connect to both databases
2. Fetch all records (first sync) or delta records
3. Upsert them to PostgreSQL
4. Show you the results

### Option B: Continuous Daemon

```bash
python main.py --daemon
```

This will run continuously, syncing every 30 seconds (or your configured interval).

Press `Ctrl+C` to stop gracefully.

## Step 6: Monitor Sync Status

Check the current sync status at any time:

```bash
python main.py --status
```

View logs:
```bash
tail -f sync_service.log
```

## Step 7: Deploy as a System Service (Optional)

### On macOS:

```bash
cd deployment
./deploy-macos.sh
```

### On Linux:

```bash
cd deployment
sudo ./deploy-linux.sh
```

## Common Issues

### Issue: "Module not found" errors

**Solution**: Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: "Connection refused" to SQL Anywhere

**Solution**: 
- Verify SQL Anywhere is running
- Check host and port in `.env`
- Ensure network connectivity

### Issue: "Connection refused" to PostgreSQL

**Solution**:
- Verify PostgreSQL is running: `pg_isready`
- Check host and port in `.env`
- Verify user has necessary permissions

### Issue: "Table not found"

**Solution**:
- Verify `SYNC_TABLE_NAME` in `.env` matches your table name
- Check table exists in SQL Anywhere: `SELECT * FROM your_table LIMIT 1`

### Issue: "Column not found"

**Solution**:
- Verify `SYNC_PRIMARY_KEY` and `SYNC_TIMESTAMP_COLUMN` match your table schema
- Run: `python test_setup.py` to see available columns

## Performance Tuning

### For Large Tables

1. **Add indexes** on the timestamp column in SQL Anywhere:
   ```sql
   CREATE INDEX idx_last_modified ON your_table(last_modified);
   ```

2. **Adjust sync interval** in `.env`:
   ```env
   SYNC_INTERVAL_SECONDS=60  # Sync every minute instead of 30 seconds
   ```

3. **Monitor resource usage**:
   ```bash
   # Check logs for sync duration
   tail -f sync_service.log | grep "Sync completed"
   ```

## Next Steps

- Set up monitoring and alerting
- Configure log rotation
- Set up database backups
- Test failover scenarios
- Document your specific table schema

## Getting Help

If you encounter issues:

1. Check the logs: `tail -f sync_service.log`
2. Run tests: `python test_setup.py`
3. Check sync status: `python main.py --status`
4. Review the full README.md for detailed documentation

## Example Workflow

Here's a complete example workflow:

```bash
# 1. Install and configure
pip install -r requirements.txt
cp .env.example .env
nano .env  # Edit configuration

# 2. Test setup
python test_setup.py

# 3. Run first sync
python main.py --once

# 4. Check results
python main.py --status

# 5. If successful, run as daemon
python main.py --daemon

# 6. In another terminal, monitor logs
tail -f sync_service.log
```

That's it! Your sync service should now be running. 🎉
