"""
Migrate database to add public API v1 tables.

Adds:
  - users.api_credits: separate prepaid balance used by API requests
                       (independent of the web-UI credits pool)
  - api_keys: developer-owned bearer credentials
  - api_credit_transactions: ledger for top-ups and debits
  - api_request_logs: per-request audit + usage metering
  - api_rate_counters: sliding-window rate-limit counters

Usage: DATABASE_URL=postgres://... python scripts/migrate_api.py
"""
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()
load_dotenv("env.local")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not set")
    raise SystemExit(1)

print("Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("Adding api_credits column to users...")
cursor.execute(
    """
    ALTER TABLE users
      ADD COLUMN IF NOT EXISTS api_credits INTEGER NOT NULL DEFAULT 0
    """
)

print("Creating api_keys table...")
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS api_keys (
        id              SERIAL PRIMARY KEY,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name            VARCHAR(120) NOT NULL,
        key_prefix      VARCHAR(24)  NOT NULL,
        key_hash        VARCHAR(128) NOT NULL UNIQUE,
        scopes          VARCHAR(255) NOT NULL DEFAULT 'read',
        rate_limit_per_min INTEGER NOT NULL DEFAULT 60,
        created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_used_at    TIMESTAMP,
        revoked_at      TIMESTAMP
    )
    """
)

print("Creating api_credit_transactions table...")
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS api_credit_transactions (
        id               SERIAL PRIMARY KEY,
        user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        api_key_id       INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
        amount           INTEGER NOT NULL,
        transaction_type VARCHAR(40) NOT NULL,
        endpoint         VARCHAR(120),
        stripe_session_id VARCHAR(255),
        description      TEXT,
        created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

print("Creating api_request_logs table...")
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS api_request_logs (
        id               BIGSERIAL PRIMARY KEY,
        api_key_id       INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
        user_id          INTEGER REFERENCES users(id) ON DELETE SET NULL,
        request_id       VARCHAR(64) NOT NULL,
        method           VARCHAR(8)  NOT NULL,
        path             VARCHAR(255) NOT NULL,
        status_code      INTEGER NOT NULL,
        credits_charged  INTEGER NOT NULL DEFAULT 0,
        duration_ms      INTEGER NOT NULL DEFAULT 0,
        ip               VARCHAR(64),
        created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)

print("Creating api_rate_counters table...")
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS api_rate_counters (
        api_key_id  INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
        window_start TIMESTAMP NOT NULL,
        count       INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (api_key_id, window_start)
    )
    """
)

print("Creating indexes...")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_api_credit_tx_user ON api_credit_transactions(user_id, created_at DESC)"
)
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_api_logs_key_time ON api_request_logs(api_key_id, created_at DESC)"
)
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_api_logs_user_time ON api_request_logs(user_id, created_at DESC)"
)

conn.commit()
print("API v1 migration complete.")

for table in (
    "api_keys",
    "api_credit_transactions",
    "api_request_logs",
    "api_rate_counters",
):
    cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    print(f"\n{table}:")
    for col in cursor.fetchall():
        print(f"  - {col[0]}: {col[1]}")

conn.close()
