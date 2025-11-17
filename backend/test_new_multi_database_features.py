#!/usr/bin/env python3
"""Test NEW Multi-Database Features (not backward compatibility)"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_explicit_database_type_parameter():
    """Test EXPLICITLY passing database_type parameter (new feature)"""
    from src.core.sql_generator import SQLGenerator

    print("Test 1: EXPLICITLY passing database_type='bigquery' (NEW API)...")
    try:
        # NEW API: Explicitly specify database type
        generator = SQLGenerator(database_type='bigquery')

        # Verify it used the new parameter
        assert generator.database_type == 'bigquery', "database_type not set"
        assert hasattr(generator, 'db_client'), "db_client not created"
        assert hasattr(generator, 'db_capabilities'), "db_capabilities not set"

        # Verify capabilities were loaded
        assert generator.db_capabilities.database_name == 'Google BigQuery'

        print(f"  ✅ database_type: {generator.database_type}")
        print(f"  ✅ database_name: {generator.db_capabilities.database_name}")
        print(f"  ✅ db_client type: {type(generator.db_client).__name__}")
        print("✅ PASSED: New explicit database_type parameter works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_config_parameter():
    """Test EXPLICITLY passing database_config parameter (new feature)"""
    from src.core.sql_generator import SQLGenerator
    from src.config import settings

    print("\nTest 2: EXPLICITLY passing database_config (NEW API)...")
    try:
        # NEW API: Explicitly specify database config
        config = {
            'project_id': settings.google_cloud_project,
            'dataset_id': settings.bigquery_dataset
        }

        generator = SQLGenerator(
            database_type='bigquery',
            database_config=config
        )

        # Verify config was used
        assert generator.database_config == config, "database_config not stored"
        assert generator.db_client.project_id == config['project_id']
        assert generator.db_client.dataset_id == config['dataset_id']

        print(f"  ✅ Custom config used: {config['project_id']}/{config['dataset_id']}")
        print("✅ PASSED: New database_config parameter works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dialect_guide_generation():
    """Test NEW dialect guide feature for LLM prompts"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 3: NEW dialect guide generation...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # This is a NEW method added in Task 5
        dialect_guide = generator._get_dialect_guide()

        assert len(dialect_guide) > 0, "Dialect guide is empty"
        assert 'BigQuery' in dialect_guide or 'bigquery' in dialect_guide.lower()
        assert 'backticks' in dialect_guide.lower() or '`' in dialect_guide

        print(f"  ✅ Dialect guide generated ({len(dialect_guide)} chars)")
        print(f"  ✅ Contains BigQuery-specific syntax")
        print("✅ PASSED: New dialect guide feature works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_qualifier_abstraction():
    """Test NEW database qualifier helper methods"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 4: NEW database qualifier abstraction...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # These are NEW methods added in Task 3
        db_qual = generator._get_database_qualifier()
        schema_qual = generator._get_schema_qualifier()
        full_qual = generator._get_full_qualifier()

        assert db_qual is not None, "database_qualifier is None"
        assert schema_qual is not None, "schema_qualifier is None"
        assert full_qual is not None, "full_qualifier is None"

        # For BigQuery: database_qualifier = project_id, schema_qualifier = dataset_id
        assert ':' in full_qual or '.' in full_qual, "full_qualifier format unexpected"

        print(f"  ✅ Database qualifier: {db_qual}")
        print(f"  ✅ Schema qualifier: {schema_qual}")
        print(f"  ✅ Full qualifier: {full_qual}")
        print("✅ PASSED: New database qualifier abstraction works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_model_new_fields():
    """Test NEW API model fields for multi-database"""
    from src.api.models import QueryRequest, SQLGenerateRequest

    print("\nTest 5: NEW API model fields...")
    try:
        # Test QueryRequest with NEW fields
        request1 = QueryRequest(
            question="Show me total sales",
            database_type="snowflake",  # NEW field
            database_config={"account": "test"}  # NEW field
        )

        assert request1.database_type == "snowflake"
        assert request1.database_config == {"account": "test"}

        # Test SQLGenerateRequest with NEW fields
        request2 = SQLGenerateRequest(
            question="Show me revenue",
            database_type="postgresql",  # NEW field
            database_config={"host": "localhost"}  # NEW field
        )

        assert request2.database_type == "postgresql"
        assert request2.database_config == {"host": "localhost"}

        print("  ✅ QueryRequest has new database_type field")
        print("  ✅ QueryRequest has new database_config field")
        print("  ✅ SQLGenerateRequest has new database_type field")
        print("  ✅ SQLGenerateRequest has new database_config field")
        print("✅ PASSED: New API model fields work")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_actual_sql_generation_with_dialect():
    """Test actual SQL generation using NEW dialect guide"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 6: SQL generation with NEW dialect guide integration...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # Mock the schema retrieval to avoid BigQuery API calls
        def mock_get_financial_schemas(financial_context, limit=5):
            return [{
                'table_name': 'sales_data',
                'columns': [
                    {'name': 'revenue', 'type': 'FLOAT64'},
                    {'name': 'date', 'type': 'DATE'}
                ],
                'description': 'Sales data table'
            }]

        generator._get_financial_schemas = mock_get_financial_schemas

        # Mock LLM to verify dialect guide is passed
        dialect_guide_received = []

        def mock_generate_sql(query, schemas, **kwargs):
            # This is the NEW feature - dialect guide should be in kwargs
            if 'dialect_guide' in kwargs:
                dialect_guide_received.append(kwargs['dialect_guide'])
            if 'database_type' in kwargs:
                assert kwargs['database_type'] == 'bigquery'
            if 'database_name' in kwargs:
                assert 'BigQuery' in kwargs['database_name']

            return {
                'sql': 'SELECT SUM(revenue) FROM sales_data',
                'explanation': 'Test query',
                'tables_used': ['sales_data'],
                'estimated_complexity': 'low'
            }

        generator.llm_client.generate_sql = mock_generate_sql

        # Generate SQL
        result = generator.generate_sql(
            "Show me total revenue",
            use_vector_search=False,
            max_tables=1
        )

        # Verify dialect guide was passed to LLM
        assert len(dialect_guide_received) > 0, "Dialect guide was not passed to LLM"
        assert len(dialect_guide_received[0]) > 0, "Dialect guide is empty"

        print("  ✅ SQL generation successful")
        print(f"  ✅ Dialect guide passed to LLM ({len(dialect_guide_received[0])} chars)")
        print(f"  ✅ Generated SQL: {result['sql']}")
        print("✅ PASSED: SQL generation with dialect guide works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*70)
    print("Testing NEW Multi-Database Features (Not Backward Compatibility)")
    print("="*70)

    tests = [
        test_explicit_database_type_parameter,
        test_database_config_parameter,
        test_dialect_guide_generation,
        test_database_qualifier_abstraction,
        test_api_model_new_fields,
        test_actual_sql_generation_with_dialect
    ]

    results = [test() for test in tests]

    print("\n" + "="*70)
    print(f"Results: {sum(results)}/{len(results)} NEW FEATURE tests passed")
    print("="*70)

    if all(results):
        print("✅ ALL NEW MULTI-DATABASE FEATURES WORKING!")
        print("\nThese are the NEW features added (not backward compatibility):")
        print("  1. ✅ Explicit database_type parameter")
        print("  2. ✅ Explicit database_config parameter")
        print("  3. ✅ Database-specific SQL dialect guides")
        print("  4. ✅ Database qualifier abstraction (project/dataset vs database/schema)")
        print("  5. ✅ API model fields for database type and config")
        print("  6. ✅ LLM integration with dialect guides")
        sys.exit(0)
    else:
        print("❌ SOME NEW FEATURES FAILED")
        sys.exit(1)
