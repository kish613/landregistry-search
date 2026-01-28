"""
Migration script: Add normalized columns and indexes for faster searches
This script adds pre-computed normalized columns and creates indexes to speed up database searches.

Run this script AFTER migrating data to PostgreSQL (after migrate_to_postgres.py).
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv

def log(msg):
    """Print with immediate flush"""
    print(msg)
    sys.stdout.flush()

# Load environment variables
load_dotenv()
load_dotenv('env.local')

DATABASE_URL = os.environ.get('DATABASE_URL')


def normalize_company_reg(value):
    """Normalize company registration number - matches main.py logic"""
    if not value:
        return ''
    return value.strip().upper().replace('(', '').replace(')', '').replace(' ', '').replace('-', '')


def normalize_text_upper(value):
    """Normalize text to uppercase trimmed - matches main.py logic"""
    if not value:
        return ''
    return value.strip().upper()


def add_normalized_columns(pg_conn):
    """Add normalized columns to tables"""
    cursor = pg_conn.cursor()
    
    log("Adding normalized columns to proprietors table...")
    try:
        cursor.execute("""
            ALTER TABLE proprietors 
            ADD COLUMN IF NOT EXISTS company_reg_normalized TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS proprietor_name_upper TEXT NOT NULL DEFAULT ''
        """)
        pg_conn.commit()
        log("  [OK] Added company_reg_normalized and proprietor_name_upper columns")
    except Exception as e:
        log(f"  [WARN] Error adding columns (may already exist): {e}")
        pg_conn.rollback()
    
    log("Adding normalized columns to properties table...")
    try:
        cursor.execute("""
            ALTER TABLE properties 
            ADD COLUMN IF NOT EXISTS property_address_upper TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS postcode_upper TEXT NOT NULL DEFAULT ''
        """)
        pg_conn.commit()
        log("  [OK] Added property_address_upper and postcode_upper columns")
    except Exception as e:
        log(f"  [WARN] Error adding columns (may already exist): {e}")
        pg_conn.rollback()


def backfill_normalized_data(pg_conn):
    """Populate normalized columns from existing data using efficient SQL"""
    cursor = pg_conn.cursor()
    
    log("\nBackfilling normalized data in proprietors table...")
    
    # Get count
    cursor.execute("SELECT COUNT(*) FROM proprietors")
    total = cursor.fetchone()[0]
    log(f"  Total proprietors: {total:,}")
    log("  Running SQL UPDATE (this may take a few minutes)...")
    
    # Use pure SQL for efficiency - PostgreSQL handles this much faster than Python loops
    cursor.execute("""
        UPDATE proprietors 
        SET 
            company_reg_normalized = UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(COALESCE(company_registration_no, '')), '(', ''), ')', ''), ' ', ''), '-', '')),
            proprietor_name_upper = UPPER(TRIM(COALESCE(proprietor_name, '')))
        WHERE company_reg_normalized = '' OR proprietor_name_upper = ''
    """)
    updated = cursor.rowcount
    pg_conn.commit()
    log(f"  [OK] Updated {updated:,} proprietors")
    
    log("\nBackfilling normalized data in properties table...")
    
    # Get count
    cursor.execute("SELECT COUNT(*) FROM properties")
    total = cursor.fetchone()[0]
    log(f"  Total properties: {total:,}")
    log("  Running SQL UPDATE (this may take a few minutes)...")
    
    # Use pure SQL for efficiency
    cursor.execute("""
        UPDATE properties 
        SET 
            property_address_upper = UPPER(TRIM(COALESCE(property_address, ''))),
            postcode_upper = UPPER(TRIM(COALESCE(postcode, '')))
        WHERE property_address_upper = '' OR postcode_upper = ''
    """)
    updated = cursor.rowcount
    pg_conn.commit()
    log(f"  [OK] Updated {updated:,} properties")


def create_indexes(pg_conn):
    """Enable pg_trgm extension and create indexes"""
    cursor = pg_conn.cursor()
    
    log("\nEnabling pg_trgm extension...")
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        pg_conn.commit()
        log("  [OK] pg_trgm extension enabled")
    except Exception as e:
        log(f"  [WARN] Error enabling extension (may already exist): {e}")
        pg_conn.rollback()
    
    log("\nCreating indexes...")
    
    indexes = [
        ("idx_company_reg_normalized", 
         "CREATE INDEX IF NOT EXISTS idx_company_reg_normalized ON proprietors(company_reg_normalized)"),
        ("idx_proprietor_name_trgm",
         "CREATE INDEX IF NOT EXISTS idx_proprietor_name_trgm ON proprietors USING GIN (proprietor_name_upper gin_trgm_ops)"),
        ("idx_property_address_trgm",
         "CREATE INDEX IF NOT EXISTS idx_property_address_trgm ON properties USING GIN (property_address_upper gin_trgm_ops)"),
        ("idx_postcode_trgm",
         "CREATE INDEX IF NOT EXISTS idx_postcode_trgm ON properties USING GIN (postcode_upper gin_trgm_ops)")
    ]
    
    for index_name, sql in indexes:
        try:
            cursor.execute(sql)
            pg_conn.commit()
            log(f"  [OK] Created index: {index_name}")
        except Exception as e:
            log(f"  [WARN] Error creating {index_name} (may already exist): {e}")
            pg_conn.rollback()


def verify_migration(pg_conn):
    """Verify the migration was successful"""
    cursor = pg_conn.cursor()
    
    log("\n=== Verification ===")
    
    # Check columns exist
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'proprietors' 
        AND column_name IN ('company_reg_normalized', 'proprietor_name_upper')
    """)
    prop_cols = [row[0] for row in cursor.fetchall()]
    log(f"Proprietors normalized columns: {prop_cols}")
    
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'properties' 
        AND column_name IN ('property_address_upper', 'postcode_upper')
    """)
    props_cols = [row[0] for row in cursor.fetchall()]
    log(f"Properties normalized columns: {props_cols}")
    
    # Check indexes exist
    cursor.execute("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexname IN ('idx_company_reg_normalized', 'idx_proprietor_name_trgm', 
                          'idx_property_address_trgm', 'idx_postcode_trgm')
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    log(f"Created indexes: {indexes}")
    
    # Check data population
    cursor.execute("SELECT COUNT(*) FROM proprietors WHERE company_reg_normalized != ''")
    prop_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM properties WHERE property_address_upper != ''")
    props_count = cursor.fetchone()[0]
    log(f"\nData populated:")
    log(f"  Proprietors with normalized data: {prop_count:,}")
    log(f"  Properties with normalized data: {props_count:,}")


def main():
    if not DATABASE_URL:
        log("Error: DATABASE_URL not set. Please check your env.local file.")
        return
    
    log("Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
    
    try:
        log("\n=== Adding Normalized Columns ===")
        add_normalized_columns(pg_conn)
        
        log("\n=== Backfilling Normalized Data ===")
        backfill_normalized_data(pg_conn)
        
        log("\n=== Creating Indexes ===")
        create_indexes(pg_conn)
        
        log("\n=== Verifying Migration ===")
        verify_migration(pg_conn)
        
        log("\n=== Migration Complete! ===")
        log("\nNext steps:")
        log("1. Run scripts/validate_search_results.py to verify search integrity")
        log("2. Test searches to confirm performance improvements")
        
    except Exception as e:
        log(f"\nError during migration: {e}")
        pg_conn.rollback()
        raise
    finally:
        pg_conn.close()


if __name__ == '__main__':
    main()
