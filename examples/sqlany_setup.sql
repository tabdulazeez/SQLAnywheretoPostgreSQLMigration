-- ============================================================================
-- SQL Anywhere Sample Table Setup
-- ============================================================================
-- This script creates a sample table in SQL Anywhere for testing the sync service

-- Create sample table
CREATE TABLE employees (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    salary DECIMAL(10, 2),
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    last_modified TIMESTAMP DEFAULT CURRENT TIMESTAMP NOT NULL
);

-- Create trigger to auto-update last_modified on changes
CREATE TRIGGER update_employees_timestamp
BEFORE UPDATE ON employees
FOR EACH ROW
BEGIN
    SET NEW.last_modified = CURRENT TIMESTAMP;
END;

-- Create index on last_modified for better performance
CREATE INDEX idx_employees_last_modified ON employees(last_modified);

-- Insert sample data
INSERT INTO employees (id, name, email, department, salary, hire_date) VALUES
(1, 'John Doe', 'john.doe@example.com', 'Engineering', 85000.00, '2020-01-15'),
(2, 'Jane Smith', 'jane.smith@example.com', 'Marketing', 75000.00, '2020-03-20'),
(3, 'Bob Johnson', 'bob.johnson@example.com', 'Sales', 70000.00, '2019-11-10'),
(4, 'Alice Williams', 'alice.williams@example.com', 'Engineering', 90000.00, '2021-02-01'),
(5, 'Charlie Brown', 'charlie.brown@example.com', 'HR', 65000.00, '2020-07-15');

-- Verify data
SELECT * FROM employees ORDER BY id;

-- Show table structure
SELECT column_name, data_type, is_nullable
FROM SYS.SYSCOLUMN c
JOIN SYS.SYSTABLE t ON c.table_id = t.table_id
WHERE t.table_name = 'employees'
ORDER BY c.column_id;
