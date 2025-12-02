"""
Unit tests for SQLGenerator singleton pattern and Redis-based invalidation.

Tests cover:
- Per-organization caching
- Thread-safe access
- Redis-based cross-worker invalidation
- Graceful fallback when Redis unavailable
"""

import pytest
import time
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================================
# TEST SINGLETON GET
# ============================================================================

class TestSQLGeneratorSingletonGet:
    """Test get_sql_generator function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton state before each test."""
        from src.core import sql_generator_singleton
        sql_generator_singleton._sql_generators.clear()
        sql_generator_singleton._invalidation_timestamps.clear()
        sql_generator_singleton._redis_client = None
        yield

    @pytest.fixture
    def mock_sql_generator(self):
        """Mock SQLGenerator class."""
        with patch('src.core.sql_generator.SQLGenerator') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock, mock_instance

    def test_creates_new_instance_for_new_org(self, mock_sql_generator):
        """Test that a new SQLGenerator is created for a new organization."""
        from src.core.sql_generator_singleton import get_sql_generator

        mock_class, mock_instance = mock_sql_generator

        result = get_sql_generator(organization_id="org1")

        mock_class.assert_called_once_with(organization_id="org1")
        assert result == mock_instance

    def test_returns_cached_instance_for_same_org(self, mock_sql_generator):
        """Test that cached instance is returned for same organization."""
        from src.core.sql_generator_singleton import get_sql_generator

        mock_class, mock_instance = mock_sql_generator

        result1 = get_sql_generator(organization_id="org1")
        result2 = get_sql_generator(organization_id="org1")

        # Should only create once
        mock_class.assert_called_once()
        assert result1 is result2

    def test_creates_separate_instances_for_different_orgs(self, mock_sql_generator):
        """Test that different orgs get different instances."""
        from src.core.sql_generator_singleton import get_sql_generator

        mock_class, _ = mock_sql_generator
        mock_class.side_effect = [MagicMock(), MagicMock()]

        result1 = get_sql_generator(organization_id="org1")
        result2 = get_sql_generator(organization_id="org2")

        assert mock_class.call_count == 2
        assert result1 is not result2

    def test_default_organization_id(self, mock_sql_generator):
        """Test that None organization_id defaults to 'default'."""
        from src.core.sql_generator_singleton import get_sql_generator

        mock_class, mock_instance = mock_sql_generator

        result = get_sql_generator(organization_id=None)

        mock_class.assert_called_once_with(organization_id="default")

    def test_empty_string_organization_id_defaults(self, mock_sql_generator):
        """Test that empty string organization_id defaults to 'default'."""
        from src.core.sql_generator_singleton import get_sql_generator

        mock_class, mock_instance = mock_sql_generator

        result = get_sql_generator(organization_id="")

        # Empty string is falsy, should default to "default"
        mock_class.assert_called_once_with(organization_id="default")


# ============================================================================
# TEST SINGLETON INVALIDATION
# ============================================================================

class TestSQLGeneratorSingletonInvalidation:
    """Test invalidate_sql_generator function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton state before each test."""
        from src.core import sql_generator_singleton
        sql_generator_singleton._sql_generators.clear()
        sql_generator_singleton._invalidation_timestamps.clear()
        sql_generator_singleton._redis_client = None
        yield

    @pytest.fixture
    def mock_sql_generator(self):
        """Mock SQLGenerator class."""
        with patch('src.core.sql_generator.SQLGenerator') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock, mock_instance

    def test_invalidate_removes_cached_instance(self, mock_sql_generator):
        """Test that invalidation removes the cached instance."""
        from src.core.sql_generator_singleton import get_sql_generator, invalidate_sql_generator, _sql_generators

        mock_class, _ = mock_sql_generator

        # Create an instance
        get_sql_generator(organization_id="org1")
        assert "org1" in _sql_generators

        # Invalidate it
        with patch('src.core.sql_generator_singleton._signal_invalidation'):
            result = invalidate_sql_generator(organization_id="org1")

        assert result is True
        assert "org1" not in _sql_generators

    def test_invalidate_returns_false_if_no_instance(self):
        """Test that invalidation returns False if no instance exists."""
        from src.core.sql_generator_singleton import invalidate_sql_generator

        with patch('src.core.sql_generator_singleton._signal_invalidation'):
            result = invalidate_sql_generator(organization_id="nonexistent")

        assert result is False

    def test_invalidate_signals_redis(self, mock_sql_generator):
        """Test that invalidation signals Redis for cross-worker sync."""
        from src.core.sql_generator_singleton import get_sql_generator, invalidate_sql_generator

        mock_class, _ = mock_sql_generator

        # Create an instance
        get_sql_generator(organization_id="org1")

        # Invalidate and check Redis signal
        with patch('src.core.sql_generator_singleton._signal_invalidation') as mock_signal:
            invalidate_sql_generator(organization_id="org1")
            mock_signal.assert_called_once_with("org1")

    def test_new_instance_created_after_invalidation(self, mock_sql_generator):
        """Test that a new instance is created after invalidation."""
        from src.core.sql_generator_singleton import get_sql_generator, invalidate_sql_generator

        mock_class, _ = mock_sql_generator
        instance1 = MagicMock()
        instance2 = MagicMock()
        mock_class.side_effect = [instance1, instance2]

        # Create first instance
        result1 = get_sql_generator(organization_id="org1")
        assert result1 is instance1

        # Invalidate
        with patch('src.core.sql_generator_singleton._signal_invalidation'):
            invalidate_sql_generator(organization_id="org1")

        # Get again - should create new instance
        result2 = get_sql_generator(organization_id="org1")
        assert result2 is instance2
        assert result1 is not result2


