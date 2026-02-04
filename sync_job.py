#!/usr/bin/env python3
"""
Standalone sync job script for cron/Airflow scheduling.
This script runs a single sync operation and exits with appropriate status codes.

Exit Codes:
    0 - Success (all tables synced successfully)
    1 - Partial success (some tables failed)
    2 - Complete failure (all tables failed or critical error)
    3 - Configuration error
"""
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
import json

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from table_config import TableConfigManager
from multi_table_sync import MultiTableSyncService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_sync_job():
    """
    Run a single sync operation for all configured tables.
    Returns exit code based on sync results.
    """
    job_start = datetime.utcnow()
    logger.info("=" * 80)
    logger.info(f"Starting scheduled sync job at {job_start.isoformat()}")
    logger.info("=" * 80)
    
    try:
        # Validate configuration
        Config.validate()
        logger.info("✓ Configuration validated successfully")
        
        # Load table configuration
        config_file = Config.SYNC_CONFIG_FILE if Path(Config.SYNC_CONFIG_FILE).exists() else None
        table_config_manager = TableConfigManager(config_file)
        table_config_manager.validate()
        
        enabled_tables = table_config_manager.get_enabled_tables()
        logger.info(f"✓ Loaded {len(enabled_tables)} enabled tables for sync")
        
        if not enabled_tables:
            logger.warning("No enabled tables found in configuration")
            return 0  # Not an error, just nothing to do
        
        # Initialize database manager
        db_manager = DatabaseManager()
        logger.info("✓ Database connections initialized")
        
        # Initialize multi-table sync service
        sync_service = MultiTableSyncService(
            db_manager,
            enabled_tables,
            max_workers=Config.SYNC_PARALLEL_TABLES
        )
        logger.info(f"✓ Multi-table sync service initialized")
        logger.info(f"Starting sync for {len(enabled_tables)} tables...")
        
        # Perform sync
        result = sync_service.sync_all(parallel=True)
        
        # Log results
        job_duration = (datetime.utcnow() - job_start).total_seconds()
        logger.info("-" * 80)
        logger.info(f"Sync job completed in {job_duration:.2f} seconds")
        logger.info(f"Status: {result['status']}")
        logger.info(f"Total tables: {result['total_tables']}")
        logger.info(f"Successful tables: {result['successful_tables']}")
        logger.info(f"Failed tables: {result['failed_tables']}")
        logger.info(f"Total records synced: {result['total_records_synced']}")
        logger.info(f"Sync duration: {result['total_duration_seconds']:.2f} seconds")
        
        # Log per-table results
        logger.info("-" * 80)
        logger.info("Per-table results:")
        for table_result in result['table_results']:
            table_name = table_result['table_name']
            status = table_result['status']
            
            if status == 'success':
                records = table_result.get('records_synced', 0)
                duration = table_result.get('sync_duration_seconds', 0)
                logger.info(f"  ✓ {table_name}: {records} records in {duration:.2f}s")
            else:
                error = table_result.get('error', 'Unknown error')
                logger.error(f"  ✗ {table_name}: FAILED - {error}")
        
        logger.info("=" * 80)
        
        # Cleanup
        db_manager.close()
        
        # Determine exit code
        if result['status'] == 'success':
            logger.info("Job completed successfully - all tables synced")
            return 0
        elif result['status'] == 'partial':
            logger.warning("Job completed with partial success - some tables failed")
            return 1
        else:
            logger.error("Job failed - all tables failed to sync")
            return 2
            
    except ValueError as e:
        # Configuration error
        logger.error(f"Configuration error: {e}")
        return 3
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error during sync job: {e}", exc_info=True)
        return 2


def main():
    """Main entry point."""
    try:
        exit_code = run_sync_job()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Sync job interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(2)


if __name__ == '__main__':
    main()
