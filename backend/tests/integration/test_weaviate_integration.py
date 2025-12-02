"""
Integration tests for WeaviateClient with real Weaviate.

These tests require Weaviate to be running on localhost:8082.
Run with: pytest tests/integration/test_weaviate_integration.py -v
"""

import pytest
import json
import time
from typing import Dict, Any, List


# Skip all tests if Weaviate is not available
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def weaviate_client():
    """Create a real WeaviateClient connected to Weaviate."""
    from src.db.weaviate_client import WeaviateClient
    from src.config import settings

    # Temporarily override settings for test
    original_url = settings.weaviate_url
    settings.weaviate_url = "http://localhost:8082"

    try:
        client = WeaviateClient()
        if client.client is None:
            pytest.skip("Weaviate client failed to initialize")
        yield client
    except Exception as e:
        pytest.skip(f"Weaviate not available: {e}")
    finally:
        settings.weaviate_url = original_url


@pytest.fixture(scope="module")
def embedding_service():
    """Create embedding service for generating test embeddings."""
    from src.core.embeddings import EmbeddingService

    try:
        service = EmbeddingService()
        # Test that it works
        test_embedding = service.generate_embedding("test")
        if test_embedding is None or len(test_embedding) == 0:
            pytest.skip("Embedding service not working")
        yield service
    except Exception as e:
        pytest.skip(f"Embedding service not available: {e}")


