# SQL Anywhere to PostgreSQL Sync Service - Project Summary

## 📋 Project Overview

A production-ready Python background daemon service that continuously synchronizes records from SQL Anywhere to PostgreSQL using delta synchronization based on timestamps. The service implements efficient upsert logic, state persistence, and comprehensive error handling.

## 🎯 Key Features

✅ **Delta Synchronization** - Only syncs modified records since last sync  
✅ **Upsert Logic** - Uses PostgreSQL's `ON CONFLICT` for efficient updates  
✅ **State Persistence** - Metadata table tracks sync state for resume capability  
✅ **Background Daemon** - Runs continuously with configurable intervals  
✅ **Graceful Shutdown** - Handles SIGTERM/SIGINT signals properly  
✅ **Error Recovery** - Automatic retry with error logging  
✅ **Multiple Run Modes** - Single sync, daemon, or status check  
✅ **System Service** - Deploy as macOS launchd or Linux systemd service  
✅ **Comprehensive Testing** - Built-in test suite for validation  
✅ **Production Ready** - Logging, monitoring, and deployment scripts included  

## 📁 Project Structure

```
SQLAnywheretoPostgreSQLMigration/
├── Core Application Files
│   ├── main.py                 # CLI entry point with --once, --daemon, --status
│   ├── daemon.py               # Background daemon with signal handling
│   ├── sync_service.py         # Core sync logic (fetch, upsert, metadata)
│   ├── database.py             # Database connection management
│   ├── models.py               # SQLAlchemy models (sync_metadata)
│   └── config.py               # Configuration and validation
│
├── Configuration
│   ├── .env.example            # Environment variable template
│   └── requirements.txt        # Python dependencies
│
├── Testing
│   └── test_setup.py           # Comprehensive setup validation
│
├── Documentation
│   ├── README.md               # Main documentation
│   ├── QUICKSTART.md           # Step-by-step setup guide
│   └── ARCHITECTURE.md         # Technical architecture details
│
├── Deployment
│   ├── deployment/
│   │   ├── macos-launchd.plist     # macOS service configuration
│   │   ├── linux-systemd.service   # Linux service configuration
│   │   ├── deploy-macos.sh         # macOS deployment script
│   │   └── deploy-linux.sh         # Linux deployment script
│
└── Examples
    ├── examples/
    │   ├── sqlany_setup.sql        # Sample SQL Anywhere table
    │   ├── postgres_setup.sql      # Sample PostgreSQL table
    │   └── .env.employees          # Example configuration
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with your database credentials

# 3. Test setup
python test_setup.py

# 4. Run first sync
python main.py --once

# 5. Run as daemon
python main.py --daemon
```

## 🔧 Configuration

Edit `.env` with your settings:

```env
# SQL Anywhere (Source)
SQLANY_HOST=localhost
SQLANY_DATABASE=your_db
SQLANY_USER=your_user
SQLANY_PASSWORD=your_password

# PostgreSQL (Target)
POSTGRES_HOST=localhost
POSTGRES_DATABASE=your_db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# Sync Settings
SYNC_TABLE_NAME=your_table
SYNC_PRIMARY_KEY=id
SYNC_TIMESTAMP_COLUMN=last_modified
SYNC_INTERVAL_SECONDS=30
```

## 💻 Usage

### Run Single Sync
```bash
python main.py --once
```

### Run as Daemon
```bash
python main.py --daemon
```

### Check Status
```bash
python main.py --status
```

### Deploy as System Service

**macOS:**
```bash
cd deployment
./deploy-macos.sh
```

**Linux:**
```bash
cd deployment
sudo ./deploy-linux.sh
```

## 🏗️ Architecture

```
SQL Anywhere (Source) → Sync Service → PostgreSQL (Target)
                            ↓
                      Metadata Table
                    (tracks sync state)
```

### How It Works

1. **Fetch Delta**: Query records where `last_modified > last_sync_timestamp`
2. **Upsert**: Insert new records or update existing using `ON CONFLICT`
3. **Update Metadata**: Record latest timestamp and sync statistics
4. **Repeat**: Wait for configured interval and repeat

### Upsert Example

```sql
INSERT INTO employees (id, name, email, last_modified)
VALUES (1, 'John', 'john@example.com', '2026-02-03 09:00:00')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    last_modified = EXCLUDED.last_modified;
```

## 📊 Monitoring

### Check Sync Status
```bash
python main.py --status
```

Output:
```
Sync Status for table: employees
============================================================
Last sync timestamp:    2026-02-03 09:00:00
Last sync completed:    2026-02-03 09:00:05
Records synced:         150
Status:                 success
```

### View Logs
```bash
tail -f sync_service.log
```

### Query Metadata Directly
```sql
SELECT * FROM sync_metadata WHERE table_name = 'your_table';
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_setup.py
```

