"""
Flask Web Application for Property Lookup by Company Number
"""

from flask import Flask, render_template, request, jsonify, send_file
import psycopg2
import psycopg2.extras
import os
import csv
import io
import requests
import stripe
from pathlib import Path
from rapidfuzz import fuzz, process
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env or env.local
load_dotenv()
load_dotenv('env.local')

app = Flask(__name__)

# Database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

# Companies House API Key
COMPANIES_HOUSE_API_KEY = os.environ.get('COMPANIES_HOUSE_API_KEY')
COMPANIES_HOUSE_BASE_URL = 'https://api.company-information.service.gov.uk'

# Stripe Configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Pricing in pence (£1 = 100 pence, £3 = 300 pence)
SEARCH_PRICES = {
    'name': 100,      # £1 for company name search
    'number': 100,    # £1 for company number search
    'address': 100,   # £1 for address search
    'director': 300   # £3 for director search
}

# In-memory storage for used sessions (in production, use database)
used_sessions = set()

# For local development fallback to SQLite
BASE_DIR = Path(__file__).parent.parent
LOCAL_DATABASE_PATH = BASE_DIR / 'property_data.db'


def get_db_connection():
    """Get database connection (PostgreSQL for production, SQLite for local dev)"""
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        # Fallback for local development
        import sqlite3
        conn = sqlite3.connect(LOCAL_DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def dict_cursor(conn):
    """Get appropriate cursor based on connection type"""
    if DATABASE_URL:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        return conn.cursor()


def record_payment(stripe_session_id, search_type, search_value, amount_pence, status='pending'):
    """Record a payment in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute("""
                INSERT INTO payments (stripe_session_id, search_type, search_value, amount_pence, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (stripe_session_id) DO UPDATE SET status = EXCLUDED.status
            """, (stripe_session_id, search_type, search_value, amount_pence, status))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO payments (stripe_session_id, search_type, search_value, amount_pence, status)
                VALUES (?, ?, ?, ?, ?)
            """, (stripe_session_id, search_type, search_value, amount_pence, status))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error recording payment: {e}")
        return False


def mark_payment_used(stripe_session_id):
    """Mark a payment as used in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute("""
                UPDATE payments 
                SET used_at = CURRENT_TIMESTAMP, status = 'used'
                WHERE stripe_session_id = %s AND used_at IS NULL
            """, (stripe_session_id,))
        else:
            cursor.execute("""
                UPDATE payments 
                SET used_at = CURRENT_TIMESTAMP, status = 'used'
                WHERE stripe_session_id = ? AND used_at IS NULL
            """, (stripe_session_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0
    except Exception as e:
        print(f"Error marking payment as used: {e}")
        return False


def is_payment_used(stripe_session_id):
    """Check if a payment has already been used"""
    # First check in-memory cache
    if stripe_session_id in used_sessions:
        return True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute("""
                SELECT used_at FROM payments WHERE stripe_session_id = %s
            """, (stripe_session_id,))
        else:
            cursor.execute("""
                SELECT used_at FROM payments WHERE stripe_session_id = ?
            """, (stripe_session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            used_at = result[0] if isinstance(result, tuple) else result.get('used_at')
            return used_at is not None
        return False
    except Exception as e:
        print(f"Error checking payment status: {e}")
        # Fall back to in-memory check
        return stripe_session_id in used_sessions


def search_properties_by_company(company_number):
    """Search for properties owned by a company number"""
    if not company_number:
        return []
    
    # Normalize company number - remove spaces, parentheses, hyphens, convert to uppercase
    # Preserve leading zeros!
    company_number = company_number.strip().upper()
    company_number = company_number.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
    
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    # Query properties with matching company registration number
    # Normalize both input and database values for comparison (remove spaces, parentheses, convert to uppercase)
    cursor.execute("""
        SELECT 
            p.id,
            p.title_number,
            p.tenure,
            p.property_address,
            p.district,
            p.county,
            p.region,
            p.postcode,
            p.price_paid,
            p.date_proprietor_added,
            pr.proprietor_name,
            pr.proprietorship_category,
            pr.address_line_1,
            pr.address_line_2,
            pr.address_line_3,
            pr.company_registration_no
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) = %s
        ORDER BY p.property_address
    """, (company_number.replace('(', '').replace(')', '').replace(' ', '').replace('-', ''),))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]


def get_all_unique_company_names():
    """Get all unique company names from the database"""
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute("""
        SELECT DISTINCT proprietor_name 
        FROM proprietors 
        WHERE proprietor_name IS NOT NULL AND TRIM(proprietor_name) != ''
        ORDER BY proprietor_name
    """)
    if DATABASE_URL:
        names = [row['proprietor_name'] for row in cursor.fetchall()]
    else:
        names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names


def search_properties_by_company_name(company_name, fuzzy_threshold=70):
    """Search for properties owned by a company name (partial match with fuzzy suggestions)"""
    if not company_name:
        return [], []
    
    # Normalize company name - trim and convert to uppercase for case-insensitive search
    company_name_normalized = company_name.strip().upper()
    company_name_original = company_name.strip()
    
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    # First, try exact/partial match (current behavior)
    cursor.execute("""
        SELECT 
            p.id,
            p.title_number,
            p.tenure,
            p.property_address,
            p.district,
            p.county,
            p.region,
            p.postcode,
            p.price_paid,
            p.date_proprietor_added,
            pr.proprietor_name,
            pr.proprietorship_category,
            pr.address_line_1,
            pr.address_line_2,
            pr.address_line_3,
            pr.company_registration_no
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE UPPER(TRIM(pr.proprietor_name)) LIKE %s
        ORDER BY pr.proprietor_name, p.property_address
    """, (f'%{company_name_normalized}%',))
    
    results = cursor.fetchall()
    conn.close()
    
    # If we have results, return them with no suggestions
    if results:
        return [dict(row) for row in results], []
    
    # If no results, perform fuzzy matching to find suggestions
    all_company_names = get_all_unique_company_names()
    
    # Use rapidfuzz to find similar company names
    # We'll use WRatio which combines multiple algorithms for better results
    matches = process.extract(
        company_name_original,
        all_company_names,
        scorer=fuzz.WRatio,
        limit=5
    )
    
    # Filter matches above threshold and return unique suggestions
    suggestions = []
    seen_names = set()
    for match_name, score, _ in matches:
        if score >= fuzzy_threshold and match_name.upper() not in seen_names:
            suggestions.append({
                'name': match_name,
                'similarity': round(score, 1)
            })
            seen_names.add(match_name.upper())
    
    return [], suggestions


def search_properties_by_address(address_query):
    """Search for properties by address (partial match on property_address or postcode)"""
    if not address_query:
        return []
    
    # Normalize address - trim and convert to uppercase for case-insensitive search
    address_normalized = address_query.strip().upper()
    
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    # Search in property_address and postcode fields
    cursor.execute("""
        SELECT 
            p.id,
            p.title_number,
            p.tenure,
            p.property_address,
            p.district,
            p.county,
            p.region,
            p.postcode,
            p.price_paid,
            p.date_proprietor_added,
            pr.proprietor_name,
            pr.proprietorship_category,
            pr.address_line_1,
            pr.address_line_2,
            pr.address_line_3,
            pr.company_registration_no
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE UPPER(TRIM(p.property_address)) LIKE %s
           OR UPPER(TRIM(p.postcode)) LIKE %s
        ORDER BY p.property_address
        LIMIT 500
    """, (f'%{address_normalized}%', f'%{address_normalized}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]


def is_corporate_officer(name):
    """Check if an officer name appears to be a corporate entity rather than an individual."""
    if not name:
        return False
    name_upper = name.upper()
    corporate_indicators = [
        'LTD', 'LIMITED', 'LLP', 'PLC', 'INC', 'INCORPORATED',
        'CORP', 'CORPORATION', 'LLC', 'CO.', '& CO', 'PARTNERS',
        'TRUSTEES', 'TRUST', 'SECRETARIAL', 'SERVICES', 'NOMINEES'
    ]
    return any(indicator in name_upper for indicator in corporate_indicators)


def search_directors_from_companies_house(director_name, items_per_page=50):
    """
    Search for directors/officers by name using the Companies House API.
    Returns a list of matching INDIVIDUAL officers (filters out corporate officers).
    """
    if not director_name:
        return [], "No search term provided"
    
    if not COMPANIES_HOUSE_API_KEY:
        return [], "Companies House API key not configured. Please set COMPANIES_HOUSE_API_KEY environment variable."
    
    try:
        # Search officers endpoint - request more results to filter individuals
        url = f"{COMPANIES_HOUSE_BASE_URL}/search/officers"
        params = {
            'q': director_name.strip(),
            'items_per_page': items_per_page
        }
        
        # Companies House API uses Basic Auth with API key as username, no password
        response = requests.get(
            url,
            params=params,
            auth=(COMPANIES_HOUSE_API_KEY, ''),
            timeout=15
        )
        
        if response.status_code == 401:
            return [], "Invalid API key - please check COMPANIES_HOUSE_API_KEY is set correctly"
        elif response.status_code == 429:
            return [], "Rate limit exceeded. Please try again later."
        elif response.status_code == 400:
            # Log the actual error from Companies House
            try:
                error_detail = response.json()
                return [], f"Bad request to Companies House: {error_detail}"
            except:
                return [], f"Bad request to Companies House: {response.text[:200]}"
        elif response.status_code != 200:
            return [], f"Companies House API error {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        officers = []
        
        for item in data.get('items', []):
            name = item.get('title', '')
            
            # Filter out corporate officers - we only want individual people
            if is_corporate_officer(name):
                continue
            
            # Check for individual indicators
            # Individuals typically have date_of_birth or 'born-on' in description_identifiers
            has_dob = bool(item.get('date_of_birth'))
            desc_ids = item.get('description_identifiers', [])
            has_born_on = 'born-on' in desc_ids if desc_ids else False
            
            officer_info = {
                'name': name,
                'date_of_birth': item.get('date_of_birth', {}),
                'address': item.get('address', {}),
                'appointment_count': item.get('appointment_count', 0),
                'links': item.get('links', {}),
                'is_individual': has_dob or has_born_on,
                'description': item.get('description', '')
            }
            
            officers.append(officer_info)
        
        return officers, None
        
    except requests.exceptions.Timeout:
        return [], "Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return [], f"Network error: {str(e)}"
    except Exception as e:
        return [], f"Error: {str(e)}"


def get_officer_appointments(officer_link):
    """
    Get all company appointments for a specific officer.
    Returns list of companies where this person is/was a director.
    
    Note: officer_link from search results already includes /appointments
    """
    if not officer_link or not COMPANIES_HOUSE_API_KEY:
        return []
    
    try:
        # The links.self from search already points to /officers/{id}/appointments
        # So we use it directly without appending /appointments again
        url = f"{COMPANIES_HOUSE_BASE_URL}{officer_link}"
        
        response = requests.get(
            url,
            auth=(COMPANIES_HOUSE_API_KEY, ''),
            timeout=15
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        appointments = []
        
        for item in data.get('items', []):
            appointment = {
                'company_number': item.get('appointed_to', {}).get('company_number', ''),
                'company_name': item.get('appointed_to', {}).get('company_name', ''),
                'officer_role': item.get('officer_role', ''),
                'appointed_on': item.get('appointed_on', ''),
                'resigned_on': item.get('resigned_on', ''),
                'company_status': item.get('appointed_to', {}).get('company_status', '')
            }
            if appointment['company_number']:
                appointments.append(appointment)
        
        return appointments
        
    except Exception:
        return []


def search_properties_by_director(director_name):
    """
    Search for properties by director name.
    1. Search Companies House for matching individual directors (not corporate officers)
    2. Get their company appointments
    3. Search local database for properties owned by those companies
    
    Returns: (results, directors_found, suggestions, error)
    """
    if not director_name:
        return [], [], [], "Director name is required"
    
    if not COMPANIES_HOUSE_API_KEY or COMPANIES_HOUSE_API_KEY == 'your_api_key_here':
        return [], [], [], "Companies House API key not configured. Please add your API key to env.local"
    
    # Step 1: Search for directors matching the name (corporate officers are filtered out)
    officers, api_error = search_directors_from_companies_house(director_name)
    
    if api_error:
        return [], [], [], api_error
    
    if not officers:
        # No individual officers found - suggest trying company name search instead
        all_company_names = get_all_unique_company_names()
        matches = process.extract(
            director_name,
            all_company_names,
            scorer=fuzz.WRatio,
            limit=5
        )
        suggestions = [{'name': m[0], 'similarity': round(m[1], 1)} for m in matches if m[1] >= 60]
        return [], [], suggestions, "No individual directors found matching this name. Try searching by company name instead."
    
    # Step 2: For each officer, get their company appointments
    directors_found = []
    all_company_numbers = set()
    
    # Limit to first 15 individual officers to balance thoroughness with rate limits
    for officer in officers[:15]:
        officer_link = officer.get('links', {}).get('self', '')
        
        if officer_link:
            appointments = get_officer_appointments(officer_link)
            
            # Collect unique company numbers
            for appt in appointments:
                company_num = appt.get('company_number', '').strip()
                if company_num:
                    all_company_numbers.add(company_num)
                    
                    # Track which directors map to which companies
                    directors_found.append({
                        'director_name': officer.get('name', ''),
                        'company_number': company_num,
                        'company_name': appt.get('company_name', ''),
                        'officer_role': appt.get('officer_role', ''),
                        'appointed_on': appt.get('appointed_on', ''),
                        'resigned_on': appt.get('resigned_on', ''),
                        'company_status': appt.get('company_status', '')
                    })
    
    if not all_company_numbers:
        # Found directors but no company appointments
        return [], directors_found, [], f"Found {len(officers)} matching directors but none have company appointments in the registry."
    
    # Step 3: Search our local database for properties owned by these companies
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    # Build query with multiple company numbers
    placeholders = ','.join(['%s'] * len(all_company_numbers))
    company_list = list(all_company_numbers)
    
    cursor.execute(f"""
        SELECT 
            p.id,
            p.title_number,
            p.tenure,
            p.property_address,
            p.district,
            p.county,
            p.region,
            p.postcode,
            p.price_paid,
            p.date_proprietor_added,
            pr.proprietor_name,
            pr.proprietorship_category,
            pr.address_line_1,
            pr.address_line_2,
            pr.address_line_3,
            pr.company_registration_no
        FROM properties p
        INNER JOIN proprietors pr ON p.id = pr.property_id
        WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) 
              IN ({placeholders})
        ORDER BY pr.proprietor_name, p.property_address
        LIMIT 500
    """, [cn.upper().replace('(', '').replace(')', '').replace(' ', '').replace('-', '') for cn in company_list])
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results], directors_found, [], None


@app.route('/')
def landing():
    """Landing page"""
    return render_template('landing.html')


@app.route('/search')
def search():
    """Search page"""
    return render_template('search.html')


@app.route('/api/create-checkout', methods=['POST'])
def create_checkout():
    """Create a Stripe Checkout Session for a search"""
    data = request.get_json()
    search_type = data.get('search_type', 'number')
    search_value = data.get('search_value', '').strip()
    
    if not search_value:
        return jsonify({
            'success': False,
            'error': 'Search value is required'
        }), 400
    
    if search_type not in SEARCH_PRICES:
        return jsonify({
            'success': False,
            'error': 'Invalid search type'
        }), 400
    
    # Check if Stripe is configured
    if not stripe.api_key or stripe.api_key == 'sk_test_your_secret_key_here':
        return jsonify({
            'success': False,
            'error': 'Payment system not configured. Please contact support.'
        }), 500
    
    price_pence = SEARCH_PRICES[search_type]
    price_display = f"£{price_pence / 100:.2f}"
    
    # Determine the search type label for display
    search_type_labels = {
        'name': 'Company Name Search',
        'number': 'Company Number Search',
        'address': 'Address Search',
        'director': 'Director Search'
    }
    
    try:
        # Get the base URL for redirects
        base_url = request.url_root.rstrip('/')
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': search_type_labels.get(search_type, 'Registry Search'),
                        'description': f'Search for: {search_value[:50]}{"..." if len(search_value) > 50 else ""}'
                    },
                    'unit_amount': price_pence,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{base_url}/search?session_id={{CHECKOUT_SESSION_ID}}&search_type={search_type}&search_value={requests.utils.quote(search_value)}',
            cancel_url=f'{base_url}/search?cancelled=true',
            metadata={
                'search_type': search_type,
                'search_value': search_value
            }
        )
        
        return jsonify({
            'success': True,
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        })
        
    except stripe.error.StripeError as e:
        return jsonify({
            'success': False,
            'error': f'Payment error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error creating checkout: {str(e)}'
        }), 500


def verify_stripe_payment(session_id, expected_search_type, expected_search_value):
    """
    Verify that a Stripe Checkout Session was paid and matches the search parameters.
    Returns (is_valid, error_message)
    """
    if not session_id:
        return False, "Payment required. Please complete checkout to search."
    
    # Check if session was already used (in-memory + database)
    if session_id in used_sessions or is_payment_used(session_id):
        return False, "This payment has already been used. Please make a new payment to search again."
    
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify payment was successful
        if session.payment_status != 'paid':
            return False, "Payment not completed. Please complete checkout to search."
        
        # Verify the search parameters match what was paid for
        metadata = session.metadata or {}
        paid_search_type = metadata.get('search_type', '')
        paid_search_value = metadata.get('search_value', '')
        
        if paid_search_type != expected_search_type:
            return False, "Payment was for a different search type. Please make a new payment."
        
        if paid_search_value.strip().lower() != expected_search_value.strip().lower():
            return False, "Payment was for a different search query. Please make a new payment."
        
        # Mark session as used (both in-memory and database for reliability)
        used_sessions.add(session_id)
        mark_payment_used(session_id)
        
        # Record the payment in the database (update status to 'used')
        price_pence = SEARCH_PRICES.get(paid_search_type, 100)
        record_payment(session_id, paid_search_type, paid_search_value, price_pence, 'used')
        
        return True, None
        
    except stripe.error.InvalidRequestError:
        return False, "Invalid payment session. Please try again."
    except stripe.error.StripeError as e:
        return False, f"Payment verification failed: {str(e)}"
    except Exception as e:
        return False, f"Error verifying payment: {str(e)}"


@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for searching properties"""
    data = request.get_json()
    search_type = data.get('search_type', 'number')  # 'number', 'name', 'address', or 'director'
    search_value = data.get('search_value', '').strip()
    session_id = data.get('session_id')  # Stripe Checkout Session ID
    
    if not search_value:
        return jsonify({
            'success': False,
            'error': 'Search value is required',
            'results': [],
            'count': 0,
            'suggestions': []
        })
    
    # Verify payment before executing search
    # Only require payment if Stripe is configured
    if stripe.api_key and stripe.api_key != 'sk_test_your_secret_key_here':
        is_valid, payment_error = verify_stripe_payment(session_id, search_type, search_value)
        if not is_valid:
            price_pence = SEARCH_PRICES.get(search_type, 100)
            return jsonify({
                'success': False,
                'error': payment_error,
                'payment_required': True,
                'price_pence': price_pence,
                'price_display': f'£{price_pence / 100:.2f}',
                'results': [],
                'count': 0,
                'suggestions': []
            })
    
    # Search by company number, name, address, or director
    if search_type == 'name':
        results, suggestions = search_properties_by_company_name(search_value)
        search_key = 'company_name'
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'suggestions': suggestions,
            'search_type': search_type,
            search_key: search_value
        })
    elif search_type == 'address':
        results = search_properties_by_address(search_value)
        suggestions = []
        search_key = 'address'
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'suggestions': suggestions,
            'search_type': search_type,
            search_key: search_value
        })
    elif search_type == 'director':
        results, directors_found, suggestions, error = search_properties_by_director(search_value)
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'results': [],
                'count': 0,
                'suggestions': suggestions,
                'directors_found': []
            })
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'suggestions': suggestions,
            'directors_found': directors_found,
            'search_type': search_type,
            'director_name': search_value
        })
    else:
        results = search_properties_by_company(search_value)
        suggestions = []
        search_key = 'company_number'
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'suggestions': suggestions,
            'search_type': search_type,
            search_key: search_value
        })


