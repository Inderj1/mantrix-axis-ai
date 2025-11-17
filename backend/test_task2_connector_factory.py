#!/usr/bin/env python3
"""Test Task 2: Connector Factory Integration"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_bigquery_backward_compatibility():
    """Test that BigQuery still works (backward compatibility)"""
    from src.core.sql_generator import SQLGenerator

    print("Test 1: BigQuery backward compatibility...")
    try:
        generator = SQLGenerator()

        # Check that db_client is created
        assert hasattr(generator, 'db_client'), "db_client not found"
        assert generator.db_client is not None, "db_client is None"

        # Check that bq_client alias exists for backward compatibility
        assert hasattr(generator, 'bq_client'), "bq_client alias not found"
        assert generator.bq_client is generator.db_client, "bq_client should point to db_client"

        # Check database capabilities
        assert hasattr(generator, 'db_capabilities'), "db_capabilities not found"
        assert generator.db_capabilities.database_type == 'bigquery', \
            f"Expected database_type 'bigquery', got '{generator.db_capabilities.database_type}'"

        print("✅ PASSED: BigQuery backward compatibility maintained")
        print(f"   - Database: {generator.db_capabilities.database_name}")
        print(f"   - db_client and bq_client both exist")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connector_factory_used():
    """Test that connector factory is being used"""
    from src.core.sql_generator import SQLGenerator
    from src.db.connectors.bigquery_connector import BigQueryConnector

    print("\nTest 2: Connector factory integration...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # Check that db_client is a connector instance
        assert isinstance(generator.db_client, BigQueryConnector), \
            f"Expected BigQueryConnector, got {type(generator.db_client)}"

        # Check that it has the standard connector interface
        assert hasattr(generator.db_client, 'execute_query'), "execute_query method not found"
        assert hasattr(generator.db_client, 'get_dataset_schema'), "get_dataset_schema method not found"
        assert hasattr(generator.db_client, 'validate_query'), "validate_query method not found"
        assert hasattr(generator.db_client, 'get_capabilities'), "get_capabilities method not found"
        assert hasattr(generator.db_client, 'test_connection'), "test_connection method not found"

        print("✅ PASSED: Connector factory is being used")
        print(f"   - Connector type: {type(generator.db_client).__name__}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_database_capabilities_stored():
    """Test that database capabilities are stored"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 3: Database capabilities stored...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # Check capabilities
        caps = generator.db_capabilities
        assert caps is not None, "db_capabilities is None"
        assert hasattr(caps, 'database_type'), "database_type not in capabilities"
        assert hasattr(caps, 'database_name'), "database_name not in capabilities"
        assert hasattr(caps, 'supports_window_functions'), "supports_window_functions not in capabilities"
        assert hasattr(caps, 'supports_ctes'), "supports_ctes not in capabilities"

        print("✅ PASSED: Database capabilities are stored")
        print(f"   - Type: {caps.database_type}")
        print(f"   - Name: {caps.database_name}")
        print(f"   - Window Functions: {caps.supports_window_functions}")
        print(f"   - CTEs: {caps.supports_ctes}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_config_handling():
    """Test database configuration handling"""
    from src.core.sql_generator import SQLGenerator
    from src.config import settings

    print("\nTest 4: Configuration handling...")
    try:
        # Test that BigQuery uses settings by default
        generator = SQLGenerator(database_type='bigquery')

        # Verify project_id and dataset_id are set (from settings)
        assert hasattr(generator.db_client, 'project_id'), "project_id not found"
        assert hasattr(generator.db_client, 'dataset_id'), "dataset_id not found"
        assert generator.db_client.project_id == settings.google_cloud_project, \
            "project_id doesn't match settings"
        assert generator.db_client.dataset_id == settings.bigquery_dataset, \
            "dataset_id doesn't match settings"

        print("✅ PASSED: Configuration handling works")
        print(f"   - Project: {generator.db_client.project_id}")
        print(f"   - Dataset: {generator.db_client.dataset_id}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Task 2: Connector Factory Integration Tests")
    print("="*60)

    tests = [
        test_bigquery_backward_compatibility,
        test_connector_factory_used,
        test_database_capabilities_stored,
        test_config_handling
    ]

    results = [test() for test in tests]

    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)

    if all(results):
        print("✅ ALL TESTS PASSED - Task 2 Complete!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
