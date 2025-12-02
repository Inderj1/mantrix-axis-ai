"""
Integration tests for CacheManager with real Redis.

These tests require Redis to be running on localhost:6379.
Run with: pytest tests/integration/test_cache_integration.py -v
"""

import pytest
import time
import json
import hashlib
from typing import Dict, Any


# Skip all tests if Redis is not available
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def cache_manager():
    """Create a real CacheManager connected to Redis."""
    from src.core.cache_manager import CacheManager

    try:
        cm = CacheManager(
            host="localhost",
            port=6379,
            db=15,  # Use DB 15 for testing to avoid conflicts
            decode_responses=False
        )
        # Verify connection
        cm.redis.ping()
        yield cm
        # Cleanup: clear test database after tests
        cm.redis.flushdb()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


@pytest.fixture(autouse=True)
def clear_test_keys(cache_manager):
    """Clear any test keys before each test."""
    # Clear keys with test prefix
    for key in cache_manager.redis.scan_iter("test:*"):
        cache_manager.redis.delete(key)
    for key in cache_manager.redis.scan_iter("sql:*"):
        cache_manager.redis.delete(key)
    for key in cache_manager.redis.scan_iter("schema:*"):
        cache_manager.redis.delete(key)
    for key in cache_manager.redis.scan_iter("embedding:*"):
        cache_manager.redis.delete(key)
    yield


class TestRedisCacheBasics:
    """Test basic Redis cache operations."""

    def test_redis_connection(self, cache_manager):
        """Test that Redis connection is working."""
        assert cache_manager.redis.ping() is True

    def test_set_and_get_string(self, cache_manager):
        """Test basic string set and get."""
        cache_manager.redis.setex("test:string", 60, "hello world")
        result = cache_manager.redis.get("test:string")

        assert result == b"hello world"

    def test_set_and_get_json(self, cache_manager):
        """Test JSON data storage."""
        data = {"sql": "SELECT * FROM users", "tables": ["users"]}
        cache_manager.redis.setex("test:json", 60, json.dumps(data))

        result = cache_manager.redis.get("test:json")
        parsed = json.loads(result)

        assert parsed["sql"] == "SELECT * FROM users"
        assert parsed["tables"] == ["users"]

    def test_ttl_expiration(self, cache_manager):
        """Test that TTL expiration works."""
        cache_manager.redis.setex("test:ttl", 1, "short lived")

        # Should exist immediately
        assert cache_manager.redis.get("test:ttl") is not None

        # Wait for expiration
        time.sleep(1.5)

        # Should be gone
        assert cache_manager.redis.get("test:ttl") is None

    def test_delete_key(self, cache_manager):
        """Test key deletion."""
        cache_manager.redis.setex("test:delete", 60, "to be deleted")
        assert cache_manager.redis.get("test:delete") is not None

        cache_manager.redis.delete("test:delete")
        assert cache_manager.redis.get("test:delete") is None


