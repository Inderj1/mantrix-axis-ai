-- Test PostgreSQL Database Initialization
-- Creates sample tables for testing the full NLP-to-SQL pipeline

-- Create schema
CREATE SCHEMA IF NOT EXISTS sales;

-- Sales table
CREATE TABLE sales.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customers table
CREATE TABLE sales.customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    city VARCHAR(100),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE sales.products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    unit_price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order items table
CREATE TABLE sales.order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES sales.orders(order_id),
    product_id INTEGER REFERENCES sales.products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL
);

-- Insert sample customers
INSERT INTO sales.customers (customer_name, email, city, country) VALUES
('John Doe', 'john@example.com', 'New York', 'USA'),
('Jane Smith', 'jane@example.com', 'London', 'UK'),
('Bob Johnson', 'bob@example.com', 'Toronto', 'Canada'),
('Alice Williams', 'alice@example.com', 'Sydney', 'Australia'),
('Charlie Brown', 'charlie@example.com', 'Berlin', 'Germany'),
('Diana Prince', 'diana@example.com', 'Tokyo', 'Japan'),
('Eve Davis', 'eve@example.com', 'Paris', 'France'),
('Frank Miller', 'frank@example.com', 'Mumbai', 'India'),
('Grace Lee', 'grace@example.com', 'Singapore', 'Singapore'),
('Henry Wilson', 'henry@example.com', 'Dubai', 'UAE');

-- Insert sample products
INSERT INTO sales.products (product_name, category, unit_price, stock_quantity) VALUES
('Laptop Pro', 'Electronics', 1299.99, 50),
('Wireless Mouse', 'Electronics', 29.99, 200),
('Office Chair', 'Furniture', 299.99, 30),
('Standing Desk', 'Furniture', 599.99, 20),
('USB-C Cable', 'Electronics', 19.99, 500),
('Monitor 27"', 'Electronics', 399.99, 40),
('Keyboard Mechanical', 'Electronics', 149.99, 75),
('Desk Lamp', 'Furniture', 79.99, 100),
('Webcam HD', 'Electronics', 89.99, 60),
('Headphones', 'Electronics', 199.99, 80);

-- Insert sample orders
INSERT INTO sales.orders (customer_id, order_date, total_amount, status) VALUES
(1, CURRENT_DATE - INTERVAL '1 day', 1329.98, 'completed'),
(2, CURRENT_DATE - INTERVAL '2 days', 299.99, 'completed'),
(3, CURRENT_DATE - INTERVAL '3 days', 699.98, 'pending'),
(4, CURRENT_DATE - INTERVAL '4 days', 1949.96, 'completed'),
(5, CURRENT_DATE - INTERVAL '5 days', 479.97, 'shipped'),
(6, CURRENT_DATE - INTERVAL '6 days', 229.98, 'completed'),
(7, CURRENT_DATE - INTERVAL '7 days', 1899.97, 'completed'),
(1, CURRENT_DATE - INTERVAL '8 days', 149.99, 'completed'),
(2, CURRENT_DATE - INTERVAL '9 days', 89.99, 'completed'),
(3, CURRENT_DATE - INTERVAL '10 days', 599.99, 'completed');

-- Insert sample order items
INSERT INTO sales.order_items (order_id, product_id, quantity, unit_price, total_price) VALUES
(1, 1, 1, 1299.99, 1299.99),
(1, 2, 1, 29.99, 29.99),
(2, 3, 1, 299.99, 299.99),
(3, 4, 1, 599.99, 599.99),
(3, 8, 1, 99.99, 99.99),
(4, 1, 1, 1299.99, 1299.99),
(4, 6, 1, 399.99, 399.99),
(4, 2, 1, 29.99, 29.99),
(4, 5, 1, 19.99, 19.99),
(4, 9, 2, 89.99, 179.98),
(5, 7, 3, 149.99, 449.97),
(5, 2, 1, 29.99, 29.99),
(6, 10, 1, 199.99, 199.99),
(6, 2, 1, 29.99, 29.99),
(7, 1, 1, 1299.99, 1299.99),
(7, 4, 1, 599.99, 599.99),
(8, 7, 1, 149.99, 149.99),
(9, 9, 1, 89.99, 89.99),
(10, 4, 1, 599.99, 599.99);

-- Create indexes for performance
CREATE INDEX idx_orders_customer_id ON sales.orders(customer_id);
CREATE INDEX idx_orders_order_date ON sales.orders(order_date);
CREATE INDEX idx_order_items_order_id ON sales.order_items(order_id);
CREATE INDEX idx_order_items_product_id ON sales.order_items(product_id);

-- Add comments for documentation
COMMENT ON TABLE sales.orders IS 'Customer orders with order date, amount, and status';
COMMENT ON TABLE sales.customers IS 'Customer information including contact details';
COMMENT ON TABLE sales.products IS 'Product catalog with pricing and inventory';
COMMENT ON TABLE sales.order_items IS 'Order line items linking orders to products';

COMMENT ON COLUMN sales.orders.order_date IS 'Date when the order was placed';
COMMENT ON COLUMN sales.orders.total_amount IS 'Total order amount in USD';
COMMENT ON COLUMN sales.orders.status IS 'Order status: pending, shipped, completed, cancelled';
COMMENT ON COLUMN sales.customers.customer_name IS 'Full name of the customer';
COMMENT ON COLUMN sales.products.unit_price IS 'Product price per unit in USD';
COMMENT ON COLUMN sales.products.stock_quantity IS 'Current inventory level';

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA sales TO test_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA sales TO test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA sales TO test_user;

-- Verify data
SELECT 'Database initialized successfully!' as status;
SELECT 'Customers: ' || COUNT(*) as info FROM sales.customers;
SELECT 'Products: ' || COUNT(*) as info FROM sales.products;
SELECT 'Orders: ' || COUNT(*) as info FROM sales.orders;
SELECT 'Order Items: ' || COUNT(*) as info FROM sales.order_items;
