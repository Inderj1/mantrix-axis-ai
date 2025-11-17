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

# Import PostgreSQL connector (with graceful handling if psycopg2 not installed)
try:
    from .postgresql_connector import PostgreSQLConnector, PostgreSQLClient
    POSTGRESQL_AVAILABLE = True
except ImportError:
    PostgreSQLConnector = None
    PostgreSQLClient = None
    POSTGRESQL_AVAILABLE = False

# Import Redshift connector (requires psycopg2, inherits from PostgreSQL)
try:
    from .redshift_connector import RedshiftConnector, RedshiftClient
    REDSHIFT_AVAILABLE = POSTGRESQL_AVAILABLE  # Redshift requires PostgreSQL connector
except ImportError:
    RedshiftConnector = None
    RedshiftClient = None
    REDSHIFT_AVAILABLE = False

# Import Databricks connector (with graceful handling if databricks-sql-connector not installed)
try:
    from .databricks_connector import DatabricksConnector, DatabricksClient
    DATABRICKS_AVAILABLE = True
except ImportError:
    DatabricksConnector = None
    DatabricksClient = None
    DATABRICKS_AVAILABLE = False

__all__ = [
    'BigQueryConnector',
    'BigQueryClient',
    'SnowflakeConnector',
    'SnowflakeClient',
    'SNOWFLAKE_AVAILABLE',
    'PostgreSQLConnector',
    'PostgreSQLClient',
    'POSTGRESQL_AVAILABLE',
    'RedshiftConnector',
    'RedshiftClient',
    'REDSHIFT_AVAILABLE',
    'DatabricksConnector',
    'DatabricksClient',
    'DATABRICKS_AVAILABLE',
]
