"""
Background daemon service for continuous multi-table sync operations.
"""
import sys
import time
import signal
import logging
from pathlib import Path
from config import Config
from database import DatabaseManager
from table_config import TableConfigManager
from multi_table_sync import MultiTableSyncService

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class MultiTableSyncDaemon:
    """Background daemon for continuous multi-table sync operations."""
    
    def __init__(self):
        """Initialize the sync daemon."""
        self.running = False
        self.db_manager = None
        self.sync_service = None
        self.table_config_manager = None
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self):
        """Start the sync daemon."""
        try:
            # Validate configuration
            Config.validate()
            logger.info("Configuration validated successfully")
            
            # Load table configuration
            config_file = Config.SYNC_CONFIG_FILE if Path(Config.SYNC_CONFIG_FILE).exists() else None
            self.table_config_manager = TableConfigManager(config_file)
            self.table_config_manager.validate()
            
            enabled_tables = self.table_config_manager.get_enabled_tables()
            logger.info(f"Loaded {len(enabled_tables)} enabled tables for sync")
            
            for table in enabled_tables:
                logger.info(f"  - {table.name} (pk: {table.primary_key}, ts: {table.timestamp_column})")
            
            # Initialize database manager
            self.db_manager = DatabaseManager()
            logger.info("Database connections initialized")
            
            # Initialize multi-table sync service
            self.sync_service = MultiTableSyncService(
                self.db_manager,
                enabled_tables,
                max_workers=Config.SYNC_PARALLEL_TABLES
            )
            logger.info(f"Multi-table sync service initialized (max {Config.SYNC_PARALLEL_TABLES} parallel)")
            
            # Start sync loop
            self.running = True
            logger.info(
                f"Starting sync daemon with interval of {Config.SYNC_INTERVAL_SECONDS} seconds"
            )
            
            self._run_sync_loop()
        
        except Exception as e:
            logger.error(f"Failed to start sync daemon: {e}", exc_info=True)
            self.stop()
            sys.exit(1)
    
    def _run_sync_loop(self):
        """Main sync loop that runs continuously."""
        sync_count = 0
        
        while self.running:
            try:
                sync_count += 1
                logger.info(f"{'='*80}")
                logger.info(f"Starting sync iteration #{sync_count}")
                logger.info(f"{'='*80}")
                
                # Perform multi-table sync
                result = self.sync_service.sync_all(parallel=True)
                
                # Log summary
                if result['status'] == 'success':
                    logger.info(
                        f"✓ Sync iteration #{sync_count} completed successfully: "
                        f"{result['total_records_synced']} records across "
                        f"{result['successful_tables']} tables in "
                        f"{result['total_duration_seconds']:.2f}s"
                    )
                elif result['status'] == 'partial':
                    logger.warning(
                        f"⚠ Sync iteration #{sync_count} partially successful: "
                        f"{result['successful_tables']}/{result['total_tables']} tables succeeded, "
                        f"{result['failed_tables']} failed"
                    )
                else:
                    logger.error(
                        f"✗ Sync iteration #{sync_count} failed: "
                        f"All {result['total_tables']} tables failed"
                    )
                
                # Log per-table results
                for table_result in result['table_results']:
                    if table_result['status'] == 'success' and table_result['records_synced'] > 0:
                        logger.info(
                            f"  [{table_result['table_name']}] "
                            f"{table_result['records_synced']} records in "
                            f"{table_result['sync_duration_seconds']:.2f}s"
                        )
                    elif table_result['status'] == 'failed':
                        logger.error(
                            f"  [{table_result['table_name']}] FAILED: "
                            f"{table_result.get('error', 'Unknown error')}"
                        )
                
                # Wait for next sync interval
                if self.running:
                    logger.info(
                        f"Waiting {Config.SYNC_INTERVAL_SECONDS} seconds until next sync..."
                    )
                    time.sleep(Config.SYNC_INTERVAL_SECONDS)
            
            except Exception as e:
                logger.error(
                    f"Error in sync iteration #{sync_count}: {e}",
                    exc_info=True
                )
                
                # Wait before retrying
                if self.running:
                    logger.info("Waiting before retry...")
                    time.sleep(Config.SYNC_INTERVAL_SECONDS)
    
    def stop(self):
        """Stop the sync daemon gracefully."""
        logger.info("Stopping sync daemon...")
        self.running = False
        
        if self.db_manager:
            self.db_manager.close()
        
        logger.info("Sync daemon stopped")


def main():
    """Main entry point for the daemon."""
    logger.info("=" * 80)
    logger.info("SQL Anywhere to PostgreSQL Multi-Table Sync Daemon")
    logger.info("=" * 80)
    
    daemon = MultiTableSyncDaemon()
    daemon.start()


if __name__ == '__main__':
    main()
