"""
Shared clients that don't require organization context.
Used for components like LLM that are tenant-agnostic.

This module provides thread-safe singleton access to shared resources
that can be used across all organizations without multi-tenancy concerns.
"""

import threading
from typing import Optional
import structlog

from src.core.llm_client import LLMClient
from src.core.cache_manager import CacheManager
from src.config import settings

logger = structlog.get_logger()

# Shared LLM client (not org-specific)
_llm_client: Optional[LLMClient] = None
_llm_lock = threading.Lock()

# Shared cache manager (for org-independent caching)
_cache_manager: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_shared_llm_client() -> LLMClient:
    """
    Get shared LLM client (not org-specific).

    The LLM client is tenant-agnostic and can be safely shared across
    all organizations. It uses the same API keys and model configuration
    regardless of which organization is making the request.

    Returns:
        LLMClient: Thread-safe singleton LLM client instance
    """
    global _llm_client
    if _llm_client is None:
        with _llm_lock:
            if _llm_client is None:
                _llm_client = LLMClient()
                logger.info("Initialized shared LLM client")
    return _llm_client


def get_shared_cache_manager() -> Optional[CacheManager]:
    """
    Get shared cache manager for org-independent caching.

    This cache manager is used for:
    - Health checks (checking Redis connectivity)
    - Shared caching that doesn't require org isolation

    For org-specific caching, use the cache_manager from get_sql_generator(org_id).

    Returns:
        Optional[CacheManager]: Thread-safe singleton cache manager, or None if disabled
    """
    global _cache_manager
    if _cache_manager is None and settings.cache_enabled:
        with _cache_lock:
            if _cache_manager is None:
                try:
                    _cache_manager = CacheManager(
                        redis_url=settings.redis_url,
                        host=settings.redis_host,
                        port=settings.redis_port,
                        db=settings.redis_db
                    )
                    logger.info("Initialized shared cache manager")
                except Exception as e:
                    logger.warning(f"Failed to initialize shared cache manager: {e}")
    return _cache_manager


def reset_shared_clients():
    """
    Reset all shared clients (useful for testing).
    """
    global _llm_client, _cache_manager
    with _llm_lock:
        _llm_client = None
    with _cache_lock:
        _cache_manager = None
    logger.info("Reset shared clients")
