"""
Single Database Query Optimizer

Applies the same pushdown optimization and execution strategies used by
CrossDatabaseExecutor to single-database queries. This is especially important
for large tables (like Snowflake TPC-DS at 10TB+ scale) that would otherwise
timeout or run out of memory.

Key Features:
1. Query pushdown - pushes WHERE, SELECT, LIMIT to source database
2. Row count estimation - uses Weaviate/Jena metadata to estimate data size
3. Strategy selection - chooses optimal execution strategy based on data size
4. S3 Federation - routes very large queries through Redshift Spectrum

This ensures single-database queries on billion-row tables work just as well
as cross-database queries.
"""
import asyncio
import sqlglot
from sqlglot import exp, parse_one
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import structlog
import time
import tracemalloc
import os

if TYPE_CHECKING:
    from src.core.knowledge_graph.jena_query_resolver import JenaQueryResolver
    from src.db.weaviate_client import WeaviateClient
    from src.db.base_connector import BaseDatabaseConnector

from src.core.query_pushdown_optimizer import QueryPushdownOptimizer, PushdownAnalysis
from src.config import settings

logger = structlog.get_logger()


# Data size thresholds (same as CrossDatabaseExecutor)
PANDAS_MAX_ROWS = 1_000_000        # 1M rows - direct execution OK
STAGING_MAX_ROWS = 10_000_000      # 10M rows - needs optimization
FEDERATION_THRESHOLD = 100_000_000  # 100M rows - consider federation

# Very large table threshold - force async execution
VERY_LARGE_TABLE_THRESHOLD = 1_000_000_000  # 1B rows - requires async/background execution

# Sync return limit - max rows to return in single HTTP response
# For non-aggregation queries exceeding this, force pagination
SYNC_RETURN_MAX_ROWS = 10_000  # 10K rows max for synchronous return


class ExecutionStrategy(Enum):
    """Execution strategy for single-database queries."""
    DIRECT = "direct"          # Execute directly on connector (< 1M rows)
    OPTIMIZED = "optimized"    # Apply pushdown optimization (1-100M rows)
    FEDERATED = "federated"    # Route through S3 federation (> 100M rows)


@dataclass
class JoinInfo:
    """Information about a JOIN in the query."""
    left_table: str
    right_table: str
    join_type: str  # INNER, LEFT, RIGHT, FULL, CROSS
    join_columns: List[Tuple[str, str]]  # [(left_col, right_col), ...]
    estimated_selectivity: float = 1.0  # JOIN reduction factor (0-1)


