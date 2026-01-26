-- Property Ownership Database Schema
-- SQLite database for storing property ownership data from CSV

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_number TEXT NOT NULL,
    tenure TEXT,
    property_address TEXT NOT NULL,
    district TEXT,
    county TEXT,
    region TEXT,
    postcode TEXT,
    multiple_address_indicator TEXT,
    price_paid TEXT,
    date_proprietor_added TEXT,
    additional_proprietor_indicator TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title_number)
);

CREATE TABLE IF NOT EXISTS proprietors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    proprietor_number INTEGER NOT NULL, -- 1, 2, 3, or 4
    proprietor_name TEXT,
    company_registration_no TEXT,
    proprietorship_category TEXT,
    address_line_1 TEXT,
    address_line_2 TEXT,
    address_line_3 TEXT,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    UNIQUE(property_id, proprietor_number)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_company_registration_no ON proprietors(company_registration_no);
CREATE INDEX IF NOT EXISTS idx_property_id ON proprietors(property_id);
CREATE INDEX IF NOT EXISTS idx_title_number ON properties(title_number);
CREATE INDEX IF NOT EXISTS idx_postcode ON properties(postcode);

-- Payments table for tracking Stripe transactions
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_session_id TEXT UNIQUE NOT NULL,
    search_type TEXT NOT NULL,
    search_value TEXT NOT NULL,
    amount_pence INTEGER NOT NULL,
    currency TEXT DEFAULT 'gbp',
    status TEXT DEFAULT 'pending',
    customer_email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    used_at TIMESTAMP
);

-- Index for fast payment lookup by session ID
CREATE INDEX IF NOT EXISTS idx_stripe_session_id ON payments(stripe_session_id);
CREATE INDEX IF NOT EXISTS idx_payment_status ON payments(status);

