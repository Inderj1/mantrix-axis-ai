"""
Cross-Database Executor

Executes queries across multiple databases using federated query plans.
Handles data movement, result merging, and cross-database JOINs.

Supports multiple execution strategies:
- Pandas (in-memory): <1GB datasets
- Staging tables: 1-10GB datasets
- S3 Federation: 10-100GB+ datasets (via FederationFactory)
"""
import pandas as pd
import asyncio
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import structlog
from datetime import datetime

if TYPE_CHECKING:
    from src.core.knowledge_graph.jena_query_resolver import JenaQueryResolver

from src.core.federated_query_planner import (
    ExecutionPlan,
    ExecutionStrategy,
    QueryStep,
    TableReference
)
from src.core.sql_dialect_translator import SQLDialectTranslator
from src.core.query_pushdown_optimizer import QueryPushdownOptimizer
from src.db.connector_factory import ConnectorFactory

logger = structlog.get_logger()

# Lazy imports for federation (only loaded when needed for large datasets)
FederationFactory = None
FederationStrategy = None


def _ensure_federation_imports():
    """Lazy import federation module to avoid loading boto3/pyarrow for small queries."""
    global FederationFactory, FederationStrategy
    if FederationFactory is None:
        from src.core.federation_factory import (
            FederationFactory as _FederationFactory,
            FederationStrategy as _FederationStrategy
        )
        FederationFactory = _FederationFactory
        FederationStrategy = _FederationStrategy


# Data size thresholds for strategy selection (in rows)
PANDAS_MAX_ROWS = 1_000_000        # 1M rows (~1GB)
STAGING_MAX_ROWS = 10_000_000      # 10M rows (~10GB)
# Above STAGING_MAX_ROWS: use S3 Federation


@dataclass
class ExecutionResult:
    """Result of executing a federated query."""
    data: pd.DataFrame
    execution_plan: ExecutionPlan
    execution_time_seconds: float
    rows_returned: int
    databases_accessed: List[str]
    steps_executed: int
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_number: int
    database_type: str
    data: Optional[pd.DataFrame] = None
    rows: int = 0
    execution_time_seconds: float = 0.0
    success: bool = True
    error: Optional[str] = None


