"""
Comprehensive unit tests for WeaviateClient.

Tests cover:
- Initialization and collection creation
- Schema indexing
- Vector similarity search with filtering
- Connector ID filtering (single and multiple)
- Delete operations
- Query performance tracking
- Optimization hints
"""

import pytest
import json
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================================
# TEST WEAVIATE CLIENT INITIALIZATION
# ============================================================================

class TestWeaviateClientInit:
    """Test Weaviate client initialization."""

    def test_init_creates_client(self, mock_weaviate):
        """Test that initialization creates Weaviate client."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()

                # Should have attempted to connect
                mock_weaviate['module'].connect_to_local.assert_called()

    def test_init_ensures_collections_exist(self, mock_weaviate):
        """Test that initialization ensures collections exist."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()

                # Should check for TableSchemas and OptimizedQuery collections
                mock_weaviate['client'].collections.exists.assert_called()

    def test_init_handles_connection_failure(self, mock_weaviate):
        """Test graceful handling of connection failure."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            mock_weaviate['module'].connect_to_local.side_effect = Exception("Connection failed")

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient

                # Should not raise, but client will be None
                client = WeaviateClient()
                assert client.client is None

    def test_init_sets_collection_names(self, mock_weaviate):
        """Test that collection names are set correctly."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()

                assert client.collection_name == "TableSchemas"
                assert client.query_collection_name == "OptimizedQuery"


# ============================================================================
# TEST INDEX TABLE SCHEMA
# ============================================================================

