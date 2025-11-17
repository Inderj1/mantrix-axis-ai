"""
Unit tests for Snowflake Connector

Tests the SnowflakeConnector implementation of BaseDatabaseConnector interface.
Note: These tests validate the interface implementation and structure.
Actual connection tests require Snowflake credentials and are marked as integration tests.
"""
import pytest
from src.db.base_connector import BaseDatabaseConnector
from src.db.database_capabilities import SNOWFLAKE_CAPABILITIES

# Try to import Snowflake connector (may not be available if package not installed)
try:
    from src.db.connectors.snowflake_connector import SnowflakeConnector, SNOWFLAKE_AVAILABLE
except ImportError:
    SnowflakeConnector = None
    SNOWFLAKE_AVAILABLE = False


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="snowflake-connector-python not installed")
class TestSnowflakeConnectorInterface:
    """Test that SnowflakeConnector correctly implements BaseDatabaseConnector interface."""

    def test_snowflake_connector_inherits_from_base(self):
        """Test that SnowflakeConnector inherits from BaseDatabaseConnector."""
        assert issubclass(SnowflakeConnector, BaseDatabaseConnector)

    def test_snowflake_connector_has_required_methods(self):
        """Test that SnowflakeConnector implements all required abstract methods."""
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
            assert hasattr(SnowflakeConnector, method), f"Missing required method: {method}"

    def test_snowflake_capabilities_are_correct(self):
        """Test that Snowflake capabilities are properly defined."""
        caps = SNOWFLAKE_CAPABILITIES

        # Verify database type
        assert caps.database_type == "snowflake"
        assert caps.database_name == "Snowflake"

        # Verify SQL features
        assert caps.supports_ctes is True
        assert caps.supports_window_functions is True
        assert caps.supports_recursive_ctes is True
        assert caps.supports_lateral_joins is True

        # Verify data types
        assert caps.supports_arrays is True
        assert caps.supports_json is True
        assert caps.supports_struct is True  # OBJECT and VARIANT types

        # Verify table qualification
        assert caps.requires_table_qualification is True
        assert caps.table_qualification_format == "{database}.{schema}.{table}"

        # Verify pagination
        assert caps.supports_pagination is True
        assert caps.pagination_method == "limit_offset"

    def test_snowflake_connector_initialization_requires_credentials(self):
        """Test that SnowflakeConnector requires account, user, and password."""
        with pytest.raises(ValueError, match="requires account, user, and password"):
            # This should fail because we're not providing credentials
            SnowflakeConnector()

    def test_snowflake_connector_context_manager(self):
        """Test that SnowflakeConnector supports context manager protocol."""
        # Verify it has __enter__ and __exit__ methods
        assert hasattr(SnowflakeConnector, '__enter__')
        assert hasattr(SnowflakeConnector, '__exit__')

    def test_snowflake_connector_has_utility_methods(self):
        """Test that SnowflakeConnector has Snowflake-specific utility methods."""
        utility_methods = [
            'use_warehouse',
            'use_database',
            'use_schema',
            'qualify_table_name',
        ]

        for method in utility_methods:
            assert hasattr(SnowflakeConnector, method), f"Missing utility method: {method}"


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="snowflake-connector-python not installed")
class TestSnowflakeConnectorCapabilities:
    """Test Snowflake-specific capabilities and features."""

    def test_table_qualification_format(self):
        """Test that Snowflake uses correct table qualification format."""
        # We can't actually connect, but we can test the qualification logic
        # This would require mocking, so we'll just verify the capability
        caps = SNOWFLAKE_CAPABILITIES
        assert "{database}" in caps.table_qualification_format
        assert "{schema}" in caps.table_qualification_format
        assert "{table}" in caps.table_qualification_format

    def test_snowflake_supports_query_hints(self):
        """Test that Snowflake capabilities indicate query hint support."""
        caps = SNOWFLAKE_CAPABILITIES
        assert caps.supports_query_hints is True

    def test_snowflake_supports_federated_queries(self):
        """Test that Snowflake capabilities indicate federated query support."""
        caps = SNOWFLAKE_CAPABILITIES
        assert caps.supports_federated_queries is True

    def test_snowflake_date_format_function(self):
        """Test that Snowflake uses TO_CHAR for date formatting."""
        caps = SNOWFLAKE_CAPABILITIES
        assert caps.date_format_function == "TO_CHAR"

    def test_snowflake_string_concat_operator(self):
        """Test that Snowflake uses || for string concatenation."""
        caps = SNOWFLAKE_CAPABILITIES
        assert caps.string_concat_operator == "||"


def test_snowflake_connector_can_be_imported():
    """Test that SnowflakeConnector can be imported from connectors package."""
    try:
        from src.db.connectors import SnowflakeConnector, SNOWFLAKE_AVAILABLE
        if SNOWFLAKE_AVAILABLE:
            assert SnowflakeConnector is not None
        else:
            assert SnowflakeConnector is None
    except ImportError:
        # This is fine - snowflake-connector-python may not be installed
        pass


@pytest.mark.integration
@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="snowflake-connector-python not installed")
class TestSnowflakeConnectorIntegration:
    """
    Integration tests for SnowflakeConnector.

    These tests require actual Snowflake credentials and are marked as integration tests.
    They are skipped by default unless SNOWFLAKE credentials are configured.
    """

    @pytest.fixture
    def snowflake_credentials(self):
        """
        Fixture to provide Snowflake credentials.

        Returns None if credentials are not available.
        Set these environment variables to run integration tests:
        - SNOWFLAKE_ACCOUNT
        - SNOWFLAKE_USER
        - SNOWFLAKE_PASSWORD
        - SNOWFLAKE_WAREHOUSE
        - SNOWFLAKE_DATABASE
        """
        import os
        if not all([
            os.getenv('SNOWFLAKE_ACCOUNT'),
            os.getenv('SNOWFLAKE_USER'),
            os.getenv('SNOWFLAKE_PASSWORD'),
        ]):
            pytest.skip("Snowflake credentials not configured")

        return {
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
            'database': os.getenv('SNOWFLAKE_DATABASE'),
        }

    def test_snowflake_connection(self, snowflake_credentials):
        """Test actual connection to Snowflake (requires credentials)."""
        connector = SnowflakeConnector(**snowflake_credentials)
        assert connector.connection is not None
        connector.disconnect()

    def test_snowflake_query_execution(self, snowflake_credentials):
        """Test query execution on Snowflake (requires credentials)."""
        connector = SnowflakeConnector(**snowflake_credentials)

        # Simple query to test connection
        result = connector.execute_query("SELECT 1 AS test_value")

        assert result is not None
        assert 'rows' in result
        assert len(result['rows']) == 1
        assert result['rows'][0]['TEST_VALUE'] == 1

        connector.disconnect()

    def test_snowflake_schema_introspection(self, snowflake_credentials):
        """Test schema introspection on Snowflake (requires credentials)."""
        connector = SnowflakeConnector(**snowflake_credentials)

        # List tables in the schema
        tables = connector.list_tables()

        assert isinstance(tables, list)
        # We don't assert specific tables since we don't know what's in the test database

        connector.disconnect()


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/unit/db/test_snowflake_connector.py -v
    pytest.main([__file__, "-v"])
