"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import sys
from pathlib import Path

# Add backend/src to Python path so imports work
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

# Shared fixtures

@pytest.fixture(scope="session")
def sql_generator():
    """Shared SQL generator instance for tests."""
    from src.core.sql_generator import SQLGenerator
    return SQLGenerator()

@pytest.fixture(scope="session")
def cache_manager():
    """Shared cache manager instance for tests."""
    from src.core.cache_manager import CacheManager
    return CacheManager()

@pytest.fixture(scope="session")
def bigquery_client():
    """Shared BigQuery client for integration tests."""
    from src.db.bigquery import BigQueryClient
    from src.config import settings
    
    config = {
        "project": settings.google_cloud_project,
        "dataset": settings.bigquery_dataset,
        "credentials_path": settings.google_application_credentials,
        "timeout": settings.bigquery_query_timeout_seconds
    }
    return BigQueryClient(config)

@pytest.fixture(scope="function")
def clear_cache():
    """Fixture to clear cache before each test."""
    from src.core.cache_manager import CacheManager
    cache = CacheManager()
    cache.clear_all_caches()
    yield
    # Cleanup after test if needed

@pytest.fixture(scope="session")
def sample_queries():
    """Common test queries."""
    return [
        "Show me all GL accounts",
        "What is the total revenue by customer?",
        "Show sales trends by month",
        "What products have the highest sales?",
        "Show customer segments and their performance"
    ]

@pytest.fixture(scope="session")
def sample_invalid_queries():
    """Invalid queries for negative testing."""
    return [
        "SELECT * FROM nonexistent_table",
        "SELECT nonexistent_column FROM GL_Accounts",
        "INVALID SQL SYNTAX HERE"
    ]

# Knowledge Graph fixtures

@pytest.fixture(scope="session")
def knowledge_graph():
    """Load Apache Jena knowledge graph for testing."""
    from rdflib import Graph, Namespace
    import os

    graph = Graph()
    FIN = Namespace("http://example.com/finance#")
    graph.bind("fin", FIN)

    # Try to load knowledge graph file if it exists
    kg_file = "table_metadata_kg.ttl"
    if os.path.exists(kg_file):
        graph.parse(kg_file, format="turtle")

    return graph

@pytest.fixture(scope="session")
def graph(knowledge_graph):
    """Alias for knowledge_graph fixture (for backward compatibility)."""
    return knowledge_graph

@pytest.fixture
def table1():
    """First table name for join path testing."""
    return "Customer_Master"

@pytest.fixture
def table2():
    """Second table name for join path testing."""
    return "transaction_data"

# ============================================================================
# MOCK FIXTURES FOR UNIT TESTING
# ============================================================================

from unittest.mock import MagicMock, patch, AsyncMock

