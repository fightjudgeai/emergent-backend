#!/usr/bin/env python3
"""Test supabase_routes import."""

try:
    from supabase_routes import supabase_router
    print('✓ supabase_routes imported successfully')
    print(f'Router: {supabase_router}')
    print(f'Routes ({len(supabase_router.routes)} total):')
    for route in supabase_router.routes:
        path = getattr(route, 'path', 'unknown')
        methods = getattr(route, 'methods', set())
        print(f'  {methods if methods else "NO_METHOD"} {path}')
except Exception as e:
    import traceback
    print(f'✗ Failed to import supabase_routes: {e}')
    traceback.print_exc()
