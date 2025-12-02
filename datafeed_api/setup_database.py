"""
Database Setup Script
Runs the SQL migration to set up the Supabase database schema
"""

import asyncio
import asyncpg
from dotenv import load_dotenv
import os
import sys

load_dotenv()


async def run_migration():
    """Run the database migration"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env file")
        sys.exit(1)
    
    print(f"🔗 Connecting to database...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # Read migration file
        migration_path = os.path.join(os.path.dirname(__file__), 'migrations', '001_initial_schema.sql')
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        print("📄 Running migration: 001_initial_schema.sql")
        
        # Execute migration
        await conn.execute(migration_sql)
        
        print("✅ Migration completed successfully")
        
        # Optionally seed sample data
        print("\n🌱 Seeding sample data...")
        await conn.execute("SELECT seed_sample_data();")
        
        # Get API keys
        api_keys = await conn.fetch("""
            SELECT name, api_key, scope 
            FROM api_clients 
            ORDER BY scope
        """)
        
        print("\n" + "="*60)
        print("🔑 TEST API KEYS GENERATED:")
        print("="*60)
        for key in api_keys:
            print(f"  {key['scope']:20s} | {key['name']:25s}")
            print(f"  Key: {key['api_key']}")
            print()
        print("="*60)
        print("\n✅ Database setup complete!")
        
        await conn.close()
        
    except asyncpg.exceptions.DuplicateTableError:
        print("⚠️  Tables already exist. Skipping migration.")
        print("💡 To reset database, drop tables manually in Supabase SQL Editor")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_migration())
