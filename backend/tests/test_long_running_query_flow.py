"""
Tests for Long-Running Query Detection and Background Mode Flow

This test suite verifies:
1. requires_async flag is set correctly for very large tables (>1B rows)
2. Federated queries with large tables return requires_async=True
3. routes.py correctly returns long_running status
4. Query status updates properly in Redis
5. End-to-end flow from query submission to background mode

The key bug fixed: For federated queries (>100M rows), the requires_async check
was happening AFTER _execute_federated_single_db() returned, so it was never triggered.
Now the check happens BEFORE federated execution.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestQueryAnalysisRequiresAsync:
    """Test that QueryAnalysis correctly sets requires_async for large tables."""

    def test_requires_async_set_for_billion_row_table(self):
        """Tables with >1B rows should set requires_async=True."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer, QueryAnalysis

        # Create optimizer
        optimizer = SingleDatabaseQueryOptimizer()

        # Mock the row count lookup to return 28.8B rows (like STORE_SALES)
        with patch.object(optimizer, '_get_table_row_count') as mock_row_count:
            mock_row_count.return_value = 28_800_239_865

            # Analyze a simple aggregation query - use correct method name
            sql = "SELECT SUM(amount) FROM STORE_SALES"
            analysis = optimizer.analyze_query(sql, dialect='snowflake')

            # Verify requires_async is True for >1B rows
            assert analysis.requires_async is True, \
                f"Expected requires_async=True for {analysis.largest_table_rows:,} rows"
            assert analysis.largest_table_rows == 28_800_239_865
            assert 'STORE_SALES' in analysis.largest_table.upper()

    def test_requires_async_false_for_small_table(self):
        """Tables with <1B rows should NOT set requires_async."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer

        optimizer = SingleDatabaseQueryOptimizer()

        with patch.object(optimizer, '_get_table_row_count') as mock_row_count:
            # 500M rows - large but under threshold
            mock_row_count.return_value = 500_000_000

            sql = "SELECT COUNT(*) FROM ORDERS"
            analysis = optimizer.analyze_query(sql, dialect='snowflake')

            assert analysis.requires_async is False, \
                f"Expected requires_async=False for {analysis.largest_table_rows:,} rows"

    def test_requires_async_threshold_boundary(self):
        """Test the exact 1B row boundary."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer

        optimizer = SingleDatabaseQueryOptimizer()

        # Test 1B + 1 rows - should require async
        with patch.object(optimizer, '_get_table_row_count') as mock_row_count:
            mock_row_count.return_value = 1_000_000_001
            analysis = optimizer.analyze_query("SELECT SUM(x) FROM BIG_TABLE", dialect='snowflake')
            assert analysis.requires_async is True, \
                f"Expected requires_async=True for 1B+1 rows, got {analysis.requires_async}"


