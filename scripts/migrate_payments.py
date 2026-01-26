"""
Migrate database to add payments table for Stripe integration
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

# Create payments table
print("Creating payments table...")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        stripe_session_id VARCHAR(255) UNIQUE NOT NULL,
        search_type VARCHAR(50) NOT NULL,
        search_value TEXT NOT NULL,
        amount_pence INTEGER NOT NULL,
        currency VARCHAR(10) DEFAULT 'gbp',
        status VARCHAR(50) DEFAULT 'pending',
        customer_email VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        used_at TIMESTAMP
    )
''')

# Create indexes
print("Creating indexes...")
cursor.execute('CREATE INDEX IF NOT EXISTS idx_stripe_session_id ON payments(stripe_session_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_status ON payments(status)')

conn.commit()
print('Payments table created successfully!')

# Verify table exists
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'payments'
    ORDER BY ordinal_position
""")
columns = cursor.fetchall()
print('\nTable columns:')
for col in columns:
    print(f'  - {col[0]}: {col[1]}')

conn.close()
print("\nMigration complete!")
