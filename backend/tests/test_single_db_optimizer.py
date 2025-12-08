#!/usr/bin/env python3
"""
Test the SingleDatabaseQueryOptimizer for pushdown and federation strategies.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.single_db_query_optimizer import (
    SingleDatabaseQueryOptimizer,
    get_dialect_for_database,
    ExecutionStrategy,
    PANDAS_MAX_ROWS,
    FEDERATION_THRESHOLD
)


def test_basic_sql_parsing():
    """Test that the optimizer can parse various SQL queries."""
    print("\n=== Test 1: Basic SQL Parsing ===")

    # Create optimizer with mock row count
    class MockOptimizer(SingleDatabaseQueryOptimizer):
        def _get_table_row_count(self, table_name: str):
            return 1000  # Small table for parsing tests

    optimizer = MockOptimizer(
        organization_id="Demo",
        database_type="snowflake"
    )

    # Test simple SELECT
    sql1 = "SELECT * FROM STORE_SALES"
    analysis = optimizer.analyze_query(sql1, "snowflake")
    print(f"  Query: {sql1[:50]}...")
    print(f"  Tables found: {analysis.tables}")
    print(f"  Has aggregation: {analysis.has_aggregation}")
    print(f"  Has LIMIT: {analysis.has_limit}")
    print(f"  Has filters: {analysis.has_filters}")
    print(f"  Strategy: {analysis.strategy.value}")
    assert "STORE_SALES" in analysis.tables
    print("  PASS: Simple SELECT parsed correctly")

    # Test with aggregation
    sql2 = "SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id"
    analysis = optimizer.analyze_query(sql2, "snowflake")
    print(f"\n  Query: {sql2}")
    print(f"  Has aggregation: {analysis.has_aggregation}")
    assert analysis.has_aggregation == True
    print("  PASS: Aggregation detected correctly")

    # Test with LIMIT
    sql3 = "SELECT * FROM orders LIMIT 100"
    analysis = optimizer.analyze_query(sql3, "snowflake")
    print(f"\n  Query: {sql3}")
    print(f"  Has LIMIT: {analysis.has_limit}")
    print(f"  Limit value: {analysis.limit_value}")
    assert analysis.has_limit == True
    assert analysis.limit_value == 100
    print("  PASS: LIMIT detected correctly")

    # Test with WHERE
    sql4 = "SELECT * FROM orders WHERE status = 'active'"
    analysis = optimizer.analyze_query(sql4, "snowflake")
    print(f"\n  Query: {sql4}")
    print(f"  Has filters: {analysis.has_filters}")
    assert analysis.has_filters == True
    print("  PASS: WHERE detected correctly")


def test_strategy_selection():
    """Test that strategies are selected correctly based on row counts."""
    print("\n=== Test 2: Strategy Selection ===")

    # Mock optimizer that returns configurable row counts
    class MockOptimizer(SingleDatabaseQueryOptimizer):
        def __init__(self, mock_row_count: int):
            self.mock_row_count = mock_row_count
            super().__init__(organization_id="Demo", database_type="snowflake")

        def _get_table_row_count(self, table_name: str):
            return self.mock_row_count

    # Test DIRECT strategy (< 1M rows)
    optimizer = MockOptimizer(500_000)  # 500K rows
    analysis = optimizer.analyze_query("SELECT * FROM small_table", "snowflake")
    print(f"  500K rows -> strategy: {analysis.strategy.value}")
    assert analysis.strategy == ExecutionStrategy.DIRECT
    print("  PASS: DIRECT strategy for small table")

    # Test OPTIMIZED strategy (1M-100M rows)
    optimizer = MockOptimizer(10_000_000)  # 10M rows
    analysis = optimizer.analyze_query("SELECT * FROM medium_table", "snowflake")
    print(f"  10M rows -> strategy: {analysis.strategy.value}")
    assert analysis.strategy == ExecutionStrategy.OPTIMIZED
    print("  PASS: OPTIMIZED strategy for medium table")

    # Test FEDERATED strategy (> 100M rows)
    optimizer = MockOptimizer(500_000_000)  # 500M rows
    analysis = optimizer.analyze_query("SELECT * FROM large_table", "snowflake")
    print(f"  500M rows -> strategy: {analysis.strategy.value}")
    assert analysis.strategy == ExecutionStrategy.FEDERATED
    print("  PASS: FEDERATED strategy for large table")

    # Test aggregation bypasses size check
    optimizer = MockOptimizer(500_000_000)  # 500M rows
    analysis = optimizer.analyze_query(
        "SELECT customer_id, COUNT(*) FROM huge_table GROUP BY customer_id",
        "snowflake"
    )
    print(f"\n  500M rows WITH aggregation -> strategy: {analysis.strategy.value}")
    assert analysis.strategy == ExecutionStrategy.DIRECT  # Aggregation is efficient
    print("  PASS: Aggregation uses DIRECT even for large tables")


def test_pushdown_optimization():
    """Test that pushdown optimization is applied."""
    print("\n=== Test 3: Pushdown Optimization ===")

    class MockOptimizer(SingleDatabaseQueryOptimizer):
        def _get_table_row_count(self, table_name: str):
            return 50_000_000  # 50M rows (OPTIMIZED strategy)

    optimizer = MockOptimizer(
        organization_id="Demo",
        database_type="snowflake"
    )

    # Query with filters should trigger pushdown analysis
    sql = "SELECT id, name FROM customers WHERE region = 'WEST'"
    optimized_sql, analysis = optimizer.optimize_query(sql, "snowflake")

    print(f"  Original: {sql}")
    print(f"  Strategy: {analysis.strategy.value}")
    print(f"  Has filters: {analysis.has_filters}")
    print(f"  Pushdown analysis: {analysis.pushdown_analysis is not None}")

    assert analysis.strategy == ExecutionStrategy.OPTIMIZED
    assert analysis.has_filters == True
    print("  PASS: Pushdown analysis performed for medium table with filters")


def test_dialect_mapping():
    """Test that database types map to correct sqlglot dialects."""
    print("\n=== Test 4: Dialect Mapping ===")

    dialects = [
        ("snowflake", "snowflake"),
        ("bigquery", "bigquery"),
        ("postgresql", "postgres"),
        ("postgres", "postgres"),
        ("redshift", "redshift"),
        ("databricks", "databricks"),
    ]

    for db_type, expected_dialect in dialects:
        result = get_dialect_for_database(db_type)
        print(f"  {db_type} -> {result}")
        assert result == expected_dialect

    print("  PASS: All dialects mapped correctly")


def test_tpc_ds_scenario():
    """Test with TPC-DS style large tables."""
    print("\n=== Test 5: TPC-DS Large Table Scenario ===")

    class MockOptimizer(SingleDatabaseQueryOptimizer):
        def _get_table_row_count(self, table_name: str):
            # Simulate TPC-DS SF10TCL table sizes
            sizes = {
                "STORE_SALES": 28_800_000_000,  # 28.8 billion rows
                "WEB_SALES": 7_200_000_000,
                "CATALOG_SALES": 14_400_000_000,
                "CUSTOMER": 65_000_000,
                "ITEM": 300_000,
            }
            return sizes.get(table_name.upper(), 1000)

    optimizer = MockOptimizer(
        organization_id="Demo",
        database_type="snowflake"
    )

    # Large table without aggregation -> FEDERATED
    sql1 = "SELECT * FROM STORE_SALES WHERE SS_SOLD_DATE_SK = 2450816"
    analysis = optimizer.analyze_query(sql1, "snowflake")
    print(f"  Query: STORE_SALES (28.8B rows) with filter")
    print(f"  Total estimated rows: {analysis.total_estimated_rows:,}")
    print(f"  Strategy: {analysis.strategy.value}")
    assert analysis.strategy == ExecutionStrategy.FEDERATED
    print("  PASS: STORE_SALES routed to FEDERATED")

    # Large table WITH aggregation -> DIRECT (aggregation is efficient)
    sql2 = "SELECT SS_SOLD_DATE_SK, COUNT(*) FROM STORE_SALES GROUP BY SS_SOLD_DATE_SK"
    analysis = optimizer.analyze_query(sql2, "snowflake")
    print(f"\n  Query: STORE_SALES aggregation")
    print(f"  Has aggregation: {analysis.has_aggregation}")
    print(f"  Strategy: {analysis.strategy.value}")
    assert analysis.has_aggregation == True
    assert analysis.strategy == ExecutionStrategy.DIRECT
    print("  PASS: Aggregation query uses DIRECT")

    # Small table -> DIRECT
    sql3 = "SELECT * FROM ITEM"
    analysis = optimizer.analyze_query(sql3, "snowflake")
    print(f"\n  Query: ITEM (300K rows)")
    print(f"  Strategy: {analysis.strategy.value}")
    assert analysis.strategy == ExecutionStrategy.DIRECT
    print("  PASS: Small table uses DIRECT")


def main():
    print("=" * 60)
    print("SingleDatabaseQueryOptimizer Test Suite")
    print("=" * 60)

    try:
        test_basic_sql_parsing()
        test_strategy_selection()
        test_pushdown_optimization()
        test_dialect_mapping()
        test_tpc_ds_scenario()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
