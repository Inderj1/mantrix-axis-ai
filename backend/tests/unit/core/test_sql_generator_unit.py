"""
Comprehensive unit tests for SQLGenerator.

Tests cover:
- Initialization with database_config
- Database qualifier methods
- Dialect guide generation
- SQL generation flow
- Schema selection
- Cache integration
- Financial context handling
"""

import pytest
import json
from unittest.mock import MagicMock, patch, PropertyMock, AsyncMock


# ============================================================================
# TEST SQL GENERATOR INITIALIZATION
# ============================================================================

class TestSQLGeneratorInit:
    """Test SQL Generator initialization."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for SQL Generator initialization."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate, \
             patch('src.core.sql_generator.QueryOptimizer') as mock_optimizer, \
             patch('src.core.sql_generator.QuerySuggestionService') as mock_suggestions, \
             patch('src.core.sql_generator.CacheManager') as mock_cache, \
             patch('src.core.sql_generator.FormatNormalizer') as mock_normalizer, \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            # Configure mock settings
            mock_settings.cache_enabled = False  # Disable cache for simpler tests
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"
            mock_settings.redis_url = None
            mock_settings.redis_host = "localhost"
            mock_settings.redis_port = 6379
            mock_settings.redis_db = 0
            mock_settings.redis_decode_responses = False
            mock_settings.redis_max_connections = 50

            # Configure mock factory
            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            yield {
                'llm': mock_llm,
                'weaviate': mock_weaviate,
                'optimizer': mock_optimizer,
                'suggestions': mock_suggestions,
                'cache': mock_cache,
                'normalizer': mock_normalizer,
                'factory': mock_factory,
                'settings': mock_settings,
                'connector': mock_connector,
                'capabilities': mock_capabilities
            }

    def test_init_sets_database_type(self, mock_dependencies):
        """Test that database type is set correctly."""
        from src.core.sql_generator import SQLGenerator
        generator = SQLGenerator(database_type='bigquery')

        assert generator.database_type == 'bigquery'

    def test_init_stores_database_config(self, mock_dependencies):
        """Test that database config is stored."""
        from src.core.sql_generator import SQLGenerator
        config = {"project_id": "custom-project", "dataset_id": "custom-dataset"}

        generator = SQLGenerator(database_type='bigquery', database_config=config)

        assert generator.database_config.get("project_id") == "custom-project"
        assert generator.database_config.get("dataset_id") == "custom-dataset"

    def test_init_validates_database_type(self, mock_dependencies):
        """Test that invalid database types raise error."""
        mock_dependencies['factory'].get_supported_types.return_value = ['bigquery', 'postgresql']

        from src.core.sql_generator import SQLGenerator

        with pytest.raises(ValueError) as exc_info:
            SQLGenerator(database_type='invalid_db')

        assert "Unsupported database type" in str(exc_info.value)

    def test_init_initializes_connector_ids_list(self, mock_dependencies):
        """Test that connector_ids list is initialized."""
        from src.core.sql_generator import SQLGenerator
        generator = SQLGenerator(database_type='bigquery')

        assert hasattr(generator, 'connector_ids')
        assert isinstance(generator.connector_ids, list)

    def test_init_sets_organization_id(self, mock_dependencies):
        """Test that organization ID is set."""
        from src.core.sql_generator import SQLGenerator
        generator = SQLGenerator(database_type='bigquery', organization_id='custom-org')

        assert generator.organization_id == 'custom-org'

    def test_init_defaults_organization_id(self, mock_dependencies):
        """Test that organization ID defaults from settings."""
        from src.core.sql_generator import SQLGenerator
        generator = SQLGenerator(database_type='bigquery')

        assert generator.organization_id == 'test-org'

    def test_init_creates_connector_via_factory(self, mock_dependencies):
        """Test that connector is created via factory."""
        from src.core.sql_generator import SQLGenerator
        generator = SQLGenerator(database_type='bigquery')

        # Verify db_client was set (which means factory was used)
        assert generator.db_client is not None

    def test_init_initializes_llm_client(self, mock_dependencies):
        """Test that LLM client is initialized."""
        from src.core.sql_generator import SQLGenerator
        generator = SQLGenerator(database_type='bigquery')

        mock_dependencies['llm'].assert_called_once()


# ============================================================================
# TEST DATABASE QUALIFIER METHODS
# ============================================================================

class TestDatabaseQualifiers:
    """Test database qualifier methods."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator for testing."""
        with patch('src.core.sql_generator.LLMClient'), \
             patch('src.core.sql_generator.WeaviateClient'), \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_connector.project_id = "my-project"
            mock_connector.dataset_id = "my-dataset"
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            from src.core.sql_generator import SQLGenerator
            return SQLGenerator(database_type='bigquery')

    def test_get_database_qualifier_bigquery(self, sql_generator):
        """Test database qualifier for BigQuery."""
        sql_generator.database_type = 'bigquery'
        sql_generator.db_client.project_id = "my-project"

        qualifier = sql_generator._get_database_qualifier()

        assert qualifier == "my-project"

    def test_get_database_qualifier_snowflake(self, sql_generator):
        """Test database qualifier for Snowflake."""
        sql_generator.database_type = 'snowflake'
        sql_generator.db_client.database = "my-database"

        qualifier = sql_generator._get_database_qualifier()

        assert qualifier == "my-database"

    def test_get_database_qualifier_postgresql(self, sql_generator):
        """Test database qualifier for PostgreSQL."""
        sql_generator.database_type = 'postgresql'
        sql_generator.db_client.database = "my-pg-database"

        qualifier = sql_generator._get_database_qualifier()

        assert qualifier == "my-pg-database"

    def test_get_schema_qualifier_bigquery(self, sql_generator):
        """Test schema qualifier for BigQuery."""
        sql_generator.database_type = 'bigquery'
        sql_generator.db_client.dataset_id = "my-dataset"

        qualifier = sql_generator._get_schema_qualifier()

        assert qualifier == "my-dataset"

    def test_get_schema_qualifier_postgresql(self, sql_generator):
        """Test schema qualifier for PostgreSQL."""
        sql_generator.database_type = 'postgresql'
        sql_generator.db_client.schema = "public"

        qualifier = sql_generator._get_schema_qualifier()

        assert qualifier == "public"

    def test_get_full_qualifier_both_parts(self, sql_generator):
        """Test full qualifier with both parts."""
        sql_generator.db_client.project_id = "project"
        sql_generator.db_client.dataset_id = "dataset"

        qualifier = sql_generator._get_full_qualifier()

        assert qualifier == "project:dataset"

    def test_get_full_qualifier_schema_only(self, sql_generator):
        """Test full qualifier with schema only."""
        sql_generator.db_client.project_id = None
        sql_generator.db_client.dataset_id = "dataset"

        qualifier = sql_generator._get_full_qualifier()

        assert qualifier == "dataset"


