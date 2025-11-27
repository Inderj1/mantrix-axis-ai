"""
Pluggable Federation Factory

Provides a unified interface for cross-database query federation with
pluggable backends. Supports different federation strategies based on
customer deployment:

- Redshift Spectrum (default for AWS Marketplace)
- BigQuery Omni (for GCP/BigQuery customers - BYOW)
- Snowflake External Stages (for Snowflake customers - BYOW)
- Pandas (fallback for small datasets <1GB)

The factory automatically selects the appropriate strategy based on
the target database or customer configuration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class FederationStrategy(str, Enum):
    """Available federation strategies."""
    REDSHIFT = "redshift"      # Default for AWS Marketplace
    BIGQUERY = "bigquery"      # Enterprise BYOW
    SNOWFLAKE = "snowflake"    # Enterprise BYOW
    PANDAS = "pandas"          # Fallback for small data


@dataclass
class FederationConfig:
    """Configuration for a federation strategy."""
    strategy: FederationStrategy
    # Common settings
    temp_storage_path: str = ""
    max_memory_gb: float = 10.0
    chunk_size: int = 100_000

    # AWS/Redshift settings
    s3_bucket: Optional[str] = None
    s3_prefix: str = "federation"
    redshift_schema: str = "federation_temp"
    aws_region: str = "us-east-1"

    # GCP/BigQuery settings
    gcs_bucket: Optional[str] = None
    gcs_prefix: str = "federation"
    bigquery_dataset: str = "federation_temp"
    gcp_project: Optional[str] = None

    # Snowflake settings
    snowflake_stage: Optional[str] = None
    snowflake_schema: str = "FEDERATION_TEMP"


class BaseFederationStrategy(ABC):
    """
    Abstract base class for federation strategies.

    All federation backends must implement this interface.
    """

    def __init__(self, config: FederationConfig):
        self.config = config

    @abstractmethod
    async def execute_federated_join(
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
        Execute a cross-database JOIN operation.

        Args:
            source_connector: Connector for source database
            source_query: Query to extract data from source
            target_connector: Connector for target database
            target_table: Target table to join against
            join_condition: JOIN condition
            join_type: Type of JOIN (INNER, LEFT, RIGHT, FULL)
            select_columns: Columns to select

        Returns:
            Dictionary with query results and federation metadata
        """
        pass

    @abstractmethod
    async def estimate_cost(
        self,
        source_query: str,
        estimated_rows: int
    ) -> Dict[str, Any]:
        """
        Estimate the cost/resources for a federation operation.

        Returns:
            Dictionary with cost estimates
        """
        pass

    @abstractmethod
    async def cleanup(self, job_id: str):
        """Clean up resources for a specific job."""
        pass


