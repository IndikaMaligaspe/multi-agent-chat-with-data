-- Insert categories
INSERT INTO categories (name, description) VALUES
('Electronics', 'Electronic devices and accessories'),
('Clothing', 'Apparel and fashion items'),
('Books', 'Physical and digital books'),
('Home & Garden', 'Home improvement and garden supplies'),
('Sports', 'Sports equipment and fitness gear');

-- Insert products
INSERT INTO products (name, category_id, price, cost, stock_quantity) VALUES
-- Electronics
('Wireless Headphones', 1, 99.99, 45.00, 150),
('Smart Watch', 1, 249.99, 120.00, 80),
('USB-C Cable', 1, 12.99, 3.50, 500),
('Laptop Stand', 1, 49.99, 20.00, 200),
('Bluetooth Speaker', 1, 79.99, 35.00, 120),

-- Clothing
('Cotton T-Shirt', 2, 19.99, 8.00, 300),
('Denim Jeans', 2, 59.99, 25.00, 150),
('Running Shoes', 2, 89.99, 40.00, 100),
('Winter Jacket', 2, 129.99, 60.00, 80),
('Baseball Cap', 2, 24.99, 10.00, 200),

-- Books
('Programming in Python', 3, 39.99, 15.00, 100),
('The Art of War', 3, 14.99, 5.00, 150),
('Cooking Masterclass', 3, 29.99, 12.00, 80),

-- Home & Garden
('Garden Hose', 4, 34.99, 15.00, 100),
('Tool Set', 4, 79.99, 35.00, 60),
('LED Lamp', 4, 44.99, 18.00, 120),

-- Sports
('Yoga Mat', 5, 29.99, 12.00, 150),
('Dumbbell Set', 5, 119.99, 55.00, 50),
('Tennis Racket', 5, 89.99, 40.00, 70);

-- Insert customers with variety
INSERT INTO customers (name, email, country, state, city, registration_date, customer_segment, lifetime_value) VALUES
-- USA customers
('John Doe', 'john.doe@email.com', 'USA', 'California', 'Los Angeles', '2023-01-15', 'Premium', 2500.00),
('Jane Smith', 'jane.smith@email.com', 'USA', 'New York', 'New York', '2023-02-20', 'Regular', 800.00),
('Bob Johnson', 'bob.j@email.com', 'USA', 'Texas', 'Houston', '2023-03-10', 'Budget', 300.00),
('Alice Williams', 'alice.w@email.com', 'USA', 'Florida', 'Miami', '2023-04-05', 'Premium', 3200.00),
('Charlie Brown', 'charlie.b@email.com', 'USA', 'Illinois', 'Chicago', '2023-05-12', 'Regular', 1100.00),

-- UK customers
('Emma Wilson', 'emma.w@email.com', 'UK', 'England', 'London', '2023-02-01', 'Premium', 1800.00),
('Oliver Taylor', 'oliver.t@email.com', 'UK', 'Scotland', 'Edinburgh', '2023-03-15', 'Regular', 650.00),
('Sophie Anderson', 'sophie.a@email.com', 'UK', 'Wales', 'Cardiff', '2023-06-20', 'Budget', 200.00),

-- Canada customers
('Liam Martin', 'liam.m@email.com', 'Canada', 'Ontario', 'Toronto', '2023-01-25', 'Premium', 2100.00),
('Olivia Garcia', 'olivia.g@email.com', 'Canada', 'Quebec', 'Montreal', '2023-04-18', 'Regular', 900.00),

-- Germany customers
('Noah Mueller', 'noah.m@email.com', 'Germany', 'Bavaria', 'Munich', '2023-03-05', 'Premium', 1500.00),
('Mia Schmidt', 'mia.s@email.com', 'Germany', 'Berlin', 'Berlin', '2023-05-30', 'Regular', 700.00),

-- Australia customers
('Lucas Roberts', 'lucas.r@email.com', 'Australia', 'NSW', 'Sydney', '2023-02-10', 'Premium', 1900.00),
('Ava Thompson', 'ava.t@email.com', 'Australia', 'Victoria', 'Melbourne', '2023-06-15', 'Budget', 350.00),

