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
import json
import time
import requests
import stripe
import bcrypt
import secrets
import resend
from pathlib import Path
from collections import defaultdict
from rapidfuzz import fuzz, process
from dotenv import load_dotenv
from datetime import datetime, timedelta
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from .env or env.local
load_dotenv()
load_dotenv('env.local')

app = Flask(__name__)

# Secret key for session management
_secret_key = os.environ.get('SECRET_KEY')
_is_production = os.environ.get('FLASK_ENV') == 'production'
if not _secret_key:
    if _is_production:
        raise RuntimeError("SECRET_KEY environment variable must be set in production (FLASK_ENV=production)!")
    # Development only: generate random key (sessions won't persist across restarts)
    _secret_key = secrets.token_hex(32)
    print("WARNING: SECRET_KEY not set. Using random key (sessions won't persist across restarts).")
app.secret_key = _secret_key
app.config['SESSION_COOKIE_SECURE'] = _is_production
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

# Google Analytics 4 Measurement ID (optional)
app.config['GA4_MEASUREMENT_ID'] = os.environ.get('GA4_MEASUREMENT_ID')

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

# ============================================
# RATE LIMITING CONFIGURATION
# ============================================

# In-memory rate limit store: {identifier: [(timestamp, count), ...]}
_rate_limit_store = defaultdict(list)

# Rate limit rules: endpoint_prefix -> (max_requests, window_seconds)
RATE_LIMIT_RULES = {
    '/api/search': (30, 60),           # 30 searches per minute
    '/api/auth/login': (10, 60),       # 10 login attempts per minute
    '/api/auth/register': (5, 60),     # 5 registrations per minute
    '/api/auth/magic-link': (5, 60),   # 5 magic link requests per minute
    '/api/create-checkout': (10, 60),  # 10 checkout attempts per minute
    '/api/export': (20, 60),           # 20 exports per minute
}

def get_client_identifier():
    """Get a unique identifier for rate limiting (IP + user ID if logged in)."""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip:
        ip = ip.split(',')[0].strip()
    user_id = session.get('user_id')
    if user_id:
        return f"user:{user_id}"
    return f"ip:{ip}"


def check_rate_limit(endpoint_prefix=None):
    """
    Check if the current request exceeds rate limits.
    Returns (is_allowed, retry_after_seconds).
    """
    if endpoint_prefix is None:
        endpoint_prefix = request.path

    # Find matching rule
    rule = None
    for prefix, limits in RATE_LIMIT_RULES.items():
        if endpoint_prefix.startswith(prefix):
            rule = limits
            break

    if not rule:
        return True, 0  # No rule = no limit

    max_requests, window_seconds = rule
    identifier = get_client_identifier()
    key = f"{identifier}:{endpoint_prefix}"
    now = time.time()
    window_start = now - window_seconds

    # Clean old entries and count recent ones
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > window_start]
    current_count = len(_rate_limit_store[key])

    if current_count >= max_requests:
        # Calculate retry-after
        oldest = min(_rate_limit_store[key]) if _rate_limit_store[key] else now
        retry_after = int(oldest + window_seconds - now) + 1
        return False, max(retry_after, 1)

    # Record this request
    _rate_limit_store[key].append(now)
    return True, 0


def rate_limit_response(retry_after):
    """Return a 429 Too Many Requests response."""
    response = jsonify({
        'success': False,
        'error': f'Too many requests. Please try again in {retry_after} seconds.',
        'retry_after': retry_after
    })
    response.status_code = 429
    response.headers['Retry-After'] = str(retry_after)
    return response

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
# NORMALIZATION HELPERS (Single Source of Truth)
# ============================================

def normalize_company_reg(value):
    """
    Normalize company registration number - SINGLE SOURCE OF TRUTH
    Used for both storing normalized data AND query parameters to ensure consistency.
    
    Normalizes: uppercase, removes spaces, hyphens, parentheses
    """
    if not value:
        return ''
    return value.strip().upper().replace('(', '').replace(')', '').replace(' ', '').replace('-', '')


def normalize_text_upper(value):
    """
    Normalize text to uppercase trimmed - for name/address searches
    """
    if not value:
        return ''
    return value.strip().upper()


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


def search_properties_by_company(company_number, page=1, per_page=50):
    """Search for properties owned by a company number with pagination"""
    if not company_number:
        return [], 0

    # Normalize company number using single source of truth
    company_number_normalized = normalize_company_reg(company_number)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = dict_cursor(conn)

    # Get total count first
    if DATABASE_URL:
        cursor.execute("SELECT COUNT(*) FROM proprietors WHERE company_reg_normalized = %s", (company_number_normalized,))
    else:
        cursor.execute("SELECT COUNT(*) FROM proprietors WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) = ?", (company_number_normalized,))
    total = cursor.fetchone()[0] if DATABASE_URL else cursor.fetchone()[0]

    # Query properties with matching company registration number using indexed normalized column
    if DATABASE_URL:
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
            WHERE pr.company_reg_normalized = %s
            ORDER BY p.property_address
            LIMIT %s OFFSET %s
        """, (company_number_normalized, per_page, offset))
    else:
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
            WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) = ?
            ORDER BY p.property_address
            LIMIT ? OFFSET ?
        """, (company_number_normalized, per_page, offset))

    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results], total


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


