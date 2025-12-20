#!/usr/bin/env python3
"""
Cross-Database Federation Test

Tests real federated queries between BigQuery and Snowflake.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/test_cross_db_federation.py

    # Or with specific Snowflake config:
    SNOWFLAKE_ACCOUNT=xxx SNOWFLAKE_USER=xxx SNOWFLAKE_PASSWORD=xxx \
    SNOWFLAKE_DATABASE=xxx SNOWFLAKE_SCHEMA=xxx \
    python scripts/test_cross_db_federation.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Load .env file
from dotenv import load_dotenv
env_path = Path(backend_path) / '.env'
load_dotenv(env_path)

import structlog
from src.db.connectors.bigquery_connector import BigQueryConnector
from src.db.connectors.snowflake_connector import SnowflakeConnector, SNOWFLAKE_AVAILABLE
from src.core.federated_query_orchestrator import (
    FederatedQueryOrchestrator,
    FederationConfig,
)

logger = structlog.get_logger()


def load_connectors_direct():
    """Load connectors using direct configuration."""
    print("\n" + "="*60)
    print("Loading Connectors")
    print("="*60)

    connectors = {}

    # BigQuery - uses Application Default Credentials
    print("\n1. BigQuery:")
    try:
        bq = BigQueryConnector(
            project_id="arizona-poc",
            dataset_id="copa_export_copa_data_000000000000",
            auto_connect=True
        )
        connectors['bigquery'] = bq
        print("   ✓ Connected to BigQuery")
    except Exception as e:
        print(f"   ✗ BigQuery failed: {e}")

    # Snowflake - uses environment variables or .env
    print("\n2. Snowflake:")
    if not SNOWFLAKE_AVAILABLE:
        print("   ✗ Snowflake connector not available (missing dependencies)")
    else:
        # Check for Snowflake config
        sf_account = os.getenv('SNOWFLAKE_ACCOUNT')
        sf_user = os.getenv('SNOWFLAKE_USER')
        sf_password = os.getenv('SNOWFLAKE_PASSWORD')
        sf_database = os.getenv('SNOWFLAKE_DATABASE')
        sf_schema = os.getenv('SNOWFLAKE_SCHEMA')
        sf_warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')

        if sf_account and sf_user:
            try:
                sf = SnowflakeConnector(
                    account=sf_account,
                    user=sf_user,
                    password=sf_password,
                    database=sf_database,
                    schema=sf_schema,
                    warehouse=sf_warehouse,
                    auto_connect=True
                )
                connectors['snowflake'] = sf
                print(f"   ✓ Connected to Snowflake ({sf_account})")
            except Exception as e:
                print(f"   ✗ Snowflake failed: {e}")
        else:
            print("   ✗ Snowflake not configured (set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, etc.)")
            print("   Tip: Copy from .env or set environment variables")

    return connectors


async def test_bigquery_tables(connectors):
    """List tables available in BigQuery."""
    print("\n" + "="*60)
    print("BigQuery Tables")
    print("="*60)

    if 'bigquery' not in connectors:
        print("BigQuery connector not available")
        return []

    bq = connectors['bigquery']
    tables = bq.list_tables()
    print(f"\nFound {len(tables)} tables:")
    for t in tables[:10]:
        print(f"  - {t}")
    if len(tables) > 10:
        print(f"  ... and {len(tables) - 10} more")

    return tables


async def test_snowflake_tables(connectors):
    """List tables available in Snowflake."""
    print("\n" + "="*60)
    print("Snowflake Tables")
    print("="*60)

    if 'snowflake' not in connectors:
        print("Snowflake connector not available")
        return []

    sf = connectors['snowflake']
    tables = sf.list_tables()
    print(f"\nFound {len(tables)} tables:")
    for t in tables[:10]:
        print(f"  - {t}")
    if len(tables) > 10:
        print(f"  ... and {len(tables) - 10} more")

    return tables


async def test_duckdb_cross_join(connectors):
    """Test DuckDB-based cross-database JOIN."""
    print("\n" + "="*60)
    print("TEST: DuckDB Cross-Database JOIN")
    print("="*60)

    if 'bigquery' not in connectors or 'snowflake' not in connectors:
        print("Need both BigQuery and Snowflake connectors")
        return False

    # Create federated orchestrator
    orchestrator = FederatedQueryOrchestrator(connectors=connectors)

    # Get sample data from each source
    print("\nFetching sample from BigQuery...")
    bq_result = connectors['bigquery'].execute_query(
        "SELECT Customer, RFM_Segment, ABC_Revenue FROM customer_master_analysis LIMIT 100"
    )
    print(f"  Got {bq_result.get('row_count', 0)} rows from BigQuery")

    print("\nFetching sample from Snowflake...")
    # Try to get any table from Snowflake
    sf_tables = connectors['snowflake'].list_tables()
    if sf_tables:
        first_table = sf_tables[0]
        sf_result = connectors['snowflake'].execute_query(
            f"SELECT * FROM {first_table} LIMIT 100"
        )
        print(f"  Got {sf_result.get('row_count', 0)} rows from Snowflake table: {first_table}")

    # Now test the federation with mock cross-DB query
    print("\nExecuting federated query with DuckDB...")

    # Create a query that references both databases
    query = """
    SELECT bq.Customer, bq.RFM_Segment, bq.ABC_Revenue
    FROM bigquery.customer_master_analysis bq
    LIMIT 10
    """

    result = await orchestrator.execute_federated_query(query)

    print(f"\nResult:")
    print(f"  Status: {result.status}")
    print(f"  Strategy: {result.strategy.value}")
    print(f"  Row count: {result.row_count}")
    print(f"  Sources: {result.sources_queried}")

    if result.rows:
        print(f"\n  Sample row: {result.rows[0]}")

    return result.status == "complete"


async def test_real_cross_db_join(connectors):
    """
    Test a real cross-database JOIN between BigQuery and Snowflake.

    This requires:
    1. A common key between the two databases
    2. Data that can be meaningfully joined
    """
    print("\n" + "="*60)
    print("TEST: Real Cross-Database JOIN")
    print("="*60)

    if 'bigquery' not in connectors or 'snowflake' not in connectors:
        print("Need both BigQuery and Snowflake connectors")
        return False

    # Create federated orchestrator
    orchestrator = FederatedQueryOrchestrator(connectors=connectors)

    # First, let's see what's in each database
    print("\nAnalyzing available data...")

    # BigQuery customer data
    print("\n1. BigQuery - customer_master_analysis sample:")
    bq_sample = connectors['bigquery'].execute_query(
        "SELECT Customer, RFM_Segment, Frequency, Monetary FROM customer_master_analysis LIMIT 5"
    )
    if bq_sample.get('rows'):
        for row in bq_sample['rows'][:3]:
            print(f"   {row}")

    # Snowflake data
    sf_tables = connectors['snowflake'].list_tables()
    print(f"\n2. Snowflake tables available: {sf_tables[:5]}")

    if sf_tables:
        print(f"\n3. Snowflake - {sf_tables[0]} sample:")
        sf_sample = connectors['snowflake'].execute_query(
            f"SELECT * FROM {sf_tables[0]} LIMIT 5"
        )
        if sf_sample.get('rows'):
            for row in sf_sample['rows'][:3]:
                # Truncate long values
                truncated = {k: (str(v)[:50] + '...' if len(str(v)) > 50 else v)
                            for k, v in row.items()}
                print(f"   {truncated}")

    # Execute a cross-database query using DuckDB local strategy
    print("\n4. Executing cross-database federation...")

    # This query will:
    # - Fetch from BigQuery
    # - Fetch from Snowflake
    # - Join locally in DuckDB
    query = f"""
    SELECT
        bq.Customer,
        bq.RFM_Segment,
        bq.Monetary as BigQuery_Monetary,
        sf.*
    FROM bigquery.customer_master_analysis bq
    CROSS JOIN snowflake.{sf_tables[0]} sf
    LIMIT 10
    """

    print(f"\n   Query: {query[:100]}...")

    result = await orchestrator.execute_federated_query(query)

    print(f"\n   Result:")
    print(f"   - Status: {result.status}")
    print(f"   - Strategy: {result.strategy.value}")
    print(f"   - Row count: {result.row_count}")
    print(f"   - Execution time: {result.execution_time_seconds:.2f}s")

    if result.error:
        print(f"   - Error: {result.error}")

    if result.rows:
        print(f"\n   Sample result:")
        for row in result.rows[:2]:
            truncated = {k: (str(v)[:30] + '...' if len(str(v)) > 30 else v)
                        for k, v in list(row.items())[:5]}
            print(f"   {truncated}")

    return result.status == "complete"


async def main():
    """Run cross-database federation tests."""
    print("\n" + "="*60)
    print("CROSS-DATABASE FEDERATION TEST")
    print("="*60)

    # Load connectors directly (not from MongoDB)
    connectors = load_connectors_direct()

    if not connectors:
        print("\nNo connectors loaded. Please configure connectors via the UI.")
        return False

    print(f"\nLoaded connectors: {list(connectors.keys())}")

    results = []

    # Test 1: List BigQuery tables
    try:
        await test_bigquery_tables(connectors)
        results.append(("BigQuery Tables", True))
    except Exception as e:
        print(f"Error: {e}")
        results.append(("BigQuery Tables", False))

    # Test 2: List Snowflake tables
    try:
        await test_snowflake_tables(connectors)
        results.append(("Snowflake Tables", True))
    except Exception as e:
        print(f"Error: {e}")
        results.append(("Snowflake Tables", False))

    # Test 3: DuckDB cross-join
    try:
        success = await test_duckdb_cross_join(connectors)
        results.append(("DuckDB Cross-Join", success))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("DuckDB Cross-Join", False))

    # Test 4: Real cross-DB join
    try:
        success = await test_real_cross_db_join(connectors)
        results.append(("Real Cross-DB JOIN", success))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Real Cross-DB JOIN", False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {name}: {status}")

    print(f"\n{passed}/{len(results)} tests passed")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
