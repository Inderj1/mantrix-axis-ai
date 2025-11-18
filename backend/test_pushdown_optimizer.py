"""
Quick test of Query Pushdown Optimizer

Demonstrates how pushdown optimization reduces data transfer by:
1. Pushing WHERE filters to source databases
2. Selecting only required columns
3. Applying LIMIT at the source
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.core.query_pushdown_optimizer import QueryPushdownOptimizer


def test_pushdown_optimizer():
    """Test query pushdown optimization."""
    print("\n" + "="*80)
    print("Query Pushdown Optimizer Test")
    print("="*80)

    optimizer = QueryPushdownOptimizer()

    # Test Query: Cross-database JOIN with filters
    test_query = """
        SELECT
            c.customer_id,
            c.customer_name,
            c.email,
            o.order_id,
            o.total_amount,
            o.status
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE c.active = true
          AND c.country = 'USA'
          AND o.order_date >= '2024-01-01'
        LIMIT 100
    """

    print("\n📋 Original Query:")
    print(test_query)

    # Analyze pushdown for 'customers' table
    print("\n" + "-"*80)
    print("1️⃣  Analyzing pushdown for 'customers' table")
    print("-"*80)

    analysis = optimizer.analyze_pushdown_opportunities(
        sql=test_query,
        table_name='customers',
        table_alias='c'
    )

    print(f"\n✅ Pushdown Analysis:")
    print(f"   Can pushdown filters:     {analysis.can_pushdown_filters}")
    print(f"   Can pushdown projections: {analysis.can_pushdown_projections}")
    print(f"   Can pushdown limit:       {analysis.can_pushdown_limit}")

    if analysis.pushdown_filters:
        print(f"\n   Filters to push down ({len(analysis.pushdown_filters)}):")
        for i, filter_sql in enumerate(analysis.pushdown_filters, 1):
            print(f"     {i}. {filter_sql}")

    if analysis.required_columns:
        print(f"\n   Required columns ({len(analysis.required_columns)}):")
        for col in sorted(analysis.required_columns):
            print(f"     - {col}")

    if analysis.limit_value:
        print(f"\n   LIMIT value: {analysis.limit_value}")

    print(f"\n   📊 Estimated data reduction: {analysis.estimated_reduction_percent:.1f}%")

    if analysis.optimized_sql:
        print(f"\n   🚀 Optimized SQL for 'customers' table:")
        print(f"   {'-'*76}")
        for line in analysis.optimized_sql.split('\n'):
            print(f"   {line}")
        print(f"   {'-'*76}")

    # Analyze pushdown for 'orders' table
    print("\n" + "-"*80)
    print("2️⃣  Analyzing pushdown for 'orders' table")
    print("-"*80)

    analysis_orders = optimizer.analyze_pushdown_opportunities(
        sql=test_query,
        table_name='orders',
        table_alias='o'
    )

    print(f"\n✅ Pushdown Analysis:")
    print(f"   Can pushdown filters:     {analysis_orders.can_pushdown_filters}")
    print(f"   Can pushdown projections: {analysis_orders.can_pushdown_projections}")

    if analysis_orders.pushdown_filters:
        print(f"\n   Filters to push down ({len(analysis_orders.pushdown_filters)}):")
        for i, filter_sql in enumerate(analysis_orders.pushdown_filters, 1):
            print(f"     {i}. {filter_sql}")

    if analysis_orders.required_columns:
        print(f"\n   Required columns ({len(analysis_orders.required_columns)}):")
        for col in sorted(analysis_orders.required_columns):
            print(f"     - {col}")

    print(f"\n   📊 Estimated data reduction: {analysis_orders.estimated_reduction_percent:.1f}%")

    if analysis_orders.optimized_sql:
        print(f"\n   🚀 Optimized SQL for 'orders' table:")
        print(f"   {'-'*76}")
        for line in analysis_orders.optimized_sql.split('\n'):
            print(f"   {line}")
        print(f"   {'-'*76}")

    # Summary
    print("\n" + "="*80)
    print("📈 Performance Impact Summary")
    print("="*80)

    print(f"""
Without Pushdown Optimization:
  1. Fetch ALL rows from 'customers' table → Network transfer: 100%
  2. Fetch ALL rows from 'orders' table → Network transfer: 100%
  3. Filter and JOIN locally

With Pushdown Optimization:
  1. Fetch FILTERED 'customers' (active=true, country='USA') → Network transfer: ~{100-analysis.estimated_reduction_percent:.1f}%
  2. Fetch FILTERED 'orders' (order_date >= '2024-01-01') → Network transfer: ~{100-analysis_orders.estimated_reduction_percent:.1f}%
  3. JOIN smaller datasets locally

Estimated overall data transfer reduction: {(analysis.estimated_reduction_percent + analysis_orders.estimated_reduction_percent) / 2:.1f}%
Estimated query speedup: 2-10x (depending on filter selectivity)
    """)

    print("="*80)
    print("✅ Pushdown Optimizer Test Complete!")
    print("="*80)


if __name__ == '__main__':
    test_pushdown_optimizer()
