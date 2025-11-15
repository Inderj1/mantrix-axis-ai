"""
Schema Extractor - Build-time pipeline for schema metadata collection.

This module extracts comprehensive schema information from multiple databases
and stores it for use in the build-time pipeline (Schema → RDF → Vector).

Key Features:
- Incremental schema updates (only changed tables)
- Schema versioning and change detection
- Multi-database support (BigQuery, PostgreSQL, MongoDB, Snowflake)
- Scheduled extraction jobs
- Cardinality estimation for query optimization

Author: Mantrix Axis AI
"""

import hashlib
import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
from src.db.bigquery import BigQueryClient
from src.core.cache_manager import CacheManager
from src.config import settings

logger = structlog.get_logger()


class SchemaChangeType(Enum):
    """Types of schema changes"""
    NEW_TABLE = "new_table"
    DROPPED_TABLE = "dropped_table"
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_TYPE_CHANGED = "column_type_changed"
    METADATA_CHANGED = "metadata_changed"
    NO_CHANGE = "no_change"


@dataclass
class TableSchemaSnapshot:
    """Complete snapshot of a table's schema"""
    table_name: str
    database_type: str  # bigquery, postgresql, mongodb, snowflake
    dataset: str
    project: str
    description: Optional[str]
    row_count: int
    size_bytes: int
    created_at: Optional[str]
    modified_at: Optional[str]
    columns: List[Dict[str, Any]]
    schema_hash: str
    snapshot_timestamp: str
    version: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableSchemaSnapshot':
        """Create from dictionary"""
        return cls(**data)


