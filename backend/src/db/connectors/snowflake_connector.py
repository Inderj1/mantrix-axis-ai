"""
Snowflake Database Connector

Implements the BaseDatabaseConnector interface for Snowflake.
Provides query execution, schema introspection, and metadata operations for Snowflake.

Features connection pooling for efficient connection reuse.

Supports multiple authentication methods:
- Password: Traditional username/password authentication
- Key-Pair: RSA private key authentication
- PAT: Programmatic Access Token (generated from Snowflake UI)
"""
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import threading
import re
from queue import Queue, Empty
import structlog

try:
    import snowflake.connector
    from snowflake.connector import DictCursor
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    snowflake = None

# Optional: cryptography for key-pair authentication
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from ..base_connector import (
    BaseDatabaseConnector,
    QueryExecutionError,
    TableNotFoundError,
    SchemaNotFoundError,
    ConnectionError as ConnectorConnectionError
)
from ..database_capabilities import SNOWFLAKE_CAPABILITIES, DatabaseCapabilities
from src.config import settings

logger = structlog.get_logger()

# Authentication method constants
AUTH_METHOD_PASSWORD = "password"
AUTH_METHOD_KEYPAIR = "keypair"
AUTH_METHOD_PAT = "pat"  # Programmatic Access Token
VALID_AUTH_METHODS = [AUTH_METHOD_PASSWORD, AUTH_METHOD_KEYPAIR, AUTH_METHOD_PAT]

# Default pool settings
DEFAULT_MIN_CONNECTIONS = 2
DEFAULT_MAX_CONNECTIONS = 10
CONNECTION_ACQUIRE_TIMEOUT = 30  # seconds

# TPC-DS base row counts at scale factor 1 (SF1 = 1GB)
# Used to estimate row counts for SNOWFLAKE_SAMPLE_DATA shared databases
# where INFORMATION_SCHEMA.TABLES.ROW_COUNT returns NULL
TPCDS_BASE_ROWS = {
    'STORE_SALES': 2_880_000,           # ~2.88M rows per SF
    'STORE_RETURNS': 288_000,           # ~288K rows per SF
    'CATALOG_SALES': 1_440_000,         # ~1.44M rows per SF
    'CATALOG_RETURNS': 144_000,         # ~144K rows per SF
    'WEB_SALES': 720_000,               # ~720K rows per SF
    'WEB_RETURNS': 72_000,              # ~72K rows per SF
    'INVENTORY': 11_745_000,            # ~11.7M rows per SF
    'CUSTOMER': 100_000,                # ~100K rows per SF
    'CUSTOMER_ADDRESS': 50_000,         # ~50K rows per SF
    'CUSTOMER_DEMOGRAPHICS': 1_920_800, # Fixed per spec
    'ITEM': 18_000,                     # ~18K rows per SF
    'DATE_DIM': 73_049,                 # Fixed dimension
    'TIME_DIM': 86_400,                 # Fixed dimension
    'STORE': 12,                        # Small dimension per SF
    'CALL_CENTER': 6,                   # Small dimension per SF
    'CATALOG_PAGE': 11_718,             # ~12K per SF
    'WEB_PAGE': 60,                     # Small dimension per SF
    'WEB_SITE': 30,                     # Small dimension per SF
    'WAREHOUSE': 5,                     # Small dimension per SF
    'HOUSEHOLD_DEMOGRAPHICS': 7_200,    # Fixed per spec
    'INCOME_BAND': 20,                  # Fixed dimension
    'PROMOTION': 300,                   # Small dimension per SF
    'REASON': 35,                       # Fixed dimension
    'SHIP_MODE': 20,                    # Fixed dimension
}


