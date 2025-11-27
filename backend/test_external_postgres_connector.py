#!/usr/bin/env python3
"""
Test script for external PostgreSQL connector validation.

This script validates that the external PostgreSQL test database is properly
configured and accessible via the PostgreSQL connector.

Usage:
    python test_external_postgres_connector.py

Prerequisites:
    - External PostgreSQL container running: docker-compose up -d postgres-external
    - Backend virtual environment activated: source venv/bin/activate
"""

import sys
import json
from datetime import datetime
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

# External PostgreSQL test database configuration
DB_CONFIG = {
    "host": "localhost",  # Change to "postgres-external" if running inside Docker network
    "port": 5434,
    "database": "sap_test_db",
    "user": "test_user",
    "password": "test_password",
}

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message):
    """Print formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(message):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def test_connection():
    """Test database connection."""
    print_header("Test 1: Database Connection")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        print_success(f"Connected to PostgreSQL successfully")
        print_info(f"PostgreSQL Version: {version.split(',')[0]}")

        cursor.close()
        conn.close()

        return True
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")
        print_warning("Make sure the external PostgreSQL container is running:")
        print_warning("  docker-compose up -d postgres-external")
        return False


def test_schema_exists():
    """Test that the supply_chain schema exists."""
    print_header("Test 2: Schema Validation")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Check if schema exists
        cursor.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = 'supply_chain'
        """)

        result = cursor.fetchone()

        if result:
            print_success("Schema 'supply_chain' exists")
            return True
        else:
            print_error("Schema 'supply_chain' not found")
            return False

    except Exception as e:
        print_error(f"Schema validation failed: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_tables_loaded():
    """Test that all tables are loaded with data."""
    print_header("Test 3: Table Data Validation")

    expected_tables = {
        "customers": 500,
        "materials": 50,
        "sales_orders": 5000,
        "order_items": 10000,  # Minimum expected
    }

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        all_passed = True

        for table, min_rows in expected_tables.items():
            cursor.execute(f"SELECT COUNT(*) FROM supply_chain.{table}")
            count = cursor.fetchone()[0]

            if count >= min_rows:
                print_success(f"Table '{table}': {count:,} rows (expected >= {min_rows:,})")
            else:
                print_error(f"Table '{table}': {count:,} rows (expected >= {min_rows:,})")
                all_passed = False

        return all_passed

    except Exception as e:
        print_error(f"Table validation failed: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_leading_zero_customer_ids():
    """Test that customer IDs have leading zeros."""
    print_header("Test 4: Leading Zero Validation")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Sample some customer IDs
        cursor.execute("""
            SELECT customer_id, customer_name
            FROM supply_chain.customers
            LIMIT 5
        """)

        customers = cursor.fetchall()

        all_have_leading_zeros = True
        for customer in customers:
            customer_id = customer['customer_id']
            has_leading_zero = customer_id.startswith('0') and len(customer_id) == 10

            if has_leading_zero:
                print_success(f"Customer ID '{customer_id}' has correct format")
            else:
                print_error(f"Customer ID '{customer_id}' missing leading zeros")
                all_have_leading_zeros = False

        return all_have_leading_zeros

    except Exception as e:
        print_error(f"Leading zero validation failed: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_sample_queries():
    """Test sample analytical queries."""
    print_header("Test 5: Sample Query Execution")

    queries = [
        {
            "name": "Top 5 Customers by Revenue",
            "query": """
                SELECT
                    customer_id,
                    customer_name,
                    country,
                    abc_class,
                    total_net_sales
                FROM supply_chain.v_customer_revenue
                ORDER BY total_net_sales DESC NULLS LAST
                LIMIT 5
            """
        },
        {
            "name": "Top 5 Materials by Margin",
            "query": """
                SELECT
                    material_number,
                    material_description,
                    total_revenue,
                    total_margin,
                    avg_margin_pct
                FROM supply_chain.v_material_performance
                ORDER BY total_margin DESC NULLS LAST
                LIMIT 5
            """
        },
        {
            "name": "Monthly Sales Trend (Last 6 Months)",
            "query": """
                SELECT
                    TO_CHAR(month, 'YYYY-MM') as month,
                    order_count,
                    total_net_sales,
                    ROUND(avg_margin_pct, 2) as avg_margin_pct
                FROM supply_chain.v_monthly_sales
                ORDER BY month DESC
                LIMIT 6
            """
        },
        {
            "name": "Customer Distribution by RFM Segment",
            "query": """
                SELECT
                    rfm_segment,
                    COUNT(*) as customer_count,
                    SUM(total_net_sales) as segment_revenue
                FROM supply_chain.v_customer_revenue
                GROUP BY rfm_segment
                ORDER BY segment_revenue DESC NULLS LAST
            """
        }
    ]

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        all_passed = True

        for query_info in queries:
            try:
                print_info(f"\nTesting: {query_info['name']}")

                cursor.execute(query_info['query'])
                results = cursor.fetchall()

                if results:
                    print_success(f"Query executed successfully, returned {len(results)} rows")

                    # Print first row as sample
                    if results:
                        print_info("Sample result:")
                        print(f"  {json.dumps(dict(results[0]), indent=2, default=str)}")
                else:
                    print_warning(f"Query returned no results")

            except Exception as e:
                print_error(f"Query failed: {str(e)}")
                all_passed = False

        return all_passed

    except Exception as e:
        print_error(f"Sample query testing failed: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()


def test_join_with_format_mismatch():
    """Test JOIN scenario with leading zero vs non-leading zero IDs."""
    print_header("Test 6: Format Normalization Scenario")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Simulate a query that would fail with format mismatch
        # This tests if our data has the consistency needed to test FormatNormalizer

        print_info("Testing JOIN with customer IDs...")

        cursor.execute("""
            SELECT
                o.order_number,
                o.customer_id as order_customer_id,
                c.customer_id as customer_master_id,
                c.customer_name,
                COUNT(oi.id) as line_item_count
            FROM supply_chain.sales_orders o
            JOIN supply_chain.customers c ON o.customer_id = c.customer_id
            LEFT JOIN supply_chain.order_items oi ON o.order_number = oi.order_number
            WHERE o.order_status = 'Delivered'
            GROUP BY o.order_number, o.customer_id, c.customer_id, c.customer_name
            LIMIT 5
        """)

        results = cursor.fetchall()

        if results:
            print_success(f"JOIN query executed successfully, returned {len(results)} orders")

            for row in results:
                if row['order_customer_id'] == row['customer_master_id']:
                    print_success(f"  Order {row['order_number']}: Customer ID match verified")
                else:
                    print_error(f"  Order {row['order_number']}: Customer ID mismatch!")

            return True
        else:
            print_warning("No delivered orders found for JOIN test")
            return False

    except Exception as e:
        print_error(f"Format normalization test failed: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()


def print_connection_instructions():
    """Print instructions for connecting via UI."""
    print_header("Database Connector Configuration")

    print_info("To connect to this database via the UI:")
    print()
    print("1. Navigate to: Database Configuration page (Admin menu)")
    print("2. Click 'Add Connection'")
    print("3. Fill in the following details:")
    print()
    print(f"   Connection Name: {Colors.BOLD}SAP Test Database{Colors.ENDC}")
    print(f"   Database Type:   {Colors.BOLD}PostgreSQL{Colors.ENDC}")
    print(f"   Host:            {Colors.BOLD}localhost{Colors.ENDC} (or 'postgres-external' from Docker)")
    print(f"   Port:            {Colors.BOLD}5434{Colors.ENDC}")
    print(f"   Database:        {Colors.BOLD}sap_test_db{Colors.ENDC}")
    print(f"   User:            {Colors.BOLD}test_user{Colors.ENDC}")
    print(f"   Password:        {Colors.BOLD}test_password{Colors.ENDC}")
    print(f"   Schema:          {Colors.BOLD}supply_chain{Colors.ENDC}")
    print()
    print("4. Click 'Test Connection'")
    print("5. Click 'Add' to save")
    print("6. Toggle 'Enable for Chat' to use in queries")
    print()


def print_test_queries():
    """Print sample test queries to try."""
    print_header("Sample Test Queries")

    test_queries = [
        "Show me the top 10 customers by revenue",
        "Which materials have the highest gross margin?",
        "What are the monthly sales trends for 2024?",
        "Find customers in the 'At Risk' RFM segment",
        "Show me revenue by country",
        "Which products are selling the most in Q4 2024?",
    ]

    print_info("Try these natural language queries after connecting:")
    print()
    for i, query in enumerate(test_queries, 1):
        print(f"  {i}. {query}")
    print()


def main():
    """Run all tests."""
    print_header("External PostgreSQL Connector Test Suite")
    print_info(f"Test Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print_info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("Connection", test_connection),
        ("Schema", test_schema_exists),
        ("Tables", test_tables_loaded),
        ("Leading Zeros", test_leading_zero_customer_ids),
        ("Sample Queries", test_sample_queries),
        ("JOIN Format Test", test_join_with_format_mismatch),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))

    # Print summary
    print_header("Test Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"  {test_name:.<40} {status}")

    print()
    print(f"  Total: {passed}/{total} tests passed")
    print()

    if passed == total:
        print_success("All tests passed! Database is ready for connector testing.")
        print()
        print_connection_instructions()
        print_test_queries()
        return 0
    else:
        print_error(f"{total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
