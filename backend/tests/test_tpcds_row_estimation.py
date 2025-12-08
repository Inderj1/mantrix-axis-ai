"""
Test TPC-DS row count estimation for Snowflake shared databases.

This tests the _estimate_tpcds_row_count method added to SnowflakeConnector
to handle SNOWFLAKE_SAMPLE_DATA shared databases where INFORMATION_SCHEMA
returns NULL for ROW_COUNT.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTPCDSRowEstimation:
    """Test TPC-DS row count estimation."""

    @pytest.fixture
    def mock_connector(self):
        """Create a mock connector that doesn't try to connect."""
        with patch('src.db.connectors.snowflake_connector.SnowflakeConnector.connect'):
            from src.db.connectors.snowflake_connector import SnowflakeConnector
            connector = SnowflakeConnector(
                account="test_account",
                user="test_user",
                password="test_password",
                warehouse="test_wh",
                database="SNOWFLAKE_SAMPLE_DATA",
                schema="TPCDS_SF10TCL"
            )
            yield connector

    def test_estimate_tpcds_sf10tcl_store_sales(self, mock_connector):
        """Test STORE_SALES row count for SF10TCL (10TB scale)."""
        from src.db.connectors.snowflake_connector import TPCDS_BASE_ROWS

        # Test STORE_SALES estimation
        estimated = mock_connector._estimate_tpcds_row_count(
            "SNOWFLAKE_SAMPLE_DATA",
            "TPCDS_SF10TCL",
            "STORE_SALES"
        )

        # SF10TCL = 10 * 1000 (TCL multiplier) = 10,000x base rows
        # STORE_SALES base = 2,880,000 rows
        # Expected: 2,880,000 * 10,000 = 28,800,000,000 (28.8B rows)
        expected = TPCDS_BASE_ROWS['STORE_SALES'] * 10 * 1000
        assert estimated == expected
        assert estimated == 28_800_000_000

    def test_estimate_tpcds_sf1_store_sales(self, mock_connector):
        """Test STORE_SALES row count for SF1 (1GB scale, no TCL suffix)."""
        from src.db.connectors.snowflake_connector import TPCDS_BASE_ROWS

        # Test STORE_SALES estimation for SF1 (no TCL suffix)
        estimated = mock_connector._estimate_tpcds_row_count(
            "SNOWFLAKE_SAMPLE_DATA",
            "TPCDS_SF1",
            "STORE_SALES"
        )

        # SF1 = 1x base rows
        expected = TPCDS_BASE_ROWS['STORE_SALES'] * 1
        assert estimated == expected
        assert estimated == 2_880_000

    def test_estimate_tpcds_sf100tcl_catalog_sales(self, mock_connector):
        """Test CATALOG_SALES row count for SF100TCL (100TB scale)."""
        from src.db.connectors.snowflake_connector import TPCDS_BASE_ROWS

        estimated = mock_connector._estimate_tpcds_row_count(
            "SNOWFLAKE_SAMPLE_DATA",
            "TPCDS_SF100TCL",
            "CATALOG_SALES"
        )

        # SF100TCL = 100 * 1000 = 100,000x base rows
        # CATALOG_SALES base = 1,440,000 rows
        expected = TPCDS_BASE_ROWS['CATALOG_SALES'] * 100 * 1000
        assert estimated == expected
        assert estimated == 144_000_000_000  # 144B rows

    def test_estimate_tpcds_non_snowflake_sample_data(self, mock_connector):
        """Test that non-SNOWFLAKE_SAMPLE_DATA databases return None."""
        estimated = mock_connector._estimate_tpcds_row_count(
            "MY_DATABASE",
            "TPCDS_SF10TCL",
            "STORE_SALES"
        )

        assert estimated is None

    def test_estimate_tpcds_non_tpcds_schema(self, mock_connector):
        """Test that non-TPCDS schemas return None."""
        estimated = mock_connector._estimate_tpcds_row_count(
            "SNOWFLAKE_SAMPLE_DATA",
            "SOME_OTHER_SCHEMA",
            "STORE_SALES"
        )

        assert estimated is None

    def test_estimate_tpcds_unknown_table(self, mock_connector):
        """Test that unknown table names return None."""
        estimated = mock_connector._estimate_tpcds_row_count(
            "SNOWFLAKE_SAMPLE_DATA",
            "TPCDS_SF10TCL",
            "UNKNOWN_TABLE"
        )

        assert estimated is None

    def test_estimate_tpcds_case_insensitive(self, mock_connector):
        """Test that table names are case-insensitive."""
        from src.db.connectors.snowflake_connector import TPCDS_BASE_ROWS

        # Test lowercase
        estimated_lower = mock_connector._estimate_tpcds_row_count(
            "snowflake_sample_data",
            "tpcds_sf10tcl",
            "store_sales"
        )

        expected = TPCDS_BASE_ROWS['STORE_SALES'] * 10 * 1000
        assert estimated_lower == expected

    def test_estimate_all_major_tpcds_tables(self, mock_connector):
        """Test estimation for all major TPC-DS tables."""
        from src.db.connectors.snowflake_connector import TPCDS_BASE_ROWS

        scale_factor = 10 * 1000  # SF10TCL

        for table_name, base_rows in TPCDS_BASE_ROWS.items():
            estimated = mock_connector._estimate_tpcds_row_count(
                "SNOWFLAKE_SAMPLE_DATA",
                "TPCDS_SF10TCL",
                table_name
            )
            expected = base_rows * scale_factor
            assert estimated == expected, f"Failed for {table_name}: expected {expected:,}, got {estimated:,}"


