"""
Validation script: Compare old vs new search query results
This script runs sample searches using both old (function-based) and new (indexed) query methods
to ensure the optimizations don't change search results.

Run this AFTER migrate_add_indexes.py to verify data integrity.
"""

import psycopg2
import os
from dotenv import load_dotenv
from collections import Counter

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


def search_old_company_number(conn, company_number):
    """Old search method using function-based WHERE clause"""
    cursor = conn.cursor()
    normalized = normalize_company_reg(company_number)
    
    cursor.execute("""
        SELECT 
            p.id,
            p.title_number,
            pr.company_registration_no
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) = %s
        ORDER BY p.id
    """, (normalized,))
    
    return set(row[0] for row in cursor.fetchall())


def search_new_company_number(conn, company_number):
    """New search method using indexed normalized column"""
    cursor = conn.cursor()
    normalized = normalize_company_reg(company_number)
    
    cursor.execute("""
        SELECT 
            p.id,
            p.title_number,
            pr.company_registration_no
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE pr.company_reg_normalized = %s
        ORDER BY p.id
    """, (normalized,))
    
    return set(row[0] for row in cursor.fetchall())


def search_old_company_name(conn, company_name):
    """Old search method using function-based WHERE clause"""
    cursor = conn.cursor()
    normalized = normalize_text_upper(company_name)
    
    cursor.execute("""
        SELECT 
            p.id,
            pr.proprietor_name
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE UPPER(TRIM(pr.proprietor_name)) LIKE %s
        ORDER BY p.id
        LIMIT 100
    """, (f'%{normalized}%',))
    
    return set(row[0] for row in cursor.fetchall())


def search_new_company_name(conn, company_name):
    """New search method using indexed normalized column"""
    cursor = conn.cursor()
    normalized = normalize_text_upper(company_name)
    
    cursor.execute("""
        SELECT 
            p.id,
            pr.proprietor_name
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE pr.proprietor_name_upper LIKE %s
        ORDER BY p.id
        LIMIT 100
    """, (f'%{normalized}%',))
    
    return set(row[0] for row in cursor.fetchall())


def search_old_address(conn, address):
    """Old search method using function-based WHERE clause"""
    cursor = conn.cursor()
    normalized = normalize_text_upper(address)
    
    cursor.execute("""
        SELECT 
            p.id,
            p.property_address
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE UPPER(TRIM(p.property_address)) LIKE %s
           OR UPPER(TRIM(p.postcode)) LIKE %s
        ORDER BY p.id
        LIMIT 100
    """, (f'%{normalized}%', f'%{normalized}%'))
    
    return set(row[0] for row in cursor.fetchall())


def search_new_address(conn, address):
    """New search method using indexed normalized columns"""
    cursor = conn.cursor()
    normalized = normalize_text_upper(address)
    
    cursor.execute("""
        SELECT 
            p.id,
            p.property_address
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE p.property_address_upper LIKE %s
           OR p.postcode_upper LIKE %s
        ORDER BY p.id
        LIMIT 100
    """, (f'%{normalized}%', f'%{normalized}%'))
    
    return set(row[0] for row in cursor.fetchall())


def get_sample_company_numbers(conn, limit=20):
    """Get sample company numbers from database for testing"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT company_registration_no 
        FROM proprietors 
        WHERE company_registration_no IS NOT NULL 
        AND TRIM(company_registration_no) != ''
        LIMIT %s
    """, (limit,))
    return [row[0] for row in cursor.fetchall()]


def get_sample_company_names(conn, limit=20):
    """Get sample company names from database for testing"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT proprietor_name 
        FROM proprietors 
        WHERE proprietor_name IS NOT NULL 
        AND TRIM(proprietor_name) != ''
        LIMIT %s
    """, (limit,))
    return [row[0] for row in cursor.fetchall()]


def get_sample_addresses(conn, limit=20):
    """Get sample addresses from database for testing"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT property_address 
        FROM properties 
        WHERE property_address IS NOT NULL 
        AND TRIM(property_address) != ''
        LIMIT %s
    """, (limit,))
    return [row[0] for row in cursor.fetchall()]


def compare_results(old_results, new_results, search_type, search_value):
    """Compare two result sets and report differences"""
    old_set = set(old_results)
    new_set = set(new_results)
    
    only_old = old_set - new_set
    only_new = new_set - old_set
    common = old_set & new_set
    
    match = len(only_old) == 0 and len(only_new) == 0
    
    if not match:
        print(f"\n  ⚠ MISMATCH for {search_type}: '{search_value}'")
        print(f"    Old results: {len(old_set)}, New results: {len(new_set)}, Common: {len(common)}")
        if only_old:
            print(f"    Only in old: {len(only_old)} results")
        if only_new:
            print(f"    Only in new: {len(only_new)} results")
    else:
        print(f"  ✓ Match: {len(common)} results")
    
    return match


def main():
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set. Please check your env.local file.")
        return
    
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    
    try:
        print("\n=== Validation: Comparing Old vs New Search Methods ===\n")
        
        all_match = True
        
        # Test company number searches
        print("Testing company number searches...")
        company_numbers = get_sample_company_numbers(conn, 20)
        for i, company_num in enumerate(company_numbers[:10], 1):  # Test first 10
            print(f"  Test {i}/10: {company_num[:20]}...")
            old_results = search_old_company_number(conn, company_num)
            new_results = search_new_company_number(conn, company_num)
            if not compare_results(old_results, new_results, "company_number", company_num):
                all_match = False
        
        # Test company name searches
        print("\nTesting company name searches...")
        company_names = get_sample_company_names(conn, 20)
        for i, company_name in enumerate(company_names[:10], 1):  # Test first 10
            print(f"  Test {i}/10: {company_name[:30]}...")
            old_results = search_old_company_name(conn, company_name)
            new_results = search_new_company_name(conn, company_name)
            if not compare_results(old_results, new_results, "company_name", company_name):
                all_match = False
        
        # Test address searches
        print("\nTesting address searches...")
        addresses = get_sample_addresses(conn, 20)
        for i, address in enumerate(addresses[:10], 1):  # Test first 10
            print(f"  Test {i}/10: {address[:30]}...")
            old_results = search_old_address(conn, address)
            new_results = search_new_address(conn, address)
            if not compare_results(old_results, new_results, "address", address):
                all_match = False
        
        # Summary
        print("\n" + "="*60)
        if all_match:
            print("✓ VALIDATION PASSED: All searches return identical results")
            print("\nThe optimized queries produce the same results as the original queries.")
            print("It's safe to deploy the optimized version.")
        else:
            print("✗ VALIDATION FAILED: Some searches return different results")
            print("\nWARNING: The optimized queries return different results!")
            print("Please investigate the mismatches before deploying.")
        print("="*60)
        
    except Exception as e:
        print(f"\nError during validation: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
