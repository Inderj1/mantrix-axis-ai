#!/usr/bin/env python3
"""
Snowflake Test Data Setup Script

Creates test data in Snowflake that complements BigQuery data for cross-DB query testing.

Tables created:
- CUSTOMER_REGION: Customer to region mapping (joins with BigQuery customer_master_analysis)
- PRODUCT_CATALOG: Product master data (joins with BigQuery product_customer_matrix)
- SALES_TARGETS: Sales targets by segment (joins with BigQuery segment_performance_summary)

Usage:
    cd backend
    source venv/bin/activate
    python scripts/setup_snowflake_test_data.py

    # Or with explicit credentials:
    SNOWFLAKE_ACCOUNT=xxx SNOWFLAKE_USER=xxx SNOWFLAKE_PASSWORD=xxx \
    python scripts/setup_snowflake_test_data.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

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
    print("Install with: pip install snowflake-connector-python")


def get_snowflake_connection():
    """Create Snowflake connection from environment or defaults."""

    # Parse from connection string format if provided
    # "Driver={SnowflakeDSIIDriver};Server=DAYZHDW-AD88320.snowflakecomputing.com;Database=SNOWFLAKE_LEARNING_DB;uid=JAYSINGH;pwd=xxx"

    # Default values (from user's connection string)
    account = os.getenv('SNOWFLAKE_ACCOUNT', 'DAYZHDW-AD88320')
    user = os.getenv('SNOWFLAKE_USER', 'JAYSINGH')
    password = os.getenv('SNOWFLAKE_PASSWORD')
    database = os.getenv('SNOWFLAKE_DATABASE', 'SNOWFLAKE_LEARNING_DB')
    schema = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')
    warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')

    if not password:
        print("ERROR: SNOWFLAKE_PASSWORD environment variable required")
        print("\nSet it with: export SNOWFLAKE_PASSWORD='your_password'")
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


def create_schema_and_tables(cursor):
    """Create the test schema and tables."""

    print("\n" + "="*60)
    print("Creating Schema and Tables")
    print("="*60)

    # Create schema
    print("\n1. Creating schema CROSS_DB_TEST...")
    cursor.execute("CREATE SCHEMA IF NOT EXISTS CROSS_DB_TEST")
    cursor.execute("USE SCHEMA CROSS_DB_TEST")

    # Drop existing tables if they exist
    print("2. Dropping existing tables...")
    cursor.execute("DROP TABLE IF EXISTS CUSTOMER_REGION")
    cursor.execute("DROP TABLE IF EXISTS PRODUCT_CATALOG")
    cursor.execute("DROP TABLE IF EXISTS SALES_TARGETS")
    cursor.execute("DROP TABLE IF EXISTS REGIONAL_SETTINGS")

    # Create CUSTOMER_REGION table
    print("3. Creating CUSTOMER_REGION table...")
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
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    # Create PRODUCT_CATALOG table
    print("4. Creating PRODUCT_CATALOG table...")
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
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    # Create SALES_TARGETS table
    print("5. Creating SALES_TARGETS table...")
    cursor.execute("""
        CREATE TABLE SALES_TARGETS (
            TARGET_ID INTEGER AUTOINCREMENT PRIMARY KEY,
            SEGMENT_NAME VARCHAR(100),
            FISCAL_YEAR INTEGER,
            FISCAL_QUARTER VARCHAR(10),
            REVENUE_TARGET DECIMAL(15,2),
            MARGIN_TARGET_PCT DECIMAL(5,2),
            CUSTOMER_ACQUISITION_TARGET INTEGER,
            RETENTION_TARGET_PCT DECIMAL(5,2),
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    # Create REGIONAL_SETTINGS table (for region configuration)
    print("6. Creating REGIONAL_SETTINGS table...")
    cursor.execute("""
        CREATE TABLE REGIONAL_SETTINGS (
            REGION VARCHAR(50) PRIMARY KEY,
            REGION_MANAGER VARCHAR(100),
            TIMEZONE VARCHAR(50),
            CURRENCY VARCHAR(10),
            TAX_RATE DECIMAL(5,2),
            SHIPPING_ZONE VARCHAR(20),
            WAREHOUSE_CODE VARCHAR(20)
        )
    """)

    print("\n   All tables created successfully!")


def insert_customer_region_data(cursor):
    """Insert customer region data that maps to BigQuery customer_master_analysis."""

    print("\n" + "="*60)
    print("Inserting CUSTOMER_REGION Data")
    print("="*60)

    # Regions and territories
    regions = {
        'Northeast': ['New England', 'Mid-Atlantic', 'New York Metro'],
        'Southeast': ['Florida', 'Georgia', 'Carolinas'],
        'Midwest': ['Great Lakes', 'Plains', 'Chicago Metro'],
        'Southwest': ['Texas', 'Arizona', 'New Mexico'],
        'West': ['California', 'Pacific Northwest', 'Mountain']
    }

    sales_reps = [
        'John Smith', 'Sarah Johnson', 'Mike Williams', 'Emily Brown',
        'David Davis', 'Jennifer Wilson', 'Robert Miller', 'Lisa Anderson',
        'James Taylor', 'Maria Garcia', 'Kevin Martinez', 'Nancy Robinson'
    ]

    tiers = ['Enterprise', 'Strategic', 'Growth', 'Standard']
    payment_terms = ['Net 30', 'Net 45', 'Net 60', 'Net 90', '2% 10 Net 30']

    # Generate customer IDs that would match BigQuery format
    # BigQuery customer_master_analysis has Customer column (appears to be numeric string)
    customers = []

    # Generate ~500 customers to cover a good portion of BigQuery's 2903 customers
    for i in range(1, 501):
        customer_id = str(i)  # Match BigQuery format
        region = random.choice(list(regions.keys()))
        territory = random.choice(regions[region])

        # Create realistic customer data
        customer = {
            'customer_id': customer_id,
            'customer_name': f"Customer {customer_id} Corp",
            'region': region,
            'territory': territory,
            'sales_rep': random.choice(sales_reps),
            'account_tier': random.choices(tiers, weights=[10, 20, 30, 40])[0],
            'contract_start': datetime.now() - timedelta(days=random.randint(30, 1000)),
            'contract_end': datetime.now() + timedelta(days=random.randint(30, 730)),
            'credit_limit': random.choice([10000, 25000, 50000, 100000, 250000, 500000]),
            'payment_terms': random.choice(payment_terms)
        }
        customers.append(customer)

    # Insert data
    print(f"\n   Inserting {len(customers)} customer records...")

    insert_sql = """
        INSERT INTO CUSTOMER_REGION
        (CUSTOMER_ID, CUSTOMER_NAME, REGION, TERRITORY, SALES_REP,
         ACCOUNT_TIER, CONTRACT_START_DATE, CONTRACT_END_DATE,
         CREDIT_LIMIT, PAYMENT_TERMS)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for c in customers:
        cursor.execute(insert_sql, (
            c['customer_id'], c['customer_name'], c['region'], c['territory'],
            c['sales_rep'], c['account_tier'], c['contract_start'].date(),
            c['contract_end'].date(), c['credit_limit'], c['payment_terms']
        ))

    print(f"   Inserted {len(customers)} customers")


def insert_product_catalog_data(cursor):
    """Insert product catalog data that maps to BigQuery product_customer_matrix."""

    print("\n" + "="*60)
    print("Inserting PRODUCT_CATALOG Data")
    print("="*60)

    # Product categories and brands (beverage company context from BigQuery data)
    categories = {
        'Ready-to-Drink Tea': ['Arizona', 'Peace Tea'],
        'Energy Drinks': ['Arnold Palmer', 'Jack Nicklaus'],
        'Juice': ['Arizona Juice', 'Mucho Mango'],
        'Water': ['Arizona Water', 'Premium Water'],
        'Snacks': ['Arizona Snacks', 'Golden Bear']
    }

    pack_sizes = ['12 oz', '16 oz', '20 oz', '23 oz', '1 Gallon', '6-Pack', '12-Pack', '24-Pack']
    suppliers = ['SUP001', 'SUP002', 'SUP003', 'SUP004', 'SUP005']

    products = []

    # Generate ~200 products to cover BigQuery's product_customer_matrix
    material_nums = list(range(100000, 100200))  # Numeric material numbers

    for mat_num in material_nums:
        category = random.choice(list(categories.keys()))
        brand = random.choice(categories[category])

        base_cost = random.uniform(0.50, 5.00)
        markup = random.uniform(1.3, 2.5)

        product = {
            'material_number': str(mat_num),
            'product_name': f"{brand} {category} - SKU{mat_num}",
            'category': category,
            'brand': brand,
            'unit_cost': round(base_cost, 2),
            'list_price': round(base_cost * markup, 2),
            'weight_kg': round(random.uniform(0.3, 2.0), 3),
            'pack_size': random.choice(pack_sizes),
            'is_active': random.random() > 0.1,  # 90% active
            'launch_date': datetime.now() - timedelta(days=random.randint(100, 2000)),
            'supplier_id': random.choice(suppliers),
            'lead_time_days': random.choice([3, 5, 7, 10, 14, 21])
        }
        products.append(product)

    print(f"\n   Inserting {len(products)} product records...")

    insert_sql = """
        INSERT INTO PRODUCT_CATALOG
        (MATERIAL_NUMBER, PRODUCT_NAME, PRODUCT_CATEGORY, BRAND,
         UNIT_COST, LIST_PRICE, WEIGHT_KG, PACK_SIZE, IS_ACTIVE,
         LAUNCH_DATE, SUPPLIER_ID, LEAD_TIME_DAYS)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for p in products:
        cursor.execute(insert_sql, (
            p['material_number'], p['product_name'], p['category'], p['brand'],
            p['unit_cost'], p['list_price'], p['weight_kg'], p['pack_size'],
            p['is_active'], p['launch_date'].date(), p['supplier_id'], p['lead_time_days']
        ))

    print(f"   Inserted {len(products)} products")


def insert_sales_targets_data(cursor):
    """Insert sales targets that map to BigQuery segment_performance_summary."""

    print("\n" + "="*60)
    print("Inserting SALES_TARGETS Data")
    print("="*60)

    # RFM Segments from BigQuery (customer_master_analysis has RFM_Segment)
    segments = [
        'Champions', 'Loyal Customers', 'Potential Loyalists',
        'New Customers', 'Promising', 'Need Attention',
        'About to Sleep', 'At Risk', 'Cant Lose Them',
        'Hibernating', 'Lost'
    ]

    fiscal_years = [2023, 2024, 2025]
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']

    targets = []

    for year in fiscal_years:
        for quarter in quarters:
            for segment in segments:
                # Base targets vary by segment
                segment_multiplier = {
                    'Champions': 1.5,
                    'Loyal Customers': 1.3,
                    'Potential Loyalists': 1.2,
                    'New Customers': 0.8,
                    'Promising': 0.9,
                    'Need Attention': 1.0,
                    'About to Sleep': 0.7,
                    'At Risk': 0.6,
                    'Cant Lose Them': 1.1,
                    'Hibernating': 0.4,
                    'Lost': 0.3
                }.get(segment, 1.0)

                target = {
                    'segment': segment,
                    'fiscal_year': year,
                    'quarter': quarter,
                    'revenue_target': round(random.uniform(100000, 500000) * segment_multiplier, 2),
                    'margin_target_pct': round(random.uniform(20, 40), 2),
                    'customer_acquisition': int(random.uniform(10, 100) * segment_multiplier),
                    'retention_target_pct': round(random.uniform(70, 95), 2)
                }
                targets.append(target)

    print(f"\n   Inserting {len(targets)} sales target records...")

    insert_sql = """
        INSERT INTO SALES_TARGETS
        (SEGMENT_NAME, FISCAL_YEAR, FISCAL_QUARTER, REVENUE_TARGET,
         MARGIN_TARGET_PCT, CUSTOMER_ACQUISITION_TARGET, RETENTION_TARGET_PCT)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    for t in targets:
        cursor.execute(insert_sql, (
            t['segment'], t['fiscal_year'], t['quarter'], t['revenue_target'],
            t['margin_target_pct'], t['customer_acquisition'], t['retention_target_pct']
        ))

    print(f"   Inserted {len(targets)} sales targets")


def insert_regional_settings_data(cursor):
    """Insert regional configuration data."""

    print("\n" + "="*60)
    print("Inserting REGIONAL_SETTINGS Data")
    print("="*60)

    regions = [
        ('Northeast', 'Elizabeth Warren', 'America/New_York', 'USD', 8.25, 'ZONE-A', 'WH-NE01'),
        ('Southeast', 'Carlos Rodriguez', 'America/New_York', 'USD', 7.00, 'ZONE-B', 'WH-SE01'),
        ('Midwest', 'Patricia Thompson', 'America/Chicago', 'USD', 6.50, 'ZONE-C', 'WH-MW01'),
        ('Southwest', 'Miguel Santos', 'America/Denver', 'USD', 8.00, 'ZONE-D', 'WH-SW01'),
        ('West', 'Jennifer Chang', 'America/Los_Angeles', 'USD', 9.50, 'ZONE-E', 'WH-WE01')
    ]

    print(f"\n   Inserting {len(regions)} regional settings...")

    insert_sql = """
        INSERT INTO REGIONAL_SETTINGS
        (REGION, REGION_MANAGER, TIMEZONE, CURRENCY, TAX_RATE, SHIPPING_ZONE, WAREHOUSE_CODE)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    for region in regions:
        cursor.execute(insert_sql, region)

    print(f"   Inserted {len(regions)} regional settings")


def verify_data(cursor):
    """Verify the inserted data."""

    print("\n" + "="*60)
    print("Verifying Data")
    print("="*60)

    tables = ['CUSTOMER_REGION', 'PRODUCT_CATALOG', 'SALES_TARGETS', 'REGIONAL_SETTINGS']

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table}: {count} rows")

    # Sample queries
    print("\n   Sample CUSTOMER_REGION data:")
    cursor.execute("SELECT CUSTOMER_ID, CUSTOMER_NAME, REGION, ACCOUNT_TIER FROM CUSTOMER_REGION LIMIT 3")
    for row in cursor.fetchall():
        print(f"      {row}")

    print("\n   Sample PRODUCT_CATALOG data:")
    cursor.execute("SELECT MATERIAL_NUMBER, PRODUCT_NAME, PRODUCT_CATEGORY, LIST_PRICE FROM PRODUCT_CATALOG LIMIT 3")
    for row in cursor.fetchall():
        print(f"      {row}")


