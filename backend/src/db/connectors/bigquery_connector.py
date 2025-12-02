"""
BigQuery Database Connector

Implements the BaseDatabaseConnector interface for Google BigQuery.
This is a refactored version of the original BigQueryClient that conforms to the generic connector pattern.

Supports multiple authentication methods:
- service_account: Traditional service account JSON key file
- workload_identity: AWS/Azure/GCP Workload Identity Federation (keyless)
- oauth: Google OAuth 2.0 user credentials
"""
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth import default
import json
import os
import re
import structlog

from ..base_connector import (
    BaseDatabaseConnector,
    QueryExecutionError,
    TableNotFoundError,
    SchemaNotFoundError,
    ConnectionError as ConnectorConnectionError
)
from ..database_capabilities import BIGQUERY_CAPABILITIES, DatabaseCapabilities
from src.config import settings

logger = structlog.get_logger()

# Valid authentication methods
AUTH_METHOD_SERVICE_ACCOUNT = "service_account"
AUTH_METHOD_WORKLOAD_IDENTITY = "workload_identity"
AUTH_METHOD_OAUTH = "oauth"
VALID_AUTH_METHODS = [AUTH_METHOD_SERVICE_ACCOUNT, AUTH_METHOD_WORKLOAD_IDENTITY, AUTH_METHOD_OAUTH]


