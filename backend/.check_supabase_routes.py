#!/usr/bin/env python3
"""Check if Supabase routes are registered in the running server."""
import httpx
import json
import time

# Give the server a moment if it just started
time.sleep(1)

try:
    resp = httpx.get('http://127.0.0.1:8000/openapi.json')
    if resp.status_code != 200:
        print(f'Failed to get OpenAPI schema: {resp.status_code}')
        exit(1)
    
    schema = resp.json()
    paths = schema.get('paths', {})
    
    # Look for supabase paths
    supabase_paths = [p for p in paths.keys() if 'supabase' in p]
    
    if supabase_paths:
        print(f'✓ Found {len(supabase_paths)} supabase paths in OpenAPI:')
        for path in sorted(supabase_paths):
            print(f'  {path}')
    else:
        print(f'✗ No supabase paths found in OpenAPI schema')
        print(f'  Total paths: {len(paths)}')
        print(f'  All paths (first 20):')
        for path in sorted(paths.keys())[:20]:
            print(f'    {path}')
        
        # Now test with a raw HTTP request
        print('\n  Testing raw HTTP request...')
        resp2 = httpx.post('http://127.0.0.1:8000/api/supabase/fights', json={'external_id': 'test', 'metadata': {}})
        print(f'  POST /api/supabase/fights: {resp2.status_code}')
        if resp2.status_code != 404:
            print(f'  Response: {resp2.text}')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