def search_properties_by_company_name(company_name, fuzzy_threshold=70, page=1, per_page=50):
    """Search for properties owned by a company name (partial match with fuzzy suggestions)"""
    if not company_name:
        return [], [], 0

    # Normalize company name using helper function
    company_name_normalized = normalize_text_upper(company_name)
    company_name_original = company_name.strip()
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = dict_cursor(conn)

    # Get total count first
    if DATABASE_URL:
        cursor.execute("SELECT COUNT(*) FROM proprietors pr INNER JOIN properties p ON p.id = pr.property_id WHERE pr.proprietor_name_upper LIKE %s", (f'%{company_name_normalized}%',))
    else:
        cursor.execute("SELECT COUNT(*) FROM proprietors pr INNER JOIN properties p ON p.id = pr.property_id WHERE UPPER(TRIM(pr.proprietor_name)) LIKE ?", (f'%{company_name_normalized}%',))
    total = cursor.fetchone()[0]

    # First, try exact/partial match using indexed normalized column
    if DATABASE_URL:
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
            WHERE pr.proprietor_name_upper LIKE %s
            ORDER BY pr.proprietor_name, p.property_address
            LIMIT %s OFFSET %s
        """, (f'%{company_name_normalized}%', per_page, offset))
    else:
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
            WHERE UPPER(TRIM(pr.proprietor_name)) LIKE ?
            ORDER BY pr.proprietor_name, p.property_address
            LIMIT ? OFFSET ?
        """, (f'%{company_name_normalized}%', per_page, offset))

    results = cursor.fetchall()
    conn.close()

    # If we have results, return them with no suggestions
    if results:
        return [dict(row) for row in results], [], total

    # If no results, perform fuzzy matching to find suggestions
    all_company_names = get_all_unique_company_names()

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

    return [], suggestions, 0


def search_properties_by_address(address_query, page=1, per_page=50):
    """Search for properties by address (partial match on property_address or postcode)"""
    if not address_query:
        return [], 0

    # Normalize address using helper function
    address_normalized = normalize_text_upper(address_query)
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = dict_cursor(conn)

    # Get total count
    if DATABASE_URL:
        cursor.execute("""
            SELECT COUNT(*) FROM properties p
            INNER JOIN proprietors pr ON p.id = pr.property_id
            WHERE p.property_address_upper LIKE %s OR p.postcode_upper LIKE %s
        """, (f'%{address_normalized}%', f'%{address_normalized}%'))
    else:
        cursor.execute("""
            SELECT COUNT(*) FROM properties p
            INNER JOIN proprietors pr ON p.id = pr.property_id
            WHERE UPPER(TRIM(p.property_address)) LIKE ? OR UPPER(TRIM(p.postcode)) LIKE ?
        """, (f'%{address_normalized}%', f'%{address_normalized}%'))
    total = cursor.fetchone()[0]

    # Search in property_address and postcode fields using indexed normalized columns
    if DATABASE_URL:
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
            WHERE p.property_address_upper LIKE %s
               OR p.postcode_upper LIKE %s
            ORDER BY p.property_address
            LIMIT %s OFFSET %s
        """, (f'%{address_normalized}%', f'%{address_normalized}%', per_page, offset))
    else:
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
            WHERE UPPER(TRIM(p.property_address)) LIKE ?
               OR UPPER(TRIM(p.postcode)) LIKE ?
            ORDER BY p.property_address
            LIMIT ? OFFSET ?
        """, (f'%{address_normalized}%', f'%{address_normalized}%', per_page, offset))

    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results], total


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
    
    # Step 2: For each officer, get their company appointments (PARALLELIZED)
    directors_found = []
    all_company_numbers = set()
    
    # Limit to first 15 individual officers to balance thoroughness with rate limits
    officers_to_process = officers[:15]
    
    # Parallelize API calls using ThreadPoolExecutor for faster execution
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all appointment fetch tasks
        future_to_officer = {
            executor.submit(get_officer_appointments, officer.get('links', {}).get('self', '')): officer
            for officer in officers_to_process
            if officer.get('links', {}).get('self', '')
        }
        
        # Process completed futures as they finish
        for future in as_completed(future_to_officer):
            officer = future_to_officer[future]
            try:
                appointments = future.result()
                
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
            except Exception as e:
                # Log error but continue processing other officers
                print(f"Error fetching appointments for officer {officer.get('name', 'unknown')}: {e}")
    
    if not all_company_numbers:
        # Found directors but no company appointments
        return [], directors_found, [], f"Found {len(officers)} matching directors but none have company appointments in the registry."
    
    # Step 3: Search our local database for properties owned by these companies
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    # Build query with multiple company numbers using normalized column
    placeholders = ','.join(['%s'] * len(all_company_numbers))
    company_list = [normalize_company_reg(cn) for cn in all_company_numbers]
    
    if DATABASE_URL:
        # PostgreSQL: use indexed normalized column
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
            WHERE pr.company_reg_normalized IN ({placeholders})
            ORDER BY pr.proprietor_name, p.property_address
            LIMIT 500
        """, company_list)
    else:
        # SQLite fallback: use function-based query
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
                  IN ({','.join(['?'] * len(company_list))})
            ORDER BY pr.proprietor_name, p.property_address
            LIMIT 500
        """, company_list)
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results], directors_found, [], None


