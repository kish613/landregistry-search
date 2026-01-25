import psycopg2
from dotenv import load_dotenv
import os

load_dotenv('env.local')

conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
tables = cur.fetchall()
print('Tables:', [t[0] for t in tables])

for table in ['properties', 'proprietors']:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f'{table}: {count:,} rows')
    except Exception as e:
        print(f'{table}: does not exist or error - {e}')

conn.close()