class TestIndexTableSchema:
    """Test schema indexing functionality."""

    @pytest.fixture
    def weaviate_client(self, mock_weaviate):
        """Create Weaviate client for testing."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()
                client.client = mock_weaviate['client']
                return client

    def test_index_table_schema_inserts_data(self, weaviate_client, mock_weaviate, sample_table_schema):
        """Test that index_table_schema inserts data."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(sample_table_schema, embedding)

        mock_weaviate['collection'].data.insert.assert_called_once()

    def test_index_table_schema_includes_connector_id(self, weaviate_client, mock_weaviate, sample_table_schema):
        """Test that connector_id is included in indexed data."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(sample_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        assert 'connector_id' in properties
        assert properties['connector_id'] == "conn_123"

    def test_index_table_schema_includes_organization_id(self, weaviate_client, mock_weaviate, sample_table_schema):
        """Test that organization_id is included in indexed data."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(sample_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        assert 'organization_id' in properties
        assert properties['organization_id'] == "test-org"

    def test_index_table_schema_creates_combined_text(self, weaviate_client, mock_weaviate, sample_table_schema):
        """Test that combined_text is generated for semantic search."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(sample_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        assert 'combined_text' in properties
        assert 'customers' in properties['combined_text']

    def test_index_table_schema_serializes_columns(self, weaviate_client, mock_weaviate, sample_table_schema):
        """Test that columns are JSON serialized."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(sample_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        # Should be JSON string
        assert isinstance(properties['columns'], str)
        parsed_columns = json.loads(properties['columns'])
        assert isinstance(parsed_columns, list)

    def test_index_table_schema_passes_embedding(self, weaviate_client, mock_weaviate, sample_table_schema):
        """Test that embedding vector is passed correctly."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(sample_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        assert call_args.kwargs['vector'] == embedding


# ============================================================================
# TEST SEARCH SIMILAR TABLES
# ============================================================================

class TestSearchSimilarTables:
    """Test vector search functionality with filtering."""

    @pytest.fixture
    def weaviate_client(self, mock_weaviate):
        """Create Weaviate client for testing."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()
                client.client = mock_weaviate['client']
                return client

    def test_search_returns_results(self, weaviate_client, mock_weaviate):
        """Test that search returns results."""
        # Setup mock response
        mock_item = MagicMock()
        mock_item.properties = {
            "table_name": "test_table",
            "dataset": "test_dataset",
            "project": "test_project",
            "description": "Test description",
            "columns": "[]",
            "row_count": 100,
            "connector_id": "conn_123",
            "database_type": "bigquery"
        }
        mock_item.metadata = MagicMock()
        mock_item.metadata.distance = 0.1

        mock_weaviate['response'].objects = [mock_item]

        embedding = [0.1] * 1536
        results = weaviate_client.search_similar_tables(embedding)

        assert len(results) == 1
        assert results[0]["table_name"] == "test_table"

    def test_search_filters_by_connector_id(self, weaviate_client, mock_weaviate):
        """Test filtering by single connector_id."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        weaviate_client.search_similar_tables(embedding, connector_id="conn_123")

        # Check that filter was applied
        call_args = mock_weaviate['collection'].query.near_vector.call_args
        assert call_args.kwargs.get('filters') is not None

    def test_search_filters_by_connector_ids_list(self, weaviate_client, mock_weaviate):
        """Test filtering by list of connector_ids."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        weaviate_client.search_similar_tables(
            embedding,
            connector_ids=["conn_123", "conn_456"]
        )

        # Check that filter was applied
        call_args = mock_weaviate['collection'].query.near_vector.call_args
        assert call_args.kwargs.get('filters') is not None

    def test_search_filters_by_organization_id(self, weaviate_client, mock_weaviate):
        """Test filtering by organization_id."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        weaviate_client.search_similar_tables(embedding, organization_id="org_123")

        call_args = mock_weaviate['collection'].query.near_vector.call_args
        assert call_args.kwargs.get('filters') is not None

    def test_search_filters_by_database_type(self, weaviate_client, mock_weaviate):
        """Test filtering by database_type."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        weaviate_client.search_similar_tables(embedding, database_type="postgresql")

        call_args = mock_weaviate['collection'].query.near_vector.call_args
        assert call_args.kwargs.get('filters') is not None

    def test_search_filters_by_enabled_databases(self, weaviate_client, mock_weaviate):
        """Test filtering by list of enabled databases."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        weaviate_client.search_similar_tables(
            embedding,
            enabled_databases=["bigquery", "postgresql"]
        )

        call_args = mock_weaviate['collection'].query.near_vector.call_args
        assert call_args.kwargs.get('filters') is not None

    def test_search_combines_multiple_filters(self, weaviate_client, mock_weaviate):
        """Test that multiple filters are combined with AND."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        weaviate_client.search_similar_tables(
            embedding,
            connector_id="conn_123",
            organization_id="org_123"
        )

        call_args = mock_weaviate['collection'].query.near_vector.call_args
        assert call_args.kwargs.get('filters') is not None

    def test_search_handles_empty_results(self, weaviate_client, mock_weaviate):
        """Test handling of empty search results."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        results = weaviate_client.search_similar_tables(embedding)

        assert results == []

    def test_search_respects_limit(self, weaviate_client, mock_weaviate):
        """Test that limit parameter is passed."""
        mock_weaviate['response'].objects = []

        embedding = [0.1] * 1536
        weaviate_client.search_similar_tables(embedding, limit=10)

        call_args = mock_weaviate['collection'].query.near_vector.call_args
        assert call_args.kwargs['limit'] == 10

    def test_search_includes_distance_metadata(self, weaviate_client, mock_weaviate):
        """Test that distance metadata is included in results."""
        mock_item = MagicMock()
        mock_item.properties = {
            "table_name": "test_table",
            "dataset": "test_dataset",
            "project": "test_project",
            "description": "",
            "columns": "[]",
            "row_count": 0,
            "connector_id": "",
            "database_type": "bigquery"
        }
        mock_item.metadata = MagicMock()
        mock_item.metadata.distance = 0.15

        mock_weaviate['response'].objects = [mock_item]

        embedding = [0.1] * 1536
        results = weaviate_client.search_similar_tables(embedding)

        assert results[0]["distance"] == 0.15

    def test_search_parses_columns_json(self, weaviate_client, mock_weaviate):
        """Test that columns JSON is parsed correctly."""
        mock_item = MagicMock()
        mock_item.properties = {
            "table_name": "test_table",
            "dataset": "test_dataset",
            "project": "test_project",
            "description": "",
            "columns": '[{"name": "id", "type": "INT"}]',
            "row_count": 0,
            "connector_id": "",
            "database_type": "bigquery"
        }
        mock_item.metadata = MagicMock()
        mock_item.metadata.distance = 0.1

        mock_weaviate['response'].objects = [mock_item]

        embedding = [0.1] * 1536
        results = weaviate_client.search_similar_tables(embedding)

        assert isinstance(results[0]["columns"], list)
        assert results[0]["columns"][0]["name"] == "id"

    def test_search_handles_invalid_columns_json(self, weaviate_client, mock_weaviate):
        """Test graceful handling of invalid columns JSON."""
        mock_item = MagicMock()
        mock_item.properties = {
            "table_name": "test_table",
            "dataset": "test_dataset",
            "project": "test_project",
            "description": "",
            "columns": "not valid json",
            "row_count": 0,
            "connector_id": "",
            "database_type": "bigquery"
        }
        mock_item.metadata = MagicMock()
        mock_item.metadata.distance = 0.1

        mock_weaviate['response'].objects = [mock_item]

        embedding = [0.1] * 1536
        results = weaviate_client.search_similar_tables(embedding)

        # Should return empty list for columns on parse error
        assert results[0]["columns"] == []


# ============================================================================
# TEST DELETE OPERATIONS
# ============================================================================

class TestDeleteOperations:
    """Test delete operations."""

    @pytest.fixture
    def weaviate_client(self, mock_weaviate):
        """Create Weaviate client for testing."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()
                client.client = mock_weaviate['client']
                return client

    def test_delete_all_schemas(self, weaviate_client, mock_weaviate):
        """Test deleting all schemas."""
        weaviate_client.delete_all_schemas()

        mock_weaviate['collection'].data.delete_many.assert_called_once()

    def test_delete_schemas_by_connector(self, weaviate_client, mock_weaviate):
        """Test deleting schemas by connector ID."""
        mock_delete_result = MagicMock()
        mock_delete_result.successful = 5
        mock_weaviate['collection'].data.delete_many.return_value = mock_delete_result

        deleted = weaviate_client.delete_schemas_by_connector("conn_123")

        assert deleted == 5
        mock_weaviate['collection'].data.delete_many.assert_called_once()

    def test_delete_schemas_by_connector_returns_count(self, weaviate_client, mock_weaviate):
        """Test that delete returns correct count."""
        mock_delete_result = MagicMock()
        mock_delete_result.successful = 10
        mock_weaviate['collection'].data.delete_many.return_value = mock_delete_result

        deleted = weaviate_client.delete_schemas_by_connector("conn_456")

        assert deleted == 10

    def test_get_schema_count_by_connector(self, weaviate_client, mock_weaviate):
        """Test getting schema count by connector."""
        mock_aggregate_response = MagicMock()
        mock_aggregate_response.total_count = 25
        mock_weaviate['collection'].aggregate.over_all.return_value = mock_aggregate_response

        count = weaviate_client.get_schema_count_by_connector("conn_123")

        assert count == 25

    def test_get_schema_count_handles_error(self, weaviate_client, mock_weaviate):
        """Test graceful error handling in count."""
        mock_weaviate['collection'].aggregate.over_all.side_effect = Exception("Error")

        count = weaviate_client.get_schema_count_by_connector("conn_123")

        assert count == 0