# ============================================
# SEARCH HISTORY HELPERS
# ============================================

def record_search_history(user_id, search_type, search_value, result_count):
    """Record a search in the user's history."""
    if not user_id:
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if DATABASE_URL:
            cursor.execute("""
                INSERT INTO search_history (user_id, search_type, search_value, result_count)
                VALUES (%s, %s, %s, %s)
            """, (user_id, search_type, search_value[:200], result_count))
        else:
            cursor.execute("""
                INSERT INTO search_history (user_id, search_type, search_value, result_count)
                VALUES (?, ?, ?, ?)
            """, (user_id, search_type, search_value[:200], result_count))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error recording search history: {e}")


def get_search_history(user_id, limit=20):
    """Get recent search history for a user."""
    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        if DATABASE_URL:
            cursor.execute("""
                SELECT id, search_type, search_value, result_count, created_at
                FROM search_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT id, search_type, search_value, result_count, created_at
                FROM search_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"Error getting search history: {e}")
        return []


# ============================================
# RELATED COMPANIES & GROUP DETECTION HELPERS
# ============================================

def find_related_companies(company_reg_no):
    """
    Find companies related to the given company by shared registered address.
    Returns list of companies at the same address.
    """
    if not company_reg_no:
        return []

    company_reg_normalized = normalize_company_reg(company_reg_no)

    conn = get_db_connection()
    cursor = dict_cursor(conn)

    try:
        # Step 1: Get the registered address of this company
        if DATABASE_URL:
            cursor.execute("""
                SELECT DISTINCT address_line_1, address_line_2, address_line_3
                FROM proprietors
                WHERE company_reg_normalized = %s
                AND address_line_1 IS NOT NULL AND TRIM(address_line_1) != ''
                LIMIT 1
            """, (company_reg_normalized,))
        else:
            cursor.execute("""
                SELECT DISTINCT address_line_1, address_line_2, address_line_3
                FROM proprietors
                WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) = ?
                AND address_line_1 IS NOT NULL AND TRIM(address_line_1) != ''
                LIMIT 1
            """, (company_reg_normalized,))

        address = cursor.fetchone()
        if not address:
            conn.close()
            return []

        address_dict = dict(address) if hasattr(address, 'keys') else {
            'address_line_1': address[0], 'address_line_2': address[1], 'address_line_3': address[2]
        }

        addr1 = normalize_text_upper(address_dict.get('address_line_1', ''))
        if not addr1:
            conn.close()
            return []

        # Step 2: Find other companies at the same address
        if DATABASE_URL:
            cursor.execute("""
                SELECT DISTINCT
                    pr.proprietor_name,
                    pr.company_registration_no,
                    pr.address_line_1,
                    COUNT(DISTINCT p.id) as property_count
                FROM proprietors pr
                INNER JOIN properties p ON p.id = pr.property_id
                WHERE UPPER(TRIM(pr.address_line_1)) = %s
                AND pr.company_reg_normalized != %s
                AND pr.company_registration_no IS NOT NULL
                AND TRIM(pr.company_registration_no) != ''
                GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1
                ORDER BY property_count DESC
                LIMIT 20
            """, (addr1, company_reg_normalized))
        else:
            cursor.execute("""
                SELECT DISTINCT
                    pr.proprietor_name,
                    pr.company_registration_no,
                    pr.address_line_1,
                    COUNT(DISTINCT p.id) as property_count
                FROM proprietors pr
                INNER JOIN properties p ON p.id = pr.property_id
                WHERE UPPER(TRIM(pr.address_line_1)) = ?
                AND UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) != ?
                AND pr.company_registration_no IS NOT NULL
                AND TRIM(pr.company_registration_no) != ''
                GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1
                ORDER BY property_count DESC
                LIMIT 20
            """, (addr1, company_reg_normalized))

        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

    except Exception as e:
        print(f"Error finding related companies: {e}")
        conn.close()
        return []


def detect_company_group(company_reg_no):
    """
    Detect companies in the same corporate group by:
    1. Shared registered address
    2. Similar company names (same prefix/root)
    Returns a group structure.
    """
    if not company_reg_no:
        return {'companies': [], 'shared_address': None}

    company_reg_normalized = normalize_company_reg(company_reg_no)

    conn = get_db_connection()
    cursor = dict_cursor(conn)

    try:
        # Get the source company details
        if DATABASE_URL:
            cursor.execute("""
                SELECT DISTINCT pr.proprietor_name, pr.company_registration_no,
                       pr.address_line_1, pr.address_line_2,
                       COUNT(DISTINCT p.id) as property_count
                FROM proprietors pr
                INNER JOIN properties p ON p.id = pr.property_id
                WHERE pr.company_reg_normalized = %s
                GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1, pr.address_line_2
                LIMIT 1
            """, (company_reg_normalized,))
        else:
            cursor.execute("""
                SELECT DISTINCT pr.proprietor_name, pr.company_registration_no,
                       pr.address_line_1, pr.address_line_2,
                       COUNT(DISTINCT p.id) as property_count
                FROM proprietors pr
                INNER JOIN properties p ON p.id = pr.property_id
                WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) = ?
                GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1, pr.address_line_2
                LIMIT 1
            """, (company_reg_normalized,))

        source = cursor.fetchone()
        if not source:
            conn.close()
            return {'companies': [], 'shared_address': None}

        source_dict = dict(source) if hasattr(source, 'keys') else {
            'proprietor_name': source[0], 'company_registration_no': source[1],
            'address_line_1': source[2], 'address_line_2': source[3],
            'property_count': source[4]
        }

        group_companies = [source_dict]
        shared_address = source_dict.get('address_line_1', '')

        # Extract root name for fuzzy grouping (e.g. "ACME" from "ACME HOLDINGS LTD")
        source_name = source_dict.get('proprietor_name', '')
        # Get first meaningful word(s) as root
        name_words = source_name.upper().split()
        # Remove common suffixes
        suffixes = {'LTD', 'LIMITED', 'PLC', 'LLP', 'INC', 'CORPORATION', 'CORP', 'LLC', 'CO', 'GROUP', 'HOLDINGS'}
        root_words = [w for w in name_words if w not in suffixes and len(w) > 2]
        root_name = root_words[0] if root_words else ''

        if root_name and len(root_name) >= 3:
            # Find companies with similar names
            if DATABASE_URL:
                cursor.execute("""
                    SELECT DISTINCT pr.proprietor_name, pr.company_registration_no,
                           pr.address_line_1, pr.address_line_2,
                           COUNT(DISTINCT p.id) as property_count
                    FROM proprietors pr
                    INNER JOIN properties p ON p.id = pr.property_id
                    WHERE pr.proprietor_name_upper LIKE %s
                    AND pr.company_reg_normalized != %s
                    AND pr.company_registration_no IS NOT NULL
                    AND TRIM(pr.company_registration_no) != ''
                    GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1, pr.address_line_2
                    ORDER BY property_count DESC
                    LIMIT 15
                """, (f'%{root_name}%', company_reg_normalized))
            else:
                cursor.execute("""
                    SELECT DISTINCT pr.proprietor_name, pr.company_registration_no,
                           pr.address_line_1, pr.address_line_2,
                           COUNT(DISTINCT p.id) as property_count
                    FROM proprietors pr
                    INNER JOIN properties p ON p.id = pr.property_id
                    WHERE UPPER(TRIM(pr.proprietor_name)) LIKE ?
                    AND UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) != ?
                    AND pr.company_registration_no IS NOT NULL
                    AND TRIM(pr.company_registration_no) != ''
                    GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1, pr.address_line_2
                    ORDER BY property_count DESC
                    LIMIT 15
                """, (f'%{root_name}%', company_reg_normalized))

            related = cursor.fetchall()
            for r in related:
                r_dict = dict(r) if hasattr(r, 'keys') else {
                    'proprietor_name': r[0], 'company_registration_no': r[1],
                    'address_line_1': r[2], 'address_line_2': r[3],
                    'property_count': r[4]
                }
                # Check if name is genuinely related (fuzzy match)
                r_name = r_dict.get('proprietor_name', '')
                similarity = fuzz.WRatio(source_name, r_name)
                if similarity >= 50:
                    r_dict['similarity'] = round(similarity, 1)
                    r_dict['relation'] = 'name_match'
                    group_companies.append(r_dict)

        # Also find companies at the same registered address
        addr1 = normalize_text_upper(shared_address)
        if addr1:
            if DATABASE_URL:
                cursor.execute("""
                    SELECT DISTINCT pr.proprietor_name, pr.company_registration_no,
                           pr.address_line_1, pr.address_line_2,
                           COUNT(DISTINCT p.id) as property_count
                    FROM proprietors pr
                    INNER JOIN properties p ON p.id = pr.property_id
                    WHERE UPPER(TRIM(pr.address_line_1)) = %s
                    AND pr.company_reg_normalized != %s
                    AND pr.company_registration_no IS NOT NULL
                    AND TRIM(pr.company_registration_no) != ''
                    GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1, pr.address_line_2
                    ORDER BY property_count DESC
                    LIMIT 15
                """, (addr1, company_reg_normalized))
            else:
                cursor.execute("""
                    SELECT DISTINCT pr.proprietor_name, pr.company_registration_no,
                           pr.address_line_1, pr.address_line_2,
                           COUNT(DISTINCT p.id) as property_count
                    FROM proprietors pr
                    INNER JOIN properties p ON p.id = pr.property_id
                    WHERE UPPER(TRIM(pr.address_line_1)) = ?
                    AND UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) != ?
                    AND pr.company_registration_no IS NOT NULL
                    AND TRIM(pr.company_registration_no) != ''
                    GROUP BY pr.proprietor_name, pr.company_registration_no, pr.address_line_1, pr.address_line_2
                    ORDER BY property_count DESC
                    LIMIT 15
                """, (addr1, company_reg_normalized))

            addr_related = cursor.fetchall()
            existing_regs = {c.get('company_registration_no', '') for c in group_companies}
            for r in addr_related:
                r_dict = dict(r) if hasattr(r, 'keys') else {
                    'proprietor_name': r[0], 'company_registration_no': r[1],
                    'address_line_1': r[2], 'address_line_2': r[3],
                    'property_count': r[4]
                }
                if r_dict.get('company_registration_no', '') not in existing_regs:
                    r_dict['relation'] = 'address_match'
                    group_companies.append(r_dict)
                    existing_regs.add(r_dict.get('company_registration_no', ''))

        conn.close()
        return {
            'companies': group_companies,
            'shared_address': shared_address,
            'root_name': root_name
        }

    except Exception as e:
        print(f"Error detecting company group: {e}")
        conn.close()
        return {'companies': [], 'shared_address': None}


def build_network_graph(company_reg_no):
    """
    Build a network graph dataset showing relationships between
    a company, its properties, and related companies.
    Returns nodes and edges for vis.js visualization.
    """
    if not company_reg_no:
        return {'nodes': [], 'edges': []}

    company_reg_normalized = normalize_company_reg(company_reg_no)
    nodes = []
    edges = []
    node_ids = set()

    conn = get_db_connection()
    cursor = dict_cursor(conn)

    try:
        # Get the source company and its properties
        if DATABASE_URL:
            cursor.execute("""
                SELECT DISTINCT
                    pr.proprietor_name,
                    pr.company_registration_no,
                    pr.address_line_1,
                    p.property_address,
                    p.postcode,
                    p.title_number,
                    p.tenure
                FROM proprietors pr
                INNER JOIN properties p ON p.id = pr.property_id
                WHERE pr.company_reg_normalized = %s
                LIMIT 50
            """, (company_reg_normalized,))
        else:
            cursor.execute("""
                SELECT DISTINCT
                    pr.proprietor_name,
                    pr.company_registration_no,
                    pr.address_line_1,
                    p.property_address,
                    p.postcode,
                    p.title_number,
                    p.tenure
                FROM proprietors pr
                INNER JOIN properties p ON p.id = pr.property_id
                WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(pr.company_registration_no), '(', ''), ')', ''), ' ', ''), '-', '')) = ?
                LIMIT 50
            """, (company_reg_normalized,))

        properties = cursor.fetchall()
        if not properties:
            conn.close()
            return {'nodes': [], 'edges': []}

        # Add the company node
        first_prop = dict(properties[0]) if hasattr(properties[0], 'keys') else {
            'proprietor_name': properties[0][0], 'company_registration_no': properties[0][1],
            'address_line_1': properties[0][2]
        }

        company_node_id = f"company_{company_reg_normalized}"
        nodes.append({
            'id': company_node_id,
            'label': first_prop.get('proprietor_name', 'Unknown'),
            'type': 'company',
            'company_reg': company_reg_no,
            'address': first_prop.get('address_line_1', '')
        })
        node_ids.add(company_node_id)

        # Add property nodes
        for prop in properties:
            prop_dict = dict(prop) if hasattr(prop, 'keys') else {
                'property_address': prop[3], 'postcode': prop[4],
                'title_number': prop[5], 'tenure': prop[6]
            }
            prop_id = f"property_{prop_dict.get('title_number', '')}"
            if prop_id not in node_ids:
                addr = prop_dict.get('property_address', 'Unknown')
                # Truncate long addresses for display
                label = addr[:40] + '...' if len(addr) > 40 else addr
                nodes.append({
                    'id': prop_id,
                    'label': label,
                    'type': 'property',
                    'full_address': addr,
                    'postcode': prop_dict.get('postcode', ''),
                    'tenure': prop_dict.get('tenure', '')
                })
                node_ids.add(prop_id)
                edges.append({
                    'from': company_node_id,
                    'to': prop_id,
                    'label': 'owns'
                })

        # Find related companies (same address)
        related = find_related_companies(company_reg_no)
        for rel in related[:10]:  # Limit to 10 related companies in graph
            rel_reg = normalize_company_reg(rel.get('company_registration_no', ''))
            rel_node_id = f"company_{rel_reg}"
            if rel_node_id not in node_ids:
                nodes.append({
                    'id': rel_node_id,
                    'label': rel.get('proprietor_name', 'Unknown'),
                    'type': 'related_company',
                    'company_reg': rel.get('company_registration_no', ''),
                    'property_count': rel.get('property_count', 0)
                })
                node_ids.add(rel_node_id)
                edges.append({
                    'from': company_node_id,
                    'to': rel_node_id,
                    'label': 'same address',
                    'dashes': True
                })

        conn.close()
        return {'nodes': nodes, 'edges': edges}

    except Exception as e:
        print(f"Error building network graph: {e}")
        conn.close()
        return {'nodes': [], 'edges': []}


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


@app.route('/faq')
def faq():
    """FAQ page"""
    user = get_current_user()
    return render_template('faq.html', user=user)


@app.route('/about')
def about():
    """About page"""
    user = get_current_user()
    return render_template('about.html', user=user)


@app.route('/how-to-search-land-registry')
def how_to():
    """How-to guide page"""
    user = get_current_user()
    return render_template('how-to.html', user=user)


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
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/auth/register')
    if not allowed:
        return rate_limit_response(retry_after)

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
        if not token:
            return jsonify({'success': False, 'error': 'Failed to create login link. Please try again.'}), 500
        
        if not send_magic_link_email(email, token):
            return jsonify({'success': False, 'error': 'Failed to send email. Please try again or use password.'}), 500
        
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
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/auth/login')
    if not allowed:
        return rate_limit_response(retry_after)

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
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/auth/magic-link')
    if not allowed:
        return rate_limit_response(retry_after)

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
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/create-checkout')
    if not allowed:
        return rate_limit_response(retry_after)

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


@app.route('/api/search/directors', methods=['POST'])
def api_search_directors():
    """
    Stage 1: Search for directors by name (FREE - no credits required).
    Returns a list of matching individual directors from Companies House.
    User can then select one to view their properties (Stage 2).
    """
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/search')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    director_name = data.get('director_name', '').strip()

    if not director_name:
        return jsonify({
            'success': False,
            'error': 'Director name is required',
            'directors': []
        })

    if not COMPANIES_HOUSE_API_KEY or COMPANIES_HOUSE_API_KEY == 'your_api_key_here':
        return jsonify({
            'success': False,
            'error': 'Companies House API key not configured. Please add your API key to env.local',
            'directors': []
        })

    # Search for directors (no credits charged - this is just browsing)
    officers, api_error = search_directors_from_companies_house(director_name)

    if api_error:
        return jsonify({
            'success': False,
            'error': api_error,
            'directors': []
        })

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
        return jsonify({
            'success': False,
            'error': 'No individual directors found matching this name. Try searching by company name instead.',
            'directors': [],
            'suggestions': suggestions
        })

    # Format directors for display
    directors_list = []
    for officer in officers:
        # Format date of birth for display
        dob = officer.get('date_of_birth', {})
        dob_display = ''
        if dob:
            month = dob.get('month', '')
            year = dob.get('year', '')
            if month and year:
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December']
                month_name = month_names[int(month)] if 1 <= int(month) <= 12 else str(month)
                dob_display = f"{month_name} {year}"
            elif year:
                dob_display = str(year)

        # Format address for display
        address = officer.get('address', {})
        address_parts = []
        if address.get('premises'):
            address_parts.append(address['premises'])
        if address.get('address_line_1'):
            address_parts.append(address['address_line_1'])
        if address.get('locality'):
            address_parts.append(address['locality'])
        if address.get('postal_code'):
            address_parts.append(address['postal_code'])
        address_display = ', '.join(address_parts) if address_parts else ''

        directors_list.append({
            'name': officer.get('name', ''),
            'date_of_birth': dob_display,
            'address': address_display,
            'appointment_count': officer.get('appointment_count', 0),
            'officer_id': officer.get('links', {}).get('self', ''),
            'description': officer.get('description', '')
        })

    return jsonify({
        'success': True,
        'directors': directors_list,
        'count': len(directors_list),
        'search_term': director_name
    })


@app.route('/api/search/director-properties', methods=['POST'])
def api_search_director_properties():
    """
    Stage 2: Get properties for a specific director (REQUIRES credits/payment).
    Takes an officer_id and fetches their company appointments, then searches
    the Land Registry database for properties owned by those companies.
    """
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/search')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    officer_id = data.get('officer_id', '').strip()
    director_name = data.get('director_name', '').strip()
    session_id = data.get('session_id')  # Stripe session ID for payment
    use_credits = data.get('use_credits', True)

    if not officer_id:
        return jsonify({
            'success': False,
            'error': 'Officer ID is required',
            'results': [],
            'directors_found': []
        })

    # Get current user and check credits
    user = get_current_user()
    credit_cost = CREDIT_COSTS.get('director', 3)
    credits_used = False

    # Check if user has unlimited access
    if user and user.get('is_unlimited'):
        credits_used = True
    # Try to use credits if user is logged in
    elif user and use_credits:
        user_credits = get_user_credits(user['id'])
        if user_credits >= credit_cost:
            if deduct_credits(user['id'], credit_cost, 'director', f'Director search: {director_name[:50]}'):
                credits_used = True

    # If credits weren't used, verify payment
    if not credits_used:
        if stripe.api_key and stripe.api_key != 'sk_test_your_secret_key_here':
            is_valid, payment_error = verify_stripe_payment(session_id, 'director', director_name)
            if not is_valid:
                price_pence = SEARCH_PRICES.get('director', 300)
                return jsonify({
                    'success': False,
                    'error': payment_error if not user else 'Insufficient credits. Please add more credits or pay for this search.',
                    'payment_required': True,
                    'price_pence': price_pence,
                    'price_display': f'£{price_pence / 100:.2f}',
                    'credit_cost': credit_cost,
                    'user_credits': get_user_credits(user['id']) if user else 0,
                    'results': [],
                    'directors_found': []
                })

    # Get updated credits after potential deduction
    remaining_credits = get_user_credits(user['id']) if user else 0

    # Fetch company appointments for this officer
    appointments = get_officer_appointments(officer_id)

    if not appointments:
        return jsonify({
            'success': True,
            'results': [],
            'directors_found': [],
            'count': 0,
            'message': 'This director has no company appointments in the registry.',
            'credits_used': credits_used,
            'remaining_credits': remaining_credits
        })

    # Build directors_found list and collect company numbers
    directors_found = []
    all_company_numbers = set()

    for appt in appointments:
        company_num = appt.get('company_number', '').strip()
        if company_num:
            all_company_numbers.add(company_num)
            directors_found.append({
                'director_name': director_name,
                'company_number': company_num,
                'company_name': appt.get('company_name', ''),
                'officer_role': appt.get('officer_role', ''),
                'appointed_on': appt.get('appointed_on', ''),
                'resigned_on': appt.get('resigned_on', ''),
                'company_status': appt.get('company_status', '')
            })

    if not all_company_numbers:
        return jsonify({
            'success': True,
            'results': [],
            'directors_found': directors_found,
            'count': 0,
            'message': 'No valid company numbers found for this director.',
            'credits_used': credits_used,
            'remaining_credits': remaining_credits
        })

    # Search Land Registry database for properties owned by these companies using normalized column
    conn = get_db_connection()
    cursor = dict_cursor(conn)

    placeholders = ','.join(['%s'] * len(all_company_numbers))
    company_list = [normalize_company_reg(cn) for cn in all_company_numbers]

    if DATABASE_URL:
        # PostgreSQL: use indexed normalized column
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
            WHERE pr.company_reg_normalized IN ({placeholders})
            ORDER BY pr.proprietor_name, p.property_address
            LIMIT 500
        """, company_list)
    else:
        # SQLite fallback: use function-based query
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
                  IN ({','.join(['?'] * len(company_list))})
            ORDER BY pr.proprietor_name, p.property_address
            LIMIT 500
        """, company_list)

    results = cursor.fetchall()
    conn.close()

    return jsonify({
        'success': True,
        'results': [dict(row) for row in results],
        'directors_found': directors_found,
        'count': len(results),
        'search_type': 'director',
        'director_name': director_name,
        'credits_used': credits_used,
        'remaining_credits': remaining_credits
    })


@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for searching properties with pagination"""
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/search')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    search_type = data.get('search_type', 'number')  # 'number', 'name', 'address', or 'director'
    search_value = data.get('search_value', '').strip()
    session_id = data.get('session_id')  # Stripe Checkout Session ID
    use_credits = data.get('use_credits', True)  # Whether to use credits if available
    page = max(1, int(data.get('page', 1)))
    per_page = min(100, max(1, int(data.get('per_page', 50))))

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
    # Try to use credits first if user is logged in (only charge on first page)
    elif user and use_credits and page == 1:
        user_credits = get_user_credits(user['id'])
        if user_credits >= credit_cost:
            if deduct_credits(user['id'], credit_cost, search_type, f'Search: {search_value[:50]}'):
                credits_used = True
    elif page > 1:
        # Subsequent pages don't cost credits (search already paid for)
        credits_used = True

    # If credits weren't used, verify payment
    if not credits_used:
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

    # Build pagination metadata helper
    def make_pagination(total, page, per_page):
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }

    # Search by company number, name, address, or director
    if search_type == 'name':
        results, suggestions, total = search_properties_by_company_name(search_value, page=page, per_page=per_page)
        search_key = 'company_name'

        # Record search history on first page
        if page == 1 and user:
            record_search_history(user['id'], search_type, search_value, total)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'total': total,
            'pagination': make_pagination(total, page, per_page),
            'suggestions': suggestions,
            'search_type': search_type,
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
            search_key: search_value
        })
    elif search_type == 'address':
        results, total = search_properties_by_address(search_value, page=page, per_page=per_page)
        suggestions = []
        search_key = 'address'

        if page == 1 and user:
            record_search_history(user['id'], search_type, search_value, total)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'total': total,
            'pagination': make_pagination(total, page, per_page),
            'suggestions': suggestions,
            'search_type': search_type,
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
            search_key: search_value
        })
    elif search_type == 'director':
        results, directors_found, suggestions, error = search_properties_by_director(search_value)
        total = len(results)
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

        if page == 1 and user:
            record_search_history(user['id'], search_type, search_value, total)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'total': total,
            'pagination': make_pagination(total, page, per_page),
            'suggestions': suggestions,
            'directors_found': directors_found,
            'search_type': search_type,
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
            'director_name': search_value
        })
    else:
        results, total = search_properties_by_company(search_value, page=page, per_page=per_page)
        suggestions = []
        search_key = 'company_number'

        if page == 1 and user:
            record_search_history(user['id'], search_type, search_value, total)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'total': total,
            'pagination': make_pagination(total, page, per_page),
            'suggestions': suggestions,
            'search_type': search_type,
            'credits_used': credits_used,
            'remaining_credits': remaining_credits,
            search_key: search_value
        })


