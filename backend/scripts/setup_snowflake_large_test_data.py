#!/usr/bin/env python3
"""
Snowflake Large Test Data Setup Script

Creates LARGE test data in Snowflake for stress-testing cross-DB federation.

Tables created:
- CUSTOMER_REGION: 50,000 customers (joins with BigQuery customer_master_analysis)
- PRODUCT_CATALOG: 10,000 products (joins with BigQuery product_customer_matrix)
- SALES_TRANSACTIONS: 500,000 transactions (for aggregation tests)
- SALES_TARGETS: ~132 segment targets

Usage:
    cd backend
    source venv/bin/activate
    python scripts/setup_snowflake_large_test_data.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import time

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Load .env file
from dotenv import load_dotenv
env_path = Path(backend_path) / '.env'
load_dotenv(env_path)
print(f"Loaded environment from: {env_path}")

try:
    import snowflake.connector
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    print("WARNING: snowflake-connector-python not installed")


def get_snowflake_connection():
    """Create Snowflake connection from environment."""
    account = os.getenv('SNOWFLAKE_ACCOUNT', 'DAYZHDW-AD88320')
    user = os.getenv('SNOWFLAKE_USER', 'JAYSINGH')
    password = os.getenv('SNOWFLAKE_PASSWORD')
    database = os.getenv('SNOWFLAKE_DATABASE', 'SNOWFLAKE_LEARNING_DB')
    schema = os.getenv('SNOWFLAKE_SCHEMA', 'CROSS_DB_TEST')
    warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')

    if not password:
        print("ERROR: SNOWFLAKE_PASSWORD environment variable required")
        sys.exit(1)

    print(f"\nConnecting to Snowflake:")
    print(f"  Account: {account}")
    print(f"  User: {user}")
    print(f"  Database: {database}")
    print(f"  Schema: {schema}")
    print(f"  Warehouse: {warehouse}")

    conn = snowflake.connector.connect(
        account=account,
        user=user,
        password=password,
        database=database,
        schema=schema,
        warehouse=warehouse,
    )

    return conn


def create_tables(cursor):
    """Create the large test tables."""

    print("\n" + "="*60)
    print("Creating Large Test Tables")
    print("="*60)

    cursor.execute("CREATE SCHEMA IF NOT EXISTS CROSS_DB_TEST")
    cursor.execute("USE SCHEMA CROSS_DB_TEST")

    # Drop and recreate CUSTOMER_REGION with more data
    print("\n1. Recreating CUSTOMER_REGION table...")
    cursor.execute("DROP TABLE IF EXISTS CUSTOMER_REGION")
    cursor.execute("""
        CREATE TABLE CUSTOMER_REGION (
            CUSTOMER_ID VARCHAR(50) PRIMARY KEY,
            CUSTOMER_NAME VARCHAR(200),
            REGION VARCHAR(50),
            TERRITORY VARCHAR(100),
            SALES_REP VARCHAR(100),
            ACCOUNT_TIER VARCHAR(20),
            CONTRACT_START_DATE DATE,
            CONTRACT_END_DATE DATE,
            CREDIT_LIMIT DECIMAL(15,2),
            PAYMENT_TERMS VARCHAR(50),
            ANNUAL_REVENUE DECIMAL(15,2),
            EMPLOYEE_COUNT INTEGER,
            INDUSTRY VARCHAR(100),
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    # Drop and recreate PRODUCT_CATALOG with more data
    print("2. Recreating PRODUCT_CATALOG table...")
    cursor.execute("DROP TABLE IF EXISTS PRODUCT_CATALOG")
    cursor.execute("""
        CREATE TABLE PRODUCT_CATALOG (
            MATERIAL_NUMBER VARCHAR(50) PRIMARY KEY,
            PRODUCT_NAME VARCHAR(200),
            PRODUCT_CATEGORY VARCHAR(100),
            BRAND VARCHAR(100),
            UNIT_COST DECIMAL(15,2),
            LIST_PRICE DECIMAL(15,2),
            WEIGHT_KG DECIMAL(10,3),
            PACK_SIZE VARCHAR(50),
            IS_ACTIVE BOOLEAN DEFAULT TRUE,
            LAUNCH_DATE DATE,
            SUPPLIER_ID VARCHAR(50),
            LEAD_TIME_DAYS INTEGER,
            MIN_ORDER_QTY INTEGER,
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    # Create new SALES_TRANSACTIONS table for large volume testing
    print("3. Creating SALES_TRANSACTIONS table...")
    cursor.execute("DROP TABLE IF EXISTS SALES_TRANSACTIONS")
    cursor.execute("""
        CREATE TABLE SALES_TRANSACTIONS (
            TRANSACTION_ID VARCHAR(50) PRIMARY KEY,
            CUSTOMER_ID VARCHAR(50),
            MATERIAL_NUMBER VARCHAR(50),
            TRANSACTION_DATE DATE,
            QUANTITY INTEGER,
            UNIT_PRICE DECIMAL(15,2),
            TOTAL_AMOUNT DECIMAL(15,2),
            DISCOUNT_PCT DECIMAL(5,2),
            REGION VARCHAR(50),
            SALES_CHANNEL VARCHAR(50),
            ORDER_TYPE VARCHAR(50),
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    print("\n   Tables created successfully!")


def insert_customers_batch(cursor, num_customers=50000, batch_size=5000):
    """Insert large number of customers using batch inserts."""

    print("\n" + "="*60)
    print(f"Inserting {num_customers:,} CUSTOMER_REGION Records")
    print("="*60)

    regions = {
        'Northeast': ['New England', 'Mid-Atlantic', 'New York Metro', 'Boston Area', 'Philadelphia'],
        'Southeast': ['Florida', 'Georgia', 'Carolinas', 'Virginia', 'Tennessee'],
        'Midwest': ['Great Lakes', 'Plains', 'Chicago Metro', 'Ohio Valley', 'Minnesota'],
        'Southwest': ['Texas', 'Arizona', 'New Mexico', 'Nevada', 'Colorado'],
        'West': ['California', 'Pacific Northwest', 'Mountain', 'Hawaii', 'Alaska']
    }

    sales_reps = [f"Rep_{i}" for i in range(1, 101)]  # 100 sales reps
    tiers = ['Enterprise', 'Strategic', 'Growth', 'Standard', 'Startup']
    payment_terms = ['Net 30', 'Net 45', 'Net 60', 'Net 90', '2% 10 Net 30']
    industries = ['Retail', 'Manufacturing', 'Healthcare', 'Technology', 'Finance',
                  'Education', 'Government', 'Food & Beverage', 'Transportation', 'Energy']

    insert_sql = """
        INSERT INTO CUSTOMER_REGION
        (CUSTOMER_ID, CUSTOMER_NAME, REGION, TERRITORY, SALES_REP,
         ACCOUNT_TIER, CONTRACT_START_DATE, CONTRACT_END_DATE,
         CREDIT_LIMIT, PAYMENT_TERMS, ANNUAL_REVENUE, EMPLOYEE_COUNT, INDUSTRY)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    start_time = time.time()

    for batch_start in range(0, num_customers, batch_size):
        batch_end = min(batch_start + batch_size, num_customers)
        batch_data = []

        for i in range(batch_start + 1, batch_end + 1):
            customer_id = str(i)
            region = random.choice(list(regions.keys()))
            territory = random.choice(regions[region])

            batch_data.append((
                customer_id,
                f"Customer {customer_id} Corp",
                region,
                territory,
                random.choice(sales_reps),
                random.choices(tiers, weights=[5, 15, 25, 35, 20])[0],
                (datetime.now() - timedelta(days=random.randint(30, 1500))).date(),
                (datetime.now() + timedelta(days=random.randint(30, 730))).date(),
                random.choice([10000, 25000, 50000, 100000, 250000, 500000, 1000000]),
                random.choice(payment_terms),
                random.randint(100000, 50000000),
                random.randint(10, 10000),
                random.choice(industries)
            ))

        cursor.executemany(insert_sql, batch_data)

        elapsed = time.time() - start_time
        print(f"   Inserted {batch_end:,} / {num_customers:,} customers ({elapsed:.1f}s)")

    print(f"\n   Total: {num_customers:,} customers inserted in {time.time() - start_time:.1f}s")


def insert_products_batch(cursor, num_products=10000, batch_size=2000):
    """Insert large number of products using batch inserts."""

    print("\n" + "="*60)
    print(f"Inserting {num_products:,} PRODUCT_CATALOG Records")
    print("="*60)

    categories = ['Ready-to-Drink Tea', 'Energy Drinks', 'Juice', 'Water', 'Snacks',
                  'Sports Drinks', 'Coffee', 'Carbonated', 'Organic', 'Premium']
    brands = ['Arizona', 'Peace Tea', 'Arnold Palmer', 'Golden Bear', 'Mucho Mango',
              'Jack Nicklaus', 'Premium Water', 'Arizona Juice', 'Green Tea', 'Black Tea']
    pack_sizes = ['12 oz', '16 oz', '20 oz', '23 oz', '1 Gallon', '6-Pack', '12-Pack', '24-Pack', '1 Liter']
    suppliers = [f'SUP{str(i).zfill(3)}' for i in range(1, 51)]  # 50 suppliers

    insert_sql = """
        INSERT INTO PRODUCT_CATALOG
        (MATERIAL_NUMBER, PRODUCT_NAME, PRODUCT_CATEGORY, BRAND,
         UNIT_COST, LIST_PRICE, WEIGHT_KG, PACK_SIZE, IS_ACTIVE,
         LAUNCH_DATE, SUPPLIER_ID, LEAD_TIME_DAYS, MIN_ORDER_QTY)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    start_time = time.time()

    for batch_start in range(0, num_products, batch_size):
        batch_end = min(batch_start + batch_size, num_products)
        batch_data = []

        for i in range(batch_start + 100000, batch_end + 100000):
            mat_num = str(i)
            category = random.choice(categories)
            brand = random.choice(brands)
            base_cost = random.uniform(0.50, 10.00)

            batch_data.append((
                mat_num,
                f"{brand} {category} - SKU{mat_num}",
                category,
                brand,
                round(base_cost, 2),
                round(base_cost * random.uniform(1.3, 2.5), 2),
                round(random.uniform(0.3, 5.0), 3),
                random.choice(pack_sizes),
                random.random() > 0.1,
                (datetime.now() - timedelta(days=random.randint(100, 3000))).date(),
                random.choice(suppliers),
                random.choice([3, 5, 7, 10, 14, 21, 30]),
                random.choice([12, 24, 48, 96, 144])
            ))

        cursor.executemany(insert_sql, batch_data)

        elapsed = time.time() - start_time
        print(f"   Inserted {batch_end:,} / {num_products:,} products ({elapsed:.1f}s)")

    print(f"\n   Total: {num_products:,} products inserted in {time.time() - start_time:.1f}s")


def insert_transactions_batch(cursor, num_transactions=500000, batch_size=10000):
    """Insert large number of sales transactions for aggregation testing."""

    print("\n" + "="*60)
    print(f"Inserting {num_transactions:,} SALES_TRANSACTIONS Records")
    print("="*60)

    regions = ['Northeast', 'Southeast', 'Midwest', 'Southwest', 'West']
    channels = ['Direct', 'Distributor', 'Online', 'Retail', 'Wholesale']
    order_types = ['Regular', 'Rush', 'Backorder', 'Subscription', 'Promotional']

    insert_sql = """
        INSERT INTO SALES_TRANSACTIONS
        (TRANSACTION_ID, CUSTOMER_ID, MATERIAL_NUMBER, TRANSACTION_DATE,
         QUANTITY, UNIT_PRICE, TOTAL_AMOUNT, DISCOUNT_PCT, REGION,
         SALES_CHANNEL, ORDER_TYPE)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    start_time = time.time()

    for batch_start in range(0, num_transactions, batch_size):
        batch_end = min(batch_start + batch_size, num_transactions)
        batch_data = []

        for i in range(batch_start + 1, batch_end + 1):
            trans_id = f"TXN{str(i).zfill(10)}"
            customer_id = str(random.randint(1, 50000))  # Match customer range
            material_num = str(random.randint(100000, 109999))  # Match product range
            quantity = random.randint(1, 500)
            unit_price = round(random.uniform(1.0, 50.0), 2)
            discount = round(random.uniform(0, 25), 2)
            total = round(quantity * unit_price * (1 - discount/100), 2)

            batch_data.append((
                trans_id,
                customer_id,
                material_num,
                (datetime.now() - timedelta(days=random.randint(0, 730))).date(),
                quantity,
                unit_price,
                total,
                discount,
                random.choice(regions),
                random.choice(channels),
                random.choice(order_types)
            ))

        cursor.executemany(insert_sql, batch_data)

        elapsed = time.time() - start_time
        pct = (batch_end / num_transactions) * 100
        print(f"   Inserted {batch_end:,} / {num_transactions:,} transactions ({pct:.0f}%) - {elapsed:.1f}s")

    print(f"\n   Total: {num_transactions:,} transactions inserted in {time.time() - start_time:.1f}s")


def verify_data(cursor):
    """Verify the inserted data with counts and samples."""

    print("\n" + "="*60)
    print("Verifying Data")
    print("="*60)

    tables = ['CUSTOMER_REGION', 'PRODUCT_CATALOG', 'SALES_TRANSACTIONS']

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table}: {count:,} rows")

    # Sample aggregation query
    print("\n   Sample aggregation - Sales by Region:")
    cursor.execute("""
        SELECT REGION, COUNT(*) as txn_count, SUM(TOTAL_AMOUNT) as total_sales
        FROM SALES_TRANSACTIONS
        GROUP BY REGION
        ORDER BY total_sales DESC
    """)
    for row in cursor.fetchall():
        print(f"      {row[0]}: {row[1]:,} txns, ${row[2]:,.2f}")


def print_test_queries():
    """Print example queries for testing federation."""

    print("\n" + "="*60)
    print("LARGE-SCALE FEDERATION TEST QUERIES")
    print("="*60)
    print("""
Try these queries in the Mantrix UI to test federation at scale:

1. Large Join - Customer Revenue by Region (50K customers):
   "Show total customer revenue by region with account tier breakdown"

2. Aggregation Heavy - Transaction Summary:
   "Show monthly sales trends by region for 2024"

3. Multi-Table Join:
   "Show top 100 customers by transaction volume with their region and tier"

4. Cross-DB Aggregation:
   "Compare BigQuery customer monetary value against Snowflake transaction totals"

5. Complex Federation:
   "Show product category sales by region with customer segment distribution"
""")


def main():
    """Main entry point."""

    print("\n" + "="*60)
    print("SNOWFLAKE LARGE TEST DATA SETUP")
    print("="*60)
    print("\nThis will create:")
    print("  - 50,000 customers")
    print("  - 10,000 products")
    print("  - 500,000 transactions")
    print("\nEstimated time: 2-5 minutes")

    if not SNOWFLAKE_AVAILABLE:
        print("\nSnowflake connector not available.")
        sys.exit(1)

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        print("\n   Connected successfully!")

        # Create tables
        create_tables(cursor)

        # Insert data
        insert_customers_batch(cursor, num_customers=50000)
        insert_products_batch(cursor, num_products=10000)
        insert_transactions_batch(cursor, num_transactions=500000)

        # Commit
        conn.commit()

        # Verify
        verify_data(cursor)

        # Print test queries
        print_test_queries()

        print("\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print("\nSnowflake large test data created:")
        print("   - CUSTOMER_REGION: 50,000 rows")
        print("   - PRODUCT_CATALOG: 10,000 rows")
        print("   - SALES_TRANSACTIONS: 500,000 rows")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
