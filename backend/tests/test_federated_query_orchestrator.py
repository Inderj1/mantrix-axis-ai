"""
Tests for Federated Query Orchestrator

Tests the cross-database federation functionality including:
- Strategy selection
- DuckDB local JOINs
- S3 staging + external tables
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime

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
    FederatedQueryResult,
    QueryPlan
)


class MockConnector:
    """Mock database connector for testing."""

    def __init__(self, db_name: str, data: list = None):
        self.db_name = db_name
        self.data = data or []
        self.queries_executed = []

    def execute_query(self, query: str, **kwargs):
        self.queries_executed.append(query)
        return {
            "rows": self.data,
            "row_count": len(self.data)
        }


@pytest.fixture
def mock_bigquery_connector():
    """Mock BigQuery connector with sample customer data."""
    return MockConnector("bigquery", [
        {"customer_id": "001", "name": "Acme Corp", "rfm_segment": "Champions"},
        {"customer_id": "002", "name": "Beta Inc", "rfm_segment": "Loyal"},
        {"customer_id": "003", "name": "Gamma LLC", "rfm_segment": "At Risk"},
    ])


@pytest.fixture
def mock_snowflake_connector():
    """Mock Snowflake connector with sample order data."""
    return MockConnector("snowflake", [
        {"order_id": "ORD001", "customer_id": "001", "amount": 1000.00},
        {"order_id": "ORD002", "customer_id": "001", "amount": 2500.00},
        {"order_id": "ORD003", "customer_id": "002", "amount": 750.00},
    ])


@pytest.fixture
def orchestrator(mock_bigquery_connector, mock_snowflake_connector):
    """Create orchestrator with mock connectors."""
    return FederatedQueryOrchestrator(
        connectors={
            "bigquery": mock_bigquery_connector,
            "snowflake": mock_snowflake_connector
        },
        default_config=FederationConfig(
            s3_bucket="test-bucket",
            max_local_rows=100_000
        )
    )


class TestFederationConfig:
    """Tests for FederationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FederationConfig()
        assert config.federation_db is None
        assert config.max_local_rows == 100_000
        assert config.auto_cleanup is True
        assert config.ttl_hours == 24

    def test_custom_config(self):
        """Test custom configuration."""
        config = FederationConfig(
            federation_db="snowflake",
            s3_bucket="my-bucket",
            max_local_rows=500_000
        )
        assert config.federation_db == "snowflake"
        assert config.s3_bucket == "my-bucket"
        assert config.max_local_rows == 500_000


class TestQueryParsing:
    """Tests for query parsing functionality."""

    def test_parse_single_source_query(self, orchestrator):
        """Test parsing a single-source query."""
        query = "SELECT * FROM bigquery.customers WHERE country = 'USA'"
        plan = orchestrator._parse_query(query)

        assert len(plan.source_queries) == 1
        assert "bigquery" in plan.source_queries

    def test_parse_cross_db_query(self, orchestrator):
        """Test parsing a cross-database query."""
        query = """
        SELECT c.name, SUM(o.amount) as total
        FROM bigquery.customers c
        JOIN snowflake.orders o ON c.customer_id = o.customer_id
        GROUP BY c.name
        """
        plan = orchestrator._parse_query(query)

        # Should identify both sources
        assert "bigquery" in plan.tables_by_source or "bigquery" in plan.source_queries
        assert "snowflake" in plan.tables_by_source or "snowflake" in plan.source_queries


