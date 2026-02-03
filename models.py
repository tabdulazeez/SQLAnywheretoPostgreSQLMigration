"""
SQLAlchemy models for sync metadata tracking.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SyncMetadata(Base):
    """
    Metadata table to track sync state.
    This table is created in PostgreSQL to track the last successful sync.
    """
    __tablename__ = 'sync_metadata'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(255), nullable=False, unique=True)
    last_sync_timestamp = Column(DateTime, nullable=True)
    last_sync_completed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    records_synced = Column(Integer, default=0)
    status = Column(String(50), default='success')  # success, failed, running
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return (
            f"<SyncMetadata(table='{self.table_name}', "
            f"last_sync='{self.last_sync_timestamp}', "
            f"status='{self.status}')>"
        )
