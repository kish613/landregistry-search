"""
Fast Migration script: SQLite to PostgreSQL (Neon)
Uses PostgreSQL COPY command for 10-100x faster bulk loading.
"""

import sqlite3
import psycopg2
import os
import csv
import io
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
load_dotenv()
load_dotenv('env.local')

BASE_DIR = Path(__file__).parent.parent
SQLITE_PATH = BASE_DIR / 'property_data.db'
DATABASE_URL = os.environ.get('DATABASE_URL')

def create_postgres_schema(pg_conn):
    """Create the PostgreSQL schema"""
    cursor = pg_conn.cursor()
    
    print("Dropping existing tables...")
    cursor.execute("DROP TABLE IF EXISTS proprietors CASCADE")
    cursor.execute("DROP TABLE IF EXISTS properties CASCADE")
    
    print("Creating properties table...")
    cursor.execute("""
        CREATE TABLE properties (
            id INTEGER PRIMARY KEY,
            title_number TEXT,
            tenure TEXT,
            property_address TEXT,
            district TEXT,
            county TEXT,
            region TEXT,
            postcode TEXT,
            multiple_address_indicator TEXT,
            price_paid TEXT,
            date_proprietor_added TEXT,
            additional_proprietor_indicator TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("Creating proprietors table...")
    cursor.execute("""
        CREATE TABLE proprietors (
            id INTEGER PRIMARY KEY,
            property_id INTEGER NOT NULL,
            proprietor_number INTEGER NOT NULL,
            proprietor_name TEXT,
            company_registration_no TEXT,
            proprietorship_category TEXT,
            address_line_1 TEXT,
            address_line_2 TEXT,
            address_line_3 TEXT
        )
    """)
    
    pg_conn.commit()
    print("Schema created (indexes will be added after data load for speed).")

def create_indexes(pg_conn):
    """Create indexes after data load (faster this way)"""
    cursor = pg_conn.cursor()
    
    print("\nCreating indexes...")
    print("  - idx_company_registration_no")
    cursor.execute("CREATE INDEX idx_company_registration_no ON proprietors(company_registration_no)")
    pg_conn.commit()
    
    print("  - idx_property_id")
    cursor.execute("CREATE INDEX idx_property_id ON proprietors(property_id)")
    pg_conn.commit()
    
    print("  - idx_title_number")
    cursor.execute("CREATE INDEX idx_title_number ON properties(title_number)")
    pg_conn.commit()
    
    print("  - idx_postcode")
    cursor.execute("CREATE INDEX idx_postcode ON properties(postcode)")
    pg_conn.commit()
    
    print("  - idx_proprietor_name")
    cursor.execute("CREATE INDEX idx_proprietor_name ON proprietors(proprietor_name)")
    pg_conn.commit()
    
    print("  - Adding foreign key constraint")
    cursor.execute("ALTER TABLE proprietors ADD CONSTRAINT fk_property FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE")
    pg_conn.commit()
    
    print("Indexes created!")

def copy_table_fast(sqlite_conn, pg_conn, table_name, columns, batch_size=50000):
    """Copy table using PostgreSQL COPY command with streaming CSV"""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Get total count
    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total = sqlite_cursor.fetchone()[0]
    print(f"\nMigrating {table_name}: {total:,} rows")
    
    # Select all data
    cols_str = ', '.join(columns)
    sqlite_cursor.execute(f"SELECT {cols_str} FROM {table_name}")
    
    count = 0
    while True:
        rows = sqlite_cursor.fetchmany(batch_size)
        if not rows:
            break
        
        # Create CSV in memory
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
        for row in rows:
            # Handle None values and escape
            cleaned_row = ['' if v is None else str(v).replace('\x00', '') for v in row]
            writer.writerow(cleaned_row)
        
        buffer.seek(0)
        
        # Use COPY command (much faster than INSERT)
        pg_cursor.copy_expert(
            f"COPY {table_name} ({cols_str}) FROM STDIN WITH CSV",
            buffer
        )
        pg_conn.commit()
        
        count += len(rows)
        pct = count * 100 // total
        print(f"  {count:,} / {total:,} ({pct}%)")
    
    print(f"  Completed: {count:,} rows")
    return count

def main():
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set. Please check your env.local file.")
        return
    
    if not SQLITE_PATH.exists():
        print(f"Error: SQLite database not found at {SQLITE_PATH}")
        return
    
    print(f"Connecting to SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    
    print(f"Connecting to PostgreSQL (Neon)...")
    pg_conn = psycopg2.connect(DATABASE_URL)
    
    try:
        print("\n" + "="*50)
        print("FAST MIGRATION: SQLite -> PostgreSQL")
        print("="*50)
        
        create_postgres_schema(pg_conn)
        
        # Migrate properties first (parent table)
        properties_cols = [
            'id', 'title_number', 'tenure', 'property_address', 'district', 'county',
            'region', 'postcode', 'multiple_address_indicator', 'price_paid',
            'date_proprietor_added', 'additional_proprietor_indicator'
        ]
        copy_table_fast(sqlite_conn, pg_conn, 'properties', properties_cols)
        
        # Migrate proprietors
        proprietors_cols = [
            'id', 'property_id', 'proprietor_number', 'proprietor_name',
            'company_registration_no', 'proprietorship_category',
            'address_line_1', 'address_line_2', 'address_line_3'
        ]
        copy_table_fast(sqlite_conn, pg_conn, 'proprietors', proprietors_cols)
        
        # Create indexes after data load
        create_indexes(pg_conn)
        
        print("\n" + "="*50)
        print("MIGRATION COMPLETE!")
        print("="*50)
        
        # Verify counts
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("SELECT COUNT(*) FROM properties")
        print(f"Properties in PostgreSQL: {pg_cursor.fetchone()[0]:,}")
        pg_cursor.execute("SELECT COUNT(*) FROM proprietors")
        print(f"Proprietors in PostgreSQL: {pg_cursor.fetchone()[0]:,}")
        
    except Exception as e:
        print(f"\nError during migration: {e}")
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