class TestVeryLargeTableStrategySelection:
    """Test that very large tables (>1B rows) select FEDERATED strategy."""

    def test_very_large_table_selects_federated_strategy(self):
        """Test that tables over 1B rows select FEDERATED strategy, not OPTIMIZED."""
        from src.core.single_db_query_optimizer import (
            SingleDatabaseQueryOptimizer,
            ExecutionStrategy,
            VERY_LARGE_TABLE_THRESHOLD
        )
        from unittest.mock import Mock

        # Create mock Jena resolver that returns very large row count
        mock_jena = Mock()
        mock_jena.get_table_row_count.return_value = 28_800_000_000  # 28.8B rows (TPCDS SF10TCL STORE_SALES)
        mock_jena.get_join_selectivity.return_value = None

        optimizer = SingleDatabaseQueryOptimizer(
            jena_resolver=mock_jena,
            weaviate_client=None,
            organization_id="test",
            database_type="snowflake"
        )

        # Analyze a simple query on a very large table
        analysis = optimizer.analyze_query(
            "SELECT SUM(ss_sales_price) FROM STORE_SALES",
            dialect="snowflake"
        )

        # Verify strategy is FEDERATED (not OPTIMIZED)
        assert analysis.strategy == ExecutionStrategy.FEDERATED, \
            f"Expected FEDERATED strategy for {analysis.largest_table_rows:,} row table, got {analysis.strategy.value}"

        # Verify async flag is set
        assert analysis.requires_async is True, \
            "Very large tables should require async execution"

        # Verify warning mentions federation
        assert any("federation" in w.lower() for w in analysis.warnings), \
            f"Warning should mention federation: {analysis.warnings}"

    def test_medium_table_selects_optimized_strategy(self):
        """Test that medium tables (1M-100M rows) select OPTIMIZED strategy."""
        from src.core.single_db_query_optimizer import (
            SingleDatabaseQueryOptimizer,
            ExecutionStrategy,
            PANDAS_MAX_ROWS,
            FEDERATION_THRESHOLD
        )
        from unittest.mock import Mock

        # Create mock Jena resolver that returns medium row count
        mock_jena = Mock()
        mock_jena.get_table_row_count.return_value = 50_000_000  # 50M rows
        mock_jena.get_join_selectivity.return_value = None

        optimizer = SingleDatabaseQueryOptimizer(
            jena_resolver=mock_jena,
            weaviate_client=None,
            organization_id="test",
            database_type="snowflake"
        )

        # Analyze a simple non-aggregation query
        analysis = optimizer.analyze_query(
            "SELECT * FROM MEDIUM_TABLE WHERE id > 100",
            dialect="snowflake"
        )

        # Verify strategy is OPTIMIZED (not DIRECT or FEDERATED)
        assert analysis.strategy == ExecutionStrategy.OPTIMIZED, \
            f"Expected OPTIMIZED strategy for {analysis.estimated_result_rows:,} row result, got {analysis.strategy.value}"


class TestFailFastOnUnknownTableSize:
    """Test fail-fast behavior when table size is unknown."""

    def test_fail_fast_enabled_raises_error(self):
        """Test that fail-fast raises ValueError when enabled and row count unknown."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer
        from src.config import settings

        # Save original setting
        original_value = settings.fail_fast_on_unknown_table_size

        try:
            # Enable fail-fast
            settings.fail_fast_on_unknown_table_size = True

            # Create optimizer with no Jena/Weaviate (will return None for row counts)
            optimizer = SingleDatabaseQueryOptimizer(
                jena_resolver=None,
                weaviate_client=None,
                organization_id="test",
                database_type="snowflake"
            )

            # This should raise ValueError due to unknown table size
            with pytest.raises(ValueError) as exc_info:
                optimizer.analyze_query(
                    "SELECT * FROM unknown_table",
                    dialect="snowflake"
                )

            assert "Cannot determine size of table" in str(exc_info.value)
            assert "UNKNOWN_TABLE" in str(exc_info.value)

        finally:
            # Restore original setting
            settings.fail_fast_on_unknown_table_size = original_value

    def test_fail_fast_disabled_adds_warning(self):
        """Test that fail-fast disabled adds warning instead of error."""
        from src.core.single_db_query_optimizer import SingleDatabaseQueryOptimizer
        from src.config import settings

        # Save original setting
        original_value = settings.fail_fast_on_unknown_table_size

        try:
            # Disable fail-fast
            settings.fail_fast_on_unknown_table_size = False

            # Create optimizer with no Jena/Weaviate
            optimizer = SingleDatabaseQueryOptimizer(
                jena_resolver=None,
                weaviate_client=None,
                organization_id="test",
                database_type="snowflake"
            )

            # This should NOT raise, but should add warning
            analysis = optimizer.analyze_query(
                "SELECT * FROM unknown_table",
                dialect="snowflake"
            )

            # Check that warning was added
            assert any("Unknown size" in w for w in analysis.warnings)

        finally:
            # Restore original setting
            settings.fail_fast_on_unknown_table_size = original_value


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