-- France customers
('Ethan Dubois', 'ethan.d@email.com', 'France', 'Ile-de-France', 'Paris', '2023-01-30', 'Regular', 950.00);

-- Insert orders (spread across 2024)
-- January 2024
INSERT INTO orders (customer_id, order_date, status, total_amount, shipping_cost, tax_amount, discount_amount, payment_method, completed_at) VALUES
(1, '2024-01-05', 'completed', 349.97, 10.00, 28.00, 0.00, 'credit_card', '2024-01-07 14:30:00'),
(2, '2024-01-08', 'completed', 129.98, 5.00, 10.40, 15.00, 'paypal', '2024-01-10 09:15:00'),
(3, '2024-01-12', 'completed', 59.99, 5.00, 4.80, 0.00, 'credit_card', '2024-01-14 16:20:00'),

-- February 2024
(4, '2024-02-03', 'completed', 479.95, 15.00, 38.40, 25.00, 'credit_card', '2024-02-05 11:45:00'),
(5, '2024-02-07', 'completed', 169.98, 7.00, 13.60, 0.00, 'bank_transfer', '2024-02-09 10:30:00'),
(6, '2024-02-14', 'completed', 299.97, 12.00, 24.00, 30.00, 'credit_card', '2024-02-16 15:00:00'),
(7, '2024-02-20', 'cancelled', 89.99, 5.00, 7.20, 0.00, 'paypal', NULL),

-- March 2024
(8, '2024-03-01', 'completed', 44.98, 5.00, 3.60, 0.00, 'credit_card', '2024-03-03 13:20:00'),
(9, '2024-03-10', 'completed', 549.95, 20.00, 44.00, 50.00, 'credit_card', '2024-03-12 09:45:00'),
(10, '2024-03-15', 'completed', 199.98, 8.00, 16.00, 20.00, 'paypal', '2024-03-17 14:10:00'),
(11, '2024-03-22', 'completed', 329.97, 10.00, 26.40, 0.00, 'credit_card', '2024-03-24 11:30:00'),

-- April 2024
(12, '2024-04-02', 'completed', 279.98, 12.00, 22.40, 25.00, 'credit_card', '2024-04-04 10:15:00'),
(1, '2024-04-08', 'completed', 449.96, 15.00, 36.00, 40.00, 'credit_card', '2024-04-10 15:30:00'),
(13, '2024-04-12', 'completed', 389.95, 15.00, 31.20, 35.00, 'paypal', '2024-04-14 09:00:00'),
(14, '2024-04-18', 'pending', 129.99, 7.00, 10.40, 0.00, 'credit_card', NULL),

-- May 2024
(2, '2024-05-03', 'completed', 199.98, 8.00, 16.00, 0.00, 'paypal', '2024-05-05 14:20:00'),
(15, '2024-05-10', 'completed', 259.97, 10.00, 20.80, 20.00, 'credit_card', '2024-05-12 11:45:00'),
(4, '2024-05-15', 'completed', 679.94, 25.00, 54.40, 60.00, 'credit_card', '2024-05-17 10:30:00'),
(6, '2024-05-22', 'refunded', 149.99, 7.00, 12.00, 0.00, 'paypal', '2024-05-24 09:15:00'),
(7, '2024-05-28', 'completed', 329.97, 12.00, 26.40, 30.00, 'credit_card', '2024-05-30 16:00:00'),

-- June 2024
(9, '2024-06-05', 'completed', 499.95, 18.00, 40.00, 45.00, 'credit_card', '2024-06-07 13:30:00'),
(10, '2024-06-12', 'completed', 179.98, 8.00, 14.40, 0.00, 'bank_transfer', '2024-06-14 10:45:00'),
(11, '2024-06-18', 'pending', 229.98, 10.00, 18.40, 0.00, 'credit_card', NULL),
(3, '2024-06-25', 'completed', 119.99, 6.00, 9.60, 10.00, 'paypal', '2024-06-27 15:20:00');

-- Insert order_items (line items for each order)
-- Order 1 (customer 1, Jan 5)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(1, 2, 1, 249.99, 0.00, 249.99),  -- Smart Watch
(1, 1, 1, 99.99, 0.00, 99.99);     -- Wireless Headphones

