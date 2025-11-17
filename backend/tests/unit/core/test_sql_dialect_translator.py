"""
Unit tests for SQL Dialect Translator.

Tests translation between all 5 database dialects:
- BigQuery
- Snowflake
- PostgreSQL
- Redshift
- Databricks
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.core.sql_dialect_translator import (
    SQLDialectTranslator,
    TranslationResult,
    TranslationError
)


class TestSQLDialectTranslator:
    """Test SQL dialect translation."""

    @pytest.fixture
    def translator(self):
        """Create translator instance."""
        return SQLDialectTranslator()

    # ==========================================
    # BigQuery → Snowflake Tests
    # ==========================================

    def test_bigquery_to_snowflake_date_functions(self, translator):
        """Test DATE_SUB → DATEADD translation."""
        sql = "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
        result = translator.translate(sql, 'bigquery', 'snowflake')

        assert 'DATEADD' in result.translated_sql
        assert 'DATE_SUB' not in result.translated_sql
        assert result.is_lossless is True
        assert result.confidence_score >= 0.90
        assert len(result.changes) > 0

    def test_bigquery_to_snowflake_backticks(self, translator):
        """Test backtick handling for Snowflake."""
        sql = "SELECT * FROM `project.dataset.table`"
        result = translator.translate(sql, 'bigquery', 'snowflake')

        # Backticks should be removed or converted
        assert result.translated_sql is not None
        assert result.is_lossless is True

    def test_bigquery_to_snowflake_string_agg(self, translator):
        """Test STRING_AGG function translation."""
        sql = "SELECT STRING_AGG(name, ', ') FROM products"
        result = translator.translate(sql, 'bigquery', 'snowflake')

        # Should translate to LISTAGG or similar
        assert result.translated_sql is not None
        assert result.confidence_score > 0

    # ==========================================
    # Snowflake → PostgreSQL Tests
    # ==========================================

    def test_snowflake_to_postgresql_dateadd(self, translator):
        """Test DATEADD → INTERVAL translation."""
        sql = "SELECT DATEADD(DAY, -7, CURRENT_DATE())"
        result = translator.translate(sql, 'snowflake', 'postgresql')

        assert 'INTERVAL' in result.translated_sql
        assert result.is_lossless is True
        assert len(result.changes) > 0

    def test_snowflake_to_postgresql_simple_select(self, translator):
        """Test simple SELECT translation."""
        sql = "SELECT * FROM users WHERE active = true"
        result = translator.translate(sql, 'snowflake', 'postgresql')

        assert 'SELECT' in result.translated_sql
        assert result.is_lossless is True
        assert result.confidence_score >= 0.95

    # ==========================================
    # PostgreSQL → BigQuery Tests
    # ==========================================

    def test_postgresql_to_bigquery_interval(self, translator):
        """Test INTERVAL → DATE_SUB/DATE_ADD translation."""
        sql = "SELECT CURRENT_DATE - INTERVAL '7 days'"
        result = translator.translate(sql, 'postgresql', 'bigquery')

        # Should have date arithmetic
        assert result.translated_sql is not None
        assert result.confidence_score > 0

    def test_postgresql_to_bigquery_now_function(self, translator):
        """Test NOW() function translation."""
        sql = "SELECT NOW() as current_time"
        result = translator.translate(sql, 'postgresql', 'bigquery')

        # Should translate to CURRENT_TIMESTAMP or similar
        assert result.translated_sql is not None
        assert result.confidence_score > 0

    # ==========================================
    # Redshift → PostgreSQL Tests
    # ==========================================

    def test_redshift_to_postgresql_compatibility(self, translator):
        """Test Redshift to PostgreSQL (should be very similar)."""
        sql = "SELECT * FROM users LIMIT 10"
        result = translator.translate(sql, 'redshift', 'postgresql')

        assert 'SELECT' in result.translated_sql
        assert result.is_lossless is True
        # Redshift and PostgreSQL are very similar
        assert result.confidence_score >= 0.90

    # ==========================================
    # Databricks → BigQuery Tests
    # ==========================================

    def test_databricks_to_bigquery_simple(self, translator):
        """Test Databricks to BigQuery translation."""
        sql = "SELECT * FROM users WHERE created_at > '2024-01-01'"
        result = translator.translate(sql, 'databricks', 'bigquery')

        assert 'SELECT' in result.translated_sql
        assert result.confidence_score > 0

    # ==========================================
    # Error Handling Tests
    # ==========================================

    def test_invalid_source_dialect(self, translator):
        """Test error handling for invalid source dialect."""
        with pytest.raises(ValueError) as exc_info:
            translator.translate("SELECT 1", 'invalid', 'bigquery')

        assert 'Invalid source dialect' in str(exc_info.value)

    def test_invalid_target_dialect(self, translator):
        """Test error handling for invalid target dialect."""
        with pytest.raises(ValueError) as exc_info:
            translator.translate("SELECT 1", 'bigquery', 'invalid')

        assert 'Invalid target dialect' in str(exc_info.value)

    def test_malformed_sql(self, translator):
        """Test error handling for malformed SQL."""
        with pytest.raises((ValueError, TranslationError)):
            translator.translate("SELECT FROM WHERE", 'bigquery', 'snowflake')

    def test_empty_sql(self, translator):
        """Test handling of empty SQL."""
        with pytest.raises((ValueError, TranslationError)):
            translator.translate("", 'bigquery', 'snowflake')

    # ==========================================
    # Translation Cost Tests
    # ==========================================

    def test_translation_cost_identical(self, translator):
        """Test cost for same dialect (should be 0)."""
        cost = translator.get_translation_cost(
            "SELECT * FROM users",
            'bigquery',
            'bigquery'
        )
        assert cost == 0.0

    def test_translation_cost_similar_dialects(self, translator):
        """Test cost for similar dialects (Redshift → PostgreSQL)."""
        cost = translator.get_translation_cost(
            "SELECT * FROM users",
            'redshift',
            'postgresql'
        )
        # Should be very low cost
        assert cost < 0.2

    def test_translation_cost_complex_query(self, translator):
        """Test cost for complex query with arrays."""
        sql = """
        SELECT DATE_TRUNC('month', date_column),
               ARRAY_AGG(DISTINCT value)
        FROM table
        """
        cost = translator.get_translation_cost(sql, 'snowflake', 'redshift')

        # Should be higher due to ARRAY_AGG
        assert cost > 0.15

    def test_translation_cost_window_functions(self, translator):
        """Test cost for query with window functions."""
        sql = """
        SELECT
            user_id,
            ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as rn
        FROM orders
        """
        cost = translator.get_translation_cost(sql, 'bigquery', 'redshift')

        # Window functions may have cost
        assert cost >= 0.0
        assert cost <= 1.0

    # ==========================================
    # Batch Translation Tests
    # ==========================================

    def test_batch_translate(self, translator):
        """Test batch translation of multiple queries."""
        queries = [
            "SELECT * FROM users",
            "SELECT COUNT(*) FROM products",
            "SELECT id, name FROM orders WHERE status = 'active'"
        ]
        results = translator.batch_translate(queries, 'bigquery', 'snowflake')

        assert len(results) == 3
        assert all(isinstance(r, TranslationResult) for r in results)
        assert all(r.confidence_score > 0 for r in results)

    def test_batch_translate_with_errors(self, translator):
        """Test batch translation with some invalid queries."""
        queries = [
            "SELECT * FROM users",
            "SELECT FROM WHERE",  # Invalid
            "SELECT COUNT(*) FROM products"
        ]
        results = translator.batch_translate(queries, 'bigquery', 'snowflake')

        assert len(results) == 3
        # First query should succeed
        assert results[0].confidence_score > 0
        # Second query should fail (confidence = 0)
        assert results[1].confidence_score == 0.0
        assert len(results[1].warnings) > 0
        # Third query should succeed
        assert results[2].confidence_score > 0

    # ==========================================
    # Cache Tests
    # ==========================================

    def test_translation_caching(self, translator):
        """Test that translations are cached."""
        sql = "SELECT * FROM users LIMIT 10"

        # First translation
        result1 = translator.translate(sql, 'bigquery', 'snowflake')

        # Second translation (should hit cache)
        result2 = translator.translate(sql, 'bigquery', 'snowflake')

        # Should return same result
        assert result1.translated_sql == result2.translated_sql
        assert result1.confidence_score == result2.confidence_score

    # ==========================================
    # Validation Tests
    # ==========================================

    def test_validation_enabled(self, translator):
        """Test translation with validation enabled."""
        sql = "SELECT * FROM users"
        result = translator.translate(
            sql,
            'bigquery',
            'snowflake',
            validate=True
        )

        assert result.translated_sql is not None
        assert result.confidence_score > 0

    def test_validation_disabled(self, translator):
        """Test translation with validation disabled."""
        sql = "SELECT * FROM users"
        result = translator.translate(
            sql,
            'bigquery',
            'snowflake',
            validate=False
        )

        assert result.translated_sql is not None
        assert result.confidence_score > 0

    # ==========================================
    # Complex Query Tests
    # ==========================================

    def test_complex_join_query(self, translator):
        """Test translation of complex JOIN query."""
        sql = """
        SELECT
            u.id,
            u.name,
            COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.active = true
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        """
        result = translator.translate(sql, 'bigquery', 'snowflake')

        assert 'JOIN' in result.translated_sql
        assert 'GROUP BY' in result.translated_sql
        assert 'HAVING' in result.translated_sql
        assert result.confidence_score > 0

    def test_cte_query(self, translator):
        """Test translation of CTE (Common Table Expression)."""
        sql = """
        WITH active_users AS (
            SELECT * FROM users WHERE active = true
        )
        SELECT * FROM active_users LIMIT 10
        """
        result = translator.translate(sql, 'postgresql', 'bigquery')

        assert 'WITH' in result.translated_sql
        assert result.confidence_score > 0

    def test_subquery(self, translator):
        """Test translation of subquery."""
        sql = """
        SELECT * FROM users
        WHERE id IN (SELECT user_id FROM orders WHERE total > 100)
        """
        result = translator.translate(sql, 'snowflake', 'postgresql')

        assert 'SELECT' in result.translated_sql
        assert 'IN' in result.translated_sql
        assert result.confidence_score > 0

    # ==========================================
    # Edge Cases Tests
    # ==========================================

    def test_simple_select_one(self, translator):
        """Test simplest possible query."""
        sql = "SELECT 1"
        result = translator.translate(sql, 'bigquery', 'snowflake')

        assert 'SELECT' in result.translated_sql
        assert result.is_lossless is True
        assert result.confidence_score >= 0.95

    def test_select_with_alias(self, translator):
        """Test SELECT with column alias."""
        sql = "SELECT id AS user_id, name AS user_name FROM users"
        result = translator.translate(sql, 'postgresql', 'bigquery')

        assert 'AS' in result.translated_sql or 'user_id' in result.translated_sql
        assert result.confidence_score > 0

    def test_case_statement(self, translator):
        """Test CASE statement translation."""
        sql = """
        SELECT
            id,
            CASE
                WHEN status = 'active' THEN 1
                WHEN status = 'inactive' THEN 0
                ELSE NULL
            END as status_code
        FROM users
        """
        result = translator.translate(sql, 'bigquery', 'snowflake')

        assert 'CASE' in result.translated_sql
        assert result.confidence_score > 0

    # ==========================================
    # All Dialect Pairs Tests
    # ==========================================

    @pytest.mark.parametrize("source,target", [
        ('bigquery', 'snowflake'),
        ('bigquery', 'postgresql'),
        ('bigquery', 'redshift'),
        ('bigquery', 'databricks'),
        ('snowflake', 'bigquery'),
        ('snowflake', 'postgresql'),
        ('snowflake', 'redshift'),
        ('snowflake', 'databricks'),
        ('postgresql', 'bigquery'),
        ('postgresql', 'snowflake'),
        ('postgresql', 'redshift'),
        ('postgresql', 'databricks'),
        ('redshift', 'bigquery'),
        ('redshift', 'snowflake'),
        ('redshift', 'postgresql'),
        ('redshift', 'databricks'),
        ('databricks', 'bigquery'),
        ('databricks', 'snowflake'),
        ('databricks', 'postgresql'),
        ('databricks', 'redshift'),
    ])
    def test_all_dialect_pairs(self, translator, source, target):
        """Test translation between all possible dialect pairs."""
        sql = "SELECT * FROM users WHERE active = true LIMIT 10"
        result = translator.translate(sql, source, target)

        assert result.translated_sql is not None
        assert len(result.translated_sql) > 0
        assert result.confidence_score >= 0.0
        assert result.confidence_score <= 1.0


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
