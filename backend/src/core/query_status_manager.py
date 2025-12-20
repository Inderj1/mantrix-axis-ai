"""
Query Status Manager for async query execution with polling support.

Stores query execution status in Redis for frontend polling.
Also persists completed queries to MongoDB for query history.
"""

import json
import redis
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import structlog

from src.config import settings

logger = structlog.get_logger()


class QueryStatusManager:
    """
    Manages query execution status in Redis.

    Supports the async polling pattern:
    - POST /query starts processing, returns execution_id
    - GET /query/status/{id} returns current progress
    - Frontend polls until complete or error
    """

    PREFIX = "query_status:"
    TTL = 3600  # 1 hour - queries older than this are expired

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
            logger.info("QueryStatusManager connected to Redis")
        except Exception as e:
            logger.warning(f"QueryStatusManager: Redis not available, status tracking disabled: {e}")
            self.redis = None
            self.enabled = False

    def _key(self, execution_id: str) -> str:
        """Generate Redis key for execution_id."""
        return f"{self.PREFIX}{execution_id}"

    def update_status(
        self,
        execution_id: str,
        status: str,
        progress: int,
        message: str,
        phase: Optional[str] = None,
        sql: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        correction_info: Optional[Dict[str, Any]] = None,
        **extra_data
    ) -> bool:
        """
        Update query status in Redis.

        Args:
            execution_id: Unique query execution ID
            status: Current status (processing, complete, error)
            progress: Progress percentage (0-100)
            message: Human-readable status message
            phase: Current processing phase (generating, executing, correcting, etc.)
            sql: Generated SQL (when available)
            result: Final result (when complete)
            error: Error message (when failed)
            correction_info: Error correction details (when correcting)
            **extra_data: Any additional data to store

        Returns:
            True if status was updated, False if Redis unavailable
        """
        if not self.enabled:
            return False

        try:
            data = {
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.utcnow().isoformat(),
            }

            if phase:
                data["phase"] = phase
            if sql:
                data["sql"] = sql
            if error:
                data["error"] = error
            if correction_info:
                data["correction_info"] = json.dumps(correction_info)
            if result:
                # Store result as JSON string (can be large)
                data["result"] = json.dumps(result, default=str)

            # Convert boolean values to strings for Redis compatibility
            # Redis hset doesn't accept booleans directly
            for key_name, value in extra_data.items():
                if isinstance(value, bool):
                    data[key_name] = "1" if value else "0"
                else:
                    data[key_name] = value

            key = self._key(execution_id)
            self.redis.hset(key, mapping=data)
            self.redis.expire(key, self.TTL)

            logger.info(
                f"Query status updated",
                execution_id=execution_id,
                status=status,
                progress=progress,
                phase=phase
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update query status: {e}")
            return False

    def get_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current query status from Redis.

        Args:
            execution_id: Unique query execution ID

        Returns:
            Status dict or None if not found/expired
        """
        if not self.enabled:
            return None

        try:
            key = self._key(execution_id)
            data = self.redis.hgetall(key)

            if not data:
                return None

            # Parse JSON fields
            if "result" in data:
                try:
                    data["result"] = json.loads(data["result"])
                except json.JSONDecodeError:
                    pass

            if "correction_info" in data:
                try:
                    data["correction_info"] = json.loads(data["correction_info"])
                except json.JSONDecodeError:
                    pass

            # Convert progress to int
            if "progress" in data:
                data["progress"] = int(data["progress"])

            return data

        except Exception as e:
            logger.error(f"Failed to get query status: {e}")
            return None

    def delete_status(self, execution_id: str) -> bool:
        """Delete query status (cleanup)."""
        if not self.enabled:
            return False

        try:
            self.redis.delete(self._key(execution_id))
            return True
        except Exception:
            return False

    async def complete_and_persist(
        self,
        execution_id: str,
        user_id: str,
        organization_id: str,
        question: str,
        sql: str,
        status: str,  # "complete" or "error"
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        is_background: bool = False
    ) -> bool:
        """
        Complete a query and persist to MongoDB for query history.

        This method:
        1. Updates the final status in Redis (for immediate polling)
        2. Persists the full results to MongoDB (for long-term storage)
        3. Returns True if successfully persisted

        Args:
            execution_id: Unique query execution ID
            user_id: User who ran the query
            organization_id: Organization ID
            question: Original natural language question
            sql: Generated SQL
            status: Final status ("complete" or "error")
            result: Query results dict (from QueryResponse)
            error: Error message if failed
            started_at: When the query started
            is_background: Whether this is a background query

        Returns:
            True if persisted to MongoDB
        """
        try:
            # Calculate execution time
            end_time = datetime.now(timezone.utc)
            execution_time_seconds = None
            if started_at:
                # Ensure started_at is timezone-aware (convert if naive)
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                execution_time_seconds = (end_time - started_at).total_seconds()

            # Update Redis status first (for immediate polling)
            self.update_status(
                execution_id=execution_id,
                status=status,
                progress=100,
                message="Done!" if status == "complete" else error or "Query failed",
                phase="complete" if status == "complete" else "error",
                sql=sql,
                result=result,
                error=error
            )

            # Prepare result summary for MongoDB
            result_summary = None
            full_results = None

            if result and status == "complete":
                execution_data = result.get("execution", {})
                results_data = execution_data.get("results", [])
                columns = []
                if results_data and len(results_data) > 0:
                    columns = list(results_data[0].keys())

                result_summary = {
                    "row_count": execution_data.get("row_count", 0),
                    "columns": columns,
                    "preview": results_data[:10] if results_data else []
                }

                # Store full results (MongoDB will handle size check)
                full_results = results_data

            # Persist to MongoDB
            from src.db.mongodb_client import get_mongodb_client
            mongodb = await get_mongodb_client()

            success = await mongodb.complete_query_history(
                execution_id=execution_id,
                status=status,
                result_summary=result_summary,
                full_results=full_results,
                error=error,
                execution_time_seconds=execution_time_seconds
            )

            if success:
                logger.info(
                    "Query persisted to MongoDB",
                    execution_id=execution_id,
                    status=status,
                    execution_time_seconds=execution_time_seconds,
                    is_background=is_background
                )
            else:
                logger.warning(
                    "Failed to persist query to MongoDB (entry may not exist)",
                    execution_id=execution_id
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to complete and persist query",
                execution_id=execution_id,
                error=str(e)
            )
            return False

    async def create_query_entry(
        self,
        execution_id: str,
        user_id: str,
        organization_id: str,
        question: str,
        sql: str = "",
        is_background: bool = False,
        notification_preferences: Optional[Dict[str, bool]] = None
    ) -> bool:
        """
        Create a query history entry when a query starts.

        Args:
            execution_id: Unique query execution ID
            user_id: User who ran the query
            organization_id: Organization ID
            question: Original natural language question
            sql: Generated SQL (may be empty at start)
            is_background: Whether this is a background query
            notification_preferences: User's notification preferences

        Returns:
            True if created in MongoDB
        """
        try:
            from src.db.mongodb_client import get_mongodb_client
            mongodb = await get_mongodb_client()

            await mongodb.create_query_history(
                execution_id=execution_id,
                user_id=user_id,
                organization_id=organization_id,
                question=question,
                sql=sql,
                is_background=is_background,
                notification_preferences=notification_preferences
            )

            logger.info(
                "Query history entry created",
                execution_id=execution_id,
                user_id=user_id,
                is_background=is_background
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to create query history entry",
                execution_id=execution_id,
                error=str(e)
            )
            return False


# Singleton instance
_query_status_manager: Optional[QueryStatusManager] = None


def get_query_status_manager() -> QueryStatusManager:
    """Get the singleton QueryStatusManager instance."""
    global _query_status_manager
    if _query_status_manager is None:
        _query_status_manager = QueryStatusManager(redis_url=settings.redis_url)
    return _query_status_manager
