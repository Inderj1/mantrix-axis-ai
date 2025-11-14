from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from google.auth import default
import json
import structlog
from src.config import settings

logger = structlog.get_logger()


class BigQueryClient:
    def __init__(self):
        self.project_id = settings.google_cloud_project
        self.dataset_id = settings.bigquery_dataset
        self.client = self._initialize_client()
    
    def _initialize_client(self) -> bigquery.Client:
        """Initialize BigQuery client using gcloud SDK or service account."""
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
                        client = bigquery.Client(
                            project=self.project_id,
                            credentials=credentials
                        )
                        logger.info("BigQuery client initialized with service account")
                    else:
                        # User credentials or other type - use default credentials
                        credentials, project = default()
                        client = bigquery.Client(
                            project=self.project_id,
                            credentials=credentials
                        )
                        logger.info("BigQuery client initialized with application default credentials")
                else:
                    # Fall back to default credentials
                    credentials, project = default()
                    client = bigquery.Client(
                        project=self.project_id,
                        credentials=credentials
                    )
                    logger.info("BigQuery client initialized with default credentials")
            else:
                # Use default credentials from gcloud
                credentials, project = default()
                client = bigquery.Client(
                    project=self.project_id,
                    credentials=credentials
                )
                logger.info("BigQuery client initialized with default credentials")
            
            return client
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    
    def _qualify_table_names(self, query: str) -> str:
        """Auto-qualify unqualified table names with project.dataset prefix, excluding CTEs."""
        import re

        # Extract CTE names from WITH clauses to avoid qualifying them
        cte_pattern = r'\bWITH\s+(\w+)\s+AS\s*\(|,\s*(\w+)\s+AS\s*\('
        cte_names = set()
        for match in re.finditer(cte_pattern, query, re.IGNORECASE):
            cte_name = match.group(1) or match.group(2)
            if cte_name:
                cte_names.add(cte_name.lower())

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

    def execute_query(self, query: str, max_rows: Optional[int] = None) -> Dict[str, Any]:
        """Execute a SQL query and return results with metadata.

        Args:
            query: SQL query to execute
            max_rows: Maximum number of rows to fetch (default: 10000 for safety)

        Returns:
            Dictionary with 'rows', 'total_rows', 'truncated' keys
        """
        try:
            # Safety limit - prevent memory issues
            if max_rows is None:
                max_rows = 10000  # Default max

            # Auto-qualify unqualified table names
            query = self._qualify_table_names(query)

            logger.info(f"Executing query: {query[:100]}...")
            query_job = self.client.query(query)
            results = query_job.result()

            # Get total row count
            total_rows = results.total_rows

            rows = []
            truncated = False

            for i, row in enumerate(results):
                if i >= max_rows:
                    truncated = True
                    logger.warning(f"Result set truncated at {max_rows} rows (total: {total_rows})")
                    break
                rows.append(dict(row))

            logger.info(f"Query returned {len(rows)} rows (total available: {total_rows}, truncated: {truncated})")

            return {
                'rows': rows,
                'total_rows': total_rows,
                'truncated': truncated,
                'fetched_rows': len(rows)
            }
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table."""
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"
            table = self.client.get_table(table_ref)
            
            schema_info = {
                "table_name": table_name,
                "dataset": self.dataset_id,
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
            raise
    
    def list_tables(self) -> List[str]:
        """List all tables in the dataset."""
        try:
            dataset_ref = f"{self.project_id}.{self.dataset_id}"
            tables = list(self.client.list_tables(dataset_ref))
            return [table.table_id for table in tables]
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            raise
    
    def get_dataset_schema(self) -> List[Dict[str, Any]]:
        """Get schema information for all tables in the dataset."""
        schemas = []
        table_names = self.list_tables()
        
        for table_name in table_names:
            try:
                schema = self.get_table_schema(table_name)
                schemas.append(schema)
            except Exception as e:
                logger.warning(f"Failed to get schema for {table_name}: {e}")
                continue
        
        return schemas
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate a query without executing it."""
        try:
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            query_job = self.client.query(query, job_config=job_config)
            
            return {
                "valid": True,
                "total_bytes_processed": query_job.total_bytes_processed,
                "estimated_cost_usd": (query_job.total_bytes_processed / 1e12) * 5.0  # $5 per TB
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }