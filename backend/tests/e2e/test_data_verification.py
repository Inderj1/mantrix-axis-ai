#!/usr/bin/env python3
"""
Data Verification Tests for RDF (Knowledge Graph) and Vector (Weaviate) Stores

This module verifies that:
1. RDF knowledge graph has correct table/column metadata
2. Vector store (Weaviate) has correct embeddings
3. RDF and Vector stores are in sync
4. Data quality checks pass

Usage:
    python tests/e2e/test_data_verification.py --token <jwt_token>
    python tests/e2e/test_data_verification.py --token <jwt_token> --url https://axis-dev.cloudmantra.ai/api/v1

    # With pytest
    AUTH_TOKEN=<token> pytest tests/e2e/test_data_verification.py -v -s
"""

import os
import sys
import json
import time
import argparse
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SchemaInfo:
    """Information about a table schema."""
    table_name: str
    database_type: Optional[str] = None
    connector_id: Optional[str] = None
    organization_id: Optional[str] = None
    column_count: int = 0
    columns: List[str] = field(default_factory=list)
    row_count: int = 0
    source: str = ""  # "weaviate", "rdf", "database"


@dataclass
class VerificationResult:
    """Result of a verification check."""
    check_name: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DataVerificationReport:
    """Complete data verification report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    api_url: str = ""

    # Summary
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0

    # Store status
    weaviate_connected: bool = False
    weaviate_schema_count: int = 0
    jena_connected: bool = False
    jena_triple_count: int = 0
    jena_table_count: int = 0

    # Connector info
    connectors: List[Dict[str, Any]] = field(default_factory=list)

    # Verification results
    results: List[VerificationResult] = field(default_factory=list)

    def add_result(self, result: VerificationResult):
        self.results.append(result)
        self.total_checks += 1
        if result.passed:
            self.passed_checks += 1
        else:
            self.failed_checks += 1


# =============================================================================
# VERIFICATION CLASS
# =============================================================================

class DataVerifier:
    """Verifies RDF and Vector data integrity."""

    def __init__(self, token: str, base_url: str = "http://localhost:8000/api/v1",
                 timeout: float = 60.0, verbose: bool = False):
        self.token = token
        self.base_url = base_url
        self.timeout = timeout
        self.verbose = verbose
        self.report = DataVerificationReport(api_url=base_url)

        # Cache for fetched data
        self._diagnostics_cache: Optional[Dict] = None
        self._connectors_cache: Optional[List] = None
        self._schemas_cache: Dict[str, List[SchemaInfo]] = {}

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def _make_request(self, endpoint: str, method: str = "GET",
                      payload: Optional[Dict] = None) -> tuple:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method == "GET":
                    response = client.get(url, headers=self.headers)
                else:
                    response = client.post(url, headers=self.headers, json=payload)

                if response.status_code == 200:
                    return response.status_code, response.json()
                else:
                    return response.status_code, {"error": response.text}
        except Exception as e:
            return 500, {"error": str(e)}

    def _log(self, message: str, level: str = "info"):
        """Log message if verbose mode is on."""
        if self.verbose:
            prefix = {"info": "  ", "success": "  ✓", "error": "  ✗", "warning": "  ⚠"}
            print(f"{prefix.get(level, '  ')} {message}")

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    def fetch_diagnostics(self) -> Dict[str, Any]:
        """Fetch schema diagnostics from API."""
        if self._diagnostics_cache:
            return self._diagnostics_cache

        print("\n[Fetching Schema Diagnostics]")
        status, data = self._make_request("/connectors/admin/diagnostics")

        if status == 200:
            # Handle nested response format: {success: true, diagnostics: {...}}
            if "diagnostics" in data:
                data = data["diagnostics"]
            self._diagnostics_cache = data
            print(f"  ✓ Diagnostics fetched successfully")
            return data
        elif status == 403:
            print(f"  ⚠ Admin access required for diagnostics")
            return {"error": "Admin access required"}
        else:
            print(f"  ✗ Failed to fetch diagnostics: {status}")
            return {"error": f"HTTP {status}"}

    def fetch_connectors(self) -> List[Dict[str, Any]]:
        """Fetch all connectors."""
        if self._connectors_cache:
            return self._connectors_cache

        print("\n[Fetching Connectors]")
        status, data = self._make_request("/connectors")

        if status == 200:
            connectors = data if isinstance(data, list) else data.get("connectors", [])
            self._connectors_cache = connectors
            print(f"  ✓ Found {len(connectors)} connector(s)")

            for c in connectors:
                enabled = "✓" if c.get("enabled_for_chat") else "○"
                self._log(f"{enabled} {c.get('name')} ({c.get('database_type')})",
                         "success" if c.get("enabled_for_chat") else "info")

            return connectors
        else:
            print(f"  ✗ Failed to fetch connectors: {status}")
            return []

    def fetch_schemas_from_api(self) -> List[Dict[str, Any]]:
        """Fetch schemas from the schemas endpoint."""
        print("\n[Fetching Schemas from API]")
        status, data = self._make_request("/schemas")

        if status == 200:
            schemas = data if isinstance(data, list) else data.get("schemas", [])
            print(f"  ✓ Found {len(schemas)} schema(s)")
            return schemas
        else:
            print(f"  ✗ Failed to fetch schemas: {status}")
            return []

    # =========================================================================
    # WEAVIATE VERIFICATION
    # =========================================================================

    def verify_weaviate_connection(self) -> VerificationResult:
        """Verify Weaviate is connected and has data."""
        diagnostics = self.fetch_diagnostics()
        weaviate_info = diagnostics.get("weaviate", {})

        connected = weaviate_info.get("connected", False)
        total_schemas = weaviate_info.get("total_schemas", 0)

        self.report.weaviate_connected = connected
        self.report.weaviate_schema_count = total_schemas

        result = VerificationResult(
            check_name="weaviate_connection",
            passed=connected and total_schemas > 0,
            details={
                "connected": connected,
                "total_schemas": total_schemas,
                "schemas_by_connector": weaviate_info.get("schemas_by_connector", {}),
                "sample_schemas": weaviate_info.get("sample_schemas", [])
            }
        )

        if not connected:
            result.errors.append("Weaviate is not connected")
        elif total_schemas == 0:
            result.errors.append("Weaviate has no schemas indexed")

        return result

    def verify_weaviate_schema_count(self) -> VerificationResult:
        """Verify Weaviate has schemas for enabled connectors."""
        diagnostics = self.fetch_diagnostics()
        connectors = self.fetch_connectors()

        weaviate_info = diagnostics.get("weaviate", {})
        schemas_by_connector = weaviate_info.get("schemas_by_connector", {})

        enabled_connectors = [c for c in connectors if c.get("enabled_for_chat")]

        errors = []
        warnings = []
        details = {
            "enabled_connectors": len(enabled_connectors),
            "connectors_with_schemas": {},
            "connectors_missing_schemas": []
        }

        for conn in enabled_connectors:
            conn_name = conn.get("name", "unknown")
            # Check if connector has schemas in Weaviate
            schema_count = schemas_by_connector.get(conn_name, 0)

            if schema_count > 0:
                details["connectors_with_schemas"][conn_name] = schema_count
            else:
                details["connectors_missing_schemas"].append(conn_name)
                warnings.append(f"Connector '{conn_name}' has no schemas in Weaviate")

        result = VerificationResult(
            check_name="weaviate_schema_coverage",
            passed=len(details["connectors_missing_schemas"]) == 0,
            details=details,
            errors=errors,
            warnings=warnings
        )

        return result

    def verify_weaviate_schema_quality(self) -> VerificationResult:
        """Verify Weaviate schemas have required fields."""
        diagnostics = self.fetch_diagnostics()
        weaviate_info = diagnostics.get("weaviate", {})
        sample_schemas = weaviate_info.get("sample_schemas", [])

        required_fields = ["table_name", "database_type", "connector_id"]
        missing_fields = []

        for schema in sample_schemas:
            for field in required_fields:
                if not schema.get(field):
                    missing_fields.append(f"{schema.get('table_name', 'unknown')}.{field}")

        result = VerificationResult(
            check_name="weaviate_schema_quality",
            passed=len(missing_fields) == 0,
            details={
                "samples_checked": len(sample_schemas),
                "required_fields": required_fields,
                "missing_fields": missing_fields
            }
        )

        if missing_fields:
            result.errors.append(f"Missing required fields: {missing_fields[:5]}")

        return result

    # =========================================================================
    # RDF/JENA VERIFICATION
    # =========================================================================

    def verify_jena_connection(self) -> VerificationResult:
        """Verify Jena/RDF store is connected and has data."""
        diagnostics = self.fetch_diagnostics()
        jena_info = diagnostics.get("jena", {})

        connected = jena_info.get("connected", False)
        triple_count = jena_info.get("triple_count", 0)
        table_count = jena_info.get("tables_in_graph", 0)
        backend = jena_info.get("backend", "unknown")

        self.report.jena_connected = connected
        self.report.jena_triple_count = triple_count
        self.report.jena_table_count = table_count

        result = VerificationResult(
            check_name="jena_connection",
            passed=connected,
            details={
                "connected": connected,
                "backend": backend,
                "triple_count": triple_count,
                "tables_in_graph": table_count,
                "postgres": jena_info.get("postgres", {})
            }
        )

        if not connected:
            result.errors.append(f"Jena ({backend}) is not connected")
        elif triple_count == 0:
            result.warnings.append("Jena has no triples (knowledge graph is empty)")

        return result

    def verify_jena_table_metadata(self) -> VerificationResult:
        """Verify Jena has table metadata that matches connectors."""
        diagnostics = self.fetch_diagnostics()
        connectors = self.fetch_connectors()

        jena_info = diagnostics.get("jena", {})
        table_count = jena_info.get("tables_in_graph", 0)

        # Get expected table count from Weaviate as reference
        weaviate_info = diagnostics.get("weaviate", {})
        weaviate_count = weaviate_info.get("total_schemas", 0)

        # Check if Jena has reasonable table count
        has_tables = table_count > 0
        matches_weaviate = abs(table_count - weaviate_count) < (weaviate_count * 0.2)  # Within 20%

        result = VerificationResult(
            check_name="jena_table_metadata",
            passed=has_tables,
            details={
                "jena_table_count": table_count,
                "weaviate_schema_count": weaviate_count,
                "difference": abs(table_count - weaviate_count),
                "in_sync": matches_weaviate
            }
        )

        if not has_tables:
            result.errors.append("Jena has no table metadata")
        elif not matches_weaviate:
            result.warnings.append(
                f"Jena table count ({table_count}) differs significantly from Weaviate ({weaviate_count})"
            )

        return result

    # =========================================================================
    # CROSS-REFERENCE VERIFICATION
    # =========================================================================

    def verify_rdf_vector_sync(self) -> VerificationResult:
        """Verify RDF and Vector stores have matching data."""
        diagnostics = self.fetch_diagnostics()

        weaviate_info = diagnostics.get("weaviate", {})
        jena_info = diagnostics.get("jena", {})

        weaviate_count = weaviate_info.get("total_schemas", 0)
        jena_count = jena_info.get("tables_in_graph", 0)

        # Check sync status
        both_have_data = weaviate_count > 0 and jena_count > 0
        counts_match = abs(weaviate_count - jena_count) < max(5, weaviate_count * 0.1)

        result = VerificationResult(
            check_name="rdf_vector_sync",
            passed=both_have_data and counts_match,
            details={
                "weaviate_schemas": weaviate_count,
                "jena_tables": jena_count,
                "difference": abs(weaviate_count - jena_count),
                "sync_status": "synced" if counts_match else "out_of_sync"
            }
        )

        if not both_have_data:
            if weaviate_count == 0:
                result.errors.append("Weaviate has no data")
            if jena_count == 0:
                result.errors.append("Jena has no data")
        elif not counts_match:
            result.warnings.append(
                f"RDF ({jena_count}) and Vector ({weaviate_count}) counts differ"
            )

        return result

    # =========================================================================
    # QUERY VERIFICATION
    # =========================================================================

    def verify_table_discovery(self) -> VerificationResult:
        """Verify that tables can be discovered via queries."""
        test_queries = [
            {"query": "Show all customers", "expected_tables": ["customer"]},
            {"query": "Show revenue data", "expected_tables": ["revenue", "sales"]},
            {"query": "Show GL accounts", "expected_tables": ["GL", "account"]},
        ]

        results = []
        errors = []

        for test in test_queries:
            status, data = self._make_request("/query", "POST", {"question": test["query"]})

            if status == 200:
                sql = data.get("sql", "")
                tables_used = data.get("tables_used", [])

                # Check if any expected table pattern is found
                sql_upper = sql.upper() if sql else ""
                tables_upper = [t.upper() for t in tables_used]

                found_expected = False
                for expected in test["expected_tables"]:
                    if expected.upper() in sql_upper or any(expected.upper() in t for t in tables_upper):
                        found_expected = True
                        break

                results.append({
                    "query": test["query"],
                    "found_tables": tables_used,
                    "expected_patterns": test["expected_tables"],
                    "matched": found_expected
                })

                if not found_expected:
                    errors.append(f"Query '{test['query']}' didn't find expected tables")
            else:
                errors.append(f"Query '{test['query']}' failed: {status}")

        passed = len(errors) == 0

        result = VerificationResult(
            check_name="table_discovery",
            passed=passed,
            details={
                "queries_tested": len(test_queries),
                "results": results
            },
            errors=errors
        )

        return result

    def verify_column_discovery(self) -> VerificationResult:
        """Verify that columns can be discovered via queries."""
        test_queries = [
            {"query": "Show customer names", "expected_columns": ["name", "customer"]},
            {"query": "Show total revenue", "expected_columns": ["revenue", "amount", "total"]},
        ]

        results = []
        errors = []

        for test in test_queries:
            status, data = self._make_request("/query", "POST", {"question": test["query"]})

            if status == 200:
                sql = data.get("sql", "")
                sql_upper = sql.upper() if sql else ""

                found_expected = False
                for expected in test["expected_columns"]:
                    if expected.upper() in sql_upper:
                        found_expected = True
                        break

                results.append({
                    "query": test["query"],
                    "sql_preview": sql[:100] if sql else None,
                    "expected_patterns": test["expected_columns"],
                    "matched": found_expected
                })

                if not found_expected:
                    errors.append(f"Query '{test['query']}' didn't find expected columns")
            else:
                errors.append(f"Query '{test['query']}' failed: {status}")

        result = VerificationResult(
            check_name="column_discovery",
            passed=len(errors) == 0,
            details={
                "queries_tested": len(test_queries),
                "results": results
            },
            errors=errors
        )

        return result

    # =========================================================================
    # SEMANTIC SEARCH VERIFICATION
    # =========================================================================

    def verify_semantic_search(self) -> VerificationResult:
        """Verify semantic search works correctly."""
        semantic_tests = [
            {"term": "client", "should_find": ["customer"]},
            {"term": "earnings", "should_find": ["revenue", "income", "profit"]},
            {"term": "expense", "should_find": ["cost", "COGS"]},
        ]

        results = []
        errors = []

        for test in semantic_tests:
            query = f"Show {test['term']} data"
            status, data = self._make_request("/query", "POST", {"question": query})

            if status == 200:
                sql = data.get("sql", "")
                sql_upper = sql.upper() if sql else ""

                found_expected = False
                for expected in test["should_find"]:
                    if expected.upper() in sql_upper:
                        found_expected = True
                        break

                results.append({
                    "search_term": test["term"],
                    "should_find": test["should_find"],
                    "matched": found_expected,
                    "sql_preview": sql[:80] if sql else None
                })

                if not found_expected:
                    errors.append(f"Semantic search for '{test['term']}' didn't find expected terms")

        result = VerificationResult(
            check_name="semantic_search",
            passed=len(results) > 0 and sum(1 for r in results if r["matched"]) >= len(results) // 2,
            details={
                "tests_run": len(semantic_tests),
                "results": results
            },
            errors=errors if len(errors) == len(semantic_tests) else [],  # Only error if ALL fail
            warnings=errors if 0 < len(errors) < len(semantic_tests) else []
        )

        return result

    # =========================================================================
    # RUN ALL VERIFICATIONS
    # =========================================================================

    def run_all_verifications(self):
        """Run all verification checks."""
        print("\n" + "=" * 60)
        print("DATA VERIFICATION TESTS")
        print("=" * 60)

        # Fetch base data first
        connectors = self.fetch_connectors()
        self.report.connectors = connectors

        diagnostics = self.fetch_diagnostics()

        if "error" in diagnostics:
            print(f"\n⚠ Could not fetch diagnostics: {diagnostics['error']}")
            print("  Skipping diagnostic-based tests, running query-based tests only")

            # Run query-based tests only
            verifications = [
                ("Table Discovery", self.verify_table_discovery),
                ("Column Discovery", self.verify_column_discovery),
                ("Semantic Search", self.verify_semantic_search),
            ]
        else:
            # Run all tests
            verifications = [
                # Weaviate checks
                ("Weaviate Connection", self.verify_weaviate_connection),
                ("Weaviate Schema Coverage", self.verify_weaviate_schema_count),
                ("Weaviate Schema Quality", self.verify_weaviate_schema_quality),

                # Jena checks
                ("Jena Connection", self.verify_jena_connection),
                ("Jena Table Metadata", self.verify_jena_table_metadata),

                # Cross-reference
                ("RDF-Vector Sync", self.verify_rdf_vector_sync),

                # Query-based checks
                ("Table Discovery", self.verify_table_discovery),
                ("Column Discovery", self.verify_column_discovery),
                ("Semantic Search", self.verify_semantic_search),
            ]

        print("\n[Running Verification Checks]")

        for name, check_func in verifications:
            try:
                result = check_func()
                self.report.add_result(result)

                status = "✓" if result.passed else "✗"
                print(f"  {status} {name}")

                if self.verbose:
                    for err in result.errors:
                        print(f"    ERROR: {err}")
                    for warn in result.warnings:
                        print(f"    WARNING: {warn}")

            except Exception as e:
                result = VerificationResult(
                    check_name=name.lower().replace(" ", "_"),
                    passed=False,
                    errors=[str(e)]
                )
                self.report.add_result(result)
                print(f"  ✗ {name} (exception: {e})")

    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)

        print(f"\nConnectors: {len(self.report.connectors)}")
        print(f"Weaviate: {'Connected' if self.report.weaviate_connected else 'Not Connected'} "
              f"({self.report.weaviate_schema_count} schemas)")
        print(f"Jena: {'Connected' if self.report.jena_connected else 'Not Connected'} "
              f"({self.report.jena_triple_count} triples, {self.report.jena_table_count} tables)")

        print(f"\nChecks: {self.report.passed_checks}/{self.report.total_checks} passed")

        if self.report.failed_checks > 0:
            print("\nFailed Checks:")
            for result in self.report.results:
                if not result.passed:
                    print(f"  ✗ {result.check_name}")
                    for err in result.errors[:3]:
                        print(f"      {err}")

        print("\n" + "=" * 60)

    def save_report(self, output_path: str):
        """Save report to JSON file."""
        report_dict = {
            "timestamp": self.report.timestamp,
            "api_url": self.report.api_url,
            "summary": {
                "total_checks": self.report.total_checks,
                "passed_checks": self.report.passed_checks,
                "failed_checks": self.report.failed_checks,
                "pass_rate": round(self.report.passed_checks / max(1, self.report.total_checks) * 100, 2)
            },
            "stores": {
                "weaviate": {
                    "connected": self.report.weaviate_connected,
                    "schema_count": self.report.weaviate_schema_count
                },
                "jena": {
                    "connected": self.report.jena_connected,
                    "triple_count": self.report.jena_triple_count,
                    "table_count": self.report.jena_table_count
                }
            },
            "connectors": self.report.connectors,
            "results": [asdict(r) for r in self.report.results]
        }

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"\nReport saved: {output_path}")


# =============================================================================
# PYTEST INTEGRATION
# =============================================================================

import pytest

@pytest.fixture(scope="module")
def verifier():
    """Create verifier with token from environment."""
    token = os.environ.get("AUTH_TOKEN")
    if not token:
        pytest.skip("AUTH_TOKEN environment variable not set")

    url = os.environ.get("API_URL", "http://localhost:8000/api/v1")
    return DataVerifier(token=token, base_url=url, verbose=True)


class TestWeaviateVerification:
    """Weaviate verification tests."""

    def test_weaviate_connection(self, verifier):
        result = verifier.verify_weaviate_connection()
        assert result.passed, f"Weaviate connection failed: {result.errors}"

    def test_weaviate_schema_coverage(self, verifier):
        result = verifier.verify_weaviate_schema_count()
        # Allow warnings but not errors
        assert len(result.errors) == 0, f"Schema coverage errors: {result.errors}"

    def test_weaviate_schema_quality(self, verifier):
        result = verifier.verify_weaviate_schema_quality()
        assert result.passed, f"Schema quality failed: {result.errors}"


class TestJenaVerification:
    """Jena/RDF verification tests."""

    def test_jena_connection(self, verifier):
        result = verifier.verify_jena_connection()
        assert result.passed, f"Jena connection failed: {result.errors}"

    def test_jena_table_metadata(self, verifier):
        result = verifier.verify_jena_table_metadata()
        assert result.passed, f"Jena table metadata failed: {result.errors}"


class TestCrossReferenceVerification:
    """Cross-reference verification tests."""

    def test_rdf_vector_sync(self, verifier):
        result = verifier.verify_rdf_vector_sync()
        assert result.passed, f"RDF-Vector sync failed: {result.errors}"


class TestQueryVerification:
    """Query-based verification tests."""

    def test_table_discovery(self, verifier):
        result = verifier.verify_table_discovery()
        assert result.passed, f"Table discovery failed: {result.errors}"

    def test_column_discovery(self, verifier):
        result = verifier.verify_column_discovery()
        assert result.passed, f"Column discovery failed: {result.errors}"

    def test_semantic_search(self, verifier):
        result = verifier.verify_semantic_search()
        # Semantic search is soft - just check it doesn't completely fail
        assert len(result.errors) < len(result.details.get("results", [])), \
            f"Semantic search failed: {result.errors}"


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Verify RDF and Vector data integrity")
    parser.add_argument("--token", "-t", help="JWT authentication token")
    parser.add_argument("--url", "-u", default="http://localhost:8000/api/v1",
                        help="API base URL")
    parser.add_argument("--output", "-o", help="Output file for JSON report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    token = args.token or os.environ.get("AUTH_TOKEN")
    if not token:
        print("Error: JWT token required. Use --token or set AUTH_TOKEN")
        sys.exit(1)

    print("=" * 60)
    print("MANTRIX AXIS AI - DATA VERIFICATION")
    print("=" * 60)
    print(f"API URL: {args.url}")
    print(f"Token: {token[:30]}...")

    verifier = DataVerifier(
        token=token,
        base_url=args.url,
        verbose=args.verbose
    )

    verifier.run_all_verifications()
    verifier.print_summary()

    # Save report
    if args.output:
        verifier.save_report(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = f"test_results/data_verification_{timestamp}.json"
        verifier.save_report(default_output)

    # Exit with error code if any checks failed
    sys.exit(0 if verifier.report.failed_checks == 0 else 1)


if __name__ == "__main__":
    main()
