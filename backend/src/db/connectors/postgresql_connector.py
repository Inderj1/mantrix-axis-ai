"""
PostgreSQL Database Connector

Implements the BaseDatabaseConnector interface for external PostgreSQL databases.
This is separate from the internal postgresql_client.py used for app features.

Features connection pooling for efficient connection reuse.
"""
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import structlog

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import sql
    from psycopg2 import pool
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    psycopg2 = None
    pool = None

from ..base_connector import (
    BaseDatabaseConnector,
    QueryExecutionError,
    TableNotFoundError,
    SchemaNotFoundError,
    ConnectionError as ConnectorConnectionError
)
from ..database_capabilities import DatabaseCapabilities, POSTGRESQL_CAPABILITIES
from src.config import settings

logger = structlog.get_logger()

# Default pool settings
DEFAULT_MIN_CONNECTIONS = 2
DEFAULT_MAX_CONNECTIONS = 10


class PostgreSQLConnector(BaseDatabaseConnector):
    """
    PostgreSQL database connector for external customer databases.

    Implements the BaseDatabaseConnector interface for PostgreSQL,
    providing query execution, schema introspection, and metadata operations.

    Features connection pooling for efficient connection reuse across requests.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        schema: Optional[str] = "public",
        ssl_mode: Optional[str] = None,
        min_connections: int = DEFAULT_MIN_CONNECTIONS,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        use_pool: bool = True
    ):
        """
        Initialize PostgreSQL connector with connection pooling.

        Args:
            host: PostgreSQL server hostname
            port: PostgreSQL server port (default: 5432)
            database: Database name
            user: PostgreSQL username
            password: PostgreSQL password
            schema: Schema name (default: public)
            ssl_mode: SSL mode (disable, allow, prefer, require, verify-ca, verify-full)
            min_connections: Minimum connections to keep in pool (default: 2)
            max_connections: Maximum connections allowed in pool (default: 10)
            use_pool: Whether to use connection pooling (default: True)
        """
        if not POSTGRESQL_AVAILABLE:
            raise ImportError(
                "psycopg2 is not installed. "
                "Install it with: pip install psycopg2-binary"
            )

        super().__init__()

        # Use provided values or fall back to settings
        # Note: These are different from the internal PostgreSQL settings
        self.host = host or getattr(settings, 'external_postgres_host', 'localhost')
        self.port = port or getattr(settings, 'external_postgres_port', 5432)
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema or "public"
        self.ssl_mode = ssl_mode

        # Pool configuration
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.use_pool = use_pool

        # Connection pool (initialized in connect())
        self._pool: Optional[pool.ThreadedConnectionPool] = None
        # Single connection fallback (when pooling disabled)
        self._connection: Optional[Any] = None
        self._capabilities = POSTGRESQL_CAPABILITIES

        # Validate required parameters
        if not all([self.host, self.database, self.user]):
            raise ValueError(
                "PostgreSQL connector requires host, database, and user. "
                "Provide them as parameters or set in environment variables."
            )

        # Auto-connect on initialization
        self.connect()

    def connect(self) -> None:
        """
        Initialize connection pool or single connection to PostgreSQL.

        Raises:
            ConnectionError: If connection initialization fails
        """
        try:
            connection_params = {
                'host': self.host,
                'port': self.port,
                'database': self.database,
                'user': self.user,
            }

            if self.password:
                connection_params['password'] = self.password

            if self.ssl_mode:
                connection_params['sslmode'] = self.ssl_mode

            if self.use_pool:
                # Create ThreadedConnectionPool for thread-safe connection reuse
                self._pool = pool.ThreadedConnectionPool(
                    minconn=self.min_connections,
                    maxconn=self.max_connections,
                    **connection_params
                )
                logger.info(
                    "PostgreSQL connection pool initialized",
                    host=self.host,
                    database=self.database,
                    schema=self.schema,
                    min_connections=self.min_connections,
                    max_connections=self.max_connections
                )
            else:
                # Fallback to single connection
                self._connection = psycopg2.connect(**connection_params)
                logger.info(
                    "PostgreSQL single connection initialized",
                    host=self.host,
                    database=self.database,
                    schema=self.schema
                )

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ConnectorConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def disconnect(self) -> None:
        """
        Close PostgreSQL connection pool or single connection.
        """
        if self._pool:
            try:
                self._pool.closeall()
                self._pool = None
                logger.info("PostgreSQL connection pool closed")
            except Exception as e:
                logger.warning(f"Error closing PostgreSQL connection pool: {e}")

        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                logger.info("PostgreSQL connection closed")
            except Exception as e:
                logger.warning(f"Error closing PostgreSQL connection: {e}")

    @contextmanager
    def _get_connection(self):
        """
        Context manager to get a connection from the pool.

        Automatically returns the connection to the pool when done.
        """
        conn = None
        try:
            if self._pool:
                conn = self._pool.getconn()
                yield conn
            elif self._connection:
                yield self._connection
            else:
                raise ConnectorConnectionError("PostgreSQL connection not established")
        finally:
            if conn and self._pool:
                self._pool.putconn(conn)

    # Legacy property for backward compatibility
    @property
    def connection(self):
        """Backward compatibility: returns a connection (not recommended for pooled use)."""
        if self._pool:
            # Warning: caller is responsible for returning connection
            return self._pool.getconn()
        return self._connection

    @connection.setter
    def connection(self, value):
        """Backward compatibility setter."""
        self._connection = value

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a SQL query and return results.

        Uses connection pooling for efficient connection reuse.

        Args:
            query: SQL query to execute
            parameters: Query parameters (PostgreSQL uses %(name)s format)
            **kwargs: Additional options:
                - timeout: Query timeout in seconds
                - limit: Maximum number of rows to return
                - offset: Number of rows to skip

        Returns:
            Dictionary with:
                - rows: List of result rows
                - total_rows: Total number of rows
                - fetched_rows: Number of rows in this result
                - has_more: Always False for PostgreSQL (no native pagination tracking)
                - metadata: Query execution metadata

        Raises:
            QueryExecutionError: If query execution fails
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("PostgreSQL connection not established")

        try:
            # Extract parameters
            timeout = kwargs.get('timeout')
            limit = kwargs.get('limit', kwargs.get('page_size'))
            offset = kwargs.get('offset', 0)

            # Add LIMIT/OFFSET to query if specified
            modified_query = query
            if limit:
                modified_query = f"{query.rstrip(';')} LIMIT {limit}"
                if offset:
                    modified_query = f"{modified_query} OFFSET {offset}"

            logger.info(
                f"Executing PostgreSQL query: {modified_query[:100]}...",
                timeout=timeout,
                has_parameters=parameters is not None
            )

            # Use connection from pool via context manager
            with self._get_connection() as conn:
                # Create cursor with RealDictCursor for dictionary results
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                try:
                    # Set timeout if specified
                    if timeout:
                        cursor.execute(f"SET statement_timeout = {timeout * 1000}")  # PostgreSQL uses milliseconds

                    # Execute query
                    if parameters:
                        cursor.execute(modified_query, parameters)
                    else:
                        cursor.execute(modified_query)

                    # Check if query returns results
                    if cursor.description:
                        # Fetch all results
                        rows = cursor.fetchall()

                        # Convert RealDictRow to regular dict
                        rows = [dict(row) for row in rows]

                        row_count = len(rows)
                    else:
                        # Query doesn't return results (INSERT, UPDATE, DELETE)
                        conn.commit()
                        rows = []
                        row_count = cursor.rowcount

                finally:
                    cursor.close()

            logger.info(
                f"PostgreSQL query returned {row_count} rows"
            )

            return {
                'rows': rows,
                'total_rows': row_count,
                'fetched_rows': row_count,
                'has_more': False,
                'next_page_token': None,
                'truncated': False,
                'page_info': {
                    'page_size': limit if limit else row_count,
                    'current_page_size': row_count,
                    'total_rows': row_count,
                    'has_next_page': False
                },
                'metadata': {
                    'host': self.host,
                    'database': self.database,
                }
            }

        except Exception as e:
            logger.error(f"PostgreSQL query execution failed: {e}")
            raise QueryExecutionError(f"PostgreSQL query execution failed: {e}")

    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get schema information for a specific table.

        Args:
            table_name: Name of the table
            schema: Schema name (if different from default)

        Returns:
            Dictionary with table metadata and column information

        Raises:
            TableNotFoundError: If table doesn't exist
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("PostgreSQL connection not established")

        try:
            target_schema = schema or self.schema

            # Query information_schema to get table and column information
            query = """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                col_description(
                    (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
                    c.ordinal_position
                ) as column_comment
            FROM information_schema.columns c
            WHERE c.table_schema = %(schema)s
              AND c.table_name = %(table)s
            ORDER BY c.ordinal_position
            """

            with self._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cursor.execute(query, {'schema': target_schema, 'table': table_name})
                    columns = cursor.fetchall()

                    if not columns:
                        raise TableNotFoundError(f"Table {target_schema}.{table_name} not found")

                    # Get table-level information
                    table_query = """
                    SELECT
                        obj_description((quote_ident(%(schema)s) || '.' || quote_ident(%(table)s))::regclass) as table_comment,
                        (SELECT reltuples::bigint FROM pg_class WHERE oid = (quote_ident(%(schema)s) || '.' || quote_ident(%(table)s))::regclass) as row_count,
                        pg_total_relation_size((quote_ident(%(schema)s) || '.' || quote_ident(%(table)s))::regclass) as total_bytes
                    """

                    cursor.execute(table_query, {'schema': target_schema, 'table': table_name})
                    table_info = cursor.fetchone()
                finally:
                    cursor.close()

            schema_info = {
                "table_name": table_name,
                "schema": target_schema,
                "database": self.database,
                "description": table_info['table_comment'] if table_info else None,
                "row_count": table_info['row_count'] if table_info else None,
                "size_bytes": table_info['total_bytes'] if table_info else None,
                "columns": []
            }

            for col in columns:
                column_info = {
                    "name": col['column_name'],
                    "type": col['data_type'],
                    "mode": "REQUIRED" if col['is_nullable'] == 'NO' else "NULLABLE",
                    "description": col.get('column_comment'),
                    "is_nullable": col['is_nullable'] == 'YES',
                    "default": col.get('column_default'),
                    "max_length": col.get('character_maximum_length'),
                    "precision": col.get('numeric_precision'),
                    "scale": col.get('numeric_scale'),
                }
                schema_info["columns"].append(column_info)

            return schema_info

        except TableNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {e}")
            raise TableNotFoundError(f"Table {table_name} not found: {e}")

    def list_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List all tables in a schema.

        Args:
            schema: Schema name (if different from default)

        Returns:
            List of table names

        Raises:
            SchemaNotFoundError: If schema doesn't exist
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("PostgreSQL connection not established")

        try:
            target_schema = schema or self.schema

            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %(schema)s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """

            with self._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cursor.execute(query, {'schema': target_schema})
                    tables = cursor.fetchall()
                finally:
                    cursor.close()

            return [table['table_name'] for table in tables]

        except Exception as e:
            logger.error(f"Failed to list tables in schema {target_schema}: {e}")
            raise SchemaNotFoundError(f"Schema {target_schema} not found: {e}")

    def get_dataset_schema(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get schema information for all tables in a schema.

        Args:
            schema: Schema name (if different from default)

        Returns:
            List of table schema dictionaries

        Raises:
            SchemaNotFoundError: If schema doesn't exist
        """
        schemas = []
        table_names = self.list_tables(schema=schema)

        for table_name in table_names:
            try:
                table_schema = self.get_table_schema(table_name, schema=schema)
                schemas.append(table_schema)
            except Exception as e:
                logger.warning(f"Failed to get schema for {table_name}: {e}")
                continue

        return schemas

    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate a query without executing it.

        PostgreSQL uses EXPLAIN to validate query syntax.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary with validation results
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("PostgreSQL connection not established")

        try:
            # Use EXPLAIN to validate query syntax
            explain_query = f"EXPLAIN {query}"

            with self._get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(explain_query)
                    explain_result = cursor.fetchall()
                finally:
                    cursor.close()

            return {
                "valid": True,
                "error": None,
                "warnings": [],
                "explain_plan": [row[0] for row in explain_result]
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "warnings": []
            }

    def get_capabilities(self) -> DatabaseCapabilities:
        """
        Get PostgreSQL capabilities.

        Returns:
            DatabaseCapabilities object for PostgreSQL
        """
        return self._capabilities


# Alias for consistency
PostgreSQLClient = PostgreSQLConnector