# ============================================================================
# TEST DIALECT GUIDE
# ============================================================================

class TestDialectGuide:
    """Test dialect guide generation."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator for testing."""
        with patch('src.core.sql_generator.LLMClient'), \
             patch('src.core.sql_generator.WeaviateClient'), \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            from src.core.sql_generator import SQLGenerator
            return SQLGenerator(database_type='bigquery')

    def test_get_dialect_guide_bigquery(self, sql_generator):
        """Test BigQuery dialect guide."""
        sql_generator.database_type = 'bigquery'
        guide = sql_generator._get_dialect_guide()

        assert "BigQuery" in guide
        assert "backticks" in guide

    def test_get_dialect_guide_snowflake(self, sql_generator):
        """Test Snowflake dialect guide."""
        sql_generator.database_type = 'snowflake'
        guide = sql_generator._get_dialect_guide()

        assert "Snowflake" in guide
        assert "VARIANT" in guide

    def test_get_dialect_guide_postgresql(self, sql_generator):
        """Test PostgreSQL dialect guide."""
        sql_generator.database_type = 'postgresql'
        guide = sql_generator._get_dialect_guide()

        assert "PostgreSQL" in guide
        assert "ILIKE" in guide

    def test_get_dialect_guide_redshift(self, sql_generator):
        """Test Redshift dialect guide."""
        sql_generator.database_type = 'redshift'
        guide = sql_generator._get_dialect_guide()

        assert "Redshift" in guide
        assert "SUPER" in guide

    def test_get_dialect_guide_databricks(self, sql_generator):
        """Test Databricks dialect guide."""
        sql_generator.database_type = 'databricks'
        guide = sql_generator._get_dialect_guide()

        assert "Databricks" in guide
        assert "Delta" in guide

    def test_get_dialect_guide_unknown(self, sql_generator):
        """Test unknown database type returns empty guide."""
        sql_generator.database_type = 'unknown_db'
        guide = sql_generator._get_dialect_guide()

        assert guide == ""


# ============================================================================
# TEST SCHEMA TO TEXT
# ============================================================================

class TestSchemaToText:
    """Test schema to text conversion."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator for testing."""
        with patch('src.core.sql_generator.LLMClient'), \
             patch('src.core.sql_generator.WeaviateClient'), \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            from src.core.sql_generator import SQLGenerator
            return SQLGenerator(database_type='bigquery')

    def test_schema_to_text_includes_table_name(self, sql_generator, sample_table_schema):
        """Test that schema text includes table name."""
        text = sql_generator._schema_to_text(sample_table_schema)

        assert "customers" in text

    def test_schema_to_text_includes_description(self, sql_generator, sample_table_schema):
        """Test that schema text includes description."""
        sample_table_schema['description'] = "Customer master data"
        text = sql_generator._schema_to_text(sample_table_schema)

        assert "Customer master data" in text

    def test_schema_to_text_includes_columns(self, sql_generator, sample_table_schema):
        """Test that schema text includes column information."""
        text = sql_generator._schema_to_text(sample_table_schema)

        assert "customer_id" in text
        assert "STRING" in text

    def test_schema_to_text_includes_column_descriptions(self, sql_generator, sample_table_schema):
        """Test that column descriptions are included."""
        text = sql_generator._schema_to_text(sample_table_schema)

        assert "Customer identifier" in text


# ============================================================================
# TEST GENERATE SQL
# ============================================================================

