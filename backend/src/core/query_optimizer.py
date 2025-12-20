"""
DEPRECATED: This module is deprecated and will be removed in a future version.

Use SingleDatabaseQueryOptimizer from single_db_query_optimizer.py instead.

The functionality from this module has been consolidated:
- CTE conversion: Moved to SingleDatabaseQueryOptimizer._optimize_cte_conversion()
- COUNT(*) optimization: Moved to SingleDatabaseQueryOptimizer._optimize_aggregations()
- Auto LIMIT: REMOVED (federation handles large result sets appropriately)
- BigQuery cost estimation: Use connector.validate_query() directly

SingleDatabaseQueryOptimizer provides:
- Multi-database support (BigQuery, Snowflake, PostgreSQL, Redshift, Databricks)
- Modern SQL parsing via sqlglot (not regex)
- Execution strategy selection (DIRECT/OPTIMIZED/FEDERATED)
- Row count estimation from Jena/Weaviate metadata
- Proper pagination support

Migration:
    # Old usage:
    # from src.core.query_optimizer import QueryOptimizer
    # optimizer = QueryOptimizer()
    # result = optimizer.optimize_query(sql)

    # New usage:
    from src.core.single_db_query_optimizer import (
        SingleDatabaseQueryOptimizer,
        get_dialect_for_database
    )
    optimizer = SingleDatabaseQueryOptimizer(database_type="snowflake")
    optimized_sql, analysis = optimizer.optimize_query(sql, dialect="snowflake")
"""
from typing import Dict, Any, List, Tuple, Optional
import re
import sqlparse
from sqlparse.sql import Token, TokenList, Identifier, IdentifierList
import structlog
from src.db.bigquery import BigQueryClient
from src.core.llm_client import LLMClient

logger = structlog.get_logger()


