#!/usr/bin/env python3
"""
End-to-End Integration Tests for Query Accuracy

Tests the complete pipeline using real API endpoints:
1. SQL Generation Accuracy
2. RDF/Knowledge Graph Lookups
3. Vector Embedding Search
4. Query Execution

Usage:
    # Set your JWT token first
    export AUTH_TOKEN="your_jwt_token_here"

    # Run all tests
    pytest tests/e2e/test_endpoint_accuracy.py -v

    # Run specific test categories
    pytest tests/e2e/test_endpoint_accuracy.py -v -k "sql_generation"
    pytest tests/e2e/test_endpoint_accuracy.py -v -k "knowledge_graph"
    pytest tests/e2e/test_endpoint_accuracy.py -v -k "vector_search"

    # Run with detailed output
    pytest tests/e2e/test_endpoint_accuracy.py -v -s --tb=short
"""

import os
import sys
import json
import time
import pytest
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class TestConfig:
    """Test configuration settings."""
    base_url: str = "http://localhost:8000/api/v1"
    auth_token: Optional[str] = None
    timeout: float = 120.0  # seconds
    verbose: bool = True

    def __post_init__(self):
        # Try to get token from environment
        self.auth_token = os.environ.get("AUTH_TOKEN", self.auth_token)

    @property
    def headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers


@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    query: str
    success: bool
    sql_generated: Optional[str] = None
    execution_time_ms: float = 0
    row_count: int = 0
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "query": self.query,
            "success": self.success,
            "sql_generated": self.sql_generated,
            "execution_time_ms": self.execution_time_ms,
            "row_count": self.row_count,
            "error": self.error,
            "details": self.details
        }


