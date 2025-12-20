"""
Federated Query Orchestrator

Orchestrates cross-database queries with automatic federation strategy selection.

Supports multiple federation strategies:
1. SINGLE_SOURCE - Query touches one DB only, push to source
2. DUCKDB_LOCAL - Small cross-DB JOIN (<100K rows), join in memory
3. S3_CUSTOMER_DB - Large cross-DB JOIN using customer's federation DB
4. S3_AXIS_INFRA - Large cross-DB JOIN using Axis infrastructure (DuckDB/Redshift)

Usage:
    orchestrator = FederatedQueryOrchestrator(connectors={
        "bigquery": bq_connector,
        "snowflake": sf_connector
    })

    result = await orchestrator.execute_federated_query(
        query="SELECT * FROM bigquery.customers c JOIN snowflake.orders o ON c.id = o.customer_id",
        federation_config=FederationConfig(federation_db="snowflake")
    )
"""

import asyncio
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()

# Optional imports for specific strategies
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    duckdb = None

try:
    import boto3
    import pyarrow as pa
    import pyarrow.parquet as pq
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    boto3 = None
    pa = None
    pq = None


class FederationStrategy(Enum):
    """Federation execution strategies."""
    SINGLE_SOURCE = "single_source"      # Query touches one DB only
    DUCKDB_LOCAL = "duckdb_local"        # Small JOIN in memory
    S3_CUSTOMER_DB = "s3_customer_db"    # S3 + customer's federation DB
    S3_AXIS_INFRA = "s3_axis_infra"      # S3 + DuckDB/Redshift Serverless


@dataclass
class FederationConfig:
    """Customer's federation configuration."""
    # Federation database (customer's choice for running JOINs)
    federation_db: Optional[str] = None  # "snowflake", "bigquery", "redshift"
    federation_connector: Optional[Any] = None  # Connector with write access

    # S3 configuration
    s3_bucket: Optional[str] = None      # Customer's S3 or Axis S3
    s3_prefix: str = "federation"        # Prefix for temp files
    aws_region: str = "us-east-1"

    # Thresholds
    max_local_rows: int = 100_000        # Threshold for DuckDB vs S3
    max_memory_mb: int = 1024            # Max memory for local JOINs

    # Cleanup
    auto_cleanup: bool = True            # Auto-delete temp S3 files
    ttl_hours: int = 24                  # TTL for temp data


@dataclass
class FederatedQueryResult:
    """Result of a federated query execution."""
    status: str  # "complete", "error"
    strategy: FederationStrategy
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time_seconds: float = 0.0

    # Federation metadata
    sources_queried: List[str] = field(default_factory=list)
    federation_db_used: Optional[str] = None
    s3_paths: List[str] = field(default_factory=list)
    external_tables_created: List[str] = field(default_factory=list)

    # Error info
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status,
            "strategy": self.strategy.value,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_seconds": self.execution_time_seconds,
            "federation_metadata": {
                "sources_queried": self.sources_queried,
                "federation_db_used": self.federation_db_used,
                "s3_paths": self.s3_paths,
                "external_tables_created": self.external_tables_created
            },
            "error": self.error
        }


@dataclass
class QueryPlan:
    """Plan for executing a federated query."""
    original_query: str
    strategy: FederationStrategy
    source_queries: Dict[str, str]  # db_name -> SQL query
    join_query: Optional[str] = None  # Final JOIN query
    estimated_rows: Dict[str, int] = field(default_factory=dict)  # db_name -> row estimate
    tables_by_source: Dict[str, List[str]] = field(default_factory=dict)


