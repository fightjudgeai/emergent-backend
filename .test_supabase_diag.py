#!/usr/bin/env python3
"""Detailed Supabase client diagnostics."""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def test():
    # Check environment variables
    print("Environment Variables:")
    print(f"  SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')[:50]}...")
    print(f"  SUPABASE_ANON_KEY: {os.getenv('SUPABASE_ANON_KEY', 'NOT SET')[:30]}...")
    print(f"  SUPABASE_SERVICE_ROLE_KEY: {os.getenv('SUPABASE_SERVICE_ROLE_KEY', 'NOT SET')[:30]}...")
    
    print("\nImporting supabase_client...")
    try:
        import supabase_client
        print("✓ supabase_client imported successfully")
        
        # Try to initialize
        await supabase_client.init_supabase()
        print("✓ init_supabase() called")
        
        # Try health check with detailed error
        print("\nAttempting health check...")
        import httpx
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        
        if url and key:
            print(f"  URL: {url}")
            print(f"  Key: {key[:30]}...")
            
            async with httpx.AsyncClient() as client:
                headers = {
                    'Authorization': f'Bearer {key}',
                    'apikey': key,
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal'
                }
                
                rest_url = f"{url}/rest/v1"
                resp = await client.get(f"{rest_url}/fights?select=id&limit=1", headers=headers)
                print(f"  Response: {resp.status_code}")
                print(f"  Body: {resp.text[:200]}")
        else:
            print("  ERROR: Missing SUPABASE_URL or SUPABASE_ANON_KEY")
            
    except Exception as e:
        import traceback
        print(f"✗ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
