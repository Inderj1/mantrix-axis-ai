-- ============================================================================
-- SAP-Style Supply Chain Test Database
-- Large performance testing dataset with realistic SAP field naming patterns
-- ============================================================================
--
-- Purpose: External PostgreSQL test database for connector testing
-- Schema: supply_chain
-- Volume: 500 customers, 50 materials, 5,000 orders, 10,000+ line items
--
-- Key Features:
-- - Leading zero customer IDs (e.g., '0000001234') to test FormatNormalizer
-- - RFM segmentation for customer analytics
-- - ABC classification for customer importance
-- - Time-series data (2022-2024)
-- - SAP-style field naming conventions
-- - Realistic business scenarios and edge cases
-- ============================================================================

-- Create schema
CREATE SCHEMA IF NOT EXISTS supply_chain;

-- Set search path
SET search_path TO supply_chain, public;

-- ============================================================================
-- TABLE: customers
-- SAP-style customer master data with leading zero IDs
-- ============================================================================
CREATE TABLE supply_chain.customers (
    customer_id VARCHAR(10) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    abc_class VARCHAR(10) NOT NULL,  -- 'A', 'B', 'C' classification
    rfm_segment VARCHAR(50) NOT NULL, -- RFM segmentation
    customer_since DATE NOT NULL,
    credit_limit DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE supply_chain.customers IS 'Customer master data with SAP-style leading zero IDs';
COMMENT ON COLUMN supply_chain.customers.customer_id IS 'Customer ID with leading zeros (e.g., 0000001234)';
COMMENT ON COLUMN supply_chain.customers.abc_class IS 'ABC classification: A (high value), B (medium value), C (low value)';
COMMENT ON COLUMN supply_chain.customers.rfm_segment IS 'RFM Segment: Champions, Loyal, Potential, At Risk, Lost, etc.';

-- ============================================================================
-- TABLE: materials
-- SAP-style material master data (products)
-- ============================================================================
CREATE TABLE supply_chain.materials (
    material_number VARCHAR(18) PRIMARY KEY,
    material_description VARCHAR(255) NOT NULL,
    material_group VARCHAR(50) NOT NULL,
    material_type VARCHAR(50) NOT NULL,
    unit_of_measure VARCHAR(10) NOT NULL,
    standard_price DECIMAL(15,2) NOT NULL,
    cost_price DECIMAL(15,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE supply_chain.materials IS 'Material master data (products)';
COMMENT ON COLUMN supply_chain.materials.material_number IS 'SAP-style material number';
COMMENT ON COLUMN supply_chain.materials.material_group IS 'Product category/group';

-- ============================================================================
-- TABLE: sales_orders
-- SAP-style sales order header data
-- ============================================================================
CREATE TABLE supply_chain.sales_orders (
    order_number VARCHAR(10) PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL,
    order_date DATE NOT NULL,
    posting_date DATE NOT NULL,
    delivery_date DATE,
    order_status VARCHAR(50) NOT NULL,
    sales_organization VARCHAR(50),
    distribution_channel VARCHAR(50),
    division VARCHAR(50),
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES supply_chain.customers(customer_id)
);

COMMENT ON TABLE supply_chain.sales_orders IS 'Sales order header data';
COMMENT ON COLUMN supply_chain.sales_orders.order_number IS 'Unique order identifier';
COMMENT ON COLUMN supply_chain.sales_orders.order_status IS 'Status: Open, In Progress, Delivered, Cancelled';

-- ============================================================================
-- TABLE: order_items
-- SAP COPA-style profitability analysis (line items)
-- ============================================================================
CREATE TABLE supply_chain.order_items (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(10) NOT NULL,
    line_item_number INT NOT NULL,
    customer_id VARCHAR(10) NOT NULL,  -- Denormalized for JOIN testing
    material_number VARCHAR(18) NOT NULL,
    posting_date DATE NOT NULL,
    quantity DECIMAL(15,3) NOT NULL,
    unit_of_measure VARCHAR(10) NOT NULL,
    gross_revenue DECIMAL(15,2) NOT NULL,
    net_sales DECIMAL(15,2) NOT NULL,
    discounts DECIMAL(15,2) DEFAULT 0,
    cogs DECIMAL(15,2) NOT NULL,
    gross_margin DECIMAL(15,2) NOT NULL,
    contribution_margin DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_number) REFERENCES supply_chain.sales_orders(order_number),
    FOREIGN KEY (customer_id) REFERENCES supply_chain.customers(customer_id),
    FOREIGN KEY (material_number) REFERENCES supply_chain.materials(material_number),
    UNIQUE (order_number, line_item_number)
);

COMMENT ON TABLE supply_chain.order_items IS 'Order line items with COPA-style profitability data';
COMMENT ON COLUMN supply_chain.order_items.gross_revenue IS 'Revenue before deductions';
COMMENT ON COLUMN supply_chain.order_items.net_sales IS 'Revenue after discounts';
COMMENT ON COLUMN supply_chain.order_items.gross_margin IS 'Net Sales - COGS';
COMMENT ON COLUMN supply_chain.order_items.contribution_margin IS 'Gross Margin - Variable Costs';

-- ============================================================================
-- INDEXES for performance
-- ============================================================================
CREATE INDEX idx_customers_abc_class ON supply_chain.customers(abc_class);
CREATE INDEX idx_customers_rfm_segment ON supply_chain.customers(rfm_segment);
CREATE INDEX idx_customers_country ON supply_chain.customers(country);

CREATE INDEX idx_materials_group ON supply_chain.materials(material_group);
CREATE INDEX idx_materials_type ON supply_chain.materials(material_type);

CREATE INDEX idx_orders_customer ON supply_chain.sales_orders(customer_id);
CREATE INDEX idx_orders_posting_date ON supply_chain.sales_orders(posting_date);
CREATE INDEX idx_orders_status ON supply_chain.sales_orders(order_status);

CREATE INDEX idx_items_order ON supply_chain.order_items(order_number);
CREATE INDEX idx_items_customer ON supply_chain.order_items(customer_id);
CREATE INDEX idx_items_material ON supply_chain.order_items(material_number);
CREATE INDEX idx_items_posting_date ON supply_chain.order_items(posting_date);

-- ============================================================================
-- POPULATE: Customers (500 customers with leading zeros)
-- ============================================================================
INSERT INTO supply_chain.customers (customer_id, customer_name, country, region, city, abc_class, rfm_segment, customer_since, credit_limit)
SELECT
    LPAD(i::TEXT, 10, '0') AS customer_id,
    CASE
        WHEN i % 10 = 1 THEN 'Global Electronics Ltd'
        WHEN i % 10 = 2 THEN 'Tech Solutions Inc'
        WHEN i % 10 = 3 THEN 'Manufacturing Corp'
        WHEN i % 10 = 4 THEN 'Retail Partners Group'
        WHEN i % 10 = 5 THEN 'Distribution Services'
        WHEN i % 10 = 6 THEN 'Innovation Systems'
        WHEN i % 10 = 7 THEN 'Enterprise Holdings'
        WHEN i % 10 = 8 THEN 'Commerce Solutions'
        WHEN i % 10 = 9 THEN 'Industry Leaders LLC'
        ELSE 'Business Ventures Co'
    END || ' ' || i AS customer_name,
    CASE
        WHEN i % 15 = 0 THEN 'USA'
        WHEN i % 15 = 1 THEN 'Germany'
        WHEN i % 15 = 2 THEN 'UK'
        WHEN i % 15 = 3 THEN 'France'
        WHEN i % 15 = 4 THEN 'Japan'
        WHEN i % 15 = 5 THEN 'Canada'
        WHEN i % 15 = 6 THEN 'Australia'
        WHEN i % 15 = 7 THEN 'China'
        WHEN i % 15 = 8 THEN 'India'
        WHEN i % 15 = 9 THEN 'Brazil'
        WHEN i % 15 = 10 THEN 'Mexico'
        WHEN i % 15 = 11 THEN 'Singapore'
        WHEN i % 15 = 12 THEN 'UAE'
        WHEN i % 15 = 13 THEN 'South Korea'
        ELSE 'Netherlands'
    END AS country,
    CASE
        WHEN i % 15 IN (0,5,10) THEN 'Americas'
        WHEN i % 15 IN (1,2,3,14) THEN 'EMEA'
        ELSE 'APAC'
    END AS region,
    'City ' || i AS city,
    CASE
        WHEN i <= 100 THEN 'A'  -- Top 100 customers
        WHEN i <= 300 THEN 'B'  -- Next 200 customers
        ELSE 'C'                -- Remaining 200 customers
    END AS abc_class,
    CASE
        WHEN i <= 50 THEN 'Champions'
        WHEN i <= 120 THEN 'Loyal Customers'
        WHEN i <= 200 THEN 'Potential Loyalists'
        WHEN i <= 280 THEN 'Promising'
        WHEN i <= 350 THEN 'Needs Attention'
        WHEN i <= 420 THEN 'At Risk'
        WHEN i <= 470 THEN 'Cannot Lose Them'
        ELSE 'Lost Customers'
    END AS rfm_segment,
    (CURRENT_DATE - ((i * 3) || ' days')::INTERVAL)::DATE AS customer_since,
    CASE
        WHEN i <= 100 THEN 1000000 + (i * 10000)
        WHEN i <= 300 THEN 500000 + (i * 5000)
        ELSE 100000 + (i * 1000)
    END AS credit_limit
FROM generate_series(1, 500) AS i;

-- ============================================================================
-- POPULATE: Materials (50 materials)
-- ============================================================================
INSERT INTO supply_chain.materials (material_number, material_description, material_group, material_type, unit_of_measure, standard_price, cost_price, is_active)
VALUES
    ('MAT000000000000001', 'Premium Laptop - Core i7, 16GB RAM', 'Electronics', 'FERT', 'EA', 1299.99, 850.00, true),
    ('MAT000000000000002', 'Wireless Mouse - Ergonomic Design', 'Electronics', 'FERT', 'EA', 49.99, 25.00, true),
    ('MAT000000000000003', 'Mechanical Keyboard - RGB Backlit', 'Electronics', 'FERT', 'EA', 129.99, 65.00, true),
    ('MAT000000000000004', '27" 4K Monitor - IPS Panel', 'Electronics', 'FERT', 'EA', 449.99, 280.00, true),
    ('MAT000000000000005', 'USB-C Docking Station', 'Electronics', 'FERT', 'EA', 199.99, 110.00, true),
    ('MAT000000000000006', 'Noise-Cancelling Headphones', 'Electronics', 'FERT', 'EA', 299.99, 150.00, true),
    ('MAT000000000000007', '1080p Webcam - Autofocus', 'Electronics', 'FERT', 'EA', 89.99, 45.00, true),
    ('MAT000000000000008', 'Wireless Charger - Fast Charging', 'Electronics', 'FERT', 'EA', 39.99, 18.00, true),
    ('MAT000000000000009', 'Laptop Stand - Aluminum', 'Office Furniture', 'FERT', 'EA', 59.99, 28.00, true),
    ('MAT000000000000010', 'Ergonomic Office Chair', 'Office Furniture', 'FERT', 'EA', 399.99, 220.00, true),
    ('MAT000000000000011', 'Standing Desk - Adjustable Height', 'Office Furniture', 'FERT', 'EA', 599.99, 350.00, true),
    ('MAT000000000000012', 'LED Desk Lamp - Dimmable', 'Office Furniture', 'FERT', 'EA', 79.99, 38.00, true),
    ('MAT000000000000013', 'Cable Management Kit', 'Electronics', 'FERT', 'EA', 24.99, 10.00, true),
    ('MAT000000000000014', 'External SSD - 1TB', 'Electronics', 'FERT', 'EA', 149.99, 80.00, true),
    ('MAT000000000000015', 'Graphics Tablet - Digital Drawing', 'Electronics', 'FERT', 'EA', 249.99, 140.00, true),
    ('MAT000000000000016', 'Portable Monitor - 15.6"', 'Electronics', 'FERT', 'EA', 199.99, 115.00, true),
    ('MAT000000000000017', 'Bluetooth Speaker - Portable', 'Electronics', 'FERT', 'EA', 69.99, 32.00, true),
    ('MAT000000000000018', 'Smartwatch - Fitness Tracking', 'Electronics', 'FERT', 'EA', 299.99, 165.00, true),
    ('MAT000000000000019', 'Wireless Earbuds - ANC', 'Electronics', 'FERT', 'EA', 179.99, 95.00, true),
    ('MAT000000000000020', 'Laptop Backpack - Water Resistant', 'Accessories', 'FERT', 'EA', 89.99, 42.00, true),
    ('MAT000000000000021', 'Monitor Arm - Dual Display', 'Office Furniture', 'FERT', 'EA', 129.99, 68.00, true),
    ('MAT000000000000022', 'Wireless Presenter - Laser Pointer', 'Electronics', 'FERT', 'EA', 49.99, 22.00, true),
    ('MAT000000000000023', 'Document Scanner - Portable', 'Electronics', 'FERT', 'EA', 199.99, 108.00, true),
    ('MAT000000000000024', 'Label Printer - Thermal', 'Electronics', 'FERT', 'EA', 149.99, 78.00, true),
    ('MAT000000000000025', 'Conference Camera - 4K', 'Electronics', 'FERT', 'EA', 399.99, 225.00, true),
    ('MAT000000000000026', 'Speakerphone - Omnidirectional', 'Electronics', 'FERT', 'EA', 149.99, 80.00, true),
    ('MAT000000000000027', 'Whiteboard - Magnetic Glass', 'Office Furniture', 'FERT', 'EA', 299.99, 165.00, true),
    ('MAT000000000000028', 'Desk Organizer Set', 'Office Furniture', 'FERT', 'EA', 49.99, 22.00, true),
    ('MAT000000000000029', 'Anti-Fatigue Mat - Standing Desk', 'Office Furniture', 'FERT', 'EA', 59.99, 28.00, true),
    ('MAT000000000000030', 'Monitor Privacy Screen - 24"', 'Accessories', 'FERT', 'EA', 69.99, 32.00, true),
    ('MAT000000000000031', 'KVM Switch - 2 Port', 'Electronics', 'FERT', 'EA', 79.99, 38.00, true),
    ('MAT000000000000032', 'UPS Battery Backup - 1500VA', 'Electronics', 'FERT', 'EA', 199.99, 115.00, true),
    ('MAT000000000000033', 'Network Switch - 8 Port Gigabit', 'Electronics', 'FERT', 'EA', 89.99, 48.00, true),
    ('MAT000000000000034', 'WiFi Router - Dual Band', 'Electronics', 'FERT', 'EA', 149.99, 82.00, true),
    ('MAT000000000000035', 'Surge Protector - 12 Outlet', 'Electronics', 'FERT', 'EA', 39.99, 18.00, true),
    ('MAT000000000000036', 'Desktop PC - Core i5', 'Electronics', 'FERT', 'EA', 899.99, 580.00, true),
    ('MAT000000000000037', 'All-in-One Printer - Laser', 'Electronics', 'FERT', 'EA', 349.99, 195.00, true),
    ('MAT000000000000038', 'Shredder - Cross Cut', 'Electronics', 'FERT', 'EA', 129.99, 68.00, true),
    ('MAT000000000000039', 'Laminator - Thermal', 'Electronics', 'FERT', 'EA', 89.99, 45.00, true),
    ('MAT000000000000040', 'Binding Machine - Comb', 'Electronics', 'FERT', 'EA', 99.99, 52.00, true),
    ('MAT000000000000041', 'File Cabinet - 4 Drawer', 'Office Furniture', 'FERT', 'EA', 299.99, 165.00, true),
    ('MAT000000000000042', 'Bookshelf - 5 Tier', 'Office Furniture', 'FERT', 'EA', 149.99, 82.00, true),
    ('MAT000000000000043', 'Meeting Table - Conference', 'Office Furniture', 'FERT', 'EA', 799.99, 450.00, true),
    ('MAT000000000000044', 'Guest Chairs - Set of 2', 'Office Furniture', 'FERT', 'EA', 249.99, 138.00, true),
    ('MAT000000000000045', 'Coat Rack - Standing', 'Office Furniture', 'FERT', 'EA', 79.99, 38.00, true),
    ('MAT000000000000046', 'Trash Can - Motion Sensor', 'Office Furniture', 'FERT', 'EA', 69.99, 32.00, true),
    ('MAT000000000000047', 'Air Purifier - HEPA Filter', 'Electronics', 'FERT', 'EA', 199.99, 110.00, true),
    ('MAT000000000000048', 'Humidifier - Ultrasonic', 'Electronics', 'FERT', 'EA', 89.99, 45.00, true),
    ('MAT000000000000049', 'Coffee Maker - Programmable', 'Electronics', 'FERT', 'EA', 129.99, 68.00, true),
    ('MAT000000000000050', 'Water Cooler - Hot & Cold', 'Electronics', 'FERT', 'EA', 299.99, 165.00, true);

-- ============================================================================
-- POPULATE: Sales Orders (5,000 orders over 3 years)
-- ============================================================================
INSERT INTO supply_chain.sales_orders (order_number, customer_id, order_date, posting_date, delivery_date, order_status, sales_organization, distribution_channel, division, currency)
SELECT
    'ORD' || LPAD(i::TEXT, 7, '0') AS order_number,
    LPAD((1 + (i % 500))::TEXT, 10, '0') AS customer_id,
    (DATE '2022-01-01' + ((i * 0.2)::INT || ' days')::INTERVAL)::DATE AS order_date,
    (DATE '2022-01-01' + ((i * 0.2 + 2)::INT || ' days')::INTERVAL)::DATE AS posting_date,
    (DATE '2022-01-01' + ((i * 0.2 + 7)::INT || ' days')::INTERVAL)::DATE AS delivery_date,
    CASE
        WHEN i % 20 = 0 THEN 'Cancelled'
        WHEN i % 15 = 0 THEN 'In Progress'
        WHEN i % 10 = 0 THEN 'Open'
        ELSE 'Delivered'
    END AS order_status,
    CASE
        WHEN (i % 500) % 15 IN (0,5,10) THEN 'SO_AMERICAS'
        WHEN (i % 500) % 15 IN (1,2,3,14) THEN 'SO_EMEA'
        ELSE 'SO_APAC'
    END AS sales_organization,
    CASE
        WHEN i % 3 = 0 THEN 'Direct Sales'
        WHEN i % 3 = 1 THEN 'Partner Channel'
        ELSE 'Online Store'
    END AS distribution_channel,
    CASE
        WHEN i % 2 = 0 THEN 'DIV_ELECTRONICS'
        ELSE 'DIV_FURNITURE'
    END AS division,
    'USD' AS currency
FROM generate_series(1, 5000) AS i;

-- ============================================================================
-- POPULATE: Order Items (10,000+ line items, 2-3 items per order average)
-- ============================================================================
INSERT INTO supply_chain.order_items (
    order_number, line_item_number, customer_id, material_number, posting_date,
    quantity, unit_of_measure, gross_revenue, net_sales, discounts, cogs, gross_margin, contribution_margin
)
SELECT
    'ORD' || LPAD(order_num::TEXT, 7, '0') AS order_number,
    line_num AS line_item_number,
    LPAD((1 + (order_num % 500))::TEXT, 10, '0') AS customer_id,
    'MAT' || LPAD((1 + (random() * 49)::INT)::TEXT, 18, '0') AS material_number,
    (DATE '2022-01-01' + ((order_num * 0.2 + 2)::INT || ' days')::INTERVAL)::DATE AS posting_date,
    (1 + (random() * 10)::INT)::DECIMAL(15,3) AS quantity,
    'EA' AS unit_of_measure,
    (50 + (random() * 1000))::DECIMAL(15,2) AS gross_revenue,
    (45 + (random() * 900))::DECIMAL(15,2) AS net_sales,
    (5 + (random() * 100))::DECIMAL(15,2) AS discounts,
    (30 + (random() * 600))::DECIMAL(15,2) AS cogs,
    (15 + (random() * 300))::DECIMAL(15,2) AS gross_margin,
    (10 + (random() * 200))::DECIMAL(15,2) AS contribution_margin
FROM
    generate_series(1, 5000) AS order_num,
    generate_series(1, 1 + ((random() * 2)::INT)) AS line_num;

-- Update calculated fields for consistency
UPDATE supply_chain.order_items
SET
    net_sales = gross_revenue - discounts,
    gross_margin = (gross_revenue - discounts) - cogs,
    contribution_margin = ((gross_revenue - discounts) - cogs) * 0.85;

-- ============================================================================
-- CREATE VIEWS for common analytics queries
-- ============================================================================

-- View: Customer Revenue Summary
CREATE OR REPLACE VIEW supply_chain.v_customer_revenue AS
SELECT
    c.customer_id,
    c.customer_name,
    c.country,
    c.region,
    c.abc_class,
    c.rfm_segment,
    COUNT(DISTINCT o.order_number) AS total_orders,
    SUM(oi.quantity) AS total_quantity,
    SUM(oi.gross_revenue) AS total_gross_revenue,
    SUM(oi.net_sales) AS total_net_sales,
    SUM(oi.gross_margin) AS total_gross_margin,
    AVG(oi.gross_margin / NULLIF(oi.net_sales, 0)) * 100 AS avg_margin_pct
FROM supply_chain.customers c
LEFT JOIN supply_chain.order_items oi ON c.customer_id = oi.customer_id
LEFT JOIN supply_chain.sales_orders o ON oi.order_number = o.order_number
WHERE o.order_status != 'Cancelled'
GROUP BY c.customer_id, c.customer_name, c.country, c.region, c.abc_class, c.rfm_segment;

-- View: Material Performance
CREATE OR REPLACE VIEW supply_chain.v_material_performance AS
SELECT
    m.material_number,
    m.material_description,
    m.material_group,
    COUNT(DISTINCT oi.order_number) AS orders_count,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.net_sales) AS total_revenue,
    SUM(oi.gross_margin) AS total_margin,
    AVG(oi.gross_margin / NULLIF(oi.net_sales, 0)) * 100 AS avg_margin_pct
FROM supply_chain.materials m
LEFT JOIN supply_chain.order_items oi ON m.material_number = oi.material_number
GROUP BY m.material_number, m.material_description, m.material_group;

-- View: Monthly Sales Trends
CREATE OR REPLACE VIEW supply_chain.v_monthly_sales AS
SELECT
    DATE_TRUNC('month', posting_date) AS month,
    COUNT(DISTINCT order_number) AS order_count,
    SUM(quantity) AS total_quantity,
    SUM(gross_revenue) AS total_gross_revenue,
    SUM(net_sales) AS total_net_sales,
    SUM(gross_margin) AS total_gross_margin,
    AVG(gross_margin / NULLIF(net_sales, 0)) * 100 AS avg_margin_pct
FROM supply_chain.order_items
GROUP BY DATE_TRUNC('month', posting_date)
ORDER BY month;

-- ============================================================================
-- GRANT permissions
-- ============================================================================
GRANT USAGE ON SCHEMA supply_chain TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA supply_chain TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA supply_chain TO PUBLIC;

-- ============================================================================
-- Analytics: Quick stats query
-- ============================================================================
DO $$
DECLARE
    customer_count INT;
    material_count INT;
    order_count INT;
    line_item_count INT;
    date_range TEXT;
BEGIN
    SELECT COUNT(*) INTO customer_count FROM supply_chain.customers;
    SELECT COUNT(*) INTO material_count FROM supply_chain.materials;
    SELECT COUNT(*) INTO order_count FROM supply_chain.sales_orders;
    SELECT COUNT(*) INTO line_item_count FROM supply_chain.order_items;
    SELECT MIN(posting_date)::TEXT || ' to ' || MAX(posting_date)::TEXT
        INTO date_range FROM supply_chain.order_items;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'SAP Supply Chain Test Database Loaded';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Customers: %', customer_count;
    RAISE NOTICE 'Materials: %', material_count;
    RAISE NOTICE 'Orders: %', order_count;
    RAISE NOTICE 'Line Items: %', line_item_count;
    RAISE NOTICE 'Date Range: %', date_range;
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Ready for connector testing!';
    RAISE NOTICE '========================================';
END $$;