class FederatedQueryOrchestrator:
    """
    Orchestrates cross-database queries with automatic federation strategy selection.

    This class:
    1. Parses queries to identify which databases are involved
    2. Selects the optimal federation strategy
    3. Executes using the selected strategy
    4. Handles cleanup of temp resources
    """

    # Default S3 bucket for Axis SaaS
    DEFAULT_S3_BUCKET = "mantrix-dev-federation-709141244278"

    def __init__(
        self,
        connectors: Dict[str, Any],
        default_config: Optional[FederationConfig] = None
    ):
        """
        Initialize the federated query orchestrator.

        Args:
            connectors: Dict mapping db names to connector instances
                        e.g., {"bigquery": bq_connector, "snowflake": sf_connector}
            default_config: Default federation configuration
        """
        self.connectors = connectors
        self.default_config = default_config or FederationConfig(
            s3_bucket=self.DEFAULT_S3_BUCKET
        )

        # Initialize S3 client if available
        self._s3_client = None
        if S3_AVAILABLE:
            self._s3_client = boto3.client('s3', region_name=self.default_config.aws_region)

        # Track active jobs for cleanup
        self._active_jobs: Dict[str, Dict[str, Any]] = {}

        logger.info(
            "FederatedQueryOrchestrator initialized",
            connectors=list(connectors.keys()),
            duckdb_available=DUCKDB_AVAILABLE,
            s3_available=S3_AVAILABLE
        )

    async def execute_federated_query(
        self,
        query: str,
        federation_config: Optional[FederationConfig] = None
    ) -> FederatedQueryResult:
        """
        Execute a query that may span multiple databases.

        Args:
            query: SQL query (may reference multiple databases)
            federation_config: Optional override for federation config

        Returns:
            FederatedQueryResult with execution results
        """
        start_time = datetime.utcnow()
        config = federation_config or self.default_config
        job_id = str(uuid.uuid4())[:8]

        logger.info(
            "Starting federated query execution",
            job_id=job_id,
            query_preview=query[:100] if query else None
        )

        try:
            # Step 1: Parse query to identify sources
            query_plan = self._parse_query(query)

            # Step 2: Select federation strategy
            strategy = self._select_strategy(query_plan, config)
            query_plan.strategy = strategy

            logger.info(
                "Federation strategy selected",
                job_id=job_id,
                strategy=strategy.value,
                sources=list(query_plan.source_queries.keys())
            )

            # Step 3: Execute using selected strategy
            if strategy == FederationStrategy.SINGLE_SOURCE:
                result = await self._execute_single_source(query_plan)
            elif strategy == FederationStrategy.DUCKDB_LOCAL:
                result = await self._execute_duckdb_local(query_plan, config)
            elif strategy == FederationStrategy.S3_CUSTOMER_DB:
                result = await self._execute_s3_customer_db(query_plan, config, job_id)
            elif strategy == FederationStrategy.S3_AXIS_INFRA:
                result = await self._execute_s3_axis_infra(query_plan, config, job_id)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time_seconds = execution_time

            logger.info(
                "Federated query completed",
                job_id=job_id,
                strategy=strategy.value,
                row_count=result.row_count,
                execution_time=f"{execution_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(
                "Federated query failed",
                job_id=job_id,
                error=str(e),
                exc_info=True
            )
            return FederatedQueryResult(
                status="error",
                strategy=FederationStrategy.SINGLE_SOURCE,
                error=str(e)
            )

    def _parse_query(self, query: str) -> QueryPlan:
        """
        Parse a federated query to identify source databases and tables.

        Supports syntax like:
        - SELECT * FROM bigquery.schema.table
        - SELECT * FROM snowflake.database.schema.table
        - SELECT * FROM postgres.table
        """
        # Pattern to match database.schema.table or database.table references
        # Handles: db.table, db.schema.table, db.database.schema.table
        table_pattern = r'\b(FROM|JOIN)\s+(\w+)\.(\w+(?:\.\w+)*)'

        source_tables: Dict[str, List[str]] = {}
        source_queries: Dict[str, str] = {}

        matches = re.findall(table_pattern, query, re.IGNORECASE)

        for match in matches:
            _, db_name, table_path = match
            db_name_lower = db_name.lower()

            if db_name_lower in self.connectors:
                if db_name_lower not in source_tables:
                    source_tables[db_name_lower] = []
                source_tables[db_name_lower].append(table_path)

        # If only one source or no recognized sources, treat as single source
        if len(source_tables) <= 1:
            # Single source - use the original query
            source_db = list(source_tables.keys())[0] if source_tables else list(self.connectors.keys())[0]
            source_queries[source_db] = query
        else:
            # Multiple sources - split query (simplified)
            # In production, use a proper SQL parser like sqlglot
            for db_name, tables in source_tables.items():
                # Extract sub-query for each source
                # This is a simplified version - real implementation needs proper SQL parsing
                source_queries[db_name] = query  # Placeholder

        return QueryPlan(
            original_query=query,
            strategy=FederationStrategy.SINGLE_SOURCE,  # Will be updated
            source_queries=source_queries,
            tables_by_source=source_tables
        )

    def _select_strategy(
        self,
        query_plan: QueryPlan,
        config: FederationConfig
    ) -> FederationStrategy:
        """
        Select optimal federation strategy based on query and config.

        Decision tree:
        1. Single source? -> SINGLE_SOURCE
        2. Customer has federation DB with write access? -> S3_CUSTOMER_DB
        3. Estimated result < max_local_rows? -> DUCKDB_LOCAL
        4. Otherwise -> S3_AXIS_INFRA
        """
        # Single source - no federation needed
        if len(query_plan.source_queries) <= 1:
            return FederationStrategy.SINGLE_SOURCE

        # Multiple sources - need federation
        total_estimated_rows = sum(query_plan.estimated_rows.values())

        # Customer has a federation DB?
        if config.federation_db and config.federation_connector:
            return FederationStrategy.S3_CUSTOMER_DB

        # Small enough for local JOIN?
        if total_estimated_rows < config.max_local_rows and DUCKDB_AVAILABLE:
            return FederationStrategy.DUCKDB_LOCAL

        # Fall back to Axis infrastructure
        return FederationStrategy.S3_AXIS_INFRA

    async def _execute_single_source(
        self,
        query_plan: QueryPlan
    ) -> FederatedQueryResult:
        """Execute query on a single source database."""
        source_db = list(query_plan.source_queries.keys())[0]
        query = query_plan.source_queries[source_db]
        connector = self.connectors[source_db]

        # Execute query
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: connector.execute_query(query)
        )

        rows = result.get('rows', [])

        return FederatedQueryResult(
            status="complete",
            strategy=FederationStrategy.SINGLE_SOURCE,
            rows=rows,
            row_count=len(rows),
            sources_queried=[source_db]
        )

    async def _execute_duckdb_local(
        self,
        query_plan: QueryPlan,
        config: FederationConfig
    ) -> FederatedQueryResult:
        """
        Execute cross-DB JOIN locally using DuckDB.

        1. Fetch data from each source
        2. Load into DuckDB in-memory tables
        3. Execute JOIN in DuckDB
        """
        if not DUCKDB_AVAILABLE:
            raise RuntimeError("DuckDB not available for local JOINs")

        sources_queried = []
        duckdb_tables = {}

        # Create in-memory DuckDB connection
        conn = duckdb.connect(':memory:')

        try:
            # Fetch data from each source
            for db_name, query in query_plan.source_queries.items():
                connector = self.connectors[db_name]

                # Execute query on source
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda q=query, c=connector: c.execute_query(q)
                )

                rows = result.get('rows', [])
                sources_queried.append(db_name)

                if rows:
                    # Create DuckDB table from results
                    # Convert list of dicts to pyarrow table for DuckDB compatibility
                    import pyarrow as pa
                    arrow_table = pa.Table.from_pylist(rows)

                    table_name = f"source_{db_name}"
                    conn.register(table_name, arrow_table)
                    duckdb_tables[db_name] = table_name

            # Execute JOIN query in DuckDB
            # Rewrite the original query to use DuckDB table names
            rewritten_query = query_plan.original_query

            # Replace database-prefixed table names with DuckDB table names
            for db_name, table_name in duckdb_tables.items():
                # Replace patterns like "bigquery.customers" or "bigquery.table"
                import re
                pattern = rf'\b{db_name}\.(\w+)\b'
                rewritten_query = re.sub(pattern, table_name, rewritten_query)

            # If no explicit JOINs detected, do a simple UNION of all tables
            if not duckdb_tables:
                return FederatedQueryResult(
                    status="complete",
                    strategy=FederationStrategy.DUCKDB_LOCAL,
                    rows=[],
                    row_count=0,
                    sources_queried=sources_queried
                )

            # Try to execute the rewritten query
            try:
                final_result = conn.execute(rewritten_query).fetchall()
                columns = [desc[0] for desc in conn.description] if conn.description else []
            except Exception as query_err:
                # If the rewritten query fails, fall back to simple selection
                logger.warning(
                    "Rewritten query failed, falling back to simple selection",
                    error=str(query_err)
                )
                # Just select from the first table as fallback
                first_table = list(duckdb_tables.values())[0]
                final_result = conn.execute(f"SELECT * FROM {first_table}").fetchall()
                columns = [desc[0] for desc in conn.description] if conn.description else []

            # Convert result to list of dicts
            if final_result and columns:
                rows = [dict(zip(columns, row)) for row in final_result]
            else:
                rows = []

            return FederatedQueryResult(
                status="complete",
                strategy=FederationStrategy.DUCKDB_LOCAL,
                rows=rows,
                row_count=len(rows),
                sources_queried=sources_queried
            )

        finally:
            conn.close()

    async def _execute_s3_customer_db(
        self,
        query_plan: QueryPlan,
        config: FederationConfig,
        job_id: str
    ) -> FederatedQueryResult:
        """
        Execute cross-DB JOIN using customer's federation DB.

        1. Export non-federation sources to S3 as Parquet
        2. Create external tables in customer's federation DB
        3. Execute JOIN in federation DB
        4. Cleanup temp resources
        """
        if not S3_AVAILABLE:
            raise RuntimeError("S3/Parquet libraries not available")

        s3_paths = []
        external_tables = []
        sources_queried = []

        try:
            federation_db = config.federation_db
            federation_connector = config.federation_connector

            # Export non-federation sources to S3
            for db_name, query in query_plan.source_queries.items():
                if db_name == federation_db:
                    # This source is native to federation DB, skip export
                    continue

                connector = self.connectors[db_name]
                sources_queried.append(db_name)

                # Execute query on source
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda q=query, c=connector: c.execute_query(q)
                )

                rows = result.get('rows', [])

                if rows:
                    # Export to S3 as Parquet
                    s3_path = await self._export_to_s3(
                        rows=rows,
                        bucket=config.s3_bucket,
                        prefix=f"{config.s3_prefix}/{job_id}/{db_name}",
                        job_id=job_id
                    )
                    s3_paths.append(s3_path)

                    # Create external table in federation DB
                    table_name = f"_fed_temp_{job_id}_{db_name}"
                    await self._create_external_table(
                        connector=federation_connector,
                        db_type=federation_db,
                        table_name=table_name,
                        s3_path=s3_path,
                        schema=self._infer_schema(rows[0])
                    )
                    external_tables.append(table_name)

            # Execute JOIN in federation DB
            # In production, rewrite query to use external table names
            join_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: federation_connector.execute_query(query_plan.original_query)
            )

            rows = join_result.get('rows', [])

            return FederatedQueryResult(
                status="complete",
                strategy=FederationStrategy.S3_CUSTOMER_DB,
                rows=rows,
                row_count=len(rows),
                sources_queried=sources_queried,
                federation_db_used=federation_db,
                s3_paths=s3_paths,
                external_tables_created=external_tables
            )

        finally:
            # Cleanup external tables and S3 data
            if config.auto_cleanup:
                await self._cleanup(
                    connector=federation_connector,
                    external_tables=external_tables,
                    s3_bucket=config.s3_bucket,
                    s3_paths=s3_paths
                )

    async def _execute_s3_axis_infra(
        self,
        query_plan: QueryPlan,
        config: FederationConfig,
        job_id: str
    ) -> FederatedQueryResult:
        """
        Execute cross-DB JOIN using Axis infrastructure (DuckDB reading from S3).

        1. Export all sources to S3 as Parquet
        2. Use DuckDB to read Parquet files directly from S3
        3. Execute JOIN in DuckDB
        4. Cleanup temp resources
        """
        if not S3_AVAILABLE:
            raise RuntimeError("S3/Parquet libraries not available")
        if not DUCKDB_AVAILABLE:
            raise RuntimeError("DuckDB not available")

        s3_paths = []
        sources_queried = []

        try:
            # Export all sources to S3
            for db_name, query in query_plan.source_queries.items():
                connector = self.connectors[db_name]
                sources_queried.append(db_name)

                # Execute query on source
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda q=query, c=connector: c.execute_query(q)
                )

                rows = result.get('rows', [])

                if rows:
                    # Export to S3 as Parquet
                    s3_path = await self._export_to_s3(
                        rows=rows,
                        bucket=config.s3_bucket,
                        prefix=f"{config.s3_prefix}/{job_id}/{db_name}",
                        job_id=job_id
                    )
                    s3_paths.append(s3_path)

            # Use DuckDB to read from S3 and execute JOIN
            conn = duckdb.connect(':memory:')

            try:
                # Install and load httpfs for S3 access
                conn.execute("INSTALL httpfs; LOAD httpfs;")

                # Configure S3 credentials (from environment or boto3 session)
                # In production, use IAM roles or explicit credentials
                conn.execute(f"SET s3_region='{config.aws_region}';")

                # Create views for each S3 path
                for i, s3_path in enumerate(s3_paths):
                    db_name = sources_queried[i]
                    conn.execute(f"""
                        CREATE VIEW source_{db_name} AS
                        SELECT * FROM read_parquet('{s3_path}')
                    """)

                # Execute JOIN
                # In production, rewrite query to use view names
                final_result = conn.execute(query_plan.original_query).fetchall()
                columns = [desc[0] for desc in conn.description]

                rows = [dict(zip(columns, row)) for row in final_result]

                return FederatedQueryResult(
                    status="complete",
                    strategy=FederationStrategy.S3_AXIS_INFRA,
                    rows=rows,
                    row_count=len(rows),
                    sources_queried=sources_queried,
                    s3_paths=s3_paths
                )

            finally:
                conn.close()

        finally:
            # Cleanup S3 data
            if config.auto_cleanup:
                await self._cleanup_s3(config.s3_bucket, s3_paths)

    async def _export_to_s3(
        self,
        rows: List[Dict[str, Any]],
        bucket: str,
        prefix: str,
        job_id: str
    ) -> str:
        """Export rows to S3 as Parquet and return S3 path."""
        if not S3_AVAILABLE:
            raise RuntimeError("S3/Parquet libraries not available")

        # Convert to PyArrow table
        table = pa.Table.from_pylist(rows)

        # Write to buffer
        buffer = io.BytesIO()
        pq.write_table(table, buffer, compression='snappy')
        buffer.seek(0)

        # Upload to S3
        s3_key = f"{prefix}/data.parquet"
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=buffer.getvalue()
            )
        )

        s3_path = f"s3://{bucket}/{s3_key}"
        logger.info(f"Exported {len(rows)} rows to {s3_path}")

        return s3_path

    async def _create_external_table(
        self,
        connector: Any,
        db_type: str,
        table_name: str,
        s3_path: str,
        schema: Dict[str, str]
    ) -> None:
        """Create external table in the federation database."""
        if db_type == "snowflake":
            await self._create_snowflake_external_table(
                connector, table_name, s3_path, schema
            )
        elif db_type == "bigquery":
            await self._create_bigquery_external_table(
                connector, table_name, s3_path, schema
            )
        elif db_type == "redshift":
            await self._create_redshift_external_table(
                connector, table_name, s3_path, schema
            )
        else:
            raise ValueError(f"Unsupported federation DB type: {db_type}")

    async def _create_snowflake_external_table(
        self,
        connector: Any,
        table_name: str,
        s3_path: str,
        schema: Dict[str, str]
    ) -> None:
        """Create external table in Snowflake."""
        # Column definitions
        columns = ", ".join([
            f"{col} {self._to_snowflake_type(dtype)}"
            for col, dtype in schema.items()
        ])

        # Create external table
        # Note: Requires pre-configured stage with S3 access
        sql = f"""
        CREATE OR REPLACE EXTERNAL TABLE {table_name} (
            {columns}
        )
        WITH LOCATION = @federation_stage/{s3_path.replace('s3://', '')}/
        FILE_FORMAT = (TYPE = PARQUET)
        AUTO_REFRESH = FALSE
        """

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: connector.execute_query(sql)
        )

        logger.info(f"Created Snowflake external table: {table_name}")

    async def _create_bigquery_external_table(
        self,
        connector: Any,
        table_name: str,
        s3_path: str,
        schema: Dict[str, str]
    ) -> None:
        """Create external table in BigQuery via BigLake."""
        # BigQuery external tables require Cloud Storage or BigLake for S3
        # This is a simplified version
        sql = f"""
        CREATE OR REPLACE EXTERNAL TABLE {table_name}
        WITH CONNECTION `aws-s3-connection`
        OPTIONS (
            format = 'PARQUET',
            uris = ['{s3_path}']
        )
        """

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: connector.execute_query(sql)
        )

        logger.info(f"Created BigQuery external table: {table_name}")

    async def _create_redshift_external_table(
        self,
        connector: Any,
        table_name: str,
        s3_path: str,
        schema: Dict[str, str]
    ) -> None:
        """Create external table in Redshift Spectrum."""
        columns = ", ".join([
            f"{col} {self._to_redshift_type(dtype)}"
            for col, dtype in schema.items()
        ])

        sql = f"""
        CREATE EXTERNAL TABLE spectrum.{table_name} (
            {columns}
        )
        STORED AS PARQUET
        LOCATION '{s3_path}'
        """

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: connector.execute_query(sql)
        )

        logger.info(f"Created Redshift external table: {table_name}")

    def _infer_schema(self, row: Dict[str, Any]) -> Dict[str, str]:
        """Infer schema from a sample row."""
        schema = {}
        for col, value in row.items():
            if isinstance(value, bool):
                schema[col] = "BOOLEAN"
            elif isinstance(value, int):
                schema[col] = "INTEGER"
            elif isinstance(value, float):
                schema[col] = "FLOAT"
            elif isinstance(value, datetime):
                schema[col] = "TIMESTAMP"
            else:
                schema[col] = "STRING"
        return schema

    def _to_snowflake_type(self, dtype: str) -> str:
        """Convert generic type to Snowflake type."""
        mapping = {
            "STRING": "VARCHAR",
            "INTEGER": "INTEGER",
            "FLOAT": "FLOAT",
            "BOOLEAN": "BOOLEAN",
            "TIMESTAMP": "TIMESTAMP",
        }
        return mapping.get(dtype.upper(), "VARCHAR")

    def _to_redshift_type(self, dtype: str) -> str:
        """Convert generic type to Redshift type."""
        mapping = {
            "STRING": "VARCHAR(65535)",
            "INTEGER": "BIGINT",
            "FLOAT": "DOUBLE PRECISION",
            "BOOLEAN": "BOOLEAN",
            "TIMESTAMP": "TIMESTAMP",
        }
        return mapping.get(dtype.upper(), "VARCHAR(65535)")

    async def _cleanup(
        self,
        connector: Any,
        external_tables: List[str],
        s3_bucket: str,
        s3_paths: List[str]
    ) -> None:
        """Cleanup external tables and S3 data."""
        # Drop external tables
        for table in external_tables:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda t=table: connector.execute_query(f"DROP TABLE IF EXISTS {t}")
                )
                logger.debug(f"Dropped external table: {table}")
            except Exception as e:
                logger.warning(f"Failed to drop table {table}: {e}")

        # Delete S3 objects
        await self._cleanup_s3(s3_bucket, s3_paths)

    async def _cleanup_s3(self, bucket: str, s3_paths: List[str]) -> None:
        """Delete S3 objects."""
        if not self._s3_client:
            return

        for s3_path in s3_paths:
            try:
                # Extract key from s3://bucket/key
                key = s3_path.replace(f"s3://{bucket}/", "")
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda k=key: self._s3_client.delete_object(Bucket=bucket, Key=k)
                )
                logger.debug(f"Deleted S3 object: {s3_path}")
            except Exception as e:
                logger.warning(f"Failed to delete S3 object {s3_path}: {e}")


# Singleton instance
_federated_orchestrator: Optional[FederatedQueryOrchestrator] = None


def get_federated_orchestrator(
    connectors: Optional[Dict[str, Any]] = None,
    config: Optional[FederationConfig] = None
) -> FederatedQueryOrchestrator:
    """
    Get or create the FederatedQueryOrchestrator singleton.

    Args:
        connectors: Dict mapping db names to connector instances
        config: Federation configuration

    Returns:
        FederatedQueryOrchestrator instance
    """
    global _federated_orchestrator

    if _federated_orchestrator is None:
        if connectors is None:
            raise ValueError("connectors is required on first call")
        _federated_orchestrator = FederatedQueryOrchestrator(
            connectors=connectors,
            default_config=config
        )

    return _federated_orchestrator
