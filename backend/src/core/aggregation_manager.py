"""
Aggregation Manager for pre-computed data caching.

Pre-computes and caches common aggregations for instant dashboard loading:
- Dimension rollups (GROUP BY aggregations)
- Time-series aggregations
- Frequently accessed metrics
"""

import json
import redis
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from src.config import settings
from src.db.connector_factory import get_connector

logger = structlog.get_logger()


class AggregationManager:
    """
    Pre-computes and caches aggregations for common dimensions.

    Features:
    - Automatic aggregation caching
    - Configurable TTL per aggregation type
    - Cache invalidation on data changes
    - Support for multiple aggregation functions
    """

    PREFIX = "agg:"
    DEFAULT_TTL = 3600  # 1 hour default
    TIME_SERIES_TTL = 1800  # 30 minutes for time-sensitive data
    DIMENSION_TTL = 7200  # 2 hours for dimension rollups

    # Supported aggregation functions
    AGG_FUNCTIONS = {
        "SUM": "SUM",
        "AVG": "AVG",
        "COUNT": "COUNT",
        "MIN": "MIN",
        "MAX": "MAX",
        "COUNT_DISTINCT": "COUNT(DISTINCT {})"
    }

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize with Redis connection."""
        try:
            if redis_url:
                self.redis = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=0,
                    decode_responses=True
                )
            self.redis.ping()
            self.enabled = True
            logger.info("AggregationManager connected to Redis")
        except Exception as e:
            logger.warning(f"AggregationManager: Redis not available, aggregation caching disabled: {e}")
            self.redis = None
            self.enabled = False

    def _cache_key(
        self,
        connector_id: str,
        table: str,
        dimension: str,
        measure: str,
        agg_func: str,
        filters: Optional[Dict] = None
    ) -> str:
        """Generate cache key for an aggregation."""
        # Include filters in key if present
        filter_hash = ""
        if filters:
            filter_str = json.dumps(filters, sort_keys=True)
            filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]

        key_parts = [self.PREFIX, connector_id, table, dimension, measure, agg_func]
        if filter_hash:
            key_parts.append(filter_hash)

        return ":".join(key_parts)

    def _build_agg_sql(
        self,
        table: str,
        dimension: str,
        measure: str,
        agg_func: str,
        filters: Optional[Dict] = None,
        order_by: str = "value",
        limit: Optional[int] = None
    ) -> str:
        """Build SQL for aggregation query."""
        # Handle COUNT DISTINCT specially
        if agg_func == "COUNT_DISTINCT":
            agg_expr = f"COUNT(DISTINCT {measure})"
        else:
            agg_expr = f"{agg_func}({measure})"

        sql = f"""
            SELECT {dimension}, {agg_expr} as value
            FROM {table}
        """

        # Add WHERE clause for filters
        if filters:
            where_clauses = []
            for col, val in filters.items():
                if isinstance(val, list):
                    # IN clause for multiple values
                    vals = ", ".join(f"'{v}'" for v in val)
                    where_clauses.append(f"{col} IN ({vals})")
                elif isinstance(val, dict):
                    # Range filter
                    if "min" in val:
                        where_clauses.append(f"{col} >= '{val['min']}'")
                    if "max" in val:
                        where_clauses.append(f"{col} <= '{val['max']}'")
                else:
                    where_clauses.append(f"{col} = '{val}'")

            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

        sql += f" GROUP BY {dimension}"

        # Order by value or dimension
        if order_by == "value":
            sql += " ORDER BY value DESC"
        else:
            sql += f" ORDER BY {dimension}"

        if limit:
            sql += f" LIMIT {limit}"

        return sql

    async def get_or_compute_aggregation(
        self,
        connector_id: str,
        table: str,
        dimension: str,
        measure: str,
        agg_func: str = "SUM",
        filters: Optional[Dict] = None,
        force_refresh: bool = False,
        limit: Optional[int] = 100
    ) -> Dict[str, Any]:
        """
        Get cached aggregation or compute and cache it.

        Args:
            connector_id: Database connector identifier
            table: Table name (can include schema)
            dimension: Column to group by
            measure: Column to aggregate
            agg_func: Aggregation function (SUM, AVG, COUNT, etc.)
            filters: Optional filter conditions
            force_refresh: Skip cache and recompute
            limit: Max rows to return

        Returns:
            Dict with data, metadata, and cache info
        """
        cache_key = self._cache_key(connector_id, table, dimension, measure, agg_func, filters)

        # Check cache first
        if self.enabled and not force_refresh:
            cached = self.redis.get(cache_key)
            if cached:
                try:
                    result = json.loads(cached)
                    result["from_cache"] = True
                    logger.debug(
                        "Aggregation cache hit",
                        connector_id=connector_id,
                        table=table,
                        dimension=dimension
                    )
                    return result
                except json.JSONDecodeError:
                    pass

        # Compute aggregation
        try:
            connector = get_connector(connector_id)
            if not connector:
                return {
                    "success": False,
                    "error": f"Connector not found: {connector_id}",
                    "data": []
                }

            sql = self._build_agg_sql(
                table, dimension, measure, agg_func,
                filters=filters, limit=limit
            )

            logger.debug(
                "Computing aggregation",
                connector_id=connector_id,
                sql=sql[:200]
            )

            # Execute query
            result = connector.execute_query(sql)

            response = {
                "success": True,
                "data": result.get("results", []),
                "row_count": len(result.get("results", [])),
                "dimension": dimension,
                "measure": measure,
                "agg_func": agg_func,
                "computed_at": datetime.utcnow().isoformat(),
                "from_cache": False
            }

            # Cache the result
            if self.enabled:
                # Determine TTL based on dimension type
                ttl = self.DEFAULT_TTL
                dim_lower = dimension.lower()
                if any(t in dim_lower for t in ["date", "time", "day", "month", "year"]):
                    ttl = self.TIME_SERIES_TTL
                else:
                    ttl = self.DIMENSION_TTL

                self.redis.setex(cache_key, ttl, json.dumps(response, default=str))
                logger.info(
                    "Aggregation cached",
                    connector_id=connector_id,
                    table=table,
                    dimension=dimension,
                    ttl=ttl
                )

            return response

        except Exception as e:
            logger.error(f"Failed to compute aggregation: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }

    async def get_time_series(
        self,
        connector_id: str,
        table: str,
        time_column: str,
        measure: str,
        agg_func: str = "SUM",
        granularity: str = "day",
        filters: Optional[Dict] = None,
        limit: int = 365
    ) -> Dict[str, Any]:
        """
        Get time series aggregation with automatic date truncation.

        Args:
            connector_id: Database connector identifier
            table: Table name
            time_column: Date/timestamp column
            measure: Column to aggregate
            agg_func: Aggregation function
            granularity: Time granularity (day, week, month, quarter, year)
            filters: Optional filter conditions
            limit: Max rows to return

        Returns:
            Dict with time series data
        """
        # Build date truncation expression based on connector type
        connector = get_connector(connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found", "data": []}

        db_type = getattr(connector, 'db_type', 'postgres')

        # Date truncation expressions by database type
        trunc_exprs = {
            "bigquery": f"DATE_TRUNC({time_column}, {granularity.upper()})",
            "snowflake": f"DATE_TRUNC('{granularity}', {time_column})",
            "postgres": f"DATE_TRUNC('{granularity}', {time_column})",
            "postgresql": f"DATE_TRUNC('{granularity}', {time_column})",
            "redshift": f"DATE_TRUNC('{granularity}', {time_column})",
            "databricks": f"DATE_TRUNC('{granularity}', {time_column})"
        }

        trunc_expr = trunc_exprs.get(db_type, f"DATE_TRUNC('{granularity}', {time_column})")

        # Use the truncated date as dimension
        cache_key = f"{self.PREFIX}ts:{connector_id}:{table}:{time_column}:{granularity}:{measure}:{agg_func}"

        # Check cache
        if self.enabled:
            cached = self.redis.get(cache_key)
            if cached:
                try:
                    result = json.loads(cached)
                    result["from_cache"] = True
                    return result
                except json.JSONDecodeError:
                    pass

        try:
            # Build custom SQL for time series
            agg_expr = f"{agg_func}({measure})" if agg_func != "COUNT_DISTINCT" else f"COUNT(DISTINCT {measure})"

            sql = f"""
                SELECT {trunc_expr} as period, {agg_expr} as value
                FROM {table}
            """

            if filters:
                where_clauses = []
                for col, val in filters.items():
                    if isinstance(val, dict):
                        if "min" in val:
                            where_clauses.append(f"{col} >= '{val['min']}'")
                        if "max" in val:
                            where_clauses.append(f"{col} <= '{val['max']}'")
                    else:
                        where_clauses.append(f"{col} = '{val}'")
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)

            sql += f"""
                GROUP BY {trunc_expr}
                ORDER BY period
                LIMIT {limit}
            """

            result = connector.execute_query(sql)

            response = {
                "success": True,
                "data": result.get("results", []),
                "row_count": len(result.get("results", [])),
                "time_column": time_column,
                "granularity": granularity,
                "measure": measure,
                "agg_func": agg_func,
                "computed_at": datetime.utcnow().isoformat(),
                "from_cache": False
            }

            # Cache with shorter TTL for time series
            if self.enabled:
                self.redis.setex(cache_key, self.TIME_SERIES_TTL, json.dumps(response, default=str))

            return response

        except Exception as e:
            logger.error(f"Failed to compute time series: {e}")
            return {"success": False, "error": str(e), "data": []}

    def invalidate_table(self, connector_id: str, table: str) -> int:
        """
        Invalidate all aggregations for a table.

        Call this when underlying data changes.

        Args:
            connector_id: Database connector identifier
            table: Table name

        Returns:
            Number of cache entries invalidated
        """
        if not self.enabled:
            return 0

        try:
            pattern = f"{self.PREFIX}{connector_id}:{table}:*"
            count = 0
            for key in self.redis.scan_iter(pattern):
                self.redis.delete(key)
                count += 1

            # Also invalidate time series
            ts_pattern = f"{self.PREFIX}ts:{connector_id}:{table}:*"
            for key in self.redis.scan_iter(ts_pattern):
                self.redis.delete(key)
                count += 1

            logger.info(
                "Table aggregations invalidated",
                connector_id=connector_id,
                table=table,
                count=count
            )
            return count

        except Exception as e:
            logger.error(f"Failed to invalidate table aggregations: {e}")
            return 0

    def invalidate_connector(self, connector_id: str) -> int:
        """Invalidate all aggregations for a connector."""
        if not self.enabled:
            return 0

        try:
            count = 0
            for pattern in [f"{self.PREFIX}{connector_id}:*", f"{self.PREFIX}ts:{connector_id}:*"]:
                for key in self.redis.scan_iter(pattern):
                    self.redis.delete(key)
                    count += 1

            logger.info(
                "Connector aggregations invalidated",
                connector_id=connector_id,
                count=count
            )
            return count

        except Exception as e:
            logger.error(f"Failed to invalidate connector aggregations: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached aggregations."""
        if not self.enabled:
            return {"enabled": False}

        try:
            agg_count = 0
            ts_count = 0
            total_size = 0

            for key in self.redis.scan_iter(f"{self.PREFIX}*"):
                if key.startswith(f"{self.PREFIX}ts:"):
                    ts_count += 1
                else:
                    agg_count += 1

                # Estimate size
                try:
                    val = self.redis.get(key)
                    if val:
                        total_size += len(val)
                except Exception:
                    pass

            return {
                "enabled": True,
                "aggregation_count": agg_count,
                "time_series_count": ts_count,
                "total_entries": agg_count + ts_count,
                "estimated_size_bytes": total_size,
                "estimated_size_mb": round(total_size / (1024 * 1024), 2)
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    def warm_cache(
        self,
        connector_id: str,
        table: str,
        dimensions: List[str],
        measures: List[str],
        agg_funcs: List[str] = ["SUM", "COUNT"]
    ) -> Dict[str, Any]:
        """
        Pre-warm cache with common aggregations.

        Args:
            connector_id: Database connector identifier
            table: Table name
            dimensions: List of dimension columns
            measures: List of measure columns
            agg_funcs: Aggregation functions to pre-compute

        Returns:
            Summary of warmed aggregations
        """
        warmed = 0
        errors = 0

        for dim in dimensions:
            for measure in measures:
                for agg_func in agg_funcs:
                    try:
                        # This will compute and cache
                        import asyncio
                        asyncio.run(self.get_or_compute_aggregation(
                            connector_id, table, dim, measure, agg_func,
                            force_refresh=True
                        ))
                        warmed += 1
                    except Exception as e:
                        logger.warning(f"Failed to warm cache for {dim}/{measure}/{agg_func}: {e}")
                        errors += 1

        return {
            "warmed": warmed,
            "errors": errors,
            "total_attempted": len(dimensions) * len(measures) * len(agg_funcs)
        }


# Singleton instance
_aggregation_manager: Optional[AggregationManager] = None


def get_aggregation_manager() -> AggregationManager:
    """Get the singleton AggregationManager instance."""
    global _aggregation_manager
    if _aggregation_manager is None:
        _aggregation_manager = AggregationManager(redis_url=settings.redis_url)
    return _aggregation_manager
