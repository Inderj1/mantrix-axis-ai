"""
Query Orchestrator

Coordinates the query processing pipeline:
1. Generate SQL from natural language (SQLGenerator)
2. Analyze SQL for execution strategy (SingleDatabaseQueryOptimizer)
3. Check if async execution is required (>1B rows)
4. Execute the query (connector)

This module provides a clean interface for routes.py and ensures
the requires_async check happens at the right point in the flow.
"""

import time
import structlog
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from src.core.single_db_query_optimizer import (
    SingleDatabaseQueryOptimizer,
    QueryAnalysis,
    ExecutionStrategy,
    VERY_LARGE_TABLE_THRESHOLD
)

logger = structlog.get_logger()


@dataclass
class QueryResult:
    """Result of query processing."""
    # Status
    status: str  # "complete", "long_running", "error"

    # SQL Generation
    sql: Optional[str] = None
    explanation: Optional[str] = None
    tables_used: List[str] = field(default_factory=list)

    # Execution (if completed)
    results: Optional[List[Dict]] = None
    row_count: int = 0
    execution_time_seconds: float = 0.0

    # Long-running query info
    requires_async: bool = False
    is_long_running: bool = False
    largest_table_rows: int = 0
    estimated_minutes: int = 0

    # Analysis details
    query_analysis: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)

    # Error info
    error: Optional[str] = None

    # Metadata
    from_cache: bool = False
    database_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "status": self.status,
            "sql": self.sql,
            "explanation": self.explanation,
            "tables_used": self.tables_used,
            "requires_async": self.requires_async,
            "is_long_running": self.is_long_running,
            "warnings": self.warnings,
            "from_cache": self.from_cache,
        }

        if self.results is not None:
            result["execution"] = {
                "results": self.results,
                "row_count": self.row_count,
                "execution_time_seconds": self.execution_time_seconds,
            }

        if self.is_long_running:
            result["largest_table_rows"] = self.largest_table_rows
            result["estimated_minutes"] = self.estimated_minutes
            result["message"] = (
                f"This query scans ~{self.largest_table_rows:,} rows and may take "
                f"{self.estimated_minutes}+ minutes. You can wait or close this and "
                "be notified when it completes."
            )

        if self.query_analysis:
            result["query_analysis"] = self.query_analysis

        if self.error:
            result["error"] = self.error

        if self.database_type:
            result["database_type"] = self.database_type

        return result


