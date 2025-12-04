#!/usr/bin/env python3
"""
Debug tests for error correction flow.

This script debugs why COALESCE type mismatch errors are not being caught
by the error correction agent.

Run: cd backend && source venv/bin/activate && python test_error_correction_flow.py
"""

import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# Test 1: BigQuery Dry-Run vs Actual Execution for Type Errors
# ============================================================================

def test_bigquery_validation_type_error():
    """
    Test whether BigQuery dry-run validation catches COALESCE type errors.

    Expected finding: Dry-run passes for type errors (doesn't catch them),
    only actual execution fails.
    """
    print("\n" + "="*70)
    print("TEST 1: BigQuery Dry-Run vs Actual Execution for Type Errors")
    print("="*70)

    # SQL with known type mismatch (STRING column with INT default in COALESCE)
    test_sql = """
    SELECT
        COALESCE(Gross_Revenue, 0) as revenue
    FROM `arizona-poc.copa_export_copa_data_000000000000.transaction_data`
    LIMIT 1
    """

    try:
        from src.db.connectors.bigquery_connector import BigQueryConnector
        from src.config import settings

        print(f"\nConnecting to BigQuery...")
        print(f"  Project: {settings.google_cloud_project}")
        print(f"  Dataset: {settings.bigquery_dataset}")

        connector = BigQueryConnector(
            project_id=settings.google_cloud_project,
            dataset_id=settings.bigquery_dataset
        )
        connector.connect()

        # Test 1a: Dry-run validation
        print(f"\n--- Test 1a: Dry-Run Validation ---")
        print(f"SQL: {test_sql[:100]}...")

        validation_result = connector.validate_query(test_sql)
        print(f"Validation result:")
        print(f"  valid: {validation_result.get('valid')}")
        print(f"  error: {validation_result.get('error', 'None')[:200] if validation_result.get('error') else 'None'}")

        # Test 1b: Actual execution
        print(f"\n--- Test 1b: Actual Execution ---")
        try:
            result = connector.execute_query(test_sql)
            print(f"Execution succeeded!")
            print(f"  rows: {len(result.get('rows', []))}")
        except Exception as exec_error:
            print(f"Execution failed (expected):")
            print(f"  error: {str(exec_error)[:300]}")

        # Conclusion
        print(f"\n--- CONCLUSION ---")
        if validation_result.get('valid'):
            print("CONFIRMED: BigQuery dry-run PASSES for COALESCE type errors")
            print("This is why pre-execution validation doesn't catch the error!")
        else:
            print("UNEXPECTED: BigQuery dry-run CAUGHT the type error")
            print(f"Error: {validation_result.get('error')}")

        connector.disconnect()

    except ImportError as e:
        print(f"Could not import BigQuery connector: {e}")
        print("Skipping live BigQuery test...")
    except Exception as e:
        print(f"Test error: {e}")


# ============================================================================
# Test 2: Error Correction Triggering Conditions
# ============================================================================