class RedshiftSpectrumStrategy(BaseFederationStrategy):
    """
    Federation strategy using S3 and Redshift Spectrum.

    Default for AWS Marketplace customers.
    """

    def __init__(self, config: FederationConfig):
        super().__init__(config)
        self._federation = None

    @property
    def federation(self):
        """Lazy load S3Federation."""
        if self._federation is None:
            from .s3_federation import S3Federation
            if not self.config.s3_bucket:
                raise ValueError("s3_bucket is required for Redshift Spectrum strategy")
            self._federation = S3Federation(
                s3_bucket=self.config.s3_bucket,
                s3_prefix=self.config.s3_prefix,
                redshift_schema=self.config.redshift_schema,
                aws_region=self.config.aws_region,
                chunk_size=self.config.chunk_size
            )
        return self._federation

    async def execute_federated_join(
        self,
        source_connector,
        source_query: str,
        target_connector,
        target_table: str,
        join_condition: str,
        join_type: str = "INNER",
        select_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute JOIN using S3 + Redshift Spectrum."""
        return await self.federation.execute_large_join(
            source_connector=source_connector,
            source_query=source_query,
            target_connector=target_connector,
            target_table=target_table,
            join_condition=join_condition,
            join_type=join_type,
            select_columns=select_columns
        )

    async def estimate_cost(
        self,
        source_query: str,
        estimated_rows: int
    ) -> Dict[str, Any]:
        """Estimate S3 storage and Spectrum query costs."""
        # Rough estimates based on AWS pricing
        estimated_size_gb = estimated_rows * 500 / (1024 ** 3)  # ~500 bytes/row avg
        s3_storage_cost = estimated_size_gb * 0.023  # $0.023/GB-month
        spectrum_scan_cost = estimated_size_gb * 5.0  # $5/TB scanned

        return {
            'strategy': 'redshift_spectrum',
            'estimated_rows': estimated_rows,
            'estimated_size_gb': estimated_size_gb,
            's3_storage_cost_usd': s3_storage_cost,
            'spectrum_scan_cost_usd': spectrum_scan_cost,
            'total_estimated_cost_usd': s3_storage_cost + spectrum_scan_cost
        }

    async def cleanup(self, job_id: str):
        """Cleanup is handled automatically by S3Federation."""
        job = self.federation.get_job_status(job_id)
        if job:
            await self.federation._cleanup_async(
                job.s3_prefix, None, job.external_table, job
            )


class BigQueryOmniStrategy(BaseFederationStrategy):
    """
    Federation strategy using GCS and BigQuery Omni.

    For enterprise customers bringing their own GCP/BigQuery warehouse.
    """

    def __init__(self, config: FederationConfig):
        super().__init__(config)
        self._gcs_client = None

    async def execute_federated_join(
        self,
        source_connector,
        source_query: str,
        target_connector,
        target_table: str,
        join_condition: str,
        join_type: str = "INNER",
        select_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute JOIN using GCS + BigQuery external tables."""
        # TODO: Implement BigQuery Omni federation
        # This would follow similar pattern to S3Federation:
        # 1. Stream data to GCS as Parquet
        # 2. Create external table in BigQuery
        # 3. Execute federated JOIN
        # 4. Cleanup

        raise NotImplementedError(
            "BigQuery Omni federation not yet implemented. "
            "Please use Redshift Spectrum strategy or contact support."
        )

    async def estimate_cost(
        self,
        source_query: str,
        estimated_rows: int
    ) -> Dict[str, Any]:
        """Estimate GCS storage and BigQuery query costs."""
        estimated_size_gb = estimated_rows * 500 / (1024 ** 3)
        gcs_storage_cost = estimated_size_gb * 0.020  # $0.020/GB-month
        bq_scan_cost = estimated_size_gb * 5.0  # $5/TB scanned

        return {
            'strategy': 'bigquery_omni',
            'estimated_rows': estimated_rows,
            'estimated_size_gb': estimated_size_gb,
            'gcs_storage_cost_usd': gcs_storage_cost,
            'bq_scan_cost_usd': bq_scan_cost,
            'total_estimated_cost_usd': gcs_storage_cost + bq_scan_cost
        }

    async def cleanup(self, job_id: str):
        """Cleanup GCS and BigQuery external table."""
        pass  # TODO: Implement


class SnowflakeExternalStageStrategy(BaseFederationStrategy):
    """
    Federation strategy using Snowflake External Stages.

    For enterprise customers bringing their own Snowflake warehouse.
    """

    def __init__(self, config: FederationConfig):
        super().__init__(config)

    async def execute_federated_join(
        self,
        source_connector,
        source_query: str,
        target_connector,
        target_table: str,
        join_condition: str,
        join_type: str = "INNER",
        select_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute JOIN using Snowflake external stages."""
        # TODO: Implement Snowflake external stage federation
        # This would:
        # 1. Stream data to S3/Azure/GCS stage
        # 2. Create external table in Snowflake
        # 3. Execute federated JOIN
        # 4. Cleanup

        raise NotImplementedError(
            "Snowflake external stage federation not yet implemented. "
            "Please use Redshift Spectrum strategy or contact support."
        )

    async def estimate_cost(
        self,
        source_query: str,
        estimated_rows: int
    ) -> Dict[str, Any]:
        """Estimate Snowflake compute costs."""
        estimated_size_gb = estimated_rows * 500 / (1024 ** 3)
        # Snowflake charges by compute time, harder to estimate
        estimated_compute_credits = estimated_size_gb * 0.1  # rough estimate

        return {
            'strategy': 'snowflake_external_stage',
            'estimated_rows': estimated_rows,
            'estimated_size_gb': estimated_size_gb,
            'estimated_compute_credits': estimated_compute_credits,
            'note': 'Actual cost depends on warehouse size and query complexity'
        }

    async def cleanup(self, job_id: str):
        """Cleanup Snowflake stage and external table."""
        pass  # TODO: Implement


class PandasStrategy(BaseFederationStrategy):
    """
    Fallback federation strategy using Pandas in-memory JOIN.

    Only suitable for small datasets (<1GB).
    """

    def __init__(self, config: FederationConfig):
        super().__init__(config)
        self.max_memory_gb = config.max_memory_gb

    async def execute_federated_join(
        self,
        source_connector,
        source_query: str,
        target_connector,
        target_table: str,
        join_condition: str,
        join_type: str = "INNER",
        select_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute JOIN using Pandas in-memory."""
        import asyncio

        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Pandas strategy")

        # Execute source query
        source_result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: source_connector.execute_query(source_query)
        )
        source_df = pd.DataFrame(source_result.get('rows', []))

        # Check memory limit
        memory_usage_gb = source_df.memory_usage(deep=True).sum() / (1024 ** 3)
        if memory_usage_gb > self.max_memory_gb:
            raise MemoryError(
                f"Source data ({memory_usage_gb:.2f}GB) exceeds memory limit "
                f"({self.max_memory_gb}GB). Use a larger federation strategy."
            )

        # Execute target query
        target_query = f"SELECT * FROM {target_table}"
        target_result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: target_connector.execute_query(target_query)
        )
        target_df = pd.DataFrame(target_result.get('rows', []))

        # Parse join condition to get join columns
        # Simple parsing for "a.col = b.col" format
        join_parts = join_condition.replace(' ', '').split('=')
        if len(join_parts) != 2:
            raise ValueError(f"Cannot parse join condition: {join_condition}")

        left_col = join_parts[0].split('.')[-1]
        right_col = join_parts[1].split('.')[-1]

        # Map join type
        how_map = {
            'INNER': 'inner',
            'LEFT': 'left',
            'RIGHT': 'right',
            'FULL': 'outer'
        }
        how = how_map.get(join_type.upper(), 'inner')

        # Execute join
        result_df = pd.merge(
            source_df, target_df,
            left_on=left_col, right_on=right_col,
            how=how,
            suffixes=('_source', '_target')
        )

        # Select columns if specified
        if select_columns:
            available_cols = [c for c in select_columns if c in result_df.columns]
            result_df = result_df[available_cols]

        rows = result_df.to_dict('records')

        return {
            'rows': rows,
            'total_rows': len(rows),
            'fetched_rows': len(rows),
            'has_more': False,
            'federation_metadata': {
                'strategy': 'pandas',
                'source_rows': len(source_df),
                'target_rows': len(target_df),
                'memory_usage_gb': memory_usage_gb
            }
        }

    async def estimate_cost(
        self,
        source_query: str,
        estimated_rows: int
    ) -> Dict[str, Any]:
        """Estimate memory requirements."""
        estimated_size_gb = estimated_rows * 500 / (1024 ** 3)

        return {
            'strategy': 'pandas',
            'estimated_rows': estimated_rows,
            'estimated_memory_gb': estimated_size_gb * 2,  # 2x for join operation
            'within_limit': estimated_size_gb * 2 <= self.max_memory_gb,
            'cost_usd': 0.0  # No external cost
        }

    async def cleanup(self, job_id: str):
        """No cleanup needed for in-memory operations."""
        pass


