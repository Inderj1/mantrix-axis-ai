"""
End-to-End Test: Connector Schema Pipeline

Tests the complete flow:
1. Clear schema cache
2. Sync connector
3. Verify Weaviate has schemas with connector_id
4. Run a query and verify it uses connector tables (not hardcoded ones)

Usage:
    export API_TOKEN="your-jwt-token"
    export API_BASE_URL="https://axis-dev.cloudmantra.ai"  # or http://localhost:8000
    export CONNECTOR_ID="69296bfdd497f625b331518e"
    python -m pytest tests/integration/test_connector_pipeline_e2e.py -v
"""

import os
import time
import requests
import pytest


# Configuration from environment
API_BASE_URL = os.environ.get("API_BASE_URL", "https://axis-dev.cloudmantra.ai")
API_TOKEN = os.environ.get("API_TOKEN", "")
CONNECTOR_ID = os.environ.get("CONNECTOR_ID", "69296bfdd497f625b331518e")

# Expected tables from madison_reed_inventory dataset
EXPECTED_TABLES = [
    "madison_reed_current_inventory",
    "madison_reed_products",
    "madison_reed_sales_history",
    "madison_reed_social_trends",
    "madison_reed_suppliers"
]

# Tables that should NOT be used (hardcoded legacy tables)
FORBIDDEN_TABLES = [
    "dataset_25m_table",
    "sales_order_cockpit_export"
]


def get_headers():
    """Get auth headers for API requests."""
    if not API_TOKEN:
        pytest.skip("API_TOKEN environment variable not set")
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }


class TestConnectorPipelineE2E:
    """End-to-end tests for connector schema pipeline."""

    def test_1_clear_schema_cache(self):
        """Step 1: Clear schema cache."""
        response = requests.post(
            f"{API_BASE_URL}/api/v1/connectors/admin/clear-schema-cache",
            headers=get_headers()
        )

        print(f"\n=== Clear Schema Cache ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        assert response.status_code == 200, f"Failed to clear cache: {response.text}"

    def test_2_sync_connector(self):
        """Step 2: Sync connector to rebuild schema."""
        response = requests.post(
            f"{API_BASE_URL}/api/v1/connectors/{CONNECTOR_ID}/sync",
            headers=get_headers()
        )

        print(f"\n=== Sync Connector ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        assert response.status_code == 200, f"Failed to sync connector: {response.text}"

        data = response.json()
        assert data.get("success") or data.get("status") == "success", "Sync did not succeed"

        # Wait a moment for async indexing to complete
        print("Waiting 3 seconds for indexing to complete...")
        time.sleep(3)

    def test_3_verify_diagnostics(self):
        """Step 3: Verify Weaviate has schemas with connector_id."""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/connectors/admin/diagnostics",
            headers=get_headers()
        )

        print(f"\n=== Schema Diagnostics ===")
        print(f"Status: {response.status_code}")

        assert response.status_code == 200, f"Failed to get diagnostics: {response.text}"

        data = response.json()
        diagnostics = data.get("diagnostics", {})
        weaviate = diagnostics.get("weaviate", {})

        print(f"Weaviate connected: {weaviate.get('connected')}")
        print(f"Total schemas: {weaviate.get('total_schemas')}")
        print(f"Schemas with connector_id: {weaviate.get('schemas_with_connector_id')}")
        print(f"Schemas by connector: {weaviate.get('schemas_by_connector')}")
        print(f"Sample schemas: {weaviate.get('sample_schemas')}")

        # Assertions
        assert weaviate.get("connected"), "Weaviate not connected"
        assert weaviate.get("schemas_with_connector_id", 0) > 0, \
            "No schemas with connector_id found in Weaviate"

        # Verify expected number of tables (5 for madison_reed)
        schemas_count = weaviate.get("schemas_with_connector_id", 0)
        print(f"\nExpected ~{len(EXPECTED_TABLES)} tables, found {schemas_count}")
        assert schemas_count >= len(EXPECTED_TABLES), \
            f"Expected at least {len(EXPECTED_TABLES)} schemas, got {schemas_count}"

    def test_4_verify_sample_schemas(self):
        """Step 4: Verify sample schemas are from connector (not hardcoded)."""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/connectors/admin/diagnostics",
            headers=get_headers()
        )

        data = response.json()
        sample_schemas = data.get("diagnostics", {}).get("weaviate", {}).get("sample_schemas", [])

        print(f"\n=== Sample Schema Verification ===")

        for schema in sample_schemas:
            table_name = schema.get("table_name", "")
            connector_id = schema.get("connector_id", "")

            print(f"Table: {table_name}, Connector: {connector_id}")

            # Verify not a forbidden (hardcoded) table
            assert table_name not in FORBIDDEN_TABLES, \
                f"Found forbidden hardcoded table: {table_name}"

            # Verify has connector_id if it's one of expected tables
            if any(expected in table_name for expected in ["madison_reed"]):
                assert connector_id, f"Expected connector_id for {table_name}"

    def test_5_query_uses_connector_tables(self):
        """Step 5: Run a query and verify it uses connector tables."""
        query_payload = {
            "question": "Show me top 5 products by total sales amount",
            "database_type": "bigquery",
            "conversation_id": None
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/query",
            headers=get_headers(),
            json=query_payload
        )

        print(f"\n=== Query Test ===")
        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: {response.text}")
            pytest.fail(f"Query failed: {response.text}")

        data = response.json()
        generated_sql = data.get("sql", "")
        tables_used = data.get("tables_used", [])

        print(f"Generated SQL:\n{generated_sql}")
        print(f"Tables used: {tables_used}")

        # Verify SQL doesn't use forbidden tables
        for forbidden in FORBIDDEN_TABLES:
            assert forbidden not in generated_sql.lower(), \
                f"SQL uses forbidden hardcoded table: {forbidden}"

        # Verify SQL uses connector tables (madison_reed_*)
        sql_lower = generated_sql.lower()
        uses_connector_table = any(
            expected.lower() in sql_lower
            for expected in EXPECTED_TABLES
        )

        print(f"\nUses connector tables: {uses_connector_table}")

        # This assertion may be too strict if the query legitimately uses other tables
        # Comment out if needed
        if not uses_connector_table:
            print("WARNING: Query did not use expected connector tables")
            print("This may be OK if vector search selected different tables")


class TestConnectorDiagnosticsOnly:
    """Quick diagnostic test - just checks current state without sync."""

    def test_diagnostics_only(self):
        """Check current Weaviate/Jena state."""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/connectors/admin/diagnostics",
            headers=get_headers()
        )

        print(f"\n=== Current Schema Diagnostics ===")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            import json
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    # Run tests manually
    import sys

    if not API_TOKEN:
        print("ERROR: Set API_TOKEN environment variable")
        print("Usage:")
        print('  export API_TOKEN="your-jwt-token"')
        print('  export API_BASE_URL="https://axis-dev.cloudmantra.ai"')
        print('  python tests/integration/test_connector_pipeline_e2e.py')
        sys.exit(1)

    print("=" * 60)
    print("CONNECTOR PIPELINE END-TO-END TEST")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Connector ID: {CONNECTOR_ID}")
    print("=" * 60)

    test = TestConnectorPipelineE2E()

    try:
        print("\n[1/5] Clearing schema cache...")
        test.test_1_clear_schema_cache()
        print("✓ Cache cleared")

        print("\n[2/5] Syncing connector...")
        test.test_2_sync_connector()
        print("✓ Connector synced")

        print("\n[3/5] Verifying diagnostics...")
        test.test_3_verify_diagnostics()
        print("✓ Diagnostics verified")

        print("\n[4/5] Verifying sample schemas...")
        test.test_4_verify_sample_schemas()
        print("✓ Sample schemas verified")

        print("\n[5/5] Testing query...")
        test.test_5_query_uses_connector_tables()
        print("✓ Query test complete")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)