@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export search results as CSV"""
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/export')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    search_type = data.get('search_type', 'number')
    search_value = data.get('search_value', '').strip()

    if not search_value:
        return jsonify({'success': False, 'error': 'Search value is required'}), 400

    # Search by company number, name, address, or director (get all results for export)
    if search_type == 'name':
        results, _, _ = search_properties_by_company_name(search_value, per_page=10000)
    elif search_type == 'address':
        results, _ = search_properties_by_address(search_value, per_page=10000)
    elif search_type == 'director':
        results, _, _, error = search_properties_by_director(search_value)
        if error:
            return jsonify({'success': False, 'error': error}), 400
    else:
        results, _ = search_properties_by_company(search_value, per_page=10000)
    
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
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/export')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    search_type = data.get('search_type', 'number')
    search_value = data.get('search_value', '').strip()

    if not search_value:
        return jsonify({'success': False, 'error': 'Search value is required'}), 400

    # Search by company number, name, address, or director (get all results for export)
    if search_type == 'name':
        results, _, _ = search_properties_by_company_name(search_value, per_page=10000)
        directors_found = []
    elif search_type == 'address':
        results, _ = search_properties_by_address(search_value, per_page=10000)
        directors_found = []
    elif search_type == 'director':
        results, directors_found, _, error = search_properties_by_director(search_value)
        if error:
            return jsonify({'success': False, 'error': error}), 400
    else:
        results, _ = search_properties_by_company(search_value, per_page=10000)
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


# ============================================
# SEARCH HISTORY API
# ============================================

@app.route('/api/search/history', methods=['GET'])
@login_required
def api_search_history():
    """Get the current user's search history."""
    user = get_current_user()
    limit = min(50, max(1, int(request.args.get('limit', 20))))
    history = get_search_history(user['id'], limit=limit)

    # Convert datetime objects to strings for JSON serialization
    for entry in history:
        if entry.get('created_at') and hasattr(entry['created_at'], 'isoformat'):
            entry['created_at'] = entry['created_at'].isoformat()

    return jsonify({
        'success': True,
        'history': history,
        'count': len(history)
    })