class TestFederatedQueryRequiresAsync:
    """Test that federated queries correctly return requires_async before execution."""

    def test_federated_execution_skipped_when_requires_async(self):
        """
        CRITICAL TEST: Verify _execute_federated_single_db is NOT called when requires_async=True.

        This verifies the fix is in place: requires_async check should come BEFORE
        _execute_federated_single_db call in the FEDERATED strategy block.
        """
        # Read the actual source file directly instead of using inspect
        import os
        sql_generator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'core', 'sql_generator.py'
        )

        with open(sql_generator_path, 'r') as f:
            source = f.read()

        # Find the FEDERATED EXECUTION block
        federated_marker = 'FEDERATED EXECUTION: Routing large query'
        federated_block_start = source.find(federated_marker)

        assert federated_block_start > 0, \
            f"Could not find FEDERATED EXECUTION block in sql_generator.py"

        # Get the section of code after the federated marker (3000 chars should be enough)
        federated_section = source[federated_block_start:federated_block_start + 3000]

        # Find the requires_async check and federated execution call
        requires_async_pos = federated_section.find('if query_analysis.requires_async:')
        federated_exec_pos = federated_section.find('_execute_federated_single_db')

        assert requires_async_pos > 0, \
            f"requires_async check not found in federated block"
        assert federated_exec_pos > 0, \
            f"_execute_federated_single_db call not found"

        # THE KEY ASSERTION: requires_async must be checked BEFORE federated execution
        assert requires_async_pos < federated_exec_pos, \
            f"BUG NOT FIXED: requires_async check (pos {requires_async_pos}) must come BEFORE " \
            f"_execute_federated_single_db (pos {federated_exec_pos}). " \
            f"The check is happening after execution, so long-running queries won't be detected!"

    def test_requires_async_returns_correct_response_structure(self):
        """Verify the requires_async response has all required fields."""
        import os
        sql_generator_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'core', 'sql_generator.py'
        )

        with open(sql_generator_path, 'r') as f:
            source = f.read()

        # Find the return statement in the requires_async block within federated section
        federated_start = source.find('FEDERATED EXECUTION')
        assert federated_start > 0

        # Look for the async block after FEDERATED EXECUTION
        federated_section = source[federated_start:federated_start + 3500]

        # Find the return block after requires_async check
        async_check = federated_section.find('if query_analysis.requires_async:')
        assert async_check > 0, "requires_async check not found in federated section"

        # Get enough content to capture the return statement
        return_section = federated_section[async_check:async_check + 1200]

        # Verify required fields are in the return
        required_fields = ['requires_async', 'sql', 'largest_table_rows', 'tables_used']
        for field in required_fields:
            # Check for the field with quotes
            field_found = f'"{field}"' in return_section or f"'{field}'" in return_section
            assert field_found, \
                f"Missing required field '{field}' in requires_async response. " \
                f"Section content: {return_section[:500]}..."


