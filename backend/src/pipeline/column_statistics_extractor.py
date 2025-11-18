"""
Column Statistics Extractor

Database-agnostic interface for extracting column-level statistics
(cardinality, selectivity, indexes) from different database systems.

This module provides optimization metadata for the RDF Builder to enable
intelligent query optimization decisions.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class ColumnStatistics:
    """Statistics for a single column."""
    column_name: str
    data_type: str
    cardinality: Optional[int] = None  # Number of distinct values
    total_rows: Optional[int] = None
    selectivity: Optional[float] = None  # cardinality / total_rows (0-1)
    has_index: bool = False
    is_unique: bool = False
    is_primary_key: bool = False
    is_foreign_key: bool = False
    null_count: Optional[int] = None
    null_fraction: Optional[float] = None
    avg_length: Optional[int] = None  # For string columns
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None


@dataclass
class TableStatistics:
    """Statistics for a table including all columns."""
    table_name: str
    database_type: str
    total_rows: int
    total_size_bytes: int
    column_stats: Dict[str, ColumnStatistics]
    indexes: List[Dict[str, Any]]
    last_analyzed: Optional[str] = None


class ColumnStatisticsExtractor(ABC):
    """
    Abstract base class for extracting column statistics.

    Each database connector implements this interface to provide
    optimization metadata in a standardized format.
    """

    def __init__(self, connector):
        """
        Initialize extractor with database connector.

        Args:
            connector: Database connector instance
        """
        self.connector = connector

    @abstractmethod
    def extract_table_statistics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        sample_size: int = 10000
    ) -> TableStatistics:
        """
        Extract complete statistics for a table.

        Args:
            table_name: Name of the table
            schema: Optional schema/dataset name
            sample_size: Number of rows to sample for statistics

        Returns:
            TableStatistics with all column metadata
        """
        pass

    @abstractmethod
    def extract_column_cardinality(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> Optional[int]:
        """
        Extract distinct value count for a column.

        Args:
            table_name: Name of the table
            column_name: Name of the column
            schema: Optional schema/dataset name

        Returns:
            Number of distinct values, or None if unavailable
        """
        pass

    @abstractmethod
    def extract_indexes(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract index information for a table.

        Args:
            table_name: Name of the table
            schema: Optional schema/dataset name

        Returns:
            List of index definitions
        """
        pass


