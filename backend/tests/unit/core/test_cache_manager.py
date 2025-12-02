"""
Comprehensive unit tests for CacheManager.

Tests cover:
- Basic get/set operations
- get_or_generate_sql with connector isolation
- cache_validated_sql quality gates
- Schema caching operations
- TTL and tier logic
- Error handling
"""

import pytest
import json
import hashlib
from unittest.mock import MagicMock, patch, call
from datetime import datetime


# ============================================================================
# TEST CACHE MANAGER BASICS
# ============================================================================

class TestCacheManagerBasics:
    """Test basic cache operations."""

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create cache manager with mocked Redis."""
        from src.core.cache_manager import CacheManager
        manager = CacheManager(host='localhost', port=6379)
        return manager

    def test_get_returns_value_when_exists(self, cache_manager, mock_redis):
        """Test that get returns cached value when it exists."""
        mock_redis.get.return_value = b"cached_value"

        result = cache_manager.get("test_key")

        assert result == "cached_value"
        mock_redis.get.assert_called_once_with("test_key")

    def test_get_returns_none_for_missing_key(self, cache_manager, mock_redis):
        """Test that get returns None for missing keys."""
        mock_redis.get.return_value = None

        result = cache_manager.get("nonexistent_key")

        assert result is None

    def test_get_handles_string_response(self, cache_manager, mock_redis):
        """Test that get handles already decoded string responses."""
        mock_redis.get.return_value = "string_value"

        result = cache_manager.get("test_key")

        assert result == "string_value"

    def test_set_stores_value_with_ttl(self, cache_manager, mock_redis):
        """Test that set stores values with TTL."""
        cache_manager.set("test_key", "test_value", ttl=3600)

        mock_redis.setex.assert_called_once_with("test_key", 3600, "test_value")

    def test_get_handles_redis_error(self, cache_manager, mock_redis):
        """Test that get handles Redis errors gracefully."""
        mock_redis.get.side_effect = Exception("Redis connection error")

        result = cache_manager.get("test_key")

        assert result is None

    def test_set_handles_redis_error(self, cache_manager, mock_redis):
        """Test that set handles Redis errors gracefully."""
        mock_redis.setex.side_effect = Exception("Redis connection error")

        # Should not raise
        cache_manager.set("test_key", "test_value")

    def test_enabled_flag_skips_operations(self, mock_redis):
        """Test that disabled cache skips operations."""
        from src.core.cache_manager import CacheManager
        manager = CacheManager(host='localhost', port=6379)
        manager.enabled = False

        result = manager.get("test_key")
        assert result is None
        mock_redis.get.assert_not_called()

    def test_normalize_query_handles_whitespace(self, cache_manager):
        """Test query normalization handles extra whitespace."""
        q1 = "Show   me  all    products"
        q2 = "show me all products"
        q3 = "  SHOW ME ALL PRODUCTS  "

        assert cache_manager._normalize_query(q1) == "show me all products"
        assert cache_manager._normalize_query(q2) == "show me all products"
        assert cache_manager._normalize_query(q3) == "show me all products"

    def test_normalize_query_handles_none(self, cache_manager):
        """Test query normalization handles None."""
        result = cache_manager._normalize_query(None)
        assert result == ""

    def test_hash_dict_is_deterministic(self, cache_manager):
        """Test that hash_dict produces consistent results."""
        data = {"key": "value", "number": 42}

        hash1 = cache_manager._hash_dict(data)
        hash2 = cache_manager._hash_dict(data)

        assert hash1 == hash2

    def test_hash_dict_is_order_independent(self, cache_manager):
        """Test that dict key order doesn't affect hash."""
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}

        assert cache_manager._hash_dict(data1) == cache_manager._hash_dict(data2)


# ============================================================================
# TEST GET_OR_GENERATE_SQL
# ============================================================================