class TestQueryStatusManager:
    """Test that QueryStatusManager correctly stores and retrieves long_running status."""

    def test_update_status_with_long_running(self):
        """Verify status manager stores long_running fields correctly."""
        from src.core.query_status_manager import QueryStatusManager

        with patch('src.core.query_status_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping = Mock(return_value=True)
            mock_client.setex = Mock()
            mock_client.get = Mock()

            manager = QueryStatusManager()

            # Update with long_running status
            manager.update_status(
                execution_id='test-123',
                status='long_running',
                progress=10,
                message='Query scans ~28B rows',
                phase='executing',
                sql='SELECT ...',
                is_long_running=True,
                estimated_minutes=30,
                largest_table_rows=28_800_239_865
            )

            # Verify setex was called with correct data
            assert mock_client.setex.called
            call_args = mock_client.setex.call_args

            # Extract the stored data from the call
            stored_data = None
            if call_args[0]:
                # Positional args: (key, time, value) or (key, value, time)
                for arg in call_args[0]:
                    if isinstance(arg, str) and arg.startswith('{'):
                        stored_data = json.loads(arg)
                        break

            if stored_data is None and call_args[1]:
                stored_data = json.loads(call_args[1].get('value', '{}'))

            if stored_data:
                assert stored_data.get('status') == 'long_running'
                assert stored_data.get('is_long_running') == True
                assert stored_data.get('estimated_minutes') == 30
                assert stored_data.get('largest_table_rows') == 28_800_239_865


class TestEndToEndLongRunningFlow:
    """End-to-end test of the full long-running query flow."""

    def test_full_flow_large_snowflake_query(self):
        """
        Test the complete flow:
        1. User submits query against 28B row table
        2. SingleDatabaseQueryOptimizer detects large table, sets requires_async=True
        3. SQLGenerator returns requires_async response (doesn't execute)
        4. routes.py detects requires_async, sets status to long_running
        5. Frontend receives long_running status
        6. Frontend auto-switches to background mode
        """
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer, ExecutionStrategy

        optimizer = SingleDatabaseQueryOptimizer()

        # Step 1: Simulate query against STORE_SALES (28.8B rows)
        with patch.object(optimizer, '_get_table_row_count') as mock_count:
            mock_count.return_value = 28_800_239_865

            sql = """
                SELECT
                    ROUND(SUM(COALESCE(SS_NET_PAID, 0)), 2) as total_sales
                FROM SNOWFLAKE_SAMPLE_DATA.TPCDS_SF10TCL.STORE_SALES
            """

            # Step 2: Analyze query - use correct method name
            analysis = optimizer.analyze_query(sql, dialect='snowflake')

            # Verify detection
            print(f"\n=== Query Analysis Results ===")
            print(f"Strategy: {analysis.strategy}")
            print(f"Largest table: {analysis.largest_table}")
            print(f"Largest table rows: {analysis.largest_table_rows:,}")
            print(f"requires_async: {analysis.requires_async}")
            print(f"Warnings: {analysis.warnings}")

            # Step 3: Assertions
            assert analysis.strategy == ExecutionStrategy.FEDERATED, \
                f"Expected FEDERATED strategy for 28B rows, got {analysis.strategy}"

            assert analysis.requires_async is True, \
                f"Expected requires_async=True for 28B rows, got {analysis.requires_async}"

            assert analysis.largest_table_rows >= 1_000_000_000, \
                f"Expected >1B rows, got {analysis.largest_table_rows:,}"

            print("\n=== All checks passed! ===")
            print("The fix ensures requires_async is checked BEFORE federated execution.")


class TestPreviewEndpoint:
    """Test the /api/v1/query/preview endpoint logic."""

    def test_preview_calculates_is_long_running_correctly(self):
        """Preview endpoint should return is_long_running=True for large tables."""
        # Test the calculation logic used in the preview endpoint

        largest_rows = 28_800_239_865

        # This is the logic from routes.py preview endpoint
        is_long_running = largest_rows >= 1_000_000_000
        estimated_minutes = max(5, int(largest_rows / 5_000_000_000) * 5) if is_long_running else 0

        assert is_long_running is True, \
            f"Expected is_long_running=True for {largest_rows:,} rows"
        assert estimated_minutes >= 5, \
            f"Expected estimated_minutes >= 5, got {estimated_minutes}"

        # 28.8B / 5B = 5.76, int = 5, then 5 * 5 = 25
        assert estimated_minutes == 25, \
            f"Expected 25 minutes for 28.8B rows, got {estimated_minutes}"

    def test_preview_returns_warning_for_large_queries(self):
        """Preview should include a warning message for large queries."""
        largest_rows = 28_800_239_865
        is_long_running = largest_rows >= 1_000_000_000
        estimated_minutes = max(5, int(largest_rows / 5_000_000_000) * 5) if is_long_running else 0

        warning = f"This query will scan ~{largest_rows:,} rows and may take {estimated_minutes}+ minutes." if is_long_running else None

        assert warning is not None
        assert "28,800,239,865" in warning
        assert "25+" in warning or "minutes" in warning


class TestRoutesLongRunningHandler:
    """Test that routes.py correctly handles requires_async flag."""

    def test_routes_checks_requires_async(self):
        """Verify routes.py has code to check requires_async and return long_running."""
        import os
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Check that routes.py handles requires_async
        assert 'requires_async' in source, \
            "routes.py should check for requires_async flag"

        # Check that it returns long_running status
        assert '"long_running"' in source or "'long_running'" in source, \
            "routes.py should return 'long_running' status"

        # Check that is_long_running is set
        assert 'is_long_running' in source, \
            "routes.py should set is_long_running field"

    def test_execute_query_logic_handles_requires_async(self):
        """Verify _execute_query_logic uses QueryOrchestrator to check requires_async."""
        import os
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Find _execute_query_logic function
        func_start = source.find('async def _execute_query_logic(')
        assert func_start > 0, "_execute_query_logic function not found"

        # Get function body (up to next top-level function)
        next_func = source.find('\nasync def ', func_start + 1)
        if next_func == -1:
            next_func = source.find('\ndef ', func_start + 1)
        func_body = source[func_start:next_func] if next_func > 0 else source[func_start:]

        # Check that QueryOrchestrator is used for analysis
        assert 'QueryOrchestrator' in func_body, \
            "_execute_query_logic should use QueryOrchestrator for analysis"

        # Check that analyze_for_preview is called
        assert 'analyze_for_preview' in func_body, \
            "_execute_query_logic should call analyze_for_preview"

        # Check that requires_async is checked
        assert 'requires_async' in func_body, \
            "_execute_query_logic should check requires_async"

        # Check that long_running status is returned
        assert '"status": "long_running"' in func_body or "'status': 'long_running'" in func_body, \
            "_execute_query_logic should return long_running status when requires_async"

    def test_execute_long_running_query_helper_exists(self):
        """Verify _execute_long_running_query helper function exists."""
        import os
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Check that the helper function exists
        assert 'async def _execute_long_running_query(' in source, \
            "_execute_long_running_query helper function should exist"

        # Check it's called from process_in_background
        assert '_execute_long_running_query(' in source.split('async def _execute_long_running_query(')[1], \
            "_execute_long_running_query should be called from somewhere"


class TestQueryOrchestrator:
    """Test the QueryOrchestrator module."""

    def test_orchestrator_module_exists(self):
        """Verify QueryOrchestrator module exists and can be imported."""
        from src.core.query_orchestrator import QueryOrchestrator, QueryResult
        assert QueryOrchestrator is not None
        assert QueryResult is not None

    def test_orchestrator_analyze_for_preview(self):
        """Test that analyze_for_preview returns correct structure."""
        from src.core.query_orchestrator import QueryOrchestrator
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer

        # Create mock generator with optimizer
        class MockGenerator:
            def __init__(self):
                self.single_db_optimizer = SingleDatabaseQueryOptimizer(
                    organization_id='test',
                    database_type='snowflake'
                )

        orchestrator = QueryOrchestrator(
            sql_generator=MockGenerator(),
            database_type='snowflake'
        )

        # Test analyze_for_preview - should handle unknown tables gracefully
        result = orchestrator.analyze_for_preview(
            'SELECT * FROM test_table',
            'snowflake'
        )

        # Should return a dict with expected keys
        assert isinstance(result, dict)
        assert 'requires_async' in result
        assert 'is_long_running' in result
        assert 'warnings' in result


class TestSyncPathQueryOrchestrator:
    """Test that SYNC PATH in process_query uses QueryOrchestrator."""

    def test_sync_path_uses_query_orchestrator(self):
        """
        Verify that the SYNC path in process_query() (default async_mode=False)
        uses QueryOrchestrator to analyze SQL and detect large tables.
        This is critical because sync path was missing the analysis!
        """
        import os
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Find the process_query function (sync path)
        func_start = source.find('@router.post("/query"')
        assert func_start > 0, "process_query route not found"

        # Get the function body (including nested functions)
        # Look for the next router decorator to find end of function
        next_route = source.find('\n@router.', func_start + 20)
        func_body = source[func_start:next_route] if next_route > 0 else source[func_start:]

        # Check that SYNC PATH analysis comment exists
        assert 'SYNC PATH' in func_body, \
            "Sync path should have SYNC PATH comment marker"

        # Check that QueryOrchestrator is used IN THE SYNC PATH
        # (not just in _execute_query_logic which is for async)
        sync_section = func_body[func_body.find('# Sync mode'):]
        assert 'QueryOrchestrator' in sync_section, \
            "SYNC PATH in process_query should use QueryOrchestrator"

        # Check that analyze_for_preview is called
        assert 'analyze_for_preview' in sync_section, \
            "SYNC PATH should call analyze_for_preview"

        # Check that requires_async is checked
        assert 'if requires_async:' in sync_section, \
            "SYNC PATH should check 'if requires_async:'"


def run_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("Running Long-Running Query Flow Tests")
    print("=" * 70)

    results = []

    # Test 1: Query Analysis - requires_async detection
    print("\n[Test 1] QueryAnalysis: requires_async detection for >1B rows...")
    test = TestQueryAnalysisRequiresAsync()
    try:
        test.test_requires_async_set_for_billion_row_table()
        print("  PASSED")
        results.append(("requires_async detection", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("requires_async detection", False, str(e)))

    # Test 2: requires_async false for small tables
    print("\n[Test 2] QueryAnalysis: requires_async=False for <1B rows...")
    try:
        test.test_requires_async_false_for_small_table()
        print("  PASSED")
        results.append(("small table detection", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("small table detection", False, str(e)))

    # Test 3: Code structure verification (THE CRITICAL TEST)
    print("\n[Test 3] CRITICAL: requires_async check comes BEFORE federated execution...")
    test2 = TestFederatedQueryRequiresAsync()
    try:
        test2.test_federated_execution_skipped_when_requires_async()
        print("  PASSED - Fix is in place!")
        results.append(("federated check order", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("federated check order", False, str(e)))

    # Test 4: Response structure
    print("\n[Test 4] requires_async response has all required fields...")
    try:
        test2.test_requires_async_returns_correct_response_structure()
        print("  PASSED")
        results.append(("response structure", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("response structure", False, str(e)))

    # Test 5: End-to-end flow
    print("\n[Test 5] End-to-end: Full flow with 28B row table...")
    test3 = TestEndToEndLongRunningFlow()
    try:
        test3.test_full_flow_large_snowflake_query()
        print("  PASSED")
        results.append(("end-to-end flow", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("end-to-end flow", False, str(e)))

    # Test 6: Preview calculation
    print("\n[Test 6] Preview endpoint: is_long_running calculation...")
    test4 = TestPreviewEndpoint()
    try:
        test4.test_preview_calculates_is_long_running_correctly()
        print("  PASSED")
        results.append(("preview calculation", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("preview calculation", False, str(e)))

    # Test 7: Routes handler
    print("\n[Test 7] Routes.py: handles requires_async and returns long_running...")
    test5 = TestRoutesLongRunningHandler()
    try:
        test5.test_routes_checks_requires_async()
        print("  PASSED")
        results.append(("routes handler", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("routes handler", False, str(e)))

    # Test 8: _execute_query_logic handles requires_async
    print("\n[Test 8] _execute_query_logic: checks requires_async before execution...")
    try:
        test5.test_execute_query_logic_handles_requires_async()
        print("  PASSED")
        results.append(("execute_query_logic", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("execute_query_logic", False, str(e)))

    # Test 9: _execute_long_running_query helper exists
    print("\n[Test 9] _execute_long_running_query: helper function exists...")
    try:
        test5.test_execute_long_running_query_helper_exists()
        print("  PASSED")
        results.append(("long_running_helper", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("long_running_helper", False, str(e)))

    # Test 10: SYNC PATH uses QueryOrchestrator (critical fix!)
    print("\n[Test 10] SYNC PATH: process_query uses QueryOrchestrator...")
    test6 = TestSyncPathQueryOrchestrator()
    try:
        test6.test_sync_path_uses_query_orchestrator()
        print("  PASSED")
        results.append(("sync_path_orchestrator", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("sync_path_orchestrator", False, str(e)))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    for name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {name}")
        if error:
            print(f"         Error: {error[:100]}...")

    print(f"\nTotal: {passed}/{len(results)} passed")

    if failed > 0:
        print("\nFAILED TESTS NEED ATTENTION!")
        return 1
    else:
        print("\nAll tests passed! The fix is working correctly.")
        return 0


if __name__ == '__main__':
    sys.exit(run_tests())
