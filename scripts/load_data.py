"""
CSV Data Loader for Property Ownership Database
Loads CSV data into SQLite database with validation and logging
"""

import csv
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'property_data.db')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'CCOD_FULL_2025_10.csv')


def normalize_company_number(company_no):
    """Normalize company number by removing whitespace and converting to uppercase"""
    if not company_no:
        return None
    return company_no.strip().upper()


def create_database():
    """Create database schema"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Read and execute schema file
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')
    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found at {schema_path}")
        conn.close()
        return False
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
        cursor.executescript(schema_sql)
    
    conn.commit()
    conn.close()
    print("Database schema created successfully")
    return True


def load_csv_data():
    """Load CSV data into database"""
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return
    
    # Create database if it doesn't exist
    if not os.path.exists(DATABASE_PATH):
        if not create_database():
            print("Failed to create database schema")
            return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM proprietors")
    cursor.execute("DELETE FROM properties")
    conn.commit()
    
    stats = {
        'total_rows': 0,
        'properties_inserted': 0,
        'proprietors_inserted': 0,
        'errors': 0,
        'skipped_empty_company': 0
    }
    
    print(f"Loading data from {CSV_PATH}...")
    print("This may take a few minutes for large files...")
    
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                stats['total_rows'] += 1
                
                if row_num % 10000 == 0:
                    print(f"Processed {row_num:,} rows...")
                    conn.commit()  # Periodic commits for large files
                
                try:
                    # Insert property
                    cursor.execute("""
                        INSERT OR REPLACE INTO properties 
                        (title_number, tenure, property_address, district, county, region, 
                         postcode, multiple_address_indicator, price_paid, 
                         date_proprietor_added, additional_proprietor_indicator)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('Title Number', '').strip(),
                        row.get('Tenure', '').strip(),
                        row.get('Property Address', '').strip(),
                        row.get('District', '').strip(),
                        row.get('County', '').strip(),
                        row.get('Region', '').strip(),
                        row.get('Postcode', '').strip(),
                        row.get('Multiple Address Indicator', '').strip(),
                        row.get('Price Paid', '').strip(),
                        row.get('Date Proprietor Added', '').strip(),
                        row.get('Additional Proprietor Indicator', '').strip()
                    ))
                    
                    property_id = cursor.lastrowid
                    stats['properties_inserted'] += 1
                    
                    # Insert proprietors (up to 4)
                    for prop_num in range(1, 5):
                        company_no = normalize_company_number(
                            row.get(f'Company Registration No. ({prop_num})', '')
                        )
                        proprietor_name = row.get(f'Proprietor Name ({prop_num})', '').strip()
                        
                        # Skip if no company number and no proprietor name
                        if not company_no and not proprietor_name:
                            continue
                        
                        # Track if we skip rows with no company number (user wants companies only)
                        if not company_no:
                            stats['skipped_empty_company'] += 1
                            continue
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO proprietors
                            (property_id, proprietor_number, proprietor_name, company_registration_no,
                             proprietorship_category, address_line_1, address_line_2, address_line_3)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            property_id,
                            prop_num,
                            proprietor_name,
                            company_no,
                            row.get(f'Proprietorship Category ({prop_num})', '').strip(),
                            row.get(f'Proprietor ({prop_num}) Address (1)', '').strip(),
                            row.get(f'Proprietor ({prop_num}) Address (2)', '').strip(),
                            row.get(f'Proprietor ({prop_num}) Address (3)', '').strip()
                        ))
                        stats['proprietors_inserted'] += 1
                
                except Exception as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 5:  # Only print first 5 errors
                        print(f"Error processing row {row_num}: {e}")
        
        conn.commit()
        print("\n" + "="*60)
        print("Data loading completed!")
        print("="*60)
        print(f"Total rows processed: {stats['total_rows']:,}")
        print(f"Properties inserted: {stats['properties_inserted']:,}")
        print(f"Proprietors inserted: {stats['proprietors_inserted']:,}")
        print(f"Rows skipped (no company number): {stats['skipped_empty_company']:,}")
        print(f"Errors: {stats['errors']}")
        print("="*60)
    
    except Exception as e:
        print(f"Fatal error: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


if __name__ == '__main__':
    print("Property Ownership Data Loader")
    print("="*60)
    load_csv_data()

