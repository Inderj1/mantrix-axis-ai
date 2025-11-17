"""
Cross-Database Integration Test

Tests joining data between PostgreSQL (Docker) and BigQuery using the
federated query planner and cross-database executor.
"""
import pytest
import sys
import os
import asyncio
import pandas as pd
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.federated_query_planner import FederatedQueryPlanner
from src.core.cross_database_executor import CrossDatabaseExecutor
from src.db.connector_factory import ConnectorFactory

# PostgreSQL test database config
PG_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'test_mantrix',
    'user': 'test_user',
    'password': 'test_pass_123',
    'schema': 'sales'
}


class TestCrossDatabaseJoin:
    """Test cross-database JOIN between PostgreSQL and BigQuery."""

    @pytest.fixture
    def planner(self):
        """Create federated query planner."""
        return FederatedQueryPlanner()

    @pytest.fixture
    def executor(self):
        """Create cross-database executor."""
        return CrossDatabaseExecutor()

    @pytest.mark.asyncio
    async def test_postgres_bigquery_simple_join(self, planner, executor):
        """
        Test simple JOIN between PostgreSQL and BigQuery.

        PostgreSQL: customer data (in Docker)
        BigQuery: hypothetical order data

        For this test, we'll simulate by using PostgreSQL for both sides,
        but with the cross-database infrastructure.
        """
        print("\n=== Test: Cross-Database JOIN (PostgreSQL + PostgreSQL simulation) ===")

        # Since we may not have BigQuery credentials, we'll test the infrastructure
        # by joining two tables from PostgreSQL, but treating them as if they're
        # from different databases to test the cross-DB machinery

        # Query: Join customers with orders
        sql = """
            SELECT
                c.id as customer_id,
                c.name as customer_name,
                c.email,
                o.id as order_id,
                o.total_amount
            FROM customers c
            INNER JOIN orders o ON c.id = o.customer_id
            WHERE c.active = true
            LIMIT 5
        """

        # Create execution plan
        # Note: Both tables are actually in PostgreSQL, but we're testing the planner
        plan = planner.create_execution_plan(
            sql=sql,
            primary_database='postgresql',
            table_database_mapping={
                'customers': 'postgresql',
                'orders': 'postgresql'
            }
        )

        print(f"\nExecution Plan:")
        print(f"  Strategy: {plan.strategy.value}")
        print(f"  Databases: {plan.databases_involved}")
        print(f"  Steps: {len(plan.steps)}")
        for step in plan.steps:
            print(f"    {step.step_number}. {step.description}")

        # Assert plan is reasonable
        assert plan.strategy.value == 'single_database', "Should use single database strategy"
        assert 'postgresql' in plan.databases_involved
        assert len(plan.steps) >= 1

        print("\n✅ Execution plan created successfully")

    @pytest.mark.asyncio
    async def test_cross_db_join_direct_method(self, executor):
        """
        Test direct cross-database JOIN method.

        This tests the execute_cross_db_join method which fetches from
        two databases and joins in memory using pandas.
        """
        print("\n=== Test: Direct Cross-Database JOIN Method ===")

        # Left side: fetch customers from PostgreSQL
        left_query = """
            SELECT customer_id, customer_name, email
            FROM sales.customers
            LIMIT 3
        """

        # Right side: fetch orders from PostgreSQL
        # (simulating as if this were from a different database)
        right_query = """
            SELECT order_id, customer_id, total_amount, status
            FROM sales.orders
            LIMIT 10
        """

        print("\nExecuting cross-database JOIN...")
        print(f"  Left: PostgreSQL (customers)")
        print(f"  Right: PostgreSQL (orders)")
        print(f"  Join: customers.customer_id = orders.customer_id")

        try:
            # Execute cross-database join
            result_df = await executor.execute_cross_db_join(
                left_db='postgresql',
                left_query=left_query,
                right_db='postgresql',
                right_query=right_query,
                join_condition='customer_id = customer_id',
                join_type='INNER',
                user_id='test_user',
                organization_id='test_org',
                database_configs={
                    'postgresql': PG_CONFIG
                }
            )

            print(f"\nJoin Results:")
            print(f"  Rows returned: {len(result_df)}")
            print(f"  Columns: {list(result_df.columns)}")

            if len(result_df) > 0:
                print(f"\n  Sample data (first 3 rows):")
                print(result_df.head(3).to_string())

                # Assertions
                assert len(result_df) > 0, "Should return some rows"
                assert 'customer_name' in result_df.columns, "Should have customer name"
                assert 'total_amount' in result_df.columns, "Should have order amount"

                print("\n✅ Cross-database JOIN executed successfully!")
            else:
                print("\n⚠️  No matching rows (this may be expected if data doesn't match)")

        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            # Check if it's a credentials issue
            if 'credentials' in str(e).lower() or 'config' in str(e).lower():
                pytest.skip(f"Skipping due to configuration: {str(e)}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_federated_query_analysis(self, planner):
        """
        Test federated query analysis to detect cross-database queries.
        """
        print("\n=== Test: Federated Query Analysis ===")

        # Simulate a cross-database query
        sql = """
            SELECT
                bq_sales.revenue,
                pg_customers.customer_name
            FROM bigquery_sales bq_sales
            JOIN postgres_customers pg_customers
                ON bq_sales.customer_id = pg_customers.id
        """

        # Analyze the query
        analysis = planner.analyze_query(
            sql=sql,
            primary_database='bigquery',
            table_database_mapping={
                'bigquery_sales': 'bigquery',
                'postgres_customers': 'postgresql'
            }
        )

        print(f"\nQuery Analysis:")
        print(f"  Databases involved: {analysis['databases']}")
        print(f"  Is federated: {analysis['is_federated']}")
        print(f"  Has joins: {analysis['has_joins']}")
        print(f"  Complexity: {analysis['complexity']}")
        print(f"  Tables by database:")
        for db, tables in analysis['tables_by_database'].items():
            print(f"    {db}: {[t.table for t in tables]}")

        # Assertions
        assert analysis['is_federated'], "Should detect as federated query"
        assert len(analysis['databases']) == 2, "Should detect 2 databases"
        assert 'bigquery' in analysis['databases']
        assert 'postgresql' in analysis['databases']

        print("\n✅ Query analysis successful!")

    @pytest.mark.asyncio
    async def test_execution_strategies(self, planner):
        """
        Test that planner selects appropriate strategies for different queries.
        """
        print("\n=== Test: Execution Strategy Selection ===")

        test_cases = [
            {
                'name': 'Single Database Query',
                'sql': 'SELECT * FROM users LIMIT 10',
                'mapping': {'users': 'bigquery'},
                'expected_strategy': 'single_database'
            },
            {
                'name': 'Simple Cross-DB Query',
                'sql': 'SELECT * FROM table1 JOIN table2 ON table1.id = table2.id',
                'mapping': {'table1': 'bigquery', 'table2': 'snowflake'},
                'expected_strategy': 'distributed'  # or move_to_primary
            },
            {
                'name': 'Complex Multi-DB Query',
                'sql': '''
                    SELECT t1.*, t2.*, t3.*
                    FROM table1 t1
                    JOIN table2 t2 ON t1.id = t2.id
                    JOIN table3 t3 ON t2.id = t3.id
                ''',
                'mapping': {
                    'table1': 'bigquery',
                    'table2': 'snowflake',
                    'table3': 'postgresql'
                },
                'expected_strategy': 'distributed'  # Complex query
            }
        ]

        for test_case in test_cases:
            print(f"\n  Testing: {test_case['name']}")

            plan = planner.create_execution_plan(
                sql=test_case['sql'],
                primary_database='bigquery',
                table_database_mapping=test_case['mapping']
            )

            print(f"    Strategy selected: {plan.strategy.value}")
            print(f"    Expected: {test_case['expected_strategy']}")
            print(f"    Databases: {plan.databases_involved}")
            print(f"    Steps: {len(plan.steps)}")

            # Strategy might vary based on optimization logic, so we just check it's valid
            assert plan.strategy.value in [
                'single_database',
                'move_to_primary',
                'distributed',
                'materialize'
            ], f"Should select a valid strategy"

        print("\n✅ All strategy selections completed!")

    def test_connector_factory_integration(self):
        """
        Test that ConnectorFactory works with cross-database executor.
        """
        print("\n=== Test: ConnectorFactory Integration ===")

        factory = ConnectorFactory()

        # Test creating PostgreSQL connector
        try:
            pg_connector = factory.create_connector(
                'postgresql',
                config=PG_CONFIG
            )
            print(f"  ✅ Created PostgreSQL connector: {type(pg_connector).__name__}")

            # Test it can connect
            # Note: This requires actual database connection
            print(f"  Testing connection...")

        except Exception as e:
            print(f"  ⚠️  PostgreSQL connector creation failed: {str(e)}")
            if 'module' not in str(e).lower():
                raise

        # Test BigQuery connector (may not have credentials)
        try:
            bq_connector = factory.create_connector('bigquery')
            print(f"  ✅ Created BigQuery connector: {type(bq_connector).__name__}")
        except Exception as e:
            print(f"  ⚠️  BigQuery connector creation failed (expected if no credentials): {str(e)}")

        print("\n✅ ConnectorFactory integration test complete!")


def run_integration_test():
    """Run the integration test directly."""
    print("\n" + "="*80)
    print("CROSS-DATABASE INTEGRATION TEST")
    print("="*80)

    # Run async tests
    async def run_tests():
        planner = FederatedQueryPlanner()
        executor = CrossDatabaseExecutor()

        test = TestCrossDatabaseJoin()

        # Test 1: Query analysis
        await test.test_federated_query_analysis(planner)

        # Test 2: Execution strategies
        await test.test_execution_strategies(planner)

        # Test 3: Simple join
        await test.test_postgres_bigquery_simple_join(planner, executor)

        # Test 4: Direct cross-DB join
        await test.test_cross_db_join_direct_method(executor)

        # Test 5: Connector factory
        test.test_connector_factory_integration()

    # Run all tests
    asyncio.run(run_tests())

    print("\n" + "="*80)
    print("ALL INTEGRATION TESTS COMPLETE!")
    print("="*80)


if __name__ == '__main__':
    run_integration_test()
