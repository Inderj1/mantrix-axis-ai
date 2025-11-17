#!/usr/bin/env python3
"""Test Task 1: Database Type Parameter in SQLGenerator"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_default_bigquery():
    """Test that default initialization uses BigQuery"""
    from src.core.sql_generator import SQLGenerator

    print("Test 1: Default initialization (BigQuery)...")
    try:
        generator = SQLGenerator()
        assert generator.database_type == 'bigquery', f"Expected 'bigquery', got '{generator.database_type}'"
        assert generator.database_config == {}, f"Expected empty config, got {generator.database_config}"
        print("✅ PASSED: Default initialization works (BigQuery)")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_explicit_bigquery():
    """Test explicit BigQuery initialization"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 2: Explicit BigQuery initialization...")
    try:
        generator = SQLGenerator(database_type='bigquery')
        assert generator.database_type == 'bigquery'
        print("✅ PASSED: Explicit BigQuery initialization works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_snowflake_type():
    """Test Snowflake database type"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 3: Snowflake database type...")
    try:
        config = {
            'account': 'test_account',
            'user': 'test_user',
            'password': 'test_password',
            'warehouse': 'TEST_WH'
        }
        generator = SQLGenerator(database_type='snowflake', database_config=config)
        assert generator.database_type == 'snowflake'
        # Note: config may be modified by connector, so just check database_type
        print("✅ PASSED: Snowflake initialization works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_invalid_database_type():
    """Test that invalid database types are rejected"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 4: Invalid database type rejection...")
    try:
        generator = SQLGenerator(database_type='invalid_db')
        print("❌ FAILED: Should have raised ValueError for invalid database type")
        return False
    except ValueError as e:
        if "Unsupported database type" in str(e):
            print(f"✅ PASSED: Invalid database type correctly rejected: {e}")
            return True
        else:
            print(f"❌ FAILED: Wrong error message: {e}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected exception: {e}")
        return False

def test_supported_types():
    """Test all supported database types"""
    from src.core.sql_generator import SQLGenerator
    from src.db.connector_factory import ConnectorFactory

    print("\nTest 5: All supported database types...")
    supported = ConnectorFactory.get_supported_types()
    print(f"Supported types: {', '.join(supported)}")

    # Minimal configs for each database type (for testing only)
    configs = {
        'bigquery': {},  # Uses settings by default
        'snowflake': {
            'account': 'test_account',
            'user': 'test_user',
            'password': 'test_password',
            'warehouse': 'TEST_WH'
        },
        'postgresql': {
            'host': 'localhost',
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_password'
        },
        'redshift': {
            'host': 'localhost',
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_password'
        },
        'databricks': {
            'server_hostname': 'test.cloud.databricks.com',
            'http_path': '/sql/1.0/warehouses/test',
            'access_token': 'test_token'
        }
    }

    all_passed = True
    for db_type in supported:
        try:
            config = configs.get(db_type, {})
            generator = SQLGenerator(database_type=db_type, database_config=config)
            assert generator.database_type == db_type
            print(f"  ✅ {db_type}: OK")
        except Exception as e:
            print(f"  ❌ {db_type}: FAILED - {e}")
            all_passed = False

    if all_passed:
        print("✅ PASSED: All supported types work")
    else:
        print("❌ FAILED: Some database types failed")

    return all_passed

if __name__ == "__main__":
    print("="*60)
    print("Task 1: Database Type Parameter Tests")
    print("="*60)

    tests = [
        test_default_bigquery,
        test_explicit_bigquery,
        test_snowflake_type,
        test_invalid_database_type,
        test_supported_types
    ]

    results = [test() for test in tests]

    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)

    if all(results):
        print("✅ ALL TESTS PASSED - Task 1 Complete!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