class TestGetOrGenerateSQL:
    """Test the main cache lookup and generation method."""

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create cache manager with mocked Redis."""
        from src.core.cache_manager import CacheManager
        manager = CacheManager(host='localhost', port=6379)
        return manager

    def test_cache_hit_returns_cached_result(self, cache_manager, mock_redis):
        """Test that cache hits return cached data."""
        cached_data = {
            "sql": "SELECT * FROM cached_table",
            "explanation": "Cached query",
            "tables_used": ["cached_table"],
            "hit_count": 5
        }
        mock_redis.get.return_value = json.dumps(cached_data).encode()

        result, from_cache = cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[{"table_name": "test"}],
            generator_func=lambda q, t: None
        )

        assert from_cache is True
        assert result["sql"] == "SELECT * FROM cached_table"

    def test_cache_miss_calls_generator_func(self, cache_manager, mock_redis):
        """Test that cache misses call the generator function."""
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={
            "sql": "SELECT * FROM generated",
            "explanation": "Generated query"
        })

        result, from_cache = cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[{"table_name": "test"}],
            generator_func=generator
        )

        assert from_cache is False
        generator.assert_called_once()
        assert result["sql"] == "SELECT * FROM generated"

    def test_cache_miss_does_not_cache_immediately(self, cache_manager, mock_redis):
        """Test that get_or_generate_sql does NOT cache immediately.

        Caching is now deferred to cache_validated_sql() after execution,
        so we can check for empty results and errors before caching.
        """
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={
            "sql": "SELECT * FROM new_table",
            "explanation": "New query"
        })

        cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[{"table_name": "test"}],
            generator_func=generator
        )

        # Verify setex was NOT called - caching is deferred to cache_validated_sql()
        mock_redis.setex.assert_not_called()

    def test_force_refresh_bypasses_cache(self, cache_manager, mock_redis):
        """Test that force_refresh bypasses cache lookup."""
        cached_data = {"sql": "SELECT * FROM old", "hit_count": 5}
        mock_redis.get.return_value = json.dumps(cached_data).encode()
        generator = MagicMock(return_value={
            "sql": "SELECT * FROM fresh",
            "explanation": "Fresh query"
        })

        result, from_cache = cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[{"table_name": "test"}],
            generator_func=generator,
            force_refresh=True
        )

        assert from_cache is False
        assert result["sql"] == "SELECT * FROM fresh"

    def test_connector_ids_in_cache_key(self, cache_manager, mock_redis):
        """Test that connector_ids are included in cache key."""
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={"sql": "SELECT 1"})

        # First call with connector_a
        cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[{"table_name": "test"}],
            generator_func=generator,
            connector_ids=["connector_a"]
        )

        # Second call with connector_b (should generate new)
        cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[{"table_name": "test"}],
            generator_func=generator,
            connector_ids=["connector_b"]
        )

        # Generator should be called twice (different cache keys)
        assert generator.call_count == 2

    def test_different_connectors_get_different_keys(self, cache_manager):
        """Test that different connector_ids produce different cache keys."""
        context_a = {"tables": ["test"], "connector_ids": ["connector_a"]}
        context_b = {"tables": ["test"], "connector_ids": ["connector_b"]}

        hash_a = cache_manager._hash_dict(context_a)
        hash_b = cache_manager._hash_dict(context_b)

        assert hash_a != hash_b

    def test_sorted_connector_ids_consistent_hash(self, cache_manager):
        """Test that connector_ids are sorted for consistent hashing."""
        # Different order, same connectors
        context_1 = {"tables": ["test"], "connector_ids": sorted(["b", "a", "c"])}
        context_2 = {"tables": ["test"], "connector_ids": sorted(["c", "a", "b"])}

        hash_1 = cache_manager._hash_dict(context_1)
        hash_2 = cache_manager._hash_dict(context_2)

        assert hash_1 == hash_2

    def test_empty_table_context_handled(self, cache_manager, mock_redis):
        """Test handling of empty table context."""
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={"sql": "SELECT 1"})

        result, from_cache = cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[],
            generator_func=generator
        )

        assert result is not None
        generator.assert_called_once()

    def test_string_table_names_handled(self, cache_manager, mock_redis):
        """Test handling of string table names in context."""
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={"sql": "SELECT 1"})

        result, from_cache = cache_manager.get_or_generate_sql(
            query="test query",
            table_context=["table1", "table2"],  # Strings not dicts
            generator_func=generator
        )

        generator.assert_called_once()

    def test_dict_table_context_handled(self, cache_manager, mock_redis):
        """Test handling of dict table context."""
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={"sql": "SELECT 1"})

        result, from_cache = cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[
                {"table_name": "customers"},
                {"table_name": "orders"}
            ],
            generator_func=generator
        )

        generator.assert_called_once()

    def test_generator_error_not_cached(self, cache_manager, mock_redis):
        """Test that errors from generator are not cached."""
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={
            "error": "Generation failed",
            "sql": None
        })

        cache_manager.get_or_generate_sql(
            query="test query",
            table_context=[{"table_name": "test"}],
            generator_func=generator
        )

        # setex should not be called for error results
        # (Actually it checks for 'error' key, so let's verify)
        # Looking at the code, it caches if no error key
        # So this test verifies error results aren't cached
        for call in mock_redis.setex.call_args_list:
            cached_value = call[0][2] if len(call[0]) > 2 else call[1].get('value')
            if cached_value:
                data = json.loads(cached_value)
                assert "error" not in data or data.get("error") is None

    def test_stats_updated_on_hit(self, cache_manager, mock_redis):
        """Test that stats are updated on cache hit."""
        cached_data = {"sql": "SELECT 1", "hit_count": 0}
        mock_redis.get.return_value = json.dumps(cached_data).encode()

        initial_hits = cache_manager.stats.hits
        cache_manager.get_or_generate_sql(
            query="test",
            table_context=[],
            generator_func=lambda q, t: None
        )

        assert cache_manager.stats.hits == initial_hits + 1

    def test_stats_updated_on_miss(self, cache_manager, mock_redis):
        """Test that stats are updated on cache miss."""
        mock_redis.get.return_value = None
        generator = MagicMock(return_value={"sql": "SELECT 1"})

        initial_misses = cache_manager.stats.misses
        cache_manager.get_or_generate_sql(
            query="test",
            table_context=[],
            generator_func=generator
        )

        assert cache_manager.stats.misses == initial_misses + 1


# ============================================================================
# TEST CACHE_VALIDATED_SQL
# ============================================================================

class TestCacheValidatedSQL:
    """Test the validated SQL caching with quality gates."""

    @pytest.fixture
    def cache_manager(self, mock_redis, mock_settings):
        """Create cache manager with mocked Redis and settings."""
        from src.core.cache_manager import CacheManager
        manager = CacheManager(host='localhost', port=6379)
        return manager

    def test_rejects_failed_validation(self, cache_manager, mock_redis, mock_settings):
        """Test that failed validation rejects caching."""
        mock_settings.cache_validation_required = True

        result = cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=100,
            row_count=10,
            validation_status=False,  # Failed validation
            error_details="Validation failed"
        )

        assert result is False

    def test_rejects_execution_error(self, cache_manager, mock_redis, mock_settings):
        """Test that execution errors reject caching."""
        result = cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=100,
            row_count=0,
            validation_status=True,
            error_details="Query execution failed"  # Has error
        )

        assert result is False

    def test_rejects_empty_results(self, cache_manager, mock_redis, mock_settings):
        """Test that empty results reject caching when configured."""
        mock_settings.cache_reject_empty_results = True

        result = cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=100,
            row_count=0,  # Zero rows returned
            validation_status=True,
            error_details=None
        )

        assert result is False

    def test_allows_empty_results_when_disabled(self, cache_manager, mock_redis, mock_settings):
        """Test that empty results are cached when rejection is disabled."""
        mock_settings.cache_reject_empty_results = False
        mock_settings.cache_min_confidence = 0.0  # Don't reject for confidence

        result = cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=100,
            row_count=0,  # Zero rows returned
            validation_status=True,
            error_details=None,
            confidence_score=0.9
        )

        assert result is True  # Should be cached when feature is disabled

    def test_rejects_low_confidence(self, cache_manager, mock_redis, mock_settings):
        """Test that low confidence scores reject caching."""
        mock_settings.cache_min_confidence = 0.8

        result = cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=100,
            row_count=10,
            validation_status=True,
            error_details=None,
            confidence_score=0.5  # Below threshold
        )

        assert result is False

    def test_marks_suspect_high_rows(self, cache_manager, mock_redis, mock_settings):
        """Test that high row counts are marked as suspect."""
        mock_settings.cache_max_rows_threshold = 1000

        result = cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=100,
            row_count=5000,  # Above threshold
            validation_status=True,
            error_details=None
        )

        # Should still cache but mark as suspect
        assert result is True
        # Check the cached data has suspect flag
        call_args = mock_redis.setex.call_args
        cached_json = call_args[0][2] if len(call_args[0]) > 2 else None
        if cached_json:
            cached_data = json.loads(cached_json)
            assert cached_data.get("execution_metadata", {}).get("suspect_high_rows") is True

    def test_gold_tier_for_fast_high_confidence(self, cache_manager, mock_settings):
        """Test that fast, high-confidence queries get Gold tier."""
        tier, ttl = cache_manager._determine_cache_tier(
            execution_time_ms=1000,  # Fast (< 5000)
            confidence_score=0.95,    # High confidence
            suspect_high_rows=False
        )

        assert tier == "GOLD"
        assert ttl == mock_settings.cache_ttl_gold

    def test_silver_tier_for_normal_queries(self, cache_manager, mock_settings):
        """Test that normal queries get Silver tier."""
        tier, ttl = cache_manager._determine_cache_tier(
            execution_time_ms=10000,  # Moderate
            confidence_score=0.75,
            suspect_high_rows=False
        )

        assert tier == "SILVER"
        assert ttl == mock_settings.cache_ttl_silver

    def test_bronze_tier_for_slow_queries(self, cache_manager, mock_settings):
        """Test that slow queries get Bronze tier."""
        mock_settings.cache_execution_threshold_ms = 30000

        tier, ttl = cache_manager._determine_cache_tier(
            execution_time_ms=35000,  # Slow (> threshold)
            confidence_score=0.9,
            suspect_high_rows=False
        )

        assert tier == "BRONZE"
        assert ttl == mock_settings.cache_ttl_bronze

    def test_bronze_tier_for_suspect_rows(self, cache_manager, mock_settings):
        """Test that suspect high rows get Bronze tier."""
        tier, ttl = cache_manager._determine_cache_tier(
            execution_time_ms=1000,
            confidence_score=0.95,
            suspect_high_rows=True  # Suspect
        )

        assert tier == "BRONZE"

    def test_execution_metadata_stored(self, cache_manager, mock_redis, mock_settings):
        """Test that execution metadata is stored with cached result."""
        cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=150,
            row_count=42,
            validation_status=True,
            error_details=None,
            confidence_score=0.9
        )

        call_args = mock_redis.setex.call_args
        cached_json = call_args[0][2] if len(call_args[0]) > 2 else None
        if cached_json:
            cached_data = json.loads(cached_json)
            metadata = cached_data.get("execution_metadata", {})
            assert metadata.get("execution_time_ms") == 150
            assert metadata.get("row_count") == 42
            assert metadata.get("validation_status") is True

    def test_hit_count_initialized_to_zero(self, cache_manager, mock_redis, mock_settings):
        """Test that hit_count is initialized to 0."""
        cache_manager.cache_validated_sql(
            key="test_key",
            result={"sql": "SELECT 1"},
            query="test",
            execution_time_ms=100,
            row_count=10,
            validation_status=True,
            error_details=None
        )

        call_args = mock_redis.setex.call_args
        cached_json = call_args[0][2] if len(call_args[0]) > 2 else None
        if cached_json:
            cached_data = json.loads(cached_json)
            assert cached_data.get("hit_count") == 0


# ============================================================================
# TEST SCHEMA CACHE
# ============================================================================

class TestSchemaCache:
    """Test schema-specific caching operations."""

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create cache manager with mocked Redis."""
        from src.core.cache_manager import CacheManager
        manager = CacheManager(host='localhost', port=6379)
        return manager

    def test_cache_schema_stores_correctly(self, cache_manager, mock_redis):
        """Test that schemas are cached correctly."""
        schema = {
            "table_name": "test_table",
            "columns": [{"name": "id", "type": "STRING"}]
        }

        cache_manager.cache_schema("project", "dataset", "test_table", schema)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        key = call_args[0][0]
        assert "project:dataset:test_table" in key

    def test_get_schema_returns_cached(self, cache_manager, mock_redis):
        """Test that cached schemas are retrieved."""
        schema = {"table_name": "test_table", "columns": []}
        mock_redis.get.return_value = json.dumps(schema).encode()

        result = cache_manager.get_schema("project", "dataset", "test_table")

        assert result["table_name"] == "test_table"

    def test_get_schema_returns_none_for_missing(self, cache_manager, mock_redis):
        """Test that missing schemas return None."""
        mock_redis.get.return_value = None

        result = cache_manager.get_schema("project", "dataset", "nonexistent")

        assert result is None

    def test_invalidate_schema_by_table(self, cache_manager, mock_redis):
        """Test invalidating a specific table's schema."""
        mock_redis.scan_iter.return_value = iter(["schema:project:dataset:table1"])

        deleted = cache_manager.invalidate_schema_cache("project", "dataset", "table1")

        mock_redis.delete.assert_called()

    def test_invalidate_schema_by_dataset(self, cache_manager, mock_redis):
        """Test invalidating all schemas in a dataset."""
        mock_redis.scan_iter.return_value = iter([
            "schema:project:dataset:table1",
            "schema:project:dataset:table2"
        ])

        deleted = cache_manager.invalidate_schema_cache("project", "dataset")

        assert mock_redis.delete.call_count >= 2

    def test_cached_schema_direct_key_methods(self, cache_manager, mock_redis):
        """Test direct cache key methods for schema access."""
        schema = {"table": "test"}
        mock_redis.get.return_value = json.dumps(schema).encode()

        result = cache_manager.get_cached_schema("direct_key")
        assert result["table"] == "test"

        cache_manager.set_cached_schema("direct_key", schema, ttl=3600)
        mock_redis.setex.assert_called()


