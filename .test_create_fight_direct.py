#!/usr/bin/env python3
"""Test Supabase fight creation with detailed error output."""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def test():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("✗ Missing SUPABASE_URL or SUPABASE_ANON_KEY")
        return
    
    print(f"Testing Supabase fight creation...")
    print(f"  URL: {url}/rest/v1")
    
    fight_data = {
        "external_id": "test_fight_001",
        "metadata": {"event": "demo"}
    }
    
    headers = {
        'Authorization': f'Bearer {key}',
        'apikey': key,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{url}/rest/v1/fights",
            headers=headers,
            json=fight_data
        )
        
        print(f"\nResponse Status: {resp.status_code}")
        print(f"Response Headers: {dict(resp.headers)}")
        print(f"Response Body: {resp.text}")
        
        if resp.status_code not in [200, 201]:
            print(f"\n✗ Failed to create fight (status {resp.status_code})")
            try:
                error_data = resp.json()
                print(f"Error details: {error_data}")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(test())