# ============================================================================
# TEST QUERY PERFORMANCE TRACKING
# ============================================================================

class TestQueryPerformanceTracking:
    """Test query performance recording and retrieval."""

    @pytest.fixture
    def weaviate_client(self, mock_weaviate):
        """Create Weaviate client for testing."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()
                client.client = mock_weaviate['client']
                return client

    def test_record_query_performance_inserts_data(self, weaviate_client, mock_weaviate):
        """Test recording query performance."""
        # Setup mock for OptimizedQuery collection
        mock_query_collection = MagicMock()
        mock_weaviate['client'].collections.get.return_value = mock_query_collection

        embedding = [0.1] * 1536
        weaviate_client.record_query_performance(
            sql_text="SELECT * FROM test",
            sql_embedding=embedding,
            execution_time_ms=150.0,
            rows_returned=100,
            data_transferred_mb=1.5,
            strategy_used="STAGING_TABLE"
        )

        mock_query_collection.data.insert.assert_called_once()

    def test_record_query_performance_includes_metrics(self, weaviate_client, mock_weaviate):
        """Test that all metrics are recorded."""
        mock_query_collection = MagicMock()
        mock_weaviate['client'].collections.get.return_value = mock_query_collection

        embedding = [0.1] * 1536
        weaviate_client.record_query_performance(
            sql_text="SELECT * FROM test",
            sql_embedding=embedding,
            execution_time_ms=200.0,
            rows_returned=50,
            data_transferred_mb=0.5,
            strategy_used="MOVE_TO_PRIMARY",
            pushdown_applied=True,
            filters_pushed=2
        )

        call_args = mock_query_collection.data.insert.call_args
        properties = call_args.kwargs['properties']

        assert properties['execution_time_ms'] == 200.0
        assert properties['rows_returned'] == 50
        assert properties['pushdown_applied'] is True
        assert properties['filters_pushed'] == 2

    def test_record_query_performance_handles_error_gracefully(self, weaviate_client, mock_weaviate):
        """Test that errors don't propagate."""
        mock_weaviate['client'].collections.get.side_effect = Exception("Error")

        embedding = [0.1] * 1536
        # Should not raise
        weaviate_client.record_query_performance(
            sql_text="SELECT * FROM test",
            sql_embedding=embedding,
            execution_time_ms=100.0,
            rows_returned=10,
            data_transferred_mb=0.1,
            strategy_used="DIRECT"
        )

    def test_search_similar_queries_returns_results(self, weaviate_client, mock_weaviate):
        """Test searching similar historical queries."""
        mock_query_collection = MagicMock()
        mock_weaviate['client'].collections.get.return_value = mock_query_collection

        mock_item = MagicMock()
        mock_item.properties = {
            "sql_text": "SELECT * FROM similar",
            "execution_time_ms": 100,
            "rows_returned": 50,
            "data_transferred_mb": 0.5,
            "strategy_used": "STAGING_TABLE",
            "pushdown_applied": True,
            "filters_pushed": 1,
            "source_database": "bigquery",
            "target_database": "postgresql",
            "tables_involved": "[]",
            "join_type": "INNER",
            "timestamp": "2024-01-01T00:00:00",
            "success": True
        }
        mock_item.metadata = MagicMock()
        mock_item.metadata.distance = 0.1

        mock_response = MagicMock()
        mock_response.objects = [mock_item]
        mock_query_collection.query.near_vector.return_value = mock_response

        embedding = [0.1] * 1536
        results = weaviate_client.search_similar_queries(embedding)

        assert len(results) == 1
        assert results[0]["strategy_used"] == "STAGING_TABLE"

    def test_search_similar_queries_filters_successful(self, weaviate_client, mock_weaviate):
        """Test that search filters for successful queries."""
        mock_query_collection = MagicMock()
        mock_weaviate['client'].collections.get.return_value = mock_query_collection

        mock_response = MagicMock()
        mock_response.objects = []
        mock_query_collection.query.near_vector.return_value = mock_response

        embedding = [0.1] * 1536
        weaviate_client.search_similar_queries(embedding, only_successful=True)

        call_args = mock_query_collection.query.near_vector.call_args
        assert call_args.kwargs.get('filters') is not None


