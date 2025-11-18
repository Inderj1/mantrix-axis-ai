"""
Cross-Database Executor

Executes queries across multiple databases using federated query plans.
Handles data movement, result merging, and cross-database JOINs.
"""
import pandas as pd
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import structlog
from datetime import datetime

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
        enable_pushdown: bool = True
    ):
        """
        Initialize the cross-database executor.

        Args:
            connector_factory: Factory for creating database connectors
            enable_pushdown: Enable query pushdown optimization (default: True)
        """
        self.factory = connector_factory or ConnectorFactory()
        self.translator = SQLDialectTranslator()
        self.pushdown_optimizer = QueryPushdownOptimizer() if enable_pushdown else None
        self._temp_tables = {}  # Track temporary tables created
        self.enable_pushdown = enable_pushdown
        logger.info(
            "CrossDatabaseExecutor initialized",
            pushdown_enabled=enable_pushdown
        )

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        user_id: str,
        organization_id: str,
        database_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> ExecutionResult:
        """
        Execute a federated query plan.

        Args:
            plan: Execution plan from FederatedQueryPlanner
            user_id: User ID for permissions
            organization_id: Organization ID
            database_configs: Optional database connection configs

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
            user_id=user_id
        )

        start_time = datetime.now()
        step_results = {}

        try:
            # Check permissions for all databases
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
        right_table_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Execute JOIN between tables in different databases.

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

        Returns:
            DataFrame with joined results
        """
        logger.info(
            "Executing cross-database JOIN",
            left_db=left_db,
            right_db=right_db,
            join_type=join_type,
            pushdown_enabled=self.enable_pushdown
        )

        # Get configs or use empty dict
        configs = database_configs or {}

        # Optimize queries with pushdown if enabled and table names provided
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

        # Fetch from left database
        left_connector = self.factory.create_connector(
            left_db,
            config=configs.get(left_db, {})
        )
        left_df = await self._execute_query(left_connector, optimized_left_query)

        # Fetch from right database
        right_connector = self.factory.create_connector(
            right_db,
            config=configs.get(right_db, {})
        )
        right_df = await self._execute_query(right_connector, optimized_right_query)

        # Parse join condition to extract columns
        # Simplified: assumes format "left.col = right.col"
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
            "Cross-database JOIN complete",
            left_rows=len(left_df),
            right_rows=len(right_df),
            result_rows=len(result_df)
        )

        return result_df

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
        # Execute all fetch steps in parallel
        fetch_tasks = []
        for step in plan.steps[:-1]:  # All but last step
            connector = self.factory.create_connector(step.database_type)
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
        primary_connector = self.factory.create_connector(plan.primary_database)
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
        # Execute sub-queries in parallel
        tasks = []
        for step in plan.steps[:-1]:  # All but merge step
            connector = self.factory.create_connector(step.database_type)
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
