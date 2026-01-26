"""
Flask Web Application for Property Lookup by Company Number
With User Account System and Credits
"""

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import psycopg2
import psycopg2.extras
import os
import csv
import io
import requests
import stripe
import bcrypt
import secrets
import resend
from pathlib import Path
from rapidfuzz import fuzz, process
from dotenv import load_dotenv
from datetime import datetime, timedelta
from functools import wraps

# Load environment variables from .env or env.local
load_dotenv()
load_dotenv('env.local')

app = Flask(__name__)

# Secret key for session management - MUST be set in production
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    _secret_key = 'dev-fallback-key-change-in-production-12345'
    print("WARNING: SECRET_KEY not set! Using fallback. Set SECRET_KEY in production!")
app.secret_key = _secret_key
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

# Resend API for emails
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Email sender address
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'noreply@landregistry.company')

# Base URL for links in emails
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

# Credit costs for different search types
CREDIT_COSTS = {
    'name': 1,      # 1 credit for company name search
    'number': 1,    # 1 credit for company number search
    'address': 1,   # 1 credit for address search
    'director': 3   # 3 credits for director search
}

# Initial credits for new users
SIGNUP_CREDITS = 10

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


# ============================================
# USER AUTHENTICATION HELPERS
# ============================================

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_token():
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)


def get_current_user():
    """Get the current logged-in user from session"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        
        if DATABASE_URL:
            cursor.execute("SELECT id, email, credits, is_unlimited, email_verified, created_at, last_login FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("SELECT id, email, credits, is_unlimited, email_verified, created_at, last_login FROM users WHERE id = ?", (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user) if hasattr(user, 'keys') else {
                'id': user[0], 'email': user[1], 'credits': user[2],
                'is_unlimited': user[3], 'email_verified': user[4], 'created_at': user[5], 'last_login': user[6]
            }
        return None
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None


def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            if request.is_json:
                return jsonify({'success': False, 'error': 'Authentication required', 'login_required': True}), 401
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated_function


def create_user(email, password=None):
    """Create a new user with initial credits"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = hash_password(password) if password else None
        
        if DATABASE_URL:
            cursor.execute("""
                INSERT INTO users (email, password_hash, credits, email_verified)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (email.lower(), password_hash, SIGNUP_CREDITS, password is not None))
            user_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO users (email, password_hash, credits, email_verified)
                VALUES (?, ?, ?, ?)
            """, (email.lower(), password_hash, SIGNUP_CREDITS, password is not None))
            user_id = cursor.lastrowid
        
        # Record the signup bonus in transactions
        if DATABASE_URL:
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, transaction_type, description)
                VALUES (%s, %s, %s, %s)
            """, (user_id, SIGNUP_CREDITS, 'signup_bonus', 'Welcome bonus - 10 free credits'))
        else:
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, transaction_type, description)
                VALUES (?, ?, ?, ?)
            """, (user_id, SIGNUP_CREDITS, 'signup_bonus', 'Welcome bonus - 10 free credits'))
        
        conn.commit()
        conn.close()
        return user_id
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


def get_user_by_email(email):
    """Get a user by email address"""
    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        
        if DATABASE_URL:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
        else:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user) if hasattr(user, 'keys') else None
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def update_user_last_login(user_id):
    """Update user's last login timestamp"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
        else:
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating last login: {e}")


def deduct_credits(user_id, amount, search_type, description=None):
    """Deduct credits from a user's account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user has enough credits
        if DATABASE_URL:
            cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("SELECT credits FROM users WHERE id = ?", (user_id,))
        
        result = cursor.fetchone()
        if not result or result[0] < amount:
            conn.close()
            return False
        
        # Deduct credits
        if DATABASE_URL:
            cursor.execute("UPDATE users SET credits = credits - %s WHERE id = %s", (amount, user_id))
        else:
            cursor.execute("UPDATE users SET credits = credits - ? WHERE id = ?", (amount, user_id))
        
        # Record transaction
        desc = description or f'{search_type.capitalize()} search'
        if DATABASE_URL:
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, transaction_type, search_type, description)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, -amount, 'search_used', search_type, desc))
        else:
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, transaction_type, search_type, description)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, -amount, 'search_used', search_type, desc))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deducting credits: {e}")
        return False


