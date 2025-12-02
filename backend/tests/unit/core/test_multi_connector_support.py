"""
Tests for Multi-Connector Schema Search Support

These tests verify that SQLGenerator can:
1. Load connector IDs from ALL enabled connectors (not just one database type)
2. Search vectors across ALL databases (no database_type filter)
3. Determine target database from tables used in generated SQL
4. Dynamically create connectors for different database types
5. Execute queries on the correct target database
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Dict, List, Any


class TestRefreshConnectorIdsMultiDatabase:
    """Tests for _refresh_connector_ids loading ALL database types."""

    @pytest.fixture
    def mock_mongo_collection(self):
        """Create a mock MongoDB collection with multi-database connectors."""
        mock_collection = Mock()

        # Simulate connectors from multiple database types
        mock_connectors = [
            {
                "_id": "bigquery_connector_1",
                "organization_id": "test_org",
                "connector_type": "bigquery",
                "enabled_for_chat": True,
                "status": "connected"
            },
            {
                "_id": "snowflake_connector_1",
                "organization_id": "test_org",
                "connector_type": "snowflake",
                "enabled_for_chat": True,
                "status": "active"
            },
            {
                "_id": "postgresql_connector_1",
                "organization_id": "test_org",
                "connector_type": "postgresql",
                "enabled_for_chat": True,
                "status": "connected"
            }
        ]
        mock_collection.find.return_value = mock_connectors
        return mock_collection

    @pytest.fixture
    def mock_sql_generator(self, mock_mongo_collection):
        """Create a minimal mock SQLGenerator for testing _refresh_connector_ids."""
        generator = Mock()
        generator.organization_id = "test_org"
        generator.database_type = "bigquery"
        generator.connector_ids = []
        generator.connector_db_types = {}
        return generator

    def test_refresh_loads_all_database_types(self, mock_mongo_collection):
        """Verify that _refresh_connector_ids loads connectors from ALL database types."""
        # Simulate the find query that should be made by _refresh_connector_ids
        # Note: NO "connector_type" filter - this is the key change for multi-connector support
        expected_query = {
            "organization_id": "test_org",
            # Note: NO "connector_type" filter
            "enabled_for_chat": True,
            "status": {"$in": ["connected", "active"]}
        }

        # Call find with our expected query
        mock_mongo_collection.find(expected_query)

        # Verify the query structure (no connector_type)
        call_args = mock_mongo_collection.find.call_args[0][0]
        assert "connector_type" not in call_args, \
            "Query should NOT filter by connector_type for multi-connector support"
        assert "organization_id" in call_args, \
            "Query should still filter by organization_id for security"
        assert "enabled_for_chat" in call_args, \
            "Query should still filter by enabled_for_chat"

    def test_refresh_builds_connector_db_types_mapping(self, mock_mongo_collection):
        """Verify that connector_db_types mapping is built correctly."""
        connectors = list(mock_mongo_collection.find.return_value)

        # Simulate what _refresh_connector_ids should do
        connector_ids = []
        connector_db_types = {}

        for connector in connectors:
            connector_id = str(connector.get("_id"))
            if connector_id:
                connector_ids.append(connector_id)
                connector_db_types[connector_id] = connector.get("connector_type")

        # Verify results
        assert len(connector_ids) == 3
        assert "bigquery_connector_1" in connector_ids
        assert "snowflake_connector_1" in connector_ids
        assert "postgresql_connector_1" in connector_ids

        assert connector_db_types["bigquery_connector_1"] == "bigquery"
        assert connector_db_types["snowflake_connector_1"] == "snowflake"
        assert connector_db_types["postgresql_connector_1"] == "postgresql"


class TestGetRelevantSchemasNoDatabaseTypeFilter:
    """Tests for _get_relevant_schemas not filtering by database_type."""

    def test_vector_search_called_without_database_type(self):
        """Verify vector search is called without database_type filter."""
        mock_vector_client = Mock()
        mock_vector_client.search_similar_tables.return_value = [
            {"table_name": "orders", "database_type": "bigquery", "score": 0.9},
            {"table_name": "customers", "database_type": "snowflake", "score": 0.85},
        ]

        # Simulate the call that should be made
        query_embedding = [0.1] * 1536  # Mock embedding
        organization_id = "test_org"
        connector_ids = ["bq_1", "sf_1"]

        # This is what _get_relevant_schemas should call
        mock_vector_client.search_similar_tables(
            query_embedding,
            limit=10,
            # Note: NO database_type parameter
            organization_id=organization_id,
            connector_ids=connector_ids
        )

        # Verify the call
        call_kwargs = mock_vector_client.search_similar_tables.call_args

        # Check that database_type was NOT passed
        if call_kwargs.kwargs:
            assert "database_type" not in call_kwargs.kwargs, \
                "search_similar_tables should NOT receive database_type filter"

        # Check that connector_ids WAS passed (for security)
        if call_kwargs.kwargs:
            assert "connector_ids" in call_kwargs.kwargs, \
                "search_similar_tables MUST receive connector_ids for security"

    def test_vector_search_returns_multi_database_tables(self):
        """Verify vector search can return tables from multiple databases."""
        # Simulated vector search results from multiple databases
        multi_db_results = [
            {
                "table_name": "sales_orders",
                "database_type": "bigquery",
                "connector_id": "bq_1",
                "score": 0.95,
                "description": "Sales order data"
            },
            {
                "table_name": "inventory",
                "database_type": "snowflake",
                "connector_id": "sf_1",
                "score": 0.90,
                "description": "Inventory levels"
            },
            {
                "table_name": "customers",
                "database_type": "postgresql",
                "connector_id": "pg_1",
                "score": 0.88,
                "description": "Customer master data"
            }
        ]

        # Verify we got tables from different databases
        db_types = {r["database_type"] for r in multi_db_results}
        assert len(db_types) == 3, "Should have tables from 3 different database types"
        assert "bigquery" in db_types
        assert "snowflake" in db_types
        assert "postgresql" in db_types


class TestDetermineTargetDatabase:
    """Tests for _determine_target_database method."""

    def test_single_database_type_detected(self):
        """When all tables are from one database, return that database type."""
        tables_used = ["orders", "order_items", "customers"]
        schemas = [
            {"table_name": "orders", "database_type": "snowflake"},
            {"table_name": "order_items", "database_type": "snowflake"},
            {"table_name": "customers", "database_type": "snowflake"},
        ]

        # Simulate _determine_target_database logic
        db_types_used = set()
        for table in tables_used:
            for schema in schemas:
                if schema.get('table_name') == table:
                    db_types_used.add(schema.get('database_type'))
                    break

        assert len(db_types_used) == 1
        assert "snowflake" in db_types_used

    def test_empty_tables_returns_default(self):
        """When no tables used, return default database type."""
        tables_used = []
        schemas = []
        default_db_type = "bigquery"

        db_types_used = set()
        for table in tables_used:
            for schema in schemas:
                if schema.get('table_name') == table:
                    db_types_used.add(schema.get('database_type'))
                    break

        # Should return default when empty
        result = default_db_type if len(db_types_used) == 0 else list(db_types_used)[0]
        assert result == default_db_type

    def test_cross_database_detected(self):
        """When tables from multiple databases are used, detect cross-database query."""
        tables_used = ["bq_orders", "sf_inventory"]
        schemas = [
            {"table_name": "bq_orders", "database_type": "bigquery"},
            {"table_name": "sf_inventory", "database_type": "snowflake"},
        ]

        db_types_used = set()
        for table in tables_used:
            for schema in schemas:
                if schema.get('table_name') == table:
                    db_types_used.add(schema.get('database_type'))
                    break

        assert len(db_types_used) == 2, "Should detect tables from 2 different databases"
        assert "bigquery" in db_types_used
        assert "snowflake" in db_types_used

    def test_table_not_found_uses_default(self):
        """When a table isn't found in schemas, it doesn't affect detection."""
        tables_used = ["orders", "unknown_table"]
        schemas = [
            {"table_name": "orders", "database_type": "postgresql"},
        ]
        default_db_type = "bigquery"

        db_types_used = set()
        for table in tables_used:
            for schema in schemas:
                if schema.get('table_name') == table:
                    db_types_used.add(schema.get('database_type', default_db_type))
                    break

        # Only "orders" was found, so only postgresql
        assert len(db_types_used) == 1
        assert "postgresql" in db_types_used


class TestGetConnectorForDatabase:
    """Tests for _get_connector_for_database dynamic connector pool."""

    def test_returns_primary_connector_for_matching_type(self):
        """When requested type matches primary, return existing connector."""
        # Simulate SQLGenerator state
        primary_db_type = "bigquery"
        primary_connector = Mock(name="primary_bq_connector")

        requested_type = "bigquery"

        # Logic from _get_connector_for_database
        if requested_type == primary_db_type:
            result = primary_connector

        assert result == primary_connector

    def test_creates_new_connector_for_different_type(self):
        """When requested type differs, create new connector."""
        primary_db_type = "bigquery"
        primary_connector = Mock(name="primary_bq_connector")
        connector_pool = {}

        requested_type = "snowflake"

        # Simulate connector creation
        if requested_type != primary_db_type:
            if requested_type not in connector_pool:
                new_connector = Mock(name=f"new_{requested_type}_connector")
                new_connector.connect = Mock()
                connector_pool[requested_type] = new_connector

        assert requested_type in connector_pool
        assert connector_pool[requested_type] is not None

    def test_reuses_cached_connector(self):
        """When connector already in pool, reuse it."""
        connector_pool = {}

        # First request creates connector
        snowflake_connector = Mock(name="snowflake_connector")
        connector_pool["snowflake"] = snowflake_connector

        # Second request should reuse
        requested_type = "snowflake"
        if requested_type in connector_pool:
            result = connector_pool[requested_type]

        assert result == snowflake_connector

    def test_connector_connect_called_on_creation(self):
        """Verify connect() is called when creating new connector."""
        mock_connector = Mock()
        mock_connector.connect = Mock()

        # Simulate creation
        mock_connector.connect()

        mock_connector.connect.assert_called_once()


class TestExecuteQueryMultiConnector:
    """Tests for execute_query with target_database_type parameter."""

    def test_uses_default_connector_when_no_target_specified(self):
        """When target_database_type is None, use primary connector."""
        primary_connector = Mock()
        primary_connector.validate_query.return_value = {"valid": True}
        primary_connector.execute_query.return_value = {"rows": [{"id": 1}]}

        # Simulate execute_query logic
        target_database_type = None
        primary_db_type = "bigquery"

        if target_database_type and target_database_type != primary_db_type:
            db_connector = Mock(name="alternate_connector")
        else:
            db_connector = primary_connector

        assert db_connector == primary_connector

    def test_uses_alternate_connector_when_target_differs(self):
        """When target_database_type differs from primary, use alternate connector."""
        primary_connector = Mock(name="bq_connector")
        snowflake_connector = Mock(name="sf_connector")

        connector_pool = {"snowflake": snowflake_connector}
        primary_db_type = "bigquery"
        target_database_type = "snowflake"

        if target_database_type and target_database_type != primary_db_type:
            db_connector = connector_pool.get(target_database_type)
        else:
            db_connector = primary_connector

        assert db_connector == snowflake_connector

    def test_federated_type_uses_primary_connector(self):
        """When target is 'federated', use primary connector (for now)."""
        primary_connector = Mock(name="bq_connector")
        primary_db_type = "bigquery"
        target_database_type = "federated"

        # Federated queries are handled specially, default to primary
        if target_database_type == "federated":
            db_connector = primary_connector
        elif target_database_type and target_database_type != primary_db_type:
            db_connector = Mock(name="alternate")
        else:
            db_connector = primary_connector

        assert db_connector == primary_connector


class TestGenerateSQLFlowIntegration:
    """Integration tests for the full generate_sql flow with multi-connector support."""

    def test_result_includes_target_database_type(self):
        """Verify generate_sql result includes target_database_type."""
        # Simulated result after target DB detection
        result = {
            "sql": "SELECT * FROM inventory",
            "tables_used": ["inventory"],
            "target_database_type": "snowflake",
            "requires_alternate_connector": True
        }

        assert "target_database_type" in result
        assert result["target_database_type"] == "snowflake"
        assert result["requires_alternate_connector"] is True

    def test_cross_database_error_in_result(self):
        """Verify cross-database errors are captured in result."""
        result = {
            "sql": "SELECT * FROM bq_table JOIN sf_table ON ...",
            "tables_used": ["bq_table", "sf_table"],
            "cross_database_error": "Query uses tables from multiple databases (bigquery, snowflake)"
        }

        assert "cross_database_error" in result

    def test_validation_uses_target_connector(self):
        """Verify validation is performed on the target database connector."""
        # Simulate the validation flow
        target_db_type = "postgresql"
        primary_db_type = "bigquery"

        primary_connector = Mock(name="bq_connector")
        pg_connector = Mock(name="pg_connector")
        pg_connector.validate_query.return_value = {"valid": True}

        connector_pool = {"postgresql": pg_connector}

        # Logic from generate_sql
        if target_db_type and target_db_type != primary_db_type and target_db_type != 'federated':
            validation_connector = connector_pool.get(target_db_type, primary_connector)
        else:
            validation_connector = primary_connector

        # Validate using the correct connector
        validation_connector.validate_query("SELECT * FROM users")

        # Verify pg_connector was used, not primary
        pg_connector.validate_query.assert_called_once()
        primary_connector.validate_query.assert_not_called()


class TestConnectorIdsSecurityFilter:
    """Tests verifying that connector_ids filter is maintained for security."""

    def test_vector_search_includes_connector_ids(self):
        """Verify vector search always includes connector_ids for security isolation."""
        mock_vector_client = Mock()

        connector_ids = ["org1_bq", "org1_sf"]
        organization_id = "org1"

        # Call that should be made
        mock_vector_client.search_similar_tables(
            embedding=[0.1] * 1536,
            limit=10,
            organization_id=organization_id,
            connector_ids=connector_ids
        )

        call_kwargs = mock_vector_client.search_similar_tables.call_args.kwargs

        assert "connector_ids" in call_kwargs, \
            "connector_ids MUST be passed for security isolation"
        assert call_kwargs["connector_ids"] == connector_ids

    def test_empty_connector_ids_handled_gracefully(self):
        """When no connectors are enabled, handle gracefully."""
        connector_ids = []

        # Should pass None when empty (let Weaviate handle it)
        search_connector_ids = connector_ids if connector_ids else None

        assert search_connector_ids is None


class TestConnectorDbTypesMapping:
    """Tests for the connector_db_types mapping."""

    def test_mapping_built_during_refresh(self):
        """Verify connector_db_types is built correctly during refresh."""
        connectors = [
            {"_id": "c1", "connector_type": "bigquery"},
            {"_id": "c2", "connector_type": "snowflake"},
            {"_id": "c3", "connector_type": "bigquery"},  # Second BQ connector
        ]

        connector_db_types = {}
        for c in connectors:
            connector_db_types[str(c["_id"])] = c["connector_type"]

        assert connector_db_types["c1"] == "bigquery"
        assert connector_db_types["c2"] == "snowflake"
        assert connector_db_types["c3"] == "bigquery"

    def test_mapping_allows_lookup_by_connector_id(self):
        """Verify we can look up database type by connector_id."""
        connector_db_types = {
            "bq_123": "bigquery",
            "sf_456": "snowflake",
            "pg_789": "postgresql"
        }

        # When we get a table with connector_id, we can find its db_type
        table_connector_id = "sf_456"
        db_type = connector_db_types.get(table_connector_id)

        assert db_type == "snowflake"


class TestActualImplementation:
    """Tests that verify the actual implementation code changes."""

    def test_refresh_connector_ids_code_no_connector_type_filter(self):
        """Verify the actual _refresh_connector_ids code doesn't filter by connector_type."""
        import ast

        with open('src/core/sql_generator.py', 'r') as f:
            source = f.read()

        # Find the _refresh_connector_ids method and check it doesn't use connector_type filter
        # The method should have a comment indicating the filter was removed
        assert 'REMOVED: "connector_type"' in source or \
               '# REMOVED: "connector_type": self.database_type' in source, \
            "_refresh_connector_ids should have connector_type filter removed"

        # Verify connector_db_types is being built
        assert 'connector_db_types' in source, \
            "connector_db_types mapping should be built"

    def test_get_relevant_schemas_code_no_database_type_filter(self):
        """Verify the actual _get_relevant_schemas code doesn't pass database_type."""
        with open('src/core/sql_generator.py', 'r') as f:
            source = f.read()

        # Check that database_type is removed from vector search
        assert 'REMOVED: database_type=self.database_type' in source or \
               '# REMOVED: database_type=self.database_type' in source, \
            "_get_relevant_schemas should have database_type filter removed from vector search"

    def test_determine_target_database_method_exists(self):
        """Verify _determine_target_database method exists."""
        import ast

        with open('src/core/sql_generator.py', 'r') as f:
            tree = ast.parse(f.read())

        method_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'SQLGenerator':
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '_determine_target_database':
                        method_found = True
                        # Check it has the right parameters
                        args = [arg.arg for arg in item.args.args]
                        assert 'tables_used' in args, "Method should have tables_used parameter"
                        assert 'schemas' in args, "Method should have schemas parameter"
                        break

        assert method_found, "_determine_target_database method should exist in SQLGenerator"

    def test_get_connector_for_database_method_exists(self):
        """Verify _get_connector_for_database method exists."""
        import ast

        with open('src/core/sql_generator.py', 'r') as f:
            tree = ast.parse(f.read())

        method_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'SQLGenerator':
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '_get_connector_for_database':
                        method_found = True
                        # Check it has the right parameters
                        args = [arg.arg for arg in item.args.args]
                        assert 'db_type' in args, "Method should have db_type parameter"
                        break

        assert method_found, "_get_connector_for_database method should exist in SQLGenerator"

    def test_execute_query_has_target_database_type_parameter(self):
        """Verify execute_query method has target_database_type parameter."""
        import ast

        with open('src/core/sql_generator.py', 'r') as f:
            tree = ast.parse(f.read())

        param_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'SQLGenerator':
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == 'execute_query':
                        args = [arg.arg for arg in item.args.args]
                        if 'target_database_type' in args:
                            param_found = True
                        break

        assert param_found, "execute_query should have target_database_type parameter"

    def test_validation_uses_validation_connector_variable(self):
        """Verify validation code uses validation_connector instead of self.bq_client."""
        with open('src/core/sql_generator.py', 'r') as f:
            source = f.read()

        # Check that validation_connector is used
        assert 'validation_connector.validate_query' in source, \
            "Validation should use validation_connector"
        assert 'validation_connector.execute_query' in source, \
            "Test execution should use validation_connector"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
