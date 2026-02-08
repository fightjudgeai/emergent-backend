#!/usr/bin/env python3
"""Quick test of v1 endpoints"""
import httpx
import asyncio
import json

async def test():
    async with httpx.AsyncClient() as client:
        # Test v1/supabase/health
        r1 = await client.get('http://127.0.0.1:8000/api/v1/supabase/health')
        print(f"GET /api/v1/supabase/health: {r1.status_code}")
        if r1.status_code == 200:
            print(json.dumps(r1.json(), indent=2))
        else:
            print(f"  Error: {r1.text[:100]}")
        
        # Test v1/supabase/fights list
        r2 = await client.get('http://127.0.0.1:8000/api/v1/supabase/fights')
        print(f"\nGET /api/v1/supabase/fights: {r2.status_code}")
        if r2.status_code == 200:
            data = r2.json()
            print(f"  Count: {data.get('count', 0)}")
        else:
            print(f"  Error: {r2.text[:100]}")
        
        # Test v1/supabase/fights create
        r3 = await client.post('http://127.0.0.1:8000/api/v1/supabase/fights', json={
            "external_id": "test_v1",
            "metadata": {"test": "data"}
        })
        print(f"\nPOST /api/v1/supabase/fights: {r3.status_code}")
        if r3.status_code in [200, 201]:
            print(f"  Fight created: {r3.json().get('data', {}).get('id', 'N/A')[:8]}...")
        else:
            print(f"  Error: {r3.text[:100]}")

asyncio.run(test())
