#!/usr/bin/env python3
"""
Test the Join Path Finder with Jena knowledge graph.
"""
import os
os.environ['SKIP_REDIS'] = 'true'

from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph
from src.core.knowledge_graph.join_path_finder import JoinPathFinder


def test_direct_joins():
    """Test finding direct joins between tables."""
    print("=" * 80)
    print("TEST 1: Find Direct Joins")
    print("=" * 80)

    kg = get_jena_knowledge_graph()
    finder = JoinPathFinder(kg)

    # Test 1: dataset_25m_table -> customer_master_analysis
    print("\n📊 Test: dataset_25m_table → customer_master_analysis")
    print("-" * 60)
    joins = finder.find_direct_join("dataset_25m_table", "customer_master_analysis")

    if joins:
        for join in joins:
            print(f"✓ {join.to_sql()}")
    else:
        print("✗ No direct join found")

    # Test 2: dataset_25m_table -> GL_Accounts
    print("\n📊 Test: dataset_25m_table → GL_Accounts")
    print("-" * 60)
    joins = finder.find_direct_join("dataset_25m_table", "GL_Accounts")

    if joins:
        for join in joins:
            print(f"✓ {join.to_sql()}")
    else:
        print("✗ No direct join found")


def test_multi_hop():
    """Test finding multi-hop join paths."""
    print("\n" + "=" * 80)
    print("TEST 2: Find Multi-Hop Paths")
    print("=" * 80)

    kg = get_jena_knowledge_graph()
    finder = JoinPathFinder(kg)

    # Test: dataset_25m_table -> product_customer_matrix (might need intermediate table)
    print("\n📊 Test: dataset_25m_table → product_customer_matrix (max 2 hops)")
    print("-" * 60)

    paths = finder.find_multi_hop_paths("dataset_25m_table", "product_customer_matrix", max_hops=2)

    if paths:
        for i, path in enumerate(paths, 1):
            print(f"\nPath {i} ({path.total_hops} hops):")
            print(f"  Tables: {' → '.join(path.tables_involved)}")
            print("  SQL:")
            for join_sql in path.to_sql_joins():
                print(f"    {join_sql}")
    else:
        print("✗ No multi-hop paths found")


def test_join_order():
    """Test recommending join order for multiple tables."""
    print("\n" + "=" * 80)
    print("TEST 3: Recommend Join Order")
    print("=" * 80)

    kg = get_jena_knowledge_graph()
    finder = JoinPathFinder(kg)

    # Test: Join customer + product + GL data
    tables = [
        "dataset_25m_table",        # Fact table (large)
        "customer_master_analysis",  # Dimension (medium)
        "GL_Accounts"               # Dimension (small)
    ]

    print(f"\n📊 Test: Optimal join order for {len(tables)} tables")
    print(f"   Tables: {', '.join(tables)}")
    print("-" * 60)

    join_order = finder.recommend_join_order(tables)

    if join_order:
        base_table = tables[0]
        print(f"\n✓ Recommended Join Order:")
        print(f"   Base Table: {base_table}")
        print()

        for i, join_path in enumerate(join_order, 1):
            print(f"   {i}. {join_path.to_sql()}")
    else:
        print("✗ Could not determine join order")

    # Print summary
    print("\n" + "=" * 80)
    print("Join Summary:")
    print("=" * 80)
    summary = finder.get_join_summary(tables)
    print(summary)


def test_real_world_query():
    """Test a real-world multi-table query scenario."""
    print("\n" + "=" * 80)
    print("TEST 4: Real-World Query Scenario")
    print("=" * 80)

    kg = get_jena_knowledge_graph()
    finder = JoinPathFinder(kg)

    # Scenario: "Show top 10 customers by revenue with their RFM segments and product preferences"
    # Tables needed: dataset_25m_table, customer_master_analysis, product_customer_matrix
    tables = [
        "dataset_25m_table",
        "customer_master_analysis",
        "product_customer_matrix"
    ]

    print("\n📊 Scenario: Top customers by revenue + RFM + product preferences")
    print(f"   Tables: {', '.join(tables)}")
    print("-" * 60)

    join_order = finder.recommend_join_order(tables)

    if join_order:
        print(f"\n✓ Query Plan:")
        print(f"   SELECT ...")
        print(f"   FROM {tables[0]}")

        for join_path in join_order:
            print(f"   {join_path.to_sql()}")

        print(f"   WHERE ...")
        print(f"   GROUP BY ...")
        print(f"   ORDER BY SUM(revenue) DESC")
        print(f"   LIMIT 10")

        print(f"\n✓ Successfully generated query plan with {len(join_order)} joins")
    else:
        print("✗ Could not generate query plan")


def main():
    """Run all tests."""
    print("=" * 80)
    print("TESTING JOIN PATH FINDER WITH JENA KNOWLEDGE GRAPH")
    print("=" * 80)

    try:
        test_direct_joins()
        test_multi_hop()
        test_join_order()
        test_real_world_query()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
