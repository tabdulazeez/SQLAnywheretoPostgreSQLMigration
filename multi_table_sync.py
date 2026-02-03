"""
Multi-table sync service for syncing multiple tables from SQL Anywhere to PostgreSQL.
"""
import logging
import concurrent.futures
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from database import DatabaseManager
from models import SyncMetadata
from table_config import TableConfig

logger = logging.getLogger(__name__)


class TableSyncService:
    """Service to sync a single table from SQL Anywhere to PostgreSQL."""
    
    def __init__(self, db_manager: DatabaseManager, table_config: TableConfig):
        """Initialize sync service with database manager and table configuration."""
        self.db_manager = db_manager
        self.table_config = table_config
        self.table_name = table_config.name
        self.primary_key = table_config.primary_key
        self.timestamp_column = table_config.timestamp_column
        self.batch_size = table_config.batch_size
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the last successful sync timestamp from metadata table."""
        try:
            with self.db_manager.get_target_session() as session:
                metadata = session.query(SyncMetadata).filter_by(
                    table_name=self.table_name
                ).first()
                
                if metadata:
                    logger.debug(
                        f"[{self.table_name}] Last sync: {metadata.last_sync_timestamp}"
                    )
                    return metadata.last_sync_timestamp
                else:
                    logger.info(
                        f"[{self.table_name}] No previous sync found, will sync all records"
                    )
                    return None
        except Exception as e:
            logger.error(f"[{self.table_name}] Error getting last sync timestamp: {e}")
            raise
    
    def update_sync_metadata(
        self,
        last_timestamp: Optional[datetime],
        records_synced: int,
        status: str = 'success',
        error_message: Optional[str] = None
    ):
        """Update sync metadata after sync operation."""
        try:
            with self.db_manager.get_target_session() as session:
                metadata = session.query(SyncMetadata).filter_by(
                    table_name=self.table_name
                ).first()
                
                if metadata:
                    metadata.last_sync_timestamp = last_timestamp
                    metadata.last_sync_completed_at = datetime.utcnow()
                    metadata.records_synced = records_synced
                    metadata.status = status
                    metadata.error_message = error_message
                else:
                    metadata = SyncMetadata(
                        table_name=self.table_name,
                        last_sync_timestamp=last_timestamp,
                        last_sync_completed_at=datetime.utcnow(),
                        records_synced=records_synced,
                        status=status,
                        error_message=error_message
                    )
                    session.add(metadata)
                
                session.commit()
                logger.debug(f"[{self.table_name}] Metadata updated: {records_synced} records")
        except Exception as e:
            logger.error(f"[{self.table_name}] Error updating sync metadata: {e}")
            raise
    
    def fetch_delta_records(
        self,
        last_sync_timestamp: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Fetch records modified since last sync from SQL Anywhere."""
        try:
            with self.db_manager.get_source_session() as session:
                # Build query to fetch delta records
                if last_sync_timestamp:
                    query = text(
                        f"SELECT * FROM {self.table_name} "
                        f"WHERE {self.timestamp_column} > :last_sync "
                        f"ORDER BY {self.timestamp_column}"
                    )
                    result = session.execute(
                        query,
                        {"last_sync": last_sync_timestamp}
                    )
                else:
                    # First sync - get all records
                    query = text(
                        f"SELECT * FROM {self.table_name} "
                        f"ORDER BY {self.timestamp_column}"
                    )
                    result = session.execute(query)
                
                # Convert to list of dictionaries
                records = []
                for row in result:
                    records.append(dict(row._mapping))
                
                if records:
                    logger.info(f"[{self.table_name}] Fetched {len(records)} delta records")
                return records
        except Exception as e:
            logger.error(f"[{self.table_name}] Error fetching delta records: {e}")
            raise
    
    def upsert_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Upsert records to PostgreSQL using ON CONFLICT clause.
        Returns the number of records processed.
        """
        if not records:
            return 0
        
        try:
            with self.db_manager.get_target_session() as session:
                # Get table metadata
                table = self.db_manager.get_table_metadata(
                    self.table_name,
                    self.db_manager.target_engine
                )
                
                # Process in batches if batch_size is specified
                if self.batch_size and len(records) > self.batch_size:
                    total_upserted = 0
                    for i in range(0, len(records), self.batch_size):
                        batch = records[i:i + self.batch_size]
                        total_upserted += self._upsert_batch(session, table, batch)
                        logger.debug(
                            f"[{self.table_name}] Upserted batch {i//self.batch_size + 1}: "
                            f"{len(batch)} records"
                        )
                    session.commit()
                    return total_upserted
                else:
                    # Single batch
                    count = self._upsert_batch(session, table, records)
                    session.commit()
                    return count
                
        except Exception as e:
            logger.error(f"[{self.table_name}] Error upserting records: {e}")
            raise
    
    def _upsert_batch(self, session, table, records: List[Dict[str, Any]]) -> int:
        """Upsert a single batch of records."""
        # Prepare upsert statement
        stmt = insert(table).values(records)
        
        # Get all column names except primary key for update
        update_columns = {
            col.name: stmt.excluded[col.name]
            for col in table.columns
            if col.name != self.primary_key
        }
        
        # Create upsert with ON CONFLICT DO UPDATE
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[self.primary_key],
            set_=update_columns
        )
        
        # Execute upsert
        session.execute(upsert_stmt)
        return len(records)
    
    def sync(self) -> Dict[str, Any]:
        """
        Perform a single sync operation for this table.
        Returns sync statistics.
        """
        sync_start = datetime.utcnow()
        logger.info(f"[{self.table_name}] Starting sync")
        
        try:
            # Get last sync timestamp
            last_sync_timestamp = self.get_last_sync_timestamp()
            
            # Fetch delta records from SQL Anywhere
            records = self.fetch_delta_records(last_sync_timestamp)
            
            if not records:
                return {
                    'table_name': self.table_name,
                    'status': 'success',
                    'records_synced': 0,
                    'sync_duration_seconds': (datetime.utcnow() - sync_start).total_seconds()
                }
            
            # Upsert records to PostgreSQL
            records_synced = self.upsert_records(records)
            
            # Get the latest timestamp from synced records
            latest_timestamp = max(
                record[self.timestamp_column]
                for record in records
                if record.get(self.timestamp_column)
            )
            
            # Update sync metadata
            self.update_sync_metadata(
                last_timestamp=latest_timestamp,
                records_synced=records_synced,
                status='success'
            )
            
            sync_duration = (datetime.utcnow() - sync_start).total_seconds()
            logger.info(
                f"[{self.table_name}] Sync completed: {records_synced} records "
                f"in {sync_duration:.2f}s"
            )
            
            return {
                'table_name': self.table_name,
                'status': 'success',
                'records_synced': records_synced,
                'sync_duration_seconds': sync_duration,
                'latest_timestamp': latest_timestamp
            }
        
        except Exception as e:
            logger.error(f"[{self.table_name}] Sync failed: {e}", exc_info=True)
            
            # Update metadata with error
            try:
                self.update_sync_metadata(
                    last_timestamp=last_sync_timestamp,
                    records_synced=0,
                    status='failed',
                    error_message=str(e)
                )
            except Exception as meta_error:
                logger.error(f"[{self.table_name}] Failed to update error metadata: {meta_error}")
            
            return {
                'table_name': self.table_name,
                'status': 'failed',
                'error': str(e),
                'sync_duration_seconds': (datetime.utcnow() - sync_start).total_seconds()
            }


class MultiTableSyncService:
    """Service to sync multiple tables in parallel."""
    
    def __init__(self, db_manager: DatabaseManager, table_configs: List[TableConfig], max_workers: int = 5):
        """
        Initialize multi-table sync service.
        
        Args:
            db_manager: Database manager instance
            table_configs: List of table configurations
            max_workers: Maximum number of parallel sync operations
        """
        self.db_manager = db_manager
        self.table_configs = table_configs
        self.max_workers = max_workers
        self.table_services = {
            config.name: TableSyncService(db_manager, config)
            for config in table_configs
        }
    
    def sync_all(self, parallel: bool = True) -> Dict[str, Any]:
        """
        Sync all configured tables.
        
        Args:
            parallel: If True, sync tables in parallel; if False, sync sequentially
        
        Returns:
            Dictionary with overall sync statistics
        """
        sync_start = datetime.utcnow()
        logger.info(f"Starting multi-table sync for {len(self.table_configs)} tables")
        
        if parallel:
            results = self._sync_parallel()
        else:
            results = self._sync_sequential()
        
        # Calculate overall statistics
        total_records = sum(r['records_synced'] for r in results)
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'failed')
        total_duration = (datetime.utcnow() - sync_start).total_seconds()
        
        summary = {
            'status': 'success' if failed == 0 else 'partial' if successful > 0 else 'failed',
            'total_tables': len(self.table_configs),
            'successful_tables': successful,
            'failed_tables': failed,
            'total_records_synced': total_records,
            'total_duration_seconds': total_duration,
            'table_results': results
        }
        
        logger.info(
            f"Multi-table sync completed: {successful}/{len(self.table_configs)} tables successful, "
            f"{total_records} total records in {total_duration:.2f}s"
        )
        
        return summary
    
    def _sync_parallel(self) -> List[Dict[str, Any]]:
        """Sync tables in parallel using thread pool."""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all sync tasks
            future_to_table = {
                executor.submit(service.sync): config.name
                for config, service in zip(self.table_configs, self.table_services.values())
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_table):
                table_name = future_to_table[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"[{table_name}] Unexpected error in parallel sync: {e}")
                    results.append({
                        'table_name': table_name,
                        'status': 'failed',
                        'error': str(e),
                        'records_synced': 0,
                        'sync_duration_seconds': 0
                    })
        
        return results
    
    def _sync_sequential(self) -> List[Dict[str, Any]]:
        """Sync tables sequentially."""
        results = []
        
        for service in self.table_services.values():
            try:
                result = service.sync()
                results.append(result)
            except Exception as e:
                logger.error(f"[{service.table_name}] Unexpected error in sequential sync: {e}")
                results.append({
                    'table_name': service.table_name,
                    'status': 'failed',
                    'error': str(e),
                    'records_synced': 0,
                    'sync_duration_seconds': 0
                })
        
        return results
    
    def sync_table(self, table_name: str) -> Dict[str, Any]:
        """Sync a specific table by name."""
        if table_name not in self.table_services:
            raise ValueError(f"Table '{table_name}' not found in configuration")
        
        return self.table_services[table_name].sync()
