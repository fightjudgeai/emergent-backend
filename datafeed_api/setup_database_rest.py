"""
Database Setup Script using Supabase REST API
Runs the SQL migration via Supabase Management API
"""

import os
import requests
from dotenv import load_dotenv
import sys

load_dotenv()


def run_migration():
    """Run the database migration via Supabase REST API"""
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not service_key:
        print("❌ ERROR: SUPABASE_URL or SUPABASE_KEY not set in .env file")
        sys.exit(1)
    
    print(f"🔗 Connecting to Supabase...")
    print(f"URL: {supabase_url}")
    
    # Read migration file
    migration_path = os.path.join(os.path.dirname(__file__), 'migrations', '001_initial_schema.sql')
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    # Split SQL into individual statements (rough split by semicolons outside strings)
    # For safety, we'll execute the whole thing as one transaction
    
    try:
        # Use Supabase REST API to execute SQL
        # The endpoint is: POST /rest/v1/rpc/exec_sql
        
        # First, let's try using PostgREST directly
        headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json'
        }
        
        print("📄 Executing migration SQL via Supabase...")
        
        # We'll need to use the SQL editor approach or create a custom function
        # For now, let's output instructions
        print("\n" + "="*70)
        print("⚠️  MANUAL SETUP REQUIRED")
        print("="*70)
        print("\nSince direct SQL execution requires Supabase Management API access,")
        print("please follow these steps:\n")
        print("1. Open Supabase SQL Editor:")
        print(f"   {supabase_url.replace('https://', 'https://supabase.com/dashboard/project/')}/sql/new")
        print("\n2. Copy and paste the SQL from:")
        print(f"   {migration_path}")
        print("\n3. Click 'Run' to execute the migration")
        print("\n4. The migration will create all tables and seed sample data")
        print("\n" + "="*70)
        
        # Read the migration file and display first few lines
        print("\n📄 MIGRATION SQL (first 50 lines):")
        print("-" * 70)
        with open(migration_path, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:50], 1):
                print(f"{i:3d} | {line.rstrip()}")
        
        if len(lines) > 50:
            print(f"... ({len(lines) - 50} more lines)")
        
        print("-" * 70)
        print(f"\n✅ Full SQL file location: {migration_path}")
        print("\nAfter running the migration in Supabase, you can start the API server.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
