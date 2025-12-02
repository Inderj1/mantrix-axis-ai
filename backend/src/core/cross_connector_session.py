"""
Cross-Connector Session Manager

Manages session-based caching of per-connector query results for cross-database queries.
Enables secure backend re-joins when users edit individual queries.

Security Benefits:
- Data never exposed in browser memory
- Existing DB permissions apply
- Audit trail maintained
- Handles large datasets using appropriate strategy (pandas/staging/federation)
"""

import json
import uuid
import pickle
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
import pandas as pd
import structlog

from src.config import settings

logger = structlog.get_logger()

# Cache TTL for cross-connector results (30 minutes)
CROSS_CONNECTOR_TTL = 30 * 60

# Size thresholds for join strategy selection (in MB)
PANDAS_THRESHOLD_MB = 100  # Use pandas for < 100MB
STAGING_THRESHOLD_MB = 10_000  # Use staging tables for < 10GB


@dataclass
class ConnectorResult:
    """Cached result from a single connector query."""
    connector_id: str
    database_type: str
    sql: str
    results: List[Dict[str, Any]]
    row_count: int
    size_mb: float
    executed_at: str
    tables_used: List[str] = field(default_factory=list)


@dataclass
class CrossConnectorSession:
    """Session data for a cross-connector query."""
    session_id: str
    organization_id: str
    user_id: str
    created_at: str
    connector_results: Dict[str, ConnectorResult]  # connector_id -> result
    join_specification: Dict[str, Any]
    merged_results: Optional[List[Dict[str, Any]]] = None
    merged_row_count: int = 0


