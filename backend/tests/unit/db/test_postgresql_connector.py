"""
Unit tests for PostgreSQL Connector

Tests the PostgreSQLConnector implementation of BaseDatabaseConnector interface.
Note: These tests validate the interface implementation and structure.
Actual connection tests require PostgreSQL credentials and are marked as integration tests.
"""
import pytest
from src.db.base_connector import BaseDatabaseConnector
from src.db.connectors.postgresql_connector import POSTGRESQL_CAPABILITIES

# Try to import PostgreSQL connector (may not be available if package not installed)
try:
    from src.db.connectors.postgresql_connector import PostgreSQLConnector, POSTGRESQL_AVAILABLE
except ImportError:
    PostgreSQLConnector = None
    POSTGRESQL_AVAILABLE = False


@pytest.mark.skipif(not POSTGRESQL_AVAILABLE, reason="psycopg2 not installed")
class TestPostgreSQLConnectorInterface:
    """Test that PostgreSQLConnector correctly implements BaseDatabaseConnector interface."""

    def test_postgresql_connector_inherits_from_base(self):
        """Test that PostgreSQLConnector inherits from BaseDatabaseConnector."""
        assert issubclass(PostgreSQLConnector, BaseDatabaseConnector)

    def test_postgresql_connector_has_required_methods(self):
        """Test that PostgreSQLConnector implements all required abstract methods."""
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
            assert hasattr(PostgreSQLConnector, method), f"Missing required method: {method}"

    def test_postgresql_capabilities_are_correct(self):
        """Test that PostgreSQL capabilities are properly defined."""
        caps = POSTGRESQL_CAPABILITIES

        # Verify database type
        assert caps.database_type == "postgresql"
        assert caps.database_name == "PostgreSQL"

        # Verify SQL features
        assert caps.supports_ctes is True
        assert caps.supports_window_functions is True
        assert caps.supports_recursive_ctes is True
        assert caps.supports_lateral_joins is True

        # Verify data types
        assert caps.supports_arrays is True
        assert caps.supports_json is True  # JSONB
        assert caps.supports_struct is False  # PostgreSQL uses composite types differently

        # Verify table qualification
        assert caps.requires_table_qualification is False  # Schema is optional
        assert caps.table_qualification_format == "{schema}.{table}"

        # Verify pagination
        assert caps.supports_pagination is True
        assert caps.pagination_method == "limit_offset"

    def test_postgresql_connector_initialization_requires_credentials(self):
        """Test that PostgreSQLConnector requires host, database, and user."""
        with pytest.raises(ValueError, match="requires host, database, and user"):
            # This should fail because we're not providing credentials
            PostgreSQLConnector()

    def test_postgresql_connector_context_manager(self):
        """Test that PostgreSQLConnector supports context manager protocol."""
        # Verify it has __enter__ and __exit__ methods
        assert hasattr(PostgreSQLConnector, '__enter__')
        assert hasattr(PostgreSQLConnector, '__exit__')

    def test_postgresql_connector_has_utility_methods(self):
        """Test that PostgreSQLConnector has PostgreSQL-specific utility methods."""
        utility_methods = [
            'qualify_table_name',
        ]

        for method in utility_methods:
            assert hasattr(PostgreSQLConnector, method), f"Missing utility method: {method}"


@pytest.mark.skipif(not POSTGRESQL_AVAILABLE, reason="psycopg2 not installed")
class TestPostgreSQLConnectorCapabilities:
    """Test PostgreSQL-specific capabilities and features."""

    def test_table_qualification_format(self):
        """Test that PostgreSQL uses correct table qualification format."""
        caps = POSTGRESQL_CAPABILITIES
        assert "{schema}" in caps.table_qualification_format
        assert "{table}" in caps.table_qualification_format

    def test_postgresql_supports_query_hints(self):
        """Test that PostgreSQL capabilities indicate query hint support."""
        caps = POSTGRESQL_CAPABILITIES
        assert caps.supports_query_hints is False  # PostgreSQL doesn't have native hints

    def test_postgresql_supports_federated_queries(self):
        """Test that PostgreSQL capabilities indicate federated query support."""
        caps = POSTGRESQL_CAPABILITIES
        assert caps.supports_federated_queries is True  # Foreign Data Wrappers

    def test_postgresql_date_format_function(self):
        """Test that PostgreSQL uses TO_CHAR for date formatting."""
        caps = POSTGRESQL_CAPABILITIES
        assert caps.date_format_function == "TO_CHAR"

    def test_postgresql_string_concat_operator(self):
        """Test that PostgreSQL uses || for string concatenation."""
        caps = POSTGRESQL_CAPABILITIES
        assert caps.string_concat_operator == "||"


