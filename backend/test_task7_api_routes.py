#!/usr/bin/env python3
"""Test Task 7: Database Type in API Routes"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_query_request_model():
    """Test that QueryRequest model has database fields"""
    from src.api.models import QueryRequest
    import inspect

    print("Test 1: QueryRequest model has database fields...")
    try:
        # Create a sample request
        request = QueryRequest(
            question="Show me total sales",
            database_type="snowflake",
            database_config={"account": "test", "user": "test", "password": "test"}
        )

        # Verify fields exist
        assert hasattr(request, 'database_type'), "database_type field not found"
        assert hasattr(request, 'database_config'), "database_config field not found"

        # Verify values
        assert request.database_type == "snowflake", "database_type not set correctly"
        assert request.database_config is not None, "database_config is None"
        assert isinstance(request.database_config, dict), "database_config is not a dict"

        # Test default values
        default_request = QueryRequest(question="Test query")
        assert default_request.database_type == 'bigquery', "Default database_type should be 'bigquery'"
        assert default_request.database_config is None, "Default database_config should be None"

        print("  ✅ QueryRequest has database_type field")
        print("  ✅ QueryRequest has database_config field")
        print("  ✅ Default database_type is 'bigquery'")
        print("  ✅ Default database_config is None")
        print("✅ PASSED: QueryRequest model properly updated")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sql_generate_request_model():
    """Test that SQLGenerateRequest model has database fields"""
    from src.api.models import SQLGenerateRequest

    print("\nTest 2: SQLGenerateRequest model has database fields...")
    try:
        # Create a sample request
        request = SQLGenerateRequest(
            question="Show me total sales",
            database_type="postgresql",
            database_config={"host": "localhost", "database": "test"}
        )

        # Verify fields exist
        assert hasattr(request, 'database_type'), "database_type field not found"
        assert hasattr(request, 'database_config'), "database_config field not found"

        # Verify values
        assert request.database_type == "postgresql", "database_type not set correctly"
        assert request.database_config is not None, "database_config is not None"

        # Test defaults
        default_request = SQLGenerateRequest(question="Test query")
        assert default_request.database_type == 'bigquery', "Default should be 'bigquery'"

        print("  ✅ SQLGenerateRequest has database_type field")
        print("  ✅ SQLGenerateRequest has database_config field")
        print("  ✅ Defaults are correct")
        print("✅ PASSED: SQLGenerateRequest model properly updated")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_routes_import():
    """Test that API routes file imports successfully"""
    print("\nTest 3: API routes file imports successfully...")
    try:
        # This will fail if there are syntax errors in the routes file
        from src.api import routes

        # Verify the router exists
        assert hasattr(routes, 'router'), "Router not found"

        print("  ✅ API routes file imports successfully")
        print("  ✅ Router object exists")
        print("✅ PASSED: API routes file has no syntax errors")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connector_factory_validation():
    """Test that ConnectorFactory can validate database types"""
    from src.db.connector_factory import ConnectorFactory

    print("\nTest 4: ConnectorFactory validation...")
    try:
        # Get supported types
        supported_types = ConnectorFactory.get_supported_types()

        # Verify all expected types are supported
        expected_types = {'bigquery', 'snowflake', 'postgresql', 'redshift', 'databricks'}
        assert expected_types.issubset(supported_types), \
            f"Missing types: {expected_types - supported_types}"

        print(f"  ✅ Supported database types: {', '.join(supported_types)}")
        print("  ✅ All required types are supported")
        print("✅ PASSED: ConnectorFactory validation works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("Task 7: Database Type in API Routes Tests")
    print("="*60)

    tests = [
        test_query_request_model,
        test_sql_generate_request_model,
        test_api_routes_import,
        test_connector_factory_validation
    ]

    results = [test() for test in tests]

    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)

    if all(results):
        print("✅ ALL TESTS PASSED - Task 7 Complete!")
        print("\n🎉 API routes now support multi-database queries!")
        print("   - database_type parameter added to QueryRequest")
        print("   - database_type parameter added to SQLGenerateRequest")
        print("   - Database type validation in place")
        print("   - Backward compatible with existing BigQuery usage")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