class FederationFactory:
    """
    Factory for creating and managing federation strategies.

    Automatically selects the appropriate strategy based on:
    1. Explicit configuration
    2. Target database type
    3. Data size estimates
    """

    # Default strategy for AWS Marketplace deployment
    DEFAULT_STRATEGY = FederationStrategy.REDSHIFT

    # Strategy implementations
    STRATEGIES: Dict[FederationStrategy, Type[BaseFederationStrategy]] = {
        FederationStrategy.REDSHIFT: RedshiftSpectrumStrategy,
        FederationStrategy.BIGQUERY: BigQueryOmniStrategy,
        FederationStrategy.SNOWFLAKE: SnowflakeExternalStageStrategy,
        FederationStrategy.PANDAS: PandasStrategy,
    }

    # Database type to strategy mapping
    DB_TYPE_STRATEGY_MAP = {
        'redshift': FederationStrategy.REDSHIFT,
        'bigquery': FederationStrategy.BIGQUERY,
        'snowflake': FederationStrategy.SNOWFLAKE,
        'postgresql': FederationStrategy.REDSHIFT,  # Use Spectrum for PG
        'databricks': FederationStrategy.REDSHIFT,  # Use Spectrum for Databricks
    }

    def __init__(self, default_config: Optional[FederationConfig] = None):
        """
        Initialize the federation factory.

        Args:
            default_config: Default configuration for all strategies
        """
        self.default_config = default_config or FederationConfig(
            strategy=self.DEFAULT_STRATEGY
        )
        self._strategies: Dict[FederationStrategy, BaseFederationStrategy] = {}

    def get_strategy(
        self,
        strategy: Optional[FederationStrategy] = None,
        target_db_type: Optional[str] = None,
        config: Optional[FederationConfig] = None
    ) -> BaseFederationStrategy:
        """
        Get or create a federation strategy instance.

        Args:
            strategy: Explicit strategy to use
            target_db_type: Target database type (for auto-selection)
            config: Configuration override

        Returns:
            Federation strategy instance
        """
        # Determine strategy
        if strategy is None:
            if target_db_type:
                strategy = self.DB_TYPE_STRATEGY_MAP.get(
                    target_db_type.lower(),
                    self.DEFAULT_STRATEGY
                )
            else:
                strategy = self.DEFAULT_STRATEGY

        # Use config or default
        effective_config = config or self.default_config
        effective_config.strategy = strategy

        # Get or create strategy instance
        if strategy not in self._strategies:
            strategy_class = self.STRATEGIES.get(strategy)
            if strategy_class is None:
                raise ValueError(f"Unknown federation strategy: {strategy}")

            self._strategies[strategy] = strategy_class(effective_config)
            logger.info(f"Created federation strategy: {strategy.value}")

        return self._strategies[strategy]

    async def execute_federated_query(
        self,
        source_connector,
        source_query: str,
        target_connector,
        target_table: str,
        join_condition: str,
        join_type: str = "INNER",
        select_columns: Optional[List[str]] = None,
        estimated_rows: Optional[int] = None,
        strategy: Optional[FederationStrategy] = None
    ) -> Dict[str, Any]:
        """
        Execute a federated query with automatic strategy selection.

        If no strategy specified:
        - Uses Pandas for small datasets (<1M rows / <1GB)
        - Uses cloud-native federation for larger datasets

        Args:
            source_connector: Source database connector
            source_query: Query for source data
            target_connector: Target database connector
            target_table: Target table name
            join_condition: JOIN condition
            join_type: Type of JOIN
            select_columns: Columns to select
            estimated_rows: Estimated row count for strategy selection
            strategy: Explicit strategy override

        Returns:
            Query results with federation metadata
        """
        # Auto-select strategy based on size if not specified
        if strategy is None and estimated_rows:
            if estimated_rows < 1_000_000:  # <1M rows
                strategy = FederationStrategy.PANDAS
            else:
                strategy = self.DEFAULT_STRATEGY

        # Get target database type for strategy selection
        target_db_type = type(target_connector).__name__.lower().replace('connector', '')

        # Get strategy instance
        federation = self.get_strategy(
            strategy=strategy,
            target_db_type=target_db_type
        )

        logger.info(
            "Executing federated query",
            strategy=federation.config.strategy.value,
            target_db=target_db_type,
            estimated_rows=estimated_rows
        )

        # Execute the federated join
        return await federation.execute_federated_join(
            source_connector=source_connector,
            source_query=source_query,
            target_connector=target_connector,
            target_table=target_table,
            join_condition=join_condition,
            join_type=join_type,
            select_columns=select_columns
        )


# Global factory instance
_factory_instance: Optional[FederationFactory] = None


def get_federation_factory(config: Optional[FederationConfig] = None) -> FederationFactory:
    """
    Get or create the global federation factory.

    Args:
        config: Configuration for the factory

    Returns:
        FederationFactory instance
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = FederationFactory(default_config=config)

    return _factory_instance
