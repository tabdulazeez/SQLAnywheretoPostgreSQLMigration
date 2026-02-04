"""
Apache Airflow DAG for SQL Anywhere to PostgreSQL sync.
This DAG runs hourly and syncs all configured tables.

Installation:
    1. Copy this file to your Airflow DAGs folder (usually ~/airflow/dags/)
    2. Update the SYNC_PROJECT_PATH to point to your sync project directory
    3. Ensure all dependencies are installed in Airflow's Python environment
    4. Configure Airflow connections or use environment variables for credentials

Usage:
    - The DAG will run hourly by default
    - Modify schedule_interval to change frequency
    - Check Airflow UI for execution logs and status
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
import os

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================

# Path to your sync project directory
SYNC_PROJECT_PATH = '/Users/teejay/dev/SQLAnywheretoPostgreSQLMigration'

# Environment variables (optional - can also use Airflow Variables/Connections)
ENVIRONMENT_VARS = {
    # SQL Anywhere
    'SQLANY_HOST': 'localhost',
    'SQLANY_PORT': '2638',
    'SQLANY_DATABASE': 'your_database',
    'SQLANY_USER': 'your_user',
    'SQLANY_PASSWORD': 'your_password',
    
    # PostgreSQL
    'POSTGRES_HOST': 'localhost',
    'POSTGRES_PORT': '5432',
    'POSTGRES_DATABASE': 'your_database',
    'POSTGRES_USER': 'your_user',
    'POSTGRES_PASSWORD': 'your_password',
    
    # Sync Configuration
    'SYNC_INTERVAL_SECONDS': '3600',  # Not used in scheduled mode
    'SYNC_PARALLEL_TABLES': '5',
    'SYNC_CONFIG_FILE': 'tables_config.json',
    'LOG_LEVEL': 'INFO',
    'LOG_FILE': '/tmp/sync_service_airflow.log',
}

# ============================================================================
# DAG DEFINITION
# ============================================================================

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['your-email@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

dag = DAG(
    'sqlany_to_postgres_sync',
    default_args=default_args,
    description='Hourly sync from SQL Anywhere to PostgreSQL',
    schedule_interval='0 * * * *',  # Run every hour at minute 0
    start_date=days_ago(1),
    catchup=False,  # Don't backfill missed runs
    max_active_runs=1,  # Only one run at a time
    tags=['database', 'sync', 'sql-anywhere', 'postgresql'],
)


# ============================================================================
# TASK DEFINITIONS
# ============================================================================

def run_sync_task(**context):
    """
    Python callable to run the sync job.
    This imports and runs the sync job directly in Python.
    """
    # Add project path to sys.path
    if SYNC_PROJECT_PATH not in sys.path:
        sys.path.insert(0, SYNC_PROJECT_PATH)
    
    # Set environment variables
    for key, value in ENVIRONMENT_VARS.items():
        os.environ[key] = value
    
    # Import and run sync job
    from sync_job import run_sync_job
    
    exit_code = run_sync_job()
    
    # Raise exception if sync failed
    if exit_code == 1:
        raise Exception("Sync completed with partial success - some tables failed")
    elif exit_code == 2:
        raise Exception("Sync failed - all tables failed or critical error")
    elif exit_code == 3:
        raise Exception("Configuration error")
    
    return f"Sync completed successfully with exit code {exit_code}"


# Task 1: Pre-sync health check
health_check = BashOperator(
    task_id='health_check',
    bash_command=f"""
    cd {SYNC_PROJECT_PATH}
    python3 -c "from config import Config; Config.validate(); print('Health check passed')"
    """,
    dag=dag,
)

# Task 2: Run sync job (Option A: Using Python operator)
sync_tables_python = PythonOperator(
    task_id='sync_tables_python',
    python_callable=run_sync_task,
    provide_context=True,
    dag=dag,
)

# Task 2 Alternative: Run sync job (Option B: Using Bash operator)
sync_tables_bash = BashOperator(
    task_id='sync_tables_bash',
    bash_command=f"""
    cd {SYNC_PROJECT_PATH}
    export SQLANY_HOST="{ENVIRONMENT_VARS['SQLANY_HOST']}"
    export SQLANY_PORT="{ENVIRONMENT_VARS['SQLANY_PORT']}"
    export SQLANY_DATABASE="{ENVIRONMENT_VARS['SQLANY_DATABASE']}"
    export SQLANY_USER="{ENVIRONMENT_VARS['SQLANY_USER']}"
    export SQLANY_PASSWORD="{ENVIRONMENT_VARS['SQLANY_PASSWORD']}"
    export POSTGRES_HOST="{ENVIRONMENT_VARS['POSTGRES_HOST']}"
    export POSTGRES_PORT="{ENVIRONMENT_VARS['POSTGRES_PORT']}"
    export POSTGRES_DATABASE="{ENVIRONMENT_VARS['POSTGRES_DATABASE']}"
    export POSTGRES_USER="{ENVIRONMENT_VARS['POSTGRES_USER']}"
    export POSTGRES_PASSWORD="{ENVIRONMENT_VARS['POSTGRES_PASSWORD']}"
    export SYNC_PARALLEL_TABLES="{ENVIRONMENT_VARS['SYNC_PARALLEL_TABLES']}"
    export SYNC_CONFIG_FILE="{ENVIRONMENT_VARS['SYNC_CONFIG_FILE']}"
    export LOG_LEVEL="{ENVIRONMENT_VARS['LOG_LEVEL']}"
    export LOG_FILE="{ENVIRONMENT_VARS['LOG_FILE']}"
    
    python3 sync_job.py
    """,
    dag=dag,
)

# Task 3: Post-sync validation
post_sync_validation = BashOperator(
    task_id='post_sync_validation',
    bash_command=f"""
    cd {SYNC_PROJECT_PATH}
    python3 main.py --status
    """,
    dag=dag,
)

# ============================================================================
# TASK DEPENDENCIES
# ============================================================================

# Choose one of the sync task options:
# Option A: Python operator (recommended for better error handling)
health_check >> sync_tables_python >> post_sync_validation

# Option B: Bash operator (uncomment to use instead)
# health_check >> sync_tables_bash >> post_sync_validation


# ============================================================================
# ALTERNATIVE DAG CONFIGURATIONS
# ============================================================================

# Example 1: Run every 30 minutes
# schedule_interval='*/30 * * * *'

# Example 2: Run every 6 hours
# schedule_interval='0 */6 * * *'

# Example 3: Run daily at 2 AM
# schedule_interval='0 2 * * *'

# Example 4: Run on weekdays only at 9 AM
# schedule_interval='0 9 * * 1-5'

# Example 5: Use Airflow's preset intervals
# from airflow.timetables.interval import CronDataIntervalTimetable
# schedule_interval='@hourly'  # or @daily, @weekly, @monthly