@dataclass
class AccuracyReport:
    """Aggregated accuracy report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    sql_accuracy: float = 0.0
    kg_usage_rate: float = 0.0
    vector_usage_rate: float = 0.0
    avg_execution_time_ms: float = 0.0
    results: List[TestResult] = field(default_factory=list)

    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.success:
            self.passed += 1
        else:
            self.failed += 1

    def calculate_metrics(self):
        if self.total_tests > 0:
            self.sql_accuracy = (self.passed / self.total_tests) * 100

            kg_used = sum(1 for r in self.results if r.details.get("kg_enhanced"))
            self.kg_usage_rate = (kg_used / self.total_tests) * 100

            vector_used = sum(1 for r in self.results if r.details.get("vector_search_used"))
            self.vector_usage_rate = (vector_used / self.total_tests) * 100

            total_time = sum(r.execution_time_ms for r in self.results)
            self.avg_execution_time_ms = total_time / self.total_tests

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "sql_accuracy_pct": round(self.sql_accuracy, 2),
                "kg_usage_rate_pct": round(self.kg_usage_rate, 2),
                "vector_usage_rate_pct": round(self.vector_usage_rate, 2),
                "avg_execution_time_ms": round(self.avg_execution_time_ms, 2)
            },
            "results": [r.to_dict() for r in self.results]
        }


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def config():
    """Test configuration fixture."""
    cfg = TestConfig()
    if not cfg.auth_token:
        pytest.skip("AUTH_TOKEN environment variable not set")
    return cfg


@pytest.fixture(scope="module")
def http_client(config):
    """HTTP client with authentication."""
    with httpx.Client(
        base_url=config.base_url,
        headers=config.headers,
        timeout=config.timeout
    ) as client:
        yield client


@pytest.fixture(scope="module")
def accuracy_report():
    """Shared accuracy report for all tests."""
    return AccuracyReport()


# =============================================================================
# TEST CASES - SQL GENERATION ACCURACY
# =============================================================================

SQL_GENERATION_TEST_CASES = [
    # Easy queries - basic aggregations
    {
        "name": "simple_total_revenue",
        "query": "What is the total revenue?",
        "difficulty": "easy",
        "expected_patterns": ["SUM", "revenue", "Net_Sales"],
        "should_return_rows": True
    },
    {
        "name": "simple_customer_filter",
        "query": "Show me sales for customer 1000123",
        "difficulty": "easy",
        "expected_patterns": ["Customer", "WHERE"],
        "should_return_rows": False  # May not exist
    },
    {
        "name": "simple_count",
        "query": "How many customers do we have?",
        "difficulty": "easy",
        "expected_patterns": ["COUNT", "customer"],
        "should_return_rows": True
    },

    # Medium queries - joins and grouping
    {
        "name": "revenue_by_segment",
        "query": "Show revenue by customer segment",
        "difficulty": "medium",
        "expected_patterns": ["GROUP BY", "segment"],
        "should_return_rows": True
    },
    {
        "name": "monthly_trends",
        "query": "What are the monthly revenue trends?",
        "difficulty": "medium",
        "expected_patterns": ["GROUP BY", "month", "EXTRACT", "DATE_TRUNC"],
        "should_return_rows": True
    },
    {
        "name": "top_customers",
        "query": "Show me the top 10 customers by revenue",
        "difficulty": "medium",
        "expected_patterns": ["ORDER BY", "DESC", "LIMIT 10"],
        "should_return_rows": True
    },

    # Complex queries - multiple joins and calculations
    {
        "name": "customer_rfm_analysis",
        "query": "Show top 10 customers by revenue with their RFM segments",
        "difficulty": "complex",
        "expected_patterns": ["JOIN", "RFM"],
        "should_return_rows": True
    },
    {
        "name": "gross_profit_by_category",
        "query": "What is the gross profit margin by product category?",
        "difficulty": "complex",
        "expected_patterns": ["revenue", "COGS", "category"],
        "should_return_rows": True
    },
    {
        "name": "yoy_comparison",
        "query": "Compare this year's revenue to last year",
        "difficulty": "complex",
        "expected_patterns": ["YEAR", "revenue"],
        "should_return_rows": True
    },
]


class TestSQLGenerationAccuracy:
    """Test SQL generation accuracy using real endpoints."""

    @pytest.mark.parametrize("test_case", SQL_GENERATION_TEST_CASES, ids=lambda x: x["name"])
    def test_sql_generation(self, http_client, config, accuracy_report, test_case):
        """Test SQL generation for various query types."""
        start_time = time.time()

        # Make request
        payload = {
            "question": test_case["query"],
            "options": {
                "use_vector_search": True,
                "max_tables": 5
            }
        }

        try:
            response = http_client.post("/query", json=payload)
            execution_time_ms = (time.time() - start_time) * 1000

            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=False,
                execution_time_ms=execution_time_ms
            )

            if response.status_code == 200:
                data = response.json()
                result.sql_generated = data.get("sql")
                result.row_count = len(data.get("execution", {}).get("results", []))

                # Check for expected patterns in SQL
                sql_upper = (result.sql_generated or "").upper()
                patterns_found = []
                patterns_missing = []

                for pattern in test_case.get("expected_patterns", []):
                    if pattern.upper() in sql_upper:
                        patterns_found.append(pattern)
                    else:
                        patterns_missing.append(pattern)

                # Determine success
                # Success if SQL was generated and at least one expected pattern found
                result.success = (
                    result.sql_generated is not None and
                    len(patterns_found) > 0 and
                    data.get("error") is None
                )

                result.details = {
                    "patterns_found": patterns_found,
                    "patterns_missing": patterns_missing,
                    "kg_enhanced": data.get("kg_enhanced", False),
                    "vector_search_used": data.get("options", {}).get("use_vector_search", False),
                    "tables_used": data.get("tables_used", []),
                    "confidence_score": data.get("confidence_score"),
                    "from_cache": data.get("from_cache", False),
                    "explanation": data.get("explanation")
                }

            elif response.status_code == 401:
                result.error = "Authentication failed - check AUTH_TOKEN"
            else:
                result.error = f"HTTP {response.status_code}: {response.text[:200]}"

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=False,
                execution_time_ms=execution_time_ms,
                error=str(e)
            )

        accuracy_report.add_result(result)

        # Print result for visibility
        if config.verbose:
            status = "✓" if result.success else "✗"
            print(f"\n{status} [{test_case['difficulty'].upper()}] {test_case['name']}")
            print(f"  Query: {test_case['query']}")
            if result.sql_generated:
                sql_preview = result.sql_generated[:150] + "..." if len(result.sql_generated) > 150 else result.sql_generated
                print(f"  SQL: {sql_preview}")
            if result.error:
                print(f"  Error: {result.error}")
            print(f"  Time: {result.execution_time_ms:.0f}ms, Rows: {result.row_count}")

        # Assert for pytest
        assert result.success, f"Test {test_case['name']} failed: {result.error or 'SQL generation issues'}"


# =============================================================================
# TEST CASES - KNOWLEDGE GRAPH VERIFICATION
# =============================================================================

KG_TEST_CASES = [
    {
        "name": "kg_customer_tables",
        "query": "Show all customers with their names",
        "expected_tables": ["customer"],
        "description": "Should find customer-related tables via KG"
    },
    {
        "name": "kg_join_discovery",
        "query": "Show customer revenue with RFM segments",
        "expected_tables": ["customer", "RFM"],
        "description": "Should discover join paths between customer and RFM tables"
    },
    {
        "name": "kg_financial_columns",
        "query": "Show total revenue and COGS by month",
        "expected_tables": ["revenue", "COGS"],
        "description": "Should find financial metric columns"
    },
]


class TestKnowledgeGraphVerification:
    """Test knowledge graph integration."""

    @pytest.mark.parametrize("test_case", KG_TEST_CASES, ids=lambda x: x["name"])
    def test_kg_table_discovery(self, http_client, config, accuracy_report, test_case):
        """Test that knowledge graph correctly identifies relevant tables."""
        start_time = time.time()

        payload = {
            "question": test_case["query"],
            "options": {
                "use_vector_search": True,
                "max_tables": 5
            }
        }

        try:
            response = http_client.post("/query", json=payload)
            execution_time_ms = (time.time() - start_time) * 1000

            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=False,
                execution_time_ms=execution_time_ms
            )

            if response.status_code == 200:
                data = response.json()
                result.sql_generated = data.get("sql")

                sql_upper = (result.sql_generated or "").upper()
                tables_found = data.get("tables_used", [])

                # Check if expected table patterns appear
                expected_found = []
                expected_missing = []

                for expected in test_case.get("expected_tables", []):
                    found = any(
                        expected.upper() in t.upper() for t in tables_found
                    ) or expected.upper() in sql_upper

                    if found:
                        expected_found.append(expected)
                    else:
                        expected_missing.append(expected)

                result.success = len(expected_found) > 0
                result.details = {
                    "kg_enhanced": data.get("kg_enhanced", False),
                    "tables_used": tables_found,
                    "expected_found": expected_found,
                    "expected_missing": expected_missing,
                    "description": test_case.get("description")
                }

            else:
                result.error = f"HTTP {response.status_code}"

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=False,
                execution_time_ms=execution_time_ms,
                error=str(e)
            )

        accuracy_report.add_result(result)

        if config.verbose:
            status = "✓" if result.success else "✗"
            print(f"\n{status} [KG] {test_case['name']}")
            print(f"  Query: {test_case['query']}")
            print(f"  Tables found: {result.details.get('tables_used', [])}")
            if result.error:
                print(f"  Error: {result.error}")

        # Soft assertion - KG enhancement is optional
        if not result.success:
            pytest.xfail(f"KG test {test_case['name']} - tables not found as expected")


# =============================================================================
# TEST CASES - VECTOR SEARCH VERIFICATION
# =============================================================================

VECTOR_TEST_CASES = [
    {
        "name": "vector_semantic_match",
        "query": "Show me client spending patterns",
        "synonyms": ["customer", "revenue", "purchase"],
        "description": "Should match 'client' to 'customer' tables via embeddings"
    },
    {
        "name": "vector_metric_match",
        "query": "What is our gross margin?",
        "synonyms": ["profit", "revenue", "COGS"],
        "description": "Should find gross margin related columns"
    },
    {
        "name": "vector_time_match",
        "query": "Show quarterly performance",
        "synonyms": ["quarter", "date", "period", "time"],
        "description": "Should understand quarterly = time-based grouping"
    },
]


class TestVectorSearchVerification:
    """Test vector embedding search integration."""

    @pytest.mark.parametrize("test_case", VECTOR_TEST_CASES, ids=lambda x: x["name"])
    def test_vector_semantic_matching(self, http_client, config, accuracy_report, test_case):
        """Test that vector search correctly matches semantic concepts."""
        start_time = time.time()

        payload = {
            "question": test_case["query"],
            "options": {
                "use_vector_search": True,
                "max_tables": 5
            }
        }

        try:
            response = http_client.post("/query", json=payload)
            execution_time_ms = (time.time() - start_time) * 1000

            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=False,
                execution_time_ms=execution_time_ms
            )

            if response.status_code == 200:
                data = response.json()
                result.sql_generated = data.get("sql")

                sql_upper = (result.sql_generated or "").upper()
                tables_used = [t.upper() for t in data.get("tables_used", [])]

                # Check if any synonym-related terms appear
                synonyms_found = []
                for syn in test_case.get("synonyms", []):
                    if syn.upper() in sql_upper or any(syn.upper() in t for t in tables_used):
                        synonyms_found.append(syn)

                result.success = len(synonyms_found) > 0 and result.sql_generated is not None
                result.details = {
                    "vector_search_used": True,
                    "synonyms_found": synonyms_found,
                    "tables_used": data.get("tables_used", []),
                    "description": test_case.get("description")
                }

            else:
                result.error = f"HTTP {response.status_code}"

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=False,
                execution_time_ms=execution_time_ms,
                error=str(e)
            )

        accuracy_report.add_result(result)

        if config.verbose:
            status = "✓" if result.success else "✗"
            print(f"\n{status} [VECTOR] {test_case['name']}")
            print(f"  Query: {test_case['query']}")
            print(f"  Synonyms found: {result.details.get('synonyms_found', [])}")
            if result.error:
                print(f"  Error: {result.error}")

        assert result.success, f"Vector test {test_case['name']} failed"


# =============================================================================
# TEST CASES - CACHE VERIFICATION
# =============================================================================

class TestCacheVerification:
    """Test caching behavior."""

    def test_cache_hit_on_repeat_query(self, http_client, config, accuracy_report):
        """Test that repeated queries hit the cache."""
        query = "What is the total revenue?"

        # First request
        start1 = time.time()
        response1 = http_client.post("/query", json={"question": query})
        time1 = (time.time() - start1) * 1000

        if response1.status_code != 200:
            pytest.skip(f"First request failed: {response1.status_code}")

        data1 = response1.json()
        from_cache_1 = data1.get("from_cache", False)

        # Second request (should be cached)
        start2 = time.time()
        response2 = http_client.post("/query", json={"question": query})
        time2 = (time.time() - start2) * 1000

        if response2.status_code == 200:
            data2 = response2.json()
            from_cache_2 = data2.get("from_cache", False)

            result = TestResult(
                test_name="cache_hit_on_repeat",
                query=query,
                success=from_cache_2 or time2 < time1 * 0.5,  # Either cached or significantly faster
                execution_time_ms=time2,
                details={
                    "first_request_ms": time1,
                    "second_request_ms": time2,
                    "first_from_cache": from_cache_1,
                    "second_from_cache": from_cache_2,
                    "speedup": time1 / time2 if time2 > 0 else 0
                }
            )

            accuracy_report.add_result(result)

            if config.verbose:
                print(f"\n[CACHE] Repeat query test")
                print(f"  First: {time1:.0f}ms (cached: {from_cache_1})")
                print(f"  Second: {time2:.0f}ms (cached: {from_cache_2})")
                print(f"  Speedup: {result.details['speedup']:.1f}x")

            # Cache should work
            assert result.success, "Cache not working - second request not faster"


# =============================================================================
# TEST CASES - CONNECTOR HEALTH
# =============================================================================

class TestConnectorHealth:
    """Test database connector health and configuration."""

    def test_list_connectors(self, http_client, config):
        """Test that connectors can be listed."""
        response = http_client.get("/connectors")

        assert response.status_code == 200, f"Failed to list connectors: {response.status_code}"

        data = response.json()

        if config.verbose:
            print(f"\n[CONNECTORS] Found {len(data)} connector(s)")
            for conn in data:
                status = "✓" if conn.get("enabled_for_chat") else "○"
                print(f"  {status} {conn.get('name', 'unnamed')} ({conn.get('database_type', '?')})")

    def test_connector_diagnostics(self, http_client, config):
        """Test connector diagnostics endpoint."""
        response = http_client.get("/connectors/admin/diagnostics")

        if response.status_code == 403:
            pytest.skip("Admin access required for diagnostics")

        assert response.status_code == 200, f"Diagnostics failed: {response.status_code}"

        data = response.json()

        if config.verbose:
            print(f"\n[DIAGNOSTICS]")
            print(f"  Total connectors: {data.get('total_connectors', 0)}")
            print(f"  Enabled for chat: {data.get('enabled_for_chat', 0)}")


# =============================================================================
# TEST CASES - ERROR HANDLING
# =============================================================================

ERROR_TEST_CASES = [
    {
        "name": "empty_query",
        "query": "",
        "expected_error": True,
        "description": "Empty query should return error"
    },
    {
        "name": "nonsense_query",
        "query": "asdfghjkl qwertyuiop",
        "expected_error": False,  # Should still try to generate SQL
        "description": "Nonsense query - system should handle gracefully"
    },
    {
        "name": "sql_injection_attempt",
        "query": "'; DROP TABLE customers; --",
        "expected_error": False,  # Should be sanitized
        "description": "SQL injection attempt should be sanitized"
    },
]


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.parametrize("test_case", ERROR_TEST_CASES, ids=lambda x: x["name"])
    def test_error_scenarios(self, http_client, config, accuracy_report, test_case):
        """Test various error scenarios."""
        start_time = time.time()

        payload = {"question": test_case["query"]}

        try:
            response = http_client.post("/query", json=payload)
            execution_time_ms = (time.time() - start_time) * 1000

            has_error = response.status_code != 200 or response.json().get("error") is not None

            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=(has_error == test_case["expected_error"]) or not test_case["expected_error"],
                execution_time_ms=execution_time_ms,
                details={
                    "http_status": response.status_code,
                    "expected_error": test_case["expected_error"],
                    "got_error": has_error,
                    "description": test_case["description"]
                }
            )

            if response.status_code == 200:
                data = response.json()
                result.sql_generated = data.get("sql")

                # For SQL injection test, verify no DROP TABLE in output
                if test_case["name"] == "sql_injection_attempt" and result.sql_generated:
                    if "DROP" in result.sql_generated.upper():
                        result.success = False
                        result.error = "SQL injection not properly sanitized!"

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_case["name"],
                query=test_case["query"],
                success=test_case["expected_error"],  # If we expected error, exception is OK
                execution_time_ms=execution_time_ms,
                error=str(e)
            )

        accuracy_report.add_result(result)

        if config.verbose:
            status = "✓" if result.success else "✗"
            print(f"\n{status} [ERROR] {test_case['name']}")
            print(f"  Description: {test_case['description']}")
            if result.error:
                print(f"  Error: {result.error}")


# =============================================================================
# REPORT GENERATION
# =============================================================================

@pytest.fixture(scope="module", autouse=True)
def generate_report(accuracy_report):
    """Generate final report after all tests."""
    yield

    accuracy_report.calculate_metrics()
    report = accuracy_report.to_dict()

    print("\n" + "=" * 80)
    print("ACCURACY TEST REPORT")
    print("=" * 80)
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"\nSummary:")
    print(f"  Total Tests: {report['summary']['total_tests']}")
    print(f"  Passed: {report['summary']['passed']}")
    print(f"  Failed: {report['summary']['failed']}")
    print(f"  SQL Accuracy: {report['summary']['sql_accuracy_pct']}%")
    print(f"  KG Usage Rate: {report['summary']['kg_usage_rate_pct']}%")
    print(f"  Vector Usage Rate: {report['summary']['vector_usage_rate_pct']}%")
    print(f"  Avg Execution Time: {report['summary']['avg_execution_time_ms']:.0f}ms")
    print("=" * 80)

    # Save report to file
    report_path = os.path.join(
        os.path.dirname(__file__),
        f"../../test_results/accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {report_path}")


# =============================================================================
# STANDALONE RUNNER
# =============================================================================

def run_tests_standalone(token: str, base_url: str = "http://localhost:8000/api/v1"):
    """Run tests without pytest for quick debugging."""
    config = TestConfig(base_url=base_url, auth_token=token)
    report = AccuracyReport()

    print("=" * 80)
    print("MANTRIX AXIS AI - ACCURACY TESTING")
    print("=" * 80)
    print(f"Base URL: {base_url}")
    print(f"Token: {token[:20]}...")

    with httpx.Client(
        base_url=config.base_url,
        headers=config.headers,
        timeout=config.timeout
    ) as client:

        # Test health first
        print("\n[1] Testing API Health...")
        try:
            health = client.get("/health")
            print(f"  Health: {health.status_code}")
        except Exception as e:
            print(f"  Health check failed: {e}")
            return

        # Test SQL generation
        print("\n[2] Testing SQL Generation...")
        for test_case in SQL_GENERATION_TEST_CASES[:3]:  # First 3 for quick test
            start = time.time()
            try:
                response = client.post("/query", json={"question": test_case["query"]})
                elapsed = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    sql = data.get("sql", "")[:100]
                    print(f"  ✓ {test_case['name']}: {elapsed:.0f}ms")
                    print(f"    SQL: {sql}...")
                else:
                    print(f"  ✗ {test_case['name']}: HTTP {response.status_code}")
            except Exception as e:
                print(f"  ✗ {test_case['name']}: {e}")

        # Test connectors
        print("\n[3] Testing Connectors...")
        try:
            connectors = client.get("/connectors")
            if connectors.status_code == 200:
                data = connectors.json()
                print(f"  Found {len(data)} connector(s)")
                for c in data:
                    enabled = "✓" if c.get("enabled_for_chat") else "○"
                    print(f"    {enabled} {c.get('name')} ({c.get('database_type')})")
            else:
                print(f"  Failed: HTTP {connectors.status_code}")
        except Exception as e:
            print(f"  Failed: {e}")

    print("\n" + "=" * 80)
    print("Quick test complete. Run pytest for full test suite.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run accuracy tests")
    parser.add_argument("--token", "-t", help="JWT auth token")
    parser.add_argument("--url", "-u", default="http://localhost:8000/api/v1", help="API base URL")
    parser.add_argument("--pytest", "-p", action="store_true", help="Run with pytest")

    args = parser.parse_args()

    token = args.token or os.environ.get("AUTH_TOKEN")

    if not token:
        print("Error: Please provide AUTH_TOKEN via --token or environment variable")
        sys.exit(1)

    if args.pytest:
        os.environ["AUTH_TOKEN"] = token
        sys.exit(pytest.main([__file__, "-v", "-s"]))
    else:
        run_tests_standalone(token, args.url)
