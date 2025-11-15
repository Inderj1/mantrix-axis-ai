#!/usr/bin/env python3
"""
Phase 1 Implementation Tests
Tests for caching, timeouts, format normalization, and pagination

Run before/after Phase 1 implementation to verify everything works.

Usage:
    python test_phase1_implementation.py
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.bigquery import BigQueryClient
from src.core.cache_manager import CacheManager
from src.core.format_normalizer import FormatNormalizer
from src.core.sql_generator import SQLGenerator
from src.config import settings
import structlog

logger = structlog.get_logger()

# Test results tracker
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def log_test(test_name: str, status: str, details: str = ""):
    """Log test result"""
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"\n{icon} {test_name}")
    if details:
        print(f"   {details}")

    if status == "PASS":
        test_results["passed"].append(test_name)
    elif status == "FAIL":
        test_results["failed"].append((test_name, details))
    else:
        test_results["warnings"].append((test_name, details))


def test_cache_enabled():
    """Test 1.1: Verify caching is enabled"""
    print("\n" + "="*80)
    print("TEST 1.1: Cache Configuration")
    print("="*80)

    try:
        assert settings.cache_enabled == True, "CACHE_ENABLED should be True"
        assert settings.cache_sql_enabled == True, "CACHE_SQL_ENABLED should be True"
        assert settings.cache_schema_enabled == True, "CACHE_SCHEMA_ENABLED should be True"

        log_test("Cache Enabled", "PASS", "All cache flags are enabled")

        # Test Redis connection
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )

        # Test write/read
        test_key = "test:phase1:cache"
        test_value = {"test": "data", "timestamp": datetime.now().isoformat()}

        cache_manager.redis.setex(test_key, 60, str(test_value))
        retrieved = cache_manager.redis.get(test_key)

        assert retrieved is not None, "Failed to retrieve cached value"

        # Cleanup
        cache_manager.redis.delete(test_key)

        log_test("Redis Connection", "PASS", f"Connected to {settings.redis_host}:{settings.redis_port}")
        return True

    except Exception as e:
        log_test("Cache Configuration", "FAIL", str(e))
        return False


def test_query_timeout():
    """Test 1.2: Verify query timeout is configured"""
    print("\n" + "="*80)
    print("TEST 1.2: Query Timeout Configuration")
    print("="*80)

    try:
        assert hasattr(settings, 'bigquery_query_timeout_seconds'), "Missing timeout setting"
        assert settings.bigquery_query_timeout_seconds == 60, "Timeout should be 60 seconds"

        log_test("Timeout Configuration", "PASS", f"Timeout set to {settings.bigquery_query_timeout_seconds}s")

        # Test BigQuery client uses timeout
        bq_client = BigQueryClient()

        # Quick query to test timeout parameter
        query = f"""
        SELECT COUNT(*) as count
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.__TABLES__`
        """

        result = bq_client.execute_query(query, timeout=5)
        assert 'rows' in result, "Query should return results"

        log_test("Timeout Applied", "PASS", "Query executed with timeout parameter")
        return True

    except Exception as e:
        log_test("Query Timeout", "FAIL", str(e))
        return False


def test_format_normalizer_initialization():
    """Test 1.3: Verify format normalizer initializes correctly"""
    print("\n" + "="*80)
    print("TEST 1.3: Format Normalizer Initialization")
    print("="*80)

    try:
        bq_client = BigQueryClient()
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )

        normalizer = FormatNormalizer(bq_client, cache_manager)

        assert normalizer is not None, "Normalizer should initialize"
        assert normalizer.bq_client is not None, "BigQuery client should be set"
        assert normalizer.cache_manager is not None, "Cache manager should be set"

        log_test("Format Normalizer Init", "PASS", "Initialized successfully")
        return normalizer

    except Exception as e:
        log_test("Format Normalizer Init", "FAIL", str(e))
        return None


def test_format_detection(normalizer: FormatNormalizer):
    """Test 1.4: Test format detection on sample table"""
    print("\n" + "="*80)
    print("TEST 1.4: Format Detection")
    print("="*80)

    if not normalizer:
        log_test("Format Detection", "FAIL", "Normalizer not initialized")
        return False

    try:
        # Get first table from dataset
        tables = normalizer.bq_client.list_tables()
        if not tables:
            log_test("Format Detection", "WARN", "No tables found in dataset")
            return True

        test_table = tables[0]

        # Get schema to find a string column
        schema = normalizer.bq_client.get_table_schema(test_table)
        string_columns = [
            col['name'] for col in schema.get('columns', [])
            if col['type'] in ('STRING', 'VARCHAR', 'TEXT')
        ]

        if not string_columns:
            log_test("Format Detection", "WARN", f"No string columns in {test_table}")
            return True

        test_column = string_columns[0]

        # Detect format
        format_info = normalizer.detect_column_format(test_table, test_column)

        assert format_info is not None, "Should return format info"
        assert format_info.table_name == test_table, "Table name should match"
        assert format_info.column_name == test_column, "Column name should match"
        assert format_info.format_type is not None, "Should have format type"

        log_test(
            "Format Detection",
            "PASS",
            f"{test_table}.{test_column} = {format_info.format_type.value} "
            f"(leading zeros: {format_info.leading_zero_percentage:.1%})"
        )
        return True

    except Exception as e:
        log_test("Format Detection", "FAIL", str(e))
        return False


def test_join_normalization(normalizer: FormatNormalizer):
    """Test 1.5: Test JOIN normalization"""
    print("\n" + "="*80)
    print("TEST 1.5: JOIN Normalization")
    print("="*80)

    if not normalizer:
        log_test("JOIN Normalization", "FAIL", "Normalizer not initialized")
        return False

    try:
        # Test with sample JOIN query
        test_query = """
        SELECT t1.customer_id, t2.order_id
        FROM customers t1
        INNER JOIN orders t2 ON t1.customer_id = t2.customer_id
        LIMIT 10
        """

        # This should run without error (may or may not modify query)
        normalized_query = normalizer.normalize_join_query(test_query)

        assert normalized_query is not None, "Should return query"
        assert "JOIN" in normalized_query.upper(), "Should preserve JOIN"

        if normalized_query != test_query:
            log_test(
                "JOIN Normalization",
                "PASS",
                "Query was normalized (format mismatch detected)"
            )
        else:
            log_test(
                "JOIN Normalization",
                "PASS",
                "Query unchanged (no format mismatch)"
            )
        return True

    except Exception as e:
        log_test("JOIN Normalization", "FAIL", str(e))
        return False


def test_pagination():
    """Test 1.6: Test pagination functionality"""
    print("\n" + "="*80)
    print("TEST 1.6: Pagination")
    print("="*80)

    try:
        bq_client = BigQueryClient()

        # Get a table with data
        tables = bq_client.list_tables()
        if not tables:
            log_test("Pagination", "WARN", "No tables to test pagination")
            return True

        test_table = tables[0]

        # Test pagination with small page size
        query = f"""
        SELECT *
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.{test_table}`
        LIMIT 100
        """

        # First page
        result = bq_client.execute_query(query, page_size=10)

        assert 'rows' in result, "Should have rows"
        assert 'total_rows' in result, "Should have total_rows"
        assert 'has_more' in result, "Should have has_more flag"
        assert 'page_info' in result, "Should have page_info"

        first_page_rows = len(result['rows'])
        has_more = result.get('has_more', False)
        next_token = result.get('next_page_token')

        log_test(
            "Pagination - First Page",
            "PASS",
            f"Fetched {first_page_rows} rows, has_more={has_more}"
        )

        # Test second page if available
        if has_more and next_token:
            result2 = bq_client.execute_query(query, page_size=10, page_token=next_token)
            second_page_rows = len(result2['rows'])

            log_test(
                "Pagination - Second Page",
                "PASS",
                f"Fetched {second_page_rows} more rows"
            )

        return True

    except Exception as e:
        log_test("Pagination", "FAIL", str(e))
        return False


def test_sql_generator_integration():
    """Test 1.7: Test SQL generator with all Phase 1 features"""
    print("\n" + "="*80)
    print("TEST 1.7: SQL Generator Integration")
    print("="*80)

    try:
        generator = SQLGenerator()

        # Check format normalizer is initialized
        assert hasattr(generator, 'format_normalizer'), "Should have format_normalizer"
        if generator.format_normalizer:
            log_test("Format Normalizer in Generator", "PASS", "Integrated successfully")
        else:
            log_test("Format Normalizer in Generator", "WARN", "Not initialized")

        # Check cache manager
        assert hasattr(generator, 'cache_manager'), "Should have cache_manager"
        if generator.cache_manager:
            log_test("Cache Manager in Generator", "PASS", "Integrated successfully")
        else:
            log_test("Cache Manager in Generator", "FAIL", "Not initialized")
            return False

        # Test simple query generation
        test_query = "Show me the first 5 tables"

        result = generator.generate_sql(test_query)

        assert 'sql' in result or 'error' in result, "Should return SQL or error"

        if 'sql' in result and result['sql']:
            log_test("SQL Generation", "PASS", f"Generated: {result['sql'][:60]}...")

            # Check if format normalization flag is present
            if 'format_normalized' in result:
                log_test(
                    "Format Normalization Flag",
                    "PASS",
                    f"format_normalized={result['format_normalized']}"
                )
        else:
            log_test("SQL Generation", "WARN", f"Error: {result.get('error', 'Unknown')}")

        return True

    except Exception as e:
        log_test("SQL Generator Integration", "FAIL", str(e))
        return False


def test_performance_baseline():
    """Test 1.8: Establish performance baseline"""
    print("\n" + "="*80)
    print("TEST 1.8: Performance Baseline")
    print("="*80)

    try:
        bq_client = BigQueryClient()
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )

        # Test 1: Simple query performance
        query = f"""
        SELECT COUNT(*) as table_count
        FROM `{bq_client.project_id}.{bq_client.dataset_id}.__TABLES__`
        """

        start = time.time()
        result = bq_client.execute_query(query)
        duration = (time.time() - start) * 1000

        log_test(
            "Simple Query Performance",
            "PASS",
            f"{duration:.0f}ms for COUNT(*) on __TABLES__"
        )

        # Test 2: Cache hit/miss
        test_key = "test:performance:cache"
        test_data = {"test": "data" * 100}

        # Write
        start = time.time()
        cache_manager.redis.setex(test_key, 60, str(test_data))
        write_time = (time.time() - start) * 1000

        # Read
        start = time.time()
        cache_manager.redis.get(test_key)
        read_time = (time.time() - start) * 1000

        cache_manager.redis.delete(test_key)

        log_test(
            "Cache Performance",
            "PASS",
            f"Write: {write_time:.2f}ms, Read: {read_time:.2f}ms"
        )

        return True

    except Exception as e:
        log_test("Performance Baseline", "FAIL", str(e))
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total = len(test_results["passed"]) + len(test_results["failed"]) + len(test_results["warnings"])
    passed = len(test_results["passed"])
    failed = len(test_results["failed"])
    warnings = len(test_results["warnings"])

    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")

    if failed > 0:
        print("\nFailed Tests:")
        for test_name, details in test_results["failed"]:
            print(f"  ❌ {test_name}: {details}")

    if warnings > 0:
        print("\nWarnings:")
        for test_name, details in test_results["warnings"]:
            print(f"  ⚠️  {test_name}: {details}")

    print("\n" + "="*80)

    # Exit code
    return 0 if failed == 0 else 1


def main():
    """Run all Phase 1 tests"""
    print("="*80)
    print("PHASE 1 IMPLEMENTATION TESTS")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: {settings.google_cloud_project}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print("="*80)

    # Run tests in order
    test_cache_enabled()
    test_query_timeout()

    normalizer = test_format_normalizer_initialization()
    test_format_detection(normalizer)
    test_join_normalization(normalizer)

    test_pagination()
    test_sql_generator_integration()
    test_performance_baseline()

    # Print summary
    exit_code = print_summary()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