def get_user_credits(user_id):
    """Get user's current credit balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute("SELECT credits FROM users WHERE id = %s", (user_id,))
        else:
            cursor.execute("SELECT credits FROM users WHERE id = ?", (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        print(f"Error getting credits: {e}")
        return 0


def create_magic_link(user_id):
    """Create a magic link token for passwordless login"""
    try:
        token = generate_token()
        expires_at = datetime.now() + timedelta(minutes=15)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute("""
                INSERT INTO magic_links (user_id, token, expires_at)
                VALUES (%s, %s, %s)
            """, (user_id, token, expires_at))
        else:
            cursor.execute("""
                INSERT INTO magic_links (user_id, token, expires_at)
                VALUES (?, ?, ?)
            """, (user_id, token, expires_at))
        
        conn.commit()
        conn.close()
        return token
    except Exception as e:
        print(f"Error creating magic link: {e}")
        return None


def verify_magic_link(token):
    """Verify a magic link token and return user_id if valid"""
    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        
        if DATABASE_URL:
            cursor.execute("""
                SELECT user_id, expires_at, used_at FROM magic_links WHERE token = %s
            """, (token,))
        else:
            cursor.execute("""
                SELECT user_id, expires_at, used_at FROM magic_links WHERE token = ?
            """, (token,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return None, "Invalid or expired link"
        
        result_dict = dict(result) if hasattr(result, 'keys') else {
            'user_id': result[0], 'expires_at': result[1], 'used_at': result[2]
        }
        
        if result_dict['used_at']:
            conn.close()
            return None, "This link has already been used"
        
        if result_dict['expires_at'] < datetime.now():
            conn.close()
            return None, "This link has expired. Please request a new one."
        
        # Mark as used
        if DATABASE_URL:
            cursor.execute("UPDATE magic_links SET used_at = CURRENT_TIMESTAMP WHERE token = %s", (token,))
        else:
            cursor.execute("UPDATE magic_links SET used_at = CURRENT_TIMESTAMP WHERE token = ?", (token,))
        
        # Mark user email as verified
        if DATABASE_URL:
            cursor.execute("UPDATE users SET email_verified = TRUE WHERE id = %s", (result_dict['user_id'],))
        else:
            cursor.execute("UPDATE users SET email_verified = TRUE WHERE id = ?", (result_dict['user_id'],))
        
        conn.commit()
        conn.close()
        return result_dict['user_id'], None
    except Exception as e:
        print(f"Error verifying magic link: {e}")
        return None, "An error occurred"


def send_magic_link_email(email, token):
    """Send magic link email using Resend"""
    if not RESEND_API_KEY:
        print(f"Magic link for {email}: {BASE_URL}/auth/verify?token={token}")
        return True  # Return True for testing without email
    
    try:
        magic_url = f"{BASE_URL}/auth/verify?token={token}"
        
        resend.Emails.send({
            "from": EMAIL_FROM,
            "to": email,
            "subject": "Sign in to Corporate Land Registry",
            "html": f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                <h1 style="color: #09090b; font-size: 24px; margin-bottom: 24px;">Sign in to Corporate Land Registry</h1>
                <p style="color: #52525b; font-size: 16px; line-height: 24px; margin-bottom: 24px;">
                    Click the button below to sign in to your account. This link will expire in 15 minutes.
                </p>
                <a href="{magic_url}" style="display: inline-block; background-color: #09090b; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px;">
                    Sign In
                </a>
                <p style="color: #a1a1aa; font-size: 14px; margin-top: 32px;">
                    If you didn't request this email, you can safely ignore it.
                </p>
                <hr style="border: none; border-top: 1px solid #e4e4e7; margin: 32px 0;">
                <p style="color: #a1a1aa; font-size: 12px;">
                    Corporate Land Registry - landregistry.company
                </p>
            </div>
            """
        })
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


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
    user = get_current_user()
    return render_template('landing.html', user=user)


@app.route('/search')
def search():
    """Search page"""
    user = get_current_user()
    return render_template('search.html', user=user)


@app.route('/auth')
def auth_page():
    """Login/Register page"""
    # Redirect if already logged in
    if get_current_user():
        return redirect(url_for('search'))
    return render_template('auth.html')


