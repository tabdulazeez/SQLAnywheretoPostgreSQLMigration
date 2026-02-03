"""
Sync service for syncing records from SQL Anywhere to PostgreSQL.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from config import Config
from database import DatabaseManager
from models import SyncMetadata

logger = logging.getLogger(__name__)


class SyncService:
    """Service to sync records from SQL Anywhere to PostgreSQL."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize sync service with database manager."""
        self.db_manager = db_manager
        self.table_name = Config.SYNC_TABLE_NAME
        self.primary_key = Config.SYNC_PRIMARY_KEY
        self.timestamp_column = Config.SYNC_TIMESTAMP_COLUMN
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the last successful sync timestamp from metadata table."""
        try:
            with self.db_manager.get_target_session() as session:
                metadata = session.query(SyncMetadata).filter_by(
                    table_name=self.table_name
                ).first()
                
                if metadata:
                    logger.info(
                        f"Last sync timestamp for {self.table_name}: "
                        f"{metadata.last_sync_timestamp}"
                    )
                    return metadata.last_sync_timestamp
                else:
                    logger.info(
                        f"No previous sync found for {self.table_name}, "
                        "will sync all records"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
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
                logger.info(f"Sync metadata updated: {records_synced} records synced")
        except Exception as e:
            logger.error(f"Error updating sync metadata: {e}")
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
                
                logger.info(f"Fetched {len(records)} delta records from SQL Anywhere")
                return records
        except Exception as e:
            logger.error(f"Error fetching delta records: {e}")
            raise
    
    def upsert_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Upsert records to PostgreSQL using ON CONFLICT clause.
        Returns the number of records processed.
        """
        if not records:
            logger.info("No records to upsert")
            return 0
        
        try:
            with self.db_manager.get_target_session() as session:
                # Get table metadata
                table = self.db_manager.get_table_metadata(
                    self.table_name,
                    self.db_manager.target_engine
                )
                
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
                session.commit()
                
                logger.info(f"Successfully upserted {len(records)} records to PostgreSQL")
                return len(records)
        except Exception as e:
            logger.error(f"Error upserting records: {e}")
            raise
    
    def sync(self) -> Dict[str, Any]:
        """
        Perform a single sync operation.
        Returns sync statistics.
        """
        sync_start = datetime.utcnow()
        logger.info(f"Starting sync for table: {self.table_name}")
        
        try:
            # Get last sync timestamp
            last_sync_timestamp = self.get_last_sync_timestamp()
            
            # Fetch delta records from SQL Anywhere
            records = self.fetch_delta_records(last_sync_timestamp)
            
            if not records:
                logger.info("No new records to sync")
                return {
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
                f"Sync completed successfully: {records_synced} records "
                f"in {sync_duration:.2f} seconds"
            )
            
            return {
                'status': 'success',
                'records_synced': records_synced,
                'sync_duration_seconds': sync_duration,
                'latest_timestamp': latest_timestamp
            }
        
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            
            # Update metadata with error
            try:
                self.update_sync_metadata(
                    last_timestamp=last_sync_timestamp,
                    records_synced=0,
                    status='failed',
                    error_message=str(e)
                )
            except Exception as meta_error:
                logger.error(f"Failed to update error metadata: {meta_error}")
            
            return {
                'status': 'failed',
                'error': str(e),
                'sync_duration_seconds': (datetime.utcnow() - sync_start).total_seconds()
            }
