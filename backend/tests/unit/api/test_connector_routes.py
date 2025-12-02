"""
Comprehensive unit tests for Connector API Routes.

Tests cover:
- Helper functions (sanitize_config, serialize_connector)
- GET /types endpoint
- Basic endpoint structure validation
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from bson import ObjectId


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_connector_doc():
    """Sample connector document from MongoDB."""
    return {
        '_id': ObjectId(),
        'connector_type': 'postgresql',
        'name': 'Test PostgreSQL',
        'status': 'connected',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'config': {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'password': 'secret'
        },
        'enabled_for_chat': True,
        'metadata': {
            'table_count': 10,
            'total_size': '100MB',
            'last_sync': datetime.now().isoformat()
        },
        'organization_id': 'test-org',
        'sync_status': 'success',
        'sync_error': None,
        'sync_started_at': None,
        'sync_completed_at': None
    }


# ============================================================================
# TEST HELPER FUNCTIONS
# ============================================================================

class TestSanitizeConfig:
    """Test config sanitization."""

    def test_sanitize_config_masks_password(self):
        """Test that passwords are masked."""
        from src.api.connector_routes import sanitize_config

        config = {'host': 'localhost', 'password': 'secret123'}
        sanitized = sanitize_config(config)

        assert sanitized['password'] == '***'
        assert sanitized['host'] == 'localhost'

    def test_sanitize_config_masks_api_key(self):
        """Test that API keys are masked."""
        from src.api.connector_routes import sanitize_config

        config = {'host': 'localhost', 'api_key': 'sk-123'}
        sanitized = sanitize_config(config)

        assert sanitized['api_key'] == '***'

    def test_sanitize_config_masks_credentials(self):
        """Test that credentials are masked."""
        from src.api.connector_routes import sanitize_config

        config = {'project': 'test', 'credentials': {'key': 'value'}}
        sanitized = sanitize_config(config)

        assert sanitized['credentials'] == '***'

    def test_sanitize_config_masks_secret(self):
        """Test that secrets are masked."""
        from src.api.connector_routes import sanitize_config

        config = {'host': 'localhost', 'secret': 'my-secret-key'}
        sanitized = sanitize_config(config)

        assert sanitized['secret'] == '***'

    def test_sanitize_config_masks_private_key(self):
        """Test that private keys are masked."""
        from src.api.connector_routes import sanitize_config

        config = {'host': 'localhost', 'private_key': '-----BEGIN RSA PRIVATE KEY-----'}
        sanitized = sanitize_config(config)

        assert sanitized['private_key'] == '***'

    def test_sanitize_config_preserves_non_sensitive(self):
        """Test that non-sensitive fields are preserved."""
        from src.api.connector_routes import sanitize_config

        config = {'host': 'localhost', 'port': 5432, 'database': 'testdb'}
        sanitized = sanitize_config(config)

        assert sanitized == config

    def test_sanitize_config_handles_empty_config(self):
        """Test handling of empty config."""
        from src.api.connector_routes import sanitize_config

        config = {}
        sanitized = sanitize_config(config)

        assert sanitized == {}

    def test_sanitize_config_preserves_nested_non_sensitive(self):
        """Test that nested non-sensitive fields are preserved."""
        from src.api.connector_routes import sanitize_config

        config = {'connection': {'host': 'localhost', 'port': 5432}}
        sanitized = sanitize_config(config)

        assert sanitized['connection'] == {'host': 'localhost', 'port': 5432}


class TestSerializeConnector:
    """Test connector serialization."""

    def test_serialize_connector_converts_id(self, sample_connector_doc):
        """Test that ObjectId is converted to string."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert 'id' in result
        assert isinstance(result['id'], str)
        assert result['id'] == str(sample_connector_doc['_id'])

    def test_serialize_connector_includes_connector_type(self, sample_connector_doc):
        """Test that connector type is included."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert result['connector_type'] == 'postgresql'

    def test_serialize_connector_includes_name(self, sample_connector_doc):
        """Test that name is included."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert result['name'] == 'Test PostgreSQL'

    def test_serialize_connector_includes_status(self, sample_connector_doc):
        """Test that status is included."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert result['status'] == 'connected'

    def test_serialize_connector_sanitizes_config(self, sample_connector_doc):
        """Test that config is sanitized."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert result['config']['password'] == '***'
        assert result['config']['host'] == 'localhost'

    def test_serialize_connector_includes_metadata(self, sample_connector_doc):
        """Test that metadata is included."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert 'metadata' in result
        assert result['metadata']['table_count'] == 10
        assert result['metadata']['total_size'] == '100MB'

    def test_serialize_connector_includes_enabled_for_chat(self, sample_connector_doc):
        """Test that enabled_for_chat flag is included."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert result['enabled_for_chat'] is True

    def test_serialize_connector_includes_organization_id(self, sample_connector_doc):
        """Test that organization_id is included."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert result['organization_id'] == 'test-org'

    def test_serialize_connector_includes_sync_status(self, sample_connector_doc):
        """Test that sync status is included."""
        from src.api.connector_routes import serialize_connector

        result = serialize_connector(sample_connector_doc)

        assert result['sync_status'] == 'success'
        assert result['sync_error'] is None

    def test_serialize_connector_handles_missing_metadata(self):
        """Test handling of missing metadata."""
        from src.api.connector_routes import serialize_connector

        doc = {
            '_id': ObjectId(),
            'connector_type': 'postgresql',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'config': {}
        }

        result = serialize_connector(doc)

        assert result['metadata']['table_count'] == 0
        assert result['metadata']['total_size'] == 'Unknown'

    def test_serialize_connector_handles_missing_status(self):
        """Test handling of missing status."""
        from src.api.connector_routes import serialize_connector

        doc = {
            '_id': ObjectId(),
            'connector_type': 'postgresql',
            'name': 'Test',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'config': {}
        }

        result = serialize_connector(doc)

        assert result['status'] == 'disconnected'


# ============================================================================
# TEST GET CONNECTOR TYPES ENDPOINT
# ============================================================================

class TestGetConnectorTypes:
    """Test GET /types endpoint."""

    @pytest.mark.asyncio
    async def test_get_types_returns_supported_types(self):
        """Test that supported types are returned."""
        with patch('src.api.connector_routes.ConnectorFactory') as mock_factory:
            mock_factory.get_supported_types.return_value = {
                'bigquery': True,
                'postgresql': True,
                'snowflake': True
            }
            mock_factory.get_config_template.return_value = {
                'required_fields': ['host'],
                'optional_fields': ['ssl']
            }

            from src.api.connector_routes import get_connector_types

            result = await get_connector_types(current_user=None)

            assert result['success'] is True
            assert 'connector_types' in result
            assert 'bigquery' in result['connector_types']
            assert 'postgresql' in result['connector_types']

    @pytest.mark.asyncio
    async def test_get_types_includes_config_templates(self):
        """Test that config templates are included."""
        with patch('src.api.connector_routes.ConnectorFactory') as mock_factory:
            mock_factory.get_supported_types.return_value = {'bigquery': True}
            mock_factory.get_config_template.return_value = {
                'required_fields': ['project_id', 'dataset_id'],
                'optional_fields': ['credentials_path']
            }

            from src.api.connector_routes import get_connector_types

            result = await get_connector_types(current_user=None)

            connector_types = result['connector_types']
            assert 'required_fields' in connector_types['bigquery']
            assert 'optional_fields' in connector_types['bigquery']
            assert 'project_id' in connector_types['bigquery']['required_fields']

    @pytest.mark.asyncio
    async def test_get_types_handles_unavailable_connector(self):
        """Test handling of unavailable connectors."""
        with patch('src.api.connector_routes.ConnectorFactory') as mock_factory:
            mock_factory.get_supported_types.return_value = {
                'bigquery': True,
                'oracle': False  # Unavailable
            }
            mock_factory.get_config_template.return_value = {
                'required_fields': [],
                'optional_fields': []
            }

            from src.api.connector_routes import get_connector_types

            result = await get_connector_types(current_user=None)

            assert result['connector_types']['oracle']['available'] is False
            assert 'message' in result['connector_types']['oracle']

    @pytest.mark.asyncio
    async def test_get_types_filters_by_user_permissions(self):
        """Test that types are filtered by user permissions."""
        with patch('src.api.connector_routes.ConnectorFactory') as mock_factory:
            mock_factory.get_supported_types_for_user.return_value = {
                'bigquery': {'available': True, 'has_access': True, 'permission_level': 'admin'},
                'postgresql': {'available': True, 'has_access': False, 'permission_level': 'none'}
            }
            mock_factory.get_config_template.return_value = {
                'required_fields': [],
                'optional_fields': []
            }

            from src.api.connector_routes import get_connector_types

            user = {'id': 'user-123', 'organization_id': 'org-123'}
            result = await get_connector_types(current_user=user)

            assert result['success'] is True
            mock_factory.get_supported_types_for_user.assert_called_once_with(
                user_id='user-123',
                organization_id='org-123'
            )

    @pytest.mark.asyncio
    async def test_get_types_without_auth_returns_all(self):
        """Test that types are returned without authentication."""
        with patch('src.api.connector_routes.ConnectorFactory') as mock_factory:
            mock_factory.get_supported_types.return_value = {'bigquery': True}
            mock_factory.get_config_template.return_value = {
                'required_fields': [],
                'optional_fields': []
            }

            from src.api.connector_routes import get_connector_types

            result = await get_connector_types(current_user=None)

            assert result['success'] is True
            mock_factory.get_supported_types.assert_called()
            mock_factory.get_supported_types_for_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_types_handles_template_error(self):
        """Test handling of config template error."""
        with patch('src.api.connector_routes.ConnectorFactory') as mock_factory:
            mock_factory.get_supported_types.return_value = {'bigquery': True}
            mock_factory.get_config_template.side_effect = Exception("Template not found")

            from src.api.connector_routes import get_connector_types

            result = await get_connector_types(current_user=None)

            assert result['success'] is True
            assert 'error' in result['connector_types']['bigquery']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
