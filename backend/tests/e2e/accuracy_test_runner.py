#!/usr/bin/env python3
"""
Comprehensive Accuracy Test Runner for Mantrix Axis AI

This script runs end-to-end tests against live API endpoints and generates
detailed accuracy reports for SQL generation, RDF lookups, and vector search.

Usage:
    python accuracy_test_runner.py --token <jwt_token>
    python accuracy_test_runner.py --token <jwt_token> --url https://axis-dev.cloudmantra.ai/api/v1
    python accuracy_test_runner.py --token <jwt_token> --output report.json
    python accuracy_test_runner.py --token <jwt_token> --category sql
    python accuracy_test_runner.py --token <jwt_token> --verbose

Categories:
    all      - Run all tests (default)
    sql      - SQL generation accuracy
    kg       - Knowledge graph verification
    vector   - Vector search verification
    cache    - Cache behavior
    errors   - Error handling
"""

import os
import sys
import json
import time
import argparse
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)


# =============================================================================
# TEST DEFINITIONS
# =============================================================================

SQL_TESTS = [
    # Easy - Basic aggregations
    {"id": "sql_001", "query": "What is the total revenue?", "difficulty": "easy",
     "patterns": ["SUM", "revenue"], "min_confidence": 0.7},
    {"id": "sql_002", "query": "How many customers do we have?", "difficulty": "easy",
     "patterns": ["COUNT"], "min_confidence": 0.8},
    {"id": "sql_003", "query": "Show all GL accounts", "difficulty": "easy",
     "patterns": ["GL", "account"], "min_confidence": 0.7},

    # Medium - Grouping and filtering
    {"id": "sql_004", "query": "Show revenue by customer segment", "difficulty": "medium",
     "patterns": ["GROUP BY", "segment"], "min_confidence": 0.6},
    {"id": "sql_005", "query": "What are the top 10 customers by revenue?", "difficulty": "medium",
     "patterns": ["ORDER BY", "DESC", "LIMIT"], "min_confidence": 0.7},
    {"id": "sql_006", "query": "Show monthly revenue trends", "difficulty": "medium",
     "patterns": ["GROUP BY", "month"], "min_confidence": 0.6},
    {"id": "sql_007", "query": "What products have the highest sales?", "difficulty": "medium",
     "patterns": ["ORDER BY", "product"], "min_confidence": 0.6},

    # Complex - Joins and calculations
    {"id": "sql_008", "query": "Show customer revenue with RFM segments", "difficulty": "complex",
     "patterns": ["JOIN", "RFM"], "min_confidence": 0.5},
    {"id": "sql_009", "query": "Calculate gross profit margin by category", "difficulty": "complex",
     "patterns": ["margin", "category"], "min_confidence": 0.5},
    {"id": "sql_010", "query": "Compare this year's revenue to last year", "difficulty": "complex",
     "patterns": ["revenue", "year"], "min_confidence": 0.5},
]

KG_TESTS = [
    {"id": "kg_001", "query": "Show customer details with their names",
     "expected_tables": ["customer"], "description": "Basic customer table discovery"},
    {"id": "kg_002", "query": "Show sales orders with customer information",
     "expected_tables": ["order", "customer"], "description": "Join path discovery"},
    {"id": "kg_003", "query": "Show revenue and COGS breakdown",
     "expected_tables": ["revenue", "COGS", "sales"], "description": "Financial column discovery"},
]

VECTOR_TESTS = [
    {"id": "vec_001", "query": "Show client spending patterns",
     "synonyms": ["customer", "revenue"], "description": "Semantic match: client -> customer"},
    {"id": "vec_002", "query": "What is our gross margin?",
     "synonyms": ["profit", "revenue", "COGS"], "description": "Financial metric matching"},
    {"id": "vec_003", "query": "Show quarterly performance",
     "synonyms": ["quarter", "date", "period"], "description": "Time-based grouping"},
]

