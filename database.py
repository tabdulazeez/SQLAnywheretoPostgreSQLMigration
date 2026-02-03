"""
Database connection and session management.
"""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from config import Config
from models import Base, SyncMetadata

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections for both SQL Anywhere and PostgreSQL."""
    
    def __init__(self):
        """Initialize database connections."""
        # SQL Anywhere connection (source)
        self.source_engine = create_engine(
            Config.get_sqlany_connection_string(),
            poolclass=NullPool,  # Use NullPool for SQL Anywhere
            echo=False
        )
        
        # PostgreSQL connection (target)
        self.target_engine = create_engine(
            Config.get_postgres_connection_string(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
        
        # Create session factories
        self.SourceSession = sessionmaker(bind=self.source_engine)
        self.TargetSession = sessionmaker(bind=self.target_engine)
        
        # Initialize metadata table in PostgreSQL
        self._initialize_metadata_table()
    
    def _initialize_metadata_table(self):
        """Create sync_metadata table in PostgreSQL if it doesn't exist."""
        try:
            Base.metadata.create_all(self.target_engine)
            logger.info("Sync metadata table initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing metadata table: {e}")
            raise
    
    @contextmanager
    def get_source_session(self) -> Session:
        """Context manager for SQL Anywhere session."""
        session = self.SourceSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_target_session(self) -> Session:
        """Context manager for PostgreSQL session."""
        session = self.TargetSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_table_metadata(self, table_name: str, engine):
        """Get table metadata using reflection."""
        metadata = MetaData()
        try:
            table = Table(table_name, metadata, autoload_with=engine)
            return table
        except Exception as e:
            logger.error(f"Error loading table metadata for {table_name}: {e}")
            raise
    
    def get_table_columns(self, table_name: str, engine) -> list:
        """Get list of column names for a table."""
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return [col['name'] for col in columns]
    
    def close(self):
        """Close all database connections."""
        self.source_engine.dispose()
        self.target_engine.dispose()
        logger.info("Database connections closed")
