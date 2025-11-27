"""
Database Connector Factory

Factory pattern for creating database connector instances based on type.
Supports BigQuery, Snowflake, PostgreSQL, and future connectors.
Includes permission checking and access control.
"""
from typing import Dict, Any, Optional, List
import structlog

from .base_connector import BaseDatabaseConnector
from .connectors import (
    BigQueryConnector,
    SnowflakeConnector,
    SNOWFLAKE_AVAILABLE,
    PostgreSQLConnector,
    POSTGRESQL_AVAILABLE,
    RedshiftConnector,
    REDSHIFT_AVAILABLE,
    DatabricksConnector,
    DATABRICKS_AVAILABLE
)
from src.core.database_permissions import (
    DatabasePermissionsManager,
    AccessLevel
)
from src.core.permissions_storage import get_permissions_storage

logger = structlog.get_logger()

# Singleton permissions manager
_permissions_manager = None


def get_permissions_manager() -> DatabasePermissionsManager:
    """Get singleton permissions manager instance."""
    global _permissions_manager
    if _permissions_manager is None:
        storage = get_permissions_storage()
        _permissions_manager = DatabasePermissionsManager(storage_backend=storage)
    return _permissions_manager


class ConnectorFactory:
    """
    Factory for creating database connector instances.

    Supports multiple database types with graceful handling of optional dependencies.
    """

    SUPPORTED_CONNECTORS = {
        'bigquery': {
            'class': BigQueryConnector,
            'available': True,
            'required_config': ['project_id', 'dataset_id'],
            'optional_config': [
                'credentials_path',
                'location',
                # Multi-auth support
                'auth_method',           # 'service_account', 'workload_identity', 'oauth'
                'credentials_json',      # Service account JSON as string
                # Workload Identity Federation
                'wif_provider_resource_name',
                'wif_service_account_email',
                # OAuth (handled separately via /bigquery/oauth/* endpoints)
                'oauth_credentials',
            ]
        },
        'snowflake': {
            'class': SnowflakeConnector if SNOWFLAKE_AVAILABLE else None,
            'available': SNOWFLAKE_AVAILABLE,
            'required_config': ['account', 'user', 'password'],
            'optional_config': ['warehouse', 'database', 'schema', 'role']
        },
        'postgresql': {
            'class': PostgreSQLConnector if POSTGRESQL_AVAILABLE else None,
            'available': POSTGRESQL_AVAILABLE,
            'required_config': ['host', 'database', 'user'],
            'optional_config': ['port', 'password', 'schema', 'ssl_mode']
        },
        'redshift': {
            'class': RedshiftConnector if REDSHIFT_AVAILABLE else None,
            'available': REDSHIFT_AVAILABLE,
            'required_config': ['host', 'database', 'user'],
            'optional_config': ['port', 'password', 'schema', 'ssl_mode', 'cluster_identifier']
        },
        'databricks': {
            'class': DatabricksConnector if DATABRICKS_AVAILABLE else None,
            'available': DATABRICKS_AVAILABLE,
            'required_config': ['server_hostname', 'http_path', 'access_token'],
            'optional_config': ['catalog', 'schema']
        },
    }

    @classmethod
    def get_supported_types(cls) -> Dict[str, bool]:
        """
        Get list of supported connector types and their availability.

        Returns:
            Dictionary mapping connector type to availability status
        """
        return {
            connector_type: info['available']
            for connector_type, info in cls.SUPPORTED_CONNECTORS.items()
        }

    @classmethod
    def validate_config(cls, connector_type: str, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate configuration for a connector type.

        Args:
            connector_type: Type of connector (e.g., 'bigquery', 'snowflake')
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        if connector_type not in cls.SUPPORTED_CONNECTORS:
            return False, f"Unsupported connector type: {connector_type}"

        connector_info = cls.SUPPORTED_CONNECTORS[connector_type]

        if not connector_info['available']:
            return False, f"Connector {connector_type} is not available (missing dependencies)"

        # Check required config fields
        missing_fields = [
            field for field in connector_info['required_config']
            if field not in config or not config[field]
        ]

        if missing_fields:
            return False, f"Missing required config fields: {', '.join(missing_fields)}"

        return True, None

    @classmethod
    def create_connector(
        cls,
        connector_type: str,
        config: Dict[str, Any]
    ) -> BaseDatabaseConnector:
        """
        Create a database connector instance.

        Args:
            connector_type: Type of connector (e.g., 'bigquery', 'snowflake')
            config: Configuration dictionary with connector-specific parameters

        Returns:
            Initialized database connector instance

        Raises:
            ValueError: If connector type is unsupported or config is invalid
            ImportError: If required dependencies are not installed
        """
        # Validate connector type
        if connector_type not in cls.SUPPORTED_CONNECTORS:
            available_types = list(cls.SUPPORTED_CONNECTORS.keys())
            raise ValueError(
                f"Unsupported connector type: {connector_type}. "
                f"Available types: {', '.join(available_types)}"
            )

        connector_info = cls.SUPPORTED_CONNECTORS[connector_type]

        # Check availability
        if not connector_info['available']:
            raise ImportError(
                f"Connector {connector_type} is not available. "
                f"Please install required dependencies."
            )

        # Validate configuration
        is_valid, error_msg = cls.validate_config(connector_type, config)
        if not is_valid:
            raise ValueError(error_msg)

        # Get connector class
        connector_class = connector_info['class']

        try:
            logger.info(
                f"Creating {connector_type} connector",
                connector_type=connector_type,
                config_keys=list(config.keys())
            )

            # Create connector instance with config
            connector = connector_class(**config)

            logger.info(f"{connector_type} connector created successfully")
            return connector

        except Exception as e:
            logger.error(
                f"Failed to create {connector_type} connector",
                error=str(e),
                connector_type=connector_type
            )
            raise

    @classmethod
    def test_connection(
        cls,
        connector_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test a database connection without persisting the connector.

        Args:
            connector_type: Type of connector
            config: Configuration dictionary

        Returns:
            Dictionary with test results:
                - success: bool
                - message: str
                - connection_time_ms: float (optional)
                - metadata: dict (optional)
                - error: str (optional)
        """
        import time

        start_time = time.time()

        try:
            # Create connector
            connector = cls.create_connector(connector_type, config)

            # Test with a simple query
            if connector_type == 'bigquery':
                result = connector.execute_query("SELECT 1 AS test")
            elif connector_type == 'snowflake':
                result = connector.execute_query("SELECT 1 AS test")
            else:
                result = connector.execute_query("SELECT 1 AS test")

            connection_time = (time.time() - start_time) * 1000

            # Disconnect
            connector.disconnect()

            return {
                'success': True,
                'message': f'Successfully connected to {connector_type}',
                'connection_time_ms': round(connection_time, 2),
                'metadata': {
                    'connector_type': connector_type,
                    'capabilities': connector.get_capabilities().__dict__ if hasattr(connector, 'get_capabilities') else None
                }
            }

        except Exception as e:
            connection_time = (time.time() - start_time) * 1000
            logger.error(
                f"Connection test failed for {connector_type}",
                error=str(e)
            )

            return {
                'success': False,
                'message': f'Failed to connect to {connector_type}',
                'connection_time_ms': round(connection_time, 2),
                'error': str(e)
            }

    @classmethod
    def get_config_template(cls, connector_type: str) -> Dict[str, Any]:
        """
        Get configuration template for a connector type.

        Args:
            connector_type: Type of connector

        Returns:
            Dictionary with required and optional config fields
        """
        if connector_type not in cls.SUPPORTED_CONNECTORS:
            raise ValueError(f"Unsupported connector type: {connector_type}")

        connector_info = cls.SUPPORTED_CONNECTORS[connector_type]

        return {
            'connector_type': connector_type,
            'available': connector_info['available'],
            'required_fields': connector_info['required_config'],
            'optional_fields': connector_info['optional_config']
        }

    @classmethod
    def check_user_access(
        cls,
        user_id: str,
        database_type: str,
        required_level: str = AccessLevel.READ.value,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has access to a database type with required level.

        Args:
            user_id: User ID
            database_type: Database type (bigquery, snowflake, etc.)
            required_level: Required access level (read, write, admin)
            organization_id: Optional organization ID

        Returns:
            True if user has access, False otherwise
        """
        permissions_manager = get_permissions_manager()
        return permissions_manager.check_access(
            user_id=user_id,
            database_type=database_type,
            required_level=required_level,
            organization_id=organization_id
        )

    @classmethod
    def get_allowed_databases_for_user(
        cls,
        user_id: str,
        organization_id: Optional[str] = None,
        min_access_level: str = AccessLevel.READ.value
    ) -> List[str]:
        """
        Get list of database types user has access to.

        Args:
            user_id: User ID
            organization_id: Optional organization ID
            min_access_level: Minimum required access level

        Returns:
            List of database type strings (e.g., ['bigquery', 'snowflake'])
        """
        permissions_manager = get_permissions_manager()
        return permissions_manager.get_allowed_databases(
            user_id=user_id,
            organization_id=organization_id,
            min_access_level=min_access_level
        )

    @classmethod
    def get_supported_types_for_user(
        cls,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get supported connector types filtered by user permissions.

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            Dictionary mapping connector type to availability and permission info:
            {
                'bigquery': {
                    'available': True,
                    'has_access': True,
                    'access_level': 'read'
                },
                ...
            }
        """
        permissions_manager = get_permissions_manager()
        user_permissions = permissions_manager.get_user_permissions(user_id, organization_id)

        result = {}
        for connector_type, info in cls.SUPPORTED_CONNECTORS.items():
            access_level = AccessLevel.NONE.value
            has_access = False

            if user_permissions:
                access_level = user_permissions.get_access_level(connector_type)
                has_access = user_permissions.has_access(connector_type)

            result[connector_type] = {
                'available': info['available'],
                'has_access': has_access,
                'access_level': access_level,
                'globally_enabled': permissions_manager.is_database_globally_enabled(connector_type)
            }

        return result

    @classmethod
    def create_connector_with_permissions(
        cls,
        connector_type: str,
        config: Dict[str, Any],
        user_id: str,
        organization_id: Optional[str] = None,
        required_level: str = AccessLevel.READ.value
    ) -> BaseDatabaseConnector:
        """
        Create a database connector with permission checking.

        Args:
            connector_type: Type of connector (e.g., 'bigquery', 'snowflake')
            config: Configuration dictionary with connector-specific parameters
            user_id: User ID requesting the connector
            organization_id: Optional organization ID
            required_level: Required access level (default: read)

        Returns:
            Initialized database connector instance

        Raises:
            ValueError: If connector type is unsupported or config is invalid
            PermissionError: If user doesn't have required access
            ImportError: If required dependencies are not installed
        """
        # Check user permissions first
        has_access = cls.check_user_access(
            user_id=user_id,
            database_type=connector_type,
            required_level=required_level,
            organization_id=organization_id
        )

        if not has_access:
            logger.warning(
                f"User {user_id} does not have {required_level} access to {connector_type}",
                user_id=user_id,
                database_type=connector_type,
                required_level=required_level
            )
            raise PermissionError(
                f"User does not have {required_level} access to {connector_type} database"
            )

        # User has permission, create connector normally
        logger.info(
            f"Creating {connector_type} connector for user {user_id}",
            user_id=user_id,
            database_type=connector_type,
            access_level=required_level
        )

        return cls.create_connector(connector_type, config)
