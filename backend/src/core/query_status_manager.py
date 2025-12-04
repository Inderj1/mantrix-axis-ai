"""
Query Status Manager for async query execution with polling support.

Stores query execution status in Redis for frontend polling.
"""

import json
import redis
from typing import Dict, Any, Optional
from datetime import datetime
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

            data.update(extra_data)

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


# Singleton instance
_query_status_manager: Optional[QueryStatusManager] = None


def get_query_status_manager() -> QueryStatusManager:
    """Get the singleton QueryStatusManager instance."""
    global _query_status_manager
    if _query_status_manager is None:
        _query_status_manager = QueryStatusManager(redis_url=settings.redis_url)
    return _query_status_manager
