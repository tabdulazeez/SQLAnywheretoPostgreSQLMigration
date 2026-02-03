#!/usr/bin/env python3
"""
Command-line interface for the multi-table sync service.
Supports running as a foreground process or background daemon.
"""
import sys
import argparse
import logging
from pathlib import Path
from daemon import MultiTableSyncDaemon
from config import Config
from database import DatabaseManager
from table_config import TableConfigManager
from multi_table_sync import MultiTableSyncService

logger = logging.getLogger(__name__)


def run_once():
    """Run a single sync operation and exit."""
    try:
        # Validate configuration
        Config.validate()
        print("✓ Configuration validated successfully")
        
        # Load table configuration
        config_file = Config.SYNC_CONFIG_FILE if Path(Config.SYNC_CONFIG_FILE).exists() else None
        table_config_manager = TableConfigManager(config_file)
        table_config_manager.validate()
        
        enabled_tables = table_config_manager.get_enabled_tables()
        print(f"✓ Loaded {len(enabled_tables)} enabled tables for sync")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        print("✓ Database connections initialized")
        
        # Initialize multi-table sync service
        sync_service = MultiTableSyncService(
            db_manager,
            enabled_tables,
            max_workers=Config.SYNC_PARALLEL_TABLES
        )
        print(f"✓ Multi-table sync service initialized\n")
        print(f"Starting one-time sync for {len(enabled_tables)} tables...")
        print("=" * 70)
        
        # Perform sync
        result = sync_service.sync_all(parallel=True)
        
        # Print results
        print("\n" + "=" * 70)
        if result['status'] == 'success':
            print(f"✓ Sync completed successfully!")
            print(f"  Total tables:        {result['total_tables']}")
            print(f"  Successful tables:   {result['successful_tables']}")
            print(f"  Total records:       {result['total_records_synced']}")
            print(f"  Duration:            {result['total_duration_seconds']:.2f} seconds")
        elif result['status'] == 'partial':
            print(f"⚠ Sync partially successful!")
            print(f"  Total tables:        {result['total_tables']}")
            print(f"  Successful tables:   {result['successful_tables']}")
            print(f"  Failed tables:       {result['failed_tables']}")
            print(f"  Total records:       {result['total_records_synced']}")
            print(f"  Duration:            {result['total_duration_seconds']:.2f} seconds")
        else:
            print(f"✗ Sync failed!")
            print(f"  Total tables:        {result['total_tables']}")
            print(f"  Failed tables:       {result['failed_tables']}")
            sys.exit(1)
        
        # Print per-table results
        print("\nPer-Table Results:")
        print("-" * 70)
        for table_result in result['table_results']:
            status_icon = "✓" if table_result['status'] == 'success' else "✗"
            table_name = table_result['table_name']
            records = table_result['records_synced']
            duration = table_result['sync_duration_seconds']
            
            if table_result['status'] == 'success':
                print(f"  {status_icon} {table_name:<30} {records:>6} records in {duration:>6.2f}s")
            else:
                error = table_result.get('error', 'Unknown error')
                print(f"  {status_icon} {table_name:<30} FAILED: {error}")
        
        print("=" * 70)
        
        # Cleanup
        db_manager.close()
        
        if result['status'] == 'failed':
            sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_daemon():
    """Run as a background daemon."""
    daemon = MultiTableSyncDaemon()
    daemon.start()


