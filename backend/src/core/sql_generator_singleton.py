"""
Singleton pattern for SQLGenerator with per-organization caching,
thread safety, and Redis-based cross-worker invalidation.

This module provides:
1. Per-organization SQLGenerator caching
2. Thread-safe access with locking
3. Cross-worker invalidation via Redis timestamps
4. Graceful fallback when Redis is unavailable

Usage:
    from src.core.sql_generator_singleton import (
        get_sql_generator,
        invalidate_sql_generator
    )

    # Get generator for an organization
    generator = get_sql_generator(organization_id="org123")

    # Invalidate after connector changes
    invalidate_sql_generator(organization_id="org123")
"""

import threading
import time
from typing import Optional, Dict, List, TYPE_CHECKING
import structlog

if TYPE_CHECKING:
    from src.core.sql_generator import SQLGenerator

logger = structlog.get_logger()

# Thread-safe singleton storage
_sql_generator_lock = threading.Lock()
_sql_generators: Dict[str, "SQLGenerator"] = {}  # org_id -> SQLGenerator
_invalidation_timestamps: Dict[str, float] = {}  # org_id -> last known timestamp

# Redis client cache to avoid repeated initialization
_redis_client = None
_redis_client_lock = threading.Lock()


def _get_redis_client():
    """Get or create Redis client for invalidation checks."""
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    with _redis_client_lock:
        if _redis_client is not None:
            return _redis_client

        try:
            from src.config import settings
            import redis

            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis client initialized for invalidation checks")
            return _redis_client
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}")
            return None


def get_sql_generator(organization_id: str = None) -> "SQLGenerator":
    """
    Get or create SQLGenerator instance for an organization.

    Uses double-check locking pattern for thread safety.
    Checks Redis for cross-worker invalidation before returning cached instance.

    Args:
        organization_id: Organization ID (defaults to 'default')

    Returns:
        SQLGenerator instance for the organization
    """
    from src.core.sql_generator import SQLGenerator

    org_id = organization_id or "default"

    # Fast path: check for cached instance with Redis invalidation check
    if org_id in _sql_generators:
        if _should_invalidate(org_id):
            _invalidate_internal(org_id)
        else:
            return _sql_generators[org_id]

    # Slow path: acquire lock and create new instance
    with _sql_generator_lock:
        # Double-check after acquiring lock
        if org_id in _sql_generators:
            return _sql_generators[org_id]

        logger.info(
            "Creating new SQLGenerator instance",
            organization_id=org_id
        )

        generator = SQLGenerator(organization_id=org_id)
        _sql_generators[org_id] = generator

        # Update timestamp to current time to avoid immediate re-invalidation
        _invalidation_timestamps[org_id] = time.time()

        return generator


def invalidate_sql_generator(organization_id: str = None) -> bool:
    """
    Invalidate SQLGenerator cache for an organization.

    Signals invalidation via Redis for cross-worker sync,
    then clears the local cached instance.

    Args:
        organization_id: Organization ID to invalidate (defaults to 'default')

    Returns:
        True if an instance was invalidated, False if none existed
    """
    org_id = organization_id or "default"

    # Signal via Redis for cross-worker invalidation
    _signal_invalidation(org_id)

    # Invalidate local instance
    return _invalidate_internal(org_id)


def invalidate_all_sql_generators() -> int:
    """
    Invalidate all cached SQLGenerator instances.

    Use with caution - this affects all organizations.

    Returns:
        Number of instances invalidated
    """
    with _sql_generator_lock:
        count = len(_sql_generators)

        for org_id, generator in list(_sql_generators.items()):
            _signal_invalidation(org_id)
            _cleanup_generator(generator)

        _sql_generators.clear()
        _invalidation_timestamps.clear()

        logger.info(
            "Invalidated all SQLGenerator instances",
            count=count
        )
        return count


def get_cached_organization_ids() -> List[str]:
    """
    Get list of organization IDs with cached SQLGenerator instances.

    Useful for debugging and monitoring.

    Returns:
        List of organization IDs
    """
    with _sql_generator_lock:
        return list(_sql_generators.keys())


def _invalidate_internal(org_id: str) -> bool:
    """
    Internal invalidation without Redis signal.

    Called when we detect a Redis invalidation flag from another worker.
    """
    with _sql_generator_lock:
        if org_id in _sql_generators:
            old_generator = _sql_generators.pop(org_id)
            _cleanup_generator(old_generator)
            logger.info(
                "Invalidated SQLGenerator instance",
                organization_id=org_id
            )
            return True

        logger.debug(
            "No SQLGenerator instance to invalidate",
            organization_id=org_id
        )
        return False


def _signal_invalidation(org_id: str) -> None:
    """
    Signal invalidation via Redis for cross-worker sync.

    Sets a Redis key with the current timestamp.
    Other workers will detect this and invalidate their cached instances.
    """
    redis_client = _get_redis_client()
    if redis_client is None:
        logger.warning(
            "Cannot signal connector change - Redis not available",
            organization_id=org_id
        )
        return

    try:
        key = f"connector:invalidation:{org_id}"
        timestamp = time.time()

        # Set the invalidation flag with 24-hour TTL (self-cleaning)
        redis_client.setex(key, 86400, str(timestamp))

        logger.info(
            "Signaled connector invalidation",
            organization_id=org_id,
            timestamp=timestamp
        )

    except Exception as e:
        logger.error(
            "Failed to signal connector change",
            organization_id=org_id,
            error=str(e)
        )


def _should_invalidate(org_id: str) -> bool:
    """
    Check Redis if invalidation was signaled by another worker.

    Compares the Redis timestamp with our last known timestamp.
    Returns True if a newer timestamp is found.
    """
    redis_client = _get_redis_client()
    if redis_client is None:
        # No Redis = can't detect cross-worker changes
        # This is acceptable - single worker deployments don't need this
        return False

    try:
        key = f"connector:invalidation:{org_id}"
        flag_value = redis_client.get(key)

        if flag_value is None:
            # No invalidation flag set - no changes
            return False

        # Parse timestamp from flag
        flag_timestamp = float(flag_value)
        last_known = _invalidation_timestamps.get(org_id, 0)

        # Check if flag is newer than our last known state
        if flag_timestamp > last_known:
            logger.info(
                "Connector change detected from another worker",
                organization_id=org_id,
                flag_timestamp=flag_timestamp,
                last_known=last_known
            )
            # Update our known timestamp
            _invalidation_timestamps[org_id] = flag_timestamp
            return True

        return False

    except Exception as e:
        logger.warning(
            "Error checking invalidation flag",
            organization_id=org_id,
            error=str(e)
        )
        # On error, don't trigger refresh to avoid unnecessary work
        return False


def _cleanup_generator(generator: "SQLGenerator") -> None:
    """
    Clean up resources held by a SQLGenerator instance.

    Called when removing an instance from the cache.
    """
    try:
        # Close database connection if present
        if hasattr(generator, 'db_client') and generator.db_client:
            if hasattr(generator.db_client, 'disconnect'):
                generator.db_client.disconnect()
            elif hasattr(generator.db_client, 'close'):
                generator.db_client.close()

        logger.debug("Cleaned up SQLGenerator resources")
    except Exception as e:
        logger.warning(f"Error cleaning up SQLGenerator: {e}")