class TestGenerateSQL:
    """Test SQL generation method."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator with mocked dependencies."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm_class, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate_class, \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings, \
             patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value=None), \
             patch('src.core.sql_generator.SQLGenerator._refresh_connector_ids', return_value=['test-connector-id']):

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            # Setup mock connector
            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_connector.get_dataset_schema.return_value = []
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            # Setup mock LLM
            mock_llm = MagicMock()
            mock_llm.generate_sql.return_value = {
                "sql": "SELECT * FROM customers",
                "explanation": "Query all customers",
                "tables_used": ["customers"],
                "estimated_complexity": "low"
            }
            mock_llm.generate_embedding.return_value = [0.1] * 1536
            mock_llm_class.return_value = mock_llm

            # Setup mock Weaviate
            mock_weaviate = MagicMock()
            mock_weaviate.search_similar_tables.return_value = [
                {
                    "table_name": "customers",
                    "dataset": "test_dataset",
                    "project": "test_project",
                    "columns": [{"name": "customer_id", "type": "STRING"}],
                    "distance": 0.1
                }
            ]
            mock_weaviate_class.return_value = mock_weaviate

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.llm_client = mock_llm
            generator.vector_client = mock_weaviate
            generator.db_client = mock_connector
            generator.bq_client = mock_connector
            generator.enable_financial_features = False
            generator.knowledge_graph = None
            generator.kg_query_resolver = None
            # Set connector_ids to prevent "No database connector configured" error
            generator.connector_ids = ['test-connector-id']

            return generator

    def test_generate_sql_returns_dict(self, sql_generator):
        """Test that generate_sql returns a dictionary."""
        result = sql_generator.generate_sql("Show me all customers")

        assert isinstance(result, dict)

    def test_generate_sql_includes_sql(self, sql_generator):
        """Test that result includes SQL."""
        # Disable format normalizer and optimizer for this test
        sql_generator.format_normalizer = None
        sql_generator.optimizer.optimize_query.return_value = {
            "sql": "SELECT * FROM customers",
            "optimizations_applied": []
        }
        result = sql_generator.generate_sql("Show me all customers")

        assert "sql" in result
        assert result["sql"] is not None
        assert "SELECT" in result["sql"]

    def test_generate_sql_includes_explanation(self, sql_generator):
        """Test that result includes explanation."""
        result = sql_generator.generate_sql("Show me all customers")

        assert "explanation" in result

    def test_generate_sql_includes_tables_used(self, sql_generator):
        """Test that result includes tables_used."""
        result = sql_generator.generate_sql("Show me all customers")

        assert "tables_used" in result
        assert "customers" in result["tables_used"]

    def test_generate_sql_uses_vector_search(self, sql_generator):
        """Test that vector search is used by default."""
        sql_generator.generate_sql("Show me all customers")

        sql_generator.vector_client.search_similar_tables.assert_called()

    def test_generate_sql_passes_database_config_to_llm(self, sql_generator):
        """Test that database_config is passed to LLM."""
        sql_generator.database_config = {"project_id": "my-project", "dataset_id": "my-dataset"}

        sql_generator.generate_sql("Show me all customers")

        call_args = sql_generator.llm_client.generate_sql.call_args
        assert call_args.kwargs.get('database_config') == sql_generator.database_config

    def test_generate_sql_passes_dialect_guide(self, sql_generator):
        """Test that dialect guide is passed to LLM."""
        sql_generator.generate_sql("Show me all customers")

        call_args = sql_generator.llm_client.generate_sql.call_args
        assert 'dialect_guide' in call_args.kwargs

    def test_generate_sql_handles_no_tables(self, sql_generator):
        """Test handling when no relevant tables found."""
        sql_generator.vector_client.search_similar_tables.return_value = []
        sql_generator.bq_client.get_dataset_schema.return_value = []

        result = sql_generator.generate_sql("Show me unicorn data")

        assert "error" in result
        assert result["sql"] is None

    def test_generate_sql_handles_conversation_context(self, sql_generator):
        """Test that conversation context is handled."""
        context = {
            "previous_sql": "SELECT * FROM customers WHERE status = 'active'",
            "follow_up_type": "filter"
        }

        result = sql_generator.generate_sql(
            "Add a limit of 10",
            conversation_context=context
        )

        call_args = sql_generator.llm_client.generate_sql.call_args
        assert call_args.kwargs.get('conversation_context') == context


# ============================================================================
# TEST GET RELEVANT SCHEMAS
# ============================================================================

class TestGetRelevantSchemas:
    """Test schema retrieval methods."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator for testing."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm_class, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate_class, \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            # Setup mock LLM
            mock_llm = MagicMock()
            mock_llm.generate_embedding.return_value = [0.1] * 1536
            mock_llm_class.return_value = mock_llm

            # Setup mock Weaviate
            mock_weaviate = MagicMock()
            mock_weaviate_class.return_value = mock_weaviate

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.llm_client = mock_llm
            generator.vector_client = mock_weaviate
            generator.connector_ids = ["conn_123"]

            return generator

    def test_get_relevant_schemas_uses_embedding(self, sql_generator):
        """Test that embedding is generated for query."""
        sql_generator.vector_client.search_similar_tables.return_value = []

        sql_generator._get_relevant_schemas("Show customers", 5)

        sql_generator.llm_client.generate_embedding.assert_called()

    @pytest.mark.skip(reason="connector_ids filtering disabled until schemas are re-indexed")
    def test_get_relevant_schemas_passes_connector_ids(self, sql_generator):
        """Test that connector_ids are passed to vector search."""
        sql_generator.vector_client.search_similar_tables.return_value = []

        sql_generator._get_relevant_schemas("Show customers", 5)

        call_args = sql_generator.vector_client.search_similar_tables.call_args
        assert call_args.kwargs.get('connector_ids') == ["conn_123"]

    def test_get_relevant_schemas_respects_max_tables(self, sql_generator):
        """Test that max_tables limit is respected."""
        sql_generator.vector_client.search_similar_tables.return_value = []

        # Call with positional argument for max_tables
        sql_generator._get_relevant_schemas("Show customers", 3)

        call_args = sql_generator.vector_client.search_similar_tables.call_args
        assert call_args.kwargs.get('limit') == 3


# ============================================================================
# TEST CACHE INTEGRATION
# ============================================================================

class TestCacheIntegration:
    """Test cache manager integration."""

    @pytest.fixture
    def sql_generator_with_cache(self):
        """Create SQL generator with cache enabled."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm_class, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate_class, \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager') as mock_cache_class, \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            mock_settings.cache_enabled = True
            mock_settings.cache_schema_enabled = True
            mock_settings.cache_embedding_enabled = True
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"
            mock_settings.redis_url = None
            mock_settings.redis_host = "localhost"
            mock_settings.redis_port = 6379
            mock_settings.redis_db = 0
            mock_settings.redis_decode_responses = False
            mock_settings.redis_max_connections = 50
            mock_settings.cache_ttl_sql_frequent = 604800
            mock_settings.cache_ttl_sql_infrequent = 86400
            mock_settings.cache_ttl_schema = 86400
            mock_settings.cache_ttl_embedding = 2592000
            mock_settings.cache_ttl_validation = 3600
            mock_settings.cache_ttl_result = 300
            mock_settings.cache_ttl_session = 86400

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            # Setup mock cache
            mock_cache = MagicMock()
            mock_cache.get_embedding.return_value = None
            mock_cache_class.return_value = mock_cache

            # Setup mock LLM
            mock_llm = MagicMock()
            mock_llm.generate_sql.return_value = {
                "sql": "SELECT * FROM customers",
                "explanation": "Test",
                "tables_used": ["customers"],
                "estimated_complexity": "low"
            }
            mock_llm.generate_embedding.return_value = [0.1] * 1536
            mock_llm_class.return_value = mock_llm

            # Setup mock Weaviate
            mock_weaviate = MagicMock()
            mock_weaviate.search_similar_tables.return_value = [
                {"table_name": "customers", "dataset": "test", "project": "test", "columns": []}
            ]
            mock_weaviate_class.return_value = mock_weaviate

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.llm_client = mock_llm
            generator.vector_client = mock_weaviate
            generator.cache_manager = mock_cache
            generator.enable_financial_features = False
            generator.knowledge_graph = None
            generator.kg_query_resolver = None

            return generator

    def test_cache_manager_initialized_when_enabled(self, sql_generator_with_cache):
        """Test that cache manager is initialized when enabled."""
        assert sql_generator_with_cache.cache_manager is not None

    def test_embedding_cached_after_generation(self, sql_generator_with_cache):
        """Test that embedding is cached after generation."""
        sql_generator_with_cache.cache_manager.get_embedding.return_value = None

        sql_generator_with_cache._get_relevant_schemas("Show customers", 5)

        # Check that embedding was cached
        sql_generator_with_cache.cache_manager.cache_embedding.assert_called()

    def test_cached_embedding_used_when_available(self, sql_generator_with_cache):
        """Test that cached embedding is used when available."""
        cached_embedding = [0.2] * 1536
        sql_generator_with_cache.cache_manager.get_embedding.return_value = cached_embedding

        sql_generator_with_cache._get_relevant_schemas("Show customers", 5)

        # LLM embedding generation should not be called
        sql_generator_with_cache.llm_client.generate_embedding.assert_not_called()


# ============================================================================
# TEST CONNECTOR ID REFRESH
# ============================================================================

class TestConnectorIdRefresh:
    """Test connector ID refresh functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for SQL Generator initialization."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate, \
             patch('src.core.sql_generator.QueryOptimizer') as mock_optimizer, \
             patch('src.core.sql_generator.QuerySuggestionService') as mock_suggestions, \
             patch('src.core.sql_generator.CacheManager') as mock_cache, \
             patch('src.core.sql_generator.FormatNormalizer') as mock_normalizer, \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            # Configure mock settings
            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"
            mock_settings.mongodb_url = "mongodb://localhost:27017"
            mock_settings.mongodb_database = "test_db"
            mock_settings.redis_url = None
            mock_settings.redis_host = "localhost"
            mock_settings.redis_port = 6379
            mock_settings.redis_db = 0
            mock_settings.redis_decode_responses = False
            mock_settings.redis_max_connections = 50

            # Configure mock factory
            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            yield {
                'llm': mock_llm,
                'weaviate': mock_weaviate,
                'optimizer': mock_optimizer,
                'suggestions': mock_suggestions,
                'cache': mock_cache,
                'normalizer': mock_normalizer,
                'factory': mock_factory,
                'settings': mock_settings,
                'connector': mock_connector,
                'capabilities': mock_capabilities
            }

    def test_refresh_connector_ids_called_during_init(self, mock_dependencies):
        """Test that _refresh_connector_ids is called during __init__."""
        from src.core.sql_generator import SQLGenerator

        with patch.object(SQLGenerator, '_refresh_connector_ids') as mock_refresh:
            generator = SQLGenerator(database_type='bigquery')
            mock_refresh.assert_called_once()

    def test_refresh_connector_ids_loads_all_enabled_connectors(self, mock_dependencies):
        """Test that _refresh_connector_ids loads ALL enabled connectors."""
        from src.core.sql_generator import SQLGenerator

        # Mock MongoDB to return multiple connectors
        mock_collection = MagicMock()
        mock_connectors = [
            {"_id": "conn_1", "organization_id": "test-org", "enabled_for_chat": True},
            {"_id": "conn_2", "organization_id": "test-org", "enabled_for_chat": True},
            {"_id": "conn_3", "organization_id": "test-org", "enabled_for_chat": True},
        ]
        mock_collection.find.return_value = mock_connectors

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value={"project_id": "test", "dataset_id": "test"}):
            with patch('pymongo.MongoClient', return_value=mock_client):
                generator = SQLGenerator(database_type='bigquery', organization_id='test-org')

                # Should have all 3 connector IDs
                assert len(generator.connector_ids) == 3
                assert "conn_1" in generator.connector_ids
                assert "conn_2" in generator.connector_ids
                assert "conn_3" in generator.connector_ids

    def test_refresh_connector_ids_filters_by_organization(self, mock_dependencies):
        """Test that _refresh_connector_ids filters by organization_id."""
        from src.core.sql_generator import SQLGenerator

        mock_collection = MagicMock()
        mock_collection.find.return_value = []

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value={"project_id": "test", "dataset_id": "test"}):
            with patch('pymongo.MongoClient', return_value=mock_client):
                generator = SQLGenerator(database_type='bigquery', organization_id='my-org')

                # Verify the query includes organization_id filter
                call_args = mock_collection.find.call_args
                query = call_args[0][0]
                assert query["organization_id"] == "my-org"
                assert query["enabled_for_chat"] == True