@pytest.fixture
def sample_schemas():
    """Generate sample table schemas for testing."""
    return [
        {
            "table_name": "test_customers",
            "dataset": "test_dataset",
            "project": "test_project",
            "description": "Customer master data for testing",
            "columns": [
                {"name": "customer_id", "type": "STRING", "description": "Unique customer identifier"},
                {"name": "customer_name", "type": "STRING", "description": "Customer full name"},
                {"name": "email", "type": "STRING", "description": "Customer email address"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Account creation date"}
            ],
            "row_count": 10000,
            "connector_id": "test_conn_001",
            "organization_id": "test_org",
            "database_type": "bigquery"
        },
        {
            "table_name": "test_orders",
            "dataset": "test_dataset",
            "project": "test_project",
            "description": "Sales orders for testing",
            "columns": [
                {"name": "order_id", "type": "STRING", "description": "Unique order identifier"},
                {"name": "customer_id", "type": "STRING", "description": "Reference to customer"},
                {"name": "order_date", "type": "DATE", "description": "Date order was placed"},
                {"name": "total_amount", "type": "FLOAT64", "description": "Order total value"}
            ],
            "row_count": 50000,
            "connector_id": "test_conn_001",
            "organization_id": "test_org",
            "database_type": "bigquery"
        },
        {
            "table_name": "test_products",
            "dataset": "other_dataset",
            "project": "test_project",
            "description": "Product catalog for testing",
            "columns": [
                {"name": "product_id", "type": "STRING", "description": "Product identifier"},
                {"name": "product_name", "type": "STRING", "description": "Product name"},
                {"name": "price", "type": "FLOAT64", "description": "Product price"}
            ],
            "row_count": 5000,
            "connector_id": "test_conn_002",  # Different connector
            "organization_id": "test_org",
            "database_type": "postgresql"
        }
    ]


@pytest.fixture(autouse=True)
def cleanup_test_schemas(weaviate_client):
    """Clean up test schemas before and after each test."""
    # Cleanup before test
    try:
        weaviate_client.delete_schemas_by_connector("test_conn_001")
        weaviate_client.delete_schemas_by_connector("test_conn_002")
    except:
        pass

    yield

    # Cleanup after test
    try:
        weaviate_client.delete_schemas_by_connector("test_conn_001")
        weaviate_client.delete_schemas_by_connector("test_conn_002")
    except:
        pass


class TestWeaviateConnection:
    """Test Weaviate connection and basic operations."""

    def test_client_connected(self, weaviate_client):
        """Test that client is connected."""
        assert weaviate_client.client is not None

    def test_collection_exists(self, weaviate_client):
        """Test that TableSchemas collection exists."""
        exists = weaviate_client.client.collections.exists(weaviate_client.collection_name)
        assert exists is True


class TestSchemaIndexing:
    """Test schema indexing functionality."""

    def test_index_single_schema(self, weaviate_client, embedding_service, sample_schemas):
        """Test indexing a single table schema."""
        schema = sample_schemas[0]

        # Generate embedding for the schema
        schema_text = f"Table: {schema['table_name']} - {schema['description']}"
        embedding = embedding_service.generate_embedding(schema_text)

        # Index the schema
        weaviate_client.index_table_schema(schema, embedding)

        # Verify it was indexed
        count = weaviate_client.get_schema_count_by_connector("test_conn_001")
        assert count >= 1

    def test_index_multiple_schemas(self, weaviate_client, embedding_service, sample_schemas):
        """Test indexing multiple table schemas."""
        for schema in sample_schemas:
            schema_text = f"Table: {schema['table_name']} - {schema['description']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        # Verify counts
        count_conn1 = weaviate_client.get_schema_count_by_connector("test_conn_001")
        count_conn2 = weaviate_client.get_schema_count_by_connector("test_conn_002")

        assert count_conn1 == 2  # customers and orders
        assert count_conn2 == 1  # products


class TestVectorSearch:
    """Test vector similarity search functionality."""

    def test_search_returns_results(self, weaviate_client, embedding_service, sample_schemas):
        """Test that search returns relevant results."""
        # First, index the schemas
        for schema in sample_schemas:
            schema_text = f"Table: {schema['table_name']} - {schema['description']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        # Wait a moment for indexing
        time.sleep(0.5)

        # Search for "customer information" - no filters
        query_embedding = embedding_service.generate_embedding("customer information and details")
        results = weaviate_client.search_similar_tables(query_embedding, limit=5)

        assert len(results) > 0
        # Customer table should be most relevant
        table_names = [r["table_name"] for r in results]
        assert "test_customers" in table_names

    def test_search_filters_by_connector_id(self, weaviate_client, embedding_service, sample_schemas):
        """Test that search filters by connector_id."""
        # Index all schemas
        for schema in sample_schemas:
            schema_text = f"Table: {schema['table_name']} - {schema['description']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        time.sleep(0.5)

        # Search with connector filter
        query_embedding = embedding_service.generate_embedding("show me data")
        results = weaviate_client.search_similar_tables(
            query_embedding,
            limit=10,
            connector_id="test_conn_001"
        )

        # Should only return schemas from test_conn_001
        for result in results:
            assert result.get("connector_id") == "test_conn_001"

    def test_search_filters_by_multiple_connector_ids(self, weaviate_client, embedding_service, sample_schemas):
        """Test that search filters by multiple connector_ids."""
        # Index all schemas
        for schema in sample_schemas:
            schema_text = f"Table: {schema['table_name']} - {schema['description']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        time.sleep(0.5)

        # Search with multiple connectors
        query_embedding = embedding_service.generate_embedding("show me all tables")
        results = weaviate_client.search_similar_tables(
            query_embedding,
            limit=10,
            connector_ids=["test_conn_001", "test_conn_002"]
        )

        # Should return schemas from both connectors
        assert len(results) == 3  # All 3 schemas

    def test_search_filters_by_database_type(self, weaviate_client, embedding_service, sample_schemas):
        """Test that search filters by database_type."""
        # Index all schemas
        for schema in sample_schemas:
            schema_text = f"Table: {schema['table_name']} - {schema['description']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        time.sleep(0.5)

        # Search for postgresql only
        query_embedding = embedding_service.generate_embedding("product catalog")
        results = weaviate_client.search_similar_tables(
            query_embedding,
            limit=10,
            database_type="postgresql"
        )

        # Should only return postgresql schemas
        for result in results:
            assert result.get("database_type") == "postgresql"

    def test_search_respects_limit(self, weaviate_client, embedding_service, sample_schemas):
        """Test that search respects the limit parameter."""
        # Index all schemas
        for schema in sample_schemas:
            schema_text = f"Table: {schema['table_name']} - {schema['description']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        time.sleep(0.5)

        # Search with limit of 1
        query_embedding = embedding_service.generate_embedding("show data")
        results = weaviate_client.search_similar_tables(query_embedding, limit=1)

        assert len(results) == 1


class TestDeleteOperations:
    """Test schema deletion operations."""

    def test_delete_schemas_by_connector(self, weaviate_client, embedding_service, sample_schemas):
        """Test deleting schemas by connector ID."""
        # Index all schemas
        for schema in sample_schemas:
            schema_text = f"Table: {schema['table_name']} - {schema['description']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        time.sleep(0.5)

        # Verify initial counts
        count_before = weaviate_client.get_schema_count_by_connector("test_conn_001")
        assert count_before == 2

        # Delete connector 1 schemas
        deleted = weaviate_client.delete_schemas_by_connector("test_conn_001")

        time.sleep(0.5)

        # Verify deletion
        count_after = weaviate_client.get_schema_count_by_connector("test_conn_001")
        assert count_after == 0

        # Connector 2 should still have its schema
        count_conn2 = weaviate_client.get_schema_count_by_connector("test_conn_002")
        assert count_conn2 == 1


class TestSchemaCount:
    """Test schema counting operations."""

    def test_get_schema_count_by_connector(self, weaviate_client, embedding_service, sample_schemas):
        """Test getting schema count by connector."""
        # Index schemas
        for schema in sample_schemas[:2]:  # Only first two (same connector)
            schema_text = f"Table: {schema['table_name']}"
            embedding = embedding_service.generate_embedding(schema_text)
            weaviate_client.index_table_schema(schema, embedding)

        time.sleep(0.5)

        count = weaviate_client.get_schema_count_by_connector("test_conn_001")
        assert count == 2

    def test_get_schema_count_nonexistent_connector(self, weaviate_client):
        """Test getting count for non-existent connector."""
        count = weaviate_client.get_schema_count_by_connector("nonexistent_connector")
        assert count == 0


class TestQueryPerformanceTracking:
    """Test query performance recording for optimization."""

    def test_record_query_performance(self, weaviate_client, embedding_service):
        """Test recording query performance data."""
        sql_text = "SELECT * FROM customers WHERE status = 'active'"
        sql_embedding = embedding_service.generate_embedding(sql_text)

        # Record the query
        weaviate_client.record_query_performance(
            sql_text=sql_text,
            sql_embedding=sql_embedding,
            execution_time_ms=150.5,
            rows_returned=1000,
            data_transferred_mb=0.5,
            strategy_used="DIRECT",
            pushdown_applied=True,
            filters_pushed=1,
            source_database="bigquery",
            target_database=None,
            tables_involved=["customers"],
            join_type=None,
            join_columns=None,
            success=True,
            error_message=None,
            user_id="test_user",
            organization_id="test_org"
        )

        # Recording should succeed (no exception thrown)
        # We can verify by searching for similar queries
        time.sleep(0.5)

        results = weaviate_client.search_similar_queries(sql_embedding, limit=5)
        assert len(results) > 0
        assert results[0]["strategy_used"] == "DIRECT"

    def test_search_similar_queries(self, weaviate_client, embedding_service):
        """Test searching for similar historical queries."""
        # Record a few queries
        queries = [
            "SELECT customer_id, name FROM customers",
            "SELECT customer_id, email FROM customers WHERE active = true",
            "SELECT order_id, total FROM orders"
        ]

        for sql in queries:
            sql_embedding = embedding_service.generate_embedding(sql)
            weaviate_client.record_query_performance(
                sql_text=sql,
                sql_embedding=sql_embedding,
                execution_time_ms=100.0,
                rows_returned=100,
                data_transferred_mb=0.1,
                strategy_used="DIRECT",
                success=True
            )

        time.sleep(0.5)

        # Search for something similar to customer queries
        search_embedding = embedding_service.generate_embedding("SELECT customer information")
        results = weaviate_client.search_similar_queries(search_embedding, limit=3)

        # Should find customer-related queries
        assert len(results) > 0
        # At least one result should be from customers table
        found_customer = any("customers" in r.get("sql_text", "") for r in results)
        assert found_customer


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