def test_postgresql_connector_can_be_imported():
    """Test that PostgreSQLConnector can be imported from connectors package."""
    try:
        from src.db.connectors import PostgreSQLConnector, POSTGRESQL_AVAILABLE
        if POSTGRESQL_AVAILABLE:
            assert PostgreSQLConnector is not None
        else:
            assert PostgreSQLConnector is None
    except ImportError:
        # This is fine - psycopg2 may not be installed
        pass


@pytest.mark.integration
@pytest.mark.skipif(not POSTGRESQL_AVAILABLE, reason="psycopg2 not installed")
class TestPostgreSQLConnectorIntegration:
    """
    Integration tests for PostgreSQLConnector.

    These tests require actual PostgreSQL credentials and are marked as integration tests.
    They are skipped by default unless PostgreSQL credentials are configured.
    """

    @pytest.fixture
    def postgresql_credentials(self):
        """
        Fixture to provide PostgreSQL credentials.

        Returns None if credentials are not available.
        Set these environment variables to run integration tests:
        - EXTERNAL_POSTGRES_HOST
        - EXTERNAL_POSTGRES_DATABASE
        - EXTERNAL_POSTGRES_USER
        - EXTERNAL_POSTGRES_PASSWORD (optional)
        """
        import os
        if not all([
            os.getenv('EXTERNAL_POSTGRES_HOST'),
            os.getenv('EXTERNAL_POSTGRES_DATABASE'),
            os.getenv('EXTERNAL_POSTGRES_USER'),
        ]):
            pytest.skip("PostgreSQL credentials not configured")

        return {
            'host': os.getenv('EXTERNAL_POSTGRES_HOST'),
            'database': os.getenv('EXTERNAL_POSTGRES_DATABASE'),
            'user': os.getenv('EXTERNAL_POSTGRES_USER'),
            'password': os.getenv('EXTERNAL_POSTGRES_PASSWORD', ''),
            'port': int(os.getenv('EXTERNAL_POSTGRES_PORT', '5432')),
        }

    def test_postgresql_connection(self, postgresql_credentials):
        """Test actual connection to PostgreSQL (requires credentials)."""
        connector = PostgreSQLConnector(**postgresql_credentials)
        assert connector.connection is not None
        connector.disconnect()

    def test_postgresql_query_execution(self, postgresql_credentials):
        """Test query execution on PostgreSQL (requires credentials)."""
        connector = PostgreSQLConnector(**postgresql_credentials)

        # Simple query to test connection
        result = connector.execute_query("SELECT 1 AS test_value")

        assert result is not None
        assert 'rows' in result
        assert len(result['rows']) == 1
        assert result['rows'][0]['test_value'] == 1

        connector.disconnect()

    def test_postgresql_schema_introspection(self, postgresql_credentials):
        """Test schema introspection on PostgreSQL (requires credentials)."""
        connector = PostgreSQLConnector(**postgresql_credentials)

        # List tables in the schema
        tables = connector.list_tables()

        assert isinstance(tables, list)
        # We don't assert specific tables since we don't know what's in the test database

        connector.disconnect()

    def test_postgresql_validate_query(self, postgresql_credentials):
        """Test query validation on PostgreSQL (requires credentials)."""
        connector = PostgreSQLConnector(**postgresql_credentials)

        # Valid query
        result = connector.validate_query("SELECT 1")
        assert result['valid'] is True

        # Invalid query
        result = connector.validate_query("SELECT FROM WHERE")
        assert result['valid'] is False
        assert result['error'] is not None

        connector.disconnect()


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/unit/db/test_postgresql_connector.py -v
    pytest.main([__file__, "-v"])
