"""
Configuration module for SQL Anywhere to PostgreSQL sync service.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for sync service."""
    
    # SQL Anywhere Configuration
    SQLANY_HOST = os.getenv('SQLANY_HOST', 'localhost')
    SQLANY_PORT = os.getenv('SQLANY_PORT', '2638')
    SQLANY_DATABASE = os.getenv('SQLANY_DATABASE')
    SQLANY_USER = os.getenv('SQLANY_USER')
    SQLANY_PASSWORD = os.getenv('SQLANY_PASSWORD')
    
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DATABASE = os.getenv('POSTGRES_DATABASE')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    
    # Sync Configuration
    SYNC_INTERVAL_SECONDS = int(os.getenv('SYNC_INTERVAL_SECONDS', '30'))
    SYNC_PARALLEL_TABLES = int(os.getenv('SYNC_PARALLEL_TABLES', '5'))  # Number of tables to sync in parallel
    SYNC_CONFIG_FILE = os.getenv('SYNC_CONFIG_FILE', 'tables_config.json')  # Path to table config file
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'sync_service.log')
    
    @classmethod
    def get_sqlany_connection_string(cls) -> str:
        """Generate SQL Anywhere connection string."""
        return (
            f"sqlany://{cls.SQLANY_USER}:{cls.SQLANY_PASSWORD}"
            f"@{cls.SQLANY_HOST}:{cls.SQLANY_PORT}/{cls.SQLANY_DATABASE}"
        )
    
    @classmethod
    def get_postgres_connection_string(cls) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DATABASE}"
        )
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        required_fields = [
            'SQLANY_DATABASE', 'SQLANY_USER', 'SQLANY_PASSWORD',
            'POSTGRES_DATABASE', 'POSTGRES_USER', 'POSTGRES_PASSWORD'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(
                f"Missing required configuration fields: {', '.join(missing_fields)}"
            )
