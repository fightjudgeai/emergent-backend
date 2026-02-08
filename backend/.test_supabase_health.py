#!/usr/bin/env python3
"""Test Supabase client connectivity and auth."""
import asyncio
from supabase_client import check_supabase_health

async def test():
    result = await check_supabase_health()
    print(f"Supabase Health Check: {result}")

if __name__ == "__main__":
    asyncio.run(test())
