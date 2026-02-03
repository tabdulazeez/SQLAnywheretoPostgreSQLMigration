"""
Table configuration for multi-table sync.
Supports both YAML file and environment variable configuration.
"""
import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TableConfig:
    """Configuration for a single table sync."""
    name: str
    primary_key: str = 'id'
    timestamp_column: str = 'last_modified'
    enabled: bool = True
    batch_size: Optional[int] = None  # Optional batch size for large tables
    
    def __repr__(self):
        return f"TableConfig(name='{self.name}', pk='{self.primary_key}', ts='{self.timestamp_column}')"


class TableConfigManager:
    """Manages configuration for multiple tables."""
    
    def __init__(self, config_source: Optional[str] = None):
        """
        Initialize table configuration manager.
        
        Args:
            config_source: Path to JSON config file or None to use env vars
        """
        self.config_source = config_source
        self.tables: List[TableConfig] = []
        self._load_config()
    
    def _load_config(self):
        """Load table configuration from file or environment."""
        if self.config_source and Path(self.config_source).exists():
            self._load_from_file()
        else:
            self._load_from_env()
    
    def _load_from_file(self):
        """Load table configuration from JSON file."""
        try:
            with open(self.config_source, 'r') as f:
                config_data = json.load(f)
            
            for table_data in config_data.get('tables', []):
                table = TableConfig(
                    name=table_data['name'],
                    primary_key=table_data.get('primary_key', 'id'),
                    timestamp_column=table_data.get('timestamp_column', 'last_modified'),
                    enabled=table_data.get('enabled', True),
                    batch_size=table_data.get('batch_size')
                )
                self.tables.append(table)
            
            print(f"Loaded {len(self.tables)} table configurations from {self.config_source}")
        
        except Exception as e:
            raise ValueError(f"Error loading table config from file: {e}")
    
    def _load_from_env(self):
        """Load table configuration from environment variables."""
        # Support both single table (legacy) and multi-table config
        
        # Check for multi-table JSON config in env
        tables_json = os.getenv('SYNC_TABLES_JSON')
        if tables_json:
            try:
                tables_data = json.loads(tables_json)
                for table_data in tables_data:
                    table = TableConfig(
                        name=table_data['name'],
                        primary_key=table_data.get('primary_key', 'id'),
                        timestamp_column=table_data.get('timestamp_column', 'last_modified'),
                        enabled=table_data.get('enabled', True),
                        batch_size=table_data.get('batch_size')
                    )
                    self.tables.append(table)
                return
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in SYNC_TABLES_JSON: {e}")
        
        # Check for comma-separated table names
        tables_str = os.getenv('SYNC_TABLES')
        if tables_str:
            table_names = [t.strip() for t in tables_str.split(',')]
            default_pk = os.getenv('SYNC_PRIMARY_KEY', 'id')
            default_ts = os.getenv('SYNC_TIMESTAMP_COLUMN', 'last_modified')
            
            for name in table_names:
                if name:
                    table = TableConfig(
                        name=name,
                        primary_key=default_pk,
                        timestamp_column=default_ts,
                        enabled=True
                    )
                    self.tables.append(table)
            return
        
        # Fall back to single table (legacy support)
        table_name = os.getenv('SYNC_TABLE_NAME')
        if table_name:
            table = TableConfig(
                name=table_name,
                primary_key=os.getenv('SYNC_PRIMARY_KEY', 'id'),
                timestamp_column=os.getenv('SYNC_TIMESTAMP_COLUMN', 'last_modified'),
                enabled=True
            )
            self.tables.append(table)
    
    def get_enabled_tables(self) -> List[TableConfig]:
        """Get list of enabled tables."""
        return [t for t in self.tables if t.enabled]
    
    def get_table(self, name: str) -> Optional[TableConfig]:
        """Get configuration for a specific table."""
        for table in self.tables:
            if table.name == name:
                return table
        return None
    
    def validate(self):
        """Validate table configuration."""
        if not self.tables:
            raise ValueError("No tables configured for sync")
        
        # Check for duplicate table names
        table_names = [t.name for t in self.tables]
        if len(table_names) != len(set(table_names)):
            raise ValueError("Duplicate table names found in configuration")
        
        # Validate each table
        for table in self.tables:
            if not table.name:
                raise ValueError("Table name cannot be empty")
            if not table.primary_key:
                raise ValueError(f"Primary key not specified for table {table.name}")
            if not table.timestamp_column:
                raise ValueError(f"Timestamp column not specified for table {table.name}")
    
    def __len__(self):
        """Return number of configured tables."""
        return len(self.tables)
    
    def __iter__(self):
        """Iterate over table configurations."""
        return iter(self.tables)
