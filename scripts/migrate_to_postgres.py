"""
Migration script: SQLite to PostgreSQL (Neon)
This script migrates data from the local SQLite database to Neon PostgreSQL.
"""

import sqlite3
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv('env.local')

BASE_DIR = Path(__file__).parent.parent
SQLITE_PATH = BASE_DIR / 'property_data.db'
DATABASE_URL = os.environ.get('DATABASE_URL')

def create_postgres_schema(pg_conn):
    """Create the PostgreSQL schema"""
    cursor = pg_conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute("DROP TABLE IF EXISTS proprietors CASCADE")
    cursor.execute("DROP TABLE IF EXISTS properties CASCADE")
    
    # Create properties table
    cursor.execute("""
        CREATE TABLE properties (
            id SERIAL PRIMARY KEY,
            title_number TEXT NOT NULL UNIQUE,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create proprietors table
    cursor.execute("""
        CREATE TABLE proprietors (
            id SERIAL PRIMARY KEY,
            property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
            proprietor_number INTEGER NOT NULL,
            proprietor_name TEXT,
            company_registration_no TEXT,
            proprietorship_category TEXT,
            address_line_1 TEXT,
            address_line_2 TEXT,
            address_line_3 TEXT,
            UNIQUE(property_id, proprietor_number)
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX idx_company_registration_no ON proprietors(company_registration_no)")
    cursor.execute("CREATE INDEX idx_property_id ON proprietors(property_id)")
    cursor.execute("CREATE INDEX idx_title_number ON properties(title_number)")
    cursor.execute("CREATE INDEX idx_postcode ON properties(postcode)")
    cursor.execute("CREATE INDEX idx_proprietor_name ON proprietors(proprietor_name)")
    
    pg_conn.commit()
    print("PostgreSQL schema created successfully.")

def migrate_data(sqlite_conn, pg_conn, batch_size=1000):
    """Migrate data from SQLite to PostgreSQL"""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Migrate properties
    print("Migrating properties...")
    sqlite_cursor.execute("SELECT COUNT(*) FROM properties")
    total_properties = sqlite_cursor.fetchone()[0]
    print(f"Total properties to migrate: {total_properties:,}")
    
    sqlite_cursor.execute("""
        SELECT id, title_number, tenure, property_address, district, county, 
               region, postcode, multiple_address_indicator, price_paid,
               date_proprietor_added, additional_proprietor_indicator
        FROM properties
    """)
    
    count = 0
    batch = []
    for row in sqlite_cursor:
        batch.append(row)
        if len(batch) >= batch_size:
            pg_cursor.executemany("""
                INSERT INTO properties (id, title_number, tenure, property_address, district, county,
                                       region, postcode, multiple_address_indicator, price_paid,
                                       date_proprietor_added, additional_proprietor_indicator)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
            pg_conn.commit()
            count += len(batch)
            print(f"  Migrated {count:,} / {total_properties:,} properties ({count*100//total_properties}%)")
            batch = []
    
    if batch:
        pg_cursor.executemany("""
            INSERT INTO properties (id, title_number, tenure, property_address, district, county,
                                   region, postcode, multiple_address_indicator, price_paid,
                                   date_proprietor_added, additional_proprietor_indicator)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, batch)
        pg_conn.commit()
        count += len(batch)
    
    print(f"  Completed: {count:,} properties migrated.")
    
    # Reset the sequence for properties
    pg_cursor.execute("SELECT setval('properties_id_seq', (SELECT MAX(id) FROM properties))")
    pg_conn.commit()
    
    # Migrate proprietors
    print("\nMigrating proprietors...")
    sqlite_cursor.execute("SELECT COUNT(*) FROM proprietors")
    total_proprietors = sqlite_cursor.fetchone()[0]
    print(f"Total proprietors to migrate: {total_proprietors:,}")
    
    sqlite_cursor.execute("""
        SELECT id, property_id, proprietor_number, proprietor_name, company_registration_no,
               proprietorship_category, address_line_1, address_line_2, address_line_3
        FROM proprietors
    """)
    
    count = 0
    batch = []
    for row in sqlite_cursor:
        batch.append(row)
        if len(batch) >= batch_size:
            pg_cursor.executemany("""
                INSERT INTO proprietors (id, property_id, proprietor_number, proprietor_name, 
                                        company_registration_no, proprietorship_category,
                                        address_line_1, address_line_2, address_line_3)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
            pg_conn.commit()
            count += len(batch)
            print(f"  Migrated {count:,} / {total_proprietors:,} proprietors ({count*100//total_proprietors}%)")
            batch = []
    
    if batch:
        pg_cursor.executemany("""
            INSERT INTO proprietors (id, property_id, proprietor_number, proprietor_name, 
                                    company_registration_no, proprietorship_category,
                                    address_line_1, address_line_2, address_line_3)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, batch)
        pg_conn.commit()
        count += len(batch)
    
    print(f"  Completed: {count:,} proprietors migrated.")
    
    # Reset the sequence for proprietors
    pg_cursor.execute("SELECT setval('proprietors_id_seq', (SELECT MAX(id) FROM proprietors))")
    pg_conn.commit()

def main():
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set. Please check your env.local file.")
        return
    
    if not SQLITE_PATH.exists():
        print(f"Error: SQLite database not found at {SQLITE_PATH}")
        return
    
    print(f"Connecting to SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    
    print(f"Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(DATABASE_URL)
    
    try:
        print("\n=== Creating PostgreSQL Schema ===")
        create_postgres_schema(pg_conn)
        
        print("\n=== Migrating Data ===")
        migrate_data(sqlite_conn, pg_conn)
        
        print("\n=== Migration Complete! ===")
        
        # Verify counts
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()
        
        sqlite_cursor.execute("SELECT COUNT(*) FROM properties")
        pg_cursor.execute("SELECT COUNT(*) FROM properties")
        print(f"Properties: SQLite={sqlite_cursor.fetchone()[0]:,}, PostgreSQL={pg_cursor.fetchone()[0]:,}")
        
        sqlite_cursor.execute("SELECT COUNT(*) FROM proprietors")
        pg_cursor.execute("SELECT COUNT(*) FROM proprietors")
        print(f"Proprietors: SQLite={sqlite_cursor.fetchone()[0]:,}, PostgreSQL={pg_cursor.fetchone()[0]:,}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main()
