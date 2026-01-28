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

-- ============================================
-- USER ACCOUNT SYSTEM TABLES
-- ============================================

-- Users table for authentication and credits
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULL if magic link only user
    credits INTEGER DEFAULT 10,  -- 10 free credits on signup
    is_unlimited BOOLEAN DEFAULT FALSE,  -- TRUE for friends/family with unlimited access
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Magic links for passwordless authentication
CREATE TABLE IF NOT EXISTS magic_links (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP
);

-- Credit transaction history for audit trail
CREATE TABLE IF NOT EXISTS credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,  -- positive = added, negative = used
    transaction_type VARCHAR(50) NOT NULL,  -- 'signup_bonus', 'search_used', 'purchase'
    search_type VARCHAR(50),  -- for search_used transactions: 'name', 'number', 'address', 'director'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP
);

-- Indexes for user system
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_magic_links_token ON magic_links(token);
CREATE INDEX IF NOT EXISTS idx_magic_links_user_id ON magic_links(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token);

-- ============================================
-- PERFORMANCE OPTIMIZATION: Normalized Columns & Indexes (PostgreSQL only)
-- ============================================
-- These columns and indexes are added by scripts/migrate_add_indexes.py
-- They enable fast indexed searches instead of full table scans.
--
-- Normalized columns (added to existing tables):
--   proprietors.company_reg_normalized - uppercase, no spaces/hyphens/parentheses (indexed)
--   proprietors.proprietor_name_upper - uppercase trimmed name (trigram indexed)
--   properties.property_address_upper - uppercase trimmed address (trigram indexed)
--   properties.postcode_upper - uppercase trimmed postcode (trigram indexed)
--
-- Indexes created:
--   idx_company_reg_normalized - B-tree index for exact company number matches
--   idx_proprietor_name_trgm - GIN trigram index for LIKE '%term%' queries on names
--   idx_property_address_trgm - GIN trigram index for LIKE '%term%' queries on addresses
--   idx_postcode_trgm - GIN trigram index for LIKE '%term%' queries on postcodes
--
-- Performance improvements:
--   - Company number search: ~100x faster (index lookup vs full table scan)
--   - Company name search: ~10-50x faster (trigram index enables LIKE queries)
--   - Address search: ~10-50x faster (trigram index enables LIKE queries)
--
-- Note: Requires pg_trgm extension: CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- See scripts/migrate_add_indexes.py for migration script.

