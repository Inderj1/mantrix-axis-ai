"""
Query Pushdown Optimizer

Optimizes cross-database queries by pushing filters (WHERE, LIMIT, SELECT)
to source databases before data transfer. This significantly reduces:
- Network data transfer
- Memory usage
- Query execution time

Example:
    Instead of:
        1. Fetch 1M rows from PostgreSQL
        2. Filter to 10K rows locally
        3. JOIN with BigQuery

    Optimized:
        1. Push WHERE filter to PostgreSQL
        2. Fetch only 10K rows
        3. JOIN with BigQuery
"""
import sqlglot
from sqlglot import exp, parse_one
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger()


@dataclass
class PushdownAnalysis:
    """Analysis of what can be pushed down to source database."""
    can_pushdown_filters: bool = False
    can_pushdown_projections: bool = False
    can_pushdown_limit: bool = False

    # Filters that can be pushed down
    pushdown_filters: List[str] = field(default_factory=list)

    # Columns needed (for projection pushdown)
    required_columns: Set[str] = field(default_factory=set)

    # LIMIT clause if present
    limit_value: Optional[int] = None

    # Estimated reduction in data transfer
    estimated_reduction_percent: float = 0.0

    # Optimized SQL for source database
    optimized_sql: Optional[str] = None

    warnings: List[str] = field(default_factory=list)


@dataclass
class TableFilter:
    """Filter that applies to a specific table."""
    table_name: str
    table_alias: Optional[str]
    column: str
    operator: str  # =, >, <, >=, <=, LIKE, IN, etc.
    value: Any
    sql_text: str  # Original SQL text of the filter