@dataclass
class QueryAnalysis:
    """Analysis of a single-database query for optimization."""
    # Extracted info
    tables: List[str] = field(default_factory=list)
    table_row_counts: Dict[str, int] = field(default_factory=dict)
    total_estimated_rows: int = 0
    largest_table: Optional[str] = None
    largest_table_rows: int = 0

    # JOIN information
    has_joins: bool = False
    joins: List[JoinInfo] = field(default_factory=list)
    join_estimated_rows: int = 0  # Estimated rows after JOINs

    # Query characteristics
    has_aggregation: bool = False
    has_limit: bool = False
    has_filters: bool = False
    limit_value: Optional[int] = None
    group_by_columns: List[str] = field(default_factory=list)
    aggregation_columns: List[str] = field(default_factory=list)  # SUM, COUNT, etc. columns

    # Pushdown analysis (per-table for multi-table queries)
    pushdown_analysis: Optional[PushdownAnalysis] = None
    table_pushdown_analyses: Dict[str, PushdownAnalysis] = field(default_factory=dict)
    optimized_sql: Optional[str] = None

    # Strategy selection
    strategy: ExecutionStrategy = ExecutionStrategy.DIRECT
    estimated_result_rows: int = 0

    # Pagination support
    supports_pagination: bool = False
    total_count_sql: Optional[str] = None

    # Warnings for user
    warnings: List[str] = field(default_factory=list)

    # Performance metrics
    analysis_time_ms: float = 0.0
    memory_used_mb: float = 0.0

    # Async execution flag - set when table is very large (>1B rows)
    requires_async: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary for logging."""
        return {
            "tables": self.tables,
            "table_row_counts": self.table_row_counts,
            "total_estimated_rows": self.total_estimated_rows,
            "largest_table": self.largest_table,
            "largest_table_rows": self.largest_table_rows,
            "has_joins": self.has_joins,
            "join_count": len(self.joins),
            "join_estimated_rows": self.join_estimated_rows,
            "has_aggregation": self.has_aggregation,
            "has_limit": self.has_limit,
            "has_filters": self.has_filters,
            "limit_value": self.limit_value,
            "group_by_columns": self.group_by_columns,
            "aggregation_columns": self.aggregation_columns,
            "strategy": self.strategy.value,
            "estimated_result_rows": self.estimated_result_rows,
            "supports_pagination": self.supports_pagination,
            "warnings": self.warnings,
            "analysis_time_ms": round(self.analysis_time_ms, 2),
            "memory_used_mb": round(self.memory_used_mb, 3),
            "requires_async": self.requires_async,
        }


class SingleDatabaseQueryOptimizer:
    """
    Optimizer for single-database queries using pushdown and federation.

    Uses the same strategies as CrossDatabaseExecutor:
    - DIRECT: For small tables (< 1M rows), execute as-is
    - OPTIMIZED: For medium tables (1-100M rows), apply pushdown optimization
    - FEDERATED: For very large tables (> 100M rows), route through S3
    """

    def __init__(
        self,
        jena_resolver: Optional["JenaQueryResolver"] = None,
        weaviate_client: Optional["WeaviateClient"] = None,
        organization_id: str = "default",
        database_type: str = "bigquery"
    ):
        """
        Initialize the optimizer.

        Args:
            jena_resolver: Jena resolver for row count/selectivity lookups
            weaviate_client: Weaviate client for table metadata
            organization_id: Organization ID for multi-tenancy
            database_type: Database type for dialect selection
        """
        self.jena_resolver = jena_resolver
        self.weaviate_client = weaviate_client
        self.organization_id = organization_id
        self.database_type = database_type

        # Initialize pushdown optimizer with Jena for selectivity data
        self.pushdown_optimizer = QueryPushdownOptimizer(jena_resolver=jena_resolver)

        logger.info(
            "SingleDatabaseQueryOptimizer initialized",
            organization_id=organization_id,
            database_type=database_type,
            has_jena=jena_resolver is not None,
            has_weaviate=weaviate_client is not None
        )

    def analyze_query(self, sql: str, dialect: str = "snowflake") -> QueryAnalysis:
        """
        Analyze a SQL query and determine optimal execution strategy.

        Enhanced to handle:
        - Multi-table JOINs with proper row estimation
        - Per-table pushdown analysis
        - Pagination support detection

        Args:
            sql: The SQL query to analyze
            dialect: SQL dialect for parsing

        Returns:
            QueryAnalysis with strategy recommendation
        """
        analysis = QueryAnalysis()

        # Start timing and memory tracking
        start_time = time.perf_counter()
        tracemalloc.start()
        mem_start = tracemalloc.get_traced_memory()[0]

        try:
            logger.info(
                "Starting query analysis",
                sql_preview=sql[:100] + "..." if len(sql) > 100 else sql,
                dialect=dialect,
                database_type=self.database_type
            )

            # Parse SQL
            parse_start = time.perf_counter()
            parsed = parse_one(sql, read=dialect)
            parse_time = (time.perf_counter() - parse_start) * 1000
            logger.debug(f"SQL parsing completed in {parse_time:.2f}ms")

            # 1. Extract tables and their row counts
            analysis.tables = self._extract_table_names(parsed)
            logger.debug(f"Extracted tables: {analysis.tables}")

            row_count_start = time.perf_counter()
            tables_without_row_count = []
            for table_name in analysis.tables:
                row_count = self._get_table_row_count(table_name)
                if row_count:
                    analysis.table_row_counts[table_name] = row_count
                    # Track largest table
                    if row_count > analysis.largest_table_rows:
                        analysis.largest_table_rows = row_count
                        analysis.largest_table = table_name
                    logger.debug(
                        f"Table row count",
                        table=table_name,
                        row_count=f"{row_count:,}",
                        source="jena/weaviate"
                    )
                else:
                    tables_without_row_count.append(table_name)
                    logger.warning(f"No row count found for table: {table_name}")

            # Check fail-fast for unknown table sizes
            if tables_without_row_count and settings.fail_fast_on_unknown_table_size:
                missing_tables_str = ", ".join(tables_without_row_count)
                error_msg = (
                    f"Cannot determine size of table(s): {missing_tables_str}. "
                    f"This prevents safe query execution strategy selection. "
                    f"Please sync the database schema to load table metadata, "
                    f"or set FAIL_FAST_ON_UNKNOWN_TABLE_SIZE=false to allow "
                    f"queries on tables with unknown size."
                )
                logger.error(
                    "Fail-fast: Unknown table sizes",
                    tables=tables_without_row_count,
                    database_type=self.database_type
                )
                raise ValueError(error_msg)
            elif tables_without_row_count:
                # Log warning but continue (fail_fast disabled)
                for table_name in tables_without_row_count:
                    analysis.warnings.append(
                        f"Unknown size for table '{table_name}' - assuming small table"
                    )

            row_count_time = (time.perf_counter() - row_count_start) * 1000
            logger.debug(f"Row count lookup completed in {row_count_time:.2f}ms")

            # 2. Detect JOINs and extract JOIN info
            analysis.joins = self._extract_joins(parsed)
            analysis.has_joins = len(analysis.joins) > 0
            if analysis.has_joins:
                logger.info(
                    f"Detected {len(analysis.joins)} JOIN(s) in query",
                    tables=analysis.tables,
                    join_types=[j.join_type for j in analysis.joins]
                )

            # 3. Calculate total_estimated_rows based on query structure
            if analysis.has_joins:
                # For JOINs: use largest table as base, not sum
                analysis.total_estimated_rows = analysis.largest_table_rows
                # Estimate JOIN result rows based on cardinality
                analysis.join_estimated_rows = self._estimate_join_rows(analysis)
                logger.info(
                    "JOIN row estimation",
                    largest_table=analysis.largest_table,
                    largest_rows=f"{analysis.largest_table_rows:,}",
                    join_estimated_rows=f"{analysis.join_estimated_rows:,}"
                )
            else:
                # Single table: use that table's row count
                analysis.total_estimated_rows = sum(analysis.table_row_counts.values())

            # 4. Detect query characteristics
            analysis.has_aggregation = self._has_aggregation(parsed)
            analysis.has_limit = self._has_limit(parsed)
            analysis.has_filters = self._has_filters(parsed)
            analysis.limit_value = self._extract_limit_value(parsed)
            analysis.group_by_columns = self._extract_group_by_columns(parsed)
            analysis.aggregation_columns = self._extract_aggregation_columns(parsed)

            # Determine if query supports pagination (row-level without aggregation)
            # Even if LLM added LIMIT, we still support pagination for large tables
            # The LIMIT just means we're on page 1 with that page size
            analysis.supports_pagination = not analysis.has_aggregation

            logger.debug(
                "Query characteristics detected",
                has_aggregation=analysis.has_aggregation,
                has_limit=analysis.has_limit,
                has_filters=analysis.has_filters,
                has_joins=analysis.has_joins,
                limit_value=analysis.limit_value,
                group_by_count=len(analysis.group_by_columns),
                group_by_columns=analysis.group_by_columns,
                aggregation_columns=analysis.aggregation_columns,
                supports_pagination=analysis.supports_pagination
            )

            # 5. Apply pushdown analysis - per table for multi-table queries
            estimated_rows = analysis.join_estimated_rows if analysis.has_joins else analysis.total_estimated_rows

            if analysis.tables and analysis.has_filters:
                pushdown_start = time.perf_counter()

                # Analyze pushdown for each table in the query
                total_reduction = 0.0
                for table_name in analysis.tables:
                    try:
                        pushdown = self.pushdown_optimizer.analyze_pushdown_opportunities(
                            sql, table_name
                        )
                        analysis.table_pushdown_analyses[table_name] = pushdown
                        if pushdown.estimated_reduction_percent > 0:
                            total_reduction = max(total_reduction, pushdown.estimated_reduction_percent)
                            logger.debug(
                                f"Pushdown for {table_name}: {pushdown.estimated_reduction_percent:.1f}% reduction"
                            )
                    except Exception as e:
                        logger.debug(f"Pushdown analysis failed for {table_name}: {e}")

                # Use the best pushdown analysis as the primary one
                if analysis.table_pushdown_analyses:
                    best_table = max(
                        analysis.table_pushdown_analyses.keys(),
                        key=lambda t: analysis.table_pushdown_analyses[t].estimated_reduction_percent
                    )
                    analysis.pushdown_analysis = analysis.table_pushdown_analyses[best_table]

                pushdown_time = (time.perf_counter() - pushdown_start) * 1000

                if total_reduction > 0:
                    reduction_factor = 1 - (total_reduction / 100)
                    estimated_rows = int(estimated_rows * reduction_factor)
                    logger.info(
                        "Pushdown optimization analyzed",
                        tables_analyzed=len(analysis.table_pushdown_analyses),
                        best_reduction_percent=f"{total_reduction:.1f}%",
                        original_rows=f"{analysis.total_estimated_rows:,}",
                        reduced_rows=f"{estimated_rows:,}",
                        analysis_time_ms=f"{pushdown_time:.2f}"
                    )

                if analysis.pushdown_analysis and analysis.pushdown_analysis.optimized_sql:
                    analysis.optimized_sql = analysis.pushdown_analysis.optimized_sql

            # 6. Apply aggregation reduction estimate
            if analysis.has_aggregation and analysis.group_by_columns:
                # Aggregation with GROUP BY dramatically reduces output
                # Estimate: output rows ≈ cardinality of GROUP BY columns
                # Conservative estimate: 1% of largest table or 1M rows max
                agg_estimate = min(analysis.largest_table_rows * 0.01, 1_000_000)
                if agg_estimate < estimated_rows:
                    logger.info(
                        "Aggregation reduction applied",
                        group_by_columns=analysis.group_by_columns,
                        before=f"{estimated_rows:,}",
                        after=f"{int(agg_estimate):,}"
                    )
                    estimated_rows = int(agg_estimate)

            # 7. Apply limit if present
            if analysis.has_limit and analysis.limit_value:
                estimated_rows = min(estimated_rows, analysis.limit_value)
                logger.debug(f"Applied LIMIT {analysis.limit_value}, estimated rows now: {estimated_rows:,}")

            analysis.estimated_result_rows = estimated_rows

            # 8. Select execution strategy
            analysis.strategy = self._select_strategy(analysis)

            # Log strategy decision with reasoning
            strategy_reason = self._get_strategy_reason(analysis)
            logger.info(
                "Execution strategy selected",
                strategy=analysis.strategy.value,
                reason=strategy_reason,
                estimated_result_rows=f"{analysis.estimated_result_rows:,}",
                has_joins=analysis.has_joins,
                threshold_direct=f"{PANDAS_MAX_ROWS:,}",
                threshold_federated=f"{FEDERATION_THRESHOLD:,}"
            )

            # 9. Add warnings for large queries
            self._add_warnings(analysis)

            # Capture final metrics
            mem_end = tracemalloc.get_traced_memory()[0]
            tracemalloc.stop()
            end_time = time.perf_counter()

            analysis.analysis_time_ms = (end_time - start_time) * 1000
            analysis.memory_used_mb = (mem_end - mem_start) / 1024 / 1024

            logger.info(
                "Query analysis complete",
                tables=analysis.tables,
                has_joins=analysis.has_joins,
                largest_table=analysis.largest_table,
                total_rows=f"{analysis.total_estimated_rows:,}",
                estimated_result=f"{analysis.estimated_result_rows:,}",
                has_aggregation=analysis.has_aggregation,
                has_filters=analysis.has_filters,
                strategy=analysis.strategy.value,
                supports_pagination=analysis.supports_pagination,
                analysis_time_ms=f"{analysis.analysis_time_ms:.2f}",
                memory_used_mb=f"{analysis.memory_used_mb:.3f}"
            )

            return analysis

        except ValueError:
            # Re-raise ValueError (includes fail-fast for unknown table sizes)
            # Stop tracemalloc if still running
            try:
                tracemalloc.stop()
            except:
                pass
            raise
        except Exception as e:
            # Stop tracemalloc if still running
            try:
                tracemalloc.stop()
            except:
                pass

            logger.warning(
                "Query analysis failed",
                error=str(e),
                sql_preview=sql[:100] if sql else "empty",
                exc_info=True
            )
            analysis.warnings.append(f"Analysis failed: {str(e)}")
            return analysis

    def _get_strategy_reason(self, analysis: QueryAnalysis) -> str:
        """Get human-readable reason for strategy selection."""
        # Check very large tables first (requires async)
        if analysis.largest_table_rows >= VERY_LARGE_TABLE_THRESHOLD:
            return f"Very large source table ({analysis.largest_table_rows:,} rows) - async background execution"
        elif analysis.has_aggregation:
            return "Aggregation query - efficient execution on database"
        elif analysis.estimated_result_rows < PANDAS_MAX_ROWS:
            return f"Small result set ({analysis.estimated_result_rows:,} < {PANDAS_MAX_ROWS:,})"
        elif analysis.estimated_result_rows < FEDERATION_THRESHOLD:
            return f"Medium result set ({analysis.estimated_result_rows:,} rows) - pushdown applied"
        else:
            return f"Large result set ({analysis.estimated_result_rows:,} >= {FEDERATION_THRESHOLD:,}) - federation required"

    def optimize_query(self, sql: str, dialect: str = "snowflake") -> Tuple[str, QueryAnalysis]:
        """
        Analyze and optimize a query for execution.

        Applies SQL transformations:
        1. CTE conversion for repeated subqueries
        2. COUNT(*) optimization for non-DISTINCT counts

        NOTE: Does NOT add auto LIMIT - federation handles large result sets.

        Returns:
            Tuple of (optimized_sql, analysis)
        """
        analysis = self.analyze_query(sql, dialect)
        optimized_sql = sql
        optimizations_applied = []

        try:
            # Parse the SQL for transformation
            parsed = parse_one(sql, read=dialect)

            # Apply CTE conversion for repeated subqueries
            cte_result = self._optimize_cte_conversion(parsed, dialect)
            if cte_result:
                parsed = cte_result
                optimizations_applied.append("Converted repeated subqueries to CTEs")
                logger.info("Applied CTE optimization for repeated subqueries")

            # Apply aggregation optimization (COUNT column -> COUNT(*))
            agg_result = self._optimize_aggregations(parsed)
            if agg_result:
                parsed = agg_result
                optimizations_applied.append("Optimized COUNT functions")
                logger.info("Applied COUNT optimization")

            # Generate optimized SQL if any transformations applied
            if optimizations_applied:
                optimized_sql = parsed.sql(dialect=dialect)
                analysis.optimized_sql = optimized_sql
                logger.info(
                    "SQL transformations applied",
                    optimizations=optimizations_applied,
                    original_preview=sql[:100],
                    optimized_preview=optimized_sql[:100]
                )
        except Exception as e:
            logger.warning(f"SQL transformation failed, using original query: {e}")
            # Fall through to use original or pushdown-optimized SQL

        # If pushdown produced optimized SQL and no other optimizations, use it
        if analysis.optimized_sql:
            return analysis.optimized_sql, analysis

        return optimized_sql if optimizations_applied else sql, analysis

    def _optimize_cte_conversion(
        self,
        parsed: exp.Expression,
        dialect: str = "snowflake"
    ) -> Optional[exp.Expression]:
        """
        Convert repeated subqueries to CTEs using sqlglot.

        This optimization reduces redundant computation when the same
        subquery appears multiple times in a query.

        Args:
            parsed: Parsed SQL expression
            dialect: SQL dialect for generation

        Returns:
            Optimized expression with CTEs, or None if no optimization needed
        """
        try:
            # Find all subqueries
            subqueries = list(parsed.find_all(exp.Subquery))
            if len(subqueries) < 2:
                return None

            # Group subqueries by their SQL representation
            subquery_sql_map: Dict[str, List[exp.Subquery]] = {}
            for sq in subqueries:
                # Generate SQL for comparison (normalized)
                sq_sql = sq.sql(dialect=dialect)
                if sq_sql not in subquery_sql_map:
                    subquery_sql_map[sq_sql] = []
                subquery_sql_map[sq_sql].append(sq)

            # Find repeated subqueries (appear more than once)
            repeated = {sql: sqs for sql, sqs in subquery_sql_map.items() if len(sqs) > 1}
            if not repeated:
                return None

            # Create CTEs for repeated subqueries
            cte_counter = 1
            ctes = []
            replacements = {}

            for sq_sql, subquery_list in repeated.items():
                cte_name = f"cte_{cte_counter}"
                cte_counter += 1

                # Get the inner select from first subquery
                first_sq = subquery_list[0]
                inner_select = first_sq.this if first_sq.this else first_sq

                # Create CTE
                cte = exp.CTE(
                    this=inner_select.copy(),
                    alias=exp.TableAlias(this=exp.to_identifier(cte_name))
                )
                ctes.append(cte)

                # Map all instances to replacement
                for sq in subquery_list:
                    replacements[id(sq)] = exp.Table(this=exp.to_identifier(cte_name))

            if not ctes:
                return None

            # Clone and modify the parsed expression
            result = parsed.copy()

            # Replace subqueries with CTE references
            for sq in result.find_all(exp.Subquery):
                original_id = None
                # Find matching original subquery by SQL content
                sq_sql = sq.sql(dialect=dialect)
                for orig_sql, orig_list in repeated.items():
                    if sq_sql == orig_sql:
                        original_id = id(orig_list[0])
                        break

                if original_id and original_id in replacements:
                    # Replace with table reference
                    sq.replace(replacements[original_id].copy())

            # Add WITH clause
            existing_with = result.find(exp.With)
            if existing_with:
                # Extend existing WITH
                for cte in ctes:
                    existing_with.append("expressions", cte)
            else:
                # Create new WITH clause
                with_clause = exp.With(expressions=ctes)
                # For SELECT statements, prepend WITH
                if isinstance(result, exp.Select):
                    result.set("with", with_clause)

            logger.debug(
                "CTE conversion completed",
                repeated_subqueries=len(repeated),
                ctes_created=len(ctes)
            )

            return result

        except Exception as e:
            logger.debug(f"CTE conversion failed: {e}")
            return None

    def _optimize_aggregations(self, parsed: exp.Expression) -> Optional[exp.Expression]:
        """
        Optimize aggregation functions using sqlglot.

        Optimizations:
        - COUNT(column) -> COUNT(*) when not DISTINCT (more efficient)

        NOTE: Does NOT add auto LIMIT. Federation handles large result sets.

        Args:
            parsed: Parsed SQL expression

        Returns:
            Optimized expression, or None if no optimization needed
        """
        try:
            optimized = False
            result = parsed.copy()

            # Find all COUNT expressions
            for count_expr in result.find_all(exp.Count):
                # Skip COUNT(*) - already optimal
                if isinstance(count_expr.this, exp.Star):
                    continue

                # Skip COUNT(DISTINCT ...) - semantically different
                if count_expr.args.get("distinct"):
                    continue

                # COUNT(column) can be replaced with COUNT(*) if column is not nullable
                # For safety, we only replace simple column references
                if isinstance(count_expr.this, (exp.Column, exp.Identifier)):
                    # Replace with COUNT(*)
                    count_expr.set("this", exp.Star())
                    optimized = True
                    logger.debug(f"Replaced COUNT(column) with COUNT(*)")

            return result if optimized else None

        except Exception as e:
            logger.debug(f"Aggregation optimization failed: {e}")
            return None

    def _extract_table_names(self, parsed: exp.Expression) -> List[str]:
        """Extract all table names from parsed SQL."""
        tables = []
        for table_expr in parsed.find_all(exp.Table):
            tables.append(table_expr.name.upper())
        return list(set(tables))

    def _get_table_row_count(self, table_name: str) -> Optional[int]:
        """Get row count from Jena or Weaviate."""
        # Try Jena first
        if self.jena_resolver:
            try:
                row_count = self.jena_resolver.get_table_row_count(table_name)
                if row_count:
                    logger.debug(f"Jena row count for {table_name}: {row_count:,}")
                    return row_count
            except Exception as e:
                logger.debug(f"Jena lookup failed for {table_name}: {e}")

        # Fall back to Weaviate
        if self.weaviate_client:
            try:
                result = self.weaviate_client.get_table_by_name(
                    table_name,
                    organization_id=self.organization_id
                )
                if result and result.get("row_count"):
                    logger.debug(f"Weaviate row count for {table_name}: {result['row_count']:,}")
                    return result["row_count"]
            except Exception as e:
                logger.debug(f"Weaviate lookup failed for {table_name}: {e}")

        return None

    def _has_aggregation(self, parsed: exp.Expression) -> bool:
        """Check for GROUP BY or aggregate functions."""
        if parsed.find(exp.Group):
            return True
        for _ in parsed.find_all((exp.Sum, exp.Count, exp.Avg, exp.Min, exp.Max)):
            return True
        return False

    def _has_limit(self, parsed: exp.Expression) -> bool:
        """Check for LIMIT clause."""
        return parsed.find(exp.Limit) is not None

    def _has_filters(self, parsed: exp.Expression) -> bool:
        """Check for WHERE clause."""
        return parsed.find(exp.Where) is not None

    def _extract_limit_value(self, parsed: exp.Expression) -> Optional[int]:
        """Extract LIMIT value if present."""
        limit_expr = parsed.find(exp.Limit)
        if limit_expr and limit_expr.expression:
            try:
                return int(str(limit_expr.expression))
            except ValueError:
                pass
        return None

    def _extract_joins(self, parsed: exp.Expression) -> List[JoinInfo]:
        """Extract JOIN information from parsed SQL."""
        joins = []
        for join_expr in parsed.find_all(exp.Join):
            try:
                # Get join type
                join_type = "INNER"  # default
                if join_expr.kind:
                    join_type = join_expr.kind.upper()
                elif join_expr.side:
                    join_type = join_expr.side.upper()

                # Get right table
                right_table = ""
                if join_expr.this and isinstance(join_expr.this, exp.Table):
                    right_table = join_expr.this.name.upper()

                # Get join columns from ON clause
                join_columns = []
                on_clause = join_expr.args.get("on")
                if on_clause:
                    # Extract column pairs from equality conditions
                    for eq_expr in on_clause.find_all(exp.EQ):
                        left_col = str(eq_expr.left).split(".")[-1].upper() if eq_expr.left else ""
                        right_col = str(eq_expr.right).split(".")[-1].upper() if eq_expr.right else ""
                        if left_col and right_col:
                            join_columns.append((left_col, right_col))

                # Get left table (parent FROM clause table)
                left_table = ""
                from_clause = parsed.find(exp.From)
                if from_clause and from_clause.this and isinstance(from_clause.this, exp.Table):
                    left_table = from_clause.this.name.upper()

                if right_table:
                    joins.append(JoinInfo(
                        left_table=left_table,
                        right_table=right_table,
                        join_type=join_type,
                        join_columns=join_columns,
                        estimated_selectivity=self._get_join_selectivity(join_type, join_columns)
                    ))
            except Exception as e:
                logger.debug(f"Failed to extract JOIN info: {e}")
                continue

        return joins

    def _get_join_selectivity(self, join_type: str, join_columns: List[Tuple[str, str]]) -> float:
        """
        Estimate JOIN selectivity (reduction factor).

        Returns a factor 0-1 where lower = more selective (fewer rows).
        """
        # Default selectivities by join type
        if join_type == "INNER":
            # Inner join typically reduces rows
            base_selectivity = 0.8
        elif join_type in ("LEFT", "RIGHT"):
            # Outer join preserves base table rows
            base_selectivity = 1.0
        elif join_type == "FULL":
            base_selectivity = 1.2  # Can increase rows
        elif join_type == "CROSS":
            base_selectivity = 10.0  # Cartesian product
        else:
            base_selectivity = 1.0

        # If we have Jena, try to get actual selectivity
        if self.jena_resolver and join_columns:
            try:
                # Look up foreign key relationship selectivity
                for left_col, right_col in join_columns:
                    selectivity = self.jena_resolver.get_join_selectivity(left_col, right_col)
                    if selectivity:
                        return selectivity
            except Exception:
                pass

        return base_selectivity

    def _estimate_join_rows(self, analysis: QueryAnalysis) -> int:
        """
        Estimate result rows after JOINs.

        For JOINs between fact and dimension tables (common in analytics):
        - Fact table rows are typically preserved (1:1 or N:1 with dimension)
        - Result ≈ largest table rows (fact table)

        For many-to-many JOINs:
        - Result can be larger than either table
        """
        if not analysis.joins:
            return analysis.largest_table_rows

        estimated = analysis.largest_table_rows

        for join_info in analysis.joins:
            # Apply selectivity factor
            estimated = int(estimated * join_info.estimated_selectivity)

            # For dimension table JOINs, don't increase beyond fact table
            # (common pattern: STORE_SALES JOIN CUSTOMER)
            right_rows = analysis.table_row_counts.get(join_info.right_table, 0)
            if right_rows > 0 and right_rows < analysis.largest_table_rows * 0.1:
                # Small dimension table - likely 1:1 or N:1, don't expand
                estimated = min(estimated, analysis.largest_table_rows)

        return max(estimated, 1)

    def _extract_group_by_columns(self, parsed: exp.Expression) -> List[str]:
        """Extract GROUP BY column names."""
        columns = []
        group_clause = parsed.find(exp.Group)
        if group_clause:
            for expr in group_clause.expressions:
                col_name = str(expr).split(".")[-1].upper()
                columns.append(col_name)
        return columns

    def _extract_aggregation_columns(self, parsed: exp.Expression) -> List[str]:
        """Extract columns used in aggregate functions (SUM, COUNT, AVG, etc.)."""
        agg_columns = []
        agg_types = (exp.Sum, exp.Count, exp.Avg, exp.Min, exp.Max)

        for agg_expr in parsed.find_all(agg_types):
            # Get the column inside the aggregate function
            if agg_expr.this:
                col_expr = agg_expr.this
                # Handle COUNT(*) specially
                if isinstance(col_expr, exp.Star):
                    agg_columns.append("*")
                else:
                    col_name = str(col_expr).split(".")[-1].upper()
                    agg_columns.append(col_name)

        return list(set(agg_columns))  # Deduplicate

    def _select_strategy(self, analysis: QueryAnalysis) -> ExecutionStrategy:
        """Select execution strategy based on data size and query characteristics."""
        estimated = analysis.estimated_result_rows

        # Very large source tables (>1B rows) MUST use federation
        # because scanning billions of rows requires S3 staging regardless of output size
        if analysis.largest_table_rows >= VERY_LARGE_TABLE_THRESHOLD:
            # Set async flag - this query should run in background
            analysis.requires_async = True
            analysis.warnings.append(
                f"Query scans ~{analysis.largest_table_rows:,} rows. "
                "Using S3 federation with background execution - poll for results."
            )
            # IMPORTANT: Use FEDERATED, not OPTIMIZED - these tables are too large
            # for direct execution even with pushdown optimization
            return ExecutionStrategy.FEDERATED

        # Aggregation queries on normal-sized tables are efficient
        if analysis.has_aggregation:
            return ExecutionStrategy.DIRECT

        # Small tables - execute directly
        if estimated < PANDAS_MAX_ROWS:
            return ExecutionStrategy.DIRECT

        # Medium tables - apply pushdown
        if estimated < FEDERATION_THRESHOLD:
            return ExecutionStrategy.OPTIMIZED

        # Large tables (>100M rows) - use federation
        return ExecutionStrategy.FEDERATED

    def _add_warnings(self, analysis: QueryAnalysis):
        """Add warnings for potentially slow queries."""
        if analysis.strategy == ExecutionStrategy.FEDERATED:
            analysis.warnings.append(
                f"Query scans ~{analysis.total_estimated_rows:,} rows. "
                "Using optimized execution path."
            )
        elif analysis.strategy == ExecutionStrategy.OPTIMIZED:
            analysis.warnings.append(
                f"Query involves ~{analysis.total_estimated_rows:,} rows. "
                "Pushdown optimization applied."
            )

    def generate_paginated_sql(
        self,
        sql: str,
        page: int = 1,
        page_size: int = 1000,
        dialect: str = "snowflake"
    ) -> Tuple[str, str]:
        """
        Generate paginated SQL and count SQL for row-level queries.

        Args:
            sql: Original SQL query
            page: Page number (1-indexed)
            page_size: Number of rows per page
            dialect: SQL dialect for parsing

        Returns:
            Tuple of (paginated_sql, count_sql)
        """
        try:
            parsed = parse_one(sql, read=dialect)

            # Generate count SQL (wrap original in subquery)
            count_sql = f"SELECT COUNT(*) as total_count FROM ({sql}) AS _count_subquery"

            # Calculate offset
            offset = (page - 1) * page_size

            # Check if query already has LIMIT
            existing_limit = parsed.find(exp.Limit)
            if existing_limit:
                # Query already has LIMIT - use as-is for pagination
                logger.debug("Query already has LIMIT clause, using as pagination boundary")
                return sql, count_sql

            # Add LIMIT and OFFSET
            # Different dialects have different syntax
            if dialect.lower() in ("bigquery", "postgres", "postgresql", "snowflake", "redshift"):
                paginated_sql = f"{sql}\nLIMIT {page_size} OFFSET {offset}"
            elif dialect.lower() == "databricks":
                paginated_sql = f"{sql}\nLIMIT {page_size} OFFSET {offset}"
            else:
                # Default ANSI SQL
                paginated_sql = f"{sql}\nLIMIT {page_size} OFFSET {offset}"

            logger.info(
                "Generated paginated SQL",
                page=page,
                page_size=page_size,
                offset=offset,
                dialect=dialect
            )

            return paginated_sql, count_sql

        except Exception as e:
            logger.warning(f"Failed to generate paginated SQL: {e}")
            # Return original SQL with simple pagination
            offset = (page - 1) * page_size
            return f"{sql}\nLIMIT {page_size} OFFSET {offset}", f"SELECT COUNT(*) FROM ({sql}) AS _c"

    def get_pagination_metadata(
        self,
        total_count: int,
        page: int,
        page_size: int
    ) -> Dict[str, Any]:
        """
        Generate pagination metadata for response.

        Args:
            total_count: Total number of rows
            page: Current page number (1-indexed)
            page_size: Rows per page

        Returns:
            Pagination metadata dict
        """
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1

        return {
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next_page": has_next,
            "has_previous_page": has_prev,
            "start_row": (page - 1) * page_size + 1,
            "end_row": min(page * page_size, total_count),
        }


def get_dialect_for_database(database_type: str) -> str:
    """Map database type to sqlglot dialect."""
    dialect_map = {
        "snowflake": "snowflake",
        "bigquery": "bigquery",
        "postgresql": "postgres",
        "postgres": "postgres",
        "redshift": "redshift",
        "databricks": "databricks",
    }
    return dialect_map.get(database_type.lower(), "snowflake")