# ============================================================================
# TEST LOAD ORG CONNECTOR CONFIG (NO FALLBACK)
# ============================================================================

class TestLoadOrgConnectorConfigNoFallback:
    """Test that _load_org_connector_config doesn't fall back to other orgs."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies."""
        with patch('src.core.sql_generator.LLMClient'), \
             patch('src.core.sql_generator.WeaviateClient'), \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings:

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"
            mock_settings.mongodb_url = "mongodb://localhost:27017"
            mock_settings.mongodb_database = "test_db"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            yield mock_settings

    def test_no_fallback_to_other_organizations(self, mock_dependencies):
        """Test that _load_org_connector_config does NOT fall back to other orgs."""
        from src.core.sql_generator import SQLGenerator

        mock_collection = MagicMock()
        # First query (for specific org) returns None
        # The old code would then do a second query without org filter
        mock_collection.find_one.return_value = None

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch('pymongo.MongoClient', return_value=mock_client):
            generator = SQLGenerator.__new__(SQLGenerator)
            generator.connector_ids = []
            generator.organization_id = "my-org"
            generator.database_type = "bigquery"

            result = generator._load_org_connector_config("my-org", "bigquery")

            # Should return None, NOT try to find connector from another org
            assert result is None

            # Should only call find_one ONCE (no fallback query)
            assert mock_collection.find_one.call_count == 1

            # The single query should have organization_id filter
            call_args = mock_collection.find_one.call_args
            query = call_args[0][0]
            assert query["organization_id"] == "my-org"

    def test_returns_connector_for_matching_org(self, mock_dependencies):
        """Test that correct connector is returned for matching org."""
        from src.core.sql_generator import SQLGenerator

        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "_id": "conn_123",
            "organization_id": "my-org",
            "connector_type": "bigquery",
            "enabled_for_chat": True,
            "config": {"project_id": "my-project", "dataset_id": "my-dataset"}
        }

        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection

        mock_client = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch('pymongo.MongoClient', return_value=mock_client):
            generator = SQLGenerator.__new__(SQLGenerator)
            generator.connector_ids = []
            generator.organization_id = "my-org"
            generator.database_type = "bigquery"

            result = generator._load_org_connector_config("my-org", "bigquery")

            assert result is not None
            assert result["project_id"] == "my-project"
            assert result["dataset_id"] == "my-dataset"


# ============================================================================
# TEST PRE-DETECT TARGET DATABASE
# ============================================================================

class TestPreDetectTargetDatabase:
    """Test pre-detection of target database from schemas."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator for testing."""
        with patch('src.core.sql_generator.LLMClient'), \
             patch('src.core.sql_generator.WeaviateClient'), \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings, \
             patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value={"project_id": "test", "dataset_id": "test"}), \
             patch('src.core.sql_generator.SQLGenerator._refresh_connector_ids', return_value=['test-connector-id']):

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.connector_ids = ['test-connector-id']
            return generator

    def test_returns_snowflake_when_all_schemas_are_snowflake(self, sql_generator):
        """Test that Snowflake is detected when all schemas are from Snowflake."""
        schemas = [
            {"table_name": "SALES_TRANSACTIONS", "database_type": "snowflake"},
            {"table_name": "CUSTOMER_REGION", "database_type": "snowflake"},
        ]
        result = sql_generator._pre_detect_target_database(schemas)
        assert result == "snowflake"

    def test_returns_bigquery_when_all_schemas_are_bigquery(self, sql_generator):
        """Test that BigQuery is detected when all schemas are from BigQuery."""
        schemas = [
            {"table_name": "customer_master", "database_type": "bigquery"},
            {"table_name": "sales_data", "database_type": "bigquery"},
        ]
        result = sql_generator._pre_detect_target_database(schemas)
        assert result == "bigquery"

    def test_returns_federated_when_schemas_are_mixed(self, sql_generator):
        """Test that 'federated' is returned when schemas are from different databases."""
        schemas = [
            {"table_name": "CUSTOMER_REGION", "database_type": "snowflake"},
            {"table_name": "customer_master", "database_type": "bigquery"},
        ]
        result = sql_generator._pre_detect_target_database(schemas)
        assert result == "federated"

    def test_returns_primary_type_when_schemas_empty(self, sql_generator):
        """Test that primary database type is returned when schemas list is empty."""
        schemas = []
        result = sql_generator._pre_detect_target_database(schemas)
        assert result == sql_generator.database_type  # "bigquery"

    def test_returns_single_type_when_only_one_schema(self, sql_generator):
        """Test single schema detection."""
        schemas = [{"table_name": "PRODUCTS", "database_type": "postgresql"}]
        result = sql_generator._pre_detect_target_database(schemas)
        assert result == "postgresql"

    def test_handles_missing_database_type_in_schema(self, sql_generator):
        """Test fallback when schema doesn't have database_type."""
        schemas = [
            {"table_name": "some_table"},  # No database_type
            {"table_name": "another_table"},  # No database_type
        ]
        result = sql_generator._pre_detect_target_database(schemas)
        # Should fallback to primary database type
        assert result == sql_generator.database_type


