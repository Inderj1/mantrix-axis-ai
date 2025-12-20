#!/usr/bin/env python3
"""
Live Federation Test Script

Tests the FederatedQueryOrchestrator with real database connections.
Requires BigQuery credentials to be configured.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/test_federation_live.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.core.federated_query_orchestrator import (
    FederatedQueryOrchestrator,
    FederationConfig,
    FederationStrategy,
)
from src.db.connectors.bigquery_connector import BigQueryConnector


def test_single_source_bigquery():
    """Test single-source query against BigQuery."""
    print("\n" + "="*60)
    print("TEST 1: Single-Source BigQuery Query")
    print("="*60)

    # Connect to BigQuery
    connector = BigQueryConnector(
        project_id="arizona-poc",
        dataset_id="copa_export_copa_data_000000000000",
        auto_connect=True
    )

    # Create orchestrator with single connector
    orchestrator = FederatedQueryOrchestrator(
        connectors={"bigquery": connector}
    )

    # Test query - use actual table name (orchestrator adds qualifications)
    query = "SELECT * FROM customer_master_analysis LIMIT 10"

    print(f"\nQuery: {query}")
    print("\nExecuting...")

    result = asyncio.run(orchestrator.execute_federated_query(query))

    print(f"\nStatus: {result.status}")
    print(f"Strategy: {result.strategy.value}")
    print(f"Row count: {result.row_count}")
    print(f"Sources queried: {result.sources_queried}")

    if result.rows:
        print(f"\nSample row keys: {list(result.rows[0].keys())[:5]}...")

    return result.status == "complete"


def test_duckdb_local_join():
    """Test DuckDB local JOIN with mock data simulating cross-DB."""
    print("\n" + "="*60)
    print("TEST 2: DuckDB Local JOIN (Mock Cross-DB)")
    print("="*60)

    # Create mock connectors that return sample data
    class MockConnector:
        def __init__(self, data):
            self.data = data

        def execute_query(self, query, **kwargs):
            return {"rows": self.data, "row_count": len(self.data)}

    # Mock BigQuery customer data
    bq_data = [
        {"customer_id": "001", "name": "Acme Corp", "segment": "Champions"},
        {"customer_id": "002", "name": "Beta Inc", "segment": "Loyal"},
        {"customer_id": "003", "name": "Gamma LLC", "segment": "At Risk"},
    ]

    # Mock Snowflake order data
    sf_data = [
        {"order_id": "ORD001", "customer_id": "001", "amount": 5000.00},
        {"order_id": "ORD002", "customer_id": "001", "amount": 3000.00},
        {"order_id": "ORD003", "customer_id": "002", "amount": 2500.00},
    ]

    orchestrator = FederatedQueryOrchestrator(
        connectors={
            "bigquery": MockConnector(bq_data),
            "snowflake": MockConnector(sf_data),
        }
    )

    # Cross-database query
    query = """
    SELECT c.name, c.segment, SUM(o.amount) as total
    FROM bigquery.customers c
    JOIN snowflake.orders o ON c.customer_id = o.customer_id
    GROUP BY c.name, c.segment
    """

    print(f"\nQuery: {query.strip()}")
    print("\nExecuting...")

    result = asyncio.run(orchestrator.execute_federated_query(query))

    print(f"\nStatus: {result.status}")
    print(f"Strategy: {result.strategy.value}")
    print(f"Row count: {result.row_count}")
    print(f"Sources queried: {result.sources_queried}")

    if result.rows:
        print(f"\nResults:")
        for row in result.rows[:5]:
            print(f"  {row}")

    return result.status == "complete"


def test_strategy_selection():
    """Test that correct strategies are selected."""
    print("\n" + "="*60)
    print("TEST 3: Strategy Selection")
    print("="*60)

    class MockConnector:
        def execute_query(self, query, **kwargs):
            return {"rows": [], "row_count": 0}

    # Test 1: Single source should use SINGLE_SOURCE
    orchestrator = FederatedQueryOrchestrator(
        connectors={"bigquery": MockConnector()}
    )

    query = "SELECT * FROM bigquery.customers"
    plan = orchestrator._parse_query(query)
    strategy = orchestrator._select_strategy(plan, orchestrator.default_config)

    print(f"\nSingle-source query: {strategy.value}")
    assert strategy == FederationStrategy.SINGLE_SOURCE, "Expected SINGLE_SOURCE"

    # Test 2: Cross-DB with small rows should use DUCKDB_LOCAL
    orchestrator2 = FederatedQueryOrchestrator(
        connectors={
            "bigquery": MockConnector(),
            "snowflake": MockConnector(),
        }
    )

    query2 = "SELECT * FROM bigquery.a JOIN snowflake.b ON a.id = b.id"
    plan2 = orchestrator2._parse_query(query2)
    plan2.estimated_rows = {"bigquery": 1000, "snowflake": 500}
    strategy2 = orchestrator2._select_strategy(plan2, orchestrator2.default_config)

    print(f"Cross-DB (small): {strategy2.value}")
    assert strategy2 == FederationStrategy.DUCKDB_LOCAL, "Expected DUCKDB_LOCAL"

    # Test 3: Cross-DB with customer federation DB should use S3_CUSTOMER_DB
    config_with_federation = FederationConfig(
        federation_db="snowflake",
        federation_connector=MockConnector(),
        s3_bucket="customer-bucket"
    )
    strategy3 = orchestrator2._select_strategy(plan2, config_with_federation)

    print(f"Cross-DB (customer DB): {strategy3.value}")
    assert strategy3 == FederationStrategy.S3_CUSTOMER_DB, "Expected S3_CUSTOMER_DB"

    print("\nAll strategy selection tests passed!")
    return True


def test_schema_inference():
    """Test schema inference from sample data."""
    print("\n" + "="*60)
    print("TEST 4: Schema Inference")
    print("="*60)

    from datetime import datetime

    orchestrator = FederatedQueryOrchestrator(connectors={})

    sample_row = {
        "id": 123,
        "name": "Test",
        "price": 99.99,
        "active": True,
        "created_at": datetime.now(),
    }

    schema = orchestrator._infer_schema(sample_row)

    print("\nInferred schema:")
    for col, dtype in schema.items():
        print(f"  {col}: {dtype}")

    # Verify type conversions
    print("\nSnowflake type conversions:")
    for col, dtype in schema.items():
        sf_type = orchestrator._to_snowflake_type(dtype)
        print(f"  {col}: {dtype} -> {sf_type}")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("FEDERATION LIVE TESTS")
    print("="*60)

    results = []

    # Test 1: Strategy selection (no real DB needed)
    try:
        results.append(("Strategy Selection", test_strategy_selection()))
    except Exception as e:
        print(f"\nERROR: {e}")
        results.append(("Strategy Selection", False))

    # Test 2: Schema inference (no real DB needed)
    try:
        results.append(("Schema Inference", test_schema_inference()))
    except Exception as e:
        print(f"\nERROR: {e}")
        results.append(("Schema Inference", False))

    # Test 3: DuckDB local JOIN (mock data)
    try:
        results.append(("DuckDB Local JOIN", test_duckdb_local_join()))
    except Exception as e:
        print(f"\nERROR: {e}")
        results.append(("DuckDB Local JOIN", False))

    # Test 4: Real BigQuery (requires credentials)
    try:
        results.append(("BigQuery Single-Source", test_single_source_bigquery()))
    except Exception as e:
        print(f"\nERROR (BigQuery may not be configured): {e}")
        results.append(("BigQuery Single-Source", False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {name}: {status}")
        if success:
            passed += 1

    print(f"\n{passed}/{len(results)} tests passed")

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
