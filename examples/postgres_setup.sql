-- ============================================================================
-- PostgreSQL Sample Table Setup
-- ============================================================================
-- This script creates a sample table in PostgreSQL for testing the sync service

-- Create sample table (matching SQL Anywhere structure)
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    salary DECIMAL(10, 2),
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create index on last_modified for better query performance
CREATE INDEX IF NOT EXISTS idx_employees_last_modified ON employees(last_modified);

-- Create index on email for lookups
CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email);

-- Add comment to table
COMMENT ON TABLE employees IS 'Employee records synced from SQL Anywhere';

-- Add comments to columns
COMMENT ON COLUMN employees.id IS 'Primary key - employee ID';
COMMENT ON COLUMN employees.last_modified IS 'Timestamp of last modification - used for delta sync';

-- Verify table structure
\d employees

-- The sync_metadata table will be created automatically by the sync service
-- But here's what it looks like for reference:
/*
CREATE TABLE IF NOT EXISTS sync_metadata (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL UNIQUE,
    last_sync_timestamp TIMESTAMP,
    last_sync_completed_at TIMESTAMP NOT NULL,
    records_synced INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT
);
*/

-- Query to check sync metadata after running the service
-- SELECT * FROM sync_metadata WHERE table_name = 'employees';