class QueryOrchestrator:
    """
    Orchestrates the query processing pipeline.

    This class coordinates:
    1. SQL generation from natural language
    2. Query analysis for execution strategy
    3. Async detection for very large tables
    4. Query execution

    The key benefit is that requires_async is checked in ONE place,
    making it easy to debug and maintain.
    """

    def __init__(
        self,
        sql_generator,  # SQLGenerator instance
        organization_id: str = "default",
        database_type: str = "snowflake"
    ):
        """
        Initialize the orchestrator.

        Args:
            sql_generator: SQLGenerator instance for SQL generation
            organization_id: Organization ID for multi-tenancy
            database_type: Default database type
        """
        self.sql_generator = sql_generator
        self.organization_id = organization_id
        self.database_type = database_type

        # Get the query optimizer from sql_generator if it exists
        self.query_optimizer = getattr(sql_generator, 'single_db_optimizer', None)

        logger.info(
            "QueryOrchestrator initialized",
            organization_id=organization_id,
            database_type=database_type,
            has_optimizer=self.query_optimizer is not None
        )

    def process_query(
        self,
        question: str,
        execute: bool = True,
        database_type: Optional[str] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
        persona_context: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Process a natural language query through the full pipeline.

        This is the main entry point for query processing. It:
        1. Generates SQL from the question
        2. Analyzes the SQL for execution strategy
        3. Returns early if async execution is required
        4. Executes the query and returns results

        Args:
            question: Natural language question
            execute: Whether to execute the query (False for SQL-only)
            database_type: Target database type (overrides default)
            conversation_context: Previous conversation context
            persona_context: User persona context

        Returns:
            QueryResult with status and data
        """
        start_time = time.time()
        db_type = database_type or self.database_type

        logger.info(
            "QueryOrchestrator: Starting query processing",
            question_preview=question[:100] if question else None,
            execute=execute,
            database_type=db_type
        )

        try:
            # Step 1: Generate SQL
            generation_result = self.sql_generator.generate_sql(
                query=question,
                conversation_context=conversation_context,
                persona_context=persona_context
            )

            # Check for generation errors
            if generation_result.get("error"):
                return QueryResult(
                    status="error",
                    error=generation_result.get("error"),
                    database_type=db_type
                )

            sql = generation_result.get("sql")
            if not sql:
                return QueryResult(
                    status="error",
                    error="No SQL generated",
                    database_type=db_type
                )

            # Step 2: Analyze the SQL for execution strategy
            analysis = self._analyze_sql(sql, db_type)

            # Step 3: Check if async execution is required
            # THIS IS THE KEY CHECK - happens in ONE clear place!
            if analysis and analysis.requires_async:
                estimated_minutes = self._estimate_execution_time(analysis)

                logger.info(
                    "QueryOrchestrator: Async execution required",
                    largest_table=analysis.largest_table,
                    largest_table_rows=f"{analysis.largest_table_rows:,}",
                    estimated_minutes=estimated_minutes,
                    strategy=analysis.strategy.value
                )

                return QueryResult(
                    status="long_running",
                    sql=sql,
                    explanation=generation_result.get("explanation"),
                    tables_used=generation_result.get("tables_used", []),
                    requires_async=True,
                    is_long_running=True,
                    largest_table_rows=analysis.largest_table_rows,
                    estimated_minutes=estimated_minutes,
                    query_analysis=analysis.to_dict() if analysis else None,
                    warnings=analysis.warnings if analysis else [],
                    database_type=db_type
                )

            # Step 4: If not executing, return SQL only
            if not execute:
                return QueryResult(
                    status="complete",
                    sql=sql,
                    explanation=generation_result.get("explanation"),
                    tables_used=generation_result.get("tables_used", []),
                    query_analysis=analysis.to_dict() if analysis else None,
                    warnings=analysis.warnings if analysis else [],
                    from_cache=generation_result.get("from_cache", False),
                    database_type=db_type
                )

            # Step 5: Execute the query
            execution_result = self._execute_query(sql, db_type, analysis)

            execution_time = time.time() - start_time

            return QueryResult(
                status="complete",
                sql=sql,
                explanation=generation_result.get("explanation"),
                tables_used=generation_result.get("tables_used", []),
                results=execution_result.get("rows", []),
                row_count=execution_result.get("row_count", 0),
                execution_time_seconds=execution_time,
                query_analysis=analysis.to_dict() if analysis else None,
                warnings=analysis.warnings if analysis else [],
                from_cache=generation_result.get("from_cache", False),
                database_type=db_type
            )

        except Exception as e:
            logger.error(
                "QueryOrchestrator: Query processing failed",
                error=str(e),
                exc_info=True
            )
            return QueryResult(
                status="error",
                error=str(e),
                database_type=db_type
            )

    def analyze_for_preview(
        self,
        sql: str,
        database_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze SQL for preview (used by preview endpoint).

        Returns analysis without executing, useful for showing
        warnings to users before they commit to running a query.

        Args:
            sql: SQL query to analyze
            database_type: Target database type

        Returns:
            Dict with analysis results including requires_async flag
        """
        db_type = database_type or self.database_type
        analysis = self._analyze_sql(sql, db_type)

        if analysis:
            estimated_minutes = self._estimate_execution_time(analysis) if analysis.requires_async else 0

            return {
                "tables": analysis.tables,
                "largest_table": analysis.largest_table,
                "largest_table_rows": analysis.largest_table_rows,
                "total_estimated_rows": analysis.total_estimated_rows,
                "strategy": analysis.strategy.value,
                "requires_async": analysis.requires_async,
                "is_long_running": analysis.requires_async,
                "estimated_minutes": estimated_minutes,
                "warnings": analysis.warnings,
                "has_aggregation": analysis.has_aggregation,
                "has_joins": analysis.has_joins,
                "supports_pagination": analysis.supports_pagination
            }

        return {
            "tables": [],
            "requires_async": False,
            "is_long_running": False,
            "warnings": []
        }

    def _analyze_sql(
        self,
        sql: str,
        database_type: str
    ) -> Optional[QueryAnalysis]:
        """
        Analyze SQL query for execution strategy.

        Uses SingleDatabaseQueryOptimizer to determine:
        - Which tables are involved
        - Row counts for each table
        - Execution strategy (DIRECT/OPTIMIZED/FEDERATED)
        - Whether async execution is required
        """
        if not self.query_optimizer:
            logger.warning("No query optimizer available, skipping analysis")
            return None

        try:
            # Map database type to dialect
            dialect_map = {
                "snowflake": "snowflake",
                "bigquery": "bigquery",
                "postgresql": "postgres",
                "redshift": "redshift",
                "databricks": "spark"
            }
            dialect = dialect_map.get(database_type, "snowflake")

            analysis = self.query_optimizer.analyze_query(sql, dialect)

            logger.info(
                "QueryOrchestrator: SQL analysis complete",
                tables=analysis.tables,
                largest_table=analysis.largest_table,
                largest_table_rows=f"{analysis.largest_table_rows:,}",
                strategy=analysis.strategy.value,
                requires_async=analysis.requires_async
            )

            return analysis

        except Exception as e:
            logger.warning(
                "QueryOrchestrator: SQL analysis failed",
                error=str(e)
            )
            return None

    def _execute_query(
        self,
        sql: str,
        database_type: str,
        analysis: Optional[QueryAnalysis]
    ) -> Dict[str, Any]:
        """
        Execute SQL query on the appropriate connector.

        For normal queries, executes directly.
        For federated queries, uses CrossDatabaseExecutor.
        """
        try:
            # Use sql_generator's execute_query method
            result = self.sql_generator.execute_query(sql, database_type)
            return result

        except Exception as e:
            logger.error(
                "QueryOrchestrator: Query execution failed",
                error=str(e),
                sql_preview=sql[:100] if sql else None
            )
            raise

    def _estimate_execution_time(self, analysis: QueryAnalysis) -> int:
        """
        Estimate execution time in minutes based on row count.

        Rough estimate:
        - 1B rows ~ 5 minutes
        - 5B rows ~ 10 minutes
        - 10B+ rows ~ 15+ minutes
        """
        rows = analysis.largest_table_rows

        if rows < 1_000_000_000:
            return 1
        elif rows < 5_000_000_000:
            return 5
        elif rows < 10_000_000_000:
            return 10
        elif rows < 20_000_000_000:
            return 15
        else:
            # Scale: roughly 5 minutes per 5B rows
            return max(5, int(rows / 5_000_000_000) * 5)


# Singleton instance
_orchestrator_instance: Optional[QueryOrchestrator] = None


def get_query_orchestrator(
    sql_generator=None,
    organization_id: str = "default",
    database_type: str = "snowflake"
) -> QueryOrchestrator:
    """
    Get or create the QueryOrchestrator singleton.

    Args:
        sql_generator: SQLGenerator instance (required on first call)
        organization_id: Organization ID
        database_type: Default database type

    Returns:
        QueryOrchestrator instance
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        if sql_generator is None:
            raise ValueError("sql_generator is required on first call to get_query_orchestrator")
        _orchestrator_instance = QueryOrchestrator(
            sql_generator=sql_generator,
            organization_id=organization_id,
            database_type=database_type
        )

    return _orchestrator_instance
