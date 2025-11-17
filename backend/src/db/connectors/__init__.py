"""
Database Connectors

This package contains database-specific connector implementations.
All connectors implement the BaseDatabaseConnector interface.
"""
from .bigquery_connector import BigQueryConnector, BigQueryClient

# Import Snowflake connector (with graceful handling if snowflake-connector-python not installed)
try:
    from .snowflake_connector import SnowflakeConnector, SnowflakeClient
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SnowflakeConnector = None
    SnowflakeClient = None
    SNOWFLAKE_AVAILABLE = False

__all__ = [
    'BigQueryConnector',
    'BigQueryClient',
    'SnowflakeConnector',
    'SnowflakeClient',
    'SNOWFLAKE_AVAILABLE',
]
