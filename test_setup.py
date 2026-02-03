"""
Test script to verify the sync service configuration and connectivity.
Run this before starting the actual sync service.
"""
import sys
from config import Config

def test_configuration():
    """Test configuration validation."""
    print("=" * 70)
    print("Testing Configuration")
    print("=" * 70)
    
    try:
        Config.validate()
        print("✓ Configuration validation passed")
        print(f"  - SQL Anywhere Database: {Config.SQLANY_DATABASE}")
        print(f"  - PostgreSQL Database: {Config.POSTGRES_DATABASE}")
        print(f"  - Sync Table: {Config.SYNC_TABLE_NAME}")
        print(f"  - Primary Key: {Config.SYNC_PRIMARY_KEY}")
        print(f"  - Timestamp Column: {Config.SYNC_TIMESTAMP_COLUMN}")
        print(f"  - Sync Interval: {Config.SYNC_INTERVAL_SECONDS} seconds")
        return True
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False


def test_database_connections():
    """Test database connectivity."""
    print("\n" + "=" * 70)
    print("Testing Database Connections")
    print("=" * 70)
    
    from database import DatabaseManager
    
    try:
        db_manager = DatabaseManager()
        print("✓ Database manager initialized")
        
        # Test SQL Anywhere connection
        print("\nTesting SQL Anywhere connection...")
        try:
            with db_manager.get_source_session() as session:
                result = session.execute("SELECT 1")
                result.fetchone()
                print("✓ SQL Anywhere connection successful")
        except Exception as e:
            print(f"✗ SQL Anywhere connection failed: {e}")
            return False
        
        # Test PostgreSQL connection
        print("\nTesting PostgreSQL connection...")
        try:
            with db_manager.get_target_session() as session:
                result = session.execute("SELECT 1")
                result.fetchone()
                print("✓ PostgreSQL connection successful")
        except Exception as e:
            print(f"✗ PostgreSQL connection failed: {e}")
            return False
        
        # Test metadata table
        print("\nTesting metadata table...")
        try:
            with db_manager.get_target_session() as session:
                from models import SyncMetadata
                count = session.query(SyncMetadata).count()
                print(f"✓ Metadata table accessible ({count} records)")
        except Exception as e:
            print(f"✗ Metadata table test failed: {e}")
            return False
        
        db_manager.close()
        return True
        
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False


def test_table_structure():
    """Test that the source table exists and has required columns."""
    print("\n" + "=" * 70)
    print("Testing Source Table Structure")
    print("=" * 70)
    
    from database import DatabaseManager
    
    try:
        db_manager = DatabaseManager()
        
        # Check if table exists
        print(f"\nChecking table: {Config.SYNC_TABLE_NAME}")
        try:
            columns = db_manager.get_table_columns(
                Config.SYNC_TABLE_NAME,
                db_manager.source_engine
            )
            print(f"✓ Table found with {len(columns)} columns")
            print(f"  Columns: {', '.join(columns)}")
            
            # Check for primary key
            if Config.SYNC_PRIMARY_KEY in columns:
                print(f"✓ Primary key column '{Config.SYNC_PRIMARY_KEY}' found")
            else:
                print(f"✗ Primary key column '{Config.SYNC_PRIMARY_KEY}' not found")
                return False
            
            # Check for timestamp column
            if Config.SYNC_TIMESTAMP_COLUMN in columns:
                print(f"✓ Timestamp column '{Config.SYNC_TIMESTAMP_COLUMN}' found")
            else:
                print(f"✗ Timestamp column '{Config.SYNC_TIMESTAMP_COLUMN}' not found")
                return False
            
            # Get row count
            with db_manager.get_source_session() as session:
                from sqlalchemy import text
                result = session.execute(
                    text(f"SELECT COUNT(*) FROM {Config.SYNC_TABLE_NAME}")
                )
                count = result.scalar()
                print(f"✓ Table contains {count} records")
            
            db_manager.close()
            return True
            
        except Exception as e:
            print(f"✗ Table structure test failed: {e}")
            return False
        
    except Exception as e:
        print(f"✗ Table test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "SQL Anywhere to PostgreSQL Sync - Test Suite" + " " * 13 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    tests = [
        ("Configuration", test_configuration),
        ("Database Connections", test_database_connections),
        ("Table Structure", test_table_structure),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<50} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All tests passed! The service is ready to run.")
        print("\nNext steps:")
        print("  1. Run a single sync: python main.py --once")
        print("  2. Run as daemon:     python main.py --daemon")
        print("  3. Check status:      python main.py --status")
    else:
        print("✗ Some tests failed. Please fix the issues before running the service.")
        sys.exit(1)
    
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