@pytest.fixture
def mock_redis():
    """Mock Redis client for cache testing without actual Redis."""
    with patch('src.core.cache_manager.redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.ConnectionPool.return_value = MagicMock()
        mock_redis.Redis.return_value = mock_instance
        mock_redis.from_url.return_value = mock_instance
        mock_instance.ping.return_value = True
        mock_instance.get.return_value = None  # Default cache miss
        mock_instance.setex.return_value = True
        mock_instance.delete.return_value = 1
        mock_instance.scan_iter.return_value = iter([])
        mock_instance.ttl.return_value = 3600
        mock_instance.incr.return_value = 1
        mock_instance.expire.return_value = True
        mock_instance.info.return_value = {
            'used_memory_human': '100MB',
            'connected_clients': 1,
            'total_connections_received': 10,
            'instantaneous_ops_per_sec': 5
        }
        yield mock_instance


@pytest.fixture
def mock_weaviate():
    """Mock Weaviate client for vector search testing."""
    with patch('src.db.weaviate_client.weaviate') as mock_weaviate:
        mock_client = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.exists.return_value = True
        mock_collection = MagicMock()
        mock_client.collections.get.return_value = mock_collection

        # Mock empty search results by default
        mock_response = MagicMock()
        mock_response.objects = []
        mock_collection.query.near_vector.return_value = mock_response

        # Mock delete operation
        mock_delete_result = MagicMock()
        mock_delete_result.successful = 0
        mock_collection.data.delete_many.return_value = mock_delete_result

        # Mock aggregate
        mock_aggregate_response = MagicMock()
        mock_aggregate_response.total_count = 0
        mock_collection.aggregate.over_all.return_value = mock_aggregate_response

        yield {
            'client': mock_client,
            'collection': mock_collection,
            'module': mock_weaviate,
            'response': mock_response
        }


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client for LLM testing."""
    with patch('src.core.llm_client.Anthropic') as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.type = "tool_use"
        mock_content.name = "generate_sql_query"
        mock_content.input = {
            "sql": "SELECT * FROM test_table",
            "explanation": "Test query",
            "tables_used": ["test_table"],
            "estimated_complexity": "low"
        }
        mock_response.content = [mock_content]
        mock_response.stop_reason = "tool_use"
        mock_client.messages.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for embedding testing."""
    with patch('src.core.embeddings.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response.data = [mock_embedding]
        mock_client.embeddings.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client for database testing."""
    with patch('google.cloud.bigquery.Client') as mock_bq:
        mock_client = MagicMock()
        mock_bq.return_value = mock_client

        mock_job = MagicMock()
        mock_job.result.return_value = []
        mock_job.total_bytes_billed = 1000
        mock_job.total_bytes_processed = 5000
        mock_client.query.return_value = mock_job

        yield mock_client


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB client for testing."""
    with patch('src.db.mongodb_client.get_mongodb_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_db = MagicMock()
        mock_collection = AsyncMock()

        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_collection.find_one = AsyncMock(return_value=None)
        mock_collection.find = MagicMock(return_value=AsyncMock())
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
        mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

        mock_get_client.return_value = mock_client
        yield {
            'client': mock_client,
            'db': mock_db,
            'collection': mock_collection
        }


@pytest.fixture
def mock_settings():
    """Mock settings for testing without environment variables."""
    with patch('src.config.settings') as mock_settings:
        mock_settings.google_cloud_project = "test-project"
        mock_settings.bigquery_dataset = "test-dataset"
        mock_settings.anthropic_api_key = "test-anthropic-key"
        mock_settings.anthropic_model = "claude-3-sonnet"
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.cache_enabled = True
        mock_settings.weaviate_url = "http://localhost:8082"
        mock_settings.redis_host = "localhost"
        mock_settings.redis_port = 6379
        mock_settings.redis_db = 0
        mock_settings.redis_url = None
        mock_settings.redis_decode_responses = False
        mock_settings.redis_max_connections = 50
        mock_settings.default_org_id = "test-org"
        mock_settings.enable_industry_features = False
        mock_settings.cache_validation_required = False
        mock_settings.cache_min_confidence = 0.5
        mock_settings.cache_max_rows_threshold = 100000
        mock_settings.cache_execution_threshold_ms = 30000
        mock_settings.cache_ttl_gold = 604800
        mock_settings.cache_ttl_silver = 86400
        mock_settings.cache_ttl_bronze = 3600
        mock_settings.cache_ttl_sql_frequent = 604800
        mock_settings.cache_ttl_sql_infrequent = 86400
        mock_settings.cache_ttl_schema = 86400
        mock_settings.cache_ttl_embedding = 2592000
        mock_settings.cache_ttl_validation = 3600
        mock_settings.cache_ttl_result = 300
        mock_settings.cache_ttl_session = 86400
        mock_settings.cache_reject_empty_results = True  # Default to True (don't cache empty results)
        yield mock_settings


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_table_schema():
    """Sample table schema for testing."""
    return {
        "table_name": "customers",
        "dataset": "test_dataset",
        "project": "test_project",
        "columns": [
            {"name": "customer_id", "type": "STRING", "is_nullable": False, "description": "Customer identifier"},
            {"name": "customer_name", "type": "STRING", "is_nullable": False, "description": "Customer name"},
            {"name": "total_revenue", "type": "FLOAT64", "is_nullable": True, "description": "Total revenue"}
        ],
        "row_count": 10000,
        "connector_id": "conn_123",
        "organization_id": "test-org",
        "database_type": "bigquery"
    }


@pytest.fixture
def sample_table_schemas():
    """Multiple sample table schemas for testing."""
    return [
        {
            "table_name": "customers",
            "dataset": "test_dataset",
            "project": "test_project",
            "columns": [
                {"name": "customer_id", "type": "STRING", "is_nullable": False, "description": "Customer identifier"},
                {"name": "customer_name", "type": "STRING", "is_nullable": False, "description": "Customer name"}
            ],
            "connector_id": "conn_123",
            "organization_id": "test-org",
            "database_type": "bigquery"
        },
        {
            "table_name": "orders",
            "dataset": "test_dataset",
            "project": "test_project",
            "columns": [
                {"name": "order_id", "type": "STRING", "is_nullable": False, "description": "Order identifier"},
                {"name": "customer_id", "type": "STRING", "is_nullable": False, "description": "Customer reference"},
                {"name": "total_amount", "type": "FLOAT64", "is_nullable": True, "description": "Order total"}
            ],
            "connector_id": "conn_123",
            "organization_id": "test-org",
            "database_type": "bigquery"
        }
    ]


@pytest.fixture
def sample_llm_response():
    """Sample LLM response for SQL generation tests."""
    return {
        "sql": "SELECT customer_id, SUM(total_amount) as revenue FROM orders GROUP BY customer_id",
        "explanation": "Calculates total revenue per customer",
        "tables_used": ["orders"],
        "estimated_complexity": "low"
    }


@pytest.fixture
def sample_database_config():
    """Sample database configuration for testing."""
    return {
        "project_id": "test-project",
        "dataset_id": "test-dataset",
        "connector_id": "conn_123"
    }


@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing."""
    return [0.1] * 1536  # OpenAI embedding dimension


# ============================================================================
# MULTI-DATABASE SCHEMA FIXTURES
# ============================================================================

@pytest.fixture
def bigquery_table_schema():
    """Sample BigQuery table schema (uses dataset/project field names)."""
    return {
        "table_name": "customers",
        "dataset": "sales_data",
        "project": "my-gcp-project",
        "columns": [
            {"name": "customer_id", "type": "STRING", "is_nullable": False, "description": "Customer identifier"},
            {"name": "customer_name", "type": "STRING", "is_nullable": False, "description": "Customer name"},
            {"name": "total_revenue", "type": "FLOAT64", "is_nullable": True, "description": "Total revenue"}
        ],
        "row_count": 10000,
        "connector_id": "bq_conn_123",
        "organization_id": "test-org",
        "database_type": "bigquery"
    }


@pytest.fixture
def snowflake_table_schema():
    """Sample Snowflake table schema (uses schema/database field names)."""
    return {
        "table_name": "ORDERS",
        "schema": "PUBLIC",
        "database": "ANALYTICS_DB",
        "columns": [
            {"name": "ORDER_ID", "type": "VARCHAR", "is_nullable": False, "description": "Order identifier"},
            {"name": "CUSTOMER_ID", "type": "VARCHAR", "is_nullable": False, "description": "Customer reference"},
            {"name": "ORDER_TOTAL", "type": "NUMBER", "is_nullable": True, "description": "Order total amount"}
        ],
        "row_count": 50000,
        "connector_id": "sf_conn_456",
        "organization_id": "test-org",
        "source_database_type": "snowflake"
    }


@pytest.fixture
def postgresql_table_schema():
    """Sample PostgreSQL table schema (uses schema/database field names)."""
    return {
        "table_name": "products",
        "schema": "inventory",
        "database": "warehouse_db",
        "columns": [
            {"name": "product_id", "type": "integer", "is_nullable": False, "description": "Product identifier"},
            {"name": "product_name", "type": "varchar", "is_nullable": False, "description": "Product name"},
            {"name": "price", "type": "numeric", "is_nullable": True, "description": "Product price"}
        ],
        "row_count": 5000,
        "connector_id": "pg_conn_789",
        "organization_id": "test-org",
        "source_database_type": "postgresql"
    }


@pytest.fixture
def redshift_table_schema():
    """Sample Redshift table schema (uses schema/database field names)."""
    return {
        "table_name": "transactions",
        "schema": "finance",
        "database": "data_warehouse",
        "columns": [
            {"name": "txn_id", "type": "bigint", "is_nullable": False, "description": "Transaction ID"},
            {"name": "amount", "type": "decimal", "is_nullable": True, "description": "Transaction amount"},
            {"name": "txn_date", "type": "date", "is_nullable": False, "description": "Transaction date"}
        ],
        "row_count": 100000,
        "connector_id": "rs_conn_101",
        "organization_id": "test-org",
        "source_database_type": "redshift"
    }


@pytest.fixture
def databricks_table_schema():
    """Sample Databricks table schema (uses schema/database field names)."""
    return {
        "table_name": "events",
        "schema": "analytics",
        "database": "lakehouse",
        "columns": [
            {"name": "event_id", "type": "STRING", "is_nullable": False, "description": "Event identifier"},
            {"name": "event_type", "type": "STRING", "is_nullable": False, "description": "Type of event"},
            {"name": "event_timestamp", "type": "TIMESTAMP", "is_nullable": False, "description": "Event time"}
        ],
        "row_count": 1000000,
        "connector_id": "db_conn_202",
        "organization_id": "test-org",
        "source_database_type": "databricks"
    }


@pytest.fixture
def all_database_schemas(
    bigquery_table_schema,
    snowflake_table_schema,
    postgresql_table_schema,
    redshift_table_schema,
    databricks_table_schema
):
    """All database schema fixtures grouped together."""
    return {
        "bigquery": bigquery_table_schema,
        "snowflake": snowflake_table_schema,
        "postgresql": postgresql_table_schema,
        "redshift": redshift_table_schema,
        "databricks": databricks_table_schema
    }


# Pytest configuration
def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (multi-component)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full workflows)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (>10s)"
    )
    config.addinivalue_line(
        "markers", "requires_db: Tests that require database access"
    )
    config.addinivalue_line(
        "markers", "requires_redis: Tests that require Redis"
    )
    config.addinivalue_line(
        "markers", "requires_weaviate: Tests that require Weaviate"
    )
    config.addinivalue_line(
        "markers", "requires_anthropic: Tests that require Anthropic API"
    )
    config.addinivalue_line(
        "markers", "cache: Cache-related tests"
    )
    config.addinivalue_line(
        "markers", "llm: LLM client tests"
    )
    config.addinivalue_line(
        "markers", "sql: SQL generation tests"
    )
    config.addinivalue_line(
        "markers", "connectors: Database connector tests"
    )
    config.addinivalue_line(
        "markers", "api: API route tests"
    )
    config.addinivalue_line(
        "markers", "critical: Critical path tests"
    )