class TestCacheManagerSQLCaching:
    """Test SQL caching functionality using actual CacheManager methods."""

    def test_cache_sql_generation(self, cache_manager):
        """Test caching a SQL generation result."""
        # Generate a cache key
        query = "show me all customers"
        normalized = cache_manager._normalize_query(query)
        context_hash = cache_manager._hash_dict({"tables": ["customers"]})
        cache_key = cache_manager._generate_key(
            cache_manager.PREFIX_SQL,
            f"{hashlib.sha256(normalized.encode()).hexdigest()}:{context_hash}"
        )

        result = {
            "sql": "SELECT * FROM customers",
            "explanation": "Retrieves all customer records",
            "tables_used": ["customers"]
        }

        # Cache the result
        cache_manager.cache_sql_generation(cache_key, result, normalized)

        # Retrieve from cache
        cached = cache_manager.get_sql_generation(cache_key)

        assert cached is not None
        assert cached["sql"] == "SELECT * FROM customers"

    def test_cache_miss_returns_none(self, cache_manager):
        """Test that cache miss returns None."""
        cache_key = "sql:nonexistent_key_123"
        cached = cache_manager.get_sql_generation(cache_key)

        assert cached is None

    def test_get_or_generate_sql_cache_hit(self, cache_manager):
        """Test get_or_generate_sql returns cached result."""
        query = "show me all orders"
        table_context = [{"table_name": "orders"}]

        # First call should be a miss
        result_1, from_cache_1 = cache_manager.get_or_generate_sql(
            query=query,
            table_context=table_context,
            generator_func=lambda q, t: {"sql": "SELECT * FROM orders", "error": None}
        )

        assert from_cache_1 is False
        assert result_1["sql"] == "SELECT * FROM orders"

        # Second call should be a hit
        result_2, from_cache_2 = cache_manager.get_or_generate_sql(
            query=query,
            table_context=table_context,
            generator_func=lambda q, t: {"sql": "SHOULD NOT BE CALLED", "error": None}
        )

        assert from_cache_2 is True
        assert result_2["sql"] == "SELECT * FROM orders"

    def test_different_connectors_different_cache(self, cache_manager):
        """Test that different connector IDs get different cache entries."""
        query = "show me all orders"
        table_context = [{"table_name": "orders"}]

        # Cache for connector 1
        result_1, _ = cache_manager.get_or_generate_sql(
            query=query,
            table_context=table_context,
            generator_func=lambda q, t: {"sql": "SELECT * FROM orders_1", "error": None},
            connector_ids=["conn_1"]
        )

        # Cache for connector 2
        result_2, _ = cache_manager.get_or_generate_sql(
            query=query,
            table_context=table_context,
            generator_func=lambda q, t: {"sql": "SELECT * FROM orders_2", "error": None},
            connector_ids=["conn_2"]
        )

        assert result_1["sql"] == "SELECT * FROM orders_1"
        assert result_2["sql"] == "SELECT * FROM orders_2"

    def test_cache_key_consistency(self, cache_manager):
        """Test that same inputs produce same cache key."""
        query = "Show revenue"
        connector_ids = ["conn_a", "conn_b"]

        # Generate key with connectors in one order
        context_1 = {"tables": ["sales"], "connector_ids": sorted(["conn_a", "conn_b"])}
        context_2 = {"tables": ["sales"], "connector_ids": sorted(["conn_b", "conn_a"])}

        hash_1 = cache_manager._hash_dict(context_1)
        hash_2 = cache_manager._hash_dict(context_2)

        # Hashes should be identical after sorting
        assert hash_1 == hash_2


class TestCacheManagerEmbeddingCaching:
    """Test embedding caching functionality."""

    def test_cache_embedding(self, cache_manager):
        """Test caching an embedding vector."""
        text = "customer sales revenue"
        embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions

        cache_manager.cache_embedding(text, embedding)

        cached = cache_manager.get_embedding(text)

        assert cached is not None
        assert len(cached) == 1536
        assert cached[0] == 0.1

    def test_embedding_cache_miss(self, cache_manager):
        """Test embedding cache miss."""
        cached = cache_manager.get_embedding("non-existent text that was never cached")

        assert cached is None


class TestCacheManagerSchemaCaching:
    """Test schema caching functionality."""

    def test_cache_schema(self, cache_manager):
        """Test caching table schema."""
        schema = {
            "table_name": "customers",
            "columns": [
                {"name": "id", "type": "INT"},
                {"name": "name", "type": "STRING"}
            ]
        }

        cache_manager.cache_schema(
            project="test-project",
            dataset="test-dataset",
            table="customers",
            schema=schema
        )

        cached = cache_manager.get_schema(
            project="test-project",
            dataset="test-dataset",
            table="customers"
        )

        assert cached is not None
        assert cached["table_name"] == "customers"
        assert len(cached["columns"]) == 2


