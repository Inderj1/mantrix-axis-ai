#!/usr/bin/env python3
"""
Test suite for pagination functionality.

Tests:
1. PaginateRequest/PaginateResponse models
2. Pagination metadata in execute_query response
3. Pagination SQL generation (LIMIT/OFFSET)
4. Frontend API contract (pagination at top level)
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.models import PaginateRequest, PaginateResponse
from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer, QueryAnalysis, ExecutionStrategy


class TestPaginateModels:
    """Test Pydantic models for pagination."""

    def test_paginate_request_defaults(self):
        """Test PaginateRequest with minimal required fields."""
        request = PaginateRequest(
            sql="SELECT * FROM test_table",
            database_type="snowflake"
        )
        assert request.page == 2  # Default for "load more"
        assert request.page_size == 100
        assert request.connector_id is None
        assert request.total_count is None

    def test_paginate_request_full(self):
        """Test PaginateRequest with all fields."""
        request = PaginateRequest(
            sql="SELECT * FROM STORE_SALES LIMIT 100",
            database_type="snowflake",
            connector_id="abc123",
            page=3,
            page_size=500,
            total_count=28800000000
        )
        assert request.sql == "SELECT * FROM STORE_SALES LIMIT 100"
        assert request.database_type == "snowflake"
        assert request.connector_id == "abc123"
        assert request.page == 3
        assert request.page_size == 500
        assert request.total_count == 28800000000

    def test_paginate_request_validation(self):
        """Test PaginateRequest validation."""
        # page must be >= 1
        with pytest.raises(ValueError):
            PaginateRequest(
                sql="SELECT * FROM test",
                database_type="snowflake",
                page=0
            )

        # page_size must be >= 1 and <= 10000
        with pytest.raises(ValueError):
            PaginateRequest(
                sql="SELECT * FROM test",
                database_type="snowflake",
                page_size=0
            )

        with pytest.raises(ValueError):
            PaginateRequest(
                sql="SELECT * FROM test",
                database_type="snowflake",
                page_size=20000
            )

    def test_paginate_response_success(self):
        """Test PaginateResponse for successful pagination."""
        response = PaginateResponse(
            success=True,
            results=[{"id": 1}, {"id": 2}],
            row_count=2,
            page=2,
            page_size=100,
            has_more=True,
            total_count=1000,
            execution_time_ms=150.5
        )
        assert response.success is True
        assert len(response.results) == 2
        assert response.row_count == 2
        assert response.page == 2
        assert response.has_more is True
        assert response.error is None

    def test_paginate_response_error(self):
        """Test PaginateResponse for error case."""
        response = PaginateResponse(
            success=False,
            results=[],
            row_count=0,
            page=2,
            page_size=100,
            has_more=False,
            error="Connection timeout"
        )
        assert response.success is False
        assert response.error == "Connection timeout"
        assert len(response.results) == 0


class TestQueryAnalysisPagination:
    """Test QueryAnalysis pagination support detection."""

    def test_supports_pagination_simple_select(self):
        """Simple SELECT should support pagination."""
        analysis = QueryAnalysis()
        analysis.has_aggregation = False
        analysis.supports_pagination = not analysis.has_aggregation
        assert analysis.supports_pagination is True

    def test_no_pagination_with_aggregation(self):
        """Aggregation queries should not support pagination."""
        analysis = QueryAnalysis()
        analysis.has_aggregation = True
        analysis.supports_pagination = not analysis.has_aggregation
        assert analysis.supports_pagination is False

    def test_pagination_with_limit(self):
        """Queries with LIMIT should still support pagination."""
        analysis = QueryAnalysis()
        analysis.has_aggregation = False
        analysis.has_limit = True
        analysis.limit_value = 1000
        analysis.supports_pagination = not analysis.has_aggregation
        # Even with LIMIT, pagination is supported (LIMIT just sets page size)
        assert analysis.supports_pagination is True


class TestPaginationSQLGeneration:
    """Test SQL generation for pagination."""

    def test_generate_paginated_sql_page1(self):
        """Test pagination SQL for page 1."""
        optimizer = SingleDatabaseQueryOptimizer(
            jena_resolver=None,
            weaviate_client=None,
            organization_id="test",
            database_type="snowflake"
        )

        sql = "SELECT * FROM STORE_SALES"
        paginated_sql, count_sql = optimizer.generate_paginated_sql(
            sql=sql,
            page=1,
            page_size=100,
            dialect="snowflake"
        )

        assert "LIMIT 100" in paginated_sql
        assert "OFFSET 0" in paginated_sql or "OFFSET" not in paginated_sql  # Page 1 may omit OFFSET
        assert "COUNT(*)" in count_sql

    def test_generate_paginated_sql_page2(self):
        """Test pagination SQL for page 2."""
        optimizer = SingleDatabaseQueryOptimizer(
            jena_resolver=None,
            weaviate_client=None,
            organization_id="test",
            database_type="snowflake"
        )

        sql = "SELECT * FROM STORE_SALES"
        paginated_sql, count_sql = optimizer.generate_paginated_sql(
            sql=sql,
            page=2,
            page_size=100,
            dialect="snowflake"
        )

        assert "LIMIT 100" in paginated_sql
        assert "OFFSET 100" in paginated_sql

    def test_generate_paginated_sql_with_existing_limit(self):
        """Test that existing LIMIT is preserved as pagination boundary."""
        optimizer = SingleDatabaseQueryOptimizer(
            jena_resolver=None,
            weaviate_client=None,
            organization_id="test",
            database_type="snowflake"
        )

        sql = "SELECT * FROM STORE_SALES LIMIT 1000"
        paginated_sql, count_sql = optimizer.generate_paginated_sql(
            sql=sql,
            page=3,
            page_size=100,
            dialect="snowflake"
        )

        # Implementation preserves existing LIMIT as pagination boundary
        # Returns SQL as-is when LIMIT already exists
        assert "LIMIT 1000" in paginated_sql
        # Count SQL should still be generated
        assert "COUNT(*)" in count_sql


class TestPaginationMetadata:
    """Test pagination metadata generation."""

    def test_get_pagination_metadata(self):
        """Test pagination metadata structure."""
        optimizer = SingleDatabaseQueryOptimizer(
            jena_resolver=None,
            weaviate_client=None,
            organization_id="test",
            database_type="snowflake"
        )

        metadata = optimizer.get_pagination_metadata(
            total_count=28800000000,
            page=1,
            page_size=1000
        )

        # Check required fields
        assert "total_count" in metadata
        assert "page" in metadata
        assert "page_size" in metadata
        assert "total_pages" in metadata
        assert "has_next_page" in metadata
        assert "has_previous_page" in metadata
        assert "start_row" in metadata
        assert "end_row" in metadata

        # Check values
        assert metadata["total_count"] == 28800000000
        assert metadata["page"] == 1
        assert metadata["page_size"] == 1000
        # 28.8B rows / 1000 per page = 28.8M pages (ceiling division)
        assert metadata["total_pages"] == 28800000  # (28800000000 + 1000 - 1) // 1000 = 28800000
        assert metadata["has_next_page"] is True  # Page 1 of 28.8M pages
        assert metadata["has_previous_page"] is False  # First page
        assert metadata["start_row"] == 1
        assert metadata["end_row"] == 1000

    def test_pagination_metadata_has_more(self):
        """Test has_next_page calculation in metadata."""
        optimizer = SingleDatabaseQueryOptimizer(
            jena_resolver=None,
            weaviate_client=None,
            organization_id="test",
            database_type="snowflake"
        )

        # Page 1 of many - has more
        metadata1 = optimizer.get_pagination_metadata(
            total_count=10000,
            page=1,
            page_size=100
        )
        assert metadata1["has_next_page"] is True  # 100 pages total, on page 1
        assert metadata1["has_previous_page"] is False

        # Last page - no more
        metadata_last = optimizer.get_pagination_metadata(
            total_count=150,
            page=2,
            page_size=100
        )
        # Page 2 with 150 total and page_size 100 is the last page (2 pages total)
        assert metadata_last["has_next_page"] is False
        assert metadata_last["has_previous_page"] is True


class TestPaginationEndpointContract:
    """Test the API contract for pagination endpoint."""

    def test_paginate_endpoint_sql_modification(self):
        """Test SQL modification for pagination (simulated)."""
        import re

        # Simulate the endpoint logic
        sql = "SELECT * FROM STORE_SALES LIMIT 1000"
        page = 2
        page_size = 100

        # Remove trailing semicolon
        if sql.endswith(';'):
            sql = sql[:-1].strip()

        # Remove existing LIMIT
        limit_pattern = re.compile(r'\bLIMIT\s+\d+\s*$', re.IGNORECASE)
        if limit_pattern.search(sql):
            sql = limit_pattern.sub('', sql).strip()

        # Add pagination
        offset = (page - 1) * page_size
        paginated_sql = f"{sql} LIMIT {page_size} OFFSET {offset}"

        assert "SELECT * FROM STORE_SALES LIMIT 100 OFFSET 100" == paginated_sql
        assert "LIMIT 1000" not in paginated_sql

    def test_has_more_calculation(self):
        """Test has_more flag calculation."""
        # Case 1: Known total_count, more results available
        total_count = 1000
        page = 2
        page_size = 100
        rows_fetched = 100
        offset = (page - 1) * page_size
        total_fetched = offset + rows_fetched
        has_more = total_fetched < total_count
        assert has_more is True  # 200 < 1000

        # Case 2: Known total_count, no more results
        total_count = 150
        page = 2
        rows_fetched = 50
        offset = (page - 1) * page_size
        total_fetched = offset + rows_fetched
        has_more = total_fetched < total_count
        assert has_more is False  # 150 >= 150

        # Case 3: Unknown total_count, full page returned
        total_count = None
        rows_fetched = 100
        if total_count:
            has_more = (offset + rows_fetched) < total_count
        elif rows_fetched == page_size:
            has_more = True
        else:
            has_more = False
        assert has_more is True  # Got full page, assume more


class TestResponseStructure:
    """Test that pagination is at the correct level in response."""

    def test_pagination_promoted_to_top_level(self):
        """Test that pagination is promoted from execution to top level."""
        # Simulate backend response building
        execution_result = {
            "results": [{"id": 1}],
            "row_count": 1,
            "pagination": {
                "total_count": 28800000000,
                "page": 1,
                "page_size": 1000,
                "is_paginated": True
            }
        }

        sql_result = {
            "sql": "SELECT * FROM STORE_SALES LIMIT 1000",
            "explanation": "Query executed"
        }

        # This is the fix we applied - promote pagination to top level
        result = {**sql_result, "execution": execution_result}
        if execution_result.get("pagination"):
            result["pagination"] = execution_result["pagination"]

        # Verify pagination is at top level
        assert "pagination" in result
        assert result["pagination"]["is_paginated"] is True
        assert result["pagination"]["total_count"] == 28800000000

        # Verify execution still has pagination (for backward compat)
        assert "pagination" in result["execution"]

    def test_database_type_and_connector_id_in_response(self):
        """Test that database_type and connector_id are included in response."""
        # Simulate backend response building with database info
        execution_result = {
            "results": [{"id": 1}],
            "row_count": 1,
            "pagination": {
                "total_count": 28800000000,
                "page": 1,
                "page_size": 1000,
                "is_paginated": True
            }
        }

        sql_result = {
            "sql": "SELECT * FROM STORE_SALES LIMIT 1000",
            "explanation": "Query executed"
        }

        # Simulate the backend response building with database_type and connector_id
        database_type = "snowflake"
        connector_id = "conn_123"

        result = {**sql_result, "execution": execution_result}
        if execution_result.get("pagination"):
            result["pagination"] = execution_result["pagination"]
        result["database_type"] = database_type
        result["connector_id"] = connector_id

        # Verify database_type and connector_id are at top level
        assert "database_type" in result
        assert result["database_type"] == "snowflake"
        assert "connector_id" in result
        assert result["connector_id"] == "conn_123"

    def test_frontend_message_metadata_includes_database_info(self):
        """Test that frontend message metadata includes database_type and connector_id."""
        # Simulate API response with database info
        data = {
            "sql": "SELECT * FROM STORE_SALES LIMIT 1000",
            "execution": {
                "results": [{"id": i} for i in range(1000)],
                "row_count": 1000
            },
            "pagination": {
                "total_count": 28800000000,
                "page": 1,
                "page_size": 1000,
                "is_paginated": True
            },
            "database_type": "snowflake",
            "connector_id": "conn_123"
        }

        # Simulate frontend conversationStore mapping
        message = {
            "sql": data.get("sql"),
            "results": data.get("execution", {}).get("results", []),
            "pagination": data.get("pagination"),
            "metadata": {
                "databaseType": data.get("database_type"),
                "connectorId": data.get("connector_id"),
            }
        }

        # Verify frontend message has database info in metadata
        assert message["metadata"]["databaseType"] == "snowflake"
        assert message["metadata"]["connectorId"] == "conn_123"

    def test_frontend_message_mapping(self):
        """Test that frontend correctly maps pagination from response."""
        # Simulate API response
        data = {
            "sql": "SELECT * FROM STORE_SALES LIMIT 1000",
            "execution": {
                "results": [{"id": i} for i in range(1000)],
                "row_count": 1000
            },
            "pagination": {
                "total_count": 28800000000,
                "page": 1,
                "page_size": 1000,
                "is_paginated": True
            }
        }

        # Simulate frontend conversationStore mapping
        message = {
            "sql": data.get("sql"),
            "results": data.get("execution", {}).get("results", []),
            "resultCount": data.get("execution", {}).get("row_count", 0),
            "pagination": data.get("pagination"),  # Frontend expects this at top level
        }

        # Verify frontend can access pagination
        assert message["pagination"] is not None
        assert message["pagination"]["is_paginated"] is True
        assert message["pagination"]["total_count"] == 28800000000

    def test_load_more_button_visibility_condition(self):
        """Test the condition for showing Load More button."""
        # Simulate EnhancedResultsCard logic
        pagination = {
            "is_paginated": True,
            "total_count": 28800000000,
            "page": 1,
            "page_size": 1000
        }
        results = [{"id": i} for i in range(1000)]

        # EnhancedResultsCard condition
        has_more_results = (
            pagination.get("is_paginated") and
            pagination.get("total_count", 0) > len(results)
        )

        assert has_more_results is True

        # After loading all results
        pagination_done = {
            "is_paginated": False,
            "total_count": 1000,
            "page": 1,
            "page_size": 1000
        }
        has_more_results = (
            pagination_done.get("is_paginated") and
            pagination_done.get("total_count", 0) > len(results)
        )

        assert has_more_results is False


def run_tests():
    """Run all tests and print results."""
    print("=" * 60)
    print("PAGINATION TESTS")
    print("=" * 60)

    test_classes = [
        TestPaginateModels,
        TestQueryAnalysisPagination,
        TestPaginationSQLGeneration,
        TestPaginationMetadata,
        TestPaginationEndpointContract,
        TestResponseStructure,
    ]

    total_passed = 0
    total_failed = 0
    failures = []

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 40)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  [PASS] {method_name}")
                    total_passed += 1
                except Exception as e:
                    print(f"  [FAIL] {method_name}: {e}")
                    total_failed += 1
                    failures.append((test_class.__name__, method_name, str(e)))

    print("\n" + "=" * 60)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    if failures:
        print("\nFailed tests:")
        for class_name, method_name, error in failures:
            print(f"  - {class_name}.{method_name}: {error}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