class BigQueryConnector(BaseDatabaseConnector):
    """
    Google BigQuery database connector.

    Implements the BaseDatabaseConnector interface for BigQuery,
    providing query execution, schema introspection, and metadata operations.

    Supports multiple authentication methods:
    - service_account: Traditional JSON key file (via file path or JSON string)
    - workload_identity: AWS/Azure Workload Identity Federation (keyless)
    - oauth: Google OAuth 2.0 user credentials
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        auto_connect: bool = False,
        # Authentication method selection
        auth_method: str = AUTH_METHOD_SERVICE_ACCOUNT,
        # Service account options (JSON string or file path)
        credentials_json: Optional[str] = None,
        # Workload Identity Federation options
        wif_provider_resource_name: Optional[str] = None,
        wif_service_account_email: Optional[str] = None,
        # OAuth options
        oauth_credentials: Optional[Dict[str, Any]] = None,
        # BigQuery location for job execution
        location: Optional[str] = None,
    ):
        """
        Initialize BigQuery connector.

        Args:
            project_id: GCP project ID (defaults to settings.google_cloud_project)
            dataset_id: BigQuery dataset ID (defaults to settings.bigquery_dataset)
            auto_connect: If True, connect immediately. If False, connect lazily on first use.
            auth_method: Authentication method - 'service_account', 'workload_identity', or 'oauth'
            credentials_json: Service account JSON as a string (alternative to file)
            wif_provider_resource_name: WIF provider resource name (for workload_identity)
            wif_service_account_email: Service account to impersonate (for workload_identity)
            oauth_credentials: OAuth credentials dict with access_token, refresh_token, etc.
            location: BigQuery location for job execution (e.g., 'US', 'EU', 'us-central1')
        """
        super().__init__()
        self.project_id = project_id or settings.google_cloud_project
        self.dataset_id = dataset_id or settings.bigquery_dataset
        self.location = location
        self.client: Optional[bigquery.Client] = None
        self._capabilities = BIGQUERY_CAPABILITIES

        # Authentication configuration
        if auth_method not in VALID_AUTH_METHODS:
            raise ValueError(f"Invalid auth_method '{auth_method}'. Must be one of: {VALID_AUTH_METHODS}")
        self.auth_method = auth_method
        self._credentials_json = credentials_json
        self.wif_provider_resource_name = wif_provider_resource_name
        self.wif_service_account_email = wif_service_account_email
        self._oauth_credentials = oauth_credentials

        # Only auto-connect if explicitly requested (lazy connection by default)
        if auto_connect:
            try:
                self.connect()
            except Exception as e:
                logger.error(f"Failed to initialize BigQuery connector: {e}")
                # Don't raise - allow service to start without BigQuery

    def connect(self) -> None:
        """
        Establish connection to BigQuery.

        Initializes the BigQuery client using the configured authentication method:
        - service_account: JSON key file or string
        - workload_identity: AWS/Azure WIF token exchange
        - oauth: User OAuth credentials

        Raises:
            ConnectionError: If connection initialization fails
        """
        try:
            if self.auth_method == AUTH_METHOD_WORKLOAD_IDENTITY:
                credentials = self._get_wif_credentials()
                logger.info("BigQuery connector initialized with Workload Identity Federation")
            elif self.auth_method == AUTH_METHOD_OAUTH:
                credentials = self._get_oauth_credentials()
                logger.info("BigQuery connector initialized with OAuth credentials")
            else:
                # Default: service_account
                credentials = self._get_service_account_credentials()

            self.client = bigquery.Client(
                project=self.project_id,
                credentials=credentials,
                location=self.location  # May be None, which is fine
            )

        except Exception as e:
            logger.error(f"Failed to initialize BigQuery connector: {e}")
            raise ConnectorConnectionError(f"Failed to connect to BigQuery: {e}")

    def _get_service_account_credentials(self):
        """
        Get credentials from service account JSON (string or file).

        Returns:
            google.auth.credentials.Credentials object
        """
        # Option 1: JSON string passed directly (from UI/API)
        if self._credentials_json:
            try:
                cred_info = json.loads(self._credentials_json)
                credentials = service_account.Credentials.from_service_account_info(cred_info)
                logger.info("Using service account credentials from JSON string")
                return credentials
            except json.JSONDecodeError as e:
                raise ConnectorConnectionError(f"Invalid credentials JSON: {e}")

        # Option 2: File path from environment variable
        if settings.google_application_credentials:
            if os.path.exists(settings.google_application_credentials):
                with open(settings.google_application_credentials, 'r') as f:
                    cred_data = json.load(f)

                if cred_data.get('type') == 'service_account':
                    credentials = service_account.Credentials.from_service_account_file(
                        settings.google_application_credentials
                    )
                    logger.info("Using service account credentials from file")
                    return credentials
                else:
                    # User credentials or other type - use default
                    credentials, _ = default()
                    logger.info("Using application default credentials (non-service-account file)")
                    return credentials

        # Option 3: Fall back to application default credentials
        credentials, _ = default()
        logger.info("Using application default credentials")
        return credentials

    def _get_wif_credentials(self):
        """
        Get credentials via Workload Identity Federation.

        Uses AWS IAM credentials (from ECS task role) to exchange for GCP credentials
        via the Security Token Service (STS).

        Returns:
            google.auth.credentials.Credentials object

        Raises:
            ConnectionError: If WIF configuration is incomplete
        """
        if not self.wif_provider_resource_name:
            raise ConnectorConnectionError(
                "Workload Identity Federation requires 'wif_provider_resource_name'"
            )
        if not self.wif_service_account_email:
            raise ConnectorConnectionError(
                "Workload Identity Federation requires 'wif_service_account_email'"
            )

        try:
            # Import google.auth.aws for AWS credential exchange
            from google.auth import aws as google_aws

            # Build the external account configuration for AWS
            # This uses the ECS container metadata endpoint to get AWS credentials
            wif_config = {
                "type": "external_account",
                "audience": f"//iam.googleapis.com/{self.wif_provider_resource_name}",
                "subject_token_type": "urn:ietf:params:aws:token-type:aws4_request",
                "service_account_impersonation_url": (
                    f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
                    f"{self.wif_service_account_email}:generateAccessToken"
                ),
                "token_url": "https://sts.googleapis.com/v1/token",
                "credential_source": {
                    "environment_id": "aws1",
                    "region_url": "http://169.254.169.254/latest/meta-data/placement/region",
                    "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials",
                    "regional_cred_verification_url": (
                        "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15"
                    )
                }
            }

            credentials = google_aws.Credentials.from_info(wif_config)
            logger.info(
                f"WIF credentials created for service account: {self.wif_service_account_email}"
            )
            return credentials

        except ImportError:
            raise ConnectorConnectionError(
                "Workload Identity Federation requires google-auth>=2.23.0"
            )
        except Exception as e:
            raise ConnectorConnectionError(f"Failed to get WIF credentials: {e}")

    def _get_oauth_credentials(self):
        """
        Get credentials from OAuth tokens.

        Uses stored OAuth access/refresh tokens to create credentials.

        Returns:
            google.oauth2.credentials.Credentials object

        Raises:
            ConnectionError: If OAuth credentials are missing or invalid
        """
        if not self._oauth_credentials:
            raise ConnectorConnectionError("OAuth auth method requires 'oauth_credentials'")

        access_token = self._oauth_credentials.get('access_token')
        refresh_token = self._oauth_credentials.get('refresh_token')
        token_uri = self._oauth_credentials.get('token_uri', 'https://oauth2.googleapis.com/token')
        client_id = self._oauth_credentials.get('client_id') or settings.google_oauth_client_id
        client_secret = self._oauth_credentials.get('client_secret') or settings.google_oauth_client_secret

        if not access_token:
            raise ConnectorConnectionError("OAuth credentials missing 'access_token'")

        try:
            credentials = OAuthCredentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=[
                    'https://www.googleapis.com/auth/bigquery',
                    'https://www.googleapis.com/auth/cloud-platform.read-only'
                ]
            )
            logger.info("Using OAuth credentials for BigQuery")
            return credentials

        except Exception as e:
            raise ConnectorConnectionError(f"Failed to create OAuth credentials: {e}")

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