# ============================================================================
# TEST OPTIMIZATION HINTS
# ============================================================================

class TestOptimizationHints:
    """Test optimization hint generation."""

    @pytest.fixture
    def weaviate_client(self, mock_weaviate):
        """Create Weaviate client for testing."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()
                client.client = mock_weaviate['client']
                return client

    def test_get_optimization_hints_with_similar_queries(self, weaviate_client, mock_weaviate):
        """Test getting optimization hints from similar queries."""
        # Mock search_similar_queries - need enough samples for confidence
        with patch.object(weaviate_client, 'search_similar_queries') as mock_search:
            # Need 7+ similar queries for confidence > 0.7 (threshold)
            mock_search.return_value = [
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 100, "data_transferred_mb": 0.5, "distance": 0.1},
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 110, "data_transferred_mb": 0.5, "distance": 0.11},
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 120, "data_transferred_mb": 0.6, "distance": 0.12},
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 105, "data_transferred_mb": 0.5, "distance": 0.13},
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 115, "data_transferred_mb": 0.55, "distance": 0.14},
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 125, "data_transferred_mb": 0.6, "distance": 0.15},
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 108, "data_transferred_mb": 0.52, "distance": 0.16},
                {"strategy_used": "STAGING_TABLE", "execution_time_ms": 112, "data_transferred_mb": 0.58, "distance": 0.17},
            ]

            embedding = [0.1] * 1536
            hints = weaviate_client.get_optimization_hints(embedding)

            assert hints is not None
            assert hints['recommended_strategy'] == "STAGING_TABLE"
            assert hints['confidence'] >= 0.7

    def test_get_optimization_hints_returns_none_when_no_similar(self, weaviate_client, mock_weaviate):
        """Test that None is returned when no similar queries exist."""
        with patch.object(weaviate_client, 'search_similar_queries') as mock_search:
            mock_search.return_value = []

            embedding = [0.1] * 1536
            hints = weaviate_client.get_optimization_hints(embedding)

            assert hints is None

    def test_get_optimization_hints_respects_confidence_threshold(self, weaviate_client, mock_weaviate):
        """Test that confidence threshold is respected."""
        with patch.object(weaviate_client, 'search_similar_queries') as mock_search:
            # Only one similar query - low confidence
            mock_search.return_value = [
                {
                    "strategy_used": "STAGING_TABLE",
                    "execution_time_ms": 100,
                    "data_transferred_mb": 0.5,
                    "distance": 0.1
                }
            ]

            embedding = [0.1] * 1536
            # High threshold
            hints = weaviate_client.get_optimization_hints(
                embedding,
                confidence_threshold=0.9
            )

            # Should return None due to low confidence
            assert hints is None

    def test_get_optimization_hints_filters_by_distance(self, weaviate_client, mock_weaviate):
        """Test that only very similar queries are considered."""
        with patch.object(weaviate_client, 'search_similar_queries') as mock_search:
            # Queries with high distance (not similar)
            mock_search.return_value = [
                {
                    "strategy_used": "STAGING_TABLE",
                    "execution_time_ms": 100,
                    "data_transferred_mb": 0.5,
                    "distance": 0.5  # Not very similar
                }
            ]

            embedding = [0.1] * 1536
            hints = weaviate_client.get_optimization_hints(embedding)

            # Should return None because distance > 0.2
            assert hints is None


# ============================================================================
# TEST MULTI-DATABASE SCHEMA FIELD NAME HANDLING
# ============================================================================

class TestMultiDatabaseSchemaIndexing:
    """
    Test that schema indexing works correctly for all database types.

    BigQuery uses: dataset/project
    Snowflake/PostgreSQL/Redshift/Databricks use: schema/database

    The WeaviateClient must handle both field naming conventions.
    """

    @pytest.fixture
    def weaviate_client(self, mock_weaviate):
        """Create Weaviate client for testing."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()
                client.client = mock_weaviate['client']
                return client

    def test_index_bigquery_schema_uses_dataset_project(
        self, weaviate_client, mock_weaviate, bigquery_table_schema
    ):
        """Test BigQuery schema indexing uses dataset/project fields correctly."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(bigquery_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        # Verify dataset and project are populated from BigQuery field names
        assert properties['dataset'] == "sales_data"
        assert properties['project'] == "my-gcp-project"
        assert properties['table_name'] == "customers"
        assert properties['connector_id'] == "bq_conn_123"

    def test_index_snowflake_schema_uses_schema_database(
        self, weaviate_client, mock_weaviate, snowflake_table_schema
    ):
        """Test Snowflake schema indexing uses schema/database fields correctly."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(snowflake_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        # Verify dataset/project are populated from Snowflake's schema/database
        assert properties['dataset'] == "PUBLIC"  # From schema field
        assert properties['project'] == "ANALYTICS_DB"  # From database field
        assert properties['table_name'] == "ORDERS"
        assert properties['connector_id'] == "sf_conn_456"

    def test_index_postgresql_schema_uses_schema_database(
        self, weaviate_client, mock_weaviate, postgresql_table_schema
    ):
        """Test PostgreSQL schema indexing uses schema/database fields correctly."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(postgresql_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        # Verify dataset/project are populated from PostgreSQL's schema/database
        assert properties['dataset'] == "inventory"  # From schema field
        assert properties['project'] == "warehouse_db"  # From database field
        assert properties['table_name'] == "products"
        assert properties['connector_id'] == "pg_conn_789"

    def test_index_redshift_schema_uses_schema_database(
        self, weaviate_client, mock_weaviate, redshift_table_schema
    ):
        """Test Redshift schema indexing uses schema/database fields correctly."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(redshift_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        # Verify dataset/project are populated from Redshift's schema/database
        assert properties['dataset'] == "finance"  # From schema field
        assert properties['project'] == "data_warehouse"  # From database field
        assert properties['table_name'] == "transactions"
        assert properties['connector_id'] == "rs_conn_101"

    def test_index_databricks_schema_uses_schema_database(
        self, weaviate_client, mock_weaviate, databricks_table_schema
    ):
        """Test Databricks schema indexing uses schema/database fields correctly."""
        embedding = [0.1] * 1536

        weaviate_client.index_table_schema(databricks_table_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        # Verify dataset/project are populated from Databricks' schema/database
        assert properties['dataset'] == "analytics"  # From schema field
        assert properties['project'] == "lakehouse"  # From database field
        assert properties['table_name'] == "events"
        assert properties['connector_id'] == "db_conn_202"

    def test_combined_text_uses_correct_dataset_for_all_databases(
        self, weaviate_client, mock_weaviate, all_database_schemas
    ):
        """Test combined_text field is generated correctly for all database types."""
        embedding = [0.1] * 1536

        for db_type, schema in all_database_schemas.items():
            # Reset mock
            mock_weaviate['collection'].data.insert.reset_mock()

            weaviate_client.index_table_schema(schema, embedding)

            call_args = mock_weaviate['collection'].data.insert.call_args
            properties = call_args.kwargs['properties']

            # combined_text should contain the table name
            assert schema['table_name'] in properties['combined_text'], \
                f"Table name missing from combined_text for {db_type}"

            # combined_text should NOT raise KeyError (the bug we fixed)
            assert 'Dataset:' in properties['combined_text'] or 'dataset' in properties['combined_text'].lower(), \
                f"Dataset info missing from combined_text for {db_type}"

    def test_database_type_is_indexed_correctly(
        self, weaviate_client, mock_weaviate, all_database_schemas
    ):
        """Test database_type field is indexed correctly for all database types."""
        embedding = [0.1] * 1536

        expected_types = {
            "bigquery": "bigquery",
            "snowflake": "snowflake",
            "postgresql": "postgresql",
            "redshift": "redshift",
            "databricks": "databricks"
        }

        for db_type, schema in all_database_schemas.items():
            mock_weaviate['collection'].data.insert.reset_mock()

            weaviate_client.index_table_schema(schema, embedding)

            call_args = mock_weaviate['collection'].data.insert.call_args
            properties = call_args.kwargs['properties']

            assert properties['database_type'] == expected_types[db_type], \
                f"Incorrect database_type for {db_type}"

    def test_schema_without_dataset_or_schema_field_defaults_to_empty(
        self, weaviate_client, mock_weaviate
    ):
        """Test schema with neither dataset nor schema field defaults to empty string."""
        embedding = [0.1] * 1536

        minimal_schema = {
            "table_name": "minimal_table",
            "columns": [{"name": "id", "type": "INT", "description": "ID"}],
            "connector_id": "min_conn",
            "organization_id": "test-org"
        }

        weaviate_client.index_table_schema(minimal_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        assert properties['dataset'] == ""
        assert properties['project'] == ""

    def test_schema_with_both_dataset_and_schema_prefers_dataset(
        self, weaviate_client, mock_weaviate
    ):
        """Test that dataset field takes precedence over schema field."""
        embedding = [0.1] * 1536

        # Edge case: schema has both field naming conventions
        mixed_schema = {
            "table_name": "mixed_table",
            "dataset": "dataset_value",  # BigQuery style
            "schema": "schema_value",  # Snowflake style
            "project": "project_value",
            "database": "database_value",
            "columns": [{"name": "id", "type": "INT", "description": "ID"}],
            "connector_id": "mixed_conn",
            "organization_id": "test-org"
        }

        weaviate_client.index_table_schema(mixed_schema, embedding)

        call_args = mock_weaviate['collection'].data.insert.call_args
        properties = call_args.kwargs['properties']

        # dataset should take precedence over schema
        assert properties['dataset'] == "dataset_value"
        # project should take precedence over database
        assert properties['project'] == "project_value"

    def test_all_database_schemas_index_without_keyerror(
        self, weaviate_client, mock_weaviate, all_database_schemas
    ):
        """
        Regression test: Ensure no KeyError is raised for any database type.

        This was the original bug - Snowflake schemas would fail with:
        'Failed to index schema: 'dataset''
        """
        embedding = [0.1] * 1536

        for db_type, schema in all_database_schemas.items():
            mock_weaviate['collection'].data.insert.reset_mock()

            # This should NOT raise KeyError
            try:
                weaviate_client.index_table_schema(schema, embedding)
            except KeyError as e:
                pytest.fail(f"KeyError raised for {db_type} schema: {e}")

            # Verify the insert was called
            assert mock_weaviate['collection'].data.insert.called, \
                f"Insert not called for {db_type}"


# ============================================================================
# TEST CLIENT CLEANUP
# ============================================================================

class TestClientCleanup:
    """Test client cleanup."""

    def test_close_closes_client(self, mock_weaviate):
        """Test that close method closes the client."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()
                client.client = mock_weaviate['client']

                client.close()

                mock_weaviate['client'].close.assert_called_once()

    def test_close_handles_none_client(self, mock_weaviate):
        """Test that close handles None client gracefully."""
        with patch('src.db.weaviate_client.settings') as mock_settings:
            mock_settings.weaviate_url = "http://localhost:8082"

            mock_weaviate['module'].connect_to_local.side_effect = Exception("Failed")

            with patch('src.db.weaviate_client.weaviate', mock_weaviate['module']):
                from src.db.weaviate_client import WeaviateClient
                client = WeaviateClient()

                # Should not raise
                client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
