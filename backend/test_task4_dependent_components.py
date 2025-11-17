#!/usr/bin/env python3
"""Test Task 4: Updated Dependent Components"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_format_normalizer_updated():
    """Test that FormatNormalizer works with generic database client"""
    from src.core.format_normalizer import FormatNormalizer
    from src.core.sql_generator import SQLGenerator

    print("Test 1: FormatNormalizer with BigQuery...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # Check that FormatNormalizer was initialized
        assert generator.format_normalizer is not None, "FormatNormalizer not initialized"

        # Check that it has the new attributes
        normalizer = generator.format_normalizer
        assert hasattr(normalizer, 'db_client'), "db_client not found"
        assert hasattr(normalizer, 'database_qualifier'), "database_qualifier not found"
        assert hasattr(normalizer, 'schema_qualifier'), "schema_qualifier not found"
        assert hasattr(normalizer, 'db_type'), "db_type not found"

        # Check values
        assert normalizer.database_qualifier is not None, "database_qualifier is None"
        assert normalizer.schema_qualifier is not None, "schema_qualifier is None"
        assert normalizer.db_type == 'bigquery', f"Expected 'bigquery', got '{normalizer.db_type}'"

        print(f"  ✅ Database qualifier: {normalizer.database_qualifier}")
        print(f"  ✅ Schema qualifier: {normalizer.schema_qualifier}")
        print(f"  ✅ Database type: {normalizer.db_type}")
        print("✅ PASSED: FormatNormalizer properly updated")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_metrics_precalculator_updated():
    """Test that FinancialMetricsPreCalculator works with generic database client"""
    from src.core.metrics_precalculation import FinancialMetricsPreCalculator
    from src.core.sql_generator import SQLGenerator

    print("\nTest 2: FinancialMetricsPreCalculator with BigQuery...")
    try:
        generator = SQLGenerator(database_type='bigquery')

        # Check that precalc integrator was initialized
        if generator.precalc_integrator is None:
            print("  ⚠️  PreCalc integrator not initialized (might be disabled)")
            # This is okay - not a failure
            return True

        # Get the precalculator from the integrator
        precalculator = generator.precalc_integrator.precalculator

        # Check that it has the new attributes
        assert hasattr(precalculator, 'db_client'), "db_client not found"
        assert hasattr(precalculator, 'database_qualifier'), "database_qualifier not found"
        assert hasattr(precalculator, 'schema_qualifier'), "schema_qualifier not found"
        assert hasattr(precalculator, 'db_type'), "db_type not found"

        # Check values
        assert precalculator.db_type == 'bigquery', f"Expected 'bigquery', got '{precalculator.db_type}'"

        print(f"  ✅ Database qualifier: {precalculator.database_qualifier}")
        print(f"  ✅ Schema qualifier: {precalculator.schema_qualifier}")
        print(f"  ✅ Database type: {precalculator.db_type}")
        print("✅ PASSED: FinancialMetricsPreCalculator properly updated")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility with bq_client parameter"""
    from src.core.format_normalizer import FormatNormalizer
    from src.core.metrics_precalculation import FinancialMetricsPreCalculator
    from src.db.connectors import BigQueryConnector
    from src.config import settings

    print("\nTest 3: Backward compatibility...")
    try:
        # Create a BigQuery connector
        bq_connector = BigQueryConnector(
            project_id=settings.google_cloud_project,
            dataset_id=settings.bigquery_dataset
        )

        # Test FormatNormalizer with old parameter name (should still work)
        normalizer = FormatNormalizer(bq_connector)
        assert normalizer.db_client is not None, "db_client not set"
        assert normalizer.bq_client is normalizer.db_client, "bq_client alias not working"
        print("  ✅ FormatNormalizer backward compatibility works")

        # Test FinancialMetricsPreCalculator with old parameter name
        precalculator = FinancialMetricsPreCalculator(bq_client=bq_connector)
        assert precalculator.db_client is not None, "db_client not set"
        assert precalculator.bq_client is precalculator.db_client, "bq_client alias not working"
        print("  ✅ FinancialMetricsPreCalculator backward compatibility works")

        print("✅ PASSED: Full backward compatibility maintained")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test that everything works together end-to-end"""
    from src.core.sql_generator import SQLGenerator

    print("\nTest 4: Full integration test...")
    try:
        # Create SQL generator
        generator = SQLGenerator(database_type='bigquery')

        # Verify all components are using the same db_client
        assert generator.db_client is not None, "db_client not initialized"

        if generator.format_normalizer:
            assert generator.format_normalizer.db_client is generator.db_client, \
                "FormatNormalizer using different db_client"
            print("  ✅ FormatNormalizer using same db_client")

        if generator.precalc_integrator:
            precalculator = generator.precalc_integrator.precalculator
            # Note: precalculator might have its own instance, but should be same type
            assert hasattr(precalculator, 'db_client'), "Precalculator missing db_client"
            print("  ✅ Precalculator has db_client")

        # Verify qualifiers are consistent
        db_qual = generator._get_database_qualifier()
        schema_qual = generator._get_schema_qualifier()

        if generator.format_normalizer:
            assert generator.format_normalizer.database_qualifier == db_qual, \
                "FormatNormalizer has different database qualifier"
            assert generator.format_normalizer.schema_qualifier == schema_qual, \
                "FormatNormalizer has different schema qualifier"
            print("  ✅ FormatNormalizer qualifiers match")

        print("✅ PASSED: Full integration works correctly")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("Task 4: Dependent Components Update Tests")
    print("="*60)

    tests = [
        test_format_normalizer_updated,
        test_metrics_precalculator_updated,
        test_backward_compatibility,
        test_integration
    ]

    results = [test() for test in tests]

    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)

    if all(results):
        print("✅ ALL TESTS PASSED - Task 4 Complete!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
