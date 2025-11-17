"""
Databricks SQL Database Connector

Implements the BaseDatabaseConnector interface for Databricks SQL Warehouses.
Uses Databricks SQL connector with Spark SQL dialect.
"""
from typing import List, Dict, Any, Optional
import structlog

try:
    from databricks import sql
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    sql = None

from ..base_connector import (
    BaseDatabaseConnector,
    QueryExecutionError,
    TableNotFoundError,
    SchemaNotFoundError,
    ConnectionError as ConnectorConnectionError
)
from ..database_capabilities import DatabaseCapabilities, DATABRICKS_CAPABILITIES
from src.config import settings

logger = structlog.get_logger()


class DatabricksConnector(BaseDatabaseConnector):
    """
    Databricks SQL Warehouse connector.

    Implements the BaseDatabaseConnector interface for Databricks SQL,
    providing query execution on Databricks SQL Warehouses using Spark SQL.
    """

    def __init__(
        self,
        server_hostname: Optional[str] = None,
        http_path: Optional[str] = None,
        access_token: Optional[str] = None,
        catalog: Optional[str] = "main",
        schema: Optional[str] = "default"
    ):
        """
        Initialize Databricks connector.

        Args:
            server_hostname: Databricks workspace hostname (e.g., your-workspace.cloud.databricks.com)
            http_path: HTTP path to SQL warehouse (e.g., /sql/1.0/warehouses/warehouse-id)
            access_token: Databricks personal access token
            catalog: Unity Catalog name (default: main)
            schema: Schema/database name (default: default)
        """
        if not DATABRICKS_AVAILABLE:
            raise ImportError(
                "databricks-sql-connector is not installed. "
                "Install it with: pip install databricks-sql-connector"
            )

        super().__init__()

        # Use provided values or fall back to settings
        self.server_hostname = server_hostname or getattr(settings, 'databricks_server_hostname', None)
        self.http_path = http_path or getattr(settings, 'databricks_http_path', None)
        self.access_token = access_token or getattr(settings, 'databricks_access_token', None)
        self.catalog = catalog or getattr(settings, 'databricks_catalog', 'main')
        self.schema = schema or getattr(settings, 'databricks_schema', 'default')

        self.connection: Optional[Any] = None
        self._capabilities = DATABRICKS_CAPABILITIES

        # Validate required parameters
        if not all([self.server_hostname, self.http_path, self.access_token]):
            raise ValueError(
                "Databricks connector requires server_hostname, http_path, and access_token. "
                "Provide them as parameters or set DATABRICKS_SERVER_HOSTNAME, "
                "DATABRICKS_HTTP_PATH, and DATABRICKS_ACCESS_TOKEN in environment variables."
            )

        # Auto-connect on initialization
        self.connect()

    def connect(self) -> None:
        """
        Establish connection to Databricks SQL Warehouse.

        Raises:
            ConnectionError: If connection initialization fails
        """
        try:
            self.connection = sql.connect(
                server_hostname=self.server_hostname,
                http_path=self.http_path,
                access_token=self.access_token
            )

            logger.info(
                "Databricks connector initialized",
                server=self.server_hostname,
                catalog=self.catalog,
                schema=self.schema
            )

        except Exception as e:
            logger.error(f"Failed to connect to Databricks: {e}")
            raise ConnectorConnectionError(f"Failed to connect to Databricks: {e}")

    def disconnect(self) -> None:
        """
        Close Databricks connection.
        """
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.info("Databricks connector disconnected")
            except Exception as e:
                logger.warning(f"Error closing Databricks connection: {e}")

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a Spark SQL query and return results.

        Args:
            query: Spark SQL query to execute
            parameters: Query parameters (Databricks uses %(name)s format)
            **kwargs: Additional options:
                - timeout: Query timeout in seconds (not supported by Databricks connector)
                - limit: Maximum number of rows to return
                - offset: Number of rows to skip

        Returns:
            Dictionary with:
                - rows: List of result rows
                - total_rows: Total number of rows
                - fetched_rows: Number of rows in this result
                - has_more: Always False for Databricks
                - metadata: Query execution metadata

        Raises:
            QueryExecutionError: If query execution fails
        """
        if not self.connection:
            raise QueryExecutionError("Databricks connection not established")

        try:
            # Extract parameters
            limit = kwargs.get('limit', kwargs.get('page_size'))
            offset = kwargs.get('offset', 0)

            # Add LIMIT/OFFSET to query if specified
            modified_query = query
            if limit:
                modified_query = f"{query.rstrip(';')} LIMIT {limit}"
                if offset:
                    modified_query = f"{modified_query} OFFSET {offset}"

            logger.info(
                f"Executing Databricks query: {modified_query[:100]}...",
                has_parameters=parameters is not None
            )

            # Execute query
            cursor = self.connection.cursor()

            if parameters:
                cursor.execute(modified_query, parameters)
            else:
                cursor.execute(modified_query)

            # Fetch column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Fetch all results
            raw_rows = cursor.fetchall()

            # Convert to dictionaries
            rows = []
            for row in raw_rows:
                row_dict = dict(zip(columns, row))
                rows.append(row_dict)

            row_count = len(rows)

            cursor.close()

            logger.info(
                f"Databricks query returned {row_count} rows"
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
                    'server': self.server_hostname,
                    'catalog': self.catalog,
                    'schema': self.schema,
                }
            }

        except Exception as e:
            logger.error(f"Databricks query execution failed: {e}")
            raise QueryExecutionError(f"Databricks query execution failed: {e}")

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
            raise QueryExecutionError("Databricks connection not established")

        try:
            target_schema = schema or self.schema

            # Use DESCRIBE EXTENDED to get table metadata
            describe_query = f"DESCRIBE EXTENDED {self.catalog}.{target_schema}.{table_name}"

            cursor = self.connection.cursor()
            cursor.execute(describe_query)
            describe_results = cursor.fetchall()

            if not describe_results:
                raise TableNotFoundError(f"Table {self.catalog}.{target_schema}.{table_name} not found")

            # Parse DESCRIBE output
            columns = []
            table_metadata = {}
            in_metadata_section = False

            for row in describe_results:
                col_name = row[0]
                data_type = row[1]
                comment = row[2] if len(row) > 2 else None

                # Check if we've reached the metadata section
                if col_name == "# Detailed Table Information" or col_name == "":
                    in_metadata_section = True
                    continue

                if not in_metadata_section:
                    # This is a column definition
                    columns.append({
                        "name": col_name,
                        "type": data_type,
                        "mode": "NULLABLE",  # Spark SQL columns are nullable by default
                        "description": comment,
                        "is_nullable": True,
                    })
                else:
                    # This is metadata
                    if col_name and data_type:
                        table_metadata[col_name] = data_type

            cursor.close()

            schema_info = {
                "table_name": table_name,
                "schema": target_schema,
                "database": self.catalog,
                "description": table_metadata.get("Comment"),
                "columns": columns,
                "row_count": 0,  # Would need COUNT(*) query
                "bytes": 0,  # Not easily available
                "location": table_metadata.get("Location"),
                "provider": table_metadata.get("Provider"),
                "table_type": table_metadata.get("Type")
            }

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
            raise QueryExecutionError("Databricks connection not established")

        try:
            target_schema = schema or self.schema

            query = f"SHOW TABLES IN {self.catalog}.{target_schema}"

            cursor = self.connection.cursor()
            cursor.execute(query)
            tables = cursor.fetchall()
            cursor.close()

            # SHOW TABLES returns (namespace, tableName, isTemporary)
            return [table[1] for table in tables]

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

        Databricks uses EXPLAIN to validate query syntax.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary with validation results
        """
        if not self.connection:
            raise QueryExecutionError("Databricks connection not established")

        try:
            # Use EXPLAIN to validate query syntax
            explain_query = f"EXPLAIN {query}"

            cursor = self.connection.cursor()
            cursor.execute(explain_query)
            explain_result = cursor.fetchall()
            cursor.close()

            # Parse explain output
            explain_text = '\n'.join([row[0] for row in explain_result])

            return {
                "valid": True,
                "error": None,
                "warnings": [],
                "explain_plan": explain_text
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "warnings": []
            }

    def get_capabilities(self) -> DatabaseCapabilities:
        """
        Get Databricks capabilities.

        Returns:
            DatabaseCapabilities object for Databricks
        """
        return self._capabilities


# Alias for consistency
DatabricksClient = DatabricksConnector