class QueryPushdownOptimizer:
    """
    Optimize cross-database queries by pushing operations to source databases.

    Strategies:
    1. Filter Pushdown: Push WHERE clauses to source
    2. Projection Pushdown: SELECT only needed columns
    3. Limit Pushdown: Apply LIMIT at source
    4. Aggregation Pushdown: Push GROUP BY/aggregations when possible
    """

    def __init__(self):
        """Initialize the query pushdown optimizer."""
        logger.info("QueryPushdownOptimizer initialized")

    def analyze_pushdown_opportunities(
        self,
        sql: str,
        table_name: str,
        table_alias: Optional[str] = None
    ) -> PushdownAnalysis:
        """
        Analyze a query to identify pushdown opportunities for a specific table.

        Args:
            sql: The full SQL query
            table_name: Name of the table to optimize
            table_alias: Alias used for the table in the query

        Returns:
            PushdownAnalysis with optimization opportunities
        """
        logger.info(
            "Analyzing pushdown opportunities",
            table=table_name,
            alias=table_alias
        )

        try:
            # Parse SQL
            parsed = parse_one(sql, read='bigquery')

            analysis = PushdownAnalysis()

            # 1. Analyze filters (WHERE clause)
            filters = self._extract_table_filters(parsed, table_name, table_alias)
            if filters:
                analysis.can_pushdown_filters = True
                analysis.pushdown_filters = [f.sql_text for f in filters]
                logger.debug(f"Found {len(filters)} pushdown filters", filters=analysis.pushdown_filters)

            # 2. Analyze required columns (SELECT clause)
            required_cols = self._extract_required_columns(parsed, table_name, table_alias)
            if required_cols:
                analysis.can_pushdown_projections = True
                analysis.required_columns = required_cols
                logger.debug(f"Found {len(required_cols)} required columns", columns=list(required_cols))

            # 3. Analyze LIMIT clause
            limit = self._extract_limit(parsed)
            if limit:
                analysis.can_pushdown_limit = True
                analysis.limit_value = limit
                logger.debug(f"Found LIMIT clause", limit=limit)

            # 4. Extract full table reference (with schema if present)
            table_ref = self._extract_table_reference(parsed, table_name, table_alias)

            # 5. Estimate reduction
            analysis.estimated_reduction_percent = self._estimate_reduction(analysis)

            # 6. Generate optimized SQL
            analysis.optimized_sql = self._generate_optimized_query(
                table_ref or table_name,  # Use full table ref if available
                analysis
            )

            logger.info(
                "Pushdown analysis complete",
                table=table_name,
                can_pushdown_filters=analysis.can_pushdown_filters,
                can_pushdown_projections=analysis.can_pushdown_projections,
                estimated_reduction=f"{analysis.estimated_reduction_percent:.1f}%"
            )

            return analysis

        except Exception as e:
            logger.error("Failed to analyze pushdown opportunities", error=str(e))
            return PushdownAnalysis(
                warnings=[f"Analysis failed: {str(e)}"]
            )

    def _extract_table_filters(
        self,
        parsed_sql: exp.Expression,
        table_name: str,
        table_alias: Optional[str]
    ) -> List[TableFilter]:
        """Extract WHERE clause filters that apply to the given table."""
        filters = []

        # Find WHERE clause
        where_clause = parsed_sql.find(exp.Where)
        if not where_clause:
            return filters

        # Extract conditions
        conditions = self._flatten_conditions(where_clause.this)

        # Filter conditions that apply to our table
        table_identifier = table_alias or table_name

        for condition in conditions:
            # Check if condition references our table
            if self._condition_references_table(condition, table_identifier):
                filters.append(TableFilter(
                    table_name=table_name,
                    table_alias=table_alias,
                    column=self._extract_column_name(condition),
                    operator=self._extract_operator(condition),
                    value=self._extract_value(condition),
                    sql_text=str(condition)
                ))

        return filters

    def _flatten_conditions(self, expr: exp.Expression) -> List[exp.Expression]:
        """Flatten AND conditions into a list."""
        conditions = []

        if isinstance(expr, exp.And):
            # Recursively flatten AND conditions
            conditions.extend(self._flatten_conditions(expr.left))
            conditions.extend(self._flatten_conditions(expr.right))
        else:
            conditions.append(expr)

        return conditions

    def _condition_references_table(
        self,
        condition: exp.Expression,
        table_identifier: str
    ) -> bool:
        """Check if a condition references the given table."""
        # Look for column references
        for col in condition.find_all(exp.Column):
            if col.table and col.table == table_identifier:
                return True
            # If no table specified, assume it's our table (single table query)
            if not col.table:
                return True
        return False

    def _extract_column_name(self, condition: exp.Expression) -> str:
        """Extract column name from condition."""
        for col in condition.find_all(exp.Column):
            return col.name
        return "unknown"

    def _extract_operator(self, condition: exp.Expression) -> str:
        """Extract comparison operator from condition."""
        if isinstance(condition, exp.EQ):
            return "="
        elif isinstance(condition, exp.GT):
            return ">"
        elif isinstance(condition, exp.LT):
            return "<"
        elif isinstance(condition, exp.GTE):
            return ">="
        elif isinstance(condition, exp.LTE):
            return "<="
        elif isinstance(condition, exp.Like):
            return "LIKE"
        elif isinstance(condition, exp.In):
            return "IN"
        else:
            return str(type(condition).__name__)

    def _extract_value(self, condition: exp.Expression) -> Any:
        """Extract comparison value from condition."""
        # This is simplified - would need more robust handling
        return "value"

    def _extract_required_columns(
        self,
        parsed_sql: exp.Expression,
        table_name: str,
        table_alias: Optional[str]
    ) -> Set[str]:
        """Extract columns that are actually used from this table."""
        required_cols = set()
        table_identifier = table_alias or table_name

        # Get all columns referenced in the query for this table
        for col in parsed_sql.find_all(exp.Column):
            if col.table == table_identifier or (not col.table and table_alias):
                required_cols.add(col.name)

        return required_cols

    def _extract_limit(self, parsed_sql: exp.Expression) -> Optional[int]:
        """Extract LIMIT value if present."""
        limit_expr = parsed_sql.find(exp.Limit)
        if limit_expr and limit_expr.expression:
            try:
                return int(str(limit_expr.expression))
            except ValueError:
                return None
        return None

    def _extract_table_reference(
        self,
        parsed_sql: exp.Expression,
        table_name: str,
        table_alias: Optional[str]
    ) -> Optional[str]:
        """
        Extract the full table reference (including schema if present) from the query.

        Args:
            parsed_sql: Parsed SQL expression
            table_name: Table name to find
            table_alias: Alias used for the table

        Returns:
            Full table reference (e.g., "schema.table") or None
        """
        # Find all table references in FROM clause
        for table_expr in parsed_sql.find_all(exp.Table):
            # Check if this is our table (match by name or alias)
            if table_expr.name == table_name:
                # Build full reference
                parts = []
                if table_expr.catalog:
                    parts.append(table_expr.catalog)
                if table_expr.db:
                    parts.append(table_expr.db)
                parts.append(table_expr.name)
                return ".".join(parts)

        return None

    def _estimate_reduction(self, analysis: PushdownAnalysis) -> float:
        """
        Estimate percentage reduction in data transfer.

        Heuristics:
        - Each filter: ~50% reduction (assumes good selectivity)
        - Projection pushdown: ~30% reduction (assumes half columns needed)
        - LIMIT: Variable based on limit value
        """
        reduction = 0.0

        # Filter pushdown
        if analysis.can_pushdown_filters:
            # Each filter provides ~50% reduction (assumes good selectivity)
            # Multiple filters compound
            num_filters = len(analysis.pushdown_filters)
            filter_reduction = 1.0 - (0.5 ** num_filters)
            reduction += filter_reduction * 100

        # Projection pushdown (conservative estimate)
        if analysis.can_pushdown_projections and len(analysis.required_columns) > 0:
            # Assume projection reduces by 30% (conservative)
            reduction += 30 * (1 - reduction/100)

        # LIMIT pushdown
        if analysis.can_pushdown_limit and analysis.limit_value:
            # If limit is small (< 1000), assume 90% reduction
            if analysis.limit_value < 1000:
                limit_reduction = 90 * (1 - reduction/100)
                reduction += limit_reduction

        return min(reduction, 95.0)  # Cap at 95%

    def _generate_optimized_query(
        self,
        table_name: str,
        analysis: PushdownAnalysis
    ) -> str:
        """Generate optimized SQL for fetching from source database."""
        parts = []

        # SELECT clause
        if analysis.can_pushdown_projections and analysis.required_columns:
            columns = ", ".join(sorted(analysis.required_columns))
            parts.append(f"SELECT {columns}")
        else:
            parts.append("SELECT *")

        # FROM clause
        parts.append(f"FROM {table_name}")

        # WHERE clause
        if analysis.can_pushdown_filters and analysis.pushdown_filters:
            where_conditions = " AND ".join(analysis.pushdown_filters)
            parts.append(f"WHERE {where_conditions}")

        # LIMIT clause
        if analysis.can_pushdown_limit and analysis.limit_value:
            parts.append(f"LIMIT {analysis.limit_value}")

        return "\n".join(parts)

    def apply_pushdown_optimization(
        self,
        original_query: str,
        table_name: str,
        optimized_query: str
    ) -> str:
        """
        Apply pushdown optimization by replacing table reference with subquery.

        This is a placeholder - full implementation would need more sophisticated
        query rewriting.
        """
        # For now, just return the optimized query
        # In a full implementation, would replace the table reference in the
        # original query with a subquery using the optimized query
        return optimized_query
