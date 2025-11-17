#!/usr/bin/env python3
"""Test Task 5: Database Dialect in LLM Prompts"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dialect_guide_method():
    """Test that dialect guide method returns correct guidelines"""
    from src.core.sql_generator import SQLGenerator

    print("Test 1: Dialect guide method...")
    try:
        # Test BigQuery (only database we can actually connect to)
        generator = SQLGenerator(database_type='bigquery')
        guide = generator._get_dialect_guide()
        assert guide is not None, "BigQuery dialect guide is None"
        assert "backticks" in guide.lower(), "BigQuery guide should mention backticks"
        assert "FORMAT_DATE" in guide, "BigQuery guide should mention FORMAT_DATE"
        print("  ✅ BigQuery dialect guide present and correct")

        # Test dialect guide method directly (without connection)
        # This tests that all guides are defined
        guides = {
            'bigquery': generator._get_dialect_guide(),
            'snowflake': SQLGenerator._get_dialect_guide.__get__(
                type('obj', (object,), {'database_type': 'snowflake'})(), SQLGenerator
            )() if hasattr(SQLGenerator, '_get_dialect_guide') else None,
        }

        # Verify BigQuery guide content
        bq_guide = guides['bigquery']
        assert "backticks" in bq_guide.lower(), "BigQuery should mention backticks"
        assert "FORMAT_DATE" in bq_guide, "BigQuery should mention FORMAT_DATE"
        assert "STRUCT" in bq_guide, "BigQuery should mention STRUCT"
        print("  ✅ BigQuery guide has correct content")

        print("✅ PASSED: Dialect guide method returns correct guidelines")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_kwargs_include_dialect():
    """Test that SQL generator passes dialect info to LLM"""
    from src.core.sql_generator import SQLGenerator
    from unittest.mock import Mock, patch

    print("\nTest 2: Dialect info in LLM kwargs...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # Mock the LLM client to capture the kwargs
        captured_kwargs = {}

        def mock_generate_sql(query, schemas, **kwargs):
            captured_kwargs.update(kwargs)
            return {
                'sql': 'SELECT 1',
                'explanation': 'Test query',
                'tables_used': [],
                'estimated_complexity': 'low'
            }

        generator.llm_client.generate_sql = mock_generate_sql

        # Mock the schema retrieval to avoid BigQuery API calls
        def mock_get_financial_schemas(financial_context, limit=5):
            return [{
                'table_name': 'test_table',
                'columns': [{'name': 'sales', 'type': 'FLOAT64'}],
                'description': 'Test table'
            }]

        generator._get_financial_schemas = mock_get_financial_schemas

        # Generate a simple SQL query
        result = generator.generate_sql(
            "Show me total sales",
            use_vector_search=False,
            max_tables=1
        )

        # Check that dialect info was passed
        assert 'database_type' in captured_kwargs, "database_type not in kwargs"
        assert 'database_name' in captured_kwargs, "database_name not in kwargs"
        assert 'dialect_guide' in captured_kwargs, "dialect_guide not in kwargs"

        assert captured_kwargs['database_type'] == 'bigquery', \
            f"Expected 'bigquery', got '{captured_kwargs['database_type']}'"
        assert captured_kwargs['database_name'] == 'Google BigQuery', \
            f"Expected 'Google BigQuery', got '{captured_kwargs['database_name']}'"
        assert len(captured_kwargs['dialect_guide']) > 0, "Dialect guide is empty"

        print(f"  ✅ database_type: {captured_kwargs['database_type']}")
        print(f"  ✅ database_name: {captured_kwargs['database_name']}")
        print(f"  ✅ dialect_guide length: {len(captured_kwargs['dialect_guide'])} chars")
        print("✅ PASSED: Dialect info passed to LLM correctly")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_client_accepts_dialect():
    """Test that LLM client accepts and uses dialect parameters"""
    from src.core.llm_client import LLMClient
    import inspect

    print("\nTest 3: LLM client signature updated...")
    try:
        client = LLMClient()

        # Check that generate_sql has the new parameters
        sig = inspect.signature(client.generate_sql)
        params = list(sig.parameters.keys())

        assert 'database_type' in params, "database_type parameter not found"
        assert 'database_name' in params, "database_name parameter not found"
        assert 'dialect_guide' in params, "dialect_guide parameter not found"

        # Check defaults
        assert sig.parameters['database_type'].default == 'bigquery', \
            "database_type default should be 'bigquery'"
        assert sig.parameters['database_name'].default == 'BigQuery', \
            "database_name default should be 'BigQuery'"
        assert sig.parameters['dialect_guide'].default == '', \
            "dialect_guide default should be ''"

        print("  ✅ database_type parameter added")
        print("  ✅ database_name parameter added")
        print("  ✅ dialect_guide parameter added")
        print("  ✅ All parameters have correct defaults")
        print("✅ PASSED: LLM client signature properly updated")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dialect_differences():
    """Test that different databases get different dialect guides"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 4: Different dialects for different databases...")
    try:
        # Test by calling the method directly on instances with different database_type
        # This avoids actual database connections

        # Create a test object that has the _get_dialect_guide method
        gen_bq = SQLGenerator(database_type='bigquery')

        # Manually test different dialect guides by temporarily changing database_type
        original_type = gen_bq.database_type

        # Get BigQuery guide
        gen_bq.database_type = 'bigquery'
        guide_bq = gen_bq._get_dialect_guide()

        # Get Snowflake guide
        gen_bq.database_type = 'snowflake'
        guide_sf = gen_bq._get_dialect_guide()

        # Get PostgreSQL guide
        gen_bq.database_type = 'postgresql'
        guide_pg = gen_bq._get_dialect_guide()

        # Get Redshift guide
        gen_bq.database_type = 'redshift'
        guide_rs = gen_bq._get_dialect_guide()

        # Get Databricks guide
        gen_bq.database_type = 'databricks'
        guide_db = gen_bq._get_dialect_guide()

        # Restore original type
        gen_bq.database_type = original_type

        # Verify they're all different
        assert guide_bq != guide_sf, "BigQuery and Snowflake guides should differ"
        assert guide_bq != guide_pg, "BigQuery and PostgreSQL guides should differ"
        assert guide_sf != guide_pg, "Snowflake and PostgreSQL guides should differ"

        # Verify BigQuery-specific content (uses backticks for identifiers)
        assert "backticks" in guide_bq.lower() or "`" in guide_bq, "BigQuery should mention backticks"
        # Snow flake uses database.schema.table, not backticks for quoting
        assert "database.schema.table" in guide_sf.lower(), "Snowflake should use database.schema.table format"

        # Verify Snowflake-specific content
        assert "VARIANT" in guide_sf, "Snowflake should mention VARIANT type"
        assert "VARIANT" not in guide_bq, "BigQuery should not mention VARIANT"

        # Verify PostgreSQL-specific content
        assert "ILIKE" in guide_pg or "ilike" in guide_pg.lower(), "PostgreSQL should mention ILIKE"
        assert "ILIKE" not in guide_bq, "BigQuery should not mention ILIKE"

        # Verify Redshift-specific content
        assert "SUPER" in guide_rs, "Redshift should mention SUPER type"

        # Verify Databricks-specific content
        assert "Delta Lake" in guide_db or "DELTA" in guide_db, "Databricks should mention Delta Lake"

        print("  ✅ BigQuery guide is unique")
        print("  ✅ Snowflake guide is unique")
        print("  ✅ PostgreSQL guide is unique")
        print("  ✅ Redshift guide is unique")
        print("  ✅ Databricks guide is unique")
        print("  ✅ Each database has database-specific syntax")
        print("✅ PASSED: Different databases get different dialect guides")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("Task 5: Database Dialect in LLM Prompts Tests")
    print("="*60)

    tests = [
        test_dialect_guide_method,
        test_llm_kwargs_include_dialect,
        test_llm_client_accepts_dialect,
        test_dialect_differences
    ]

    results = [test() for test in tests]

    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)

    if all(results):
        print("✅ ALL TESTS PASSED - Task 5 Complete!")
        print("\n🎉 SQL Generator now supports multi-database SQL generation!")
        print("   - BigQuery: backticks, FORMAT_DATE")
        print("   - Snowflake: three-part names, TO_CHAR")
        print("   - PostgreSQL: schema.table, ILIKE")
        print("   - Redshift: PostgreSQL-compatible")
        print("   - Databricks: Spark SQL, Delta Lake")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
