-- ============================================================================
-- NovaTech Enterprise Synthetic Sales Database Seed Script
-- Description : PostgreSQL script to create and populate the 'sales' table.
-- Date Range  : Q1 & Q2 2026 (Jan 2026 - Jun 2026)
-- Company     : NovaTech
-- ============================================================================

CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY NOT NULL,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    sale_date DATE NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    product_category VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    revenue NUMERIC(12, 2) NOT NULL CHECK (revenue >= 0),
    payment_status VARCHAR(20) DEFAULT 'Completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optional cleanup before insert (uncomment if re-running in fresh environment)
-- TRUNCATE TABLE sales RESTART IDENTITY;

INSERT INTO sales (transaction_id, sale_date, product_name, product_category, region, customer_name, quantity, unit_price, revenue, payment_status)
VALUES
    ('TXN-2026-001', '2026-01-07', 'NovaAnalytics Suite', 'Data & Analytics', 'North America', 'Velocity Retail Solutions', 4, 6500.00, 26000.00, 'Pending'),
    ('TXN-2026-002', '2026-01-16', 'NovaSync Hub', 'Integration & Middleware', 'LATAM', 'Nexus Telecom', 10, 3200.00, 32000.00, 'Pending'),
    ('TXN-2026-003', '2026-01-18', 'NovaCloud Enterprise', 'Cloud Infrastructure', 'North America', 'Vortex Dynamics', 5, 12000.00, 60000.00, 'Completed'),
    ('TXN-2026-004', '2026-01-25', 'NovaCloud Enterprise', 'Cloud Infrastructure', 'LATAM', 'OmniCorp International', 6, 12000.00, 72000.00, 'Completed'),
    ('TXN-2026-005', '2026-01-30', 'NovaAnalytics Suite', 'Data & Analytics', 'APAC', 'Velocity Retail Solutions', 6, 6500.00, 39000.00, 'Pending'),
    ('TXN-2026-006', '2026-02-05', 'NovaData Warehouse', 'Database Services', 'North America', 'Atlas Robotics', 6, 9800.00, 58800.00, 'Completed'),
    ('TXN-2026-007', '2026-02-10', 'NovaSync Hub', 'Integration & Middleware', 'APAC', 'Horizon Healthcare', 8, 3200.00, 25600.00, 'Completed'),
    ('TXN-2026-008', '2026-02-15', 'NovaAnalytics Suite', 'Data & Analytics', 'North America', 'Borealis Pharma', 6, 6500.00, 39000.00, 'Completed'),
    ('TXN-2026-009', '2026-02-19', 'NovaSecurity Shield', 'Cybersecurity', 'North America', 'Starlight Media Group', 10, 4500.00, 45000.00, 'Pending'),
    ('TXN-2026-010', '2026-02-21', 'NovaSecurity Shield', 'Cybersecurity', 'LATAM', 'Starlight Media Group', 9, 4500.00, 40500.00, 'Completed'),
    ('TXN-2026-011', '2026-03-01', 'NovaSync Hub', 'Integration & Middleware', 'LATAM', 'AeroSpace Tech Inc', 9, 3200.00, 28800.00, 'Completed'),
    ('TXN-2026-012', '2026-03-07', 'NovaAI Assistant Platform', 'Artificial Intelligence', 'EMEA', 'Borealis Pharma', 1, 8500.00, 8500.00, 'Completed'),
    ('TXN-2026-013', '2026-03-12', 'NovaSecurity Shield', 'Cybersecurity', 'LATAM', 'Quantum Logistics', 8, 4500.00, 36000.00, 'Completed'),
    ('TXN-2026-014', '2026-03-13', 'NovaData Warehouse', 'Database Services', 'LATAM', 'OmniCorp International', 8, 9800.00, 78400.00, 'Completed'),
    ('TXN-2026-015', '2026-03-22', 'NovaSecurity Shield', 'Cybersecurity', 'APAC', 'AeroSpace Tech Inc', 9, 4500.00, 40500.00, 'Pending'),
    ('TXN-2026-016', '2026-03-26', 'NovaSecurity Shield', 'Cybersecurity', 'EMEA', 'Horizon Healthcare', 5, 4500.00, 22500.00, 'Completed'),
    ('TXN-2026-017', '2026-03-28', 'NovaAI Assistant Platform', 'Artificial Intelligence', 'LATAM', 'Nexus Telecom', 9, 8500.00, 76500.00, 'Pending'),
    ('TXN-2026-018', '2026-04-04', 'NovaAI Assistant Platform', 'Artificial Intelligence', 'APAC', 'Atlas Robotics', 8, 8500.00, 68000.00, 'Pending'),
    ('TXN-2026-019', '2026-04-11', 'NovaSecurity Shield', 'Cybersecurity', 'LATAM', 'AeroSpace Tech Inc', 1, 4500.00, 4500.00, 'Completed'),
    ('TXN-2026-020', '2026-04-14', 'NovaSecurity Shield', 'Cybersecurity', 'North America', 'Echo Energy Corp', 9, 4500.00, 40500.00, 'Completed'),
    ('TXN-2026-021', '2026-04-20', 'NovaAI Assistant Platform', 'Artificial Intelligence', 'LATAM', 'Borealis Pharma', 8, 8500.00, 68000.00, 'Completed'),
    ('TXN-2026-022', '2026-04-24', 'NovaSecurity Shield', 'Cybersecurity', 'APAC', 'Vortex Dynamics', 4, 4500.00, 18000.00, 'Pending'),
    ('TXN-2026-023', '2026-04-28', 'NovaSecurity Shield', 'Cybersecurity', 'North America', 'Vortex Dynamics', 1, 4500.00, 4500.00, 'Pending'),
    ('TXN-2026-024', '2026-05-06', 'NovaSync Hub', 'Integration & Middleware', 'North America', 'Crestview Capital', 4, 3200.00, 12800.00, 'Completed'),
    ('TXN-2026-025', '2026-05-07', 'NovaSync Hub', 'Integration & Middleware', 'North America', 'Nexus Telecom', 9, 3200.00, 28800.00, 'Completed'),
    ('TXN-2026-026', '2026-05-14', 'NovaAI Assistant Platform', 'Artificial Intelligence', 'North America', 'Pinnacle Systems', 10, 8500.00, 85000.00, 'Pending'),
    ('TXN-2026-027', '2026-05-18', 'NovaSync Hub', 'Integration & Middleware', 'EMEA', 'Echo Energy Corp', 10, 3200.00, 32000.00, 'Completed'),
    ('TXN-2026-028', '2026-05-26', 'NovaData Warehouse', 'Database Services', 'APAC', 'Vortex Dynamics', 7, 9800.00, 68600.00, 'Completed'),
    ('TXN-2026-029', '2026-05-28', 'NovaSync Hub', 'Integration & Middleware', 'APAC', 'AeroSpace Tech Inc', 7, 3200.00, 22400.00, 'Pending'),
    ('TXN-2026-030', '2026-06-02', 'NovaSync Hub', 'Integration & Middleware', 'EMEA', 'Starlight Media Group', 1, 3200.00, 3200.00, 'Completed'),
    ('TXN-2026-031', '2026-06-09', 'NovaCloud Enterprise', 'Cloud Infrastructure', 'North America', 'Borealis Pharma', 6, 12000.00, 72000.00, 'Completed'),
    ('TXN-2026-032', '2026-06-11', 'NovaCloud Enterprise', 'Cloud Infrastructure', 'LATAM', 'Pinnacle Systems', 5, 12000.00, 60000.00, 'Pending'),
    ('TXN-2026-033', '2026-06-18', 'NovaCloud Enterprise', 'Cloud Infrastructure', 'LATAM', 'Echo Energy Corp', 10, 12000.00, 120000.00, 'Completed'),
    ('TXN-2026-034', '2026-06-22', 'NovaSync Hub', 'Integration & Middleware', 'EMEA', 'Starlight Media Group', 10, 3200.00, 32000.00, 'Completed'),
    ('TXN-2026-035', '2026-06-28', 'NovaSync Hub', 'Integration & Middleware', 'EMEA', 'OmniCorp International', 2, 3200.00, 6400.00, 'Pending'),
    ('TXN-2026-036', '2026-01-10', 'NovaCloud Enterprise', 'Cloud Infrastructure', 'North America', 'Vortex Dynamics', 7, 12000.00, 84000.00, 'Completed');

