"""
Database Setup Script (Synchronous)
Uses psycopg2 for direct PostgreSQL connection
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

load_dotenv()


def get_connection_params():
    """Parse DATABASE_URL and return connection parameters"""
    supabase_url = os.getenv('SUPABASE_URL')
    project_ref = supabase_url.split('//')[1].split('.')[0]
    password = os.getenv('DATABASE_URL').split(':')[3].split('@')[0]
    
    # Try different connection formats
    connection_options = [
        {
            'host': f'db.{project_ref}.supabase.co',
            'port': 5432,
            'dbname': 'postgres',
            'user': 'postgres',
            'password': password,
            'sslmode': 'require'
        },
        {
            'host': f'{project_ref}.supabase.co',
            'port': 5432,
            'dbname': 'postgres',
            'user': 'postgres',
            'password': password,
            'sslmode': 'require'
        }
    ]
    
    return connection_options


def run_migration():
    """Run the database migration"""
    
    print("🔗 Connecting to Supabase PostgreSQL...")
    
    connection_options = get_connection_params()
    conn = None
    
    for i, params in enumerate(connection_options, 1):
        try:
            print(f"\nAttempt {i}: Connecting to {params['host']}...")
            conn = psycopg2.connect(**params)
            print("✅ Connected successfully!")
            break
        except Exception as e:
            print(f"❌ Failed: {e}")
            if i == len(connection_options):
                print("\n" + "="*70)
                print("⚠️  Unable to connect directly to Supabase")
                print("="*70)
                print("\nPlease use the Supabase SQL Editor to run the migration:")
                print(f"1. Go to: {os.getenv('SUPABASE_URL').replace('https://', 'https://supabase.com/dashboard/project/')}/sql/new")
                print(f"2. Copy contents from: /app/datafeed_api/migrations/001_initial_schema.sql")
                print("3. Paste and click 'Run'\n")
                return False
    
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Read migration file
        migration_path = os.path.join(os.path.dirname(__file__), 'migrations', '001_initial_schema.sql')
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        print("\n📄 Running migration: 001_initial_schema.sql")
        
        # Execute migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration completed successfully")
        
        # Seed sample data
        print("\n🌱 Seeding sample data...")
        cursor.execute("SELECT seed_sample_data();")
        conn.commit()
        
        # Get API keys
        cursor.execute("""
            SELECT name, api_key, scope 
            FROM api_clients 
            ORDER BY scope
        """)
        
        api_keys = cursor.fetchall()
        
        print("\n" + "="*70)
        print("🔑 TEST API KEYS GENERATED:")
        print("="*70)
        for key in api_keys:
            print(f"  {key[2]:20s} | {key[0]:25s}")
            print(f"  Key: {key[1]}")
            print()
        print("="*70)
        print("\n✅ Database setup complete!")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.errors.DuplicateTable as e:
        print("⚠️  Tables already exist. Skipping migration.")
        print("💡 To reset database, drop tables manually in Supabase SQL Editor")
        conn.rollback()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
