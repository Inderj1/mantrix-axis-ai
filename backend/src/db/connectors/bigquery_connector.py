"""
BigQuery Database Connector

Implements the BaseDatabaseConnector interface for Google BigQuery.
This is a refactored version of the original BigQueryClient that conforms to the generic connector pattern.
"""
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from google.auth import default
import json
import re
import structlog

from ..base_connector import BaseDatabaseConnector, QueryExecutionError, TableNotFoundError, SchemaNotFoundError
from ..database_capabilities import BIGQUERY_CAPABILITIES, DatabaseCapabilities
from src.config import settings

logger = structlog.get_logger()


class BigQueryConnector(BaseDatabaseConnector):
    """
    Google BigQuery database connector.

    Implements the BaseDatabaseConnector interface for BigQuery,
    providing query execution, schema introspection, and metadata operations.
    """

    def __init__(self, project_id: Optional[str] = None, dataset_id: Optional[str] = None):
        """
        Initialize BigQuery connector.

        Args:
            project_id: GCP project ID (defaults to settings.google_cloud_project)
            dataset_id: BigQuery dataset ID (defaults to settings.bigquery_dataset)
        """
        super().__init__()
        self.project_id = project_id or settings.google_cloud_project
        self.dataset_id = dataset_id or settings.bigquery_dataset
        self.client: Optional[bigquery.Client] = None
        self._capabilities = BIGQUERY_CAPABILITIES

        # Auto-connect on initialization (matches original behavior)
        self.connect()

    def connect(self) -> None:
        """
        Establish connection to BigQuery.

        Initializes the BigQuery client using either service account credentials
        or application default credentials.

        Raises:
            ConnectionError: If connection initialization fails
        """
        try:
            if settings.google_application_credentials:
                # Only try service account if file actually exists
                import os
                if os.path.exists(settings.google_application_credentials):
                    # Check if it's a service account or user credentials file
                    with open(settings.google_application_credentials, 'r') as f:
                        cred_data = json.load(f)

                    if cred_data.get('type') == 'service_account':
                        # Service account credentials
                        credentials = service_account.Credentials.from_service_account_file(
                            settings.google_application_credentials
                        )
                        self.client = bigquery.Client(
                            project=self.project_id,
                            credentials=credentials
                        )
                        logger.info("BigQuery connector initialized with service account")
                    else:
                        # User credentials or other type - use default credentials
                        credentials, project = default()
                        self.client = bigquery.Client(
                            project=self.project_id,
                            credentials=credentials
                        )
                        logger.info("BigQuery connector initialized with application default credentials")
                else:
                    # Fall back to default credentials
                    credentials, project = default()
                    self.client = bigquery.Client(
                        project=self.project_id,
                        credentials=credentials
                    )
                    logger.info("BigQuery connector initialized with default credentials")
            else:
                # Use default credentials from gcloud
                credentials, project = default()
                self.client = bigquery.Client(
                    project=self.project_id,
                    credentials=credentials
                )
                logger.info("BigQuery connector initialized with default credentials")

        except Exception as e:
            logger.error(f"Failed to initialize BigQuery connector: {e}")
            raise ConnectionError(f"Failed to connect to BigQuery: {e}")

    def disconnect(self) -> None:
        """
        Close BigQuery connection.

        Note: BigQuery client doesn't require explicit disconnection,
        but we provide this for interface compliance.
        """
        if self.client:
            self.client.close()
            self.client = None
            logger.info("BigQuery connector disconnected")

    def _qualify_table_names(self, query: str) -> str:
        """
        Auto-qualify unqualified table names with project.dataset prefix, excluding CTEs.

        This is BigQuery-specific functionality to ensure table names are fully qualified.

        Args:
            query: SQL query with potentially unqualified table names

        Returns:
            Query with qualified table names
        """
        # Extract CTE names from WITH clauses to avoid qualifying them
        cte_pattern = r'\bWITH\s+(\w+)\s+AS\s*\(|,\s*(\w+)\s+AS\s*\('
        cte_names = set()
        for match in re.finditer(cte_pattern, query, re.IGNORECASE):
            cte_name = match.group(1) or match.group(2)
            if cte_name:
                cte_names.add(cte_name.lower())

        if cte_names:
            logger.info(f"Found {len(cte_names)} CTEs: {cte_names}")

        # Pattern to match unqualified table names (no backticks or dots before them)
        # Matches: FROM tablename, JOIN tablename, but not FROM `project.dataset.table` or dataset.table
        pattern = r'\b(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'

        def replacer(match):
            keyword = match.group(1)
            table_name = match.group(2)

            # Don't qualify if it's a CTE name
            if table_name.lower() in cte_names:
                return match.group(0)  # Return unchanged

            # Don't qualify if already qualified (contains backtick or will be qualified)
            qualified_name = f"`{self.project_id}.{self.dataset_id}.{table_name}`"
            return f"{keyword} {qualified_name}"

        qualified_query = re.sub(pattern, replacer, query, flags=re.IGNORECASE)

        if qualified_query != query:
            logger.info(f"Auto-qualified table names in query")

        return qualified_query

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a SQL query and return results with pagination support.

        Args:
            query: SQL query to execute
            parameters: Query parameters (not currently used for BigQuery)
            **kwargs: Additional options:
                - max_rows: Maximum number of rows to fetch total
                - timeout: Query timeout in seconds
                - page_token: Token for fetching next page
                - page_size: Number of rows per page

        Returns:
            Dictionary with:
                - rows: List of result rows
                - total_rows: Total number of rows
                - fetched_rows: Number of rows in this page
                - has_more: Boolean indicating more results available
                - next_page_token: Token for next page (if applicable)
                - truncated: Boolean if results were truncated
                - page_info: Pagination metadata

        Raises:
            QueryExecutionError: If query execution fails
        """
        if not self.client:
            raise QueryExecutionError("BigQuery client not connected")

        try:
            # Extract parameters
            max_rows = kwargs.get('max_rows')
            timeout = kwargs.get('timeout', settings.bigquery_query_timeout_seconds)
            page_token = kwargs.get('page_token')
            page_size = kwargs.get('page_size', 10000)

            # Safety limit for single page
            if page_size > 100000:
                logger.warning(f"Page size {page_size} exceeds safe limit, capping at 100,000")
                page_size = 100000

            # Auto-qualify unqualified table names
            query = self._qualify_table_names(query)

            logger.info(
                f"Executing query: {query[:100]}... "
                f"(timeout: {timeout}s, page_size: {page_size}, page_token: {page_token is not None})"
            )

            # Configure query job with timeout
            job_config = bigquery.QueryJobConfig()
            query_job = self.client.query(query, job_config=job_config)

            # Wait for query to complete
            query_job.result(timeout=timeout)

            # Get destination table for pagination
            destination = query_job.destination

            # Use list_rows for proper pagination support
            if page_token:
                # Resume from page token - use list_rows API
                results = self.client.list_rows(
                    destination,
                    page_token=page_token,
                    max_results=page_size
                )
            else:
                # First page
                results = self.client.list_rows(
                    destination,
                    max_results=page_size
                )

            # Get total row count
            total_rows = results.total_rows

            # Collect rows from current page
            rows = []
            for row in results:
                rows.append(dict(row))

            # Check if there are more pages
            next_page_token = results.next_page_token
            has_more = next_page_token is not None

            # Calculate page info
            current_page_size = len(rows)

            # If max_rows is set, check if we've hit the limit
            truncated = False
            if max_rows is not None and current_page_size >= max_rows:
                rows = rows[:max_rows]
                truncated = True
                has_more = False
                next_page_token = None
                logger.warning(f"Result set truncated at {max_rows} rows (max_rows limit)")

            logger.info(
                f"Query returned {current_page_size} rows on this page "
                f"(total available: {total_rows}, has_more: {has_more})"
            )

            return {
                'rows': rows,
                'total_rows': total_rows,
                'fetched_rows': current_page_size,
                'has_more': has_more,
                'next_page_token': next_page_token,
                'truncated': truncated,
                'page_info': {
                    'page_size': page_size,
                    'current_page_size': current_page_size,
                    'total_rows': total_rows,
                    'has_next_page': has_more
                },
                'metadata': {
                    'bytes_processed': query_job.total_bytes_processed if query_job.total_bytes_processed else 0,
                    'cache_hit': query_job.cache_hit if hasattr(query_job, 'cache_hit') else False,
                }
            }

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise QueryExecutionError(f"BigQuery query execution failed: {e}")

    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get schema information for a specific table.

        Args:
            table_name: Name of the table
            schema: Dataset name (if different from default)

        Returns:
            Dictionary with table metadata and column information

        Raises:
            TableNotFoundError: If table doesn't exist
        """
        if not self.client:
            raise QueryExecutionError("BigQuery client not connected")

        try:
            dataset = schema or self.dataset_id
            table_ref = f"{self.project_id}.{dataset}.{table_name}"
            table = self.client.get_table(table_ref)

            schema_info = {
                "table_name": table_name,
                "schema": dataset,  # BigQuery uses "dataset" instead of "schema"
                "dataset": dataset,
                "project": self.project_id,
                "description": table.description,
                "row_count": table.num_rows,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "columns": []
            }

            for field in table.schema:
                column_info = {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description,
                    "is_nullable": field.mode != "REQUIRED"
                }
                schema_info["columns"].append(column_info)

            return schema_info

        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {e}")
            raise TableNotFoundError(f"Table {table_name} not found: {e}")

    def list_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List all tables in a dataset.

        Args:
            schema: Dataset name (if different from default)

        Returns:
            List of table names

        Raises:
            SchemaNotFoundError: If dataset doesn't exist
        """
        if not self.client:
            raise QueryExecutionError("BigQuery client not connected")

        try:
            dataset = schema or self.dataset_id
            dataset_ref = f"{self.project_id}.{dataset}"
            tables = list(self.client.list_tables(dataset_ref))
            return [table.table_id for table in tables]

        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            raise SchemaNotFoundError(f"Dataset not found: {e}")

    def get_dataset_schema(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get schema information for all tables in a dataset.

        Args:
            schema: Dataset name (if different from default)

        Returns:
            List of table schema dictionaries

        Raises:
            SchemaNotFoundError: If dataset doesn't exist
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
        Validate a query without executing it (dry-run).

        BigQuery supports dry-run validation which estimates cost and validates syntax.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary with validation results and cost estimation
        """
        if not self.client:
            raise QueryExecutionError("BigQuery client not connected")

        try:
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            query_job = self.client.query(query, job_config=job_config)

            return {
                "valid": True,
                "error": None,
                "total_bytes_processed": query_job.total_bytes_processed,
                "estimated_cost_usd": (query_job.total_bytes_processed / 1e12) * 5.0,  # $5 per TB
                "warnings": []
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "total_bytes_processed": 0,
                "estimated_cost_usd": 0.0,
                "warnings": []
            }

    def get_capabilities(self) -> DatabaseCapabilities:
        """
        Get BigQuery capabilities.

        Returns:
            DatabaseCapabilities object for BigQuery
        """
        return self._capabilities

    def qualify_table_name(self, table_name: str, schema: Optional[str] = None) -> str:
        """
        Qualify a table name with BigQuery's specific format.

        Args:
            table_name: Unqualified table name
            schema: Dataset name (optional, uses default if not provided)

        Returns:
            Fully qualified table name in BigQuery format: `project.dataset.table`
        """
        dataset = schema or self.dataset_id
        return f"`{self.project_id}.{dataset}.{table_name}`"


# Backward compatibility: Keep BigQueryClient as an alias
# This allows existing code to continue working without changes
BigQueryClient = BigQueryConnector