class SchemaExtractor:
    """
    Extracts and versions database schemas for build-time pipeline.

    Usage:
        extractor = SchemaExtractor(bq_client, cache_manager)
        changes = extractor.extract_and_compare()
        if changes:
            extractor.store_schemas()
    """

    def __init__(self, bq_client: BigQueryClient, cache_manager: Optional[CacheManager] = None):
        self.bq_client = bq_client
        self.cache_manager = cache_manager
        self.schema_cache_prefix = "schema_snapshot:"
        self.version_cache_prefix = "schema_version:"

    def _compute_schema_hash(self, schema: Dict[str, Any]) -> str:
        """
        Compute hash of schema for change detection.

        Includes: table name, columns (name, type), row count
        Excludes: timestamps, size (these change frequently)
        """
        hashable_parts = {
            'table_name': schema.get('table_name'),
            'columns': [
                {
                    'name': col['name'],
                    'type': col['type'],
                    'mode': col.get('mode', 'NULLABLE')
                }
                for col in schema.get('columns', [])
            ],
            'row_count_bucket': self._bucket_row_count(schema.get('row_count', 0))
        }

        # Sort for consistent hashing
        json_str = json.dumps(hashable_parts, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _bucket_row_count(self, row_count: int) -> str:
        """
        Bucket row counts to avoid hash changes from minor fluctuations.

        Buckets: 0, 1-100, 101-1K, 1K-10K, 10K-100K, 100K-1M, 1M-10M, 10M+
        """
        if row_count == 0:
            return "0"
        elif row_count <= 100:
            return "1-100"
        elif row_count <= 1000:
            return "101-1K"
        elif row_count <= 10000:
            return "1K-10K"
        elif row_count <= 100000:
            return "10K-100K"
        elif row_count <= 1000000:
            return "100K-1M"
        elif row_count <= 10000000:
            return "1M-10M"
        else:
            return "10M+"

    def _get_cached_snapshot(self, table_name: str) -> Optional[TableSchemaSnapshot]:
        """Retrieve cached schema snapshot for a table"""
        if not self.cache_manager:
            return None

        cache_key = f"{self.schema_cache_prefix}{self.bq_client.project_id}:{self.bq_client.dataset_id}:{table_name}"

        try:
            cached_data = self.cache_manager.get_cached_schema(cache_key)
            if cached_data:
                return TableSchemaSnapshot.from_dict(cached_data)
        except Exception as e:
            logger.warning(f"Failed to retrieve cached snapshot for {table_name}: {e}")

        return None

    def _store_snapshot(self, snapshot: TableSchemaSnapshot):
        """Store schema snapshot in cache"""
        if not self.cache_manager:
            return

        cache_key = f"{self.schema_cache_prefix}{snapshot.project}:{snapshot.dataset}:{snapshot.table_name}"

        try:
            # Store with 7-day TTL (refreshed on next extraction)
            self.cache_manager.set_cached_schema(cache_key, snapshot.to_dict(), ttl=7 * 24 * 60 * 60)
            logger.debug(f"Stored schema snapshot for {snapshot.table_name}")
        except Exception as e:
            logger.warning(f"Failed to store snapshot for {snapshot.table_name}: {e}")

    def _get_current_version(self, table_name: str) -> int:
        """Get current schema version for a table"""
        if not self.cache_manager:
            return 1

        version_key = f"{self.version_cache_prefix}{self.bq_client.project_id}:{self.bq_client.dataset_id}:{table_name}"

        try:
            version = self.cache_manager.redis.get(version_key)
            return int(version) if version else 1
        except Exception:
            return 1

    def _increment_version(self, table_name: str) -> int:
        """Increment and return new schema version"""
        if not self.cache_manager:
            return 1

        version_key = f"{self.version_cache_prefix}{self.bq_client.project_id}:{self.bq_client.dataset_id}:{table_name}"

        try:
            new_version = self.cache_manager.redis.incr(version_key)
            return new_version
        except Exception:
            return 1

    def extract_schema(self, table_name: str, force_refresh: bool = False) -> TableSchemaSnapshot:
        """
        Extract schema for a single table.

        Args:
            table_name: Table to extract
            force_refresh: Skip cache and re-extract

        Returns:
            TableSchemaSnapshot with current schema
        """
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_snapshot(table_name)
            if cached:
                # Check if cache is recent (< 1 hour old)
                snapshot_time = datetime.fromisoformat(cached.snapshot_timestamp)
                if datetime.now() - snapshot_time < timedelta(hours=1):
                    logger.debug(f"Using cached schema for {table_name}")
                    return cached

        # Extract fresh schema
        logger.info(f"Extracting schema for {table_name}")

        try:
            schema = self.bq_client.get_table_schema(table_name)

            # Compute schema hash
            schema_hash = self._compute_schema_hash(schema)

            # Get current version
            current_version = self._get_current_version(table_name)

            # Check if schema changed
            cached_snapshot = self._get_cached_snapshot(table_name)
            if cached_snapshot and cached_snapshot.schema_hash == schema_hash:
                # No change, return cached with updated timestamp
                cached_snapshot.snapshot_timestamp = datetime.now().isoformat()
                return cached_snapshot

            # Schema changed or new table - increment version
            if cached_snapshot and cached_snapshot.schema_hash != schema_hash:
                new_version = self._increment_version(table_name)
                logger.info(f"Schema changed for {table_name}, version {current_version} → {new_version}")
            else:
                new_version = current_version

            # Create snapshot
            snapshot = TableSchemaSnapshot(
                table_name=table_name,
                database_type="bigquery",
                dataset=schema.get('dataset', self.bq_client.dataset_id),
                project=schema.get('project', self.bq_client.project_id),
                description=schema.get('description'),
                row_count=schema.get('row_count', 0),
                size_bytes=0,  # TODO: Get from table metadata
                created_at=schema.get('created'),
                modified_at=schema.get('modified'),
                columns=schema.get('columns', []),
                schema_hash=schema_hash,
                snapshot_timestamp=datetime.now().isoformat(),
                version=new_version
            )

            # Store snapshot
            self._store_snapshot(snapshot)

            return snapshot

        except Exception as e:
            logger.error(f"Failed to extract schema for {table_name}: {e}")
            raise

    def extract_all_schemas(self, force_refresh: bool = False) -> List[TableSchemaSnapshot]:
        """
        Extract schemas for all tables in dataset.

        Args:
            force_refresh: Skip cache and re-extract all

        Returns:
            List of TableSchemaSnapshot objects
        """
        logger.info(f"Extracting all schemas from {self.bq_client.dataset_id}")

        try:
            # Get list of tables
            table_names = self.bq_client.list_tables()
            logger.info(f"Found {len(table_names)} tables")

            snapshots = []
            for table_name in table_names:
                try:
                    snapshot = self.extract_schema(table_name, force_refresh=force_refresh)
                    snapshots.append(snapshot)
                except Exception as e:
                    logger.error(f"Failed to extract {table_name}: {e}")
                    continue

            logger.info(f"Successfully extracted {len(snapshots)} schemas")
            return snapshots

        except Exception as e:
            logger.error(f"Failed to extract schemas: {e}")
            raise

    def detect_changes(self, current_snapshots: List[TableSchemaSnapshot]) -> Dict[str, List[Any]]:
        """
        Detect schema changes by comparing with cached snapshots.

        Args:
            current_snapshots: Currently extracted snapshots

        Returns:
            Dictionary of change_type → list of changes
        """
        changes = {
            SchemaChangeType.NEW_TABLE: [],
            SchemaChangeType.DROPPED_TABLE: [],
            SchemaChangeType.COLUMN_ADDED: [],
            SchemaChangeType.COLUMN_REMOVED: [],
            SchemaChangeType.COLUMN_TYPE_CHANGED: [],
            SchemaChangeType.METADATA_CHANGED: [],
            SchemaChangeType.NO_CHANGE: []
        }

        current_tables = {s.table_name for s in current_snapshots}

        # Check for new and modified tables
        for snapshot in current_snapshots:
            cached = self._get_cached_snapshot(snapshot.table_name)

            if not cached:
                # New table
                changes[SchemaChangeType.NEW_TABLE].append(snapshot.table_name)
                logger.info(f"New table detected: {snapshot.table_name}")

            elif cached.schema_hash != snapshot.schema_hash:
                # Schema changed - analyze details
                self._analyze_schema_diff(cached, snapshot, changes)

            else:
                # No change
                changes[SchemaChangeType.NO_CHANGE].append(snapshot.table_name)

        # Check for dropped tables (in cache but not in current)
        if self.cache_manager:
            # Get all cached table names
            pattern = f"{self.schema_cache_prefix}{self.bq_client.project_id}:{self.bq_client.dataset_id}:*"
            try:
                cached_keys = self.cache_manager.redis.keys(pattern)
                cached_tables = {
                    key.decode().split(':')[-1] if isinstance(key, bytes) else key.split(':')[-1]
                    for key in cached_keys
                }

                dropped = cached_tables - current_tables
                if dropped:
                    changes[SchemaChangeType.DROPPED_TABLE].extend(dropped)
                    for table in dropped:
                        logger.info(f"Dropped table detected: {table}")
            except Exception as e:
                logger.warning(f"Failed to check for dropped tables: {e}")

        return changes

    def _analyze_schema_diff(
        self,
        old_snapshot: TableSchemaSnapshot,
        new_snapshot: TableSchemaSnapshot,
        changes: Dict[SchemaChangeType, List]
    ):
        """Analyze detailed differences between two schema snapshots"""
        old_cols = {col['name']: col for col in old_snapshot.columns}
        new_cols = {col['name']: col for col in new_snapshot.columns}

        # Check for added columns
        added = set(new_cols.keys()) - set(old_cols.keys())
        if added:
            for col_name in added:
                changes[SchemaChangeType.COLUMN_ADDED].append({
                    'table': new_snapshot.table_name,
                    'column': col_name,
                    'type': new_cols[col_name]['type']
                })
                logger.info(f"Column added: {new_snapshot.table_name}.{col_name}")

        # Check for removed columns
        removed = set(old_cols.keys()) - set(new_cols.keys())
        if removed:
            for col_name in removed:
                changes[SchemaChangeType.COLUMN_REMOVED].append({
                    'table': new_snapshot.table_name,
                    'column': col_name
                })
                logger.info(f"Column removed: {new_snapshot.table_name}.{col_name}")

        # Check for type changes
        common_cols = set(old_cols.keys()) & set(new_cols.keys())
        for col_name in common_cols:
            if old_cols[col_name]['type'] != new_cols[col_name]['type']:
                changes[SchemaChangeType.COLUMN_TYPE_CHANGED].append({
                    'table': new_snapshot.table_name,
                    'column': col_name,
                    'old_type': old_cols[col_name]['type'],
                    'new_type': new_cols[col_name]['type']
                })
                logger.info(
                    f"Column type changed: {new_snapshot.table_name}.{col_name} "
                    f"{old_cols[col_name]['type']} → {new_cols[col_name]['type']}"
                )

        # Check for metadata changes (description, row count bucket)
        if (old_snapshot.description != new_snapshot.description or
            self._bucket_row_count(old_snapshot.row_count) != self._bucket_row_count(new_snapshot.row_count)):
            changes[SchemaChangeType.METADATA_CHANGED].append({
                'table': new_snapshot.table_name,
                'old_row_count': old_snapshot.row_count,
                'new_row_count': new_snapshot.row_count
            })

    def estimate_cardinality(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """
        Estimate cardinality (distinct count) for a column.

        Uses HyperLogLog for efficient estimation on large tables.

        Args:
            table_name: Table to analyze
            column_name: Column to estimate

        Returns:
            Dictionary with distinct_count, total_count, selectivity
        """
        logger.info(f"Estimating cardinality for {table_name}.{column_name}")

        try:
            # Use APPROX_COUNT_DISTINCT for efficiency on large tables
            query = f"""
            SELECT
                APPROX_COUNT_DISTINCT({column_name}) as distinct_count,
                COUNT(*) as total_count,
                COUNT({column_name}) as non_null_count
            FROM `{self.bq_client.project_id}.{self.bq_client.dataset_id}.{table_name}`
            """

            result = self.bq_client.execute_query(query, max_rows=1)
            row = result.get('rows', [{}])[0]

            distinct_count = row.get('distinct_count', 0)
            total_count = row.get('total_count', 0)
            non_null_count = row.get('non_null_count', 0)

            # Calculate selectivity (lower = more selective = better for indexing)
            selectivity = distinct_count / total_count if total_count > 0 else 0

            return {
                'table_name': table_name,
                'column_name': column_name,
                'distinct_count': distinct_count,
                'total_count': total_count,
                'non_null_count': non_null_count,
                'null_count': total_count - non_null_count,
                'selectivity': round(selectivity, 4),
                'is_high_cardinality': selectivity > 0.95,
                'is_low_cardinality': selectivity < 0.01,
                'estimated_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Cardinality estimation failed for {table_name}.{column_name}: {e}")
            return {
                'table_name': table_name,
                'column_name': column_name,
                'error': str(e)
            }

    def get_extraction_summary(self, snapshots: List[TableSchemaSnapshot], changes: Dict) -> Dict[str, Any]:
        """Generate summary report of schema extraction"""
        total_tables = len(snapshots)
        total_columns = sum(len(s.columns) for s in snapshots)
        total_rows = sum(s.row_count for s in snapshots)

        return {
            'extraction_timestamp': datetime.now().isoformat(),
            'database': {
                'project': self.bq_client.project_id,
                'dataset': self.bq_client.dataset_id,
                'type': 'bigquery'
            },
            'statistics': {
                'total_tables': total_tables,
                'total_columns': total_columns,
                'total_rows': total_rows,
                'avg_columns_per_table': round(total_columns / total_tables, 1) if total_tables > 0 else 0
            },
            'changes': {
                'new_tables': len(changes.get(SchemaChangeType.NEW_TABLE, [])),
                'dropped_tables': len(changes.get(SchemaChangeType.DROPPED_TABLE, [])),
                'columns_added': len(changes.get(SchemaChangeType.COLUMN_ADDED, [])),
                'columns_removed': len(changes.get(SchemaChangeType.COLUMN_REMOVED, [])),
                'type_changes': len(changes.get(SchemaChangeType.COLUMN_TYPE_CHANGED, [])),
                'metadata_changes': len(changes.get(SchemaChangeType.METADATA_CHANGED, [])),
                'unchanged_tables': len(changes.get(SchemaChangeType.NO_CHANGE, []))
            }
        }
