"""
S3 Federation Module for Large Cross-Database JOINs

Handles 10-100GB+ cross-database JOINs using S3 as an intermediary storage
and Redshift Spectrum for federated queries.

Architecture:
1. Stream source data to S3 in Parquet format (columnar, compressed)
2. Create external table in Redshift Spectrum pointing to S3
3. Execute JOIN using Redshift's query engine
4. Clean up temporary resources

This is the default federation strategy for AWS Marketplace deployment.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()

# Lazy imports for AWS SDK
boto3 = None
pyarrow = None
pq = None


def _ensure_imports():
    """Lazy import AWS SDK and PyArrow."""
    global boto3, pyarrow, pq
    if boto3 is None:
        try:
            import boto3 as _boto3
            import pyarrow as _pyarrow
            import pyarrow.parquet as _pq
            boto3 = _boto3
            pyarrow = _pyarrow
            pq = _pq
        except ImportError as e:
            raise ImportError(
                "S3 federation requires boto3 and pyarrow. "
                "Install with: pip install boto3 pyarrow"
            ) from e


class FederationStatus(Enum):
    """Status of a federation job."""
    PENDING = "pending"
    STREAMING = "streaming"
    CREATING_TABLE = "creating_table"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CLEANING_UP = "cleaning_up"


@dataclass
class FederationJob:
    """Represents a cross-database federation job."""
    job_id: str
    source_db: str
    target_db: str
    s3_prefix: str
    external_table: str
    status: FederationStatus
    created_at: datetime
    rows_streamed: int = 0
    bytes_written: int = 0
    error: Optional[str] = None


class S3Federation:
    """
    Handle large cross-database JOINs via S3 intermediary.

    Default strategy for AWS Marketplace customers using Redshift Spectrum.
    """

    def __init__(
        self,
        s3_bucket: str,
        s3_prefix: str = "federation",
        redshift_schema: str = "federation_temp",
        aws_region: str = "us-east-1",
        chunk_size: int = 100_000,  # Rows per Parquet file
        ttl_hours: int = 24  # Auto-cleanup after 24 hours
    ):
        """
        Initialize S3 Federation handler.

        Args:
            s3_bucket: S3 bucket for intermediate storage
            s3_prefix: Prefix within bucket for federation data
            redshift_schema: Redshift schema for external tables
            aws_region: AWS region for S3 and Redshift
            chunk_size: Number of rows per Parquet file
            ttl_hours: Hours before auto-cleanup of temp data
        """
        _ensure_imports()

        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.redshift_schema = redshift_schema
        self.aws_region = aws_region
        self.chunk_size = chunk_size
        self.ttl_hours = ttl_hours

        # AWS clients (lazy initialized)
        self._s3_client = None
        self._jobs: Dict[str, FederationJob] = {}

    @property
    def s3_client(self):
        """Get or create S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3', region_name=self.aws_region)
        return self._s3_client

    async def execute_large_join(
        self,
        source_connector,
        source_query: str,
        target_connector,
        target_table: str,
        join_condition: str,
        join_type: str = "INNER",
        select_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a large cross-database JOIN using S3 federation.

        Args:
            source_connector: Connector for source database
            source_query: Query to extract data from source (will be streamed to S3)
            target_connector: Connector for target database (must support Spectrum)
            target_table: Target table to join against
            join_condition: JOIN condition (e.g., "e.customer_id = t.customer_id")
            join_type: Type of JOIN (INNER, LEFT, RIGHT, FULL)
            select_columns: Columns to select (default: all)

        Returns:
            Dictionary with query results and metadata
        """
        job_id = str(uuid.uuid4())[:8]
        s3_job_prefix = f"{self.s3_prefix}/{job_id}"
        external_table = f"{self.redshift_schema}.temp_{job_id}"

        # Create job tracking
        job = FederationJob(
            job_id=job_id,
            source_db=type(source_connector).__name__,
            target_db=type(target_connector).__name__,
            s3_prefix=s3_job_prefix,
            external_table=external_table,
            status=FederationStatus.PENDING,
            created_at=datetime.utcnow()
        )
        self._jobs[job_id] = job

        try:
            # Step 1: Stream source data to S3 as Parquet
            logger.info(
                "Starting S3 federation",
                job_id=job_id,
                source_db=job.source_db,
                target_db=job.target_db
            )
            job.status = FederationStatus.STREAMING

            schema_info = await self._stream_to_s3(
                source_connector, source_query, s3_job_prefix, job
            )

            # Step 2: Create external table in Redshift Spectrum
            job.status = FederationStatus.CREATING_TABLE
            await self._create_spectrum_table(
                target_connector, external_table, s3_job_prefix, schema_info
            )

            # Step 3: Execute federated JOIN query
            job.status = FederationStatus.EXECUTING

            select_clause = ", ".join(select_columns) if select_columns else "*"
            join_sql = f"""
            SELECT {select_clause}
            FROM {target_table} t
            {join_type} JOIN {external_table} e
            ON {join_condition}
            """

            logger.info(
                "Executing federated JOIN",
                job_id=job_id,
                join_type=join_type
            )

            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: target_connector.execute_query(join_sql)
            )

            job.status = FederationStatus.COMPLETED

            return {
                **result,
                'federation_metadata': {
                    'job_id': job_id,
                    'rows_federated': job.rows_streamed,
                    'bytes_transferred': job.bytes_written,
                    's3_location': f"s3://{self.s3_bucket}/{s3_job_prefix}",
                    'external_table': external_table
                }
            }

        except Exception as e:
            job.status = FederationStatus.FAILED
            job.error = str(e)
            logger.error(
                "S3 federation failed",
                job_id=job_id,
                error=str(e)
            )
            raise

        finally:
            # Schedule cleanup (don't block on it)
            asyncio.create_task(
                self._cleanup_async(s3_job_prefix, target_connector, external_table, job)
            )

    async def _stream_to_s3(
        self,
        connector,
        query: str,
        s3_prefix: str,
        job: FederationJob
    ) -> Dict[str, Any]:
        """
        Stream query results to S3 as Parquet files.

        Returns schema information for external table creation.
        """
        # Execute query with streaming/pagination
        logger.info(f"Streaming data to S3: s3://{self.s3_bucket}/{s3_prefix}")

        # Get first batch to determine schema
        first_result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: connector.execute_query(query, limit=self.chunk_size)
        )

        rows = first_result.get('rows', [])
        if not rows:
            logger.warning("Source query returned no rows")
            return {'columns': []}

        # Infer schema from first row
        schema_info = self._infer_schema(rows[0])

        # Write first chunk
        chunk_num = 0
        await self._write_parquet_chunk(rows, s3_prefix, chunk_num, schema_info)
        job.rows_streamed += len(rows)

        # Stream remaining chunks if there are more
        offset = self.chunk_size
        while first_result.get('has_more', False) or len(rows) == self.chunk_size:
            chunk_num += 1
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda o=offset: connector.execute_query(
                    query, limit=self.chunk_size, offset=o
                )
            )
            rows = result.get('rows', [])
            if not rows:
                break

            await self._write_parquet_chunk(rows, s3_prefix, chunk_num, schema_info)
            job.rows_streamed += len(rows)
            offset += self.chunk_size

            logger.debug(
                f"Streamed {job.rows_streamed} rows",
                job_id=job.job_id
            )

        logger.info(
            f"Completed streaming {job.rows_streamed} rows to S3",
            job_id=job.job_id,
            chunks=chunk_num + 1
        )

        return schema_info

    def _infer_schema(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Infer PyArrow schema from a sample row."""
        fields = []
        for col_name, value in row.items():
            if isinstance(value, bool):
                pa_type = pyarrow.bool_()
            elif isinstance(value, int):
                pa_type = pyarrow.int64()
            elif isinstance(value, float):
                pa_type = pyarrow.float64()
            elif isinstance(value, datetime):
                pa_type = pyarrow.timestamp('us')
            else:
                pa_type = pyarrow.string()

            fields.append({
                'name': col_name,
                'type': pa_type,
                'sql_type': self._pa_type_to_redshift(pa_type)
            })

        return {'columns': fields}

    def _pa_type_to_redshift(self, pa_type) -> str:
        """Convert PyArrow type to Redshift SQL type."""
        type_str = str(pa_type)
        mapping = {
            'bool': 'BOOLEAN',
            'int64': 'BIGINT',
            'float64': 'DOUBLE PRECISION',
            'timestamp[us]': 'TIMESTAMP',
            'string': 'VARCHAR(65535)',
            'large_string': 'VARCHAR(65535)',
        }
        return mapping.get(type_str, 'VARCHAR(65535)')

    async def _write_parquet_chunk(
        self,
        rows: List[Dict[str, Any]],
        s3_prefix: str,
        chunk_num: int,
        schema_info: Dict[str, Any]
    ):
        """Write a chunk of rows as a Parquet file to S3."""
        # Build PyArrow table
        columns = {col['name']: [] for col in schema_info['columns']}
        for row in rows:
            for col in schema_info['columns']:
                columns[col['name']].append(row.get(col['name']))

        table = pyarrow.table(columns)

        # Write to buffer
        import io
        buffer = io.BytesIO()
        pq.write_table(table, buffer, compression='snappy')
        buffer.seek(0)

        # Upload to S3
        s3_key = f"{s3_prefix}/part_{chunk_num:05d}.parquet"
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=buffer.getvalue()
            )
        )

        logger.debug(f"Wrote chunk {chunk_num} to s3://{self.s3_bucket}/{s3_key}")

    async def _create_spectrum_table(
        self,
        connector,
        table_name: str,
        s3_prefix: str,
        schema_info: Dict[str, Any]
    ):
        """Create external table in Redshift Spectrum."""
        # Build column definitions
        column_defs = ", ".join([
            f"{col['name']} {col['sql_type']}"
            for col in schema_info['columns']
        ])

        # Create external schema if not exists
        create_schema_sql = f"""
        CREATE EXTERNAL SCHEMA IF NOT EXISTS {self.redshift_schema}
        FROM DATA CATALOG
        DATABASE 'federation_db'
        IAM_ROLE DEFAULT
        CREATE EXTERNAL DATABASE IF NOT EXISTS
        """

        # Create external table
        create_table_sql = f"""
        CREATE EXTERNAL TABLE {table_name} (
            {column_defs}
        )
        STORED AS PARQUET
        LOCATION 's3://{self.s3_bucket}/{s3_prefix}/'
        """

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: connector.execute_query(create_schema_sql)
            )
        except Exception as e:
            logger.warning(f"Schema creation warning (may already exist): {e}")

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: connector.execute_query(create_table_sql)
        )

        logger.info(f"Created external table: {table_name}")

    async def _cleanup_async(
        self,
        s3_prefix: str,
        connector,
        external_table: str,
        job: FederationJob
    ):
        """Cleanup S3 data and external table after job completion."""
        try:
            job.status = FederationStatus.CLEANING_UP

            # Drop external table
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: connector.execute_query(
                        f"DROP TABLE IF EXISTS {external_table}"
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to drop external table: {e}")

            # Delete S3 objects
            await self._delete_s3_prefix(s3_prefix)

            logger.info(f"Cleaned up federation job: {job.job_id}")

        except Exception as e:
            logger.error(f"Cleanup failed for job {job.job_id}: {e}")

    async def _delete_s3_prefix(self, s3_prefix: str):
        """Delete all objects under an S3 prefix."""
        paginator = self.s3_client.get_paginator('list_objects_v2')

        objects_to_delete = []
        async for page in self._async_paginate(paginator, self.s3_bucket, s3_prefix):
            for obj in page.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})

        if objects_to_delete:
            # Delete in batches of 1000 (S3 limit)
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i + 1000]
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda b=batch: self.s3_client.delete_objects(
                        Bucket=self.s3_bucket,
                        Delete={'Objects': b}
                    )
                )

    async def _async_paginate(self, paginator, bucket: str, prefix: str):
        """Async wrapper for S3 pagination."""
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            yield page

    def get_job_status(self, job_id: str) -> Optional[FederationJob]:
        """Get status of a federation job."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[FederationJob]:
        """List all federation jobs."""
        return list(self._jobs.values())

    async def cleanup_expired_jobs(self):
        """Clean up jobs older than TTL."""
        cutoff = datetime.utcnow() - timedelta(hours=self.ttl_hours)
        expired = [
            job for job in self._jobs.values()
            if job.created_at < cutoff and job.status == FederationStatus.COMPLETED
        ]

        for job in expired:
            try:
                await self._delete_s3_prefix(job.s3_prefix)
                del self._jobs[job.job_id]
                logger.info(f"Cleaned up expired job: {job.job_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup expired job {job.job_id}: {e}")


# Singleton instance for reuse
_federation_instance: Optional[S3Federation] = None


def get_s3_federation(
    s3_bucket: Optional[str] = None,
    **kwargs
) -> S3Federation:
    """
    Get or create the S3 Federation singleton.

    Args:
        s3_bucket: S3 bucket name (required on first call)
        **kwargs: Additional arguments for S3Federation

    Returns:
        S3Federation instance
    """
    global _federation_instance

    if _federation_instance is None:
        if s3_bucket is None:
            raise ValueError("s3_bucket is required for first initialization")
        _federation_instance = S3Federation(s3_bucket=s3_bucket, **kwargs)

    return _federation_instance
