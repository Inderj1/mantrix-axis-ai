"""
Unit tests for Databricks Connector

Tests the DatabricksConnector implementation of BaseDatabaseConnector interface.
Note: These tests validate the interface implementation and structure.
Actual connection tests require Databricks credentials and are marked as integration tests.
"""
import pytest
from src.db.base_connector import BaseDatabaseConnector
from src.db.connectors.databricks_connector import DATABRICKS_CAPABILITIES

# Try to import Databricks connector (may not be available if package not installed)
try:
    from src.db.connectors.databricks_connector import DatabricksConnector, DATABRICKS_AVAILABLE
except ImportError:
    DatabricksConnector = None
    DATABRICKS_AVAILABLE = False


@pytest.mark.skipif(not DATABRICKS_AVAILABLE, reason="databricks-sql-connector not installed")
class TestDatabricksConnectorInterface:
    """Test that DatabricksConnector correctly implements BaseDatabaseConnector interface."""

    def test_databricks_connector_inherits_from_base(self):
        """Test that DatabricksConnector inherits from BaseDatabaseConnector."""
        assert issubclass(DatabricksConnector, BaseDatabaseConnector)

    def test_databricks_connector_has_required_methods(self):
        """Test that DatabricksConnector implements all required abstract methods."""
        required_methods = [
            'connect',
            'disconnect',
            'execute_query',
            'get_table_schema',
            'list_tables',
            'get_dataset_schema',
            'validate_query',
            'get_capabilities',
        ]

        for method in required_methods:
            assert hasattr(DatabricksConnector, method), f"Missing required method: {method}"

    def test_databricks_capabilities_are_correct(self):
        """Test that Databricks capabilities are properly defined."""
        caps = DATABRICKS_CAPABILITIES

        # Verify database type
        assert caps.database_type == "databricks"
        assert caps.database_name == "Databricks SQL"

        # Verify SQL features (Spark SQL)
        assert caps.supports_ctes is True
        assert caps.supports_window_functions is True
        assert caps.supports_recursive_ctes is False  # Spark SQL doesn't support recursive CTEs
        assert caps.supports_lateral_joins is True

        # Verify data types (strong support for complex types)
        assert caps.supports_arrays is True
        assert caps.supports_json is True
        assert caps.supports_struct is True  # Spark SQL supports struct, array, map

        # Verify table qualification (Unity Catalog)
        assert caps.requires_table_qualification is True
        assert caps.table_qualification_format == "{catalog}.{schema}.{table}"

        # Verify pagination
        assert caps.supports_pagination is True
        assert caps.pagination_method == "limit_offset"

    def test_databricks_connector_initialization_requires_credentials(self):
        """Test that DatabricksConnector requires server_hostname, http_path, and access_token."""
        with pytest.raises(ValueError, match="requires server_hostname, http_path, and access_token"):
            # This should fail because we're not providing credentials
            DatabricksConnector()

    def test_databricks_connector_context_manager(self):
        """Test that DatabricksConnector supports context manager protocol."""
        # Verify it has __enter__ and __exit__ methods
        assert hasattr(DatabricksConnector, '__enter__')
        assert hasattr(DatabricksConnector, '__exit__')


@pytest.mark.skipif(not DATABRICKS_AVAILABLE, reason="databricks-sql-connector not installed")
class TestDatabricksConnectorCapabilities:
    """Test Databricks-specific capabilities and features."""

    def test_table_qualification_format(self):
        """Test that Databricks uses Unity Catalog qualification format."""
        caps = DATABRICKS_CAPABILITIES
        assert "{catalog}" in caps.table_qualification_format
        assert "{schema}" in caps.table_qualification_format
        assert "{table}" in caps.table_qualification_format

    def test_databricks_supports_query_hints(self):
        """Test that Databricks capabilities indicate query hint support."""
        caps = DATABRICKS_CAPABILITIES
        assert caps.supports_query_hints is True  # Spark SQL supports hints

    def test_databricks_supports_federated_queries(self):
        """Test that Databricks capabilities indicate federated query support."""
        caps = DATABRICKS_CAPABILITIES
        assert caps.supports_federated_queries is True  # Unity Catalog external tables

    def test_databricks_date_format_function(self):
        """Test that Databricks uses DATE_FORMAT for date formatting."""
        caps = DATABRICKS_CAPABILITIES
        assert caps.date_format_function == "DATE_FORMAT"

    def test_databricks_string_concat_operator(self):
        """Test that Databricks uses || for string concatenation."""
        caps = DATABRICKS_CAPABILITIES
        assert caps.string_concat_operator == "||"

    def test_databricks_complex_types(self):
        """Test that Databricks supports complex types (arrays, structs, maps)."""
        caps = DATABRICKS_CAPABILITIES
        assert caps.supports_arrays is True
        assert caps.supports_struct is True
        assert caps.supports_json is True

    def test_databricks_no_recursive_ctes(self):
        """Test that Databricks doesn't support recursive CTEs."""
        caps = DATABRICKS_CAPABILITIES
        assert caps.supports_recursive_ctes is False