def print_cross_db_query_examples():
    """Print example cross-DB queries that can be run."""

    print("\n" + "="*60)
    print("CROSS-DATABASE QUERY EXAMPLES")
    print("="*60)

    print("""
These queries can be used to test cross-database federation between
BigQuery (arizona-poc.copa_export_copa_data_000000000000) and Snowflake (CROSS_DB_TEST).

1. Customer Revenue by Region:
   "Show me total revenue by region for our customers"

   -- BigQuery: customer_master_analysis (Customer, Monetary)
   -- Snowflake: CUSTOMER_REGION (CUSTOMER_ID, REGION)
   -- Join on: Customer = CUSTOMER_ID

2. Product Performance with Catalog Details:
   "Show product sales with product details"

   -- BigQuery: product_customer_matrix (Material_Number, Net_Sales, Gross_Margin)
   -- Snowflake: PRODUCT_CATALOG (MATERIAL_NUMBER, PRODUCT_NAME, PRODUCT_CATEGORY)
   -- Join on: Material_Number = MATERIAL_NUMBER

3. Segment Performance vs Targets:
   "Compare actual segment performance against targets"

   -- BigQuery: segment_performance_summary (Segment_Name, Monetary_sum)
   -- Snowflake: SALES_TARGETS (SEGMENT_NAME, REVENUE_TARGET)
   -- Join on: Segment_Name = SEGMENT_NAME

4. Customer Analysis with Regional Settings:
   "Show customer tiers by region with tax rates"

   -- Snowflake: CUSTOMER_REGION JOIN REGIONAL_SETTINGS
   -- BigQuery: customer_master_analysis
   -- Multi-table join

Test Commands:
   cd backend && source venv/bin/activate
   python scripts/test_cross_db_federation.py
""")


