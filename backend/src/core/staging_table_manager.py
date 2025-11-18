"""
Staging Table Manager

Manages temporary staging tables for cross-database queries with large datasets.
When datasets are too large for in-memory JOINs (>100MB), this manager:
1. Copies smaller dataset to target database as a staging table
2. Executes JOIN natively in the target database
3. Cleans up staging tables afterward

This approach is significantly faster than in-memory JOINs for large datasets
while avoiding the complexity of distributed query execution.

Performance Profile:
- In-memory JOIN:  Good for <100MB per table
- Staging tables:  Good for 100MB - 10GB per table
- Cloud storage:   Good for >10GB per table
"""
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import structlog

logger = structlog.get_logger()


@dataclass
class StagingTableConfig:
    """Configuration for a staging table."""
    source_database: str
    target_database: str
    source_query: str
    staging_table_name: str
    estimated_size_mb: float = 0.0
    ttl_seconds: int = 3600  # 1 hour default
    created_at: Optional[datetime] = None

    # Metadata
    row_count: int = 0
    actual_size_mb: float = 0.0
    creation_time_seconds: float = 0.0


@dataclass
class StagingTableResult:
    """Result of staging table operation."""
    success: bool
    staging_table: Optional[StagingTableConfig] = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    rows_staged: int = 0
    data_transferred_mb: float = 0.0