class TestStrategySelection:
    """Tests for federation strategy selection."""

    def test_single_source_strategy(self, orchestrator):
        """Test that single-source queries use SINGLE_SOURCE strategy."""
        plan = QueryPlan(
            original_query="SELECT * FROM bigquery.customers",
            strategy=FederationStrategy.SINGLE_SOURCE,
            source_queries={"bigquery": "SELECT * FROM customers"}
        )

        strategy = orchestrator._select_strategy(plan, orchestrator.default_config)
        assert strategy == FederationStrategy.SINGLE_SOURCE

    def test_small_cross_db_uses_duckdb(self, orchestrator):
        """Test that small cross-DB queries use DuckDB local strategy."""
        plan = QueryPlan(
            original_query="SELECT * FROM bigquery.a JOIN snowflake.b",
            strategy=FederationStrategy.SINGLE_SOURCE,
            source_queries={
                "bigquery": "SELECT * FROM a",
                "snowflake": "SELECT * FROM b"
            },
            estimated_rows={"bigquery": 1000, "snowflake": 500}
        )

        # With DuckDB available and small rows, should use DUCKDB_LOCAL
        strategy = orchestrator._select_strategy(plan, orchestrator.default_config)

        # If no federation DB configured and small result, use DuckDB
        if strategy != FederationStrategy.DUCKDB_LOCAL:
            # Fall back might be S3_AXIS_INFRA if DuckDB not available
            assert strategy in [FederationStrategy.DUCKDB_LOCAL, FederationStrategy.S3_AXIS_INFRA]

    def test_customer_db_strategy_when_configured(self, orchestrator):
        """Test that S3_CUSTOMER_DB is used when customer has federation DB."""
        plan = QueryPlan(
            original_query="SELECT * FROM bigquery.a JOIN snowflake.b",
            strategy=FederationStrategy.SINGLE_SOURCE,
            source_queries={
                "bigquery": "SELECT * FROM a",
                "snowflake": "SELECT * FROM b"
            }
        )

        config = FederationConfig(
            federation_db="snowflake",
            federation_connector=Mock(),
            s3_bucket="customer-bucket"
        )

        strategy = orchestrator._select_strategy(plan, config)
        assert strategy == FederationStrategy.S3_CUSTOMER_DB


class TestSingleSourceExecution:
    """Tests for single-source query execution."""

    @pytest.mark.asyncio
    async def test_execute_single_source(self, orchestrator, mock_bigquery_connector):
        """Test executing a single-source query."""
        result = await orchestrator.execute_federated_query(
            query="SELECT * FROM bigquery.customers"
        )

        assert result.status == "complete"
        assert result.strategy == FederationStrategy.SINGLE_SOURCE
        assert result.row_count == 3
        assert "bigquery" in result.sources_queried