def test_error_correction_trigger_conditions():
    """
    Test the conditions at routes.py line 819 that determine if error
    correction is triggered.

    Condition: execution_result.get("error") and not correction_info and not sql_result.get("from_cache")
    """
    print("\n" + "="*70)
    print("TEST 2: Error Correction Triggering Conditions")
    print("="*70)

    # Simulate different scenarios
    scenarios = [
        {
            "name": "Normal error (should trigger correction)",
            "execution_result": {"error": "COALESCE type mismatch", "results": None},
            "correction_info": None,
            "sql_result": {"sql": "SELECT ...", "from_cache": False},
            "expected_trigger": True
        },
        {
            "name": "Error but from cache (should NOT trigger)",
            "execution_result": {"error": "COALESCE type mismatch", "results": None},
            "correction_info": None,
            "sql_result": {"sql": "SELECT ...", "from_cache": True},
            "expected_trigger": False
        },
        {
            "name": "Error but already corrected (should NOT trigger)",
            "execution_result": {"error": "COALESCE type mismatch", "results": None},
            "correction_info": {"auto_corrected": True},
            "sql_result": {"sql": "SELECT ...", "from_cache": False},
            "expected_trigger": False
        },
        {
            "name": "No error (should NOT trigger)",
            "execution_result": {"results": [{"col": "value"}], "row_count": 1},
            "correction_info": None,
            "sql_result": {"sql": "SELECT ...", "from_cache": False},
            "expected_trigger": False
        }
    ]

    for scenario in scenarios:
        execution_result = scenario["execution_result"]
        correction_info = scenario["correction_info"]
        sql_result = scenario["sql_result"]

        # Evaluate the condition from routes.py:819
        should_trigger = (
            execution_result.get("error") and
            not correction_info and
            not sql_result.get("from_cache")
        )

        status = "PASS" if should_trigger == scenario["expected_trigger"] else "FAIL"

        print(f"\n{status}: {scenario['name']}")
        print(f"  execution_result.get('error'): {bool(execution_result.get('error'))}")
        print(f"  not correction_info: {not correction_info}")
        print(f"  not sql_result.get('from_cache'): {not sql_result.get('from_cache')}")
        print(f"  Should trigger: {should_trigger} (expected: {scenario['expected_trigger']})")


# ============================================================================
# Test 3: ErrorCorrectionAgent with Type Errors
# ============================================================================

def test_error_correction_agent_type_error():
    """
    Test ErrorCorrectionAgent directly with a COALESCE type error to see
    if it can correct it.
    """
    print("\n" + "="*70)
    print("TEST 3: ErrorCorrectionAgent with Type Errors")
    print("="*70)

    try:
        from src.core.error_correction_agent import ErrorCorrectionAgent
        from src.core.llm_client import LLMClient
        from src.config import settings

        # Initialize LLM client
        print(f"\nInitializing LLM client...")
        print(f"  Model: {settings.anthropic_model}")

        llm_client = LLMClient()
        agent = ErrorCorrectionAgent(llm_client=llm_client)

        # Test case: COALESCE type mismatch
        original_question = "Show me total revenue by customer"
        failed_sql = """
        SELECT
            Customer,
            SUM(COALESCE(Gross_Revenue, 0)) as total_revenue
        FROM `arizona-poc.copa_export_copa_data_000000000000.transaction_data`
        GROUP BY Customer
        """
        error_message = """400 No matching signature for function COALESCE
  Argument types: STRING, INT64
  Signature: COALESCE([T1, ...])
      Input types for <T1>: {INT64, STRING} at [3:17]"""

        # Schema with column types
        table_schemas = [{
            "table_name": "transaction_data",
            "columns": [
                {"name": "Customer", "type": "STRING", "description": "Customer ID"},
                {"name": "Gross_Revenue", "type": "STRING", "description": "Revenue amount stored as string"},
                {"name": "GL_Amount_in_CC", "type": "FLOAT64", "description": "GL Amount"}
            ]
        }]

        print(f"\n--- Calling ErrorCorrectionAgent ---")
        print(f"Original question: {original_question}")
        print(f"Error message: {error_message[:100]}...")

        result = agent.analyze_and_correct(
            original_question=original_question,
            failed_sql=failed_sql,
            error_message=error_message,
            table_schemas=table_schemas,
            database_type="bigquery"
        )

        print(f"\n--- ErrorCorrectionAgent Result ---")
        print(f"  error_category: {result.get('error_category')}")
        print(f"  confidence: {result.get('confidence')}")
        print(f"  should_retry: {result.get('should_retry')}")
        print(f"  requires_user_action: {result.get('requires_user_action')}")
        print(f"  analysis: {result.get('analysis', '')[:200]}...")
        print(f"  changes_made: {result.get('changes_made', [])}")

        if result.get('corrected_sql'):
            print(f"\n--- Corrected SQL ---")
            print(result.get('corrected_sql'))
        else:
            print(f"\n  NO CORRECTED SQL RETURNED!")

        # Verify correction
        print(f"\n--- VERIFICATION ---")
        if result.get('should_retry') and result.get('confidence', 0) >= 0.5:
            print("SUCCESS: Agent would retry with corrected SQL")

            # Check if correction is valid
            corrected = result.get('corrected_sql', '')
            if 'SAFE_CAST' in corrected.upper() or 'CAST' in corrected.upper():
                print("GOOD: Correction uses CAST/SAFE_CAST for type conversion")
            elif "COALESCE(Gross_Revenue, '0')" in corrected:
                print("ACCEPTABLE: Correction uses string default")
            else:
                print("WARNING: Correction approach unclear - needs validation")
        else:
            print(f"FAILURE: Agent would NOT retry")
            print(f"  confidence: {result.get('confidence', 0)}")
            print(f"  should_retry: {result.get('should_retry')}")
            if result.get('user_message'):
                print(f"  user_message: {result.get('user_message')}")

    except ImportError as e:
        print(f"Could not import: {e}")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# Test 4: Full Error Correction Flow Simulation
