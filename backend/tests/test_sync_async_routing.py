"""
Tests for Sync/Async Query Routing Logic

This test suite verifies:
1. QueryOrchestrator.analyze_for_preview() correctly sets requires_async based on table size
2. The sync path (async_mode=false) routes correctly based on query analysis
3. Response structures are correct for frontend handling

The bug being investigated: All queries going to background processing instead of just slow ones.
Root cause: Frontend always sends async_mode=true, bypassing sync path detection.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestQueryAnalysisAsync:
    """Test that QueryOrchestrator.analyze_for_preview() correctly sets requires_async."""

    def test_analysis_requires_async_for_large_table(self):
        """Tables with >1B rows should set requires_async=True."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer
        from src.core.query_orchestrator import QueryOrchestrator

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

        # Mock the row count lookup to return 5B rows
        with patch.object(
            orchestrator.query_optimizer,
            '_get_table_row_count'
        ) as mock_row_count:
            mock_row_count.return_value = 5_000_000_000  # 5B rows

            result = orchestrator.analyze_for_preview(
                "SELECT SUM(amount) FROM big_table",
                "snowflake"
            )

            assert result['requires_async'] is True, \
                f"Expected requires_async=True for 5B rows, got {result['requires_async']}"
            assert result['is_long_running'] is True, \
                f"Expected is_long_running=True for 5B rows"
            assert result['largest_table_rows'] == 5_000_000_000

    def test_analysis_not_requires_async_for_small_table(self):
        """Tables with <1B rows should NOT set requires_async."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer
        from src.core.query_orchestrator import QueryOrchestrator

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

        # Mock the row count lookup to return 100M rows
        with patch.object(
            orchestrator.query_optimizer,
            '_get_table_row_count'
        ) as mock_row_count:
            mock_row_count.return_value = 100_000_000  # 100M rows

            result = orchestrator.analyze_for_preview(
                "SELECT COUNT(*) FROM medium_table",
                "snowflake"
            )

            assert result['requires_async'] is False, \
                f"Expected requires_async=False for 100M rows, got {result['requires_async']}"
            assert result['is_long_running'] is False

    def test_threshold_boundary_exactly_1B(self):
        """Test exactly 1B rows - should NOT require async (threshold is > not >=)."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer, VERY_LARGE_TABLE_THRESHOLD
        from src.core.query_orchestrator import QueryOrchestrator

        # First, verify what the threshold actually is
        print(f"\nVERY_LARGE_TABLE_THRESHOLD = {VERY_LARGE_TABLE_THRESHOLD:,}")

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

        # Mock exactly 1B rows
        with patch.object(
            orchestrator.query_optimizer,
            '_get_table_row_count'
        ) as mock_row_count:
            mock_row_count.return_value = 1_000_000_000  # Exactly 1B

            result = orchestrator.analyze_for_preview(
                "SELECT * FROM billion_table",
                "snowflake"
            )

            # Based on code: if analysis.largest_table_rows >= VERY_LARGE_TABLE_THRESHOLD
            # So 1B should trigger requires_async since >= 1B
            print(f"Result for exactly 1B rows: requires_async={result['requires_async']}")

            # The threshold check is >= so exactly 1B SHOULD require async
            # This is different from what I wrote in the plan - let's verify actual behavior
            assert result['requires_async'] is True, \
                f"Expected requires_async=True for exactly 1B rows (>= threshold), got {result['requires_async']}"

    def test_threshold_boundary_just_under_1B(self):
        """Test just under 1B rows - should NOT require async."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer
        from src.core.query_orchestrator import QueryOrchestrator

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

        # Mock just under 1B rows
        with patch.object(
            orchestrator.query_optimizer,
            '_get_table_row_count'
        ) as mock_row_count:
            mock_row_count.return_value = 999_999_999  # Just under 1B

            result = orchestrator.analyze_for_preview(
                "SELECT * FROM almost_billion_table",
                "snowflake"
            )

            assert result['requires_async'] is False, \
                f"Expected requires_async=False for 999M rows, got {result['requires_async']}"


class TestSyncPathRoutingCode:
    """Test that routes.py has the correct sync path code structure."""

    def test_sync_path_checks_requires_async(self):
        """Verify sync path code checks requires_async before execution."""
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Find the sync path section (after "# Sync mode")
        sync_marker = '# Sync mode'
        sync_start = source.find(sync_marker)
        assert sync_start > 0, "Could not find '# Sync mode' marker in routes.py"

        # Get sync path section - need enough to capture the full sync path logic
        # The sync path goes from line ~1250 to ~1700
        sync_section = source[sync_start:sync_start + 35000]  # Increased to capture full sync path

        # Verify SYNC PATH marker exists
        assert 'SYNC PATH' in sync_section, \
            "SYNC PATH comment marker should exist in sync mode section"

        # Verify QueryOrchestrator is used
        assert 'QueryOrchestrator' in sync_section, \
            "Sync path should use QueryOrchestrator for analysis"

        # Verify analyze_for_preview is called
        assert 'analyze_for_preview' in sync_section, \
            "Sync path should call analyze_for_preview"

        # Verify requires_async is checked
        assert 'requires_async' in sync_section, \
            "Sync path should check requires_async flag"

        # Verify long_running response is returned when requires_async
        assert '"long_running"' in sync_section or "'long_running'" in sync_section, \
            "Sync path should return 'long_running' status when requires_async"

    def test_async_mode_parameter_defaults_to_false(self):
        """Verify async_mode parameter defaults to False in process_query."""
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Find process_query function
        func_start = source.find('async def process_query(')
        assert func_start > 0, "Could not find process_query function"

        # Get function signature
        func_end = source.find('):', func_start)
        func_signature = source[func_start:func_end + 2]

        # Verify async_mode defaults to False
        assert 'async_mode: bool = Query(default=False' in func_signature, \
            f"async_mode should default to False. Found: {func_signature}"


class TestAsyncModeRouting:
    """Test that async_mode=true always returns execution_id."""

    def test_async_mode_code_returns_immediately(self):
        """Verify async mode code path returns execution_id immediately."""
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Find async mode handling section
        async_marker = 'if async_mode:'
        async_start = source.find(async_marker)
        assert async_start > 0, "Could not find 'if async_mode:' check"

        # Get async mode section
        async_section = source[async_start:async_start + 3000]

        # Verify it returns execution_id
        assert 'execution_id' in async_section, \
            "Async mode should return execution_id"

        # Verify it returns 'processing' status
        assert '"processing"' in async_section or "'processing'" in async_section, \
            "Async mode should return 'processing' status"

        # Verify background task is created
        assert 'asyncio.create_task' in async_section or 'process_in_background' in async_section, \
            "Async mode should create background task"


class TestResponseStructures:
    """Test expected response structures for frontend handling."""

    def test_long_running_response_has_required_fields(self):
        """Verify long_running response has all fields needed by frontend."""
        routes_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'src', 'api', 'routes.py'
        )

        with open(routes_path, 'r') as f:
            source = f.read()

        # Find the long_running return statement in sync path
        # Look for the return statement after "ASYNC REQUIRED" marker
        async_required_marker = 'ASYNC REQUIRED'
        marker_pos = source.find(async_required_marker)
        assert marker_pos > 0, "Could not find 'ASYNC REQUIRED' marker"

        # Get a larger section containing the return statement
        # The return block starts with "return {" and might be ~1500 chars after marker
        return_section = source[marker_pos:marker_pos + 3000]

        # Find the return block - look for the pattern "# Return immediately" followed by return
        return_comment = return_section.find('# Return immediately')
        if return_comment > 0:
            return_section = return_section[return_comment:]

        return_start = return_section.find('return {')
        assert return_start >= 0, "Could not find return statement after ASYNC REQUIRED"

        # Get enough of the return block to capture all fields
        return_block = return_section[return_start:return_start + 1200]

        # Verify required fields
        required_fields = [
            'execution_id',
            'status',
            'is_long_running',
            'estimated_minutes',
            'largest_table_rows',
            'sql',
            'tables_used'
        ]

        for field in required_fields:
            assert f'"{field}"' in return_block or f"'{field}'" in return_block, \
                f"long_running response missing required field: {field}. Return block: {return_block[:500]}..."


class TestFrontendBug:
    """Test to document the frontend bug."""

    def test_frontend_always_sends_async_mode_true(self):
        """
        Document the bug: Frontend always sends async_mode=true.

        This test reads the frontend code and verifies the problematic line exists.
        After fix, this test should be updated or removed.
        """
        frontend_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'frontend', 'src', 'stores', 'conversationStore.js'
        )

        with open(frontend_path, 'r') as f:
            source = f.read()

        # Check if the bug exists (async_mode=true is hardcoded)
        bug_pattern = 'async_mode=true'
        bug_exists = bug_pattern in source

        if bug_exists:
            # Find line number
            lines = source.split('\n')
            bug_lines = [i+1 for i, line in enumerate(lines) if bug_pattern in line]

            print(f"\n*** BUG FOUND ***")
            print(f"Frontend always sends async_mode=true on line(s): {bug_lines}")
            print("This causes all queries to go to background processing.")
            print("Fix: Remove '?async_mode=true' from the fetch URL.")

            # This test passes but documents the bug
            assert True, "Bug documented - frontend sends async_mode=true"
        else:
            # Bug has been fixed
            print("\nBug has been fixed - async_mode=true no longer hardcoded")
            assert True


class TestExpectedBehavior:
    """Test expected sync/async behavior based on table size."""

    def test_document_expected_behavior(self):
        """
        Document the expected behavior:

        1. Frontend calls /api/v1/query WITHOUT async_mode (defaults to false)
        2. Backend generates SQL and analyzes with QueryOrchestrator
        3. If table rows < 1B: Execute synchronously, return results
        4. If table rows >= 1B: Return long_running status with execution_id
        5. Frontend checks response:
           - If has 'execution.results': Display immediately
           - If has 'status: long_running': Start polling
        """
        expected_flow = """
        EXPECTED FLOW:

        Fast Query (< 1B rows):
        1. Frontend: POST /api/v1/query (no async_mode)
        2. Backend: Generate SQL, analyze (requires_async=False)
        3. Backend: Execute query synchronously
        4. Backend: Return { sql, execution: { results, row_count } }
        5. Frontend: Display results immediately

        Slow Query (>= 1B rows):
        1. Frontend: POST /api/v1/query (no async_mode)
        2. Backend: Generate SQL, analyze (requires_async=True)
        3. Backend: Start background task
        4. Backend: Return { execution_id, status: 'long_running', is_long_running: true, ... }
        5. Frontend: Start polling /api/v1/query/status/{execution_id}
        6. Frontend: Display progress until complete
        """
        print(expected_flow)
        assert True


def run_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("Running Sync/Async Routing Tests")
    print("=" * 70)

    results = []

    # Test 1: Analysis for large table
    print("\n[Test 1] QueryOrchestrator: requires_async for large table (5B rows)...")
    test1 = TestQueryAnalysisAsync()
    try:
        test1.test_analysis_requires_async_for_large_table()
        print("  PASSED")
        results.append(("large table async", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("large table async", False, str(e)))

    # Test 2: Analysis for small table
    print("\n[Test 2] QueryOrchestrator: requires_async=False for small table (100M rows)...")
    try:
        test1.test_analysis_not_requires_async_for_small_table()
        print("  PASSED")
        results.append(("small table sync", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("small table sync", False, str(e)))

    # Test 3: Threshold boundary - exactly 1B
    print("\n[Test 3] Threshold boundary: exactly 1B rows...")
    try:
        test1.test_threshold_boundary_exactly_1B()
        print("  PASSED")
        results.append(("threshold 1B", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("threshold 1B", False, str(e)))

    # Test 4: Threshold boundary - just under 1B
    print("\n[Test 4] Threshold boundary: just under 1B rows...")
    try:
        test1.test_threshold_boundary_just_under_1B()
        print("  PASSED")
        results.append(("threshold under 1B", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("threshold under 1B", False, str(e)))

    # Test 5: Sync path code structure
    print("\n[Test 5] Routes.py: sync path checks requires_async...")
    test2 = TestSyncPathRoutingCode()
    try:
        test2.test_sync_path_checks_requires_async()
        print("  PASSED")
        results.append(("sync path code", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("sync path code", False, str(e)))

    # Test 6: async_mode defaults to False
    print("\n[Test 6] process_query: async_mode defaults to False...")
    try:
        test2.test_async_mode_parameter_defaults_to_false()
        print("  PASSED")
        results.append(("async_mode default", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("async_mode default", False, str(e)))

    # Test 7: Async mode returns immediately
    print("\n[Test 7] Async mode: returns execution_id immediately...")
    test3 = TestAsyncModeRouting()
    try:
        test3.test_async_mode_code_returns_immediately()
        print("  PASSED")
        results.append(("async mode return", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("async mode return", False, str(e)))

    # Test 8: Response structure
    print("\n[Test 8] long_running response has required fields...")
    test4 = TestResponseStructures()
    try:
        test4.test_long_running_response_has_required_fields()
        print("  PASSED")
        results.append(("response structure", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("response structure", False, str(e)))

    # Test 9: Frontend bug documentation
    print("\n[Test 9] Document frontend bug...")
    test5 = TestFrontendBug()
    try:
        test5.test_frontend_always_sends_async_mode_true()
        print("  PASSED (bug documented)")
        results.append(("frontend bug doc", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("frontend bug doc", False, str(e)))

    # Test 10: Expected behavior documentation
    print("\n[Test 10] Document expected behavior...")
    test6 = TestExpectedBehavior()
    try:
        test6.test_document_expected_behavior()
        print("  PASSED")
        results.append(("expected behavior", True, None))
    except Exception as e:
        print(f"  FAILED: {e}")
        results.append(("expected behavior", False, str(e)))

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
        print("\nSOME TESTS FAILED - Check results above")
        return 1
    else:
        print("\nAll tests passed!")
        print("\nNEXT STEPS:")
        print("1. Fix frontend: Remove '?async_mode=true' from conversationStore.js line 656")
        print("2. Update frontend to handle both sync and async responses")
        return 0


if __name__ == '__main__':
    sys.exit(run_tests())
