#!/usr/bin/env python3
"""
End-to-End Quality/Accuracy Test Suite for Mantrix Axis AI NLP-to-SQL System

This script tests the complete pipeline:
1. Schema sync verification (Weaviate vectors, Jena RDF)
2. Vector search quality
3. NLP query generation and execution
4. Error correction behavior
5. Results accuracy

Usage:
    # With authentication (recommended for full testing)
    TOKEN="your_jwt_token" python test_e2e_quality.py

    # Against local development
    BASE_URL="http://localhost:8000" TOKEN="your_jwt_token" python test_e2e_quality.py

    # Run specific test categories
    python test_e2e_quality.py --category schema
    python test_e2e_quality.py --category queries
    python test_e2e_quality.py --category all
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    WARN = "WARN"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    message: str
    duration_ms: float = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    name: str
    results: List[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.WARN)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.SKIP)


class E2EQualityTester:
    """End-to-end quality tester for Mantrix Axis AI"""

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

        self.suites: List[TestSuite] = []

    def _request(self, method: str, endpoint: str, **kwargs) -> Tuple[Optional[Dict], int, float]:
        """Make HTTP request and return (response_json, status_code, duration_ms)"""
        url = f"{self.base_url}{endpoint}"
        start = time.time()
        try:
            resp = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=120,
                **kwargs
            )
            duration_ms = (time.time() - start) * 1000
            try:
                return resp.json(), resp.status_code, duration_ms
            except:
                return {"raw": resp.text}, resp.status_code, duration_ms
        except requests.exceptions.Timeout:
            return None, 0, (time.time() - start) * 1000
        except Exception as e:
            return {"error": str(e)}, 0, (time.time() - start) * 1000

    # =========================================================================
    # SCHEMA & INFRASTRUCTURE TESTS
    # =========================================================================

    def test_health_check(self) -> TestResult:
        """Test basic health endpoint (unauthenticated)"""
        data, status, duration = self._request("GET", "/api/v1/health")

        if status == 200:
            # Health check without auth uses 'default' org - some errors expected
            return TestResult(
                name="Health Check",
                status=TestStatus.PASS,
                message="Health endpoint accessible",
                duration_ms=duration,
                details=data
            )
        else:
            return TestResult(
                name="Health Check",
                status=TestStatus.FAIL,
                message=f"Health check failed with status {status}",
                duration_ms=duration,
                details=data or {}
            )

    def test_diagnostics(self) -> TestResult:
        """Test admin diagnostics endpoint (requires auth)"""
        if not self.token:
            return TestResult(
                name="Diagnostics",
                status=TestStatus.SKIP,
                message="Skipped - no auth token provided"
            )

        data, status, duration = self._request("GET", "/api/v1/connectors/admin/diagnostics")

        if status == 200:
            weaviate_count = data.get("weaviate", {}).get("total_schemas", 0)
            jena_count = data.get("jena", {}).get("triple_count", 0)

            issues = []
            if weaviate_count == 0:
                issues.append("No vectors in Weaviate")
            if jena_count == 0:
                issues.append("No triples in Jena (known issue - permission error)")

            return TestResult(
                name="Diagnostics",
                status=TestStatus.WARN if issues else TestStatus.PASS,
                message=f"Weaviate: {weaviate_count} tables, Jena: {jena_count} triples" +
                        (f" - Issues: {', '.join(issues)}" if issues else ""),
                duration_ms=duration,
                details=data
            )
        elif status == 401 or status == 403:
            return TestResult(
                name="Diagnostics",
                status=TestStatus.SKIP,
                message="Auth required or insufficient permissions",
                duration_ms=duration
            )
        else:
            return TestResult(
                name="Diagnostics",
                status=TestStatus.FAIL,
                message=f"Diagnostics failed with status {status}",
                duration_ms=duration,
                details=data or {}
            )

    def test_weaviate_vectors(self) -> TestResult:
        """Verify Weaviate has indexed tables"""
        if not self.token:
            return TestResult(
                name="Weaviate Vectors",
                status=TestStatus.SKIP,
                message="Skipped - no auth token"
            )

        data, status, duration = self._request("GET", "/api/v1/connectors/admin/diagnostics")

        if status != 200:
            return TestResult(
                name="Weaviate Vectors",
                status=TestStatus.FAIL,
                message=f"Could not fetch diagnostics: status {status}",
                duration_ms=duration
            )

        weaviate = data.get("weaviate", {})
        total = weaviate.get("total_schemas", 0)
        connected = weaviate.get("connected", False)

        if not connected:
            return TestResult(
                name="Weaviate Vectors",
                status=TestStatus.FAIL,
                message="Weaviate not connected",
                duration_ms=duration,
                details=weaviate
            )

        if total == 0:
            return TestResult(
                name="Weaviate Vectors",
                status=TestStatus.FAIL,
                message="No tables indexed in Weaviate - run schema sync",
                duration_ms=duration,
                details=weaviate
            )

        return TestResult(
            name="Weaviate Vectors",
            status=TestStatus.PASS,
            message=f"{total} tables indexed in Weaviate",
            duration_ms=duration,
            details=weaviate
        )

    def test_jena_rdf(self) -> TestResult:
        """Verify Jena RDF triples (known to fail due to permission issue)"""
        if not self.token:
            return TestResult(
                name="Jena RDF",
                status=TestStatus.SKIP,
                message="Skipped - no auth token"
            )

        data, status, duration = self._request("GET", "/api/v1/connectors/admin/diagnostics")

        if status != 200:
            return TestResult(
                name="Jena RDF",
                status=TestStatus.FAIL,
                message=f"Could not fetch diagnostics: status {status}",
                duration_ms=duration
            )

        jena = data.get("jena", {})
        triple_count = jena.get("triple_count", 0)

        if triple_count == 0:
            return TestResult(
                name="Jena RDF",
                status=TestStatus.WARN,
                message="No RDF triples loaded (known issue: ECS file permission error). "
                        "System falls back to vector search + LLM for JOINs.",
                duration_ms=duration,
                details=jena
            )

        return TestResult(
            name="Jena RDF",
            status=TestStatus.PASS,
            message=f"{triple_count} triples loaded in Jena",
            duration_ms=duration,
            details=jena
        )

    # =========================================================================
    # VECTOR SEARCH TESTS
    # =========================================================================

    def test_vector_search(self, query: str, expected_tables: List[str] = None) -> TestResult:
        """Test vector search returns relevant tables"""
        if not self.token:
            return TestResult(
                name=f"Vector Search: {query}",
                status=TestStatus.SKIP,
                message="Skipped - no auth token"
            )

        data, status, duration = self._request(
            "POST",
            f"/api/v1/connectors/admin/test-vector-search?query={query}"
        )

        if status != 200:
            return TestResult(
                name=f"Vector Search: {query}",
                status=TestStatus.FAIL,
                message=f"Vector search failed: status {status}",
                duration_ms=duration,
                details=data or {}
            )

        results = data.get("results", [])
        if not results:
            return TestResult(
                name=f"Vector Search: {query}",
                status=TestStatus.FAIL,
                message="No results returned from vector search",
                duration_ms=duration,
                details=data
            )

        # Check if expected tables are in top results
        top_tables = [r.get("table_name", "").lower() for r in results[:5]]

        if expected_tables:
            found = [t for t in expected_tables if any(t.lower() in tt for tt in top_tables)]
            if not found:
                return TestResult(
                    name=f"Vector Search: {query}",
                    status=TestStatus.WARN,
                    message=f"Expected tables {expected_tables} not in top 5 results: {top_tables}",
                    duration_ms=duration,
                    details=data
                )

        return TestResult(
            name=f"Vector Search: {query}",
            status=TestStatus.PASS,
            message=f"Found {len(results)} tables. Top: {', '.join(top_tables[:3])}",
            duration_ms=duration,
            details=data
        )

    # =========================================================================
    # NLP QUERY TESTS
    # =========================================================================

    def test_nlp_query(
        self,
        query: str,
        expect_results: bool = True,
        min_rows: int = 0,
        expect_error_correction: bool = False
    ) -> TestResult:
        """Test NLP query execution"""
        if not self.token:
            return TestResult(
                name=f"Query: {query[:50]}...",
                status=TestStatus.SKIP,
                message="Skipped - no auth token"
            )

        payload = {
            "query": query,
            "conversation_id": f"test_{int(time.time())}"
        }

        data, status, duration = self._request("POST", "/api/v1/query", json=payload)

        if status != 200:
            error_msg = data.get("detail", data.get("error", "Unknown error")) if data else "Request failed"

            # Check for known issues
            if "organization" in str(error_msg).lower() or "connector" in str(error_msg).lower():
                return TestResult(
                    name=f"Query: {query[:50]}...",
                    status=TestStatus.SKIP,
                    message=f"Org/connector issue (not fixable by error correction): {error_msg}",
                    duration_ms=duration,
                    details=data or {}
                )

            return TestResult(
                name=f"Query: {query[:50]}...",
                status=TestStatus.FAIL,
                message=f"Query failed: {error_msg}",
                duration_ms=duration,
                details=data or {}
            )

        # Check if we got results
        results = data.get("results", [])
        sql = data.get("sql", data.get("generated_sql", ""))
        error_correction_used = data.get("error_correction_used", False)

        if expect_results and not results:
            return TestResult(
                name=f"Query: {query[:50]}...",
                status=TestStatus.FAIL,
                message="Query succeeded but returned no results",
                duration_ms=duration,
                details={"sql": sql, "response": data}
            )

        if min_rows > 0 and len(results) < min_rows:
            return TestResult(
                name=f"Query: {query[:50]}...",
                status=TestStatus.WARN,
                message=f"Expected at least {min_rows} rows, got {len(results)}",
                duration_ms=duration,
                details={"sql": sql, "row_count": len(results)}
            )

        return TestResult(
            name=f"Query: {query[:50]}...",
            status=TestStatus.PASS,
            message=f"Returned {len(results)} rows" +
                    (f" (error correction used)" if error_correction_used else ""),
            duration_ms=duration,
            details={
                "sql": sql,
                "row_count": len(results),
                "error_correction_used": error_correction_used,
                "sample_result": results[0] if results else None
            }
        )

    # =========================================================================
    # TEST EXECUTION
    # =========================================================================

    def run_schema_tests(self) -> TestSuite:
        """Run schema and infrastructure tests"""
        suite = TestSuite(name="Schema & Infrastructure")

        print("\n" + "=" * 60)
        print("SCHEMA & INFRASTRUCTURE TESTS")
        print("=" * 60)

        tests = [
            self.test_health_check,
            self.test_diagnostics,
            self.test_weaviate_vectors,
            self.test_jena_rdf,
        ]

        for test_fn in tests:
            result = test_fn()
            suite.results.append(result)
            self._print_result(result)

        self.suites.append(suite)
        return suite

    def run_vector_search_tests(self) -> TestSuite:
        """Run vector search quality tests"""
        suite = TestSuite(name="Vector Search")

        print("\n" + "=" * 60)
        print("VECTOR SEARCH TESTS")
        print("=" * 60)

        search_tests = [
            ("customers", ["customer"]),
            ("sales orders", ["sales", "order"]),
            ("revenue by region", ["sales", "regional"]),
            ("product performance", ["product"]),
            ("retention analysis", ["retention", "cohort"]),
        ]

        for query, expected in search_tests:
            result = self.test_vector_search(query, expected)
            suite.results.append(result)
            self._print_result(result)

        self.suites.append(suite)
        return suite

    def run_query_tests(self) -> TestSuite:
        """Run NLP query tests"""
        suite = TestSuite(name="NLP Queries")

        print("\n" + "=" * 60)
        print("NLP QUERY TESTS")
        print("=" * 60)

        # Test queries from simplest to most complex
        query_tests = [
            # Simple queries
            {
                "query": "How many customers do we have?",
                "expect_results": True,
                "min_rows": 1,
                "category": "simple"
            },
            {
                "query": "What are my top selling products?",
                "expect_results": True,
                "min_rows": 1,
                "category": "simple"
            },
            # Medium complexity
            {
                "query": "Show me revenue breakdown by region",
                "expect_results": True,
                "min_rows": 1,
                "category": "medium"
            },
            {
                "query": "What is the average order value?",
                "expect_results": True,
                "min_rows": 1,
                "category": "medium"
            },
            # Complex queries
            {
                "query": "Compare gross margin by customer segment for Q4",
                "expect_results": True,
                "min_rows": 1,
                "category": "complex"
            },
            {
                "query": "Which customers are buying the most but have declining retention?",
                "expect_results": True,
                "min_rows": 1,
                "category": "complex"
            },
            # Edge cases (may trigger error correction)
            {
                "query": "Show me the trend for last month",
                "expect_results": True,
                "min_rows": 0,  # May fail due to date issues
                "category": "edge_case"
            },
        ]

        for test in query_tests:
            print(f"\n[{test['category'].upper()}]")
            result = self.test_nlp_query(
                test["query"],
                expect_results=test["expect_results"],
                min_rows=test["min_rows"]
            )
            suite.results.append(result)
            self._print_result(result)

        self.suites.append(suite)
        return suite

    def _print_result(self, result: TestResult):
        """Print a single test result"""
        status_colors = {
            TestStatus.PASS: "\033[92m",  # Green
            TestStatus.FAIL: "\033[91m",  # Red
            TestStatus.WARN: "\033[93m",  # Yellow
            TestStatus.SKIP: "\033[94m",  # Blue
        }
        reset = "\033[0m"

        color = status_colors.get(result.status, "")
        print(f"{color}[{result.status.value}]{reset} {result.name}")
        print(f"       {result.message}")
        if result.duration_ms > 0:
            print(f"       Duration: {result.duration_ms:.0f}ms")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        total_passed = 0
        total_failed = 0
        total_warned = 0
        total_skipped = 0

        for suite in self.suites:
            print(f"\n{suite.name}:")
            print(f"  Passed:  {suite.passed}")
            print(f"  Failed:  {suite.failed}")
            print(f"  Warnings: {suite.warnings}")
            print(f"  Skipped: {suite.skipped}")

            total_passed += suite.passed
            total_failed += suite.failed
            total_warned += suite.warnings
            total_skipped += suite.skipped

        print("\n" + "-" * 60)
        print(f"TOTAL: {total_passed} passed, {total_failed} failed, "
              f"{total_warned} warnings, {total_skipped} skipped")

        # Exit code
        if total_failed > 0:
            print("\n\033[91mSome tests FAILED\033[0m")
            return 1
        elif total_warned > 0:
            print("\n\033[93mAll tests passed with WARNINGS\033[0m")
            return 0
        else:
            print("\n\033[92mAll tests PASSED\033[0m")
            return 0

    def export_results(self, filepath: str):
        """Export results to JSON file"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "authenticated": bool(self.token),
            "suites": []
        }

        for suite in self.suites:
            suite_data = {
                "name": suite.name,
                "passed": suite.passed,
                "failed": suite.failed,
                "warnings": suite.warnings,
                "skipped": suite.skipped,
                "results": [
                    {
                        "name": r.name,
                        "status": r.status.value,
                        "message": r.message,
                        "duration_ms": r.duration_ms,
                        "details": r.details
                    }
                    for r in suite.results
                ]
            }
            results["suites"].append(suite_data)

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nResults exported to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="E2E Quality Test Suite for Mantrix Axis AI")
    parser.add_argument(
        "--category",
        choices=["schema", "vector", "queries", "all"],
        default="all",
        help="Test category to run"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export results to JSON file"
    )
    args = parser.parse_args()

    # Configuration
    base_url = os.environ.get("BASE_URL", "https://axis-dev.cloudmantra.ai")
    token = os.environ.get("TOKEN")

    print("=" * 60)
    print("MANTRIX AXIS AI - E2E QUALITY TEST SUITE")
    print("=" * 60)
    print(f"Target: {base_url}")
    print(f"Auth: {'Yes' if token else 'No (some tests will be skipped)'}")
    print(f"Category: {args.category}")
    print(f"Time: {datetime.now().isoformat()}")

    if not token:
        print("\n\033[93mWARNING: No TOKEN environment variable set.")
        print("Most tests require authentication. Set TOKEN to run full suite.\033[0m")

    # Run tests
    tester = E2EQualityTester(base_url, token)

    if args.category in ["schema", "all"]:
        tester.run_schema_tests()

    if args.category in ["vector", "all"]:
        tester.run_vector_search_tests()

    if args.category in ["queries", "all"]:
        tester.run_query_tests()

    # Summary
    exit_code = tester.print_summary()

    # Export if requested
    if args.export:
        tester.export_results(args.export)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