class CrossDatabaseExecutor:
    """
    Execute queries across multiple databases.

    Supports:
    - Single database queries
    - Cross-database JOINs
    - Data movement between databases
    - Result merging
    """

    def __init__(
        self,
        connector_factory: Optional[ConnectorFactory] = None,
        enable_pushdown: bool = True,
        enable_federation: bool = True,
        federation_config: Optional[Dict[str, Any]] = None,
        jena_resolver: Optional["JenaQueryResolver"] = None
    ):
        """
        Initialize the cross-database executor.

        Args:
            connector_factory: Factory for creating database connectors
            enable_pushdown: Enable query pushdown optimization (default: True)
            enable_federation: Enable S3 federation for large datasets (default: True)
            federation_config: Optional config for FederationFactory (s3_bucket, etc.)
            jena_resolver: Optional Jena resolver for metadata lookups (row counts, selectivity)
        """
        self.factory = connector_factory or ConnectorFactory()
        self.translator = SQLDialectTranslator()
        self.jena_resolver = jena_resolver
        # Pass Jena resolver to pushdown optimizer for accurate selectivity estimates
        self.pushdown_optimizer = QueryPushdownOptimizer(jena_resolver=jena_resolver) if enable_pushdown else None
        self._temp_tables = {}  # Track temporary tables created
        self.enable_pushdown = enable_pushdown
        self.enable_federation = enable_federation
        self._federation_config = federation_config or {}
        self._federation_factory = None  # Lazy initialized
        logger.info(
            "CrossDatabaseExecutor initialized",
            pushdown_enabled=enable_pushdown,
            federation_enabled=enable_federation,
            has_jena=jena_resolver is not None
        )

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        user_id: str,
        organization_id: str,
        database_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        skip_permission_check: bool = False
    ) -> ExecutionResult:
        """
        Execute a federated query plan.

        Args:
            plan: Execution plan from FederatedQueryPlanner
            user_id: User ID for permissions
            organization_id: Organization ID
            database_configs: Optional database connection configs
            skip_permission_check: If True, skip database-type permission check.
                Use when access has already been verified via connector permissions.

        Returns:
            ExecutionResult with data and metadata

        Raises:
            PermissionError: If user lacks access to required databases
            Exception: If execution fails
        """
        logger.info(
            "Executing federated query plan",
            strategy=plan.strategy.value,
            databases=plan.databases_involved,
            steps=len(plan.steps),
            user_id=user_id,
            skip_permission_check=skip_permission_check
        )

        start_time = datetime.now()
        step_results = {}

        try:
            # Check permissions for all databases (unless already verified via connector access)
            if not skip_permission_check:
                await self._check_permissions(
                    plan.databases_involved,
                    user_id,
                    organization_id
                )

            # Execute steps based on strategy
            if plan.strategy == ExecutionStrategy.SINGLE_DATABASE:
                result_data = await self._execute_single_database(
                    plan,
                    user_id,
                    organization_id,
                    database_configs
                )

            elif plan.strategy == ExecutionStrategy.MOVE_TO_PRIMARY:
                result_data = await self._execute_move_to_primary(
                    plan,
                    user_id,
                    organization_id,
                    database_configs,
                    step_results
                )

            elif plan.strategy == ExecutionStrategy.DISTRIBUTED:
                result_data = await self._execute_distributed(
                    plan,
                    user_id,
                    organization_id,
                    database_configs,
                    step_results
                )

            elif plan.strategy == ExecutionStrategy.MATERIALIZE:
                result_data = await self._execute_materialize(
                    plan,
                    user_id,
                    organization_id,
                    database_configs,
                    step_results
                )

            else:
                raise ValueError(f"Unknown execution strategy: {plan.strategy}")

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Build result
            result = ExecutionResult(
                data=result_data,
                execution_plan=plan,
                execution_time_seconds=execution_time,
                rows_returned=len(result_data),
                databases_accessed=plan.databases_involved,
                steps_executed=len(plan.steps),
                metadata={
                    'step_results': step_results,
                    'strategy': plan.strategy.value
                }
            )

            logger.info(
                "Federated query execution complete",
                strategy=plan.strategy.value,
                rows=len(result_data),
                execution_time=execution_time,
                databases=plan.databases_involved
            )

            return result

        except Exception as e:
            logger.error(
                "Federated query execution failed",
                error=str(e),
                strategy=plan.strategy.value,
                user_id=user_id
            )
            raise

        finally:
            # Cleanup temporary tables
            await self._cleanup_temp_tables()

    async def execute_cross_db_join(
        self,
        left_db: str,
        left_query: str,
        right_db: str,
        right_query: str,
        join_condition: str,
        join_type: str = 'INNER',
        user_id: str = 'anonymous',
        organization_id: str = 'default',
        database_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        left_table_name: Optional[str] = None,
        right_table_name: Optional[str] = None,
        force_strategy: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Execute JOIN between tables in different databases.

        Uses tiered execution strategy based on estimated data size:
        - <1M rows: Pandas in-memory join (fast, no setup)
        - 1-10M rows: Staging table approach
        - >10M rows: S3 Federation (Redshift Spectrum, BigQuery Omni, etc.)

        Args:
            left_db: Left database type
            left_query: SQL for left side
            right_db: Right database type
            right_query: SQL for right side
            join_condition: Join condition (e.g., "left.id = right.user_id")
            join_type: Type of join (INNER, LEFT, RIGHT, FULL)
            user_id: User ID
            organization_id: Organization ID
            database_configs: Optional configs for database connections
            left_table_name: Optional table name for left side (for pushdown optimization)
            right_table_name: Optional table name for right side (for pushdown optimization)
            force_strategy: Force a specific strategy ('pandas', 'staging', 'federation')

        Returns:
            DataFrame with joined results
        """
        # Get configs or use empty dict
        configs = database_configs or {}

        # Create connectors
        left_connector = self.factory.create_connector(
            left_db,
            config=configs.get(left_db, {})
        )
        right_connector = self.factory.create_connector(
            right_db,
            config=configs.get(right_db, {})
        )

        # Estimate data size to select strategy
        # Use Jena table names for faster row count lookup (avoids EXPLAIN queries)
        estimated_left_rows = await self._estimate_row_count(
            left_connector, left_query, table_name=left_table_name
        )
        estimated_right_rows = await self._estimate_row_count(
            right_connector, right_query, table_name=right_table_name
        )
        total_estimated_rows = max(estimated_left_rows or 0, estimated_right_rows or 0)

        # Select execution strategy
        strategy = self._select_join_strategy(
            total_estimated_rows,
            left_db,
            right_db,
            force_strategy
        )

        logger.info(
            "Executing cross-database JOIN",
            left_db=left_db,
            right_db=right_db,
            join_type=join_type,
            strategy=strategy,
            estimated_rows=total_estimated_rows,
            pushdown_enabled=self.enable_pushdown,
            federation_enabled=self.enable_federation
        )

        # Execute based on strategy
        if strategy == 'federation' and self.enable_federation:
            return await self._execute_federated_join(
                left_connector=left_connector,
                left_query=left_query,
                left_db=left_db,
                right_connector=right_connector,
                right_query=right_query,
                right_db=right_db,
                join_condition=join_condition,
                join_type=join_type,
                estimated_rows=total_estimated_rows
            )

        # Default to pandas strategy (handles 'pandas' and 'staging' for now)
        return await self._execute_pandas_join(
            left_connector=left_connector,
            left_query=left_query,
            right_connector=right_connector,
            right_query=right_query,
            join_condition=join_condition,
            join_type=join_type,
            left_table_name=left_table_name,
            right_table_name=right_table_name
        )

    def _select_join_strategy(
        self,
        estimated_rows: int,
        left_db: str,
        right_db: str,
        force_strategy: Optional[str] = None
    ) -> str:
        """
        Select the appropriate join strategy based on data size.

        Args:
            estimated_rows: Estimated number of rows
            left_db: Left database type
            right_db: Right database type
            force_strategy: Optional forced strategy

        Returns:
            Strategy name: 'pandas', 'staging', or 'federation'
        """
        if force_strategy:
            return force_strategy

        # If federation disabled or not configured, always use pandas
        if not self.enable_federation:
            return 'pandas'

        # Check if we have S3 bucket configured for federation
        if not self._federation_config.get('s3_bucket'):
            logger.debug("No S3 bucket configured, using pandas strategy")
            return 'pandas'

        # Select based on data size
        if estimated_rows <= PANDAS_MAX_ROWS:
            return 'pandas'
        elif estimated_rows <= STAGING_MAX_ROWS:
            return 'staging'  # Falls back to pandas for now
        else:
            return 'federation'

    async def _estimate_row_count(
        self,
        connector: Any,
        query: str,
        table_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Estimate the number of rows a query will return.

        Uses Jena metadata first for fast lookup, falls back to connector estimate.

        Args:
            connector: Database connector
            query: SQL query
            table_name: Optional table name for Jena lookup (faster than EXPLAIN)

        Returns:
            Estimated row count, or None if estimation fails
        """
        try:
            # 1. Try Jena first (fast - no database round trip)
            if self.jena_resolver and table_name:
                jena_estimate = self.jena_resolver.get_table_row_count(table_name)
                if jena_estimate is not None:
                    logger.debug(
                        "Using Jena row count estimate",
                        table=table_name,
                        rows=jena_estimate
                    )
                    return jena_estimate

            # 2. Use connector's estimate method if available
            if hasattr(connector, 'estimate_row_count'):
                return connector.estimate_row_count(query)

            # 3. Fallback: use EXPLAIN if supported
            # This is a simplified approach - production would parse EXPLAIN output
            return None

        except Exception as e:
            logger.debug(f"Row count estimation failed: {e}")
            return None

    async def _execute_pandas_join(
        self,
        left_connector: Any,
        left_query: str,
        right_connector: Any,
        right_query: str,
        join_condition: str,
        join_type: str,
        left_table_name: Optional[str] = None,
        right_table_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Execute cross-database JOIN using pandas (in-memory).

        Best for datasets <1M rows.
        """
        # Optimize queries with pushdown if enabled
        optimized_left_query = left_query
        optimized_right_query = right_query

        if self.enable_pushdown and self.pushdown_optimizer:
            if left_table_name:
                optimized_left_query = self._apply_pushdown(
                    left_query,
                    left_table_name,
                    "left"
                )
            if right_table_name:
                optimized_right_query = self._apply_pushdown(
                    right_query,
                    right_table_name,
                    "right"
                )

        # Fetch data from both databases
        left_df = await self._execute_query(left_connector, optimized_left_query)
        right_df = await self._execute_query(right_connector, optimized_right_query)

        # Parse join condition to extract columns
        left_col, right_col = self._parse_join_condition(join_condition)

        # Perform pandas merge
        how = join_type.lower()
        result_df = pd.merge(
            left_df,
            right_df,
            left_on=left_col,
            right_on=right_col,
            how=how
        )

        logger.info(
            "Pandas cross-database JOIN complete",
            left_rows=len(left_df),
            right_rows=len(right_df),
            result_rows=len(result_df)
        )

        return result_df

    async def _execute_federated_join(
        self,
        left_connector: Any,
        left_query: str,
        left_db: str,
        right_connector: Any,
        right_query: str,
        right_db: str,
        join_condition: str,
        join_type: str,
        estimated_rows: int
    ) -> pd.DataFrame:
        """
        Execute cross-database JOIN using federation (S3 + Spectrum/Omni).

        Best for datasets >10M rows (10-100GB+).
        """
        _ensure_federation_imports()

        # Get or create federation factory
        if self._federation_factory is None:
            self._federation_factory = FederationFactory(
                s3_bucket=self._federation_config.get('s3_bucket'),
                s3_prefix=self._federation_config.get('s3_prefix', 'federation'),
                aws_region=self._federation_config.get('aws_region', 'us-east-1')
            )

        # Determine which database is larger (source) and which to use as target
        # Generally, we stream the smaller dataset to S3 and join in the larger DB
        # For simplicity, assume left is source (streamed) and right is target
        source_connector = left_connector
        source_query = left_query
        target_connector = right_connector
        target_db = right_db

        # Parse join condition
        left_col, right_col = self._parse_join_condition(join_condition)

        logger.info(
            "Starting federated JOIN via S3",
            source_db=left_db,
            target_db=right_db,
            estimated_rows=estimated_rows
        )

        try:
            # Execute federated query
            result = await self._federation_factory.execute_federated_query(
                source_connector=source_connector,
                source_query=source_query,
                target_connector=target_connector,
                join_condition=f"e.{left_col} = t.{right_col}",
                join_type=join_type,
                estimated_rows=estimated_rows
            )

            # Convert result to DataFrame
            if isinstance(result, dict):
                rows = result.get('rows', [])
                result_df = pd.DataFrame(rows)

                logger.info(
                    "Federated JOIN complete",
                    rows=len(result_df),
                    federation_metadata=result.get('federation_metadata', {})
                )
                return result_df
            elif isinstance(result, pd.DataFrame):
                return result
            else:
                logger.warning(f"Unexpected federation result type: {type(result)}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(
                "Federated JOIN failed, falling back to pandas",
                error=str(e)
            )
            # Fall back to pandas for robustness
            return await self._execute_pandas_join(
                left_connector=left_connector,
                left_query=left_query,
                right_connector=right_connector,
                right_query=right_query,
                join_condition=join_condition,
                join_type=join_type
            )

    async def _check_permissions(
        self,
        databases: List[str],
        user_id: str,
        organization_id: str
    ):
        """Check user has access to all required databases."""
        from src.core.database_permissions import AccessLevel

        for db_type in databases:
            has_access = self.factory.check_user_access(
                user_id=user_id,
                database_type=db_type,
                required_level=AccessLevel.READ.value,
                organization_id=organization_id
            )

            if not has_access:
                raise PermissionError(
                    f"User {user_id} lacks access to {db_type} database"
                )

    async def _execute_single_database(
        self,
        plan: ExecutionPlan,
        user_id: str,
        organization_id: str,
        database_configs: Optional[Dict[str, Dict[str, Any]]]
    ) -> pd.DataFrame:
        """Execute query in a single database."""
        step = plan.steps[0]
        connector = self.factory.create_connector(
            step.database_type,
            config=database_configs.get(step.database_type) if database_configs else None
        )
        connector.connect()

        result_df = await self._execute_query(connector, step.sql)
        return result_df

    async def _execute_move_to_primary(
        self,
        plan: ExecutionPlan,
        user_id: str,
        organization_id: str,
        database_configs: Optional[Dict[str, Dict[str, Any]]],
        step_results: Dict[int, StepResult]
    ) -> pd.DataFrame:
        """
        Execute by fetching from secondary databases and joining in primary.
        """
        configs = database_configs or {}

        # Execute all fetch steps in parallel
        fetch_tasks = []
        for step in plan.steps[:-1]:  # All but last step
            connector = self.factory.create_connector(
                step.database_type,
                configs.get(step.database_type, {})
            )
            connector.connect()
            task = self._execute_step_async(step, connector)
            fetch_tasks.append(task)

        # Wait for all fetches
        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Store results
        for i, result in enumerate(fetch_results):
            if isinstance(result, Exception):
                logger.error(f"Step {i+1} failed", error=str(result))
                raise result
            step_results[i + 1] = result

        # For now, just return the first result
        # In a full implementation, we'd join the results based on the query
        final_step = plan.steps[-1]
        primary_connector = self.factory.create_connector(
            plan.primary_database,
            configs.get(plan.primary_database, {})
        )
        primary_connector.connect()
        final_result = await self._execute_query(primary_connector, final_step.sql)

        return final_result

    async def _execute_distributed(
        self,
        plan: ExecutionPlan,
        user_id: str,
        organization_id: str,
        database_configs: Optional[Dict[str, Dict[str, Any]]],
        step_results: Dict[int, StepResult]
    ) -> pd.DataFrame:
        """Execute query parts in parallel across databases and merge."""
        # Execute all query steps in parallel
        # For UNION/UNION_ALL, all steps are query steps (no merge step)
        tasks = []
        configs = database_configs or {}
        for step in plan.steps:  # Process ALL steps
            connector = self.factory.create_connector(
                step.database_type,
                configs.get(step.database_type, {})
            )
            connector.connect()
            task = self._execute_step_async(step, connector)
            tasks.append(task)

        # Wait for all sub-queries
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        dfs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Step {i+1} failed", error=str(result))
                raise result
            if result.data is not None:
                dfs.append(result.data)
            step_results[i + 1] = result

        # Concatenate results
        if dfs:
            merged_df = pd.concat(dfs, ignore_index=True)
        else:
            merged_df = pd.DataFrame()

        return merged_df

    async def _execute_materialize(
        self,
        plan: ExecutionPlan,
        user_id: str,
        organization_id: str,
        database_configs: Optional[Dict[str, Dict[str, Any]]],
        step_results: Dict[int, StepResult]
    ) -> pd.DataFrame:
        """Execute using materialized temporary tables."""
        # For now, similar to move_to_primary
        # In full implementation, would create actual temp tables in target DB
        return await self._execute_move_to_primary(
            plan,
            user_id,
            organization_id,
            database_configs,
            step_results
        )

    async def _execute_step_async(
        self,
        step: QueryStep,
        connector: Any
    ) -> StepResult:
        """Execute a single query step asynchronously."""
        start_time = datetime.now()

        try:
            result_df = await self._execute_query(connector, step.sql)
            execution_time = (datetime.now() - start_time).total_seconds()

            return StepResult(
                step_number=step.step_number,
                database_type=step.database_type,
                data=result_df,
                rows=len(result_df),
                execution_time_seconds=execution_time,
                success=True
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(
                "Step execution failed",
                step=step.step_number,
                database=step.database_type,
                error=str(e)
            )

            return StepResult(
                step_number=step.step_number,
                database_type=step.database_type,
                execution_time_seconds=execution_time,
                success=False,
                error=str(e)
            )

    async def _execute_query(
        self,
        connector: Any,
        sql: str
    ) -> pd.DataFrame:
        """
        Execute SQL query and return DataFrame.

        Args:
            connector: Database connector
            sql: SQL query to execute

        Returns:
            DataFrame with results
        """
        try:
            # Execute query
            result = await asyncio.to_thread(
                connector.execute_query,
                sql
            )

            # Convert to DataFrame if not already
            if isinstance(result, pd.DataFrame):
                return result
            elif isinstance(result, dict):
                # Result from BigQuery/other connectors
                if 'rows' in result:
                    return pd.DataFrame(result['rows'])
                return pd.DataFrame([result])
            elif isinstance(result, list):
                return pd.DataFrame(result)
            else:
                logger.warning(f"Unexpected result type: {type(result)}")
                return pd.DataFrame()

        except Exception as e:
            logger.error("Query execution failed", sql=sql[:100], error=str(e))
            raise

    def _parse_join_condition(self, condition: str) -> Tuple[str, str]:
        """
        Parse join condition to extract column names.

        Args:
            condition: Join condition like "left.id = right.user_id"

        Returns:
            Tuple of (left_column, right_column)
        """
        # Simplified parser
        parts = condition.strip().split('=')
        if len(parts) != 2:
            raise ValueError(f"Invalid join condition: {condition}")

        left_part = parts[0].strip()
        right_part = parts[1].strip()

        # Extract column names (remove table prefixes)
        left_col = left_part.split('.')[-1] if '.' in left_part else left_part
        right_col = right_part.split('.')[-1] if '.' in right_part else right_part

        return left_col, right_col

    def _apply_pushdown(
        self,
        query: str,
        table_name: str,
        table_alias: Optional[str] = None
    ) -> str:
        """
        Apply query pushdown optimization to reduce data transfer.

        Args:
            query: Original SQL query
            table_name: Table being queried
            table_alias: Optional alias for the table

        Returns:
            Optimized SQL query
        """
        if not self.pushdown_optimizer:
            return query

        try:
            # Analyze pushdown opportunities
            analysis = self.pushdown_optimizer.analyze_pushdown_opportunities(
                query,
                table_name,
                table_alias
            )

            # Log optimization results
            if analysis.can_pushdown_filters or analysis.can_pushdown_projections:
                logger.info(
                    "Query pushdown optimization applied",
                    table=table_name,
                    filters_pushed=len(analysis.pushdown_filters),
                    columns_selected=len(analysis.required_columns) if analysis.required_columns else 0,
                    estimated_reduction=f"{analysis.estimated_reduction_percent:.1f}%"
                )

                # Use optimized query if available
                if analysis.optimized_sql:
                    return analysis.optimized_sql

        except Exception as e:
            logger.warning(
                "Failed to apply pushdown optimization, using original query",
                error=str(e)
            )

        return query

    async def _cleanup_temp_tables(self):
        """Clean up any temporary tables created during execution."""
        if not self._temp_tables:
            return

        logger.info(f"Cleaning up {len(self._temp_tables)} temporary tables")

        for table_name, (db_type, connector) in self._temp_tables.items():
            try:
                drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                await self._execute_query(connector, drop_sql)
                logger.debug(f"Dropped temp table: {table_name}")
            except Exception as e:
                logger.warning(f"Failed to drop temp table {table_name}", error=str(e))

        self._temp_tables.clear()


# Singleton instance and factory function
_executor_instance: Optional[CrossDatabaseExecutor] = None


def get_cross_database_executor(
    connector_factory: Optional[ConnectorFactory] = None
) -> CrossDatabaseExecutor:
    """
    Get or create a configured CrossDatabaseExecutor singleton.

    Uses settings from config.py for federation configuration.

    Args:
        connector_factory: Optional custom connector factory

    Returns:
        Configured CrossDatabaseExecutor instance
    """
    global _executor_instance

    if _executor_instance is None:
        from src.config import settings

        # Build federation config from settings
        federation_config = {
            's3_bucket': settings.federation_s3_bucket,
            's3_prefix': settings.federation_s3_prefix,
            'redshift_schema': settings.federation_redshift_schema,
            'aws_region': settings.aws_region,
            'chunk_size': settings.federation_chunk_size,
            'ttl_hours': settings.federation_ttl_hours
        }

        _executor_instance = CrossDatabaseExecutor(
            connector_factory=connector_factory,
            enable_pushdown=True,
            enable_federation=settings.federation_enabled,
            federation_config=federation_config
        )

        logger.info(
            "Created CrossDatabaseExecutor singleton",
            federation_enabled=settings.federation_enabled,
            s3_bucket=settings.federation_s3_bucket
        )

    return _executor_instance


def reset_executor():
    """Reset the executor singleton (useful for testing)."""
    global _executor_instance
    _executor_instance = None
