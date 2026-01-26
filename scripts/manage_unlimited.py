"""
Manage unlimited access for friends and family accounts.

Usage:
    python scripts/manage_unlimited.py grant user@example.com
    python scripts/manage_unlimited.py revoke user@example.com
    python scripts/manage_unlimited.py list
"""
import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()
load_dotenv('env.local')

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("Error: DATABASE_URL not set")
    sys.exit(1)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def grant_unlimited(email):
    """Grant unlimited access to a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id, email, is_unlimited FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
    user = cursor.fetchone()
    
    if not user:
        print(f"User '{email}' not found. They need to create an account first.")
        conn.close()
        return False
    
    if user[2]:  # is_unlimited
        print(f"User '{email}' already has unlimited access.")
        conn.close()
        return True
    
    cursor.execute("UPDATE users SET is_unlimited = TRUE WHERE id = %s", (user[0],))
    conn.commit()
    conn.close()
    
    print(f"✓ Granted unlimited access to '{email}'")
    return True


def revoke_unlimited(email):
    """Revoke unlimited access from a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, email, is_unlimited FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
    user = cursor.fetchone()
    
    if not user:
        print(f"User '{email}' not found.")
        conn.close()
        return False
    
    if not user[2]:  # is_unlimited
        print(f"User '{email}' doesn't have unlimited access.")
        conn.close()
        return True
    
    cursor.execute("UPDATE users SET is_unlimited = FALSE WHERE id = %s", (user[0],))
    conn.commit()
    conn.close()
    
    print(f"✓ Revoked unlimited access from '{email}'")
    return True


def list_unlimited():
    """List all users with unlimited access"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT email, credits, created_at, last_login 
        FROM users 
        WHERE is_unlimited = TRUE 
        ORDER BY email
    """)
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print("No users have unlimited access.")
        return
    
    print(f"\nUsers with unlimited access ({len(users)}):")
    print("-" * 60)
    for user in users:
        last_login = user[3].strftime('%Y-%m-%d %H:%M') if user[3] else 'Never'
        print(f"  {user[0]}")
        print(f"    Credits: {user[1]} | Last login: {last_login}")
    print("-" * 60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_unlimited()
    elif command == 'grant':
        if len(sys.argv) < 3:
            print("Usage: python scripts/manage_unlimited.py grant user@example.com")
            sys.exit(1)
        grant_unlimited(sys.argv[2])
    elif command == 'revoke':
        if len(sys.argv) < 3:
            print("Usage: python scripts/manage_unlimited.py revoke user@example.com")
            sys.exit(1)
        revoke_unlimited(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
