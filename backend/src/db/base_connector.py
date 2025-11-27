"""
Base Database Connector

Abstract base class that defines the interface for all database connectors.
All database-specific clients (BigQuery, Snowflake, PostgreSQL, etc.) must implement this interface.

Supports both batch and streaming query execution for cross-database federation.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator, Iterator
from .database_capabilities import DatabaseCapabilities


class BaseDatabaseConnector(ABC):
    """
    Abstract base class for database connectors.

    All database connectors must inherit from this class and implement all abstract methods.
    This ensures a consistent interface across all database types for the SQL generator.
    """

    def __init__(self):
        """Initialize the database connector."""
        self._connection = None
        self._capabilities: Optional[DatabaseCapabilities] = None

    @abstractmethod
    def connect(self) -> None:
        """
        Establish a connection to the database.

        This method should initialize the database client and establish a connection.
        It should handle authentication, connection pooling, and any necessary setup.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close the database connection.

        This method should properly close connections, clean up resources,
        and perform any necessary shutdown procedures.
        """
        pass

    @abstractmethod
    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a SQL query and return results.

        Args:
            query: SQL query string to execute
            parameters: Optional query parameters for parameterized queries
            **kwargs: Additional database-specific options (timeout, page_size, etc.)

        Returns:
            Dictionary containing:
                - rows: List of result rows (each row is a dict)
                - total_rows: Total number of rows in result set
                - fetched_rows: Number of rows in this page
                - has_more: Boolean indicating if more results available
                - next_page_token: Token for fetching next page (if applicable)
                - metadata: Additional query metadata (execution time, bytes processed, etc.)

        Raises:
            QueryExecutionError: If query execution fails
            TimeoutError: If query exceeds timeout
        """
        pass

    def execute_query_streaming(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        chunk_size: int = 10000,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        Execute a SQL query and yield results in chunks (streaming mode).

        This is useful for large result sets that don't fit in memory,
        particularly for cross-database federation operations.

        Default implementation uses pagination via execute_query.
        Subclasses can override for native streaming support.

        Args:
            query: SQL query string to execute
            parameters: Optional query parameters for parameterized queries
            chunk_size: Number of rows per chunk (default: 10000)
            **kwargs: Additional database-specific options

        Yields:
            Dictionary containing:
                - rows: List of result rows for this chunk
                - chunk_number: Current chunk number (0-indexed)
                - total_fetched: Total rows fetched so far
                - has_more: Boolean indicating if more chunks available
                - metadata: Chunk metadata

        Raises:
            QueryExecutionError: If query execution fails
        """
        offset = 0
        chunk_number = 0
        total_fetched = 0

        while True:
            # Execute paginated query
            result = self.execute_query(
                query,
                parameters=parameters,
                limit=chunk_size,
                offset=offset,
                **kwargs
            )

            rows = result.get('rows', [])
            if not rows:
                break

            total_fetched += len(rows)
            has_more = len(rows) == chunk_size  # Assume more if we got full chunk

            yield {
                'rows': rows,
                'chunk_number': chunk_number,
                'total_fetched': total_fetched,
                'has_more': has_more,
                'metadata': result.get('metadata', {})
            }

            if len(rows) < chunk_size:
                # Got fewer rows than requested, we're done
                break

            offset += chunk_size
            chunk_number += 1

    async def execute_query_streaming_async(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        chunk_size: int = 10000,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Async version of execute_query_streaming.

        Default implementation wraps the sync iterator.
        Subclasses can override for native async streaming support.

        Args:
            query: SQL query string to execute
            parameters: Optional query parameters
            chunk_size: Number of rows per chunk
            **kwargs: Additional options

        Yields:
            Same format as execute_query_streaming
        """
        import asyncio

        # Run sync streaming in executor
        loop = asyncio.get_event_loop()

        # Create sync iterator
        sync_iter = self.execute_query_streaming(
            query, parameters, chunk_size, **kwargs
        )

        # Yield chunks asynchronously
        for chunk in sync_iter:
            yield chunk
            # Allow other tasks to run
            await asyncio.sleep(0)

    def estimate_row_count(self, query: str) -> Optional[int]:
        """
        Estimate the number of rows a query will return.

        Useful for federation strategy selection (pandas vs cloud-native).
        Default implementation returns None (unknown).
        Subclasses can override with EXPLAIN-based estimation.

        Args:
            query: SQL query to estimate

        Returns:
            Estimated row count, or None if estimation not supported
        """
        return None

    @abstractmethod
    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the schema information for a specific table.

        Args:
            table_name: Name of the table
            schema: Schema/dataset name (if applicable)

        Returns:
            Dictionary containing:
                - table_name: Name of the table
                - schema: Schema/dataset name
                - description: Table description
                - row_count: Approximate number of rows
                - created: Creation timestamp
                - modified: Last modification timestamp
                - columns: List of column dictionaries with:
                    - name: Column name
                    - type: Data type
                    - mode: NULLABLE, REQUIRED, REPEATED (if applicable)
                    - description: Column description

        Raises:
            TableNotFoundError: If table doesn't exist
        """
        pass

    @abstractmethod
    def list_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List all tables in a schema/dataset.

        Args:
            schema: Schema/dataset name (if applicable, None for default)

        Returns:
            List of table names

        Raises:
            SchemaNotFoundError: If schema doesn't exist
        """
        pass

    @abstractmethod
    def get_dataset_schema(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get schema information for all tables in a dataset/schema.

        Args:
            schema: Schema/dataset name (if applicable, None for default)

        Returns:
            List of table schema dictionaries (same format as get_table_schema)

        Raises:
            SchemaNotFoundError: If schema doesn't exist
        """
        pass

    @abstractmethod
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate a query without executing it (dry-run).

        This is useful for checking syntax and estimating cost before execution.
        Not all databases support this - return basic validation if not available.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary containing:
                - valid: Boolean indicating if query is valid
                - error: Error message (if invalid)
                - estimated_cost: Estimated cost (if available)
                - estimated_bytes: Estimated bytes processed (if available)
                - warnings: List of warning messages

        Raises:
            None: Should not raise, return validation errors in result
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> DatabaseCapabilities:
        """
        Get the capabilities of this database.

        Returns:
            DatabaseCapabilities object describing what this database supports
        """
        pass

    # Non-abstract utility methods that can be overridden

    def test_connection(self) -> bool:
        """
        Test if the database connection is active.

        Returns:
            True if connected, False otherwise
        """
        try:
            # Simple query to test connection
            result = self.execute_query("SELECT 1 AS test")
            return result.get('rows', [])[0].get('test') == 1
        except Exception:
            return False

    def qualify_table_name(self, table_name: str, schema: Optional[str] = None) -> str:
        """
        Qualify a table name with schema/dataset prefix if required by the database.

        This is a helper method that uses the database's capabilities to determine
        if table qualification is needed and formats it correctly.

        Args:
            table_name: Unqualified table name
            schema: Schema/dataset name (if applicable)

        Returns:
            Fully qualified table name
        """
        capabilities = self.get_capabilities()

        if not capabilities.requires_table_qualification:
            return table_name

        # Database requires qualification but no format specified - use default
        if capabilities.table_qualification_format is None:
            if schema:
                return f"{schema}.{table_name}"
            return table_name

        # Use database-specific format
        # Subclasses should override this for complex formatting
        return table_name

    def supports_feature(self, feature_name: str) -> bool:
        """
        Check if a specific feature is supported by this database.

        Args:
            feature_name: Name of the feature (e.g., "supports_ctes", "supports_window_functions")

        Returns:
            True if supported, False otherwise
        """
        capabilities = self.get_capabilities()
        return getattr(capabilities, feature_name, False)

    def get_pagination_info(self, **kwargs) -> Dict[str, Any]:
        """
        Extract pagination parameters based on database capabilities.

        Args:
            **kwargs: Various pagination parameters

        Returns:
            Dictionary with standardized pagination info
        """
        capabilities = self.get_capabilities()

        if not capabilities.supports_pagination:
            return {"supported": False}

        method = capabilities.pagination_method

        if method == "limit_offset":
            return {
                "supported": True,
                "method": "limit_offset",
                "limit": kwargs.get("limit", kwargs.get("page_size", 10000)),
                "offset": kwargs.get("offset", 0),
            }
        elif method == "page_token":
            return {
                "supported": True,
                "method": "page_token",
                "page_size": kwargs.get("page_size", 10000),
                "page_token": kwargs.get("page_token"),
            }
        elif method == "cursor":
            return {
                "supported": True,
                "method": "cursor",
                "cursor": kwargs.get("cursor"),
            }
        else:
            return {"supported": False, "method": "unknown"}

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __repr__(self) -> str:
        """String representation."""
        capabilities = self.get_capabilities()
        return f"<{self.__class__.__name__} ({capabilities.database_name})>"


class QueryExecutionError(Exception):
    """Exception raised when query execution fails."""
    pass


class TableNotFoundError(Exception):
    """Exception raised when a table is not found."""
    pass


class SchemaNotFoundError(Exception):
    """Exception raised when a schema/dataset is not found."""
    pass


class ConnectionError(Exception):
    """Exception raised when database connection fails."""
    pass