# ============================================================================

def test_full_error_correction_flow():
    """
    Simulate the full flow from SQL generation through error correction.
    This traces through the actual code path to identify where the flow breaks.
    """
    print("\n" + "="*70)
    print("TEST 4: Full Error Correction Flow Simulation")
    print("="*70)

    try:
        from src.core.sql_generator import SQLGenerator
        from src.core.llm_client import LLMClient
        from src.config import settings

        print(f"\nInitializing SQLGenerator...")

        # Create generator
        llm_client = LLMClient()
        generator = SQLGenerator(
            llm_client=llm_client,
            organization_id="Demo"
        )

        # Test SQL with known type error
        bad_sql = """
        SELECT Customer, SUM(COALESCE(Gross_Revenue, 0)) as revenue
        FROM `arizona-poc.copa_export_copa_data_000000000000.transaction_data`
        GROUP BY Customer LIMIT 10
        """

        print(f"\n--- Step 1: Validate Query (Dry-Run) ---")
        # This uses sql_generator.execute_query which calls validate then execute

        # Check validation behavior
        if hasattr(generator, 'db_client') and generator.db_client:
            validation = generator.db_client.validate_query(bad_sql)
            print(f"Validation result: valid={validation.get('valid')}")
            if not validation.get('valid'):
                print(f"Error: {validation.get('error', '')[:200]}")
        else:
            print("No db_client available, skipping validation test")

        print(f"\n--- Step 2: Execute Query ---")
        try:
            result = generator.execute_query(bad_sql)
            print(f"execute_query returned:")
            print(f"  error: {result.get('error', 'None')[:200] if result.get('error') else 'None'}")
            print(f"  results: {'Yes' if result.get('results') else 'No'}")
            print(f"  row_count: {result.get('row_count', 0)}")
        except Exception as e:
            print(f"execute_query raised exception: {e}")

        print(f"\n--- Step 3: Check if sql_generator.execute_query handles errors ---")
        print("Reviewing the code path...")
        print("  1. sql_generator.execute_query() calls db_client.validate_query()")
        print("  2. If validation fails, it tries llm_client.correct_sql_error()")
        print("  3. If validation passes but execution fails, error is in exception handler")
        print("  4. The exception handler returns {'error': str(e), 'results': None}")
        print("")
        print("ISSUE: The error correction in sql_generator.execute_query (lines 2074-2107)")
        print("       only triggers when VALIDATION fails, not when EXECUTION fails!")
        print("       When validation passes (dry-run OK) but execution fails (type error),")
        print("       it just returns the error without attempting correction.")

    except ImportError as e:
        print(f"Could not import: {e}")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# Test 5: Cache Manager Test Execution Interaction
# ============================================================================

