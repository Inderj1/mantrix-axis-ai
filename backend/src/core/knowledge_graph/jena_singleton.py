"""
Singleton pattern for Jena knowledge graph to avoid reloading data.

Supports multiple backends:
- redis: Redis-cached store for multi-process sharing (default)
- postgres: PostgreSQL-backed persistent storage (recommended for ECS)
- memory: In-memory store for single-process performance
"""

import os
import threading
import structlog
from typing import Optional
from .jena_client import JenaKnowledgeGraph
from .jena_query_resolver import JenaQueryResolver

logger = structlog.get_logger()

# Thread-safe singleton instance
_jena_instance_lock = threading.Lock()
_jena_graph: Optional[JenaKnowledgeGraph] = None
_jena_resolver: Optional[JenaQueryResolver] = None

# Backend selection: redis (default), postgres, memory
JENA_BACKEND = os.getenv("JENA_BACKEND", "redis")


def get_jena_knowledge_graph(redis_client=None, use_cache: Optional[str] = None) -> JenaKnowledgeGraph:
    """Get or create singleton instance of Jena knowledge graph.

    Backend priority:
    1. Explicit use_cache parameter
    2. JENA_BACKEND environment variable
    3. Default to "redis"

    Args:
        redis_client: Optional Redis client to use for caching
        use_cache: Optional override for backend selection (redis, postgres, memory)

    Returns:
        JenaKnowledgeGraph singleton instance
    """
    global _jena_graph

    if _jena_graph is None:
        with _jena_instance_lock:
            # Double-check pattern
            if _jena_graph is None:
                backend = use_cache or JENA_BACKEND
                logger.info(f"Initializing JenaKnowledgeGraph with backend: {backend}")

                _jena_graph = JenaKnowledgeGraph(use_cache=backend)

                # If Redis client provided and using Redis backend, set it
                if redis_client and backend == "redis" and hasattr(_jena_graph, 'graph'):
                    from .jena_redis_store import _redis_store
                    if _redis_store:
                        _redis_store.redis = redis_client

    return _jena_graph


def get_jena_query_resolver() -> JenaQueryResolver:
    """Get or create singleton instance of Jena query resolver."""
    global _jena_resolver
    
    if _jena_resolver is None:
        with _jena_instance_lock:
            # Double-check pattern
            if _jena_resolver is None:
                kg = get_jena_knowledge_graph()
                _jena_resolver = JenaQueryResolver(kg)
    
    return _jena_resolver


def clear_jena_cache():
    """Clear the singleton instances (useful for testing or reloading)."""
    global _jena_graph, _jena_resolver
    
    with _jena_instance_lock:
        if _jena_resolver:
            _jena_resolver.close()
        if _jena_graph:
            _jena_graph.close()
        
        _jena_graph = None
        _jena_resolver = None