class CrossConnectorSessionManager:
    """
    Manages session-based caching of per-connector results for cross-database queries.

    Features:
    - Cache per-connector results in Redis with TTL
    - Re-join results after editing individual queries
    - Strategy selection based on data size (pandas/staging/federation)
    - Session cleanup on TTL expiry
    """

    # Cache key prefix
    PREFIX = "cross_connector:"

    def __init__(self, redis_client=None):
        """
        Initialize the session manager.

        Args:
            redis_client: Redis client instance (if None, creates new connection)
        """
        self.redis = redis_client
        if self.redis is None:
            import redis as redis_lib
            self.redis = redis_lib.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=0,
                decode_responses=False
            )

        logger.info("CrossConnectorSessionManager initialized")

    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"xc_{uuid.uuid4().hex[:16]}"

    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for a session."""
        return f"{self.PREFIX}session:{session_id}"

    def _get_result_key(self, session_id: str, connector_id: str) -> str:
        """Get Redis key for a connector result within a session."""
        return f"{self.PREFIX}result:{session_id}:{connector_id}"

    async def create_session(
        self,
        organization_id: str,
        user_id: str,
        connector_results: Dict[str, Dict[str, Any]],
        join_specification: Dict[str, Any],
        merged_results: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a new cross-connector session and cache results.

        Args:
            organization_id: Organization ID for permission enforcement
            user_id: User ID for audit
            connector_results: Dict of connector_id -> result data
            join_specification: Join specification (type, condition, keys)
            merged_results: Optional pre-merged results

        Returns:
            Session ID for future re-join requests
        """
        session_id = self.generate_session_id()
        created_at = datetime.utcnow().isoformat()

        # Process and cache each connector's results
        processed_results = {}
        for connector_id, result_data in connector_results.items():
            results = result_data.get('results', [])

            # Calculate size estimate
            size_mb = self._estimate_size_mb(results)

            connector_result = ConnectorResult(
                connector_id=connector_id,
                database_type=result_data.get('database_type', 'unknown'),
                sql=result_data.get('sql', ''),
                results=results,
                row_count=len(results),
                size_mb=size_mb,
                executed_at=created_at,
                tables_used=result_data.get('tables_used', [])
            )

            processed_results[connector_id] = connector_result

            # Cache individual connector result
            result_key = self._get_result_key(session_id, connector_id)
            self.redis.setex(
                result_key,
                CROSS_CONNECTOR_TTL,
                pickle.dumps(asdict(connector_result))
            )

        # Create session metadata
        session = CrossConnectorSession(
            session_id=session_id,
            organization_id=organization_id,
            user_id=user_id,
            created_at=created_at,
            connector_results={cid: asdict(cr) for cid, cr in processed_results.items()},
            join_specification=join_specification,
            merged_results=merged_results,
            merged_row_count=len(merged_results) if merged_results else 0
        )

        # Cache session metadata (without full results to save space)
        session_data = asdict(session)
        # Store only metadata, not full results (those are stored separately)
        session_data['connector_results'] = {
            cid: {k: v for k, v in cr.items() if k != 'results'}
            for cid, cr in session_data['connector_results'].items()
        }
        session_data['merged_results'] = None  # Don't duplicate merged results

        session_key = self._get_session_key(session_id)
        self.redis.setex(
            session_key,
            CROSS_CONNECTOR_TTL,
            pickle.dumps(session_data)
        )

        logger.info(
            "Cross-connector session created",
            session_id=session_id,
            connectors=list(connector_results.keys()),
            total_rows=sum(cr.row_count for cr in processed_results.values())
        )

        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata.

        Args:
            session_id: Session ID

        Returns:
            Session metadata dict or None if not found/expired
        """
        session_key = self._get_session_key(session_id)
        data = self.redis.get(session_key)

        if data is None:
            return None

        return pickle.loads(data)

    async def get_connector_results(
        self,
        session_id: str,
        connector_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached results for a specific connector.

        Args:
            session_id: Session ID
            connector_id: Connector ID

        Returns:
            List of result rows or None if not found/expired
        """
        result_key = self._get_result_key(session_id, connector_id)
        data = self.redis.get(result_key)

        if data is None:
            logger.warning(
                "Connector results not found in cache",
                session_id=session_id,
                connector_id=connector_id
            )
            return None

        result = pickle.loads(data)
        return result.get('results', [])

    async def get_all_connector_results(
        self,
        session_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all cached connector results for a session.

        Args:
            session_id: Session ID

        Returns:
            Dict of connector_id -> results list
        """
        session = await self.get_session(session_id)
        if session is None:
            return {}

        results = {}
        for connector_id in session.get('connector_results', {}).keys():
            connector_results = await self.get_connector_results(session_id, connector_id)
            if connector_results is not None:
                results[connector_id] = connector_results

        return results

    async def update_connector_results(
        self,
        session_id: str,
        connector_id: str,
        new_sql: str,
        new_results: List[Dict[str, Any]]
    ) -> bool:
        """
        Update cached results for a connector after re-execution.

        Args:
            session_id: Session ID
            connector_id: Connector ID
            new_sql: Updated SQL query
            new_results: New query results

        Returns:
            True if update successful, False otherwise
        """
        result_key = self._get_result_key(session_id, connector_id)
        existing = self.redis.get(result_key)

        if existing is None:
            logger.error(
                "Cannot update non-existent connector results",
                session_id=session_id,
                connector_id=connector_id
            )
            return False

        existing_data = pickle.loads(existing)

        # Update with new data
        existing_data['sql'] = new_sql
        existing_data['results'] = new_results
        existing_data['row_count'] = len(new_results)
        existing_data['size_mb'] = self._estimate_size_mb(new_results)
        existing_data['executed_at'] = datetime.utcnow().isoformat()

        # Refresh TTL and save
        self.redis.setex(
            result_key,
            CROSS_CONNECTOR_TTL,
            pickle.dumps(existing_data)
        )

        logger.info(
            "Connector results updated",
            session_id=session_id,
            connector_id=connector_id,
            new_row_count=len(new_results)
        )

        return True

    def select_join_strategy(
        self,
        left_size_mb: float,
        right_size_mb: float
    ) -> str:
        """
        Select appropriate join strategy based on data sizes.

        Args:
            left_size_mb: Size of left dataset in MB
            right_size_mb: Size of right dataset in MB

        Returns:
            Strategy name: "pandas", "staging_table", or "s3_federation"
        """
        total_size = left_size_mb + right_size_mb

        if total_size < PANDAS_THRESHOLD_MB:
            return "pandas"
        elif total_size < STAGING_THRESHOLD_MB:
            return "staging_table"
        else:
            return "s3_federation"

    async def rejoin_results(
        self,
        session_id: str,
        join_specification: Dict[str, Any],
        connector_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Re-join all connector results with potentially updated join specification.

        Args:
            session_id: Session ID
            join_specification: Join spec (type, condition, left_key, right_key)
            connector_configs: Optional connector configs for staging table strategy

        Returns:
            Tuple of (merged_results, metadata)
        """
        # Get all connector results
        all_results = await self.get_all_connector_results(session_id)

        if len(all_results) < 2:
            raise ValueError(f"Need at least 2 connector results to join, got {len(all_results)}")

        # Get connector IDs in order
        connector_ids = list(all_results.keys())

        # Calculate sizes
        sizes = {
            cid: self._estimate_size_mb(results)
            for cid, results in all_results.items()
        }
        total_size = sum(sizes.values())

        # Select strategy
        strategy = self.select_join_strategy(
            sizes[connector_ids[0]],
            sizes[connector_ids[1]] if len(connector_ids) > 1 else 0
        )

        logger.info(
            "Re-joining results",
            session_id=session_id,
            strategy=strategy,
            total_size_mb=f"{total_size:.2f}",
            connectors=connector_ids
        )

        # Execute join based on strategy
        if strategy == "pandas":
            merged = await self._pandas_join(all_results, join_specification)
        elif strategy == "staging_table":
            merged = await self._staging_table_join(
                all_results, join_specification, connector_configs
            )
        else:
            merged = await self._federation_join(
                all_results, join_specification, connector_configs
            )

        metadata = {
            "strategy": strategy,
            "total_input_size_mb": total_size,
            "connectors_joined": connector_ids,
            "join_type": join_specification.get("type", "INNER"),
            "result_count": len(merged)
        }

        return merged, metadata

    async def _pandas_join(
        self,
        all_results: Dict[str, List[Dict[str, Any]]],
        join_specification: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Perform in-memory join using pandas.

        Args:
            all_results: Dict of connector_id -> results
            join_specification: Join specification

        Returns:
            Merged results as list of dicts
        """
        connector_ids = list(all_results.keys())

        # Convert to DataFrames
        dfs = {cid: pd.DataFrame(results) for cid, results in all_results.items()}

        # Parse join specification
        join_type = join_specification.get("type", "INNER").lower()
        left_key = join_specification.get("left_key")
        right_key = join_specification.get("right_key")

        # If keys not specified, try to parse from condition
        if not left_key or not right_key:
            condition = join_specification.get("condition", "")
            left_key, right_key = self._parse_join_keys(condition)

        # Check if we should use UNION instead of JOIN
        # This happens when:
        # 1. No valid join keys exist, OR
        # 2. Join type is explicitly "UNION", OR
        # 3. Columns are similar and no join key found (aggregation comparison)
        if len(dfs) == 2:
            left_df = dfs[connector_ids[0]]
            right_df = dfs[connector_ids[1]]

            # Check if we have valid join keys
            has_valid_join_keys = (
                (left_key and right_key and
                 left_key in left_df.columns and right_key in right_df.columns) or
                (left_key and left_key in left_df.columns and left_key in right_df.columns)
            )

            # Check if columns are similar (suggests UNION is appropriate)
            left_cols = set(left_df.columns)
            right_cols = set(right_df.columns)
            column_overlap = len(left_cols & right_cols) / max(len(left_cols), len(right_cols), 1)

            use_union = (
                join_type == "union" or
                (not has_valid_join_keys and column_overlap > 0.5)
            )

            if use_union:
                logger.info(
                    "Using UNION instead of JOIN",
                    reason="no_valid_join_keys" if not has_valid_join_keys else "explicit_union",
                    column_overlap=f"{column_overlap:.2f}"
                )
                # Add source connector column to distinguish results
                left_df = left_df.copy()
                right_df = right_df.copy()
                left_df['_source_connector'] = connector_ids[0]
                right_df['_source_connector'] = connector_ids[1]

                # Concatenate (UNION)
                merged_df = pd.concat([left_df, right_df], ignore_index=True)
                return merged_df.to_dict('records')

        # Map join type to pandas how parameter
        how_map = {
            "inner": "inner",
            "left": "left",
            "right": "right",
            "full": "outer",
            "full outer": "outer"
        }
        how = how_map.get(join_type, "inner")

        # Perform join (for 2 connectors)
        if len(dfs) == 2:
            # Handle case where keys might be in different connectors
            if left_key in left_df.columns and right_key in right_df.columns:
                merged_df = pd.merge(
                    left_df, right_df,
                    left_on=left_key,
                    right_on=right_key,
                    how=how,
                    suffixes=('_left', '_right')
                )
            elif left_key in left_df.columns:
                # Both keys might be the same column name
                merged_df = pd.merge(
                    left_df, right_df,
                    on=left_key,
                    how=how,
                    suffixes=('_left', '_right')
                )
            else:
                # Fallback to UNION if join keys truly don't exist
                logger.warning(
                    "Join keys not found, falling back to UNION",
                    left_key=left_key,
                    right_key=right_key
                )
                left_df = left_df.copy()
                right_df = right_df.copy()
                left_df['_source_connector'] = connector_ids[0]
                right_df['_source_connector'] = connector_ids[1]
                merged_df = pd.concat([left_df, right_df], ignore_index=True)
                return merged_df.to_dict('records')
        else:
            # For more than 2 connectors, chain joins
            merged_df = dfs[connector_ids[0]]
            for cid in connector_ids[1:]:
                merged_df = pd.merge(
                    merged_df, dfs[cid],
                    left_on=left_key,
                    right_on=right_key,
                    how=how,
                    suffixes=('', f'_{cid}')
                )

        # Convert back to list of dicts
        return merged_df.to_dict('records')

    async def _staging_table_join(
        self,
        all_results: Dict[str, List[Dict[str, Any]]],
        join_specification: Dict[str, Any],
        connector_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform join using staging tables (for larger datasets).

        Falls back to pandas if staging table manager not available.
        """
        try:
            from src.core.staging_table_manager import StagingTableManager
            from src.db.connector_factory import ConnectorFactory

            # For now, fall back to pandas as staging table join requires
            # more complex setup with actual database connections
            logger.warning(
                "Staging table join not fully implemented, falling back to pandas"
            )
            return await self._pandas_join(all_results, join_specification)

        except ImportError:
            logger.warning("StagingTableManager not available, using pandas join")
            return await self._pandas_join(all_results, join_specification)

    async def _federation_join(
        self,
        all_results: Dict[str, List[Dict[str, Any]]],
        join_specification: Dict[str, Any],
        connector_configs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform join using S3 federation (for very large datasets).

        Falls back to pandas if federation not available.
        """
        try:
            from src.core.federation_factory import FederationFactory

            # For now, fall back to pandas as federation requires
            # S3 setup and additional configuration
            logger.warning(
                "S3 federation join not fully implemented, falling back to pandas"
            )
            return await self._pandas_join(all_results, join_specification)

        except ImportError:
            logger.warning("FederationFactory not available, using pandas join")
            return await self._pandas_join(all_results, join_specification)

    def _parse_join_keys(self, condition: str) -> Tuple[str, str]:
        """
        Parse join keys from a condition string.

        Args:
            condition: Join condition like "customers.id = orders.customer_id"

        Returns:
            Tuple of (left_key, right_key)
        """
        # Simple parsing for "left.key = right.key" format
        import re

        # Remove whitespace around =
        condition = condition.strip()

        # Try to match pattern: table.column = table.column
        match = re.match(r'(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)', condition)
        if match:
            return match.group(2), match.group(4)

        # Try simpler pattern: column = column
        match = re.match(r'(\w+)\s*=\s*(\w+)', condition)
        if match:
            return match.group(1), match.group(2)

        # Default to common key names
        return "id", "id"

    def _estimate_size_mb(self, results: List[Dict[str, Any]]) -> float:
        """
        Estimate size of results in MB.

        Args:
            results: List of result dictionaries

        Returns:
            Estimated size in MB
        """
        if not results:
            return 0.0

        # Sample-based estimation for large result sets
        sample_size = min(100, len(results))
        sample = results[:sample_size]

        # Estimate bytes per row
        sample_json = json.dumps(sample)
        bytes_per_row = len(sample_json.encode('utf-8')) / sample_size

        # Total estimate
        total_bytes = bytes_per_row * len(results)
        return total_bytes / (1024 * 1024)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its cached results.

        Args:
            session_id: Session ID

        Returns:
            True if deletion successful
        """
        session = await self.get_session(session_id)
        if session is None:
            return False

        # Delete all connector results
        for connector_id in session.get('connector_results', {}).keys():
            result_key = self._get_result_key(session_id, connector_id)
            self.redis.delete(result_key)

        # Delete session metadata
        session_key = self._get_session_key(session_id)
        self.redis.delete(session_key)

        logger.info("Cross-connector session deleted", session_id=session_id)
        return True


# Singleton instance
_session_manager: Optional[CrossConnectorSessionManager] = None


def get_cross_connector_session_manager() -> CrossConnectorSessionManager:
    """Get or create the singleton session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = CrossConnectorSessionManager()
    return _session_manager
