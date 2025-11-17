"""
Database Connector Factory

Factory pattern for creating database connector instances based on type.
Supports BigQuery, Snowflake, PostgreSQL, and future connectors.
"""
from typing import Dict, Any, Optional
import structlog

from .base_connector import BaseDatabaseConnector
from .connectors import (
    BigQueryConnector,
    SnowflakeConnector,
    SNOWFLAKE_AVAILABLE
)

logger = structlog.get_logger()


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
            'optional_config': ['credentials_path', 'location']
        },
        'snowflake': {
            'class': SnowflakeConnector if SNOWFLAKE_AVAILABLE else None,
            'available': SNOWFLAKE_AVAILABLE,
            'required_config': ['account', 'user', 'password'],
            'optional_config': ['warehouse', 'database', 'schema', 'role']
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
