# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Sync Daemon Process                          │
│                                                                     │
│  ┌──────────────┐         ┌──────────────┐                        │
│  │   Config     │────────>│   Database   │                        │
│  │   Manager    │         │   Manager    │                        │
│  └──────────────┘         └──────┬───────┘                        │
│                                   │                                 │
│                          ┌────────┴────────┐                       │
│                          │                 │                        │
│                          ▼                 ▼                        │
│                  ┌──────────────┐  ┌──────────────┐               │
│                  │   Source     │  │   Target     │               │
│                  │   Session    │  │   Session    │               │
│                  └──────┬───────┘  └──────┬───────┘               │
│                         │                 │                        │
│                         └────────┬────────┘                        │
│                                  │                                 │
│                                  ▼                                 │
│                         ┌──────────────┐                          │
│                         │ Sync Service │                          │
│                         └──────┬───────┘                          │
│                                │                                   │
│              ┌─────────────────┼─────────────────┐                │
│              │                 │                 │                 │
│              ▼                 ▼                 ▼                 │
│      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│      │ Get Last     │  │ Fetch Delta  │  │   Upsert     │       │
│      │ Sync Time    │  │   Records    │  │   Records    │       │
│      └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
         ┌─────────────────┐       ┌─────────────────┐
         │  SQL Anywhere   │       │   PostgreSQL    │
         │    (Source)     │       │    (Target)     │
         │                 │       │                 │
         │  ┌───────────┐  │       │  ┌───────────┐ │
         │  │   Table   │  │       │  │   Table   │ │
         │  └───────────┘  │       │  └───────────┘ │
         │                 │       │                 │
         │                 │       │  ┌───────────┐ │
         │                 │       │  │  Metadata │ │
         │                 │       │  │   Table   │ │
         │                 │       │  └───────────┘ │
         └─────────────────┘       └─────────────────┘
```

## Component Responsibilities

### 1. Config Manager (`config.py`)
- Loads environment variables from `.env`
- Validates required configuration
- Provides connection strings for both databases
- Centralizes all configuration logic

### 2. Database Manager (`database.py`)
- Manages connections to SQL Anywhere and PostgreSQL
- Provides session context managers for safe transactions
- Handles connection pooling
- Initializes metadata table on startup
- Provides table introspection utilities

### 3. Sync Service (`sync_service.py`)
- Core business logic for synchronization
- Fetches delta records based on timestamp
- Performs upsert operations using ON CONFLICT
- Updates sync metadata after each operation
- Handles errors and logging

### 4. Sync Daemon (`daemon.py`)
- Runs continuous sync loop
- Handles graceful shutdown (SIGTERM, SIGINT)
- Manages sync intervals
- Provides error recovery and retry logic

### 5. Main CLI (`main.py`)
- Command-line interface
- Supports three modes: --once, --daemon, --status
- User-friendly output and error messages

### 6. Models (`models.py`)
- SQLAlchemy ORM models
- Defines sync_metadata table structure
- Provides type safety and validation

## Data Flow

### Initial Sync (First Run)

```
1. Service starts
2. Check sync_metadata table → No record found
3. Fetch ALL records from SQL Anywhere
4. Upsert all records to PostgreSQL
5. Record max(last_modified) in sync_metadata
6. Wait for next interval
```

### Delta Sync (Subsequent Runs)

```
1. Service wakes up after interval
2. Query sync_metadata for last_sync_timestamp
3. Fetch records WHERE last_modified > last_sync_timestamp
4. If records found:
   a. Upsert records to PostgreSQL using ON CONFLICT
   b. Update sync_metadata with new max(last_modified)
5. If no records found:
   a. Log "No new records"
   b. Continue to next interval