# ============================================================================
# TEST REDIS CROSS-WORKER INVALIDATION
# ============================================================================

class TestRedisCrossWorkerInvalidation:
    """Test Redis-based cross-worker invalidation."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton state before each test."""
        from src.core import sql_generator_singleton
        sql_generator_singleton._sql_generators.clear()
        sql_generator_singleton._invalidation_timestamps.clear()
        sql_generator_singleton._redis_client = None
        yield

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_client = MagicMock()
        with patch('src.core.sql_generator_singleton._get_redis_client', return_value=mock_client):
            yield mock_client

    def test_signal_invalidation_sets_redis_key(self, mock_redis):
        """Test that _signal_invalidation sets Redis key with timestamp."""
        from src.core.sql_generator_singleton import _signal_invalidation

        _signal_invalidation("org1")

        # Should call setex with key, TTL, and timestamp
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "connector:invalidation:org1"
        assert call_args[0][1] == 86400  # 24 hour TTL

    def test_should_invalidate_returns_true_for_newer_timestamp(self, mock_redis):
        """Test that _should_invalidate returns True for newer timestamp."""
        from src.core.sql_generator_singleton import _should_invalidate, _invalidation_timestamps

        # Set up: worker knows about timestamp 100
        _invalidation_timestamps["org1"] = 100.0

        # Redis has newer timestamp 200
        mock_redis.get.return_value = "200.0"

        result = _should_invalidate("org1")

        assert result is True

    def test_should_invalidate_returns_false_for_same_timestamp(self, mock_redis):
        """Test that _should_invalidate returns False for same timestamp."""
        from src.core.sql_generator_singleton import _should_invalidate, _invalidation_timestamps

        # Set up: worker knows about timestamp 100
        _invalidation_timestamps["org1"] = 100.0

        # Redis has same timestamp
        mock_redis.get.return_value = "100.0"

        result = _should_invalidate("org1")

        assert result is False

    def test_should_invalidate_returns_false_when_no_flag(self, mock_redis):
        """Test that _should_invalidate returns False when no Redis flag exists."""
        from src.core.sql_generator_singleton import _should_invalidate

        mock_redis.get.return_value = None

        result = _should_invalidate("org1")

        assert result is False

    def test_cross_worker_invalidation_on_get(self):
        """Test that get_sql_generator checks for cross-worker invalidation."""
        from src.core.sql_generator_singleton import get_sql_generator, _sql_generators, _invalidation_timestamps

        mock_instance = MagicMock()

        with patch('src.core.sql_generator.SQLGenerator', return_value=mock_instance):
            # Create initial instance
            get_sql_generator(organization_id="org1")
            _invalidation_timestamps["org1"] = 100.0

        # Simulate another worker signaling invalidation
        mock_redis = MagicMock()
        mock_redis.get.return_value = "200.0"  # Newer timestamp

        new_instance = MagicMock()
        with patch('src.core.sql_generator_singleton._get_redis_client', return_value=mock_redis):
            with patch('src.core.sql_generator.SQLGenerator', return_value=new_instance):
                result = get_sql_generator(organization_id="org1")

        # Should have created a new instance
        assert result is new_instance


# ============================================================================
# TEST GRACEFUL FALLBACK
# ============================================================================

class TestGracefulFallback:
    """Test graceful fallback when Redis is unavailable."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton state before each test."""
        from src.core import sql_generator_singleton
        sql_generator_singleton._sql_generators.clear()
        sql_generator_singleton._invalidation_timestamps.clear()
        sql_generator_singleton._redis_client = None
        yield

    def test_should_invalidate_returns_false_when_redis_unavailable(self):
        """Test that _should_invalidate returns False when Redis is unavailable."""
        from src.core.sql_generator_singleton import _should_invalidate

        with patch('src.core.sql_generator_singleton._get_redis_client', return_value=None):
            result = _should_invalidate("org1")

        assert result is False

    def test_signal_invalidation_handles_redis_error(self):
        """Test that _signal_invalidation handles Redis errors gracefully."""
        from src.core.sql_generator_singleton import _signal_invalidation

        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception("Redis connection error")

        with patch('src.core.sql_generator_singleton._get_redis_client', return_value=mock_redis):
            # Should not raise, just log warning
            _signal_invalidation("org1")

    def test_get_works_without_redis(self):
        """Test that get_sql_generator works even without Redis."""
        from src.core.sql_generator_singleton import get_sql_generator

        mock_instance = MagicMock()

        with patch('src.core.sql_generator_singleton._get_redis_client', return_value=None):
            with patch('src.core.sql_generator.SQLGenerator', return_value=mock_instance):
                result = get_sql_generator(organization_id="org1")

        assert result is mock_instance


# ============================================================================
# TEST INVALIDATE ALL
# ============================================================================

class TestInvalidateAll:
    """Test invalidate_all_sql_generators function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton state before each test."""
        from src.core import sql_generator_singleton
        sql_generator_singleton._sql_generators.clear()
        sql_generator_singleton._invalidation_timestamps.clear()
        sql_generator_singleton._redis_client = None
        yield

    def test_invalidate_all_clears_all_instances(self):
        """Test that invalidate_all clears all cached instances."""
        from src.core.sql_generator_singleton import get_sql_generator, invalidate_all_sql_generators, _sql_generators

        with patch('src.core.sql_generator.SQLGenerator') as mock:
            mock.side_effect = [MagicMock(), MagicMock(), MagicMock()]

            get_sql_generator(organization_id="org1")
            get_sql_generator(organization_id="org2")
            get_sql_generator(organization_id="org3")

            assert len(_sql_generators) == 3

        with patch('src.core.sql_generator_singleton._signal_invalidation'):
            count = invalidate_all_sql_generators()

        assert count == 3
        assert len(_sql_generators) == 0

    def test_invalidate_all_returns_zero_when_empty(self):
        """Test that invalidate_all returns 0 when no instances exist."""
        from src.core.sql_generator_singleton import invalidate_all_sql_generators

        with patch('src.core.sql_generator_singleton._signal_invalidation'):
            count = invalidate_all_sql_generators()

        assert count == 0


# ============================================================================
# TEST GET CACHED ORGANIZATION IDS
# ============================================================================

class TestGetCachedOrganizationIds:
    """Test get_cached_organization_ids function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton state before each test."""
        from src.core import sql_generator_singleton
        sql_generator_singleton._sql_generators.clear()
        sql_generator_singleton._invalidation_timestamps.clear()
        sql_generator_singleton._redis_client = None
        yield

    def test_returns_empty_list_initially(self):
        """Test that empty list is returned when no instances exist."""
        from src.core.sql_generator_singleton import get_cached_organization_ids

        result = get_cached_organization_ids()

        assert result == []

    def test_returns_all_cached_org_ids(self):
        """Test that all cached organization IDs are returned."""
        from src.core.sql_generator_singleton import get_sql_generator, get_cached_organization_ids

        with patch('src.core.sql_generator.SQLGenerator') as mock:
            mock.side_effect = [MagicMock(), MagicMock()]

            get_sql_generator(organization_id="org1")
            get_sql_generator(organization_id="org2")

        result = get_cached_organization_ids()

        assert set(result) == {"org1", "org2"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