class SnowflakeConnector(BaseDatabaseConnector):
    """
    Snowflake database connector with connection pooling.

    Implements the BaseDatabaseConnector interface for Snowflake,
    providing query execution, schema introspection, and metadata operations.

    Features thread-safe connection pooling for efficient connection reuse.
    """

    def __init__(
        self,
        account: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        role: Optional[str] = None,
        min_connections: int = DEFAULT_MIN_CONNECTIONS,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        use_pool: bool = True,
        # Authentication method parameters
        auth_method: str = AUTH_METHOD_PASSWORD,
        private_key: Optional[str] = None,
        private_key_passphrase: Optional[str] = None,
        programmatic_access_token: Optional[str] = None,
        **kwargs  # Accept additional kwargs for flexibility
    ):
        """
        Initialize Snowflake connector with connection pooling.

        Args:
            account: Snowflake account identifier (e.g., 'xy12345.us-east-1')
            user: Snowflake username
            password: Snowflake password (required for 'password' auth method)
            warehouse: Virtual warehouse name
            database: Database name
            schema: Schema name (default: PUBLIC)
            role: Role to use (default: account default role)
            min_connections: Minimum connections to keep in pool (default: 2)
            max_connections: Maximum connections allowed in pool (default: 10)
            use_pool: Whether to use connection pooling (default: True)
            auth_method: Authentication method - 'password', 'keypair', or 'pat'
            private_key: RSA private key in PEM format (for 'keypair' auth)
            private_key_passphrase: Passphrase for encrypted private key
            programmatic_access_token: PAT from Snowflake UI (for 'pat' auth)
            **kwargs: Additional parameters for future compatibility
        """
        if not SNOWFLAKE_AVAILABLE:
            raise ImportError(
                "snowflake-connector-python is not installed. "
                "Install it with: pip install snowflake-connector-python"
            )

        super().__init__()

        # Use provided values or fall back to settings
        self.account = account or getattr(settings, 'snowflake_account', None)
        self.user = user or getattr(settings, 'snowflake_user', None)
        self.password = password or getattr(settings, 'snowflake_password', None)
        self.warehouse = warehouse or getattr(settings, 'snowflake_warehouse', None)
        self.database = database or getattr(settings, 'snowflake_database', None)
        self.schema = schema or getattr(settings, 'snowflake_schema', 'PUBLIC')
        self.role = role or getattr(settings, 'snowflake_role', None)

        # Authentication method
        self.auth_method = auth_method or getattr(settings, 'snowflake_auth_method', AUTH_METHOD_PASSWORD)
        self.private_key = private_key
        self.private_key_passphrase = private_key_passphrase
        self.programmatic_access_token = programmatic_access_token

        # Pool configuration
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.use_pool = use_pool

        # Connection pool state
        self._pool: Optional[Queue] = None
        self._pool_lock = threading.Lock()
        self._pool_size = 0  # Track total connections created

        # Single connection fallback (when pooling disabled)
        self._connection: Optional[snowflake.connector.SnowflakeConnection] = None
        self._capabilities = SNOWFLAKE_CAPABILITIES

        # Validate auth method
        if self.auth_method not in VALID_AUTH_METHODS:
            raise ValueError(
                f"Invalid auth_method '{self.auth_method}'. "
                f"Must be one of: {', '.join(VALID_AUTH_METHODS)}"
            )

        # Validate required parameters based on auth method
        self._validate_auth_config()

        # Auto-connect on initialization
        self.connect()

    def _validate_auth_config(self) -> None:
        """Validate authentication configuration based on auth method."""
        if not self.account:
            raise ValueError("Snowflake connector requires 'account' parameter.")

        if self.auth_method == AUTH_METHOD_PASSWORD:
            if not all([self.user, self.password]):
                raise ValueError(
                    "Snowflake password authentication requires 'user' and 'password'. "
                    "Provide them as parameters or set SNOWFLAKE_USER and SNOWFLAKE_PASSWORD "
                    "in environment variables."
                )

        elif self.auth_method == AUTH_METHOD_KEYPAIR:
            if not CRYPTOGRAPHY_AVAILABLE:
                raise ImportError(
                    "Key-pair authentication requires the 'cryptography' package. "
                    "Install it with: pip install cryptography"
                )
            if not self.user:
                raise ValueError("Snowflake key-pair authentication requires 'user' parameter.")
            if not self.private_key:
                raise ValueError(
                    "Snowflake key-pair authentication requires 'private_key' parameter "
                    "(RSA private key in PEM format)."
                )

        elif self.auth_method == AUTH_METHOD_PAT:
            if not self.user:
                raise ValueError("Snowflake PAT authentication requires 'user' parameter.")
            if not self.programmatic_access_token:
                raise ValueError(
                    "Snowflake PAT authentication requires 'programmatic_access_token' parameter. "
                    "Generate a token from Snowflake UI: Profile → Programmatic Access Tokens."
                )

    def _create_connection(self) -> snowflake.connector.SnowflakeConnection:
        """Create a new Snowflake connection using the configured auth method."""
        # Get auth-specific connection parameters
        if self.auth_method == AUTH_METHOD_PASSWORD:
            connection_params = self._get_password_connection_params()
        elif self.auth_method == AUTH_METHOD_KEYPAIR:
            connection_params = self._get_keypair_connection_params()
        elif self.auth_method == AUTH_METHOD_PAT:
            connection_params = self._get_pat_connection_params()
        else:
            raise ValueError(f"Unknown auth method: {self.auth_method}")

        # Add common optional parameters
        if self.warehouse:
            connection_params['warehouse'] = self.warehouse
        if self.database:
            connection_params['database'] = self.database
        if self.schema:
            connection_params['schema'] = self.schema
        if self.role:
            connection_params['role'] = self.role

        logger.debug(
            "Creating Snowflake connection",
            auth_method=self.auth_method,
            account=self.account,
            user=self.user,
            warehouse=self.warehouse
        )

        return snowflake.connector.connect(**connection_params)

    def _get_password_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for password authentication."""
        return {
            'account': self.account,
            'user': self.user,
            'password': self.password,
        }

    def _get_keypair_connection_params(self) -> Dict[str, Any]:
        """
        Get connection parameters for key-pair authentication.

        Parses the PEM-encoded private key and converts it to the DER format
        required by Snowflake.
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("cryptography package required for key-pair auth")

        try:
            # Parse the PEM private key
            private_key_bytes = self.private_key.encode('utf-8')

            # Handle passphrase if provided
            passphrase = None
            if self.private_key_passphrase:
                passphrase = self.private_key_passphrase.encode('utf-8')

            # Load the private key
            p_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=passphrase,
                backend=default_backend()
            )

            # Convert to DER format (PKCS8) as required by Snowflake
            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            return {
                'account': self.account,
                'user': self.user,
                'private_key': pkb,
            }

        except Exception as e:
            logger.error(f"Failed to parse private key: {e}")
            raise ValueError(f"Failed to parse private key for key-pair authentication: {e}")

    def _get_pat_connection_params(self) -> Dict[str, Any]:
        """
        Get connection parameters for Programmatic Access Token (PAT) authentication.

        PATs are generated from the Snowflake UI and provide secure programmatic access
        without sharing passwords. They're ideal for users who log in via SSO.
        """
        return {
            'account': self.account,
            'user': self.user,
            'token': self.programmatic_access_token,
            'authenticator': 'programmatic_access_token',
        }

    def _estimate_tpcds_row_count(self, database: str, schema: str, table_name: str) -> Optional[int]:
        """
        Estimate row count for TPC-DS tables based on scale factor.

        Snowflake's INFORMATION_SCHEMA.TABLES returns NULL for ROW_COUNT on shared
        databases like SNOWFLAKE_SAMPLE_DATA. This method estimates row counts
        based on the TPC-DS specification and scale factor encoded in the schema name.

        Schema naming convention: TPCDS_SF{scale}TCL
        - SF10TCL = Scale Factor 10 * 1000 (TCL multiplier) = 10,000x base rows
        - This represents a 10TB dataset

        Args:
            database: Database name (e.g., 'SNOWFLAKE_SAMPLE_DATA')
            schema: Schema name (e.g., 'TPCDS_SF10TCL')
            table_name: Table name (e.g., 'STORE_SALES')

        Returns:
            Estimated row count or None if not a recognized TPC-DS table
        """
        if not database or database.upper() != 'SNOWFLAKE_SAMPLE_DATA':
            return None

        if not schema:
            return None

        # Parse scale factor from schema name (e.g., TPCDS_SF10TCL -> 10 * 1000 = 10000)
        match = re.match(r'TPCDS_SF(\d+)TCL', schema.upper())
        if not match:
            # Also support non-TCL variants (e.g., TPCDS_SF1)
            match = re.match(r'TPCDS_SF(\d+)$', schema.upper())
            if not match:
                return None
            scale_factor = int(match.group(1))
        else:
            # TCL = 1000x multiplier (Tera-scale)
            scale_factor = int(match.group(1)) * 1000

        base_rows = TPCDS_BASE_ROWS.get(table_name.upper())
        if base_rows is None:
            return None

        estimated = base_rows * scale_factor
        logger.info(
            f"Estimated TPC-DS row count for {database}.{schema}.{table_name}: "
            f"{estimated:,} rows (base={base_rows:,}, scale_factor={scale_factor:,})"
        )
        return estimated

    def connect(self) -> None:
        """
        Initialize connection pool or single connection to Snowflake.

        Raises:
            ConnectionError: If connection initialization fails
        """
        try:
            if self.use_pool:
                # Initialize connection pool
                self._pool = Queue(maxsize=self.max_connections)

                # Pre-create minimum connections
                for _ in range(self.min_connections):
                    conn = self._create_connection()
                    self._pool.put(conn)
                    self._pool_size += 1

                logger.info(
                    "Snowflake connection pool initialized",
                    account=self.account,
                    warehouse=self.warehouse,
                    database=self.database,
                    schema=self.schema,
                    min_connections=self.min_connections,
                    max_connections=self.max_connections
                )
            else:
                # Single connection mode
                self._connection = self._create_connection()
                logger.info(
                    "Snowflake single connection initialized",
                    account=self.account,
                    warehouse=self.warehouse,
                    database=self.database,
                    schema=self.schema
                )

        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise ConnectorConnectionError(f"Failed to connect to Snowflake: {e}")

    def disconnect(self) -> None:
        """
        Close all Snowflake connections in the pool.
        """
        if self._pool:
            with self._pool_lock:
                # Close all connections in the pool
                while not self._pool.empty():
                    try:
                        conn = self._pool.get_nowait()
                        conn.close()
                    except Empty:
                        break
                    except Exception as e:
                        logger.warning(f"Error closing pooled connection: {e}")
                self._pool = None
                self._pool_size = 0
                logger.info("Snowflake connection pool closed")

        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                logger.info("Snowflake connection closed")
            except Exception as e:
                logger.warning(f"Error closing Snowflake connection: {e}")

    @contextmanager
    def _get_connection(self):
        """
        Context manager to get a connection from the pool.

        Automatically returns the connection to the pool when done.
        Creates a new connection if pool is empty but under max capacity.
        """
        conn = None
        created_new = False

        try:
            if self._pool is not None:
                # Try to get from pool
                try:
                    conn = self._pool.get(timeout=CONNECTION_ACQUIRE_TIMEOUT)
                except Empty:
                    # Pool empty, try to create new connection if under limit
                    with self._pool_lock:
                        if self._pool_size < self.max_connections:
                            conn = self._create_connection()
                            self._pool_size += 1
                            created_new = True
                            logger.debug(f"Created new pooled connection (size: {self._pool_size})")
                        else:
                            raise ConnectorConnectionError(
                                f"Connection pool exhausted (max: {self.max_connections})"
                            )
                yield conn
            elif self._connection:
                yield self._connection
            else:
                raise ConnectorConnectionError("Snowflake connection not established")

        finally:
            # Return connection to pool
            if conn and self._pool is not None:
                try:
                    # Check if connection is still valid
                    if not conn.is_closed():
                        self._pool.put_nowait(conn)
                    else:
                        # Connection was closed, decrement pool size
                        with self._pool_lock:
                            self._pool_size -= 1
                        logger.debug("Discarded closed connection from pool")
                except Exception:
                    # If we can't return it, close it
                    try:
                        conn.close()
                    except Exception:
                        pass
                    with self._pool_lock:
                        self._pool_size -= 1

    # Legacy property for backward compatibility
    @property
    def connection(self):
        """Backward compatibility: returns a connection (not recommended for pooled use)."""
        if self._pool:
            # Warning: caller is responsible for returning connection
            try:
                return self._pool.get_nowait()
            except Empty:
                return self._create_connection()
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
            parameters: Query parameters (Snowflake uses %(name)s format)
            **kwargs: Additional options:
                - timeout: Query timeout in seconds
                - limit: Maximum number of rows to return
                - offset: Number of rows to skip

        Returns:
            Dictionary with:
                - rows: List of result rows
                - total_rows: Total number of rows (approximate)
                - fetched_rows: Number of rows in this result
                - has_more: Always False for Snowflake (no native pagination)
                - metadata: Query execution metadata

        Raises:
            QueryExecutionError: If query execution fails
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("Snowflake connection not established")

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
                f"Executing Snowflake query: {modified_query[:100]}...",
                timeout=timeout,
                has_parameters=parameters is not None
            )

            # Use connection from pool via context manager
            with self._get_connection() as conn:
                # Create cursor with DictCursor for dictionary results
                cursor = conn.cursor(DictCursor)

                try:
                    # Set timeout if specified
                    if timeout:
                        cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout}")

                    # Execute query
                    if parameters:
                        cursor.execute(modified_query, parameters)
                    else:
                        cursor.execute(modified_query)

                    # Fetch all results
                    rows = cursor.fetchall()

                    # Get row count
                    row_count = len(rows)

                    # Get query metadata
                    query_id = cursor.sfqid if hasattr(cursor, 'sfqid') else None

                finally:
                    cursor.close()

            logger.info(
                f"Snowflake query returned {row_count} rows",
                query_id=query_id
            )

            return {
                'rows': rows,
                'total_rows': row_count,
                'fetched_rows': row_count,
                'has_more': False,  # Snowflake doesn't have native pagination
                'next_page_token': None,
                'truncated': False,
                'page_info': {
                    'page_size': limit if limit else row_count,
                    'current_page_size': row_count,
                    'total_rows': row_count,
                    'has_next_page': False
                },
                'metadata': {
                    'query_id': query_id,
                    'warehouse': self.warehouse,
                }
            }

        except Exception as e:
            logger.error(f"Snowflake query execution failed: {e}")
            raise QueryExecutionError(f"Snowflake query execution failed: {e}")

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
            raise QueryExecutionError("Snowflake connection not established")

        try:
            target_schema = schema or self.schema

            # Query INFORMATION_SCHEMA to get table and column information
            query = f"""
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE,
                c.COLUMN_DEFAULT,
                c.CHARACTER_MAXIMUM_LENGTH,
                c.NUMERIC_PRECISION,
                c.NUMERIC_SCALE,
                c.COMMENT as COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_SCHEMA = %(schema)s
              AND c.TABLE_NAME = %(table)s
            ORDER BY c.ORDINAL_POSITION
            """

            with self._get_connection() as conn:
                cursor = conn.cursor(DictCursor)
                try:
                    cursor.execute(query, {'schema': target_schema.upper(), 'table': table_name.upper()})
                    columns = cursor.fetchall()

                    if not columns:
                        raise TableNotFoundError(f"Table {target_schema}.{table_name} not found")

                    # Get table-level information
                    table_query = f"""
                    SELECT
                        ROW_COUNT,
                        BYTES,
                        CREATED,
                        LAST_ALTERED,
                        COMMENT
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = %(schema)s
                      AND TABLE_NAME = %(table)s
                    """

                    cursor.execute(table_query, {'schema': target_schema.upper(), 'table': table_name.upper()})
                    table_info = cursor.fetchone()
                finally:
                    cursor.close()

            # Get row count and bytes - use BYTES as fallback for shared databases
            # where ROW_COUNT is often NULL (e.g., SNOWFLAKE_SAMPLE_DATA)
            row_count = table_info.get('ROW_COUNT') if table_info else None
            bytes_size = table_info.get('BYTES') if table_info else None

            if not row_count and bytes_size:
                # Estimate row count from bytes (assume ~100 bytes per row average)
                # This is conservative - better to overestimate for query planning
                row_count = bytes_size // 100
                logger.info(
                    f"Estimated row_count for {table_name}: {row_count:,} "
                    f"(from {bytes_size:,} bytes, ROW_COUNT was NULL)"
                )

            # If still no row count, try TPC-DS scale-based estimation
            # This handles SNOWFLAKE_SAMPLE_DATA shared databases where both
            # ROW_COUNT and BYTES are NULL
            if not row_count:
                row_count = self._estimate_tpcds_row_count(self.database, target_schema, table_name)

            schema_info = {
                "table_name": table_name,
                "schema": target_schema,
                "database": self.database,
                "description": table_info.get('COMMENT') if table_info else None,
                "row_count": row_count,
                "bytes": bytes_size,
                "created": str(table_info.get('CREATED')) if table_info and table_info.get('CREATED') else None,
                "modified": str(table_info.get('LAST_ALTERED')) if table_info and table_info.get('LAST_ALTERED') else None,
                "columns": []
            }

            for col in columns:
                column_info = {
                    "name": col['COLUMN_NAME'],
                    "type": col['DATA_TYPE'],
                    "mode": "REQUIRED" if col['IS_NULLABLE'] == 'NO' else "NULLABLE",
                    "description": col.get('COLUMN_COMMENT'),
                    "is_nullable": col['IS_NULLABLE'] == 'YES',
                    "default": col.get('COLUMN_DEFAULT'),
                    "max_length": col.get('CHARACTER_MAXIMUM_LENGTH'),
                    "precision": col.get('NUMERIC_PRECISION'),
                    "scale": col.get('NUMERIC_SCALE'),
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
            raise QueryExecutionError("Snowflake connection not established")

        try:
            target_schema = schema or self.schema

            query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %(schema)s
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """

            with self._get_connection() as conn:
                cursor = conn.cursor(DictCursor)
                try:
                    cursor.execute(query, {'schema': target_schema.upper()})
                    tables = cursor.fetchall()
                finally:
                    cursor.close()

            return [table['TABLE_NAME'] for table in tables]

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

        Note: Snowflake doesn't have a native dry-run mode like BigQuery.
        We use EXPLAIN to validate the query syntax.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary with validation results
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            # Use EXPLAIN to validate query syntax
            explain_query = f"EXPLAIN {query}"

            with self._get_connection() as conn:
                cursor = conn.cursor(DictCursor)
                try:
                    cursor.execute(explain_query)
                    explain_result = cursor.fetchall()
                finally:
                    cursor.close()

            return {
                "valid": True,
                "error": None,
                "warnings": [],
                "explain_plan": explain_result
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "warnings": []
            }

    def get_capabilities(self) -> DatabaseCapabilities:
        """
        Get Snowflake capabilities.

        Returns:
            DatabaseCapabilities object for Snowflake
        """
        return self._capabilities

    def qualify_table_name(self, table_name: str, schema: Optional[str] = None) -> str:
        """
        Qualify a table name with Snowflake's specific format.

        Args:
            table_name: Unqualified table name
            schema: Schema name (optional, uses default if not provided)

        Returns:
            Fully qualified table name in Snowflake format: database.schema.table
        """
        target_schema = schema or self.schema

        if self.database:
            return f"{self.database}.{target_schema}.{table_name}"
        else:
            return f"{target_schema}.{table_name}"

    def use_warehouse(self, warehouse: str) -> None:
        """
        Switch to a different virtual warehouse.

        Note: This only affects the current connection context.
        For pooled connections, use warehouse parameter in queries.

        Args:
            warehouse: Warehouse name
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"USE WAREHOUSE {warehouse}")
                finally:
                    cursor.close()
            self.warehouse = warehouse
            logger.info(f"Switched to warehouse: {warehouse}")
        except Exception as e:
            logger.error(f"Failed to switch warehouse: {e}")
            raise QueryExecutionError(f"Failed to switch warehouse: {e}")

    def use_database(self, database: str) -> None:
        """
        Switch to a different database.

        Note: This only affects the current connection context.
        For pooled connections, use fully qualified table names.

        Args:
            database: Database name
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"USE DATABASE {database}")
                finally:
                    cursor.close()
            self.database = database
            logger.info(f"Switched to database: {database}")
        except Exception as e:
            logger.error(f"Failed to switch database: {e}")
            raise QueryExecutionError(f"Failed to switch database: {e}")

    def use_schema(self, schema: str) -> None:
        """
        Switch to a different schema.

        Note: This only affects the current connection context.
        For pooled connections, use fully qualified table names.

        Args:
            schema: Schema name
        """
        if not self._pool and not self._connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"USE SCHEMA {schema}")
                finally:
                    cursor.close()
            self.schema = schema
            logger.info(f"Switched to schema: {schema}")
        except Exception as e:
            logger.error(f"Failed to switch schema: {e}")
            raise QueryExecutionError(f"Failed to switch schema: {e}")


# Alias for consistency
SnowflakeClient = SnowflakeConnector