# ============================================================================
# TEST GET DIALECT GUIDE FOR TYPE
# ============================================================================

class TestGetDialectGuideForType:
    """Test getting dialect guide for specific database type."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator for testing."""
        with patch('src.core.sql_generator.LLMClient'), \
             patch('src.core.sql_generator.WeaviateClient'), \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings, \
             patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value={"project_id": "test", "dataset_id": "test"}), \
             patch('src.core.sql_generator.SQLGenerator._refresh_connector_ids', return_value=['test-connector-id']):

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.connector_ids = ['test-connector-id']
            return generator

    def test_get_snowflake_guide_when_bigquery_primary(self, sql_generator):
        """Test getting Snowflake guide when BigQuery is primary."""
        guide = sql_generator._get_dialect_guide_for_type("snowflake")
        assert "Snowflake" in guide
        assert "backticks" not in guide.lower() or "no backticks" in guide.lower()

    def test_get_bigquery_guide_explicitly(self, sql_generator):
        """Test getting BigQuery guide explicitly."""
        guide = sql_generator._get_dialect_guide_for_type("bigquery")
        assert "BigQuery" in guide
        assert "backticks" in guide

    def test_get_postgresql_guide(self, sql_generator):
        """Test getting PostgreSQL guide."""
        guide = sql_generator._get_dialect_guide_for_type("postgresql")
        assert "PostgreSQL" in guide

    def test_returns_empty_for_unknown_type(self, sql_generator):
        """Test that empty string is returned for unknown database type."""
        guide = sql_generator._get_dialect_guide_for_type("unknown_db")
        assert guide == ""


# ============================================================================
# TEST DIALECT GUIDE PASSED TO LLM
# ============================================================================

class TestDialectGuidePassedToLLM:
    """Test that correct dialect guide is passed to LLM based on schemas."""

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator with mocked dependencies."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm_class, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate_class, \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings, \
             patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value={"project_id": "test-project", "dataset_id": "test-dataset"}), \
             patch('src.core.sql_generator.SQLGenerator._refresh_connector_ids', return_value=['test-connector-id']):

            mock_settings.cache_enabled = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_connector.get_dataset_schema.return_value = []
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            mock_llm = MagicMock()
            mock_llm.generate_sql.return_value = {
                "sql": "SELECT * FROM SALES_TRANSACTIONS",
                "explanation": "Query sales transactions",
                "tables_used": ["SALES_TRANSACTIONS"],
                "estimated_complexity": "low"
            }
            mock_llm.generate_embedding.return_value = [0.1] * 1536
            mock_llm_class.return_value = mock_llm

            mock_weaviate = MagicMock()
            # Return SNOWFLAKE tables from vector search
            mock_weaviate.search_similar_tables.return_value = [
                {
                    "table_name": "SALES_TRANSACTIONS",
                    "database_type": "snowflake",
                    "dataset": "CROSS_DB_TEST",
                    "project": "SNOWFLAKE_LEARNING_DB",
                    "columns": [{"name": "TRANSACTION_ID", "type": "VARCHAR"}],
                    "distance": 0.1
                },
                {
                    "table_name": "CUSTOMER_REGION",
                    "database_type": "snowflake",
                    "dataset": "CROSS_DB_TEST",
                    "project": "SNOWFLAKE_LEARNING_DB",
                    "columns": [{"name": "CUSTOMER_ID", "type": "VARCHAR"}],
                    "distance": 0.2
                }
            ]
            mock_weaviate_class.return_value = mock_weaviate

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.llm_client = mock_llm
            generator.vector_client = mock_weaviate
            generator.db_client = mock_connector
            generator.bq_client = mock_connector
            generator.enable_financial_features = False
            generator.knowledge_graph = None
            generator.kg_query_resolver = None
            generator.connector_ids = ['test-connector-id']

            return generator

    def test_snowflake_dialect_passed_when_schemas_are_snowflake(self, sql_generator):
        """Test that Snowflake dialect guide is passed to LLM when all schemas are Snowflake."""
        sql_generator.generate_sql("Show transactions by region")

        call_args = sql_generator.llm_client.generate_sql.call_args
        dialect_guide = call_args.kwargs.get('dialect_guide', '')
        database_type = call_args.kwargs.get('database_type', '')

        # Should pass Snowflake dialect, not BigQuery
        assert "Snowflake" in dialect_guide
        assert database_type == "snowflake"


# ============================================================================
# TEST TARGET DATABASE TYPE IN RESULT (FIX FOR BACKTICK ISSUE)
# ============================================================================