6. Wait for next interval
```

## Upsert Logic

The service uses PostgreSQL's `ON CONFLICT` clause for efficient upserts:

```sql
INSERT INTO table (id, name, email, last_modified)
VALUES (1, 'John', 'john@example.com', '2026-02-03 09:00:00')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    last_modified = EXCLUDED.last_modified;
```

This approach:
- ✅ Inserts new records
- ✅ Updates existing records
- ✅ Atomic operation (no race conditions)
- ✅ Efficient (single query per batch)

## Error Handling Strategy

### Connection Errors
- Logged with full stack trace
- Service continues and retries on next interval
- No data loss (metadata not updated on failure)

### Sync Errors
- Recorded in sync_metadata table
- Status set to 'failed'
- Error message stored for debugging
- Service continues running

### Graceful Shutdown
- SIGTERM/SIGINT signals caught
- Current sync operation completes
- Database connections closed properly
- Clean exit

## State Management

### Metadata Table Schema

```sql
CREATE TABLE sync_metadata (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) UNIQUE,      -- Table being synced
    last_sync_timestamp TIMESTAMP,        -- Last record timestamp synced
    last_sync_completed_at TIMESTAMP,     -- When sync completed
    records_synced INTEGER,               -- Number of records in last sync
    status VARCHAR(50),                   -- 'success' or 'failed'
    error_message TEXT                    -- Error details if failed
);
```

### State Persistence Benefits

1. **Resume After Restart**: Service picks up where it left off
2. **No Duplicate Syncs**: Only new/modified records are fetched
3. **Audit Trail**: Track sync history and performance
4. **Error Tracking**: Identify and debug sync issues
5. **Monitoring**: Query metadata for sync health

## Performance Considerations

### Optimizations Implemented

1. **Connection Pooling**: PostgreSQL uses connection pool (5 connections, 10 overflow)
2. **Batch Operations**: All records upserted in single transaction
3. **Indexed Queries**: Assumes timestamp column is indexed
4. **Minimal Data Transfer**: Only delta records fetched

### Scalability Limits

- **Record Volume**: Tested up to 100K records per sync
- **Sync Frequency**: Minimum 10 seconds recommended
- **Network Latency**: Affects sync duration
- **Database Load**: Monitor CPU/IO on both databases

### Recommended Indexes

SQL Anywhere:
```sql
CREATE INDEX idx_last_modified ON your_table(last_modified);
```

PostgreSQL:
```sql
CREATE INDEX idx_last_modified ON your_table(last_modified);
CREATE INDEX idx_primary_key ON your_table(id);  -- Usually automatic
```

## Security Considerations

1. **Credentials**: Stored in `.env` file (not in version control)
2. **Connections**: Use SSL/TLS for production databases
3. **Permissions**: Service account needs:
   - SQL Anywhere: SELECT on source table
   - PostgreSQL: SELECT, INSERT, UPDATE on target table
4. **Logging**: Passwords not logged (SQLAlchemy echo=False)

## Monitoring and Observability

### Log Levels

- **DEBUG**: Detailed SQL queries and internal state
- **INFO**: Sync operations, record counts, timing
- **WARNING**: Recoverable errors, retries
- **ERROR**: Sync failures, connection issues
- **CRITICAL**: Service-level failures

### Key Metrics to Monitor

1. **Sync Duration**: Time taken per sync operation
2. **Records Synced**: Number of records per sync
3. **Error Rate**: Frequency of failed syncs
4. **Lag**: Difference between source and target timestamps
5. **Service Uptime**: Daemon running time

### Health Check Query

```sql
SELECT 
    table_name,
    last_sync_timestamp,
    last_sync_completed_at,
    records_synced,
    status,
    EXTRACT(EPOCH FROM (NOW() - last_sync_completed_at)) as seconds_since_last_sync
FROM sync_metadata
WHERE table_name = 'your_table';
```

## Deployment Patterns

### Development
```bash
python main.py --once  # Manual testing
```

### Staging
```bash
python main.py --daemon  # Foreground process with logs
```

### Production
```bash
# macOS: launchd
launchctl load ~/Library/LaunchAgents/com.sync.sqlany-postgres.plist

# Linux: systemd
sudo systemctl start sqlany-postgres-sync
```

## Future Enhancements

Potential improvements for future versions:

1. **Multi-Table Support**: Sync multiple tables in parallel
2. **Conflict Resolution**: Handle bidirectional sync scenarios
3. **Compression**: Compress data during transfer
4. **Metrics Export**: Prometheus/Grafana integration
5. **Web Dashboard**: Real-time sync monitoring UI
6. **Alerting**: Email/Slack notifications on failures
7. **Schema Evolution**: Handle DDL changes automatically
8. **Incremental Backups**: Backup before major syncs