@app.route('/auth/verify')
def verify_magic_link_route():
    """Verify magic link token and log user in"""
    token = request.args.get('token')
    if not token:
        return redirect(url_for('auth_page'))
    
    user_id, error = verify_magic_link(token)
    
    if error:
        return render_template('auth.html', error=error)
    
    # Log the user in
    session.permanent = True
    session['user_id'] = user_id
    update_user_last_login(user_id)
    
    return redirect(url_for('search'))


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Register a new user account"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    use_magic_link = data.get('use_magic_link', False)
    
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400
    
    # Check if user already exists
    existing_user = get_user_by_email(email)
    if existing_user:
        return jsonify({'success': False, 'error': 'An account with this email already exists. Please log in.'}), 400
    
    # Validate password if provided
    if password and len(password) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400
    
    # Create user
    if use_magic_link or not password:
        # Create user without password (magic link only)
        user_id = create_user(email, password=None)
        if not user_id:
            return jsonify({'success': False, 'error': 'Failed to create account. Please try again.'}), 500
        
        # Send magic link
        token = create_magic_link(user_id)
        if token:
            send_magic_link_email(email, token)
        
        return jsonify({
            'success': True,
            'message': 'Check your email for a sign-in link!',
            'magic_link_sent': True
        })
    else:
        # Create user with password
        user_id = create_user(email, password=password)
        if not user_id:
            return jsonify({'success': False, 'error': 'Failed to create account. Please try again.'}), 500
        
        # Log the user in
        session.permanent = True
        session['user_id'] = user_id
        update_user_last_login(user_id)
        
        return jsonify({
            'success': True,
            'message': f'Account created! You have {SIGNUP_CREDITS} free credits.',
            'user': {
                'email': email,
                'credits': SIGNUP_CREDITS
            }
        })


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Log in with email and password"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    
    user = get_user_by_email(email)
    
    if not user:
        return jsonify({'success': False, 'error': 'No account found with this email'}), 400
    
    if not user.get('password_hash'):
        # User registered with magic link only
        return jsonify({
            'success': False, 
            'error': 'This account uses passwordless login. Click "Send Magic Link" to sign in.',
            'needs_magic_link': True
        }), 400
    
    if not password:
        return jsonify({'success': False, 'error': 'Password is required'}), 400
    
    if not verify_password(password, user['password_hash']):
        return jsonify({'success': False, 'error': 'Incorrect password'}), 400
    
    # Log the user in
    session.permanent = True
    session['user_id'] = user['id']
    update_user_last_login(user['id'])
    
    return jsonify({
        'success': True,
        'message': 'Logged in successfully',
        'user': {
            'email': user['email'],
            'credits': user['credits']
        }
    })


@app.route('/api/auth/magic-link', methods=['POST'])
def api_request_magic_link():
    """Request a magic link for passwordless login"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    
    user = get_user_by_email(email)
    
    if not user:
        # Create a new user for magic link
        user_id = create_user(email, password=None)
        if not user_id:
            return jsonify({'success': False, 'error': 'Failed to create account. Please try again.'}), 500
    else:
        user_id = user['id']
    
    # Create and send magic link
    token = create_magic_link(user_id)
    if not token:
        return jsonify({'success': False, 'error': 'Failed to create login link. Please try again.'}), 500
    
    if not send_magic_link_email(email, token):
        return jsonify({'success': False, 'error': 'Failed to send email. Please try again.'}), 500
    
    return jsonify({
        'success': True,
        'message': 'Check your email for a sign-in link!'
    })


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Log out the current user"""
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@app.route('/api/auth/me', methods=['GET'])
def api_get_current_user():
    """Get the current logged-in user's info"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'logged_in': False}), 401
    
    return jsonify({
        'success': True,
        'logged_in': True,
        'user': {
            'email': user['email'],
            'credits': user['credits'],
            'is_unlimited': user.get('is_unlimited', False),
            'email_verified': user['email_verified']
        }
    })


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
    use_credits = data.get('use_credits', True)  # Whether to use credits if available
    
    if not search_value:
        return jsonify({
            'success': False,
            'error': 'Search value is required',
            'results': [],
            'count': 0,
            'suggestions': []
        })
    
    # Get current user and check credits
    user = get_current_user()
    credit_cost = CREDIT_COSTS.get(search_type, 1)
    credits_used = False
    
    # Check if user has unlimited access (friends/family)
    if user and user.get('is_unlimited'):
        credits_used = True  # Unlimited users don't need credits
    # Try to use credits first if user is logged in
    elif user and use_credits:
        user_credits = get_user_credits(user['id'])
        if user_credits >= credit_cost:
            # Deduct credits
            if deduct_credits(user['id'], credit_cost, search_type, f'Search: {search_value[:50]}'):
                credits_used = True
    
    # If credits weren't used, verify payment
    if not credits_used:
        # Verify payment before executing search
        # Only require payment if Stripe is configured
        if stripe.api_key and stripe.api_key != 'sk_test_your_secret_key_here':
            is_valid, payment_error = verify_stripe_payment(session_id, search_type, search_value)
            if not is_valid:
                price_pence = SEARCH_PRICES.get(search_type, 100)
                return jsonify({
                    'success': False,
                    'error': payment_error if not user else 'Insufficient credits. Please add more credits or pay for this search.',
                    'payment_required': True,
                    'price_pence': price_pence,
                    'price_display': f'£{price_pence / 100:.2f}',
                    'credit_cost': credit_cost,
                    'user_credits': get_user_credits(user['id']) if user else 0,
                    'results': [],
                    'count': 0,
                    'suggestions': []
                })
    
    # Get updated credits after potential deduction
    remaining_credits = get_user_credits(user['id']) if user else 0
    
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
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
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
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
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
                'directors_found': [],
                'credits_used': credits_used,
                'remaining_credits': remaining_credits
            })
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'suggestions': suggestions,
            'directors_found': directors_found,
            'search_type': search_type,
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
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
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
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