class TestTargetDatabaseTypeInResult:
    """
    Test that result["target_database_type"] uses pre-detected value.

    This tests the fix for the backtick issue where:
    - Vector search returns Snowflake tables
    - Pre-detection correctly identifies Snowflake
    - Previously, _determine_target_database would override with 'bigquery'
      because table name matching failed (simple name vs qualified name)
    - Now we use the pre-detected value directly
    """

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator with mocked dependencies."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm_class, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate_class, \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings, \
             patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value={"project_id": "test-project", "dataset_id": "test-dataset"}), \
             patch('src.core.sql_generator.SQLGenerator._refresh_connector_ids', return_value=['test-connector-id']):

            mock_settings.cache_enabled = False
            mock_settings.cache_sql_enabled = False
            mock_settings.cache_validation_enabled = False
            mock_settings.cache_execution_test_required = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_connector.get_dataset_schema.return_value = []
            mock_connector.validate_query.return_value = {"valid": True}
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            # Create a mock Snowflake connector for _get_connector_for_database
            mock_snowflake_connector = MagicMock()
            mock_snowflake_connector.validate_query.return_value = {"valid": True}

            mock_llm = MagicMock()
            mock_llm.generate_sql.return_value = {
                "sql": "SELECT SUM(t.TRANSACTION_AMOUNT) AS total_amount, r.REGION "
                       "FROM SNOWFLAKE_LEARNING_DB.CROSS_DB_TEST.SALES_TRANSACTIONS t "
                       "JOIN SNOWFLAKE_LEARNING_DB.CROSS_DB_TEST.CUSTOMER_REGION r ON t.CUSTOMER_ID = r.CUSTOMER_ID "
                       "GROUP BY r.REGION",
                "explanation": "Query total transaction amount by region",
                "tables_used": ["SALES_TRANSACTIONS", "CUSTOMER_REGION"],  # Simple names (not qualified)
                "estimated_complexity": "medium"
            }
            mock_llm.generate_embedding.return_value = [0.1] * 1536
            mock_llm_class.return_value = mock_llm

            mock_weaviate = MagicMock()
            # Return SNOWFLAKE tables with QUALIFIED names (schema.table format)
            mock_weaviate.search_similar_tables.return_value = [
                {
                    "table_name": "CROSS_DB_TEST.SALES_TRANSACTIONS",  # Qualified name
                    "database_type": "snowflake",
                    "dataset": "CROSS_DB_TEST",
                    "project": "SNOWFLAKE_LEARNING_DB",
                    "columns": [{"name": "TRANSACTION_ID", "type": "VARCHAR"}],
                    "distance": 0.1
                },
                {
                    "table_name": "CROSS_DB_TEST.CUSTOMER_REGION",  # Qualified name
                    "database_type": "snowflake",
                    "dataset": "CROSS_DB_TEST",
                    "project": "SNOWFLAKE_LEARNING_DB",
                    "columns": [{"name": "CUSTOMER_ID", "type": "VARCHAR"}],
                    "distance": 0.2
                }
            ]
            mock_weaviate_class.return_value = mock_weaviate

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.llm_client = mock_llm
            generator.vector_client = mock_weaviate
            generator.db_client = mock_connector
            generator.bq_client = mock_connector
            generator.enable_financial_features = False
            generator.knowledge_graph = None
            generator.kg_query_resolver = None
            generator.connector_ids = ['test-connector-id']
            generator.format_normalizer = None
            generator.optimizer = MagicMock()
            generator.optimizer.optimize_query.return_value = {"optimized_sql": None}
            generator.suggestion_service = MagicMock()
            generator.suggestion_service.suggest_query_improvements.return_value = []
            # Mock _get_connector_for_database to return a Snowflake connector
            generator._get_connector_for_database = MagicMock(
                return_value=(mock_snowflake_connector, "snowflake-connector-id")
            )

            return generator

    def test_result_has_snowflake_type_when_schemas_are_snowflake(self, sql_generator):
        """
        Test that result["target_database_type"] is "snowflake" when all schemas are Snowflake.

        This verifies the fix for the issue where:
        - LLM returns tables_used: ["SALES_TRANSACTIONS"] (simple name)
        - Schema has table_name: "CROSS_DB_TEST.SALES_TRANSACTIONS" (qualified)
        - Old code: _determine_target_database failed to match, returned "bigquery"
        - New code: Uses pre-detected value ("snowflake") directly
        """
        result = sql_generator.generate_sql("Show total transaction amount by region")

        assert result.get("target_database_type") == "snowflake", \
            f"Expected 'snowflake' but got '{result.get('target_database_type')}'. " \
            "This indicates the pre-detected database type is not being used correctly."

    def test_requires_alternate_connector_when_target_differs(self, sql_generator):
        """Test that requires_alternate_connector is set when target differs from primary."""
        result = sql_generator.generate_sql("Show transactions by region")

        # Since primary is BigQuery and target is Snowflake, should require alternate connector
        assert result.get("requires_alternate_connector") == True

    def test_pre_detected_type_not_overwritten_by_failed_table_matching(self, sql_generator):
        """
        Test that pre-detected type is preserved even when table name matching fails.

        The old _determine_target_database would:
        1. Try to match "SALES_TRANSACTIONS" (from LLM) with "CROSS_DB_TEST.SALES_TRANSACTIONS" (from schema)
        2. Fail because exact match fails
        3. Return self.database_type ("bigquery") as fallback

        The new code should use pre-detected value directly.
        """
        # Verify the generator's primary type is BigQuery (different from target)
        assert sql_generator.database_type == "bigquery"

        result = sql_generator.generate_sql("Show total amount by region from sales")

        # Pre-detection should have detected Snowflake from schemas
        # This should NOT be overwritten to BigQuery
        assert result.get("target_database_type") != "bigquery", \
            "target_database_type was incorrectly set to primary database type (bigquery). " \
            "The pre-detected type (snowflake) should have been used."


# ============================================================================
# TEST DATABASE TYPE MUTATION (FIX FOR CONNECTOR MISMATCH BUG)
# ============================================================================

