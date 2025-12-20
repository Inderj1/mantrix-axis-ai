#!/usr/bin/env python3
"""
Test Federation via Deployed API

Tests the federated query orchestrator through the deployed API endpoints.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/test_federation_api.py
"""

import requests
import json
import sys

# API Configuration
API_BASE = "https://axis-dev.cloudmantra.ai/api/v1"
TOKEN = "eyJraWQiOiI0V1ZmUjlVQkU1MHdBOVlaejM0N0xEZU1OZU92ZURPUStSM2ZBRUJIK0pvPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJlNGM4YjQ0OC0zMDkxLTcwN2QtNzYxOS03YzNmNzBjNDMzYzgiLCJjb2duaXRvOmdyb3VwcyI6WyJBZG1pbnMiXSwiZW1haWxfdmVyaWZpZWQiOnRydWUsImN1c3RvbTpvcmdhbml6YXRpb25faWQiOiJEZW1vIiwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tXC91cy1lYXN0LTFfZlRJeDVmYVJaIiwiY29nbml0bzp1c2VybmFtZSI6ImU0YzhiNDQ4LTMwOTEtNzA3ZC03NjE5LTdjM2Y3MGM0MzNjOCIsImdpdmVuX25hbWUiOiJKYXkiLCJvcmlnaW5fanRpIjoiZmQ5YjIwM2UtMmQ3Yy00MGZmLTg3ZTItZjBkNTJhN2NlZDVmIiwiYXVkIjoiNGhwdDhvazJ0ZjMzbHNlbTg3OHRjYWFvZGQiLCJldmVudF9pZCI6IjI1NzZmNTkxLTM0ZWUtNDQ1Mi1hNDVlLTRkYjNlZjkzYzk2NSIsInRva2VuX3VzZSI6ImlkIiwiYXV0aF90aW1lIjoxNzY1Mjg4NDQwLCJleHAiOjE3NjU2MzQ5OTUsImlhdCI6MTc2NTYzMTM5NSwiZmFtaWx5X25hbWUiOiJWZWVyIiwianRpIjoiZGUyMzU0ZjMtY2U0ZS00ZjQ2LWJlNDYtNTY0NmIzN2MxNDcyIiwiZW1haWwiOiJqYXkudmVlcjFAcHJvdG9ubWFpbC5jb20ifQ.SEbruvS2T7mU4-MUljSfV9D6GdhQp0s21FNIVipdex5PHU_5bs4UEnIF0IKNgmjwaNwP_v5ZLsLcydNYjB7iJ5n-buMS43OBMtXfhVy0vhjqrZh6yM_OHvlg8I3qOzE73Er3kbSA_t7ZeNrZQe-Rkl_o1bhV_5v1vlPx5td9p8Ps6H3mp8E_7C5LP-IqhZTyXw4ZI-HBlwMApLGtI45o5pbI71vo5SburhKxzbeLN1DankfD3jwe1sFYNq0ej-V7rSRWLW5g5_keURxAnsHDMv5N_ybcdvptaEtZWfQbms0Mnt70TMNeaDI1HV-1aeFAW15fAUhy3OXp9cP_omapJw"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def api_get(endpoint):
    """Make GET request to API."""
    resp = requests.get(f"{API_BASE}{endpoint}", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else {"error": resp.text, "status": resp.status_code}


def api_post(endpoint, data):
    """Make POST request to API."""
    resp = requests.post(f"{API_BASE}{endpoint}", headers=HEADERS, json=data)
    return resp.json() if resp.status_code == 200 else {"error": resp.text, "status": resp.status_code}


def test_list_connectors():
    """List all configured connectors."""
    print("\n" + "="*60)
    print("TEST 1: List Configured Connectors")
    print("="*60)

    result = api_get("/connectors")

    if "error" in result:
        print(f"Error: {result}")
        return False, {}

    connectors = {}
    print(f"\nFound {len(result)} connector(s):")

    for conn in result:
        name = conn.get('name', 'Unknown')
        conn_type = conn.get('connector_type', 'Unknown')
        status = conn.get('status', 'Unknown')
        enabled = conn.get('enabled_for_chat', False)

        print(f"\n  {name}")
        print(f"    Type: {conn_type}")
        print(f"    Status: {status}")
        print(f"    Enabled for chat: {enabled}")

        if status == 'connected':
            connectors[conn_type] = conn

    return True, connectors


def test_bigquery_query():
    """Test a simple BigQuery query via NLP endpoint."""
    print("\n" + "="*60)
    print("TEST 2: BigQuery Query via NLP")
    print("="*60)

    # Use the query endpoint with a simple question
    data = {
        "query": "Show me the top 5 customers by monetary value from customer_master_analysis",
        "database_type": "bigquery"
    }

    print(f"\nQuery: {data['query']}")
    print("Sending to /query endpoint...")

    result = api_post("/query", data)

    if "error" in result and result.get("status"):
        print(f"Error: {result}")
        return False

    print(f"\nStatus: {result.get('status', 'unknown')}")
    print(f"SQL: {result.get('sql', 'N/A')[:200]}...")

    if result.get('execution'):
        exec_result = result['execution']
        print(f"Row count: {exec_result.get('row_count', 0)}")
        if exec_result.get('results'):
            print(f"Sample: {exec_result['results'][0]}")

    return result.get('status') == 'complete'


def test_snowflake_query():
    """Test a simple Snowflake query via NLP endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Snowflake Query via NLP")
    print("="*60)

    # First, let's try to see what tables are in Snowflake
    data = {
        "query": "List all tables available in Snowflake",
        "database_type": "snowflake"
    }

    print(f"\nQuery: {data['query']}")
    print("Sending to /query endpoint...")

    result = api_post("/query", data)

    if "error" in result and result.get("status"):
        print(f"Error: {result}")
        return False

    print(f"\nStatus: {result.get('status', 'unknown')}")
    print(f"SQL: {result.get('sql', 'N/A')[:200]}...")

    if result.get('execution'):
        exec_result = result['execution']
        print(f"Row count: {exec_result.get('row_count', 0)}")
        if exec_result.get('results'):
            for row in exec_result['results'][:5]:
                print(f"  - {row}")

    return result.get('status') == 'complete'


def test_cross_db_nlp_query():
    """Test a cross-database query via NLP."""
    print("\n" + "="*60)
    print("TEST 4: Cross-Database Query via NLP")
    print("="*60)

    # Ask a question that might require data from both sources
    data = {
        "query": "Compare customer segments from BigQuery with order data from Snowflake",
        "database_type": "bigquery"  # Primary database
    }

    print(f"\nQuery: {data['query']}")
    print("Sending to /query endpoint...")

    result = api_post("/query", data)

    if "error" in result and result.get("status"):
        print(f"Error: {result}")
        return False

    print(f"\nStatus: {result.get('status', 'unknown')}")
    print(f"SQL: {result.get('sql', 'N/A')[:300]}...")

    if result.get('requires_async'):
        print("Query requires async execution (large dataset)")

    if result.get('execution'):
        exec_result = result['execution']
        print(f"Row count: {exec_result.get('row_count', 0)}")

    return True


def test_execute_raw_sql():
    """Test executing raw SQL on specific database."""
    print("\n" + "="*60)
    print("TEST 5: Execute Raw SQL")
    print("="*60)

    # Test BigQuery
    print("\n5a. BigQuery raw SQL:")
    data = {
        "sql": "SELECT Customer, RFM_Segment, Monetary FROM customer_master_analysis LIMIT 5",
        "database_type": "bigquery"
    }

    result = api_post("/execute-sql", data)

    if "error" in result and result.get("status"):
        print(f"Error: {result}")
    else:
        print(f"Status: {result.get('status', 'unknown')}")
        if result.get('results'):
            print(f"Results: {len(result['results'])} rows")
            for row in result['results'][:3]:
                print(f"  {row}")

    # Test Snowflake
    print("\n5b. Snowflake raw SQL:")
    data = {
        "sql": "SELECT * FROM INFORMATION_SCHEMA.TABLES LIMIT 5",
        "database_type": "snowflake"
    }

    result = api_post("/execute-sql", data)

    if "error" in result and result.get("status"):
        print(f"Error: {result}")
    else:
        print(f"Status: {result.get('status', 'unknown')}")
        if result.get('results'):
            print(f"Results: {len(result['results'])} rows")

    return True


def test_diagnostics():
    """Check admin diagnostics for federation status."""
    print("\n" + "="*60)
    print("TEST 6: Admin Diagnostics")
    print("="*60)

    result = api_get("/connectors/admin/diagnostics")

    if "error" in result:
        print(f"Error: {result}")
        return False

    print(f"\nDiagnostics:")
    print(json.dumps(result, indent=2, default=str)[:1000])

    return True


def main():
    """Run all API tests."""
    print("\n" + "="*60)
    print("FEDERATION API TESTS")
    print(f"Target: {API_BASE}")
    print("="*60)

    results = []

    # Test 1: List connectors
    success, connectors = test_list_connectors()
    results.append(("List Connectors", success))

    # Test 2: BigQuery query
    if 'bigquery' in connectors:
        results.append(("BigQuery Query", test_bigquery_query()))
    else:
        print("\nSkipping BigQuery tests - no connector configured")
        results.append(("BigQuery Query", None))

    # Test 3: Snowflake query
    if 'snowflake' in connectors:
        results.append(("Snowflake Query", test_snowflake_query()))
    else:
        print("\nSkipping Snowflake tests - no connector configured")
        results.append(("Snowflake Query", None))

    # Test 4: Cross-DB query
    if 'bigquery' in connectors and 'snowflake' in connectors:
        results.append(("Cross-DB Query", test_cross_db_nlp_query()))
    else:
        print("\nSkipping cross-DB tests - need both connectors")
        results.append(("Cross-DB Query", None))

    # Test 5: Raw SQL
    results.append(("Raw SQL Execute", test_execute_raw_sql()))

    # Test 6: Diagnostics
    results.append(("Diagnostics", test_diagnostics()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    skipped = 0
    for name, success in results:
        if success is None:
            status = "SKIP"
            skipped += 1
        elif success:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
        print(f"  {name}: {status}")

    total = len(results) - skipped
    print(f"\n{passed}/{total} tests passed ({skipped} skipped)")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
