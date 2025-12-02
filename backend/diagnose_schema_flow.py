#!/usr/bin/env python3
"""
Schema Flow Diagnostic Script

Checks each step of the schema-to-LLM flow and identifies where it breaks.
Run with: python diagnose_schema_flow.py --token "Bearer eyJ..."

This script tests:
1. API Health Check
2. Connector Status
3. Weaviate Connection
4. Weaviate Schema Search
5. Jena RDF Store
6. Query Generation
"""

import argparse
import json
import requests
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://axis-dev.cloudmantra.ai"
CONNECTOR_ID = "69296bfdd497f625b331518e"  # Arizona OAuth connector


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_step(step_num: int, title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== Step {step_num}: {title} ==={Colors.RESET}")


def print_ok(message: str):
    print(f"  {Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    print(f"  {Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    print(f"  {Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str):
    print(f"  {Colors.BLUE}ℹ {message}{Colors.RESET}")


def step1_health_check(headers: dict) -> bool:
    """Check API connectivity"""
    print_step(1, "API Health Check")

    try:
        # Try the query endpoint with a simple OPTIONS or HEAD
        response = requests.get(f"{BASE_URL}/api/v1/connectors", headers=headers, timeout=10)

        if response.status_code == 200:
            print_ok(f"API responding (status: {response.status_code})")
            return True
        else:
            print_error(f"API returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Failed to connect: {e}")
        return False


def step2_connector_status(headers: dict) -> dict:
    """Check connector exists and has schema"""
    print_step(2, "Connector Status")

    try:
        response = requests.get(f"{BASE_URL}/api/v1/connectors", headers=headers, timeout=10)
        data = response.json()

        connectors = data.get("connectors", [])
        print_info(f"Found {len(connectors)} connectors")

        # Find the Arizona connector
        arizona_connector = None
        for conn in connectors:
            if conn.get("id") == CONNECTOR_ID or "arizona" in conn.get("name", "").lower():
                arizona_connector = conn
                break

        if arizona_connector:
            print_ok(f"Found connector: {arizona_connector.get('name')}")
            print_info(f"  ID: {arizona_connector.get('id')}")
            print_info(f"  Type: {arizona_connector.get('connector_type')}")
            print_info(f"  Project: {arizona_connector.get('config', {}).get('project_id')}")
            print_info(f"  Dataset: {arizona_connector.get('config', {}).get('dataset_id')}")
            print_info(f"  Auth Method: {arizona_connector.get('config', {}).get('auth_method')}")
            print_info(f"  Sync Status: {arizona_connector.get('sync_status')}")

            table_count = arizona_connector.get('metadata', {}).get('table_count', 0)
            if table_count > 0:
                print_ok(f"  Tables extracted: {table_count}")
            else:
                print_warning(f"  Tables extracted: {table_count} (no tables!)")

            return arizona_connector
        else:
            print_error("Arizona connector not found!")
            for conn in connectors:
                print_info(f"  Available: {conn.get('name')} ({conn.get('id')})")
            return None

    except Exception as e:
        print_error(f"Failed to get connectors: {e}")
        return None


def step3_weaviate_connection(headers: dict) -> bool:
    """Check Weaviate connectivity via a debug endpoint"""
    print_step(3, "Weaviate Connection")

    # We can't directly check Weaviate from here, but we can infer from logs
    # Let's try to trigger a query and see if vector search works

    try:
        # Make a query request that would use vector search
        test_payload = {
            "query": "What tables are available?",
            "database_type": "bigquery",
            "debug": True
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/query",
            headers=headers,
            json=test_payload,
            timeout=60
        )

        data = response.json()

        # Check if vector search was used or fell back
        sql = data.get("sql", "")

        if "cloudmantra-genai" in sql:
            print_warning("Query used fallback (cloudmantra-genai in SQL)")
            print_warning("This suggests Weaviate vector search failed")
            return False
        elif "arizona-poc" in sql:
            print_ok("Query used correct schema (arizona-poc)")
            return True
        else:
            print_info(f"SQL generated: {sql[:100]}...")
            return False

    except Exception as e:
        print_error(f"Query failed: {e}")
        return False


def step4_schema_search(headers: dict) -> list:
    """Query what schemas are being used"""
    print_step(4, "Schema Search Analysis")

    try:
        test_payload = {
            "query": "Show me all tables",
            "database_type": "bigquery"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/query",
            headers=headers,
            json=test_payload,
            timeout=60
        )

        data = response.json()

        # Analyze the SQL
        sql = data.get("sql", "")
        tables_used = data.get("tables_used", [])

        print_info(f"Tables used: {tables_used}")

        # Extract project.dataset from SQL
        import re
        pattern = r'`([^`]+)\.([^`]+)\.([^`]+)`'
        matches = re.findall(pattern, sql)

        if matches:
            print_info("Project/Dataset references in SQL:")
            for project, dataset, table in matches:
                if project == "arizona-poc":
                    print_ok(f"  {project}.{dataset}.{table}")
                elif project == "cloudmantra-genai":
                    print_error(f"  {project}.{dataset}.{table} (WRONG PROJECT!)")
                else:
                    print_info(f"  {project}.{dataset}.{table}")
        else:
            print_warning("Could not parse project.dataset from SQL")
            print_info(f"SQL: {sql}")

        return matches

    except Exception as e:
        print_error(f"Schema search failed: {e}")
        return []


def step5_jena_store(headers: dict) -> bool:
    """Check if Jena RDF store has the schema"""
    print_step(5, "Jena RDF Store")

    # We can't directly check Jena from here, but we can note that it should be checked
    print_info("Jena store is an internal service - cannot check remotely")
    print_info("The sync endpoint reported: jena_cleared: true")
    print_info("RDF file: /app/table_metadata_kg.ttl (on ECS container)")
    print_warning("Need to check ECS container for Jena file contents")

    return True  # We know Jena was cleared from earlier logs


def step6_query_generation(headers: dict, connector: dict) -> dict:
    """Test query generation with specific connector context"""
    print_step(6, "Query Generation Analysis")

    if not connector:
        print_error("No connector info available for analysis")
        return {}

    try:
        # Test a specific query
        test_payload = {
            "query": "Show me all accounts",
            "database_type": "bigquery"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/query",
            headers=headers,
            json=test_payload,
            timeout=60
        )

        data = response.json()

        sql = data.get("sql", "")
        validation = data.get("validation", {})
        execution = data.get("execution", {})

        print_info(f"Query: 'Show me all accounts'")
        print_info(f"Generated SQL:\n    {sql}")

        # Check validation
        if validation.get("valid"):
            print_ok("SQL validation passed")
        else:
            print_error(f"SQL validation failed: {validation.get('error', 'Unknown')[:100]}")

        # Check execution
        if execution.get("error"):
            print_error(f"Execution error: {execution.get('error', '')[:100]}")
        elif execution.get("results"):
            print_ok("Query executed successfully")

        # Check what project was used
        if "cloudmantra-genai" in sql:
            print_error("PROBLEM: SQL references cloudmantra-genai (wrong project!)")
            print_error("Expected: arizona-poc.madison_reed_inventory")
        elif "arizona-poc" in sql:
            print_ok("SQL correctly references arizona-poc")

        return data

    except Exception as e:
        print_error(f"Query generation failed: {e}")
        return {}


def print_summary(results: dict):
    """Print diagnosis summary"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("DIAGNOSIS SUMMARY")
    print(f"{'='*60}{Colors.RESET}")

    issues = []

    if not results.get("api_ok"):
        issues.append("API is not responding")

    if not results.get("connector"):
        issues.append("Arizona connector not found")
    elif results.get("connector", {}).get("metadata", {}).get("table_count", 0) == 0:
        issues.append("Connector has no tables extracted")

    if not results.get("weaviate_ok"):
        issues.append("Weaviate vector search is failing (gRPC error)")
        issues.append("→ System falls back to default connector")
        issues.append("→ Default connector uses cloudmantra-genai.stox_ai")

    if results.get("wrong_project"):
        issues.append("SQL references wrong project (cloudmantra-genai instead of arizona-poc)")

    if issues:
        print(f"\n{Colors.RED}Issues Found:{Colors.RESET}")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

        print(f"\n{Colors.YELLOW}Recommended Fixes:{Colors.RESET}")
        print("  1. Fix Weaviate gRPC connection in ECS:")
        print("     - Check data-services container logs")
        print("     - Verify port 50051 is exposed")
        print("     - Check security group allows gRPC traffic")
        print("")
        print("  2. Add fallback to use active connector schema:")
        print("     - Modify sql_generator._get_relevant_schemas()")
        print("     - When vector search fails, use connector's get_dataset_schema()")
        print("     - Pass OAuth credentials to SQLGenerator")
    else:
        print(f"\n{Colors.GREEN}No issues found! Schema flow appears to be working.{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(description="Diagnose schema-to-LLM flow")
    parser.add_argument("--token", required=True, help="Authorization Bearer token")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    args = parser.parse_args()

    print(f"{Colors.BOLD}Schema Flow Diagnostic Tool{Colors.RESET}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Target: {args.base_url}")
    print("-" * 60)

    headers = {
        "Authorization": args.token,
        "Content-Type": "application/json"
    }

    results = {}

    # Step 1: Health Check
    results["api_ok"] = step1_health_check(headers)
    if not results["api_ok"]:
        print_summary(results)
        return 1

    # Step 2: Connector Status
    results["connector"] = step2_connector_status(headers)

    # Step 3: Weaviate Connection
    results["weaviate_ok"] = step3_weaviate_connection(headers)

    # Step 4: Schema Search
    matches = step4_schema_search(headers)
    results["wrong_project"] = any("cloudmantra-genai" in m[0] for m in matches) if matches else False

    # Step 5: Jena Store
    step5_jena_store(headers)

    # Step 6: Query Generation
    results["query_result"] = step6_query_generation(headers, results.get("connector"))

    # Summary
    print_summary(results)

    return 0 if not results.get("wrong_project") else 1


if __name__ == "__main__":
    sys.exit(main())
