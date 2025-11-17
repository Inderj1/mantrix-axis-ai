"""
Snowflake Database Connector

Implements the BaseDatabaseConnector interface for Snowflake.
Provides query execution, schema introspection, and metadata operations for Snowflake.
"""
from typing import List, Dict, Any, Optional
import structlog

try:
    import snowflake.connector
    from snowflake.connector import DictCursor
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    snowflake = None

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


class SnowflakeConnector(BaseDatabaseConnector):
    """
    Snowflake database connector.

    Implements the BaseDatabaseConnector interface for Snowflake,
    providing query execution, schema introspection, and metadata operations.
    """

    def __init__(
        self,
        account: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        role: Optional[str] = None
    ):
        """
        Initialize Snowflake connector.

        Args:
            account: Snowflake account identifier (e.g., 'xy12345.us-east-1')
            user: Snowflake username
            password: Snowflake password
            warehouse: Virtual warehouse name
            database: Database name
            schema: Schema name (default: PUBLIC)
            role: Role to use (default: account default role)
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

        self.connection: Optional[snowflake.connector.SnowflakeConnection] = None
        self._capabilities = SNOWFLAKE_CAPABILITIES

        # Validate required parameters
        if not all([self.account, self.user, self.password]):
            raise ValueError(
                "Snowflake connector requires account, user, and password. "
                "Provide them as parameters or set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, "
                "and SNOWFLAKE_PASSWORD in environment variables."
            )

        # Auto-connect on initialization
        self.connect()

    def connect(self) -> None:
        """
        Establish connection to Snowflake.

        Raises:
            ConnectionError: If connection initialization fails
        """
        try:
            connection_params = {
                'account': self.account,
                'user': self.user,
                'password': self.password,
            }

            # Add optional parameters if provided
            if self.warehouse:
                connection_params['warehouse'] = self.warehouse
            if self.database:
                connection_params['database'] = self.database
            if self.schema:
                connection_params['schema'] = self.schema
            if self.role:
                connection_params['role'] = self.role

            self.connection = snowflake.connector.connect(**connection_params)

            logger.info(
                "Snowflake connector initialized",
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
        Close Snowflake connection.
        """
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.info("Snowflake connector disconnected")
            except Exception as e:
                logger.warning(f"Error closing Snowflake connection: {e}")

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a SQL query and return results.

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
        if not self.connection:
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

            # Create cursor with DictCursor for dictionary results
            cursor = self.connection.cursor(DictCursor)

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
        if not self.connection:
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

            cursor = self.connection.cursor(DictCursor)
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
            cursor.close()

            schema_info = {
                "table_name": table_name,
                "schema": target_schema,
                "database": self.database,
                "description": table_info.get('COMMENT') if table_info else None,
                "row_count": table_info.get('ROW_COUNT') if table_info else None,
                "bytes": table_info.get('BYTES') if table_info else None,
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
        if not self.connection:
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

            cursor = self.connection.cursor(DictCursor)
            cursor.execute(query, {'schema': target_schema.upper()})
            tables = cursor.fetchall()
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
        if not self.connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            # Use EXPLAIN to validate query syntax
            explain_query = f"EXPLAIN {query}"

            cursor = self.connection.cursor(DictCursor)
            cursor.execute(explain_query)
            explain_result = cursor.fetchall()
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

        Args:
            warehouse: Warehouse name
        """
        if not self.connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"USE WAREHOUSE {warehouse}")
            cursor.close()
            self.warehouse = warehouse
            logger.info(f"Switched to warehouse: {warehouse}")
        except Exception as e:
            logger.error(f"Failed to switch warehouse: {e}")
            raise QueryExecutionError(f"Failed to switch warehouse: {e}")

    def use_database(self, database: str) -> None:
        """
        Switch to a different database.

        Args:
            database: Database name
        """
        if not self.connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"USE DATABASE {database}")
            cursor.close()
            self.database = database
            logger.info(f"Switched to database: {database}")
        except Exception as e:
            logger.error(f"Failed to switch database: {e}")
            raise QueryExecutionError(f"Failed to switch database: {e}")

    def use_schema(self, schema: str) -> None:
        """
        Switch to a different schema.

        Args:
            schema: Schema name
        """
        if not self.connection:
            raise QueryExecutionError("Snowflake connection not established")

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"USE SCHEMA {schema}")
            cursor.close()
            self.schema = schema
            logger.info(f"Switched to schema: {schema}")
        except Exception as e:
            logger.error(f"Failed to switch schema: {e}")
            raise QueryExecutionError(f"Failed to switch schema: {e}")


# Alias for consistency
SnowflakeClient = SnowflakeConnector