class TestCacheManagerValidatedSQL:
    """Test validated SQL caching with quality gates."""

    def test_cache_validated_sql_gold_tier(self, cache_manager):
        """Test caching validated SQL with gold tier."""
        # Generate cache key
        query = "show customers"
        normalized = cache_manager._normalize_query(query)
        context_hash = cache_manager._hash_dict({"tables": ["customers"]})
        cache_key = cache_manager._generate_key(
            cache_manager.PREFIX_SQL,
            f"{hashlib.sha256(normalized.encode()).hexdigest()}:{context_hash}"
        )

        result = {
            "sql": "SELECT * FROM customers",
            "tables_used": ["customers"]
        }

        success = cache_manager.cache_validated_sql(
            key=cache_key,
            result=result,
            query=normalized,
            execution_time_ms=100.0,
            row_count=100,
            validation_status=True,
            error_details=None,
            confidence_score=0.95
        )

        assert success is True

        # Verify it was cached
        cached = cache_manager.get_sql_generation(cache_key)
        assert cached is not None
        assert cached["cache_tier"] == "GOLD"

    def test_cache_validated_sql_rejects_failed_validation(self, cache_manager):
        """Test that failed validation prevents caching."""
        # Generate cache key
        query = "show invalid table"
        normalized = cache_manager._normalize_query(query)
        context_hash = cache_manager._hash_dict({"tables": ["invalid"]})
        cache_key = cache_manager._generate_key(
            cache_manager.PREFIX_SQL,
            f"{hashlib.sha256(normalized.encode()).hexdigest()}:{context_hash}"
        )

        result = {
            "sql": "SELECT * FROM customers"
        }

        success = cache_manager.cache_validated_sql(
            key=cache_key,
            result=result,
            query=normalized,
            execution_time_ms=10.0,
            row_count=0,
            validation_status=False,  # Validation failed
            error_details="Table not found",
            confidence_score=0.3
        )

        assert success is False


class TestCacheManagerStats:
    """Test cache statistics and health."""

    def test_get_cache_stats(self, cache_manager):
        """Test retrieving cache statistics."""
        # Add some data first
        cache_manager.redis.setex("test:stats", 60, "test value")

        stats = cache_manager.get_stats()

        assert stats is not None
        assert "redis_info" in stats
        assert "used_memory_human" in stats["redis_info"]

    def test_health_check(self, cache_manager):
        """Test cache health check."""
        health = cache_manager.health_check()

        assert health["status"] == "healthy"
        assert "latency_ms" in health
        assert "stats" in health


class TestCacheManagerClearOperations:
    """Test cache clearing operations."""

    def test_clear_all_caches(self, cache_manager):
        """Test clearing all caches."""
        # Add various cache entries
        cache_manager.redis.setex("sql:test_clear", 60, "sql data")
        cache_manager.redis.setex("schema:test_clear", 60, "schema data")
        cache_manager.redis.setex("embedding:test_clear", 60, "embedding data")

        # Clear all
        cleared = cache_manager.clear_all_caches()

        assert cleared >= 3  # At least the entries we added

    def test_invalidate_schema_cache(self, cache_manager):
        """Test schema cache invalidation."""
        # Add schema entries
        cache_manager.cache_schema("project", "dataset", "table1", {"name": "table1"})
        cache_manager.cache_schema("project", "dataset", "table2", {"name": "table2"})

        # Verify they exist
        assert cache_manager.get_schema("project", "dataset", "table1") is not None
        assert cache_manager.get_schema("project", "dataset", "table2") is not None

        # Invalidate all schemas for the dataset
        deleted = cache_manager.invalidate_schema_cache("project", "dataset")

        assert deleted >= 2


class TestCacheManagerQueryTracking:
    """Test query frequency tracking."""

    def test_track_query_frequency(self, cache_manager):
        """Test that query frequency is tracked."""
        query = "test query for frequency tracking"

        # Initial frequency should be 0
        initial_freq = cache_manager.get_query_frequency(query)
        assert initial_freq == 0

        # Track the query multiple times
        cache_manager._track_query_frequency(query)
        cache_manager._track_query_frequency(query)
        cache_manager._track_query_frequency(query)

        # Frequency should now be 3
        new_freq = cache_manager.get_query_frequency(query)
        assert new_freq == 3


class TestCacheManagerValidation:
    """Test validation caching."""

    def test_cache_validation(self, cache_manager):
        """Test caching validation results."""
        sql = "SELECT * FROM customers"
        validation_result = {
            "valid": True,
            "dry_run_bytes": 1000000,
            "estimated_cost": 0.005
        }

        cache_manager.cache_validation(sql, validation_result)
        cached = cache_manager.get_validation(sql)

        assert cached is not None
        assert cached["valid"] is True
        assert cached["dry_run_bytes"] == 1000000

    def test_validation_cache_miss(self, cache_manager):
        """Test validation cache miss."""
        cached = cache_manager.get_validation("SELECT * FROM nonexistent_table_xyz")
        assert cached is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
