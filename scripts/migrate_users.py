"""
Migrate database to add user account system tables
- users: Store user accounts with email, password hash, and credits
- magic_links: Store passwordless login tokens
- credit_transactions: Track credit usage and purchases
- password_reset_tokens: Store password reset tokens
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv('env.local')

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("Error: DATABASE_URL not set")
    exit(1)

print(f"Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Create users table
print("Creating users table...")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255),
        credits INTEGER DEFAULT 10,
        is_unlimited BOOLEAN DEFAULT FALSE,
        email_verified BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
''')

# Add is_unlimited column if it doesn't exist (for existing databases)
print("Ensuring is_unlimited column exists...")
try:
    cursor.execute('''
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_unlimited BOOLEAN DEFAULT FALSE
    ''')
except Exception as e:
    print(f"Note: {e}")

# Create magic_links table
print("Creating magic_links table...")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS magic_links (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        token VARCHAR(255) UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP
    )
''')

# Create credit_transactions table
print("Creating credit_transactions table...")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS credit_transactions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        amount INTEGER NOT NULL,
        transaction_type VARCHAR(50) NOT NULL,
        search_type VARCHAR(50),
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Create password_reset_tokens table
print("Creating password_reset_tokens table...")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        token VARCHAR(255) UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP
    )
''')

# Create indexes
print("Creating indexes...")
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_magic_links_token ON magic_links(token)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_magic_links_user_id ON magic_links(user_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token)')

conn.commit()
print('User tables created successfully!')

# Verify tables exist
tables = ['users', 'magic_links', 'credit_transactions', 'password_reset_tokens']
for table in tables:
    cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    print(f'\n{table} columns:')
    for col in columns:
        print(f'  - {col[0]}: {col[1]}')

conn.close()
print("\nMigration complete!")