def test_cache_manager_validation_update():
    """
    Test whether cache manager updates result["validation"] when test
    execution fails.

    Current bug: It sets local validation_status=False but doesn't update
    result["validation"]["valid"].
    """
    print("\n" + "="*70)
    print("TEST 5: Cache Manager Validation Update")
    print("="*70)

    # Simulate the caching flow from sql_generator.py lines 1551-1622
    print("\nSimulating caching flow...")

    # Initial result (after dry-run validation passed)
    result = {
        "sql": "SELECT COALESCE(Gross_Revenue, 0) FROM ...",
        "validation": {"valid": True},  # Dry-run passed
        "tables_used": ["transaction_data"],
        "from_cache": False
    }

    print(f"\n--- Initial state after dry-run ---")
    print(f"result['validation']['valid'] = {result['validation']['valid']}")

    # Simulate test execution failure (lines 1585-1589)
    try:
        # This would be the test execution
        raise Exception("No matching signature for function COALESCE")
    except Exception as exec_error:
        # This is what currently happens in the code
        error_details = str(exec_error)
        validation_status = False  # Local variable only!
        print(f"\n--- After test execution failed ---")
        print(f"Local validation_status = {validation_status}")
        print(f"error_details = '{error_details[:50]}...'")
        print(f"result['validation']['valid'] = {result['validation']['valid']}  <-- NOT UPDATED!")

    print(f"\n--- BUG IDENTIFIED ---")
    print("The code sets `validation_status = False` as a LOCAL variable")
    print("but does NOT update `result['validation']['valid']`!")
    print("")
    print("This means when the result is returned to routes.py:")
    print("  - sql_result['validation']['valid'] is still True")
    print("  - Pre-execution correction is NOT triggered (line 793)")
    print("  - Execution fails with type error")
    print("  - Post-execution correction SHOULD trigger (line 819)")
    print("")
    print("But we need to verify the post-execution path is working...")

    # Proposed fix
    print(f"\n--- PROPOSED FIX ---")
    print("In sql_generator.py around line 1588, after test execution fails:")
    print("  error_details = str(exec_error)")
    print("  validation_status = False")
    print("  result['validation']['valid'] = False  # ADD THIS LINE")
    print("  result['validation']['error'] = error_details  # ADD THIS LINE")


# ============================================================================
# Test 6: Trace Through routes.py Error Correction
# ============================================================================

def test_routes_error_correction_path():
    """
    Trace through routes.py to verify the post-execution error correction
    path is reachable.
    """
    print("\n" + "="*70)
    print("TEST 6: Trace Through routes.py Error Correction Path")
    print("="*70)

    print("\nAnalyzing routes.py execute_query_endpoint flow...")
    print("")
    print("1. Line 789: validation = sql_result.get('validation', {})")
    print("   - Gets validation from generate_sql result")
    print("   - For type errors: validation['valid'] = True (dry-run passed)")
    print("")
    print("2. Line 793: if not validation.get('valid', True) and not sql_result.get('from_cache'):")
    print("   - Checks if validation failed")
    print("   - For type errors: This is FALSE (dry-run passed)")
    print("   - Pre-execution correction SKIPPED")
    print("")
    print("3. Line 816: execution_result = generator.execute_query(current_sql)")
    print("   - Executes the query")
    print("   - For type errors: This FAILS and returns {'error': '...'}")
    print("")
    print("4. Line 819: if execution_result.get('error') and not correction_info and not sql_result.get('from_cache'):")
    print("   - execution_result.get('error'): TRUE (execution failed)")
    print("   - not correction_info: TRUE (no pre-correction happened)")
    print("   - not sql_result.get('from_cache'): TRUE (fresh generation)")
    print("   - ALL CONDITIONS MET: Post-execution correction SHOULD trigger!")
    print("")
    print("5. Line 823: corrected_sql, correction = attempt_error_correction(...)")
    print("   - Calls ErrorCorrectionAgent")
    print("")
    print("CONCLUSION: The post-execution error correction SHOULD be triggered.")
    print("If it's not working, either:")
    print("  a) ErrorCorrectionAgent returns low confidence/should_retry=False")
    print("  b) The corrected SQL still has issues")
    print("  c) There's an exception being silently caught")
    print("")
    print("Run TEST 3 to verify ErrorCorrectionAgent behavior with type errors.")


# ============================================================================
# Test 7: Add Logging to Trace Error Correction Flow
# ============================================================================