class TestDatabaseTypeMutation:
    """
    Test that self.database_type is NOT mutated during query processing.

    This tests the fix for the bug where:
    - self.database_type was changed to 'snowflake' during multi-connector query
    - But self.db_client and self.connector_ids[0] stayed as BigQuery
    - This caused _get_connector_for_database('snowflake') to return BigQuery connector
    """

    @pytest.fixture
    def sql_generator(self):
        """Create SQL generator with mocked dependencies."""
        with patch('src.core.sql_generator.LLMClient') as mock_llm_class, \
             patch('src.core.sql_generator.WeaviateClient') as mock_weaviate_class, \
             patch('src.core.sql_generator.QueryOptimizer'), \
             patch('src.core.sql_generator.QuerySuggestionService'), \
             patch('src.core.sql_generator.CacheManager'), \
             patch('src.core.sql_generator.FormatNormalizer'), \
             patch('src.core.sql_generator.ConnectorFactory') as mock_factory, \
             patch('src.core.sql_generator.settings') as mock_settings, \
             patch('src.core.sql_generator.SQLGenerator._load_org_connector_config', return_value={"project_id": "test-project", "dataset_id": "test-dataset"}), \
             patch('src.core.sql_generator.SQLGenerator._refresh_connector_ids', return_value=['test-connector-id']):

            mock_settings.cache_enabled = False
            mock_settings.cache_sql_enabled = False
            mock_settings.cache_validation_enabled = False
            mock_settings.cache_execution_test_required = False
            mock_settings.enable_industry_features = False
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"
            mock_settings.default_org_id = "test-org"

            mock_connector = MagicMock()
            mock_capabilities = MagicMock()
            mock_capabilities.database_name = "BigQuery"
            mock_connector.get_capabilities.return_value = mock_capabilities
            mock_connector.get_dataset_schema.return_value = []
            mock_connector.validate_query.return_value = {"valid": True}
            mock_factory.create_connector.return_value = mock_connector
            mock_factory.get_supported_types.return_value = ['bigquery', 'postgresql', 'snowflake', 'redshift', 'databricks']

            mock_snowflake_connector = MagicMock()
            mock_snowflake_connector.validate_query.return_value = {"valid": True}

            mock_llm = MagicMock()
            mock_llm.generate_sql.return_value = {
                "sql": "SELECT * FROM SNOWFLAKE_LEARNING_DB.CROSS_DB_TEST.SALES_TRANSACTIONS",
                "explanation": "Query sales transactions",
                "tables_used": ["SALES_TRANSACTIONS"],
                "estimated_complexity": "low"
            }
            mock_llm.generate_embedding.return_value = [0.1] * 1536
            mock_llm_class.return_value = mock_llm

            mock_weaviate = MagicMock()
            mock_weaviate.search_similar_tables.return_value = [
                {
                    "table_name": "SALES_TRANSACTIONS",
                    "database_type": "snowflake",
                    "dataset": "CROSS_DB_TEST",
                    "project": "SNOWFLAKE_LEARNING_DB",
                    "columns": [{"name": "TRANSACTION_ID", "type": "VARCHAR"}],
                    "distance": 0.1
                }
            ]
            mock_weaviate_class.return_value = mock_weaviate

            from src.core.sql_generator import SQLGenerator
            generator = SQLGenerator(database_type='bigquery')
            generator.llm_client = mock_llm
            generator.vector_client = mock_weaviate
            generator.db_client = mock_connector
            generator.bq_client = mock_connector
            generator.enable_financial_features = False
            generator.knowledge_graph = None
            generator.kg_query_resolver = None
            generator.connector_ids = ['bq-connector-id', 'sf-connector-id']
            generator.connector_db_types = {
                'bq-connector-id': 'bigquery',
                'sf-connector-id': 'snowflake'
            }
            generator.format_normalizer = None
            generator.optimizer = MagicMock()
            generator.optimizer.optimize_query.return_value = {"optimized_sql": None}
            generator.suggestion_service = MagicMock()
            generator.suggestion_service.suggest_query_improvements.return_value = []
            generator._get_connector_for_database = MagicMock(
                return_value=(mock_snowflake_connector, "sf-connector-id")
            )

            return generator

    def test_database_type_not_mutated_when_target_is_snowflake(self, sql_generator):
        """
        Test that self.database_type remains 'bigquery' even when target is Snowflake.

        The target database type should be tracked in result["target_database_type"],
        NOT by mutating self.database_type.
        """
        # Store original database_type
        original_db_type = sql_generator.database_type
        assert original_db_type == "bigquery", "Primary DB should be BigQuery"

        # Generate SQL for Snowflake target
        result = sql_generator.generate_sql("Show total sales")

        # self.database_type should NOT have changed
        assert sql_generator.database_type == original_db_type, \
            f"self.database_type was mutated from 'bigquery' to '{sql_generator.database_type}'. " \
            "This mutation causes _get_connector_for_database to return the wrong connector."

    def test_primary_connector_preserved_after_snowflake_query(self, sql_generator):
        """
        Test that primary connector (BigQuery) is still accessible after Snowflake query.

        The issue was that mutating self.database_type made the primary connector
        inaccessible because _get_connector_for_database would return wrong connector.
        """
        # Generate Snowflake query
        sql_generator.generate_sql("Show sales data")

        # db_client should still be the original BigQuery connector
        assert sql_generator.db_client is not None
        # And database_type should still be 'bigquery'
        assert sql_generator.database_type == "bigquery"


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_table_schema():
    """Sample table schema for tests."""
    return {
        "table_name": "customers",
        "columns": [
            {"name": "customer_id", "type": "STRING", "description": "Customer identifier"},
            {"name": "name", "type": "STRING", "description": "Customer name"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "Creation timestamp"}
        ]
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