Tests include:
- ✓ Configuration validation
- ✓ Database connectivity (both SQL Anywhere and PostgreSQL)
- ✓ Table structure verification
- ✓ Required columns check

## 📦 Dependencies

- **sqlalchemy** - ORM and database abstraction
- **psycopg2-binary** - PostgreSQL driver
- **sqlanydb** - SQL Anywhere driver
- **python-dotenv** - Environment variable management
- **python-daemon** - Daemon process support

## 🔒 Security

- Credentials stored in `.env` (excluded from git)
- No passwords logged
- Minimal database permissions required:
  - SQL Anywhere: SELECT on source table
  - PostgreSQL: SELECT, INSERT, UPDATE on target table

## 🎯 Use Cases

1. **Real-time Data Replication** - Keep PostgreSQL in sync with SQL Anywhere
2. **Database Migration** - Gradual migration from SQL Anywhere to PostgreSQL
3. **Analytics** - Sync operational data to PostgreSQL for analytics
4. **Backup/DR** - Maintain PostgreSQL as backup/disaster recovery
5. **Multi-Database Applications** - Support both databases simultaneously

## 📈 Performance

- **Batch Operations**: All records upserted in single transaction
- **Connection Pooling**: PostgreSQL uses connection pool (5 + 10 overflow)
- **Indexed Queries**: Assumes timestamp column is indexed
- **Delta Sync**: Only modified records transferred

### Recommended Indexes

```sql
-- SQL Anywhere
CREATE INDEX idx_last_modified ON your_table(last_modified);

-- PostgreSQL
CREATE INDEX idx_last_modified ON your_table(last_modified);
```

## 🛠️ Troubleshooting

### Connection Issues
```bash
# Test SQL Anywhere connection
python test_setup.py

# Check PostgreSQL
pg_isready
```

### No Records Syncing
```bash
# Check table structure
python test_setup.py

# Verify timestamp column is updating
SELECT * FROM your_table ORDER BY last_modified DESC LIMIT 5;
```

### View Detailed Logs
```bash
# Set debug logging in .env
LOG_LEVEL=DEBUG

# Run and watch logs
python main.py --daemon
tail -f sync_service.log
```

## 🚀 Deployment Checklist

- [ ] Install Python dependencies
- [ ] Configure `.env` with database credentials
- [ ] Run `test_setup.py` to validate setup
- [ ] Test with `python main.py --once`
- [ ] Verify data in PostgreSQL
- [ ] Check sync status with `python main.py --status`
- [ ] Deploy as system service (optional)
- [ ] Set up log rotation
- [ ] Configure monitoring/alerting
- [ ] Document table schema and sync requirements

## 📚 Documentation

- **README.md** - Main documentation with detailed usage
- **QUICKSTART.md** - Step-by-step setup guide
- **ARCHITECTURE.md** - Technical architecture and design decisions

## 🔄 Workflow

```
┌─────────────────────────────────────────────────────────┐
│                    Service Lifecycle                     │
└─────────────────────────────────────────────────────────┘

1. START
   ↓
2. Load Configuration (.env)
   ↓
3. Validate Configuration
   ↓
4. Initialize Database Connections
   ↓
5. Create Metadata Table (if not exists)
   ↓
6. ┌─────────────────────────────────┐
   │      SYNC LOOP (Continuous)     │
   │                                 │
   │  a. Get last sync timestamp     │
   │  b. Fetch delta records         │
   │  c. Upsert to PostgreSQL        │
   │  d. Update metadata             │
   │  e. Wait for interval           │
   │  f. Repeat                      │
   └─────────────────────────────────┘
   ↓
7. SHUTDOWN (on SIGTERM/SIGINT)
   ↓
8. Close Database Connections
   ↓
9. EXIT
```

## 🎓 Example Scenario

**Scenario**: Sync employee records from SQL Anywhere to PostgreSQL every 30 seconds

**Setup**:
1. Create `employees` table in both databases
2. Add trigger to update `last_modified` on changes
3. Configure `.env` with table name and credentials
4. Run sync service

**Result**:
- New employees automatically synced to PostgreSQL
- Updates to existing employees reflected in PostgreSQL
- No duplicate records (upsert handles conflicts)
- Service resumes from last sync after restart

## 🤝 Contributing

This is a production-ready template. Customize for your needs:

1. Modify `sync_service.py` for custom business logic
2. Add data transformations during sync
3. Implement multi-table support
4. Add custom error handling
5. Integrate with monitoring tools

## 📄 License

MIT License - Feel free to use and modify for your projects

## 🆘 Support

For issues:
1. Check logs: `tail -f sync_service.log`
2. Run tests: `python test_setup.py`
3. Check status: `python main.py --status`
4. Review documentation in `README.md` and `ARCHITECTURE.md`

---

**Built with ❤️ for seamless database synchronization**