def check_status(table_name: str = None):
    """Check the current sync status from metadata."""
    try:
        Config.validate()
        db_manager = DatabaseManager()
        
        with db_manager.get_target_session() as session:
            from models import SyncMetadata
            
            if table_name:
                # Show status for specific table
                metadata = session.query(SyncMetadata).filter_by(
                    table_name=table_name
                ).first()
                
                if metadata:
                    print(f"\nSync Status for table: {table_name}")
                    print("=" * 70)
                    print(f"Last sync timestamp:    {metadata.last_sync_timestamp}")
                    print(f"Last sync completed:    {metadata.last_sync_completed_at}")
                    print(f"Records synced:         {metadata.records_synced}")
                    print(f"Status:                 {metadata.status}")
                    if metadata.error_message:
                        print(f"Error message:          {metadata.error_message}")
                else:
                    print(f"\nNo sync metadata found for table: {table_name}")
                    print("The table has not been synced yet.")
            else:
                # Show status for all tables
                all_metadata = session.query(SyncMetadata).order_by(
                    SyncMetadata.table_name
                ).all()
                
                if all_metadata:
                    print(f"\nSync Status for All Tables ({len(all_metadata)} tables)")
                    print("=" * 90)
                    print(f"{'Table Name':<30} {'Status':<10} {'Records':<10} {'Last Sync':<20}")
                    print("-" * 90)
                    
                    for metadata in all_metadata:
                        status_icon = "✓" if metadata.status == 'success' else "✗"
                        last_sync = metadata.last_sync_completed_at.strftime('%Y-%m-%d %H:%M:%S') if metadata.last_sync_completed_at else 'Never'
                        
                        print(
                            f"{metadata.table_name:<30} "
                            f"{status_icon} {metadata.status:<8} "
                            f"{metadata.records_synced:<10} "
                            f"{last_sync:<20}"
                        )
                        
                        if metadata.error_message:
                            print(f"  Error: {metadata.error_message}")
                    
                    print("=" * 90)
                    
                    # Summary statistics
                    successful = sum(1 for m in all_metadata if m.status == 'success')
                    failed = sum(1 for m in all_metadata if m.status == 'failed')
                    total_records = sum(m.records_synced for m in all_metadata)
                    
                    print(f"\nSummary:")
                    print(f"  Total tables:       {len(all_metadata)}")
                    print(f"  Successful:         {successful}")
                    print(f"  Failed:             {failed}")
                    print(f"  Total records:      {total_records}")
                else:
                    print("\nNo sync metadata found.")
                    print("No tables have been synced yet.")
        
        db_manager.close()
        
    except Exception as e:
        print(f"\n✗ Error checking status: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def list_tables():
    """List all configured tables."""
    try:
        config_file = Config.SYNC_CONFIG_FILE if Path(Config.SYNC_CONFIG_FILE).exists() else None
        table_config_manager = TableConfigManager(config_file)
        
        all_tables = list(table_config_manager)
        enabled_tables = table_config_manager.get_enabled_tables()
        
        print(f"\nConfigured Tables ({len(all_tables)} total, {len(enabled_tables)} enabled)")
        print("=" * 90)
        print(f"{'Table Name':<30} {'Primary Key':<15} {'Timestamp Column':<20} {'Enabled':<10}")
        print("-" * 90)
        
        for table in all_tables:
            enabled_icon = "✓" if table.enabled else "✗"
            print(
                f"{table.name:<30} "
                f"{table.primary_key:<15} "
                f"{table.timestamp_column:<20} "
                f"{enabled_icon} {str(table.enabled):<8}"
            )
        
        print("=" * 90)
        
    except Exception as e:
        print(f"\n✗ Error listing tables: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='SQL Anywhere to PostgreSQL Multi-Table Sync Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single sync operation
  python main.py --once
  
  # Run as a continuous daemon
  python main.py --daemon
  
  # Check current sync status for all tables
  python main.py --status
  
  # Check status for a specific table
  python main.py --status --table employees
  
  # List all configured tables
  python main.py --list-tables
        """
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run a single sync operation and exit'
    )
    
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as a continuous background daemon'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Check the current sync status'
    )
    
    parser.add_argument(
        '--table',
        type=str,
        help='Specify a table name (used with --status)'
    )
    
    parser.add_argument(
        '--list-tables',
        action='store_true',
        help='List all configured tables'
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not (args.once or args.daemon or args.status or args.list_tables):
        parser.print_help()
        sys.exit(0)
    
    # Execute requested operation
    if args.list_tables:
        list_tables()
    elif args.status:
        check_status(args.table)
    elif args.once:
        run_once()
    elif args.daemon:
        run_daemon()


if __name__ == '__main__':
    main()