class BigQueryStatisticsExtractor(ColumnStatisticsExtractor):
    """Statistics extractor for Google BigQuery."""

    def extract_table_statistics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        sample_size: int = 10000
    ) -> TableStatistics:
        """Extract statistics from BigQuery INFORMATION_SCHEMA."""
        logger.info(f"Extracting BigQuery statistics for {table_name}")

        dataset = schema or self.connector.dataset
        project = self.connector.project

        # Get table metadata
        table_query = f"""
        SELECT
            row_count,
            size_bytes
        FROM `{project}.{dataset}.INFORMATION_SCHEMA.TABLES`
        WHERE table_name = '{table_name}'
        """

        table_info = self.connector.execute_query(table_query)
        total_rows = table_info['rows'][0]['row_count'] if table_info['rows'] else 0
        size_bytes = table_info['rows'][0]['size_bytes'] if table_info['rows'] else 0

        # Get column information from INFORMATION_SCHEMA
        columns_query = f"""
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{table_name}'
        """

        columns_info = self.connector.execute_query(columns_query)

        column_stats = {}

        for col in columns_info['rows']:
            col_name = col['column_name']

            # Extract cardinality using APPROX_COUNT_DISTINCT
            cardinality_query = f"""
            SELECT
                APPROX_COUNT_DISTINCT({col_name}) as cardinality,
                COUNT(*) as total,
                COUNTIF({col_name} IS NULL) as null_count
            FROM `{project}.{dataset}.{table_name}`
            """

            try:
                card_result = self.connector.execute_query(cardinality_query)
                if card_result['rows']:
                    cardinality = card_result['rows'][0]['cardinality']
                    null_count = card_result['rows'][0]['null_count']
                    null_fraction = null_count / total_rows if total_rows > 0 else 0
                    selectivity = cardinality / total_rows if total_rows > 0 else 0
                else:
                    cardinality = None
                    null_count = None
                    null_fraction = None
                    selectivity = None
            except Exception as e:
                logger.warning(f"Failed to get cardinality for {col_name}: {e}")
                cardinality = None
                null_count = None
                null_fraction = None
                selectivity = None

            column_stats[col_name] = ColumnStatistics(
                column_name=col_name,
                data_type=col['data_type'],
                cardinality=cardinality,
                total_rows=total_rows,
                selectivity=selectivity,
                null_count=null_count,
                null_fraction=null_fraction,
                has_index=False,  # BigQuery doesn't have explicit indexes
                is_unique=(cardinality == total_rows) if cardinality else False
            )

        # Get indexes (BigQuery uses clustering/partitioning instead)
        indexes = self._extract_bigquery_clustering(project, dataset, table_name)

        return TableStatistics(
            table_name=table_name,
            database_type='bigquery',
            total_rows=total_rows,
            total_size_bytes=size_bytes,
            column_stats=column_stats,
            indexes=indexes
        )

    def extract_column_cardinality(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> Optional[int]:
        """Extract cardinality using APPROX_COUNT_DISTINCT."""
        dataset = schema or self.connector.dataset
        project = self.connector.project

        query = f"""
        SELECT APPROX_COUNT_DISTINCT({column_name}) as cardinality
        FROM `{project}.{dataset}.{table_name}`
        """

        try:
            result = self.connector.execute_query(query)
            return result['rows'][0]['cardinality'] if result['rows'] else None
        except Exception as e:
            logger.error(f"Failed to extract cardinality for {column_name}: {e}")
            return None

    def extract_indexes(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract clustering/partitioning info (BigQuery's index equivalent)."""
        dataset = schema or self.connector.dataset
        project = self.connector.project

        return self._extract_bigquery_clustering(project, dataset, table_name)

    def _extract_bigquery_clustering(
        self,
        project: str,
        dataset: str,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """Extract BigQuery clustering and partitioning information."""
        try:
            query = f"""
            SELECT
                clustering_ordinal_position,
                column_name
            FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table_name}'
              AND clustering_ordinal_position IS NOT NULL
            ORDER BY clustering_ordinal_position
            """

            result = self.connector.execute_query(query)

            if result['rows']:
                return [{
                    'type': 'clustering',
                    'columns': [row['column_name'] for row in result['rows']]
                }]

            return []
        except Exception as e:
            logger.warning(f"Failed to extract clustering info: {e}")
            return []


class PostgreSQLStatisticsExtractor(ColumnStatisticsExtractor):
    """Statistics extractor for PostgreSQL."""

    def extract_table_statistics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        sample_size: int = 10000
    ) -> TableStatistics:
        """Extract statistics from PostgreSQL pg_stats."""
        logger.info(f"Extracting PostgreSQL statistics for {table_name}")

        schema_name = schema or 'public'

        # Get table size and row count
        table_query = f"""
        SELECT
            schemaname,
            tablename,
            pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes,
            n_live_tup AS row_count
        FROM pg_stat_user_tables
        WHERE tablename = '{table_name}'
          AND schemaname = '{schema_name}'
        """

        table_info = self.connector.execute_query(table_query)
        total_rows = table_info[0]['row_count'] if table_info else 0
        size_bytes = table_info[0]['size_bytes'] if table_info else 0

        # Get column statistics from pg_stats
        stats_query = f"""
        SELECT
            attname as column_name,
            format_type(atttypid, atttypmod) as data_type,
            n_distinct,
            null_frac,
            avg_width
        FROM pg_stats s
        JOIN pg_attribute a ON s.attname = a.attname
        JOIN pg_class c ON a.attrelid = c.oid
        WHERE c.relname = '{table_name}'
          AND s.schemaname = '{schema_name}'
        """

        stats_result = self.connector.execute_query(stats_query)

        column_stats = {}

        for row in stats_result:
            col_name = row['column_name']
            n_distinct = row.get('n_distinct', 0)

            # PostgreSQL stores n_distinct as negative for percentage
            if n_distinct < 0:
                cardinality = int(abs(n_distinct) * total_rows)
            else:
                cardinality = int(n_distinct) if n_distinct > 0 else None

            selectivity = cardinality / total_rows if cardinality and total_rows > 0 else None
            null_fraction = row.get('null_frac', 0)

            column_stats[col_name] = ColumnStatistics(
                column_name=col_name,
                data_type=row['data_type'],
                cardinality=cardinality,
                total_rows=total_rows,
                selectivity=selectivity,
                null_fraction=null_fraction,
                avg_length=row.get('avg_width'),
                has_index=False  # Will be updated from index query
            )

        # Get index information
        indexes = self.extract_indexes(table_name, schema_name)

        # Mark columns with indexes
        indexed_columns = set()
        for idx in indexes:
            for col in idx.get('columns', []):
                indexed_columns.add(col)

        for col_name in indexed_columns:
            if col_name in column_stats:
                column_stats[col_name].has_index = True

        return TableStatistics(
            table_name=table_name,
            database_type='postgresql',
            total_rows=total_rows,
            total_size_bytes=size_bytes,
            column_stats=column_stats,
            indexes=indexes
        )

    def extract_column_cardinality(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> Optional[int]:
        """Extract cardinality from pg_stats."""
        schema_name = schema or 'public'

        query = f"""
        SELECT n_distinct
        FROM pg_stats
        WHERE tablename = '{table_name}'
          AND attname = '{column_name}'
          AND schemaname = '{schema_name}'
        """

        try:
            result = self.connector.execute_query(query)
            if result:
                n_distinct = result[0].get('n_distinct', 0)

                # Get table row count for percentage calculation
                if n_distinct < 0:
                    count_query = f"""
                    SELECT n_live_tup
                    FROM pg_stat_user_tables
                    WHERE tablename = '{table_name}'
                      AND schemaname = '{schema_name}'
                    """
                    count_result = self.connector.execute_query(count_query)
                    total_rows = count_result[0]['n_live_tup'] if count_result else 0
                    return int(abs(n_distinct) * total_rows)
                else:
                    return int(n_distinct) if n_distinct > 0 else None

            return None
        except Exception as e:
            logger.error(f"Failed to extract cardinality: {e}")
            return None

    def extract_indexes(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract index information from pg_indexes."""
        schema_name = schema or 'public'

        query = f"""
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = '{table_name}'
          AND schemaname = '{schema_name}'
        """

        try:
            result = self.connector.execute_query(query)

            indexes = []
            for row in result:
                # Parse column names from index definition
                # This is simplified - a full parser would be more robust
                indexdef = row['indexdef']
                columns = []

                # Extract columns from CREATE INDEX statement
                if '(' in indexdef and ')' in indexdef:
                    cols_part = indexdef[indexdef.index('(')+1:indexdef.rindex(')')]
                    columns = [c.strip() for c in cols_part.split(',')]

                indexes.append({
                    'name': row['indexname'],
                    'columns': columns,
                    'definition': indexdef,
                    'type': 'btree'  # Default for PostgreSQL
                })

            return indexes
        except Exception as e:
            logger.error(f"Failed to extract indexes: {e}")
            return []


class SnowflakeStatisticsExtractor(ColumnStatisticsExtractor):
    """Statistics extractor for Snowflake."""

    def extract_table_statistics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        sample_size: int = 10000
    ) -> TableStatistics:
        """Extract statistics from Snowflake."""
        logger.info(f"Extracting Snowflake statistics for {table_name}")

        schema_name = schema or 'PUBLIC'
        database_name = self.connector.database

        # Get table metadata
        table_query = f"""
        SELECT
            ROW_COUNT,
            BYTES
        FROM {database_name}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = '{table_name}'
          AND TABLE_SCHEMA = '{schema_name}'
        """

        table_info = self.connector.execute_query(table_query)
        total_rows = table_info[0]['ROW_COUNT'] if table_info else 0
        size_bytes = table_info[0]['BYTES'] if table_info else 0

        # Get column information
        columns_query = f"""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE
        FROM {database_name}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}'
          AND TABLE_SCHEMA = '{schema_name}'
        """

        columns_info = self.connector.execute_query(columns_query)

        column_stats = {}

        for col in columns_info:
            col_name = col['COLUMN_NAME']

            # Extract cardinality using APPROX_COUNT_DISTINCT
            cardinality_query = f"""
            SELECT
                APPROX_COUNT_DISTINCT({col_name}) as CARDINALITY,
                COUNT(*) as TOTAL,
                COUNT_IF({col_name} IS NULL) as NULL_COUNT
            FROM {database_name}.{schema_name}.{table_name}
            """

            try:
                card_result = self.connector.execute_query(cardinality_query)
                if card_result:
                    cardinality = card_result[0]['CARDINALITY']
                    null_count = card_result[0]['NULL_COUNT']
                    null_fraction = null_count / total_rows if total_rows > 0 else 0
                    selectivity = cardinality / total_rows if total_rows > 0 else 0
                else:
                    cardinality = None
                    null_count = None
                    null_fraction = None
                    selectivity = None
            except Exception as e:
                logger.warning(f"Failed to get cardinality for {col_name}: {e}")
                cardinality = None
                null_count = None
                null_fraction = None
                selectivity = None

            column_stats[col_name] = ColumnStatistics(
                column_name=col_name,
                data_type=col['DATA_TYPE'],
                cardinality=cardinality,
                total_rows=total_rows,
                selectivity=selectivity,
                null_count=null_count,
                null_fraction=null_fraction
            )

        # Get indexes (Snowflake uses clustering keys)
        indexes = self.extract_indexes(table_name, schema_name)

        return TableStatistics(
            table_name=table_name,
            database_type='snowflake',
            total_rows=total_rows,
            total_size_bytes=size_bytes,
            column_stats=column_stats,
            indexes=indexes
        )

    def extract_column_cardinality(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> Optional[int]:
        """Extract cardinality using APPROX_COUNT_DISTINCT."""
        schema_name = schema or 'PUBLIC'
        database_name = self.connector.database

        query = f"""
        SELECT APPROX_COUNT_DISTINCT({column_name}) as CARDINALITY
        FROM {database_name}.{schema_name}.{table_name}
        """

        try:
            result = self.connector.execute_query(query)
            return result[0]['CARDINALITY'] if result else None
        except Exception as e:
            logger.error(f"Failed to extract cardinality: {e}")
            return None

    def extract_indexes(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract clustering key information."""
        # Snowflake doesn't have traditional indexes, but clustering keys
        # We'd need to query SHOW TABLES or table metadata
        # This is a simplified implementation
        return []


class DatabricksStatisticsExtractor(ColumnStatisticsExtractor):
    """Statistics extractor for Databricks."""

    def extract_table_statistics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        sample_size: int = 10000
    ) -> TableStatistics:
        """Extract statistics from Databricks."""
        logger.info(f"Extracting Databricks statistics for {table_name}")

        catalog = self.connector.catalog
        schema_name = schema or 'default'

        # Use DESCRIBE EXTENDED to get table metadata
        describe_query = f"DESCRIBE EXTENDED {catalog}.{schema_name}.{table_name}"

        try:
            describe_result = self.connector.execute_query(describe_query)

            # Parse DESCRIBE output (format varies)
            total_rows = 0
            size_bytes = 0

            # Extract Statistics section from DESCRIBE output
            for row in describe_result:
                if 'Statistics' in str(row):
                    # Parse statistics
                    pass

        except Exception as e:
            logger.warning(f"Failed to get table metadata: {e}")
            total_rows = 0
            size_bytes = 0

        # Get column information
        columns_query = f"""
        SELECT
            col_name,
            data_type
        FROM {catalog}.information_schema.columns
        WHERE table_name = '{table_name}'
          AND table_schema = '{schema_name}'
        """

        try:
            columns_info = self.connector.execute_query(columns_query)
        except:
            # Fallback to DESCRIBE
            columns_info = []

        column_stats = {}

        for col in columns_info:
            col_name = col['col_name']

            # Extract cardinality
            cardinality_query = f"""
            SELECT
                APPROX_COUNT_DISTINCT({col_name}) as cardinality,
                COUNT(*) as total
            FROM {catalog}.{schema_name}.{table_name}
            """

            try:
                card_result = self.connector.execute_query(cardinality_query)
                if card_result:
                    cardinality = card_result[0]['cardinality']
                    total = card_result[0]['total']
                    selectivity = cardinality / total if total > 0 else 0
                else:
                    cardinality = None
                    selectivity = None
            except Exception as e:
                logger.warning(f"Failed to get cardinality for {col_name}: {e}")
                cardinality = None
                selectivity = None

            column_stats[col_name] = ColumnStatistics(
                column_name=col_name,
                data_type=col['data_type'],
                cardinality=cardinality,
                selectivity=selectivity
            )

        return TableStatistics(
            table_name=table_name,
            database_type='databricks',
            total_rows=total_rows,
            total_size_bytes=size_bytes,
            column_stats=column_stats,
            indexes=[]
        )

    def extract_column_cardinality(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> Optional[int]:
        """Extract cardinality using APPROX_COUNT_DISTINCT."""
        catalog = self.connector.catalog
        schema_name = schema or 'default'

        query = f"""
        SELECT APPROX_COUNT_DISTINCT({column_name}) as cardinality
        FROM {catalog}.{schema_name}.{table_name}
        """

        try:
            result = self.connector.execute_query(query)
            return result[0]['cardinality'] if result else None
        except Exception as e:
            logger.error(f"Failed to extract cardinality: {e}")
            return None

    def extract_indexes(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Databricks Delta tables don't have traditional indexes."""
        return []


class RedshiftStatisticsExtractor(ColumnStatisticsExtractor):
    """Statistics extractor for Amazon Redshift."""

    def extract_table_statistics(
        self,
        table_name: str,
        schema: Optional[str] = None,
        sample_size: int = 10000
    ) -> TableStatistics:
        """Extract statistics from Redshift system tables."""
        logger.info(f"Extracting Redshift statistics for {table_name}")

        schema_name = schema or 'public'

        # Get table metadata from SVV_TABLE_INFO
        table_query = f"""
        SELECT
            size,
            tbl_rows
        FROM svv_table_info
        WHERE "table" = '{table_name}'
          AND "schema" = '{schema_name}'
        """

        table_info = self.connector.execute_query(table_query)
        total_rows = table_info[0]['tbl_rows'] if table_info else 0
        size_mb = table_info[0]['size'] if table_info else 0
        size_bytes = size_mb * 1024 * 1024

        # Get column information
        columns_query = f"""
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
          AND table_schema = '{schema_name}'
        """

        columns_info = self.connector.execute_query(columns_query)

        column_stats = {}

        for col in columns_info:
            col_name = col['column_name']

            # Extract cardinality (Redshift uses APPROXIMATE COUNT)
            cardinality_query = f"""
            SELECT
                APPROXIMATE COUNT(DISTINCT {col_name}) as cardinality
            FROM {schema_name}.{table_name}
            """

            try:
                card_result = self.connector.execute_query(cardinality_query)
                if card_result:
                    cardinality = card_result[0]['cardinality']
                    selectivity = cardinality / total_rows if total_rows > 0 else 0
                else:
                    cardinality = None
                    selectivity = None
            except Exception as e:
                logger.warning(f"Failed to get cardinality for {col_name}: {e}")
                cardinality = None
                selectivity = None

            column_stats[col_name] = ColumnStatistics(
                column_name=col_name,
                data_type=col['data_type'],
                cardinality=cardinality,
                total_rows=total_rows,
                selectivity=selectivity
            )

        # Get indexes (distkey, sortkey)
        indexes = self.extract_indexes(table_name, schema_name)

        return TableStatistics(
            table_name=table_name,
            database_type='redshift',
            total_rows=total_rows,
            total_size_bytes=size_bytes,
            column_stats=column_stats,
            indexes=indexes
        )

    def extract_column_cardinality(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> Optional[int]:
        """Extract cardinality using APPROXIMATE COUNT."""
        schema_name = schema or 'public'

        query = f"""
        SELECT APPROXIMATE COUNT(DISTINCT {column_name}) as cardinality
        FROM {schema_name}.{table_name}
        """

        try:
            result = self.connector.execute_query(query)
            return result[0]['cardinality'] if result else None
        except Exception as e:
            logger.error(f"Failed to extract cardinality: {e}")
            return None

    def extract_indexes(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract Redshift distkey and sortkey information."""
        schema_name = schema or 'public'

        # Query for distribution and sort keys
        query = f"""
        SELECT
            "column",
            distkey,
            sortkey
        FROM pg_table_def
        WHERE tablename = '{table_name}'
          AND schemaname = '{schema_name}'
        """

        try:
            result = self.connector.execute_query(query)

            indexes = []
            distkey_cols = []
            sortkey_cols = []

            for row in result:
                if row.get('distkey'):
                    distkey_cols.append(row['column'])
                if row.get('sortkey', 0) > 0:
                    sortkey_cols.append((row['sortkey'], row['column']))

            if distkey_cols:
                indexes.append({
                    'type': 'distkey',
                    'columns': distkey_cols
                })

            if sortkey_cols:
                # Sort by sortkey position
                sortkey_cols.sort()
                indexes.append({
                    'type': 'sortkey',
                    'columns': [col for _, col in sortkey_cols]
                })

            return indexes
        except Exception as e:
            logger.error(f"Failed to extract indexes: {e}")
            return []


def get_statistics_extractor(connector) -> ColumnStatisticsExtractor:
    """
    Factory function to get the appropriate statistics extractor for a connector.

    Args:
        connector: Database connector instance

    Returns:
        ColumnStatisticsExtractor for the connector's database type
    """
    from src.db.connectors.bigquery_connector import BigQueryConnector
    from src.db.connectors.postgresql_connector import PostgreSQLConnector
    from src.db.connectors.snowflake_connector import SnowflakeConnector
    from src.db.connectors.databricks_connector import DatabricksConnector
    from src.db.connectors.redshift_connector import RedshiftConnector

    extractor_map = {
        BigQueryConnector: BigQueryStatisticsExtractor,
        PostgreSQLConnector: PostgreSQLStatisticsExtractor,
        SnowflakeConnector: SnowflakeStatisticsExtractor,
        DatabricksConnector: DatabricksStatisticsExtractor,
        RedshiftConnector: RedshiftStatisticsExtractor,
    }

    for connector_class, extractor_class in extractor_map.items():
        if isinstance(connector, connector_class):
            return extractor_class(connector)

    # Default fallback - log warning
    logger.warning(
        f"No statistics extractor found for connector type {type(connector).__name__}. "
        f"Optimization metadata will be limited."
    )

    # Return a no-op extractor
    class NoOpExtractor(ColumnStatisticsExtractor):
        def extract_table_statistics(self, table_name, schema=None, sample_size=10000):
            return TableStatistics(
                table_name=table_name,
                database_type='unknown',
                total_rows=0,
                total_size_bytes=0,
                column_stats={},
                indexes=[]
            )

        def extract_column_cardinality(self, table_name, column_name, schema=None):
            return None

        def extract_indexes(self, table_name, schema=None):
            return []

    return NoOpExtractor(connector)
