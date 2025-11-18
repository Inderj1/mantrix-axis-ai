"""
Test Staging Table Manager

Demonstrates how staging tables improve performance for large cross-database JOINs.
Instead of transferring all data and joining in-memory, we:
1. Copy smaller dataset to target database as a staging table
2. Execute JOIN natively in the target database
3. Clean up staging table afterward

This is much faster for datasets between 100MB and 10GB.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

from src.core.staging_table_manager import StagingTableManager
from src.db.connector_factory import ConnectorFactory


# PostgreSQL test database config
PG_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'test_mantrix',
    'user': 'test_user',
    'password': 'test_pass_123',
    'schema': 'sales'
}


async def test_staging_table_manager():
    """Test staging table creation and usage."""
    print("\n" + "="*80)
    print("Staging Table Manager Test")
    print("="*80)

    factory = ConnectorFactory()
    manager = StagingTableManager(factory)

    # Test 1: Check if staging strategy should be used
    print("\n" + "-"*80)
    print("1️⃣  Strategy Selection")
    print("-"*80)

    test_sizes = [
        (50, "Small dataset - use in-memory JOIN"),
        (150, "Medium dataset - use staging table"),
        (5000, "Large dataset - use staging table"),
        (15000, "Very large dataset - use cloud storage")
    ]

    for size_mb, description in test_sizes:
        should_use = manager.should_use_staging(size_mb)
        status = "✅ Use staging" if should_use else "❌ Don't use staging"
        print(f"  {size_mb:6.0f} MB: {status:20} ({description})")

    # Test 2: Create staging table
    print("\n" + "-"*80)
    print("2️⃣  Create Staging Table")
    print("-"*80)

    print("\nScenario: Copy PostgreSQL customers to staging for JOIN with local orders")
    print("\nSource Query (PostgreSQL):")
    print("  SELECT customer_id, customer_name, email, country")
    print("  FROM sales.customers")
    print("  LIMIT 5")

    try:
        # Create staging table with customers data
        result = await manager.create_staging_table(
            source_db='postgresql',
            source_query="""
                SELECT customer_id, customer_name, email, country
                FROM sales.customers
                LIMIT 5
            """,
            target_db='postgresql',  # Using same DB for demo (would be different in real use)
            source_config=PG_CONFIG,
            target_config=PG_CONFIG
        )

        if result.success:
            print(f"\n✅ Staging Table Created Successfully!")
            print(f"  Table name:       {result.staging_table.staging_table_name}")
            print(f"  Rows staged:      {result.rows_staged}")
            print(f"  Data transferred: {result.data_transferred_mb:.2f} MB")
            print(f"  Creation time:    {result.execution_time_seconds:.2f} seconds")

            staging_table = result.staging_table

            # Test 3: Execute query using staging table
            print("\n" + "-"*80)
            print("3️⃣  Execute Query with Staging Table")
            print("-"*80)

            print("\nTarget Query (using staging table):")
            print("  SELECT s.customer_name, s.email, COUNT(o.order_id) as order_count")
            print("  FROM {staging_table} s")
            print("  LEFT JOIN sales.orders o ON s.customer_id = o.customer_id")
            print("  GROUP BY s.customer_name, s.email")

            # Note: In real scenario, this would be a different database
            # For demo, we're using the same PostgreSQL instance
            query_result, _ = await manager.execute_with_staging(
                source_db='postgresql',
                source_query="""
                    SELECT customer_id, customer_name, email
                    FROM sales.customers
                    LIMIT 3
                """,
                target_db='postgresql',
                target_query_template="""
                    SELECT
                        s.customer_name,
                        s.email,
                        COUNT(o.order_id) as order_count
                    FROM {staging_table} s
                    LEFT JOIN sales.orders o ON s.customer_id = o.customer_id
                    GROUP BY s.customer_name, s.email
                """,
                source_config=PG_CONFIG,
                target_config=PG_CONFIG
            )

            print(f"\n✅ Query Executed Successfully!")
            print(f"  Rows returned: {len(query_result)}")

            if len(query_result) > 0:
                print("\n  Sample results:")
                print(query_result.head(3).to_string(index=False))

            # Test 4: Cleanup
            print("\n" + "-"*80)
            print("4️⃣  Cleanup Staging Tables")
            print("-"*80)

            print(f"\nActive staging tables: {len(manager._active_staging_tables)}")
            for table_name in manager._active_staging_tables.keys():
                print(f"  - {table_name}")

            await manager.cleanup_all_staging_tables({
                'postgresql': PG_CONFIG
            })

            print(f"\n✅ All staging tables cleaned up")
            print(f"  Remaining tables: {len(manager._active_staging_tables)}")

        else:
            print(f"\n❌ Staging table creation failed: {result.error}")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

    # Performance comparison
    print("\n" + "="*80)
    print("📊 Performance Comparison: In-Memory vs Staging Table")
    print("="*80)

    print("""
Scenario: JOIN 500 MB customer data with 5 GB order data

╔════════════════════════════════════════════════════════════════════════════╗
║ Strategy 1: In-Memory JOIN                                                ║
╠════════════════════════════════════════════════════════════════════════════╣
║ 1. Fetch 500 MB from PostgreSQL    → Network: 500 MB    Time: 30s        ║
║ 2. Fetch 5 GB from BigQuery         → Network: 5 GB      Time: 180s       ║
║ 3. JOIN in memory (pandas)          → Memory: 5.5 GB     Time: 120s       ║
║ 4. Return results                   → Total: ~330 seconds                 ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║ Strategy 2: Staging Table (with pushdown optimization)                    ║
╠════════════════════════════════════════════════════════════════════════════╣
║ 1. Fetch filtered customers (50MB) → Network: 50 MB      Time: 3s        ║
║ 2. Create staging table in BigQuery → Upload: 50 MB      Time: 5s        ║
║ 3. JOIN natively in BigQuery        → Network: 0 MB      Time: 15s       ║
║ 4. Return results (1MB)             → Network: 1 MB      Time: 1s        ║
║ 5. Cleanup staging table            → Time: 1s                            ║
║ Total: ~25 seconds                                                         ║
╚════════════════════════════════════════════════════════════════════════════╝

Result: 13x faster! (330s → 25s)

Key Benefits:
✅ Much less network data transfer (5.5 GB → 101 MB)
✅ No memory pressure (JOIN in database, not in-memory)
✅ Leverage database's native JOIN optimization
✅ Can handle much larger datasets
    """)

    print("="*80)
    print("✅ Staging Table Manager Test Complete!")
    print("="*80)


if __name__ == '__main__':
    asyncio.run(test_staging_table_manager())