def test_databricks_connector_can_be_imported():
    """Test that DatabricksConnector can be imported from connectors package."""
    try:
        from src.db.connectors import DatabricksConnector, DATABRICKS_AVAILABLE
        if DATABRICKS_AVAILABLE:
            assert DatabricksConnector is not None
        else:
            assert DatabricksConnector is None
    except ImportError:
        # This is fine - databricks-sql-connector may not be installed
        pass


@pytest.mark.integration
@pytest.mark.skipif(not DATABRICKS_AVAILABLE, reason="databricks-sql-connector not installed")
class TestDatabricksConnectorIntegration:
    """
    Integration tests for DatabricksConnector.

    These tests require actual Databricks credentials and are marked as integration tests.
    They are skipped by default unless Databricks credentials are configured.
    """

    @pytest.fixture
    def databricks_credentials(self):
        """
        Fixture to provide Databricks credentials.

        Returns None if credentials are not available.
        Set these environment variables to run integration tests:
        - DATABRICKS_SERVER_HOSTNAME (e.g., your-workspace.cloud.databricks.com)
        - DATABRICKS_HTTP_PATH (e.g., /sql/1.0/warehouses/warehouse-id)
        - DATABRICKS_ACCESS_TOKEN
        - DATABRICKS_CATALOG (optional, defaults to "main")
        - DATABRICKS_SCHEMA (optional, defaults to "default")
        """
        import os
        if not all([
            os.getenv('DATABRICKS_SERVER_HOSTNAME'),
            os.getenv('DATABRICKS_HTTP_PATH'),
            os.getenv('DATABRICKS_ACCESS_TOKEN'),
        ]):
            pytest.skip("Databricks credentials not configured")

        return {
            'server_hostname': os.getenv('DATABRICKS_SERVER_HOSTNAME'),
            'http_path': os.getenv('DATABRICKS_HTTP_PATH'),
            'access_token': os.getenv('DATABRICKS_ACCESS_TOKEN'),
            'catalog': os.getenv('DATABRICKS_CATALOG', 'main'),
            'schema': os.getenv('DATABRICKS_SCHEMA', 'default'),
        }

    def test_databricks_connection(self, databricks_credentials):
        """Test actual connection to Databricks (requires credentials)."""
        connector = DatabricksConnector(**databricks_credentials)
        assert connector.connection is not None
        connector.disconnect()

    def test_databricks_query_execution(self, databricks_credentials):
        """Test query execution on Databricks (requires credentials)."""
        connector = DatabricksConnector(**databricks_credentials)

        # Simple query to test connection
        result = connector.execute_query("SELECT 1 AS test_value")

        assert result is not None
        assert 'rows' in result
        assert len(result['rows']) == 1
        assert result['rows'][0]['test_value'] == 1

        connector.disconnect()

    def test_databricks_schema_introspection(self, databricks_credentials):
        """Test schema introspection on Databricks (requires credentials)."""
        connector = DatabricksConnector(**databricks_credentials)

        # List tables in the schema
        tables = connector.list_tables()

        assert isinstance(tables, list)
        # We don't assert specific tables since we don't know what's in the test catalog

        connector.disconnect()

    def test_databricks_validate_query(self, databricks_credentials):
        """Test query validation on Databricks (requires credentials)."""
        connector = DatabricksConnector(**databricks_credentials)

        # Valid query
        result = connector.validate_query("SELECT 1")
        assert result['valid'] is True
        assert 'explain_plan' in result

        # Invalid query
        result = connector.validate_query("SELECT FROM WHERE")
        assert result['valid'] is False
        assert result['error'] is not None

        connector.disconnect()

    def test_databricks_table_schema_with_unity_catalog(self, databricks_credentials):
        """Test table schema retrieval with Unity Catalog (requires credentials)."""
        connector = DatabricksConnector(**databricks_credentials)

        # List tables first
        tables = connector.list_tables()

        if tables:
            # Get schema for first table
            schema = connector.get_table_schema(tables[0])

            assert isinstance(schema, dict)
            assert 'table_name' in schema
            assert 'columns' in schema
            assert 'catalog' in schema or 'database' in schema
            assert isinstance(schema['columns'], list)

            # Verify columns have required fields
            if schema['columns']:
                first_column = schema['columns'][0]
                assert 'name' in first_column
                assert 'type' in first_column

        connector.disconnect()

    def test_databricks_pagination(self, databricks_credentials):
        """Test query pagination on Databricks (requires credentials)."""
        connector = DatabricksConnector(**databricks_credentials)

        # Query with limit
        result = connector.execute_query("SELECT 1 AS test", limit=1)

        assert result is not None
        assert 'rows' in result
        assert len(result['rows']) <= 1

        connector.disconnect()

    def test_databricks_complex_types(self, databricks_credentials):
        """Test Databricks support for complex types (requires credentials)."""
        connector = DatabricksConnector(**databricks_credentials)

        # Test array support
        result = connector.execute_query("SELECT array(1, 2, 3) AS test_array")
        assert result is not None
        assert 'rows' in result
        assert len(result['rows']) == 1

        # Test struct support
        result = connector.execute_query("SELECT struct('a' AS field1, 'b' AS field2) AS test_struct")
        assert result is not None
        assert 'rows' in result
        assert len(result['rows']) == 1

        connector.disconnect()


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/unit/db/test_databricks_connector.py -v
    pytest.main([__file__, "-v"])
