#!/usr/bin/env python3
"""
Health check script for sync service monitoring.
Can be used by monitoring systems (Nagios, Prometheus, etc.)

Exit Codes:
    0 - OK: All tables synced recently
    1 - WARNING: Some tables haven't synced recently
    2 - CRITICAL: No recent syncs or all tables failed
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from models import SyncMetadata


def check_sync_health(max_age_hours: int = 2):
    """
    Check if tables have been synced recently.
    
    Args:
        max_age_hours: Maximum acceptable age of last sync in hours
        
    Returns:
        Tuple of (exit_code, message)
    """
    try:
        Config.validate()
        db_manager = DatabaseManager()
        
        with db_manager.get_target_session() as session:
            all_metadata = session.query(SyncMetadata).all()
            
            if not all_metadata:
                return 2, "CRITICAL: No sync metadata found - sync has never run"
            
            now = datetime.utcnow()
            max_age = timedelta(hours=max_age_hours)
            
            # Check each table
            stale_tables = []
            failed_tables = []
            ok_tables = []
            
            for metadata in all_metadata:
                if metadata.status == 'failed':
                    failed_tables.append(metadata.table_name)
                elif metadata.last_sync_completed_at:
                    age = now - metadata.last_sync_completed_at
                    if age > max_age:
                        stale_tables.append({
                            'name': metadata.table_name,
                            'hours': age.total_seconds() / 3600
                        })
                    else:
                        ok_tables.append(metadata.table_name)
                else:
                    stale_tables.append({
                        'name': metadata.table_name,
                        'hours': float('inf')
                    })
            
            # Determine status
            total_tables = len(all_metadata)
            
            if failed_tables:
                msg = f"CRITICAL: {len(failed_tables)}/{total_tables} tables failed: {', '.join(failed_tables)}"
                return 2, msg
            
            if stale_tables:
                stale_names = [f"{t['name']} ({t['hours']:.1f}h)" for t in stale_tables]
                msg = f"WARNING: {len(stale_tables)}/{total_tables} tables not synced recently: {', '.join(stale_names)}"
                return 1, msg
            
            msg = f"OK: All {total_tables} tables synced within last {max_age_hours} hours"
            return 0, msg
        
        db_manager.close()
        
    except Exception as e:
        return 2, f"CRITICAL: Error checking sync health: {e}"


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check sync service health')
    parser.add_argument(
        '--max-age-hours',
        type=int,
        default=2,
        help='Maximum acceptable age of last sync in hours (default: 2)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    
    args = parser.parse_args()
    
    exit_code, message = check_sync_health(args.max_age_hours)
    
    print(message)
    
    if args.verbose and exit_code == 0:
        # Show additional details
        try:
            from database import DatabaseManager
            from models import SyncMetadata
            
            db_manager = DatabaseManager()
            with db_manager.get_target_session() as session:
                all_metadata = session.query(SyncMetadata).order_by(
                    SyncMetadata.last_sync_completed_at.desc()
                ).all()
                
                print("\nDetailed Status:")
                print("-" * 80)
                for m in all_metadata:
                    age = (datetime.utcnow() - m.last_sync_completed_at).total_seconds() / 3600
                    print(f"  {m.table_name}: {m.records_synced} records, {age:.1f}h ago")
            
            db_manager.close()
        except Exception as e:
            print(f"Error getting details: {e}")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
