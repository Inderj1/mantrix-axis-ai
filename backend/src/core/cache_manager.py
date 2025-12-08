"""
Redis cache manager for NLP to SQL system.
Handles caching of SQL generations, schemas, embeddings, and query results.
"""

import hashlib
import json
import redis
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
import structlog
from dataclasses import dataclass, asdict
import time
import pickle

logger = structlog.get_logger()

@dataclass
class CacheStats:
    """Track cache performance metrics."""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    avg_hit_latency_ms: float = 0.0
    avg_miss_latency_ms: float = 0.0
    total_savings_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_requests if self.total_requests > 0 else 0.0


class CacheManager:
    """Manages all caching operations for the NLP to SQL system."""
    
    # Cache key prefixes
    PREFIX_SQL = "sql:"
    PREFIX_SCHEMA = "schema:"
    PREFIX_EMBEDDING = "embedding:"
    PREFIX_VALIDATION = "validation:"
    PREFIX_RESULT = "result:"
    PREFIX_SESSION = "session:"
    PREFIX_MV_LIST = "mv:list:"
    PREFIX_MV_STATS = "mv:stats:"
    PREFIX_MV_RECOMMENDATIONS = "mv:recommendations:"
    PREFIX_MV_COST = "mv:cost:"
    PREFIX_OPTIMIZATION_REPORT = "optimization:report:"
    PREFIX_WEAVIATE_SEARCH = "weaviate:"
    PREFIX_JOIN_PATH = "join_path:"  # For caching JOIN path discoveries

    # Default TTLs (in seconds)
    TTL_SQL_FREQUENT = 7 * 24 * 60 * 60  # 7 days for frequent queries
    TTL_SQL_INFREQUENT = 24 * 60 * 60    # 1 day for infrequent queries
    TTL_SCHEMA = 24 * 60 * 60             # 24 hours for schemas
    TTL_EMBEDDING = 30 * 24 * 60 * 60     # 30 days for embeddings
    TTL_VALIDATION = 60 * 60              # 1 hour for validation results
    TTL_RESULT = 5 * 60                   # 5 minutes for query results (configurable)
    TTL_SESSION = 24 * 60 * 60            # 24 hours for session data
    TTL_MV_LIST = 6 * 60 * 60             # 6 hours for MV list
    TTL_MV_STATS = 60 * 60                # 1 hour for MV statistics
    TTL_MV_RECOMMENDATIONS = 24 * 60 * 60 # 24 hours for recommendations
    TTL_MV_COST = 7 * 24 * 60 * 60       # 7 days for cost estimates
    TTL_OPTIMIZATION_REPORT = 60 * 60     # 1 hour for optimization reports
    TTL_WEAVIATE_SEARCH = 24 * 60 * 60    # 24 hours for vector search results
    TTL_JOIN_PATH = 24 * 60 * 60          # 24 hours for JOIN path cache (invalidate on schema sync)

    def __init__(self, 
                 redis_url: Optional[str] = None,
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 decode_responses: bool = False,
                 max_connections: int = 50):
        """
        Initialize cache manager with Redis connection.
        
        Args:
            redis_url: Full Redis URL (for cloud deployments)
            host: Redis host (for local deployments)
            port: Redis port
            db: Redis database number
            decode_responses: Whether to decode responses as strings
            max_connections: Maximum number of connections in pool
        """
        try:
            if redis_url:
                self.redis = redis.from_url(
                    redis_url, 
                    decode_responses=decode_responses,
                    max_connections=max_connections
                )
            else:
                pool = redis.ConnectionPool(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=decode_responses,
                    max_connections=max_connections
                )
                self.redis = redis.Redis(connection_pool=pool)
            
            # Test connection
            self.redis.ping()
            logger.info("Redis cache connected successfully")
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        self.stats = CacheStats()
        self.enabled = True  # Cache is enabled if connection successful
        self.redis_client = self.redis  # Alias for compatibility
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate a cache key with prefix."""
        return f"{prefix}{identifier}"
    
    def _hash_dict(self, data: Dict[str, Any]) -> str:
        """Generate a stable hash for a dictionary."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(data or {}, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize a query for consistent cache keys."""
        if query is None:
            return ""
        # Convert to lowercase, strip whitespace, compress spaces
        normalized = " ".join(query.lower().strip().split())
        return normalized
    
    # Generic cache methods
    
    def get(self, key: str) -> Optional[str]:
        """Generic get method for string values."""
        if not self.enabled:
            return None
        
        try:
            value = self.redis.get(key)
            if value is None:
                return None
            # If decode_responses=True, value is already a string
            if isinstance(value, str):
                return value
            # If decode_responses=False, value is bytes and needs decoding
            return value.decode('utf-8')
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = 3600):
        """Generic set method for string values."""
        if not self.enabled:
            return
        
        try:
            self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    # SQL Query Caching
    
    def get_or_generate_sql(self,
                           query: str,
                           table_context: List[Dict[str, Any]],
                           generator_func: Callable,
                           force_refresh: bool = False,
                           connector_ids: Optional[List[str]] = None) -> Tuple[Dict[str, Any], bool]:
        """
        Get SQL from cache or generate if not found.

        Args:
            query: Natural language query
            table_context: List of relevant table schemas
            generator_func: Function to generate SQL if cache miss
            force_refresh: Force regeneration even if cached
            connector_ids: List of connector IDs for cache isolation

        Returns:
            Tuple of (result, from_cache)
        """
        start_time = time.time()

        # Generate cache key
        normalized_query = self._normalize_query(query)

        # Safely extract table names
        table_names = []
        if table_context and isinstance(table_context, list):
            for t in table_context:
                if isinstance(t, dict) and "table_name" in t:
                    table_names.append(t["table_name"])
                elif isinstance(t, str):
                    table_names.append(t)

        # Include connector_ids in context hash for cache isolation
        context_data = {"tables": table_names}
        if connector_ids:
            context_data["connector_ids"] = sorted(connector_ids)  # Sort for consistent hashing

        context_hash = self._hash_dict(context_data)
        cache_key = self._generate_key(
            self.PREFIX_SQL,
            f"{hashlib.sha256((normalized_query or '').encode()).hexdigest()}:{context_hash}"
        )
        
        # Try to get from cache
        if not force_refresh:
            cached_result = self.get_sql_generation(cache_key)
            if cached_result:
                self._record_hit(time.time() - start_time)
                return cached_result, True
        
        # Cache miss - generate new SQL
        self._record_miss(time.time() - start_time)
        result = generator_func(query, table_context)

        # NOTE: Do NOT cache here - let cache_validated_sql() handle caching
        # after execution, so we can check for empty results and errors.
        # Previously this would cache before execution, causing queries that
        # return empty results to be cached and keep returning empty.

        return result, False
    
    def cache_sql_generation(self, key: str, result: Dict[str, Any], query: str) -> None:
        """Cache a successful SQL generation."""
        try:
            # Add metadata
            result["cached_at"] = datetime.now().isoformat()
            result["normalized_query"] = query
            result["hit_count"] = 0
            
            # Determine TTL based on complexity
            ttl = self.TTL_SQL_FREQUENT if result.get("estimated_complexity") == "high" else self.TTL_SQL_INFREQUENT
            
            # Store in Redis
            self.redis.setex(
                key,
                ttl,
                json.dumps(result)
            )
            
            # Update query frequency tracking
            self._track_query_frequency(query)
            
            logger.info(f"Cached SQL generation: {key[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to cache SQL generation: {e}")

    def cache_validated_sql(
        self,
        key: str,
        result: Dict[str, Any],
        query: str,
        execution_time_ms: float,
        row_count: int,
        validation_status: bool,
        error_details: Optional[str] = None,
        confidence_score: Optional[float] = None
    ) -> bool:
        """
        Cache a validated and successfully executed SQL query with quality metadata.

        This method enforces quality gates and only caches queries that meet all criteria:
        - Passed BigQuery validation (if required)
        - Executed successfully (if test execution required)
        - Meets performance thresholds
        - Meets confidence thresholds

        Args:
            key: Cache key
            result: SQL generation result from LLM
            query: Normalized query string
            execution_time_ms: Time taken to execute query in milliseconds
            row_count: Number of rows returned
            validation_status: Whether query passed BigQuery validation
            error_details: Error message if any (None if successful)
            confidence_score: LLM confidence score (0-1)

        Returns:
            bool: True if cached, False if rejected
        """
        from src.config import settings

        try:
            # QUALITY GATE 1: Validation required?
            if settings.cache_validation_required and not validation_status:
                logger.warning(f"Rejecting cache - validation failed: {error_details}")
                return False

            # QUALITY GATE 2: Execution errors?
            if error_details:
                logger.warning(f"Rejecting cache - execution error: {error_details}")
                return False

            # QUALITY GATE 2.5: Empty results (configurable)
            if row_count == 0 and settings.cache_reject_empty_results:
                logger.warning(f"Rejecting cache - query returned no results")
                return False

            # QUALITY GATE 3: Confidence threshold
            if confidence_score is not None and confidence_score < settings.cache_min_confidence:
                logger.warning(f"Rejecting cache - low confidence: {confidence_score:.2f} < {settings.cache_min_confidence}")
                return False

            # QUALITY GATE 4: Row count threshold (mark as suspect if exceeded)
            suspect_high_rows = row_count > settings.cache_max_rows_threshold

            # Add execution metadata to result
            result["execution_metadata"] = {
                "execution_time_ms": execution_time_ms,
                "row_count": row_count,
                "validation_status": validation_status,
                "error_details": error_details,
                "confidence_score": confidence_score,
                "cached_at": datetime.now().isoformat(),
                "cache_version": "2.0",  # Smart caching version
                "suspect_high_rows": suspect_high_rows
            }
            result["normalized_query"] = query
            result["hit_count"] = 0

            # Determine cache quality tier and TTL
            cache_tier, ttl = self._determine_cache_tier(
                execution_time_ms=execution_time_ms,
                confidence_score=confidence_score or 0.5,
                suspect_high_rows=suspect_high_rows
            )

            result["cache_tier"] = cache_tier

            # Store in Redis
            self.redis.setex(
                key,
                ttl,
                json.dumps(result)
            )

            # Update query frequency tracking
            self._track_query_frequency(query)

            logger.info(
                f"Cached validated SQL [{cache_tier} tier, {ttl}s TTL]: "
                f"{execution_time_ms:.0f}ms, {row_count} rows, "
                f"confidence={confidence_score or 0:.2f}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to cache validated SQL: {e}")
            return False

    def _determine_cache_tier(
        self,
        execution_time_ms: float,
        confidence_score: float,
        suspect_high_rows: bool
    ) -> tuple[str, int]:
        """
        Determine cache quality tier and TTL based on query performance.

        Returns:
            tuple: (tier_name, ttl_seconds)
        """
        from src.config import settings

        # GOLD TIER: Fast (<5s), high confidence, reasonable row count
        if (
            execution_time_ms < 5000
            and confidence_score >= 0.9
            and not suspect_high_rows
        ):
            return ("GOLD", settings.cache_ttl_gold)

        # BRONZE TIER: Slow (>30s) or suspect rows
        elif (
            execution_time_ms > settings.cache_execution_threshold_ms
            or suspect_high_rows
        ):
            return ("BRONZE", settings.cache_ttl_bronze)

        # SILVER TIER: Everything else that passed gates
        else:
            return ("SILVER", settings.cache_ttl_silver)

    def get_sql_generation(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve SQL generation from cache."""
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                result = json.loads(cached_data)
                
                # Update hit count
                result["hit_count"] = result.get("hit_count", 0) + 1
                self.redis.setex(
                    key,
                    self.redis.ttl(key),  # Preserve existing TTL
                    json.dumps(result)
                )
                
                return result
            
        except Exception as e:
            logger.error(f"Failed to get cached SQL: {e}")
        
        return None
    
    # Schema Caching
    
    def cache_schema(self, project: str, dataset: str, table: str, schema: Dict[str, Any]) -> None:
        """Cache a table schema."""
        key = self._generate_key(
            self.PREFIX_SCHEMA,
            f"{project}:{dataset}:{table}"
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_SCHEMA,
                json.dumps(schema)
            )
            logger.info(f"Cached schema for {table}")
            
        except Exception as e:
            logger.error(f"Failed to cache schema: {e}")
    
    def get_schema(self, project: str, dataset: str, table: str) -> Optional[Dict[str, Any]]:
        """Get cached schema."""
        key = self._generate_key(
            self.PREFIX_SCHEMA,
            f"{project}:{dataset}:{table}"
        )

        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return json.loads(cached_data)

        except Exception as e:
            logger.error(f"Failed to get cached schema: {e}")

        return None

    def get_cached_schema(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached schema using a direct cache key.
        Used by format_normalizer and other modules that generate their own cache keys.

        Args:
            cache_key: Direct cache key (not prefixed)

        Returns:
            Cached data as dictionary or None
        """
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Failed to get cached schema with key {cache_key}: {e}")

        return None

    def set_cached_schema(self, cache_key: str, data: Dict[str, Any], ttl: int = None) -> None:
        """
        Set cached schema using a direct cache key.
        Used by format_normalizer and other modules that generate their own cache keys.

        Args:
            cache_key: Direct cache key (not prefixed)
            data: Data to cache
            ttl: Time to live in seconds (default: TTL_SCHEMA)
        """
        if ttl is None:
            ttl = self.TTL_SCHEMA

        try:
            self.redis.setex(cache_key, ttl, json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to set cached schema with key {cache_key}: {e}")
    
    def invalidate_schema_cache(self, project: str, dataset: str, table: Optional[str] = None) -> int:
        """Invalidate schema cache for a table or entire dataset."""
        pattern = self._generate_key(
            self.PREFIX_SCHEMA,
            f"{project}:{dataset}:{table or '*'}"
        )
        
        deleted = 0
        for key in self.redis.scan_iter(match=pattern):
            self.redis.delete(key)
            deleted += 1
        
        logger.info(f"Invalidated {deleted} schema cache entries")
        return deleted
    
    # Embedding Caching
    
    def cache_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache an embedding vector."""
        key = self._generate_key(
            self.PREFIX_EMBEDDING,
            hashlib.sha256((text or '').encode()).hexdigest()
        )
        
        try:
            # Use pickle for efficient storage of float arrays
            self.redis.setex(
                key,
                self.TTL_EMBEDDING,
                pickle.dumps(embedding)
            )
            
        except Exception as e:
            logger.error(f"Failed to cache embedding: {e}")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding."""
        key = self._generate_key(
            self.PREFIX_EMBEDDING,
            hashlib.sha256((text or '').encode()).hexdigest()
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return pickle.loads(cached_data)
                
        except Exception as e:
            logger.error(f"Failed to get cached embedding: {e}")
        
        return None

    # Weaviate Vector Search Caching

    def _generate_weaviate_cache_key(
        self,
        embedding: List[float],
        organization_id: str,
        connector_ids: Optional[List[str]],
        limit: int
    ) -> str:
        """Generate cache key for Weaviate vector search results."""
        import numpy as np

        # Hash embedding vector (16 hex chars for efficiency)
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
        embedding_hash = hashlib.sha256(embedding_bytes).hexdigest()[:16]

        # Hash sorted connector IDs for consistent key
        if connector_ids:
            connector_str = ','.join(sorted(connector_ids))
            connector_hash = hashlib.sha256(connector_str.encode()).hexdigest()[:16]
        else:
            connector_hash = "none"

        return self._generate_key(
            self.PREFIX_WEAVIATE_SEARCH,
            f"{embedding_hash}:{organization_id or 'default'}:{connector_hash}:{limit}"
        )

    def cache_weaviate_search(
        self,
        embedding: List[float],
        organization_id: str,
        connector_ids: Optional[List[str]],
        limit: int,
        results: List[Dict[str, Any]]
    ) -> None:
        """Cache Weaviate vector search results."""
        key = self._generate_weaviate_cache_key(embedding, organization_id, connector_ids, limit)

        try:
            cache_data = {
                "results": results,
                "cached_at": datetime.now().isoformat(),
                "limit": limit,
                "organization_id": organization_id
            }
            self.redis.setex(
                key,
                self.TTL_WEAVIATE_SEARCH,
                json.dumps(cache_data)
            )
            logger.debug(f"Cached Weaviate search: {len(results)} results, key={key[:50]}...")

        except Exception as e:
            logger.error(f"Failed to cache Weaviate search: {e}")

    def get_weaviate_search(
        self,
        embedding: List[float],
        organization_id: str,
        connector_ids: Optional[List[str]],
        limit: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached Weaviate vector search results."""
        key = self._generate_weaviate_cache_key(embedding, organization_id, connector_ids, limit)

        try:
            cached_data = self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Weaviate cache HIT: {len(data.get('results', []))} results")
                return data.get("results")

        except Exception as e:
            logger.error(f"Failed to get cached Weaviate search: {e}")

        return None

    def invalidate_weaviate_search_by_org(self, organization_id: str) -> int:
        """Invalidate all Weaviate search cache entries for an organization."""
        pattern = f"{self.PREFIX_WEAVIATE_SEARCH}*:{organization_id}:*"
        deleted = 0

        try:
            for key in self.redis.scan_iter(match=pattern):
                self.redis.delete(key)
                deleted += 1
            logger.info(f"Invalidated {deleted} Weaviate cache entries for org {organization_id}")

        except Exception as e:
            logger.error(f"Failed to invalidate Weaviate cache: {e}")

        return deleted

    # Validation Caching

    def cache_validation(self, sql: str, validation_result: Dict[str, Any]) -> None:
        """Cache SQL validation result."""
        key = self._generate_key(
            self.PREFIX_VALIDATION,
            hashlib.sha256((sql or '').encode()).hexdigest()
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_VALIDATION,
                json.dumps(validation_result)
            )
            
        except Exception as e:
            logger.error(f"Failed to cache validation: {e}")
    
    def get_validation(self, sql: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result."""
        key = self._generate_key(
            self.PREFIX_VALIDATION,
            hashlib.sha256((sql or '').encode()).hexdigest()
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return json.loads(cached_data)
                
        except Exception as e:
            logger.error(f"Failed to get cached validation: {e}")
        
        return None
    
    # Query Result Caching (for reference data)
    
    def cache_query_result(self, sql: str, result: List[Dict[str, Any]], ttl: Optional[int] = None) -> None:
        """Cache query execution results."""
        key = self._generate_key(
            self.PREFIX_RESULT,
            hashlib.sha256((sql or '').encode()).hexdigest()
        )
        
        try:
            self.redis.setex(
                key,
                ttl or self.TTL_RESULT,
                json.dumps({
                    "result": result,
                    "cached_at": datetime.now().isoformat(),
                    "row_count": len(result)
                })
            )
            
        except Exception as e:
            logger.error(f"Failed to cache query result: {e}")
    
    def get_query_result(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached query results."""
        key = self._generate_key(
            self.PREFIX_RESULT,
            hashlib.sha256((sql or '').encode()).hexdigest()
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                return data.get("result")
                
        except Exception as e:
            logger.error(f"Failed to get cached result: {e}")
        
        return None
    
    # Session Management
    
    def save_session_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Save user session context."""
        key = self._generate_key(
            self.PREFIX_SESSION,
            f"{session_id}:context"
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_SESSION,
                json.dumps(context)
            )
            
        except Exception as e:
            logger.error(f"Failed to save session context: {e}")
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session context."""
        key = self._generate_key(
            self.PREFIX_SESSION,
            f"{session_id}:context"
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return json.loads(cached_data)
                
        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
        
        return None
    
    # Query Similarity and Suggestions
    
    def find_similar_queries(self, query: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find similar cached queries using embeddings."""
        similar_queries = []
        
        # This would integrate with the embedding system
        # For now, return empty list
        # TODO: Implement similarity search using cached embeddings
        
        return similar_queries
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular cached queries."""
        popular = []
        
        try:
            # Scan for SQL cache keys
            for key in self.redis.scan_iter(match=f"{self.PREFIX_SQL}*", count=100):
                cached_data = self.redis.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    popular.append({
                        "query": data.get("normalized_query", ""),
                        "hit_count": data.get("hit_count", 0),
                        "sql": data.get("sql", "")
                    })
            
            # Sort by hit count
            popular.sort(key=lambda x: x["hit_count"], reverse=True)
            return popular[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get popular queries: {e}")
            return []
    
    # Statistics and Monitoring
    
    def _record_hit(self, latency_ms: float) -> None:
        """Record a cache hit."""
        self.stats.hits += 1
        self.stats.total_requests += 1
        self.stats.avg_hit_latency_ms = (
            (self.stats.avg_hit_latency_ms * (self.stats.hits - 1) + latency_ms * 1000) 
            / self.stats.hits
        )
        self.stats.total_savings_ms += latency_ms * 1000
    
    def _record_miss(self, latency_ms: float) -> None:
        """Record a cache miss."""
        self.stats.misses += 1
        self.stats.total_requests += 1
        self.stats.avg_miss_latency_ms = (
            (self.stats.avg_miss_latency_ms * (self.stats.misses - 1) + latency_ms * 1000) 
            / self.stats.misses
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        info = self.redis.info()
        
        return {
            "performance": asdict(self.stats),
            "hit_rate_percent": round(self.stats.hit_rate * 100, 2),
            "redis_info": {
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_connections_received": info.get("total_connections_received"),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
            }
        }
    
    def _track_query_frequency(self, query: str) -> None:
        """Track query frequency for cache warming."""
        freq_key = f"freq:{hashlib.sha256((query or '').encode()).hexdigest()}"
        
        try:
            # Increment frequency counter
            self.redis.incr(freq_key)
            
            # Set expiry to 30 days
            self.redis.expire(freq_key, 30 * 24 * 60 * 60)
            
        except Exception as e:
            logger.error(f"Failed to track query frequency: {e}")
    
    def get_query_frequency(self, query: str) -> int:
        """Get the frequency count for a query."""
        freq_key = f"freq:{hashlib.sha256((query or '').encode()).hexdigest()}"
        
        try:
            freq = self.redis.get(freq_key)
            return int(freq) if freq else 0
            
        except Exception as e:
            logger.error(f"Failed to get query frequency: {e}")
            return 0
    
    # Materialized View Caching
    
    def cache_mv_list(self, project: str, dataset: str, mv_list: List[Dict[str, Any]]) -> None:
        """Cache the list of materialized views."""
        key = self._generate_key(
            self.PREFIX_MV_LIST,
            f"{project}:{dataset}"
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_MV_LIST,
                json.dumps({
                    "views": mv_list,
                    "cached_at": datetime.now().isoformat(),
                    "count": len(mv_list)
                })
            )
            logger.info(f"Cached MV list for {project}.{dataset}")
            
        except Exception as e:
            logger.error(f"Failed to cache MV list: {e}")
    
    def get_mv_list(self, project: str, dataset: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached list of materialized views."""
        key = self._generate_key(
            self.PREFIX_MV_LIST,
            f"{project}:{dataset}"
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                return data.get("views")
                
        except Exception as e:
            logger.error(f"Failed to get cached MV list: {e}")
        
        return None
    
    def cache_mv_stats(self, project: str, dataset: str, view_name: str, stats: Dict[str, Any]) -> None:
        """Cache materialized view statistics."""
        key = self._generate_key(
            self.PREFIX_MV_STATS,
            f"{project}:{dataset}:{view_name}"
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_MV_STATS,
                json.dumps(stats)
            )
            
        except Exception as e:
            logger.error(f"Failed to cache MV stats: {e}")
    
    def get_mv_stats(self, project: str, dataset: str, view_name: str) -> Optional[Dict[str, Any]]:
        """Get cached materialized view statistics."""
        key = self._generate_key(
            self.PREFIX_MV_STATS,
            f"{project}:{dataset}:{view_name}"
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return json.loads(cached_data)
                
        except Exception as e:
            logger.error(f"Failed to get cached MV stats: {e}")
        
        return None
    
    def cache_mv_recommendations(self, recommendations: List[Dict[str, Any]]) -> None:
        """Cache MV recommendations."""
        key = self._generate_key(
            self.PREFIX_MV_RECOMMENDATIONS,
            "current"
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_MV_RECOMMENDATIONS,
                json.dumps({
                    "recommendations": recommendations,
                    "cached_at": datetime.now().isoformat(),
                    "count": len(recommendations)
                })
            )
            logger.info(f"Cached {len(recommendations)} MV recommendations")
            
        except Exception as e:
            logger.error(f"Failed to cache MV recommendations: {e}")
    
    def get_mv_recommendations(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached MV recommendations."""
        key = self._generate_key(
            self.PREFIX_MV_RECOMMENDATIONS,
            "current"
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                return data.get("recommendations")
                
        except Exception as e:
            logger.error(f"Failed to get cached MV recommendations: {e}")
        
        return None
    
    def cache_optimization_report(self, report: Dict[str, Any]) -> None:
        """Cache optimization report."""
        key = self._generate_key(
            self.PREFIX_OPTIMIZATION_REPORT,
            "current"
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_OPTIMIZATION_REPORT,
                json.dumps(report)
            )
            
        except Exception as e:
            logger.error(f"Failed to cache optimization report: {e}")
    
    def get_optimization_report(self) -> Optional[Dict[str, Any]]:
        """Get cached optimization report."""
        key = self._generate_key(
            self.PREFIX_OPTIMIZATION_REPORT,
            "current"
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return json.loads(cached_data)
                
        except Exception as e:
            logger.error(f"Failed to get cached optimization report: {e}")
        
        return None
    
    def invalidate_mv_cache(self, project: str, dataset: str, view_name: Optional[str] = None) -> int:
        """Invalidate MV-related caches."""
        deleted = 0
        
        try:
            # Invalidate MV list
            list_key = self._generate_key(self.PREFIX_MV_LIST, f"{project}:{dataset}")
            if self.redis.delete(list_key):
                deleted += 1
            
            # Invalidate specific MV stats or all stats
            if view_name:
                stats_key = self._generate_key(self.PREFIX_MV_STATS, f"{project}:{dataset}:{view_name}")
                if self.redis.delete(stats_key):
                    deleted += 1
            else:
                # Invalidate all MV stats for the dataset
                pattern = self._generate_key(self.PREFIX_MV_STATS, f"{project}:{dataset}:*")
                for key in self.redis.scan_iter(match=pattern):
                    self.redis.delete(key)
                    deleted += 1
            
            # Invalidate recommendations and optimization report as they may be stale
            rec_key = self._generate_key(self.PREFIX_MV_RECOMMENDATIONS, "current")
            if self.redis.delete(rec_key):
                deleted += 1
                
            opt_key = self._generate_key(self.PREFIX_OPTIMIZATION_REPORT, "current")
            if self.redis.delete(opt_key):
                deleted += 1
            
            logger.info(f"Invalidated {deleted} MV cache entries")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to invalidate MV cache: {e}")
            return 0
    
    def cache_mv_cost_estimate(self, template_name: str, cost_data: Dict[str, float]) -> None:
        """Cache MV cost estimate."""
        key = self._generate_key(
            self.PREFIX_MV_COST,
            template_name
        )
        
        try:
            self.redis.setex(
                key,
                self.TTL_MV_COST,
                json.dumps(cost_data)
            )
            
        except Exception as e:
            logger.error(f"Failed to cache MV cost estimate: {e}")
    
    def get_mv_cost_estimate(self, template_name: str) -> Optional[Dict[str, float]]:
        """Get cached MV cost estimate."""
        key = self._generate_key(
            self.PREFIX_MV_COST,
            template_name
        )
        
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                return json.loads(cached_data)
                
        except Exception as e:
            logger.error(f"Failed to get cached MV cost estimate: {e}")
        
        return None
    
    def warm_mv_cache(self, mv_manager) -> None:
        """Warm MV-related caches."""
        try:
            # Get and cache MV list
            mv_list = mv_manager.list_materialized_views(
                mv_manager.bq_client.project,
                mv_manager.bq_client.dataset
            )
            self.cache_mv_list(
                mv_manager.bq_client.project,
                mv_manager.bq_client.dataset,
                mv_list
            )
            
            # Cache stats for each MV
            for mv in mv_list:
                if 'error' not in mv:
                    try:
                        stats = mv_manager.get_materialized_view_stats(
                            mv_manager.bq_client.project,
                            mv_manager.bq_client.dataset,
                            mv['name']
                        )
                        # Convert stats object to dict for caching
                        stats_dict = {
                            "view_name": stats.view_name,
                            "created_at": stats.created_at.isoformat(),
                            "last_refreshed": stats.last_refreshed.isoformat(),
                            "size_bytes": stats.size_bytes,
                            "row_count": stats.row_count,
                            "query_count": stats.query_count,
                            "avg_query_time_saved_ms": stats.avg_query_time_saved_ms,
                            "estimated_monthly_cost": stats.estimated_monthly_cost,
                            "staleness_hours": stats.staleness_hours
                        }
                        self.cache_mv_stats(
                            mv_manager.bq_client.project,
                            mv_manager.bq_client.dataset,
                            mv['name'],
                            stats_dict
                        )
                    except Exception as e:
                        logger.warning(f"Could not cache stats for MV {mv['name']}: {e}")
            
            logger.info(f"Warmed MV cache with {len(mv_list)} views")
            
        except Exception as e:
            logger.error(f"Failed to warm MV cache: {e}")

    def invalidate_failed_queries(self) -> Dict[str, int]:
        """
        Scan cache and invalidate entries that represent failed or low-quality queries.

        This method removes cache entries that:
        - Have execution errors
        - Failed validation
        - Exceed performance thresholds
        - Have old cache version (pre-smart caching)

        Returns:
            Dict with counts of different invalidation reasons
        """
        invalidation_stats = {
            "execution_errors": 0,
            "validation_failed": 0,
            "slow_queries": 0,
            "old_version": 0,
            "total_deleted": 0
        }

        try:
            # Scan all SQL cache keys
            for key in self.redis.scan_iter(match=f"{self.PREFIX_SQL}*"):
                try:
                    cached_data = self.redis.get(key)
                    if not cached_data:
                        continue

                    result = json.loads(cached_data)
                    should_invalidate = False
                    reason = None

                    # Check for execution metadata (smart cache v2.0)
                    exec_meta = result.get("execution_metadata", {})

                    # Reason 1: Old cache version (no metadata)
                    if not exec_meta:
                        should_invalidate = True
                        reason = "old_version"
                        invalidation_stats["old_version"] += 1

                    # Reason 2: Execution errors
                    elif exec_meta.get("error_details"):
                        should_invalidate = True
                        reason = "execution_errors"
                        invalidation_stats["execution_errors"] += 1

                    # Reason 3: Validation failed
                    elif not exec_meta.get("validation_status", True):
                        should_invalidate = True
                        reason = "validation_failed"
                        invalidation_stats["validation_failed"] += 1

                    # Reason 4: Excessively slow (3x threshold)
                    elif exec_meta.get("execution_time_ms", 0) > (self.settings.cache_execution_threshold_ms * 3):
                        should_invalidate = True
                        reason = "slow_queries"
                        invalidation_stats["slow_queries"] += 1

                    if should_invalidate:
                        self.redis.delete(key)
                        invalidation_stats["total_deleted"] += 1
                        logger.debug(f"Invalidated cache key for {reason}: {key[:50]}...")

                except json.JSONDecodeError:
                    # Corrupted cache entry, delete it
                    self.redis.delete(key)
                    invalidation_stats["total_deleted"] += 1
                except Exception as e:
                    logger.warning(f"Error checking cache entry {key}: {e}")

            logger.info(
                f"Cache invalidation complete: {invalidation_stats['total_deleted']} deleted "
                f"(errors: {invalidation_stats['execution_errors']}, "
                f"validation: {invalidation_stats['validation_failed']}, "
                f"slow: {invalidation_stats['slow_queries']}, "
                f"old: {invalidation_stats['old_version']})"
            )

            return invalidation_stats

        except Exception as e:
            logger.error(f"Failed to invalidate failed queries: {e}")
            return invalidation_stats

    def clear_all_caches(self) -> int:
        """Clear all caches (use with caution)."""
        deleted = 0
        
        try:
            for prefix in [self.PREFIX_SQL, self.PREFIX_SCHEMA, self.PREFIX_EMBEDDING,
                          self.PREFIX_VALIDATION, self.PREFIX_RESULT, self.PREFIX_SESSION,
                          self.PREFIX_MV_LIST, self.PREFIX_MV_STATS, self.PREFIX_MV_RECOMMENDATIONS,
                          self.PREFIX_MV_COST, self.PREFIX_OPTIMIZATION_REPORT]:
                for key in self.redis.scan_iter(match=f"{prefix}*"):
                    self.redis.delete(key)
                    deleted += 1
            
            logger.warning(f"Cleared {deleted} cache entries")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Check cache health."""
        try:
            start = time.time()
            self.redis.ping()
            latency_ms = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "stats": self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }