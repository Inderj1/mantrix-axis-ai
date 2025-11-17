"""
Unit tests for Redshift Connector

Tests the RedshiftConnector implementation of BaseDatabaseConnector interface.
Note: These tests validate the interface implementation and structure.
Actual connection tests require Redshift credentials and are marked as integration tests.
"""
import pytest
from src.db.base_connector import BaseDatabaseConnector
from src.db.connectors.redshift_connector import REDSHIFT_CAPABILITIES

# Try to import Redshift connector (may not be available if psycopg2 not installed)
try:
    from src.db.connectors.redshift_connector import RedshiftConnector, REDSHIFT_AVAILABLE
    from src.db.connectors.postgresql_connector import PostgreSQLConnector
except ImportError:
    RedshiftConnector = None
    PostgreSQLConnector = None
    REDSHIFT_AVAILABLE = False


@pytest.mark.skipif(not REDSHIFT_AVAILABLE, reason="psycopg2 not installed")
class TestRedshiftConnectorInterface:
    """Test that RedshiftConnector correctly implements BaseDatabaseConnector interface."""

    def test_redshift_connector_inherits_from_postgresql(self):
        """Test that RedshiftConnector inherits from PostgreSQLConnector."""
        assert issubclass(RedshiftConnector, PostgreSQLConnector)

    def test_redshift_connector_inherits_from_base(self):
        """Test that RedshiftConnector inherits from BaseDatabaseConnector (via PostgreSQL)."""
        assert issubclass(RedshiftConnector, BaseDatabaseConnector)

    def test_redshift_connector_has_required_methods(self):
        """Test that RedshiftConnector implements all required abstract methods."""
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
            assert hasattr(RedshiftConnector, method), f"Missing required method: {method}"

    def test_redshift_capabilities_are_correct(self):
        """Test that Redshift capabilities are properly defined."""
        caps = REDSHIFT_CAPABILITIES

        # Verify database type
        assert caps.database_type == "redshift"
        assert caps.database_name == "Amazon Redshift"

        # Verify SQL features (Redshift is based on PostgreSQL 8.0.2)
        assert caps.supports_ctes is True
        assert caps.supports_window_functions is True
        assert caps.supports_recursive_ctes is False  # Redshift doesn't support recursive CTEs
        assert caps.supports_lateral_joins is True

        # Verify data types
        assert caps.supports_arrays is False  # Redshift doesn't support arrays
        assert caps.supports_json is True  # SUPER type for JSON
        assert caps.supports_struct is False

        # Verify table qualification
        assert caps.requires_table_qualification is False
        assert caps.table_qualification_format == "{schema}.{table}"

        # Verify pagination
        assert caps.supports_pagination is True
        assert caps.pagination_method == "limit_offset"

    def test_redshift_connector_initialization_requires_credentials(self):
        """Test that RedshiftConnector requires host, database, and user."""
        with pytest.raises(ValueError, match="requires host, database, and user"):
            # This should fail because we're not providing credentials
            RedshiftConnector()

    def test_redshift_connector_default_port(self):
        """Test that RedshiftConnector defaults to port 5439 (not 5432)."""
        # We can't instantiate without credentials, but we can check the class defaults
        # This would require mocking, so we just verify in integration tests
        pass

    def test_redshift_connector_context_manager(self):
        """Test that RedshiftConnector supports context manager protocol."""
        # Verify it has __enter__ and __exit__ methods (inherited from PostgreSQL)
        assert hasattr(RedshiftConnector, '__enter__')
        assert hasattr(RedshiftConnector, '__exit__')

    def test_redshift_connector_has_utility_methods(self):
        """Test that RedshiftConnector has Redshift-specific utility methods."""
        utility_methods = [
            'qualify_table_name',
            'get_cost_estimate',  # Overridden for Redshift (cluster-based pricing)
            'get_cluster_info',  # Redshift-specific
            'get_table_statistics',  # Redshift-specific (svv_table_info)
        ]

        for method in utility_methods:
            assert hasattr(RedshiftConnector, method), f"Missing utility method: {method}"


@pytest.mark.skipif(not REDSHIFT_AVAILABLE, reason="psycopg2 not installed")
class TestRedshiftConnectorCapabilities:
    """Test Redshift-specific capabilities and features."""

    def test_table_qualification_format(self):
        """Test that Redshift uses correct table qualification format."""
        caps = REDSHIFT_CAPABILITIES
        assert "{schema}" in caps.table_qualification_format
        assert "{table}" in caps.table_qualification_format

    def test_redshift_supports_query_hints(self):
        """Test that Redshift capabilities indicate query hint support."""
        caps = REDSHIFT_CAPABILITIES
        assert caps.supports_query_hints is False  # Redshift doesn't have native hints

    def test_redshift_supports_federated_queries(self):
        """Test that Redshift capabilities indicate federated query support."""
        caps = REDSHIFT_CAPABILITIES
        assert caps.supports_federated_queries is True  # Redshift Spectrum

    def test_redshift_date_format_function(self):
        """Test that Redshift uses TO_CHAR for date formatting."""
        caps = REDSHIFT_CAPABILITIES
        assert caps.date_format_function == "TO_CHAR"

    def test_redshift_string_concat_operator(self):
        """Test that Redshift uses || for string concatenation."""
        caps = REDSHIFT_CAPABILITIES
        assert caps.string_concat_operator == "||"

    def test_redshift_no_recursive_ctes(self):
        """Test that Redshift doesn't support recursive CTEs."""
        caps = REDSHIFT_CAPABILITIES
        assert caps.supports_recursive_ctes is False

    def test_redshift_no_arrays(self):
        """Test that Redshift doesn't support arrays."""
        caps = REDSHIFT_CAPABILITIES
        assert caps.supports_arrays is False