def main():
    """Main entry point."""

    print("\n" + "="*60)
    print("SNOWFLAKE TEST DATA SETUP")
    print("="*60)

    if not SNOWFLAKE_AVAILABLE:
        print("\nSnowflake connector not available. Install with:")
        print("   pip install snowflake-connector-python")
        sys.exit(1)

    try:
        # Connect
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        print("\n   Connected successfully!")

        # Create tables
        create_schema_and_tables(cursor)

        # Insert data
        insert_customer_region_data(cursor)
        insert_product_catalog_data(cursor)
        insert_sales_targets_data(cursor)
        insert_regional_settings_data(cursor)

        # Commit
        conn.commit()

        # Verify
        verify_data(cursor)

        # Print examples
        print_cross_db_query_examples()

        print("\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print("\nSnowflake test data has been created in:")
        print(f"   Database: {os.getenv('SNOWFLAKE_DATABASE', 'SNOWFLAKE_LEARNING_DB')}")
        print("   Schema: CROSS_DB_TEST")
        print("\nTables created:")
        print("   - CUSTOMER_REGION (500 rows)")
        print("   - PRODUCT_CATALOG (200 rows)")
        print("   - SALES_TARGETS (~132 rows)")
        print("   - REGIONAL_SETTINGS (5 rows)")

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