def test_add_debug_logging():
    """
    Create a patch file to add debugging logs to routes.py error correction path.
    """
    print("\n" + "="*70)
    print("TEST 7: Debug Logging Additions for routes.py")
    print("="*70)

    print("""
To debug why error correction isn't triggering, add these logs to routes.py:

BEFORE line 789 (after PHASE 1 comment):
```python
logger.info(f"DEBUG: sql_result keys: {sql_result.keys()}")
logger.info(f"DEBUG: validation: {sql_result.get('validation')}")
logger.info(f"DEBUG: from_cache: {sql_result.get('from_cache')}")
```

BEFORE line 816 (PHASE 2 - Execute):
```python
logger.info(f"DEBUG: About to execute query. correction_info={correction_info}")
```

BEFORE line 819 (PHASE 3 - Post-execution check):
```python
logger.info(f"DEBUG: execution_result.get('error')={execution_result.get('error')[:100] if execution_result.get('error') else None}")
logger.info(f"DEBUG: not correction_info={not correction_info}")
logger.info(f"DEBUG: not sql_result.get('from_cache')={not sql_result.get('from_cache')}")
should_correct = execution_result.get("error") and not correction_info and not sql_result.get("from_cache")
logger.info(f"DEBUG: should_correct={should_correct}")
```

This will help identify exactly where the flow breaks.
""")


# ============================================================================
# Test 8: Verify Schema in Weaviate
# ============================================================================

def test_check_weaviate_schema():
    """
    Check what schema is stored in Weaviate for the problematic table.
    """
    print("\n" + "="*70)
    print("TEST 8: Check Weaviate Schema for sales_order_cockpit_export")
    print("="*70)

    try:
        from src.db.weaviate_client import WeaviateClient

        weaviate = WeaviateClient()

        # Search for the table
        results = weaviate.search_tables(
            "sales_order_cockpit_export",
            limit=1,
            organization_id="Demo"
        )

        if results:
            schema = results[0]
            print(f"\nTable: {schema.get('table_name')}")
            print(f"Database type: {schema.get('database_type')}")

            columns = schema.get('columns', [])
            print(f"\nColumns ({len(columns)}):")

            # Check if Material_MATNR exists
            material_found = False
            for col in columns:
                col_name = col.get('name', 'unknown')
                if 'material' in col_name.lower() or 'matnr' in col_name.lower():
                    material_found = True
                    print(f"  * {col_name} ({col.get('type', 'unknown')}) - MATERIAL RELATED")
                elif col_name in ['Material_MATNR', 'Material_Description', 'OPEN_DELIVERY_QTY']:
                    print(f"  - {col_name} ({col.get('type', 'unknown')}) - USED IN QUERY")

            if not material_found:
                print("\n  NO 'Material' or 'MATNR' columns found!")
                print("  This suggests the LLM is hallucinating column names.")
        else:
            print("Table not found in Weaviate!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("ERROR CORRECTION FLOW DEBUG TESTS")
    print("="*70)
    print("\nThese tests debug why COALESCE type mismatch errors aren't being")
    print("caught by the error correction system.")
    print("")

    # Run all tests
    test_bigquery_validation_type_error()
    test_error_correction_trigger_conditions()
    test_error_correction_agent_type_error()
    test_full_error_correction_flow()
    test_cache_manager_validation_update()
    test_routes_error_correction_path()
    test_add_debug_logging()
    test_check_weaviate_schema()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("""
Based on the analysis, the issue is likely:

1. BigQuery dry-run validation PASSES for type errors (confirmed)
2. This means pre-execution correction is SKIPPED
3. Execution fails with the type error
4. Post-execution correction SHOULD trigger (conditions are met)
5. Either:
   a) ErrorCorrectionAgent returns low confidence
   b) ErrorCorrectionAgent returns should_retry=False
   c) The correction itself has issues
   d) An exception is being caught silently

To fix:
1. Run TEST 3 against real LLM to verify ErrorCorrectionAgent behavior
2. Add logging in routes.py attempt_error_correction to see actual flow
3. Consider adding test execution result to result["validation"] in sql_generator.py
""")