class StagingTableManager:
    """
    Manage temporary staging tables for cross-database queries.

    Use Cases:
    1. Large cross-database JOINs (100MB - 10GB)
    2. Multiple queries against the same remote dataset
    3. Complex aggregations on remote data

    Strategy:
    1. Fetch data from source database
    2. Create temporary table in target database
    3. Execute query natively in target database
    4. Clean up staging table after use
    """

    # Size thresholds for strategy selection
    IN_MEMORY_THRESHOLD_MB = 100  # Use in-memory for < 100MB
    STAGING_TABLE_MAX_MB = 10_000  # Use cloud storage for > 10GB

    def __init__(self, connector_factory):
        """
        Initialize staging table manager.

        Args:
            connector_factory: Factory for creating database connectors
        """
        self.factory = connector_factory
        self._active_staging_tables: Dict[str, StagingTableConfig] = {}
        logger.info("StagingTableManager initialized")

    async def create_staging_table(
        self,
        source_db: str,
        source_query: str,
        target_db: str,
        table_name: Optional[str] = None,
        source_config: Optional[Dict[str, Any]] = None,
        target_config: Optional[Dict[str, Any]] = None
    ) -> StagingTableResult:
        """
        Create staging table in target database from source query.

        Args:
            source_db: Source database type
            source_query: Query to fetch data from source
            target_db: Target database type
            table_name: Optional custom table name (auto-generated if not provided)
            source_config: Optional source database config
            target_config: Optional target database config

        Returns:
            StagingTableResult with staging table info
        """
        start_time = datetime.now()

        # Generate staging table name
        if not table_name:
            table_name = self._generate_staging_table_name(source_db, target_db)

        logger.info(
            "Creating staging table",
            source_db=source_db,
            target_db=target_db,
            table_name=table_name
        )

        try:
            # Step 1: Fetch data from source
            source_connector = self.factory.create_connector(
                source_db,
                config=source_config or {}
            )

            logger.debug("Fetching data from source database", source_db=source_db)
            fetch_start = datetime.now()

            # Execute query on source
            source_data = await asyncio.to_thread(
                source_connector.execute_query,
                source_query
            )

            # Convert to DataFrame
            if isinstance(source_data, dict) and 'rows' in source_data:
                df = pd.DataFrame(source_data['rows'])
            elif isinstance(source_data, list):
                df = pd.DataFrame(source_data)
            elif isinstance(source_data, pd.DataFrame):
                df = source_data
            else:
                raise ValueError(f"Unexpected source data type: {type(source_data)}")

            fetch_time = (datetime.now() - fetch_start).total_seconds()
            data_size_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

            logger.info(
                "Data fetched from source",
                rows=len(df),
                size_mb=f"{data_size_mb:.2f}",
                fetch_time_seconds=f"{fetch_time:.2f}"
            )

            # Check if dataset is too large for staging
            if data_size_mb > self.STAGING_TABLE_MAX_MB:
                return StagingTableResult(
                    success=False,
                    error=f"Dataset too large for staging ({data_size_mb:.2f}MB). Use cloud storage strategy instead."
                )

            # Step 2: Create staging table in target database
            target_connector = self.factory.create_connector(
                target_db,
                config=target_config or {}
            )

            logger.debug("Creating staging table in target database", target_db=target_db)
            create_start = datetime.now()

            # Generate CREATE TABLE SQL
            create_sql = self._generate_create_table_sql(
                table_name,
                df,
                target_db
            )

            # Create table
            await asyncio.to_thread(
                target_connector.execute_query,
                create_sql
            )

            # Step 3: Insert data into staging table
            logger.debug("Inserting data into staging table", rows=len(df))

            # Insert data (batch insert for efficiency)
            await self._insert_dataframe(
                target_connector,
                table_name,
                df,
                target_db
            )

            create_time = (datetime.now() - create_start).total_seconds()

            # Create staging table config
            config = StagingTableConfig(
                source_database=source_db,
                target_database=target_db,
                source_query=source_query,
                staging_table_name=table_name,
                estimated_size_mb=data_size_mb,
                created_at=datetime.now(),
                row_count=len(df),
                actual_size_mb=data_size_mb,
                creation_time_seconds=create_time
            )

            # Track active staging table
            self._active_staging_tables[table_name] = config

            total_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                "Staging table created successfully",
                table_name=table_name,
                rows=len(df),
                size_mb=f"{data_size_mb:.2f}",
                total_time_seconds=f"{total_time:.2f}"
            )

            return StagingTableResult(
                success=True,
                staging_table=config,
                execution_time_seconds=total_time,
                rows_staged=len(df),
                data_transferred_mb=data_size_mb
            )

        except Exception as e:
            error_msg = f"Failed to create staging table: {str(e)}"
            logger.error(
                "Staging table creation failed",
                error=str(e),
                source_db=source_db,
                target_db=target_db
            )

            return StagingTableResult(
                success=False,
                error=error_msg,
                execution_time_seconds=(datetime.now() - start_time).total_seconds()
            )

    async def execute_with_staging(
        self,
        source_db: str,
        source_query: str,
        target_db: str,
        target_query_template: str,
        source_config: Optional[Dict[str, Any]] = None,
        target_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[pd.DataFrame, StagingTableConfig]:
        """
        Execute cross-database query using staging table.

        Args:
            source_db: Source database type
            source_query: Query to fetch data from source
            target_db: Target database type
            target_query_template: Query template with {staging_table} placeholder
            source_config: Optional source database config
            target_config: Optional target database config

        Returns:
            Tuple of (result DataFrame, staging table config)

        Example:
            ```python
            result, staging = await manager.execute_with_staging(
                source_db='postgresql',
                source_query='SELECT * FROM customers WHERE active = true',
                target_db='bigquery',
                target_query_template='''
                    SELECT c.*, o.total_amount
                    FROM {staging_table} c
                    JOIN orders o ON c.customer_id = o.customer_id
                '''
            )
            ```
        """
        # Create staging table
        staging_result = await self.create_staging_table(
            source_db=source_db,
            source_query=source_query,
            target_db=target_db,
            source_config=source_config,
            target_config=target_config
        )

        if not staging_result.success:
            raise RuntimeError(staging_result.error)

        staging_table = staging_result.staging_table

        try:
            # Execute query in target database
            target_connector = self.factory.create_connector(
                target_db,
                config=target_config or {}
            )

            # Replace {staging_table} placeholder
            final_query = target_query_template.format(
                staging_table=staging_table.staging_table_name
            )

            logger.info(
                "Executing query with staging table",
                target_db=target_db,
                staging_table=staging_table.staging_table_name
            )

            # Execute query
            result_data = await asyncio.to_thread(
                target_connector.execute_query,
                final_query
            )

            # Convert to DataFrame
            if isinstance(result_data, dict) and 'rows' in result_data:
                result_df = pd.DataFrame(result_data['rows'])
            elif isinstance(result_data, list):
                result_df = pd.DataFrame(result_data)
            elif isinstance(result_data, pd.DataFrame):
                result_df = result_data
            else:
                result_df = pd.DataFrame()

            logger.info(
                "Query executed successfully with staging table",
                rows_returned=len(result_df)
            )

            return result_df, staging_table

        except Exception as e:
            logger.error("Query execution with staging table failed", error=str(e))
            raise

    async def cleanup_staging_table(
        self,
        staging_table: StagingTableConfig,
        target_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Clean up (drop) a staging table.

        Args:
            staging_table: Staging table configuration
            target_config: Optional target database config

        Returns:
            True if cleanup successful, False otherwise
        """
        logger.info(
            "Cleaning up staging table",
            table_name=staging_table.staging_table_name,
            target_db=staging_table.target_database
        )

        try:
            target_connector = self.factory.create_connector(
                staging_table.target_database,
                config=target_config or {}
            )

            # Drop table
            drop_sql = f"DROP TABLE IF EXISTS {staging_table.staging_table_name}"
            await asyncio.to_thread(
                target_connector.execute_query,
                drop_sql
            )

            # Remove from active staging tables
            if staging_table.staging_table_name in self._active_staging_tables:
                del self._active_staging_tables[staging_table.staging_table_name]

            logger.info("Staging table cleaned up successfully")
            return True

        except Exception as e:
            logger.error("Failed to cleanup staging table", error=str(e))
            return False

    async def cleanup_all_staging_tables(
        self,
        target_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """Clean up all active staging tables."""
        logger.info(f"Cleaning up {len(self._active_staging_tables)} staging tables")

        configs = target_configs or {}

        for table_name, staging_table in list(self._active_staging_tables.items()):
            await self.cleanup_staging_table(
                staging_table,
                configs.get(staging_table.target_database)
            )

    def _generate_staging_table_name(
        self,
        source_db: str,
        target_db: str
    ) -> str:
        """Generate unique staging table name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"staging_{source_db}_to_{target_db}_{timestamp}"

    def _generate_create_table_sql(
        self,
        table_name: str,
        df: pd.DataFrame,
        target_db: str
    ) -> str:
        """
        Generate CREATE TABLE SQL for target database.

        This is simplified - production version would need more sophisticated
        type mapping for each database dialect.
        """
        # Map pandas dtypes to SQL types (simplified)
        type_map = {
            'int64': 'BIGINT',
            'float64': 'FLOAT',
            'object': 'TEXT',
            'bool': 'BOOLEAN',
            'datetime64[ns]': 'TIMESTAMP'
        }

        columns = []
        for col_name, dtype in df.dtypes.items():
            sql_type = type_map.get(str(dtype), 'TEXT')
            columns.append(f"{col_name} {sql_type}")

        columns_sql = ",\n    ".join(columns)

        return f"CREATE TABLE {table_name} (\n    {columns_sql}\n)"

    async def _insert_dataframe(
        self,
        connector: Any,
        table_name: str,
        df: pd.DataFrame,
        target_db: str
    ):
        """
        Insert DataFrame into staging table.

        This is a simplified implementation. Production version would use:
        - Batch inserts for efficiency
        - Database-specific bulk loading (COPY, LOAD DATA, etc.)
        - Parallel insertion for large datasets
        """
        # For now, convert to SQL INSERT statements
        # In production, use database-specific bulk loading

        # Simple batch insert (process in chunks)
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]

            # Generate INSERT statement
            values = []
            for _, row in batch.iterrows():
                row_values = []
                for val in row:
                    if pd.isna(val):
                        row_values.append('NULL')
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped = val.replace("'", "''")
                        row_values.append(f"'{escaped}'")
                    else:
                        row_values.append(str(val))
                values.append(f"({', '.join(row_values)})")

            columns = ', '.join(df.columns)
            values_sql = ',\n    '.join(values)
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES\n    {values_sql}"

            await asyncio.to_thread(
                connector.execute_query,
                insert_sql
            )

            logger.debug(f"Inserted batch {i//batch_size + 1}, rows {i} to {min(i+batch_size, len(df))}")

    def should_use_staging(
        self,
        estimated_size_mb: float
    ) -> bool:
        """
        Determine if staging table strategy should be used.

        Args:
            estimated_size_mb: Estimated dataset size in MB

        Returns:
            True if staging table is recommended, False otherwise
        """
        return (
            self.IN_MEMORY_THRESHOLD_MB <= estimated_size_mb <= self.STAGING_TABLE_MAX_MB
        )