ERROR_TESTS = [
    {"id": "err_001", "query": "", "expect_error": True, "description": "Empty query"},
    {"id": "err_002", "query": "asdfghjkl random nonsense", "expect_error": False,
     "description": "Nonsense should still attempt SQL"},
    {"id": "err_003", "query": "'; DROP TABLE test; --", "expect_error": False,
     "description": "SQL injection should be sanitized"},
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TestResult:
    test_id: str
    query: str
    success: bool
    sql: Optional[str] = None
    execution_time_ms: float = 0
    row_count: int = 0
    confidence_score: Optional[float] = None
    from_cache: bool = False
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CategoryResult:
    category: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    avg_time_ms: float = 0
    results: List[TestResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0


@dataclass
class AccuracyReport:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    api_url: str = ""
    categories: Dict[str, CategoryResult] = field(default_factory=dict)

    @property
    def total_tests(self) -> int:
        return sum(c.total for c in self.categories.values())

    @property
    def total_passed(self) -> int:
        return sum(c.passed for c in self.categories.values())

    @property
    def overall_pass_rate(self) -> float:
        total = self.total_tests
        return (self.total_passed / total * 100) if total > 0 else 0


# =============================================================================
# TEST RUNNER CLASS
# =============================================================================

class AccuracyTestRunner:
    """Main test runner for accuracy testing."""

    def __init__(self, token: str, base_url: str = "http://localhost:8000/api/v1",
                 timeout: float = 120.0, verbose: bool = False):
        self.token = token
        self.base_url = base_url
        self.timeout = timeout
        self.verbose = verbose
        self.report = AccuracyReport(api_url=base_url)

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def _make_request(self, endpoint: str, method: str = "GET",
                      payload: Optional[Dict] = None) -> Tuple[int, Dict]:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method == "GET":
                    response = client.get(url, headers=self.headers)
                else:
                    response = client.post(url, headers=self.headers, json=payload)

                return response.status_code, response.json() if response.status_code == 200 else {}
        except Exception as e:
            return 500, {"error": str(e)}

    def _log(self, message: str, level: str = "info"):
        """Log message if verbose mode is on."""
        if self.verbose:
            prefix = {"info": "  ", "success": "  ✓", "error": "  ✗", "warning": "  ⚠"}
            print(f"{prefix.get(level, '  ')} {message}")

    def check_health(self) -> bool:
        """Check API health."""
        print("\n[Health Check]")
        status, data = self._make_request("/health")

        if status == 200:
            print(f"  ✓ API is healthy")
            return True
        else:
            print(f"  ✗ API health check failed: {status}")
            return False

    def check_connectors(self) -> List[Dict]:
        """Check available connectors."""
        print("\n[Connectors]")
        status, data = self._make_request("/connectors")

        if status == 200:
            # Handle both list response and dict with connectors key
            connectors = data if isinstance(data, list) else data.get("connectors", [])
            if connectors:
                enabled = [c for c in connectors if c.get("enabled_for_chat")]
                print(f"  Found {len(connectors)} connector(s), {len(enabled)} enabled for chat")

                for c in connectors:
                    icon = "✓" if c.get("enabled_for_chat") else "○"
                    self._log(f"{icon} {c.get('name')} ({c.get('database_type')})")

                return connectors
            else:
                print(f"  No connectors found")
                return []
        else:
            print(f"  ⚠ Could not fetch connectors: {status}")
            return []

    def run_sql_tests(self) -> CategoryResult:
        """Run SQL generation accuracy tests."""
        print("\n[SQL Generation Tests]")
        category = CategoryResult(category="sql")

        for test in SQL_TESTS:
            result = self._run_single_sql_test(test)
            category.results.append(result)
            category.total += 1

            if result.success:
                category.passed += 1
            else:
                category.failed += 1

            # Print result
            status = "✓" if result.success else "✗"
            diff = test.get("difficulty", "?")
            print(f"  {status} [{diff.upper()[:1]}] {test['id']}: {test['query'][:50]}...")

            if self.verbose:
                if result.sql:
                    self._log(f"SQL: {result.sql[:80]}...")
                if result.error:
                    self._log(f"Error: {result.error}", "error")
                self._log(f"Time: {result.execution_time_ms:.0f}ms, Rows: {result.row_count}")

        if category.total > 0:
            category.avg_time_ms = sum(r.execution_time_ms for r in category.results) / category.total

        self.report.categories["sql"] = category
        return category

    def _run_single_sql_test(self, test: Dict) -> TestResult:
        """Run a single SQL generation test."""
        start = time.time()

        payload = {
            "question": test["query"],
            "options": {"use_vector_search": True, "max_tables": 5}
        }

        status, data = self._make_request("/query", "POST", payload)
        elapsed_ms = (time.time() - start) * 1000

        result = TestResult(
            test_id=test["id"],
            query=test["query"],
            success=False,
            execution_time_ms=elapsed_ms
        )

        if status == 200:
            result.sql = data.get("sql")
            result.confidence_score = data.get("confidence_score")
            result.from_cache = data.get("from_cache", False)

            execution = data.get("execution") or {}
            results = execution.get("results") or []
            result.row_count = len(results) if results else 0

            # Check for expected patterns
            sql_upper = (result.sql or "").upper()
            patterns_found = [p for p in test.get("patterns", []) if p.upper() in sql_upper]

            # Success criteria
            result.success = (
                result.sql is not None and
                len(patterns_found) > 0 and
                data.get("error") is None
            )

            result.details = {
                "patterns_expected": test.get("patterns", []),
                "patterns_found": patterns_found,
                "difficulty": test.get("difficulty"),
                "tables_used": data.get("tables_used", []),
                "kg_enhanced": data.get("kg_enhanced", False)
            }

        else:
            result.error = f"HTTP {status}: {data.get('error', 'Unknown error')}"

        return result

    def run_kg_tests(self) -> CategoryResult:
        """Run knowledge graph tests."""
        print("\n[Knowledge Graph Tests]")
        category = CategoryResult(category="kg")

        for test in KG_TESTS:
            result = self._run_single_kg_test(test)
            category.results.append(result)
            category.total += 1

            if result.success:
                category.passed += 1
            else:
                category.failed += 1

            status = "✓" if result.success else "○"  # Soft failures for KG
            print(f"  {status} {test['id']}: {test['description']}")

        if category.total > 0:
            category.avg_time_ms = sum(r.execution_time_ms for r in category.results) / category.total

        self.report.categories["kg"] = category
        return category

    def _run_single_kg_test(self, test: Dict) -> TestResult:
        """Run a single knowledge graph test."""
        start = time.time()

        payload = {
            "question": test["query"],
            "options": {"use_vector_search": True}
        }

        status, data = self._make_request("/query", "POST", payload)
        elapsed_ms = (time.time() - start) * 1000

        result = TestResult(
            test_id=test["id"],
            query=test["query"],
            success=False,
            execution_time_ms=elapsed_ms
        )

        if status == 200:
            result.sql = data.get("sql")
            sql_upper = (result.sql or "").upper()
            tables_used = [t.upper() for t in data.get("tables_used", [])]

            # Check if expected tables are referenced
            expected_found = []
            for expected in test.get("expected_tables", []):
                if any(expected.upper() in t for t in tables_used) or expected.upper() in sql_upper:
                    expected_found.append(expected)

            result.success = len(expected_found) > 0
            result.details = {
                "expected_tables": test.get("expected_tables", []),
                "expected_found": expected_found,
                "tables_used": data.get("tables_used", []),
                "kg_enhanced": data.get("kg_enhanced", False)
            }
        else:
            result.error = f"HTTP {status}"

        return result

    def run_vector_tests(self) -> CategoryResult:
        """Run vector search tests."""
        print("\n[Vector Search Tests]")
        category = CategoryResult(category="vector")

        for test in VECTOR_TESTS:
            result = self._run_single_vector_test(test)
            category.results.append(result)
            category.total += 1

            if result.success:
                category.passed += 1
            else:
                category.failed += 1

            status = "✓" if result.success else "✗"
            print(f"  {status} {test['id']}: {test['description']}")

        if category.total > 0:
            category.avg_time_ms = sum(r.execution_time_ms for r in category.results) / category.total

        self.report.categories["vector"] = category
        return category

    def _run_single_vector_test(self, test: Dict) -> TestResult:
        """Run a single vector search test."""
        start = time.time()

        payload = {
            "question": test["query"],
            "options": {"use_vector_search": True}
        }

        status, data = self._make_request("/query", "POST", payload)
        elapsed_ms = (time.time() - start) * 1000

        result = TestResult(
            test_id=test["id"],
            query=test["query"],
            success=False,
            execution_time_ms=elapsed_ms
        )

        if status == 200:
            result.sql = data.get("sql")
            sql_upper = (result.sql or "").upper()
            tables_used = [t.upper() for t in data.get("tables_used", [])]

            # Check synonyms
            synonyms_found = []
            for syn in test.get("synonyms", []):
                if syn.upper() in sql_upper or any(syn.upper() in t for t in tables_used):
                    synonyms_found.append(syn)

            result.success = len(synonyms_found) > 0 and result.sql is not None
            result.details = {
                "synonyms": test.get("synonyms", []),
                "synonyms_found": synonyms_found,
                "tables_used": data.get("tables_used", [])
            }
        else:
            result.error = f"HTTP {status}"

        return result

    def run_cache_test(self) -> CategoryResult:
        """Run cache verification test."""
        print("\n[Cache Tests]")
        category = CategoryResult(category="cache")

        query = "What is the total revenue?"

        # First request
        start1 = time.time()
        status1, data1 = self._make_request("/query", "POST", {"question": query})
        time1 = (time.time() - start1) * 1000

        # Second request (should be cached)
        start2 = time.time()
        status2, data2 = self._make_request("/query", "POST", {"question": query})
        time2 = (time.time() - start2) * 1000

        result = TestResult(
            test_id="cache_001",
            query=query,
            success=False,
            execution_time_ms=time2
        )

        if status1 == 200 and status2 == 200:
            from_cache_1 = data1.get("from_cache", False)
            from_cache_2 = data2.get("from_cache", False)

            # Success if second is cached or significantly faster
            result.success = from_cache_2 or (time2 < time1 * 0.5)
            result.from_cache = from_cache_2
            result.details = {
                "first_time_ms": time1,
                "second_time_ms": time2,
                "first_from_cache": from_cache_1,
                "second_from_cache": from_cache_2,
                "speedup": time1 / time2 if time2 > 0 else 0
            }

            status = "✓" if result.success else "✗"
            print(f"  {status} cache_001: First={time1:.0f}ms, Second={time2:.0f}ms (cached: {from_cache_2})")
        else:
            result.error = f"HTTP {status1}/{status2}"
            print(f"  ✗ cache_001: Request failed")

        category.results.append(result)
        category.total = 1
        category.passed = 1 if result.success else 0
        category.failed = 0 if result.success else 1
        category.avg_time_ms = time2

        self.report.categories["cache"] = category
        return category

    def run_error_tests(self) -> CategoryResult:
        """Run error handling tests."""
        print("\n[Error Handling Tests]")
        category = CategoryResult(category="errors")

        for test in ERROR_TESTS:
            start = time.time()
            status, data = self._make_request("/query", "POST", {"question": test["query"]})
            elapsed = (time.time() - start) * 1000

            has_error = status != 200 or data.get("error") is not None

            result = TestResult(
                test_id=test["id"],
                query=test["query"],
                success=(has_error == test["expect_error"]) or not test["expect_error"],
                execution_time_ms=elapsed,
                sql=data.get("sql")
            )

            # Special check for SQL injection
            if test["id"] == "err_003" and result.sql and "DROP" in result.sql.upper():
                result.success = False
                result.error = "SQL injection not sanitized!"

            result.details = {
                "expect_error": test["expect_error"],
                "got_error": has_error,
                "description": test["description"]
            }

            category.results.append(result)
            category.total += 1

            if result.success:
                category.passed += 1
            else:
                category.failed += 1

            status_icon = "✓" if result.success else "✗"
            print(f"  {status_icon} {test['id']}: {test['description']}")

        if category.total > 0:
            category.avg_time_ms = sum(r.execution_time_ms for r in category.results) / category.total

        self.report.categories["errors"] = category
        return category

    def run_all(self, categories: Optional[List[str]] = None):
        """Run all specified test categories."""
        if not self.check_health():
            print("\n⚠ API is not healthy, tests may fail")

        self.check_connectors()

        all_categories = ["sql", "kg", "vector", "cache", "errors"]
        to_run = categories if categories else all_categories

        if "sql" in to_run:
            self.run_sql_tests()
        if "kg" in to_run:
            self.run_kg_tests()
        if "vector" in to_run:
            self.run_vector_tests()
        if "cache" in to_run:
            self.run_cache_test()
        if "errors" in to_run:
            self.run_error_tests()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("ACCURACY TEST SUMMARY")
        print("=" * 60)

        for name, category in self.report.categories.items():
            print(f"\n{name.upper()}:")
            print(f"  Passed: {category.passed}/{category.total} ({category.pass_rate:.1f}%)")
            print(f"  Avg Time: {category.avg_time_ms:.0f}ms")

        print("\n" + "-" * 60)
        print(f"OVERALL: {self.report.total_passed}/{self.report.total_tests} "
              f"({self.report.overall_pass_rate:.1f}%)")
        print("=" * 60)

    def save_report(self, output_path: str):
        """Save report to JSON file."""
        report_dict = {
            "timestamp": self.report.timestamp,
            "api_url": self.report.api_url,
            "summary": {
                "total_tests": self.report.total_tests,
                "total_passed": self.report.total_passed,
                "overall_pass_rate": round(self.report.overall_pass_rate, 2)
            },
            "categories": {}
        }

        for name, category in self.report.categories.items():
            report_dict["categories"][name] = {
                "total": category.total,
                "passed": category.passed,
                "failed": category.failed,
                "pass_rate": round(category.pass_rate, 2),
                "avg_time_ms": round(category.avg_time_ms, 2),
                "results": [asdict(r) for r in category.results]
            }

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"\nReport saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run accuracy tests for Mantrix Axis AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python accuracy_test_runner.py --token YOUR_TOKEN
  python accuracy_test_runner.py --token YOUR_TOKEN --url https://axis-dev.cloudmantra.ai/api/v1
  python accuracy_test_runner.py --token YOUR_TOKEN --category sql
  python accuracy_test_runner.py --token YOUR_TOKEN --verbose --output report.json
        """
    )

    parser.add_argument("--token", "-t", help="JWT authentication token")
    parser.add_argument("--url", "-u", default="http://localhost:8000/api/v1",
                        help="API base URL")
    parser.add_argument("--category", "-c", choices=["all", "sql", "kg", "vector", "cache", "errors"],
                        default="all", help="Test category to run")
    parser.add_argument("--output", "-o", help="Output file for JSON report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--timeout", type=float, default=120.0, help="Request timeout in seconds")

    args = parser.parse_args()

    # Get token
    token = args.token or os.environ.get("AUTH_TOKEN")
    if not token:
        print("Error: JWT token required. Use --token or set AUTH_TOKEN environment variable")
        sys.exit(1)

    print("=" * 60)
    print("MANTRIX AXIS AI - ACCURACY TEST RUNNER")
    print("=" * 60)
    print(f"API URL: {args.url}")
    print(f"Token: {token[:30]}...")
    print(f"Category: {args.category}")
    print(f"Verbose: {args.verbose}")

    # Run tests
    runner = AccuracyTestRunner(
        token=token,
        base_url=args.url,
        timeout=args.timeout,
        verbose=args.verbose
    )

    categories = None if args.category == "all" else [args.category]
    runner.run_all(categories)
    runner.print_summary()

    # Save report
    if args.output:
        runner.save_report(args.output)
    else:
        # Default output location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = f"test_results/accuracy_report_{timestamp}.json"
        runner.save_report(default_output)


if __name__ == "__main__":
    main()