-- Order 2 (customer 2, Jan 8)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(2, 7, 2, 59.99, 10.00, 107.98),   -- Denim Jeans x2 with 10% discount
(2, 6, 1, 19.99, 10.00, 17.99);    -- T-Shirt with 10% discount

-- Order 3 (customer 3, Jan 12)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(3, 7, 1, 59.99, 0.00, 59.99);     -- Denim Jeans

-- Order 4 (customer 4, Feb 3)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(4, 9, 1, 129.99, 0.00, 129.99),   -- Winter Jacket
(4, 2, 1, 249.99, 0.00, 249.99),   -- Smart Watch
(4, 1, 1, 99.99, 0.00, 99.99);     -- Wireless Headphones

-- Order 5 (customer 5, Feb 7)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(5, 8, 2, 89.99, 5.00, 170.98);    -- Running Shoes x2 with 5% discount

-- Order 6 (customer 6, Feb 14)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(6, 2, 1, 249.99, 10.00, 224.99),  -- Smart Watch with 10% discount
(6, 18, 1, 89.99, 10.00, 80.99);   -- Dumbbell Set with 10% discount

-- Order 7 (customer 7, Feb 20 - CANCELLED)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(7, 8, 1, 89.99, 0.00, 89.99);     -- Running Shoes

-- Order 8 (customer 8, Mar 1)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(8, 10, 1, 24.99, 0.00, 24.99),    -- Baseball Cap
(8, 6, 1, 19.99, 0.00, 19.99);     -- T-Shirt

-- Order 9 (customer 9, Mar 10)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(9, 2, 2, 249.99, 10.00, 449.98),  -- Smart Watch x2 with 10% discount
(9, 1, 1, 99.99, 0.00, 99.99);     -- Wireless Headphones

-- Order 10 (customer 10, Mar 15)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(10, 9, 1, 129.99, 10.00, 116.99), -- Winter Jacket with 10% discount
(10, 8, 1, 89.99, 10.00, 80.99);   -- Running Shoes with 10% discount

-- Continue for remaining orders (11-24)...
-- Order 11
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(11, 2, 1, 249.99, 0.00, 249.99),
(11, 5, 1, 79.99, 0.00, 79.99);

-- Order 12
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(12, 7, 2, 59.99, 10.00, 107.98),
(12, 9, 1, 129.99, 10.00, 116.99);

-- Order 13
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(13, 1, 2, 99.99, 10.00, 179.98),
(13, 2, 1, 249.99, 10.00, 224.99);

-- Order 14 (PENDING)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(14, 9, 1, 129.99, 0.00, 129.99);

-- Order 15
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(15, 1, 2, 99.99, 0.00, 199.98);

-- Order 16
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(16, 6, 3, 19.99, 0.00, 59.97),
(16, 7, 2, 59.99, 0.00, 119.98),
(16, 8, 1, 89.99, 0.00, 89.99);

-- Order 17
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(17, 2, 2, 249.99, 10.00, 449.98),
(17, 18, 1, 119.99, 10.00, 107.99);

-- Order 18 (REFUNDED)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(18, 9, 1, 129.99, 0.00, 129.99),
(18, 6, 1, 19.99, 0.00, 19.99);

-- Order 19
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(19, 2, 1, 249.99, 0.00, 249.99),
(19, 5, 1, 79.99, 0.00, 79.99);

-- Order 20
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(20, 1, 3, 99.99, 10.00, 269.97),
(20, 18, 1, 119.99, 10.00, 107.99);

-- Order 21
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(21, 8, 2, 89.99, 0.00, 179.98);

-- Order 22 (PENDING)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(22, 7, 2, 59.99, 0.00, 119.98),
(22, 9, 1, 129.99, 0.00, 129.99);

-- Order 23
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, subtotal) VALUES
(23, 6, 5, 19.99, 10.00, 89.96),
(23, 10, 3, 24.99, 10.00, 67.47);

-- Update customer lifetime values based on completed orders
UPDATE customers c
SET lifetime_value = (
    SELECT COALESCE(SUM(o.total_amount), 0)
    FROM orders o
    WHERE o.customer_id = c.id
    AND o.status = 'completed'
);