# ============================================
# RELATED COMPANIES API
# ============================================

@app.route('/api/search/related-companies', methods=['POST'])
def api_related_companies():
    """Find companies related to a given company by shared registered address."""
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/search')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    company_reg = data.get('company_registration_no', '').strip()

    if not company_reg:
        return jsonify({'success': False, 'error': 'Company registration number is required', 'related': []})

    related = find_related_companies(company_reg)
    return jsonify({
        'success': True,
        'related': related,
        'count': len(related),
        'source_company': company_reg
    })


# ============================================
# COMPANY GROUP DETECTION API
# ============================================

@app.route('/api/search/company-group', methods=['POST'])
def api_company_group():
    """Detect corporate group structure for a given company."""
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/search')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    company_reg = data.get('company_registration_no', '').strip()

    if not company_reg:
        return jsonify({'success': False, 'error': 'Company registration number is required'})

    group = detect_company_group(company_reg)
    return jsonify({
        'success': True,
        'group': group,
        'company_count': len(group.get('companies', [])),
        'source_company': company_reg
    })


# ============================================
# NETWORK GRAPH DATA API
# ============================================

@app.route('/api/search/network-graph', methods=['POST'])
def api_network_graph():
    """Get network graph data (nodes and edges) for a company's ownership structure."""
    # Rate limiting
    allowed, retry_after = check_rate_limit('/api/search')
    if not allowed:
        return rate_limit_response(retry_after)

    data = request.get_json()
    company_reg = data.get('company_registration_no', '').strip()

    if not company_reg:
        return jsonify({'success': False, 'error': 'Company registration number is required'})

    graph = build_network_graph(company_reg)
    return jsonify({
        'success': True,
        'graph': graph,
        'node_count': len(graph.get('nodes', [])),
        'edge_count': len(graph.get('edges', []))
    })


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