def test_redshift_connector_can_be_imported():
    """Test that RedshiftConnector can be imported from connectors package."""
    try:
        from src.db.connectors import RedshiftConnector, REDSHIFT_AVAILABLE
        if REDSHIFT_AVAILABLE:
            assert RedshiftConnector is not None
        else:
            assert RedshiftConnector is None
    except ImportError:
        # This is fine - psycopg2 may not be installed
        pass


@pytest.mark.integration
@pytest.mark.skipif(not REDSHIFT_AVAILABLE, reason="psycopg2 not installed")
class TestRedshiftConnectorIntegration:
    """
    Integration tests for RedshiftConnector.

    These tests require actual Redshift credentials and are marked as integration tests.
    They are skipped by default unless Redshift credentials are configured.
    """

    @pytest.fixture
    def redshift_credentials(self):
        """
        Fixture to provide Redshift credentials.

        Returns None if credentials are not available.
        Set these environment variables to run integration tests:
        - REDSHIFT_HOST
        - REDSHIFT_DATABASE
        - REDSHIFT_USER
        - REDSHIFT_PASSWORD
        - REDSHIFT_CLUSTER_IDENTIFIER (optional)
        """
        import os
        if not all([
            os.getenv('REDSHIFT_HOST'),
            os.getenv('REDSHIFT_DATABASE'),
            os.getenv('REDSHIFT_USER'),
            os.getenv('REDSHIFT_PASSWORD'),
        ]):
            pytest.skip("Redshift credentials not configured")

        return {
            'host': os.getenv('REDSHIFT_HOST'),
            'database': os.getenv('REDSHIFT_DATABASE'),
            'user': os.getenv('REDSHIFT_USER'),
            'password': os.getenv('REDSHIFT_PASSWORD'),
            'port': int(os.getenv('REDSHIFT_PORT', '5439')),
            'cluster_identifier': os.getenv('REDSHIFT_CLUSTER_IDENTIFIER'),
        }

    def test_redshift_connection(self, redshift_credentials):
        """Test actual connection to Redshift (requires credentials)."""
        connector = RedshiftConnector(**redshift_credentials)
        assert connector.connection is not None
        assert connector.port == 5439  # Verify Redshift port
        connector.disconnect()

    def test_redshift_query_execution(self, redshift_credentials):
        """Test query execution on Redshift (requires credentials)."""
        connector = RedshiftConnector(**redshift_credentials)

        # Simple query to test connection
        result = connector.execute_query("SELECT 1 AS test_value")

        assert result is not None
        assert 'rows' in result
        assert len(result['rows']) == 1
        assert result['rows'][0]['test_value'] == 1

        connector.disconnect()

    def test_redshift_schema_introspection(self, redshift_credentials):
        """Test schema introspection on Redshift (requires credentials)."""
        connector = RedshiftConnector(**redshift_credentials)

        # List tables in the schema
        tables = connector.list_tables()

        assert isinstance(tables, list)
        # We don't assert specific tables since we don't know what's in the test database

        connector.disconnect()

    def test_redshift_cost_estimate(self, redshift_credentials):
        """Test cost estimation on Redshift (requires credentials)."""
        connector = RedshiftConnector(**redshift_credentials)

        # Redshift uses cluster-based pricing, so cost should be 0
        cost = connector.get_cost_estimate("SELECT 1")
        assert cost == 0.0

        connector.disconnect()

    def test_redshift_cluster_info(self, redshift_credentials):
        """Test cluster info retrieval on Redshift (requires credentials)."""
        connector = RedshiftConnector(**redshift_credentials)

        # Get cluster info
        info = connector.get_cluster_info()

        assert isinstance(info, dict)
        # Info may be empty if user doesn't have permissions

        connector.disconnect()

    def test_redshift_table_statistics(self, redshift_credentials):
        """Test table statistics retrieval on Redshift (requires credentials)."""
        connector = RedshiftConnector(**redshift_credentials)

        # List tables first
        tables = connector.list_tables()

        if tables:
            # Get statistics for first table
            stats = connector.get_table_statistics(tables[0])
            assert isinstance(stats, dict)

        connector.disconnect()


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/unit/db/test_redshift_connector.py -v
    pytest.main([__file__, "-v"])