class QueryOptimizer:
    """
    DEPRECATED: Optimizer for SQL queries to improve performance and reduce costs.

    This class is deprecated. Use SingleDatabaseQueryOptimizer instead.
    See module docstring for migration instructions.
    """

    def __init__(self):
        self.bq_client = BigQueryClient()
        self.llm_client = LLMClient()
        self.optimization_rules = [
            self._optimize_repeated_subqueries,
            self._suggest_partitioning,
            self._optimize_joins,
            self._suggest_materialized_views,
            self._optimize_aggregations,
            self._add_appropriate_limits
        ]
    
    def analyze_query(self, sql: str) -> Dict[str, Any]:
        """Analyze a query for optimization opportunities."""
        try:
            # Parse the SQL
            parsed = sqlparse.parse(sql)[0]
            
            # Extract query components
            tables = self._extract_tables(parsed)
            joins = self._extract_joins(sql)
            aggregations = self._extract_aggregations(sql)
            subqueries = self._extract_subqueries(sql)
            
            # Analyze complexity
            complexity_score = self._calculate_complexity(
                tables=len(tables),
                joins=len(joins),
                aggregations=len(aggregations),
                subqueries=len(subqueries)
            )
            
            return {
                "tables": tables,
                "joins": joins,
                "aggregations": aggregations,
                "subqueries": subqueries,
                "complexity_score": complexity_score,
                "has_repeated_subqueries": len(subqueries) > 1,
                "needs_cte": complexity_score > 5 or len(subqueries) > 1
            }
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {}
    
    def optimize_query(self, sql: str, query_stats: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply optimization rules to improve query performance."""
        try:
            analysis = self.analyze_query(sql)
            optimized_sql = sql
            optimizations_applied = []
            suggestions = []
            
            # Apply each optimization rule
            for rule in self.optimization_rules:
                result = rule(optimized_sql, analysis)
                if result["applied"]:
                    optimized_sql = result["sql"]
                    optimizations_applied.append(result["description"])
                if result.get("suggestions"):
                    suggestions.extend(result["suggestions"])
            
            # Calculate improvement estimates
            original_validation = self.bq_client.validate_query(sql)
            optimized_validation = self.bq_client.validate_query(optimized_sql)
            
            improvement = {
                "bytes_saved": 0,
                "cost_saved": 0,
                "percentage_improvement": 0
            }
            
            if original_validation["valid"] and optimized_validation["valid"]:
                bytes_saved = original_validation.get("total_bytes_processed", 0) - \
                             optimized_validation.get("total_bytes_processed", 0)
                cost_saved = original_validation.get("estimated_cost_usd", 0) - \
                            optimized_validation.get("estimated_cost_usd", 0)
                
                if original_validation.get("total_bytes_processed", 0) > 0:
                    percentage = (bytes_saved / original_validation["total_bytes_processed"]) * 100
                else:
                    percentage = 0
                
                improvement = {
                    "bytes_saved": bytes_saved,
                    "cost_saved": cost_saved,
                    "percentage_improvement": percentage
                }
            
            return {
                "original_sql": sql,
                "optimized_sql": optimized_sql,
                "optimizations_applied": optimizations_applied,
                "suggestions": suggestions,
                "improvement": improvement,
                "analysis": analysis,
                "original_validation": original_validation,
                "optimized_validation": optimized_validation
            }
            
        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return {
                "original_sql": sql,
                "optimized_sql": sql,
                "error": str(e)
            }
    
    def _optimize_repeated_subqueries(self, sql: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Convert repeated subqueries to CTEs."""
        if not analysis.get("has_repeated_subqueries"):
            return {"applied": False, "sql": sql}
        
        try:
            # Find repeated subquery patterns
            subquery_pattern = r'\((SELECT[^)]+)\)'
            subqueries = re.findall(subquery_pattern, sql, re.IGNORECASE | re.DOTALL)
            
            if len(subqueries) <= 1:
                return {"applied": False, "sql": sql}
            
            # Count occurrences
            subquery_counts = {}
            for sq in subqueries:
                normalized = ' '.join(sq.split())
                subquery_counts[normalized] = subquery_counts.get(normalized, 0) + 1
            
            # Convert repeated subqueries to CTEs
            ctes = []
            cte_replacements = {}
            cte_counter = 1
            
            for sq, count in subquery_counts.items():
                if count > 1:
                    cte_name = f"cte_{cte_counter}"
                    ctes.append(f"{cte_name} AS ({sq})")
                    cte_replacements[sq] = cte_name
                    cte_counter += 1
            
            if not ctes:
                return {"applied": False, "sql": sql}
            
            # Build new query with CTEs
            optimized_sql = f"WITH {', '.join(ctes)}\n{sql}"
            
            # Replace subqueries with CTE references
            for sq, cte_name in cte_replacements.items():
                optimized_sql = optimized_sql.replace(f"({sq})", cte_name)
            
            return {
                "applied": True,
                "sql": optimized_sql,
                "description": f"Converted {len(ctes)} repeated subqueries to CTEs"
            }
            
        except Exception as e:
            logger.warning(f"CTE optimization failed: {e}")
            return {"applied": False, "sql": sql}
    
    def _suggest_partitioning(self, sql: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest partitioning strategies."""
        suggestions = []
        
        # Look for date filters
        date_pattern = r'WHERE.*?(date|timestamp|created|updated).*?([<>=]+|BETWEEN)'
        if re.search(date_pattern, sql, re.IGNORECASE):
            suggestions.append("Consider partitioning tables by date column for better performance")
        
        # Look for large table scans without filters
        if len(analysis.get("tables", [])) > 0 and "WHERE" not in sql.upper():
            suggestions.append("Add WHERE clauses to limit data scanned")
        
        return {
            "applied": False,
            "sql": sql,
            "suggestions": suggestions
        }
    
    def _optimize_joins(self, sql: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize JOIN operations."""
        try:
            # Check for cross joins
            if "CROSS JOIN" in sql.upper():
                return {
                    "applied": False,
                    "sql": sql,
                    "suggestions": ["Avoid CROSS JOIN if possible - consider using INNER JOIN with conditions"]
                }
            
            # Suggest join order optimization for multiple joins
            join_count = len(analysis.get("joins", []))
            if join_count > 2:
                return {
                    "applied": False,
                    "sql": sql,
                    "suggestions": ["With multiple joins, ensure smaller tables are joined first"]
                }
            
            return {"applied": False, "sql": sql}
            
        except Exception as e:
            logger.warning(f"Join optimization failed: {e}")
            return {"applied": False, "sql": sql}
    
    def _suggest_materialized_views(self, sql: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest materialized views for complex queries."""
        suggestions = []
        
        complexity = analysis.get("complexity_score", 0)
        
        # High complexity queries benefit from materialized views
        if complexity > 8:
            suggestions.append("This complex query could benefit from a materialized view")
        
        # Queries with many aggregations
        if len(analysis.get("aggregations", [])) > 3:
            suggestions.append("Consider creating a pre-aggregated materialized view")
        
        # Generate materialized view suggestion
        if suggestions:
            mv_sql = self._generate_materialized_view(sql, analysis)
            if mv_sql:
                suggestions.append(f"Example materialized view:\n{mv_sql}")
        
        return {
            "applied": False,
            "sql": sql,
            "suggestions": suggestions
        }
    
    def _optimize_aggregations(self, sql: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize aggregation functions."""
        try:
            optimized_sql = sql
            applied = False
            
            # Replace COUNT(column) with COUNT(*) where appropriate
            count_pattern = r'COUNT\(\s*([^*\s)]+)\s*\)'
            matches = re.findall(count_pattern, sql, re.IGNORECASE)
            
            for match in matches:
                # If counting non-nullable columns, COUNT(*) is more efficient
                if not re.search(r'DISTINCT', match, re.IGNORECASE):
                    optimized_sql = re.sub(
                        rf'COUNT\(\s*{re.escape(match)}\s*\)',
                        'COUNT(*)',
                        optimized_sql,
                        flags=re.IGNORECASE
                    )
                    applied = True
            
            # Suggest APPROX functions for large datasets
            suggestions = []
            if re.search(r'COUNT\s*\(\s*DISTINCT', sql, re.IGNORECASE):
                suggestions.append("Consider using APPROX_COUNT_DISTINCT for large datasets")
            
            return {
                "applied": applied,
                "sql": optimized_sql,
                "description": "Optimized aggregation functions" if applied else None,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.warning(f"Aggregation optimization failed: {e}")
            return {"applied": False, "sql": sql}
    
    def _add_appropriate_limits(self, sql: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Add LIMIT clauses where appropriate."""
        try:
            # Don't add LIMIT if it already exists
            if re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
                return {"applied": False, "sql": sql}
            
            # Don't add LIMIT to queries with aggregations (they usually return few rows)
            if analysis.get("aggregations"):
                return {"applied": False, "sql": sql}
            
            # Add LIMIT for exploratory queries without aggregations
            if not re.search(r'\b(GROUP BY|HAVING|COUNT|SUM|AVG|MAX|MIN)\b', sql, re.IGNORECASE):
                optimized_sql = sql.rstrip().rstrip(';') + "\nLIMIT 1000"
                return {
                    "applied": True,
                    "sql": optimized_sql,
                    "description": "Added LIMIT clause for exploratory query"
                }
            
            return {"applied": False, "sql": sql}
            
        except Exception as e:
            logger.warning(f"LIMIT optimization failed: {e}")
            return {"applied": False, "sql": sql}
    
    def _extract_tables(self, parsed) -> List[str]:
        """Extract table names from parsed SQL."""
        tables = []
        try:
            for token in parsed.tokens:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.append(str(identifier))
                elif isinstance(token, Identifier):
                    tables.append(str(token))
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
        return tables
    
    def _extract_joins(self, sql: str) -> List[str]:
        """Extract JOIN operations from SQL."""
        join_pattern = r'(INNER|LEFT|RIGHT|FULL|CROSS)\s+JOIN'
        return re.findall(join_pattern, sql, re.IGNORECASE)
    
    def _extract_aggregations(self, sql: str) -> List[str]:
        """Extract aggregation functions from SQL."""
        agg_pattern = r'(COUNT|SUM|AVG|MAX|MIN|STDDEV|VARIANCE)\s*\('
        return re.findall(agg_pattern, sql, re.IGNORECASE)
    
    def _extract_subqueries(self, sql: str) -> List[str]:
        """Extract subqueries from SQL."""
        subquery_pattern = r'\((SELECT[^)]+)\)'
        return re.findall(subquery_pattern, sql, re.IGNORECASE | re.DOTALL)
    
    def _calculate_complexity(self, tables: int, joins: int, aggregations: int, subqueries: int) -> int:
        """Calculate query complexity score."""
        return tables + (joins * 2) + aggregations + (subqueries * 3)
    
    def _generate_materialized_view(self, sql: str, analysis: Dict[str, Any]) -> Optional[str]:
        """Generate a materialized view suggestion."""
        try:
            # Extract main query structure
            base_name = "mv_" + "_".join(analysis.get("tables", ["query"])[:2]).lower()
            
            mv_sql = f"""CREATE MATERIALIZED VIEW `{self.bq_client.project_id}.{self.bq_client.dataset_id}.{base_name}`
PARTITION BY DATE(created_at)  -- Adjust based on your date column
CLUSTER BY category  -- Adjust based on common filter columns
AS
{sql}"""
            
            return mv_sql
        except Exception as e:
            logger.warning(f"Materialized view generation failed: {e}")
            return None