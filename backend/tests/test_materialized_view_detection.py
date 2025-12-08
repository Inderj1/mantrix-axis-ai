"""
Tests for materialized view detection and async execution for very large tables.

Run with: cd backend && source venv/bin/activate && python -m pytest tests/test_materialized_view_detection.py -v
"""
import pytest
import sys
sys.path.insert(0, '/Users/jay/Workspace/Cloudmantra_code/mantrix-axis-ai/backend')

from src.core.single_db_query_optimizer import (
    SingleDatabaseQueryOptimizer,
    QueryAnalysis,
    ExecutionStrategy,
    VERY_LARGE_TABLE_THRESHOLD,
    PANDAS_MAX_ROWS,
    FEDERATION_THRESHOLD
)


class TestThresholdConstants:
    """Test threshold constant values."""

    def test_very_large_table_threshold(self):
        """Verify 1B row threshold for async execution."""
        assert VERY_LARGE_TABLE_THRESHOLD == 1_000_000_000

    def test_pandas_max_rows(self):
        """Verify 1M row threshold for direct execution."""
        assert PANDAS_MAX_ROWS == 1_000_000

    def test_federation_threshold(self):
        """Verify 100M row threshold for federation."""
        assert FEDERATION_THRESHOLD == 100_000_000


class TestQueryAnalysisDataclass:
    """Test the QueryAnalysis dataclass fields."""

    def test_requires_async_field_exists(self):
        """Verify requires_async field is in dataclass."""
        analysis = QueryAnalysis()
        assert hasattr(analysis, 'requires_async')
        assert analysis.requires_async is False  # Default

    def test_aggregation_columns_field_exists(self):
        """Verify aggregation_columns field is in dataclass."""
        analysis = QueryAnalysis()
        assert hasattr(analysis, 'aggregation_columns')
        assert analysis.aggregation_columns == []  # Default empty list

    def test_group_by_columns_field_exists(self):
        """Verify group_by_columns field is in dataclass."""
        analysis = QueryAnalysis()
        assert hasattr(analysis, 'group_by_columns')
        assert analysis.group_by_columns == []  # Default empty list

    def test_to_dict_includes_new_fields(self):
        """Verify to_dict() includes the new fields."""
        analysis = QueryAnalysis(
            requires_async=True,
            aggregation_columns=["SUM_SALES", "COUNT_ORDERS"],
            group_by_columns=["STORE_ID"]
        )
        d = analysis.to_dict()

        assert "requires_async" in d
        assert d["requires_async"] is True
        assert "aggregation_columns" in d
        assert d["aggregation_columns"] == ["SUM_SALES", "COUNT_ORDERS"]
        assert "group_by_columns" in d
        assert d["group_by_columns"] == ["STORE_ID"]


class TestAggregationColumnExtraction:
    """Test extraction of aggregation columns from SQL."""

    def setup_method(self):
        """Set up optimizer without external dependencies."""
        self.optimizer = SingleDatabaseQueryOptimizer()

    def test_extract_sum_column(self):
        """Test extraction of SUM column."""
        sql = "SELECT SUM(amount) FROM orders"
        import sqlglot
        parsed = sqlglot.parse_one(sql)
        cols = self.optimizer._extract_aggregation_columns(parsed)
        assert "AMOUNT" in cols

    def test_extract_count_star(self):
        """Test extraction of COUNT(*)."""
        sql = "SELECT COUNT(*) FROM orders"
        import sqlglot
        parsed = sqlglot.parse_one(sql)
        cols = self.optimizer._extract_aggregation_columns(parsed)
        assert "*" in cols

    def test_extract_multiple_aggregations(self):
        """Test extraction of multiple aggregate functions."""
        sql = """
        SELECT
            SUM(sales) as total_sales,
            COUNT(*) as order_count,
            AVG(quantity) as avg_qty,
            MAX(price) as max_price
        FROM orders
        """
        import sqlglot
        parsed = sqlglot.parse_one(sql)
        cols = self.optimizer._extract_aggregation_columns(parsed)

        assert "SALES" in cols
        assert "*" in cols
        assert "QUANTITY" in cols
        assert "PRICE" in cols

    def test_extract_group_by_columns(self):
        """Test extraction of GROUP BY columns."""
        sql = """
        SELECT store_id, region, SUM(sales)
        FROM orders
        GROUP BY store_id, region
        """
        import sqlglot
        parsed = sqlglot.parse_one(sql)
        cols = self.optimizer._extract_group_by_columns(parsed)

        assert "STORE_ID" in cols
        assert "REGION" in cols


