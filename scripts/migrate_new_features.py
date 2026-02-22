"""
Migration script: Add search_history and rate_limits tables.
Supports both PostgreSQL (production) and SQLite (development).
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()
load_dotenv('env.local')

DATABASE_URL = os.environ.get('DATABASE_URL')


def migrate_postgres():
    """Apply migration to PostgreSQL."""
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("Creating search_history table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            search_type VARCHAR(50) NOT NULL,
            search_value TEXT NOT NULL,
            result_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at)")

    print("Creating rate_limits table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id SERIAL PRIMARY KEY,
            identifier VARCHAR(255) NOT NULL,
            endpoint VARCHAR(100) NOT NULL,
            request_count INTEGER DEFAULT 1,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier, endpoint)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(window_start)")

    conn.commit()
    conn.close()
    print("PostgreSQL migration complete.")


def migrate_sqlite():
    """Apply migration to SQLite."""
    import sqlite3
    db_path = Path(__file__).parent.parent / 'property_data.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Creating search_history table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            search_type TEXT NOT NULL,
            search_value TEXT NOT NULL,
            result_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at)")

    print("Creating rate_limits table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            request_count INTEGER DEFAULT 1,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier, endpoint)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(window_start)")

    conn.commit()
    conn.close()
    print("SQLite migration complete.")


if __name__ == '__main__':
    if DATABASE_URL:
        print(f"Migrating PostgreSQL database...")
        migrate_postgres()
    else:
        print("No DATABASE_URL found, migrating local SQLite database...")
        migrate_sqlite()