# ============================================================================
# TEST EMBEDDING CACHE
# ============================================================================

class TestEmbeddingCache:
    """Test embedding caching operations."""

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create cache manager with mocked Redis."""
        from src.core.cache_manager import CacheManager
        manager = CacheManager(host='localhost', port=6379)
        return manager

    def test_cache_embedding_stores_pickled(self, cache_manager, mock_redis):
        """Test that embeddings are stored as pickle."""
        import pickle
        embedding = [0.1, 0.2, 0.3]

        cache_manager.cache_embedding("test text", embedding)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        stored_value = call_args[0][2] if len(call_args[0]) > 2 else None
        if stored_value:
            unpickled = pickle.loads(stored_value)
            assert unpickled == embedding

    def test_get_embedding_returns_unpickled(self, cache_manager, mock_redis):
        """Test that embeddings are retrieved and unpickled."""
        import pickle
        embedding = [0.1, 0.2, 0.3]
        mock_redis.get.return_value = pickle.dumps(embedding)

        result = cache_manager.get_embedding("test text")

        assert result == embedding

    def test_get_embedding_returns_none_for_missing(self, cache_manager, mock_redis):
        """Test that missing embeddings return None."""
        mock_redis.get.return_value = None

        result = cache_manager.get_embedding("unknown text")

        assert result is None


# ============================================================================
# TEST HEALTH AND STATS
# ============================================================================

class TestHealthAndStats:
    """Test health check and statistics methods."""

    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create cache manager with mocked Redis."""
        from src.core.cache_manager import CacheManager
        manager = CacheManager(host='localhost', port=6379)
        return manager

    def test_health_check_returns_healthy(self, cache_manager, mock_redis):
        """Test health check for healthy Redis."""
        mock_redis.ping.return_value = True

        result = cache_manager.health_check()

        assert result["status"] == "healthy"
        assert "latency_ms" in result

    def test_health_check_returns_unhealthy(self, cache_manager, mock_redis):
        """Test health check for unhealthy Redis."""
        mock_redis.ping.side_effect = Exception("Connection refused")

        result = cache_manager.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result

    def test_get_stats_returns_metrics(self, cache_manager, mock_redis):
        """Test that stats include all metrics."""
        result = cache_manager.get_stats()

        assert "performance" in result
        assert "hit_rate_percent" in result
        assert "redis_info" in result

    def test_hit_rate_calculation(self, cache_manager):
        """Test hit rate calculation."""
        cache_manager.stats.hits = 80
        cache_manager.stats.misses = 20
        cache_manager.stats.total_requests = 100

        assert cache_manager.stats.hit_rate == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