class TestStrategySelection:
    """Test strategy selection based on table size."""

    def test_very_large_table_gets_optimized_strategy(self):
        """Test that very large tables get OPTIMIZED strategy."""
        analysis = QueryAnalysis(
            largest_table_rows=28_800_000_000,  # 28.8B rows
            has_aggregation=True,
            estimated_result_rows=1000
        )

        optimizer = SingleDatabaseQueryOptimizer()
        strategy = optimizer._select_strategy(analysis)

        assert strategy == ExecutionStrategy.OPTIMIZED
        assert analysis.requires_async is True

    def test_small_aggregation_gets_direct_strategy(self):
        """Test that small table aggregations get DIRECT strategy."""
        analysis = QueryAnalysis(
            largest_table_rows=500_000,  # 500K rows
            has_aggregation=True,
            estimated_result_rows=100
        )

        optimizer = SingleDatabaseQueryOptimizer()
        strategy = optimizer._select_strategy(analysis)

        assert strategy == ExecutionStrategy.DIRECT
        assert analysis.requires_async is False

    def test_medium_table_without_aggregation(self):
        """Test medium table without aggregation gets OPTIMIZED."""
        analysis = QueryAnalysis(
            largest_table_rows=50_000_000,  # 50M rows
            has_aggregation=False,
            estimated_result_rows=50_000_000
        )

        optimizer = SingleDatabaseQueryOptimizer()
        strategy = optimizer._select_strategy(analysis)

        assert strategy == ExecutionStrategy.OPTIMIZED
        assert analysis.requires_async is False  # Under 1B threshold


class TestMaterializedViewRDFBuilder:
    """Test RDF builder MV registration methods exist."""

    def test_add_materialized_view_method_exists(self):
        """Verify add_materialized_view method exists."""
        from src.pipeline.rdf_builder import RDFBuilder
        builder = RDFBuilder()
        assert hasattr(builder, 'add_materialized_view')
        assert callable(builder.add_materialized_view)

    def test_get_materialized_views_method_exists(self):
        """Verify get_materialized_views_for_table method exists."""
        from src.pipeline.rdf_builder import RDFBuilder
        builder = RDFBuilder()
        assert hasattr(builder, 'get_materialized_views_for_table')
        assert callable(builder.get_materialized_views_for_table)


class TestJenaQueryResolverMVMethod:
    """Test Jena query resolver MV lookup method exists."""

    def test_find_materialized_view_method_exists(self):
        """Verify find_materialized_view method exists."""
        from src.core.knowledge_graph.jena_query_resolver import JenaQueryResolver
        resolver = JenaQueryResolver()
        assert hasattr(resolver, 'find_materialized_view')
        assert callable(resolver.find_materialized_view)

    def test_find_mv_returns_none_when_no_match(self):
        """Verify find_materialized_view returns None when no MV exists."""
        from src.core.knowledge_graph.jena_query_resolver import JenaQueryResolver
        resolver = JenaQueryResolver()

        # Query for non-existent MV
        result = resolver.find_materialized_view(
            base_table="NONEXISTENT_TABLE",
            aggregation_columns=["COL1"],
            group_by_columns=["COL2"]
        )

        # Should return None, not raise exception
        assert result is None


class TestAsyncWarningGeneration:
    """Test that async warnings are generated correctly."""

    def test_async_warning_added_for_large_table(self):
        """Test that warning is added when async is required."""
        analysis = QueryAnalysis(
            largest_table_rows=5_000_000_000,  # 5B rows
            has_aggregation=True,
            estimated_result_rows=100
        )

        optimizer = SingleDatabaseQueryOptimizer()
        optimizer._select_strategy(analysis)

        # Should have warning about background/async
        assert len(analysis.warnings) > 0
        warning_text = " ".join(analysis.warnings).lower()
        assert "background" in warning_text or "poll" in warning_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