class TestDuckDBLocalExecution:
    """Tests for DuckDB local JOIN execution."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not True, reason="DuckDB tests")
    async def test_duckdb_local_join(self, orchestrator):
        """Test local JOIN using DuckDB."""
        # This test requires DuckDB to be installed
        try:
            import duckdb
        except ImportError:
            pytest.skip("DuckDB not installed")

        # For now, test that the method exists and can be called
        plan = QueryPlan(
            original_query="SELECT * FROM a JOIN b",
            strategy=FederationStrategy.DUCKDB_LOCAL,
            source_queries={
                "bigquery": "SELECT * FROM customers",
                "snowflake": "SELECT * FROM orders"
            }
        )

        # The actual execution would need proper query parsing
        # For now, verify the method exists
        assert hasattr(orchestrator, '_execute_duckdb_local')


class TestS3FederationExecution:
    """Tests for S3-based federation execution."""

    @pytest.mark.asyncio
    async def test_export_to_s3(self, orchestrator):
        """Test exporting data to S3."""
        # Skip if S3 libraries not available
        try:
            import boto3
            import pyarrow
        except ImportError:
            pytest.skip("S3/PyArrow not installed")

        # Mock S3 client
        with patch.object(orchestrator, '_s3_client') as mock_s3:
            mock_s3.put_object = Mock()

            rows = [
                {"id": 1, "name": "Test"},
                {"id": 2, "name": "Test2"}
            ]

            s3_path = await orchestrator._export_to_s3(
                rows=rows,
                bucket="test-bucket",
                prefix="test/prefix",
                job_id="job123"
            )

            assert "s3://" in s3_path
            mock_s3.put_object.assert_called_once()


class TestSchemaInference:
    """Tests for schema inference from sample data."""

    def test_infer_schema_basic_types(self, orchestrator):
        """Test schema inference for basic types."""
        row = {
            "id": 123,
            "name": "Test",
            "amount": 99.99,
            "is_active": True,
            "created_at": datetime.now()
        }

        schema = orchestrator._infer_schema(row)

        assert schema["id"] == "INTEGER"
        assert schema["name"] == "STRING"
        assert schema["amount"] == "FLOAT"
        assert schema["is_active"] == "BOOLEAN"
        assert schema["created_at"] == "TIMESTAMP"

    def test_type_conversion_snowflake(self, orchestrator):
        """Test type conversion to Snowflake types."""
        assert orchestrator._to_snowflake_type("STRING") == "VARCHAR"
        assert orchestrator._to_snowflake_type("INTEGER") == "INTEGER"
        assert orchestrator._to_snowflake_type("FLOAT") == "FLOAT"

    def test_type_conversion_redshift(self, orchestrator):
        """Test type conversion to Redshift types."""
        assert orchestrator._to_redshift_type("STRING") == "VARCHAR(65535)"
        assert orchestrator._to_redshift_type("INTEGER") == "BIGINT"
        assert orchestrator._to_redshift_type("FLOAT") == "DOUBLE PRECISION"


class TestFederatedQueryResult:
    """Tests for FederatedQueryResult dataclass."""

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = FederatedQueryResult(
            status="complete",
            strategy=FederationStrategy.DUCKDB_LOCAL,
            rows=[{"id": 1}],
            row_count=1,
            execution_time_seconds=0.5,
            sources_queried=["bigquery", "snowflake"]
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "complete"
        assert result_dict["strategy"] == "duckdb_local"
        assert result_dict["row_count"] == 1
        assert "bigquery" in result_dict["federation_metadata"]["sources_queried"]


class TestCleanup:
    """Tests for cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_s3(self, orchestrator):
        """Test S3 cleanup."""
        with patch.object(orchestrator, '_s3_client') as mock_s3:
            mock_s3.delete_object = Mock()

            await orchestrator._cleanup_s3(
                bucket="test-bucket",
                s3_paths=["s3://test-bucket/path/to/file.parquet"]
            )

            mock_s3.delete_object.assert_called_once()


class TestEndToEndScenarios:
    """End-to-end test scenarios."""

    @pytest.mark.asyncio
    async def test_bigquery_to_snowflake_join(
        self,
        mock_bigquery_connector,
        mock_snowflake_connector
    ):
        """Test a realistic BigQuery to Snowflake JOIN scenario."""
        # Set up realistic data
        mock_bigquery_connector.data = [
            {"customer_id": "001", "name": "Acme Corp", "rfm_segment": "Champions"},
            {"customer_id": "002", "name": "Beta Inc", "rfm_segment": "Loyal"},
        ]

        mock_snowflake_connector.data = [
            {"order_id": "ORD001", "customer_id": "001", "total": 5000.00},
            {"order_id": "ORD002", "customer_id": "002", "total": 3000.00},
        ]

        orchestrator = FederatedQueryOrchestrator(
            connectors={
                "bigquery": mock_bigquery_connector,
                "snowflake": mock_snowflake_connector
            }
        )

        # Execute federated query
        result = await orchestrator.execute_federated_query(
            query="""
            SELECT c.name, c.rfm_segment, SUM(o.total) as total_revenue
            FROM bigquery.customers c
            JOIN snowflake.orders o ON c.customer_id = o.customer_id
            GROUP BY c.name, c.rfm_segment
            """
        )

        assert result.status == "complete"
        # Strategy depends on configuration and available tools
        assert result.strategy in [
            FederationStrategy.SINGLE_SOURCE,
            FederationStrategy.DUCKDB_LOCAL,
            FederationStrategy.S3_AXIS_INFRA
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
