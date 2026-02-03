# SQL Anywhere to PostgreSQL Sync Service

A Python background daemon service that continuously syncs records from SQL Anywhere to PostgreSQL using delta synchronization based on a `last_modified` timestamp.

## Features

- ✅ **Multi-Table Support**: Sync 74+ tables simultaneously with parallel processing
- ✅ **Delta Synchronization**: Only syncs records modified since the last sync
- ✅ **Upsert Logic**: Uses PostgreSQL's `ON CONFLICT` clause for efficient upserts
- ✅ **State Persistence**: Tracks sync state in a metadata table for resume capability
- ✅ **Background Daemon**: Runs continuously with configurable sync intervals
- ✅ **Parallel Processing**: Configurable number of tables to sync simultaneously
- ✅ **Per-Table Configuration**: Different primary keys and timestamp columns per table
- ✅ **Error Handling**: Comprehensive error handling and logging
- ✅ **Graceful Shutdown**: Handles SIGTERM and SIGINT signals properly
- ✅ **SQLAlchemy**: Uses SQLAlchemy ORM for database operations

## Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│  SQL Anywhere   │────────>│ Sync Service │────────>│   PostgreSQL    │
│    (Source)     │         │              │         │    (Target)     │
└─────────────────┘         └──────────────┘         └─────────────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │   Metadata   │
                            │    Table     │
                            └──────────────┘
```

## Installation

1. **Clone the repository**:
   ```bash
   cd /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

## Configuration

### Single Table (Simple Setup)

Edit the `.env` file with your database credentials and sync settings:

```env
# SQL Anywhere Connection
SQLANY_HOST=localhost
SQLANY_PORT=2638
SQLANY_DATABASE=your_database
SQLANY_USER=your_user
SQLANY_PASSWORD=your_password

# PostgreSQL Connection
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=your_database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# Sync Configuration (Single Table)
SYNC_INTERVAL_SECONDS=30
SYNC_TABLE_NAME=your_table_name
SYNC_PRIMARY_KEY=id
SYNC_TIMESTAMP_COLUMN=last_modified

# Logging
LOG_LEVEL=INFO
LOG_FILE=sync_service.log
```

### Multi-Table (74+ Tables)

For syncing multiple tables, use a JSON configuration file:

```env
# Sync Configuration (Multi-Table)
SYNC_INTERVAL_SECONDS=30
SYNC_PARALLEL_TABLES=5
SYNC_CONFIG_FILE=tables_config.json
```

Create `tables_config.json`:
```json
{
  "tables": [
    {"name": "employees", "primary_key": "id", "timestamp_column": "last_modified"},
    {"name": "customers", "primary_key": "customer_id", "timestamp_column": "updated_at"},
    // ... add all 74 tables
  ]
}
```

**See [MULTI_TABLE_GUIDE.md](MULTI_TABLE_GUIDE.md) for complete multi-table setup instructions.**

## Usage

### List Configured Tables

View all configured tables (for multi-table setup):

```bash
python main.py --list-tables
```

### Run a Single Sync Operation

Perfect for testing or manual syncs:

```bash
python main.py --once
```

### Run as a Continuous Daemon

Runs in the foreground with continuous syncing:

```bash
python main.py --daemon
```

### Check Sync Status

View the current sync metadata for all tables:

```bash
python main.py --status
```

Or for a specific table:

```bash
python main.py --status --table employees
```

## Running as a System Service

### On macOS (using launchd)

1. Create a plist file at `~/Library/LaunchAgents/com.sync.sqlany-postgres.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sync.sqlany-postgres</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/main.py</string>
        <string>--daemon</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/stderr.log</string>
</dict>
</plist>
```

2. Load and start the service:

```bash
launchctl load ~/Library/LaunchAgents/com.sync.sqlany-postgres.plist
launchctl start com.sync.sqlany-postgres
```

3. Check status:

```bash
launchctl list | grep sync
```

4. Stop the service:

```bash
launchctl stop com.sync.sqlany-postgres
launchctl unload ~/Library/LaunchAgents/com.sync.sqlany-postgres.plist
```

### On Linux (using systemd)

1. Create a service file at `/etc/systemd/system/sqlany-postgres-sync.service`:

```ini
[Unit]
Description=SQL Anywhere to PostgreSQL Sync Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration
ExecStart=/usr/bin/python3 /Users/teejay/dev/SQLAnywheretoPostgreSQLMigration/main.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sqlany-postgres-sync
sudo systemctl start sqlany-postgres-sync
```

3. Check status:

```bash
sudo systemctl status sqlany-postgres-sync
```

## Database Schema

### Metadata Table (PostgreSQL)

The service automatically creates a `sync_metadata` table in PostgreSQL:

```sql
CREATE TABLE sync_metadata (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL UNIQUE,
    last_sync_timestamp TIMESTAMP,
    last_sync_completed_at TIMESTAMP NOT NULL,
    records_synced INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT
);
```

### Source Table Requirements

Your SQL Anywhere table must have:
- A primary key column (default: `id`)
- A timestamp column for tracking modifications (default: `last_modified`)

Example:

```sql
CREATE TABLE your_table (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    last_modified TIMESTAMP DEFAULT CURRENT TIMESTAMP
);
```

## How It Works

1. **Initialization**: On startup, the service connects to both databases and creates the metadata table if it doesn't exist.

2. **Delta Fetch**: The service queries the `sync_metadata` table to get the last sync timestamp, then fetches only records from SQL Anywhere where `last_modified > last_sync_timestamp`.

3. **Upsert**: Records are upserted to PostgreSQL using:
   ```sql
   INSERT INTO table (...) VALUES (...)
   ON CONFLICT (primary_key) DO UPDATE SET ...
   ```

4. **Metadata Update**: After successful sync, the metadata table is updated with the latest timestamp and sync statistics.

5. **Repeat**: The service waits for the configured interval (default: 30 seconds) and repeats.

## Logging

Logs are written to both:
- **File**: `sync_service.log` (configurable via `LOG_FILE`)
- **Console**: stdout

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Error Handling

- **Connection Errors**: Automatically retries after the sync interval
- **Sync Failures**: Logged to metadata table with error message
- **Graceful Shutdown**: Handles SIGTERM/SIGINT to close connections properly

## Monitoring

Check sync status at any time:

```bash
python main.py --status
```

Output example:
```
Sync Status for table: your_table
============================================================
Last sync timestamp:    2026-02-03 09:00:00
Last sync completed:    2026-02-03 09:00:05
Records synced:         150
Status:                 success
```

## Troubleshooting

### Connection Issues

1. Verify database credentials in `.env`
2. Check network connectivity
3. Ensure SQL Anywhere driver is installed: `pip install sqlanydb`
4. Ensure PostgreSQL driver is installed: `pip install psycopg2-binary`

### No Records Syncing

1. Verify the timestamp column exists and is populated
2. Check that records have been modified since last sync
3. Run with `--once` to see detailed logs

### Performance Optimization

For large datasets:
- Adjust `SYNC_INTERVAL_SECONDS` to reduce frequency
- Add indexes on the timestamp column in SQL Anywhere
- Consider batch size limits if needed

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub.