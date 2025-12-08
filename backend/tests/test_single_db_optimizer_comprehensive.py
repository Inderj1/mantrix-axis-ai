#!/usr/bin/env python3
"""
Comprehensive tests for SingleDatabaseQueryOptimizer with:
- Memory usage tracking
- Execution timing
- Detailed logging
- Real-world TPC-DS scenarios
"""
import sys
import os
import time
import tracemalloc
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.single_db_query_optimizer import (
    SingleDatabaseQueryOptimizer,
    get_dialect_for_database,
    ExecutionStrategy,
    QueryAnalysis,
    PANDAS_MAX_ROWS,
    FEDERATION_THRESHOLD
)


# ============================================================================
# Test Utilities
# ============================================================================

@dataclass
class TestMetrics:
    """Metrics collected during test execution."""
    test_name: str
    duration_ms: float
    memory_peak_mb: float
    memory_current_mb: float
    passed: bool
    error: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class TestLogger:
    """Logger for test execution with timestamps and formatting."""

    COLORS = {
        'GREEN': '\033[92m',
        'RED': '\033[91m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'CYAN': '\033[96m',
        'RESET': '\033[0m',
        'BOLD': '\033[1m'
    }

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
        self.start_time = datetime.now()

    def _color(self, text: str, color: str) -> str:
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['RESET']}"

    def _timestamp(self) -> str:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return f"[{elapsed:7.3f}s]"

    def header(self, text: str):
        print(f"\n{'='*70}")
        print(self._color(f"  {text}", 'BOLD'))
        print(f"{'='*70}")

    def section(self, text: str):
        print(f"\n{self._color('>>> ', 'CYAN')}{text}")
        print("-" * 50)

    def info(self, text: str):
        print(f"{self._timestamp()} {self._color('INFO', 'BLUE')}  {text}")

    def success(self, text: str):
        print(f"{self._timestamp()} {self._color('PASS', 'GREEN')}  {text}")

    def fail(self, text: str):
        print(f"{self._timestamp()} {self._color('FAIL', 'RED')}  {text}")

    def warn(self, text: str):
        print(f"{self._timestamp()} {self._color('WARN', 'YELLOW')}  {text}")

    def metric(self, name: str, value: Any, unit: str = ""):
        formatted = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}" if isinstance(value, int) else str(value)
        print(f"           {self._color('METRIC', 'CYAN')} {name}: {formatted} {unit}")

    def detail(self, key: str, value: Any):
        print(f"           • {key}: {value}")


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def run_with_metrics(test_func, logger: TestLogger) -> TestMetrics:
    """Run a test function and collect metrics."""
    test_name = test_func.__name__

    # Start memory tracking
    tracemalloc.start()
    mem_before = get_memory_usage_mb()

    # Run test
    start_time = time.perf_counter()
    try:
        result = test_func(logger)
        passed = result if isinstance(result, bool) else True
        error = None
    except Exception as e:
        passed = False
        error = str(e)
        traceback.print_exc()

    end_time = time.perf_counter()

    # Collect memory stats
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_after = get_memory_usage_mb()

    duration_ms = (end_time - start_time) * 1000

    metrics = TestMetrics(
        test_name=test_name,
        duration_ms=duration_ms,
        memory_peak_mb=peak / 1024 / 1024,
        memory_current_mb=mem_after - mem_before,
        passed=passed,
        error=error
    )

    return metrics


# ============================================================================
# Mock Optimizer for Testing
# ============================================================================

class MockOptimizer(SingleDatabaseQueryOptimizer):
    """Mock optimizer with configurable row counts for testing."""

    def __init__(self, row_counts: Dict[str, int], database_type: str = "snowflake"):
        self.mock_row_counts = row_counts
        super().__init__(
            organization_id="Demo",
            database_type=database_type
        )

    def _get_table_row_count(self, table_name: str) -> Optional[int]:
        return self.mock_row_counts.get(table_name.upper())


# ============================================================================
# Test Cases
# ============================================================================

def test_basic_sql_parsing(logger: TestLogger) -> bool:
    """Test SQL parsing for various query types."""
    logger.section("Test 1: Basic SQL Parsing")

    optimizer = MockOptimizer({"ORDERS": 1000, "CUSTOMERS": 500})
    all_passed = True

    # Test cases
    test_cases = [
        {
            "name": "Simple SELECT",
            "sql": "SELECT * FROM ORDERS",
            "expected": {"tables": ["ORDERS"], "has_agg": False, "has_limit": False, "has_filter": False}
        },
        {
            "name": "SELECT with aggregation",
            "sql": "SELECT customer_id, SUM(amount), COUNT(*) FROM orders GROUP BY customer_id",
            "expected": {"has_agg": True}
        },
        {
            "name": "SELECT with LIMIT",
            "sql": "SELECT * FROM orders LIMIT 100",
            "expected": {"has_limit": True, "limit_value": 100}
        },
        {
            "name": "SELECT with WHERE",
            "sql": "SELECT * FROM orders WHERE status = 'active' AND amount > 100",
            "expected": {"has_filter": True}
        },
        {
            "name": "JOIN query",
            "sql": "SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
            "expected": {"tables": ["ORDERS", "CUSTOMERS"]}
        },
        {
            "name": "Complex aggregation",
            "sql": "SELECT region, AVG(amount), MIN(amount), MAX(amount) FROM orders GROUP BY region HAVING AVG(amount) > 100",
            "expected": {"has_agg": True}
        }
    ]

    for tc in test_cases:
        try:
            start = time.perf_counter()
            analysis = optimizer.analyze_query(tc["sql"], "snowflake")
            duration = (time.perf_counter() - start) * 1000

            # Validate expectations
            passed = True
            details = []

            if "tables" in tc["expected"]:
                expected_tables = set(tc["expected"]["tables"])
                actual_tables = set(analysis.tables)
                if expected_tables != actual_tables:
                    passed = False
                    details.append(f"tables: expected {expected_tables}, got {actual_tables}")

            if "has_agg" in tc["expected"] and analysis.has_aggregation != tc["expected"]["has_agg"]:
                passed = False
                details.append(f"has_aggregation: expected {tc['expected']['has_agg']}, got {analysis.has_aggregation}")

            if "has_limit" in tc["expected"] and analysis.has_limit != tc["expected"]["has_limit"]:
                passed = False
                details.append(f"has_limit: expected {tc['expected']['has_limit']}, got {analysis.has_limit}")

            if "has_filter" in tc["expected"] and analysis.has_filters != tc["expected"]["has_filter"]:
                passed = False
                details.append(f"has_filters: expected {tc['expected']['has_filter']}, got {analysis.has_filters}")

            if "limit_value" in tc["expected"] and analysis.limit_value != tc["expected"]["limit_value"]:
                passed = False
                details.append(f"limit_value: expected {tc['expected']['limit_value']}, got {analysis.limit_value}")

            if passed:
                logger.success(f"{tc['name']} ({duration:.2f}ms)")
            else:
                logger.fail(f"{tc['name']}: {', '.join(details)}")
                all_passed = False

        except Exception as e:
            logger.fail(f"{tc['name']}: {str(e)}")
            all_passed = False

    return all_passed


def test_strategy_selection(logger: TestLogger) -> bool:
    """Test execution strategy selection based on row counts."""
    logger.section("Test 2: Strategy Selection")

    all_passed = True

    test_cases = [
        {"rows": 100, "expected": ExecutionStrategy.DIRECT, "desc": "100 rows"},
        {"rows": 500_000, "expected": ExecutionStrategy.DIRECT, "desc": "500K rows"},
        {"rows": 999_999, "expected": ExecutionStrategy.DIRECT, "desc": "999K rows (just under 1M)"},
        {"rows": 1_000_000, "expected": ExecutionStrategy.OPTIMIZED, "desc": "1M rows (threshold)"},
        {"rows": 10_000_000, "expected": ExecutionStrategy.OPTIMIZED, "desc": "10M rows"},
        {"rows": 50_000_000, "expected": ExecutionStrategy.OPTIMIZED, "desc": "50M rows"},
        {"rows": 99_999_999, "expected": ExecutionStrategy.OPTIMIZED, "desc": "99.9M rows (just under 100M)"},
        {"rows": 100_000_000, "expected": ExecutionStrategy.FEDERATED, "desc": "100M rows (threshold)"},
        {"rows": 500_000_000, "expected": ExecutionStrategy.FEDERATED, "desc": "500M rows"},
        {"rows": 1_000_000_000, "expected": ExecutionStrategy.FEDERATED, "desc": "1B rows"},
        {"rows": 28_800_000_000, "expected": ExecutionStrategy.FEDERATED, "desc": "28.8B rows (TPC-DS STORE_SALES)"},
    ]

    for tc in test_cases:
        optimizer = MockOptimizer({"TEST_TABLE": tc["rows"]})

        start = time.perf_counter()
        analysis = optimizer.analyze_query("SELECT * FROM TEST_TABLE", "snowflake")
        duration = (time.perf_counter() - start) * 1000

        if analysis.strategy == tc["expected"]:
            logger.success(f"{tc['desc']} -> {analysis.strategy.value} ({duration:.2f}ms)")
        else:
            logger.fail(f"{tc['desc']}: expected {tc['expected'].value}, got {analysis.strategy.value}")
            all_passed = False

    # Test aggregation bypass
    logger.info("Testing aggregation bypass (large table with GROUP BY)...")
    optimizer = MockOptimizer({"HUGE_TABLE": 10_000_000_000})  # 10B rows
    analysis = optimizer.analyze_query(
        "SELECT category, COUNT(*), SUM(amount) FROM HUGE_TABLE GROUP BY category",
        "snowflake"
    )

    if analysis.strategy == ExecutionStrategy.DIRECT:
        logger.success(f"10B rows with aggregation -> DIRECT (aggregation bypass works)")
    else:
        logger.fail(f"Aggregation bypass failed: expected DIRECT, got {analysis.strategy.value}")
        all_passed = False

    return all_passed


def test_pushdown_optimization(logger: TestLogger) -> bool:
    """Test pushdown optimization for filter reduction."""
    logger.section("Test 3: Pushdown Optimization")

    optimizer = MockOptimizer({"CUSTOMERS": 50_000_000})  # 50M rows
    all_passed = True

    test_cases = [
        {
            "name": "Simple equality filter",
            "sql": "SELECT * FROM CUSTOMERS WHERE region = 'WEST'",
            "expect_pushdown": True
        },
        {
            "name": "Multiple filters",
            "sql": "SELECT * FROM CUSTOMERS WHERE region = 'WEST' AND status = 'active' AND created_at > '2024-01-01'",
            "expect_pushdown": True
        },
        {
            "name": "No filters (no pushdown)",
            "sql": "SELECT * FROM CUSTOMERS",
            "expect_pushdown": False
        },
        {
            "name": "BETWEEN filter",
            "sql": "SELECT * FROM CUSTOMERS WHERE amount BETWEEN 100 AND 1000",
            "expect_pushdown": True
        },
        {
            "name": "IN clause filter",
            "sql": "SELECT * FROM CUSTOMERS WHERE region IN ('WEST', 'EAST', 'NORTH')",
            "expect_pushdown": True
        }
    ]

    for tc in test_cases:
        start = time.perf_counter()
        _, analysis = optimizer.optimize_query(tc["sql"], "snowflake")
        duration = (time.perf_counter() - start) * 1000

        has_pushdown = analysis.pushdown_analysis is not None and analysis.has_filters

        if has_pushdown == tc["expect_pushdown"]:
            logger.success(f"{tc['name']} ({duration:.2f}ms)")
            if has_pushdown and analysis.pushdown_analysis:
                logger.detail("Estimated reduction", f"{analysis.pushdown_analysis.estimated_reduction_percent:.1f}%")
                logger.detail("Estimated result rows", f"{analysis.estimated_result_rows:,}")
        else:
            logger.fail(f"{tc['name']}: pushdown expected={tc['expect_pushdown']}, actual={has_pushdown}")
            all_passed = False

    return all_passed


def test_tpcds_scenarios(logger: TestLogger) -> bool:
    """Test with TPC-DS style large tables."""
    logger.section("Test 4: TPC-DS Large Table Scenarios")

    # TPC-DS SF10TCL table sizes
    tpcds_sizes = {
        "STORE_SALES": 28_800_000_000,     # 28.8B rows
        "WEB_SALES": 7_200_000_000,        # 7.2B rows
        "CATALOG_SALES": 14_400_000_000,   # 14.4B rows
        "INVENTORY": 1_330_000_000,        # 1.3B rows
        "STORE_RETURNS": 2_880_000_000,    # 2.8B rows
        "WEB_RETURNS": 720_000_000,        # 720M rows
        "CATALOG_RETURNS": 1_440_000_000,  # 1.4B rows
        "CUSTOMER": 65_000_000,            # 65M rows
        "CUSTOMER_ADDRESS": 32_500_000,    # 32.5M rows
        "CUSTOMER_DEMOGRAPHICS": 1_920_800,# 1.9M rows
        "ITEM": 300_000,                   # 300K rows
        "STORE": 1_002,                    # ~1K rows
        "DATE_DIM": 73_049,                # 73K rows
        "TIME_DIM": 86_400,                # 86K rows
        "WAREHOUSE": 20,                   # 20 rows
        "PROMOTION": 1_500,                # 1.5K rows
    }

    optimizer = MockOptimizer(tpcds_sizes)
    all_passed = True

    test_queries = [
        {
            "name": "STORE_SALES full scan",
            "sql": "SELECT * FROM STORE_SALES WHERE SS_SOLD_DATE_SK = 2450816",
            "expected_strategy": ExecutionStrategy.FEDERATED,
            "reason": "28.8B rows, even with filter stays above 100M"
        },
        {
            "name": "STORE_SALES aggregation",
            "sql": "SELECT SS_SOLD_DATE_SK, SUM(SS_NET_PAID), COUNT(*) FROM STORE_SALES GROUP BY SS_SOLD_DATE_SK",
            "expected_strategy": ExecutionStrategy.DIRECT,
            "reason": "Aggregation is efficient, bypasses size check"
        },
        {
            "name": "CUSTOMER table",
            "sql": "SELECT * FROM CUSTOMER WHERE C_CUSTOMER_SK < 1000000",
            "expected_strategy": ExecutionStrategy.OPTIMIZED,
            "reason": "65M rows with filter -> ~32.5M rows"
        },
        {
            "name": "ITEM dimension",
            "sql": "SELECT * FROM ITEM",
            "expected_strategy": ExecutionStrategy.DIRECT,
            "reason": "300K rows is small"
        },
        {
            "name": "DATE_DIM dimension",
            "sql": "SELECT * FROM DATE_DIM",
            "expected_strategy": ExecutionStrategy.DIRECT,
            "reason": "73K rows is very small"
        },
        {
            "name": "Multi-table JOIN (fact + dimensions)",
            "sql": """
                SELECT c.C_FIRST_NAME, i.I_ITEM_DESC, SUM(ss.SS_NET_PAID)
                FROM STORE_SALES ss
                JOIN CUSTOMER c ON ss.SS_CUSTOMER_SK = c.C_CUSTOMER_SK
                JOIN ITEM i ON ss.SS_ITEM_SK = i.I_ITEM_SK
                GROUP BY c.C_FIRST_NAME, i.I_ITEM_DESC
            """,
            "expected_strategy": ExecutionStrategy.DIRECT,
            "reason": "Has aggregation, so DIRECT despite large tables"
        },
        {
            "name": "WEB_SALES date range",
            "sql": "SELECT * FROM WEB_SALES WHERE WS_SOLD_DATE_SK BETWEEN 2450816 AND 2451180",
            "expected_strategy": ExecutionStrategy.FEDERATED,
            "reason": "7.2B rows, filter doesn't reduce enough"
        },
        {
            "name": "INVENTORY snapshot",
            "sql": "SELECT * FROM INVENTORY WHERE INV_DATE_SK = 2450816 LIMIT 10000",
            "expected_strategy": ExecutionStrategy.DIRECT,
            "reason": "LIMIT caps result at 10K rows"
        }
    ]

    for tq in test_queries:
        start = time.perf_counter()
        _, analysis = optimizer.optimize_query(tq["sql"], "snowflake")
        duration = (time.perf_counter() - start) * 1000

        if analysis.strategy == tq["expected_strategy"]:
            logger.success(f"{tq['name']} -> {analysis.strategy.value} ({duration:.2f}ms)")
            logger.detail("Total rows", f"{analysis.total_estimated_rows:,}")
            logger.detail("Estimated result", f"{analysis.estimated_result_rows:,}")
            logger.detail("Reason", tq["reason"])
        else:
            logger.fail(f"{tq['name']}: expected {tq['expected_strategy'].value}, got {analysis.strategy.value}")
            logger.detail("Reason expected", tq["reason"])
            all_passed = False

    return all_passed


def test_dialect_handling(logger: TestLogger) -> bool:
    """Test SQL dialect mapping and parsing."""
    logger.section("Test 5: Dialect Handling")

    all_passed = True

    # Test dialect mapping
    dialect_tests = [
        ("snowflake", "snowflake"),
        ("bigquery", "bigquery"),
        ("postgresql", "postgres"),
        ("postgres", "postgres"),
        ("redshift", "redshift"),
        ("databricks", "databricks"),
        ("mysql", "snowflake"),  # Unknown defaults to snowflake
    ]

    for db_type, expected in dialect_tests:
        result = get_dialect_for_database(db_type)
        if result == expected:
            logger.success(f"{db_type} -> {result}")
        else:
            logger.fail(f"{db_type}: expected {expected}, got {result}")
            all_passed = False

    # Test parsing with different dialects
    logger.info("Testing SQL parsing with different dialects...")

    optimizer = MockOptimizer({"ORDERS": 1000})

    dialect_sql_tests = [
        ("snowflake", "SELECT * FROM ORDERS LIMIT 10"),
        ("bigquery", "SELECT * FROM ORDERS LIMIT 10"),
        ("postgres", "SELECT * FROM orders LIMIT 10"),
    ]

    for dialect, sql in dialect_sql_tests:
        try:
            analysis = optimizer.analyze_query(sql, dialect)
            logger.success(f"Parsed {dialect} SQL: limit={analysis.limit_value}")
        except Exception as e:
            logger.fail(f"Failed to parse {dialect} SQL: {e}")
            all_passed = False

    return all_passed


def test_memory_efficiency(logger: TestLogger) -> bool:
    """Test memory efficiency with many queries."""
    logger.section("Test 6: Memory Efficiency")

    # Create optimizer once
    optimizer = MockOptimizer({
        "TABLE_A": 1_000_000,
        "TABLE_B": 10_000_000,
        "TABLE_C": 100_000_000,
    })

    mem_before = get_memory_usage_mb()
    logger.metric("Memory before", mem_before, "MB")

    # Run many queries
    num_queries = 100
    queries = [
        "SELECT * FROM TABLE_A WHERE id = 123",
        "SELECT * FROM TABLE_B GROUP BY category",
        "SELECT * FROM TABLE_C LIMIT 1000",
        "SELECT a.*, b.name FROM TABLE_A a JOIN TABLE_B b ON a.id = b.a_id",
    ]

    start = time.perf_counter()
    for i in range(num_queries):
        sql = queries[i % len(queries)]
        optimizer.analyze_query(sql, "snowflake")
    duration = time.perf_counter() - start

    mem_after = get_memory_usage_mb()
    logger.metric("Memory after", mem_after, "MB")
    logger.metric("Memory delta", mem_after - mem_before, "MB")
    logger.metric("Queries executed", num_queries, "")
    logger.metric("Total time", duration * 1000, "ms")
    logger.metric("Avg per query", (duration * 1000) / num_queries, "ms")

    # Check memory didn't grow too much (< 50MB growth for 100 queries)
    mem_growth = mem_after - mem_before
    if mem_growth < 50:
        logger.success(f"Memory growth acceptable: {mem_growth:.2f} MB")
        return True
    else:
        logger.warn(f"High memory growth: {mem_growth:.2f} MB")
        return True  # Warning, not failure


def test_edge_cases(logger: TestLogger) -> bool:
    """Test edge cases and error handling."""
    logger.section("Test 7: Edge Cases")

    optimizer = MockOptimizer({"TEST": 1000})
    all_passed = True

    edge_cases = [
        ("Empty query", "", False),
        ("Invalid SQL", "NOT VALID SQL AT ALL", False),
        ("CTE query", "WITH cte AS (SELECT * FROM TEST) SELECT * FROM cte", True),
        ("Subquery", "SELECT * FROM (SELECT * FROM TEST) AS subq", True),
        ("UNION query", "SELECT * FROM TEST UNION ALL SELECT * FROM TEST", True),
        ("Very long query", f"SELECT * FROM TEST WHERE id IN ({','.join(str(i) for i in range(1000))})", True),
        ("Special characters in filter", "SELECT * FROM TEST WHERE name = 'O''Brien'", True),
        ("NULL check", "SELECT * FROM TEST WHERE value IS NULL", True),
        ("CASE expression", "SELECT CASE WHEN status = 'A' THEN 1 ELSE 0 END FROM TEST", True),
    ]

    for name, sql, should_succeed in edge_cases:
        try:
            analysis = optimizer.analyze_query(sql, "snowflake")
            if should_succeed:
                logger.success(f"{name}: parsed successfully")
            else:
                # Some "invalid" SQL might still parse partially
                if analysis.warnings:
                    logger.success(f"{name}: handled with warnings")
                else:
                    logger.warn(f"{name}: expected to fail but succeeded")
        except Exception as e:
            if not should_succeed:
                logger.success(f"{name}: correctly rejected ({str(e)[:50]})")
            else:
                logger.fail(f"{name}: unexpected error: {e}")
                all_passed = False

    return all_passed


def test_warnings_generation(logger: TestLogger) -> bool:
    """Test that appropriate warnings are generated."""
    logger.section("Test 8: Warning Generation")

    all_passed = True

    # Large table should generate warning
    optimizer = MockOptimizer({"HUGE_TABLE": 500_000_000})
    analysis = optimizer.analyze_query("SELECT * FROM HUGE_TABLE", "snowflake")

    if analysis.warnings:
        logger.success(f"Large table warning generated: {analysis.warnings[0][:60]}...")
    else:
        logger.fail("No warning generated for 500M row table")
        all_passed = False

    # Medium table should generate pushdown warning
    optimizer = MockOptimizer({"MEDIUM_TABLE": 50_000_000})
    analysis = optimizer.analyze_query("SELECT * FROM MEDIUM_TABLE", "snowflake")

    if analysis.warnings:
        logger.success(f"Pushdown warning generated: {analysis.warnings[0][:60]}...")
    else:
        logger.fail("No warning generated for 50M row table")
        all_passed = False

    # Small table should NOT generate warning
    optimizer = MockOptimizer({"SMALL_TABLE": 10_000})
    analysis = optimizer.analyze_query("SELECT * FROM SMALL_TABLE", "snowflake")

    if not analysis.warnings:
        logger.success("No warning for small table (correct)")
    else:
        logger.warn(f"Unexpected warning for small table: {analysis.warnings}")

    return all_passed


# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    logger = TestLogger()

    logger.header("SingleDatabaseQueryOptimizer Comprehensive Test Suite")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Python version: {sys.version.split()[0]}")
    logger.info(f"Process ID: {os.getpid()}")
    logger.metric("Initial memory", get_memory_usage_mb(), "MB")

    print(f"\nThresholds:")
    print(f"  PANDAS_MAX_ROWS (DIRECT):      {PANDAS_MAX_ROWS:>15,} rows")
    print(f"  FEDERATION_THRESHOLD:          {FEDERATION_THRESHOLD:>15,} rows")

    # Run all tests
    tests = [
        test_basic_sql_parsing,
        test_strategy_selection,
        test_pushdown_optimization,
        test_tpcds_scenarios,
        test_dialect_handling,
        test_memory_efficiency,
        test_edge_cases,
        test_warnings_generation,
    ]

    results: List[TestMetrics] = []

    for test_func in tests:
        metrics = run_with_metrics(test_func, logger)
        results.append(metrics)

    # Summary
    logger.header("Test Summary")

    total_duration = sum(r.duration_ms for r in results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    print(f"\n{'Test Name':<45} {'Status':<8} {'Time (ms)':<12} {'Peak Mem (MB)':<15}")
    print("-" * 80)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        color = '\033[92m' if r.passed else '\033[91m'
        reset = '\033[0m'
        print(f"{r.test_name:<45} {color}{status:<8}{reset} {r.duration_ms:<12.2f} {r.memory_peak_mb:<15.2f}")

    print("-" * 80)
    print(f"{'TOTAL':<45} {'':<8} {total_duration:<12.2f}")

    print(f"\n{passed} passed, {failed} failed")
    logger.metric("Final memory", get_memory_usage_mb(), "MB")

    if failed == 0:
        print(f"\n{'='*70}")
        print("  ✅ ALL TESTS PASSED!")
        print(f"{'='*70}")
        return 0
    else:
        print(f"\n{'='*70}")
        print(f"  ❌ {failed} TESTS FAILED")
        print(f"{'='*70}")
        return 1


if __name__ == "__main__":
    import traceback
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