@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export search results as CSV"""
    data = request.get_json()
    search_type = data.get('search_type', 'number')
    search_value = data.get('search_value', '').strip()
    
    if not search_value:
        return jsonify({'success': False, 'error': 'Search value is required'}), 400
    
    # Search by company number, name, address, or director
    if search_type == 'name':
        results, _ = search_properties_by_company_name(search_value)
    elif search_type == 'address':
        results = search_properties_by_address(search_value)
    elif search_type == 'director':
        results, _, _, error = search_properties_by_director(search_value)
        if error:
            return jsonify({'success': False, 'error': error}), 400
    else:
        results = search_properties_by_company(search_value)
    
    if not results:
        return jsonify({'success': False, 'error': 'No results to export'}), 400
    
    # Create CSV in memory
    output = io.StringIO()
    fieldnames = [
        'title_number', 'tenure', 'property_address', 'district', 'county',
        'region', 'postcode', 'price_paid', 'proprietor_name',
        'company_registration_no', 'proprietorship_category', 'date_proprietor_added'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in results:
        writer.writerow({k: row.get(k, '') for k in fieldnames})
    
    output.seek(0)
    
    # Create response
    filename = f"properties_{search_type}_{search_value.replace(' ', '_')[:20]}.csv"
    response = app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
    
    return response


@app.route('/api/export/json', methods=['POST'])
def export_json():
    """Export search results as JSON"""
    data = request.get_json()
    search_type = data.get('search_type', 'number')
    search_value = data.get('search_value', '').strip()
    
    if not search_value:
        return jsonify({'success': False, 'error': 'Search value is required'}), 400
    
    # Search by company number, name, address, or director
    if search_type == 'name':
        results, _ = search_properties_by_company_name(search_value)
        directors_found = []
    elif search_type == 'address':
        results = search_properties_by_address(search_value)
        directors_found = []
    elif search_type == 'director':
        results, directors_found, _, error = search_properties_by_director(search_value)
        if error:
            return jsonify({'success': False, 'error': error}), 400
    else:
        results = search_properties_by_company(search_value)
        directors_found = []
    
    response_data = {
        'search_type': search_type,
        'search_value': search_value,
        'count': len(results),
        'properties': results
    }
    
    # Include directors info for director searches
    if search_type == 'director' and directors_found:
        response_data['directors_found'] = directors_found
    
    return jsonify(response_data)


@app.route('/api/reload', methods=['POST'])
def reload_data():
    """Reload data from CSV - disabled in production (serverless)"""
    if DATABASE_URL:
        return jsonify({
            'success': False,
            'error': 'Data reload is not available in production. Please use database migration tools.'
        }), 400
    
    try:
        import subprocess
        script_path = BASE_DIR / 'scripts' / 'load_data.py'
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Data reloaded successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to reload data',
                'output': result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Check if database exists (local development only)
    if not DATABASE_URL and not LOCAL_DATABASE_PATH.exists():
        print("Warning: Database not found. Please run scripts/load_data.py first.")
    
    app.run(debug=True, host='127.0.0.1', port=5000)

