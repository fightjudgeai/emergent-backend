#!/usr/bin/env python3
"""Smoke test Supabase endpoints."""
import httpx
import json
import asyncio

BASE_URL = "http://127.0.0.1:8000"

async def test_supabase_endpoints():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # Test 1: Create a fight
            print("=" * 50)
            print("TEST 1: POST /api/supabase/fights")
            print("=" * 50)
            fight_payload = {
                "external_id": "test_fight_001",
                "metadata": {"event": "demo", "timestamp": "2026-02-07", "location": "Vegas", "fighters": ["Fighter A", "Fighter B"]}
            }
            resp = await client.post(
                f"{BASE_URL}/api/supabase/fights",
                json=fight_payload
            )
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
            fight_data = None
            if resp.status_code in (200, 201):
                try:
                    resp_json = resp.json()
                    fight_data = resp_json.get("data", resp_json)  # Handle both wrapped and unwrapped responses
                    print(f"Fight created: {json.dumps(fight_data, indent=2)}")
                except:
                    pass

            # Test 2: Get all fights
            print("\n" + "=" * 50)
            print("TEST 2: GET /api/supabase/fights (list all)")
            print("=" * 50)
            resp = await client.get(f"{BASE_URL}/api/supabase/fights")
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")

            # Test 3: Create judgment (requires fight_id from response)
            if fight_data and "id" in fight_data:
                fight_id = fight_data["id"]
                print("\n" + "=" * 50)
                print("TEST 3: POST /api/supabase/judgments")
                print("=" * 50)
                judgment_payload = {
                    "fight_id": fight_id,
                    "judge": "judge_001",
                    "scores": {"round_1": 10, "round_2": 9, "round_3": 10}
                }
                resp = await client.post(
                    f"{BASE_URL}/api/supabase/judgments",
                    json=judgment_payload
                )
                print(f"Status: {resp.status_code}")
                print(f"Body: {resp.text}")

                # Test 4: Get judgments for fight
                print("\n" + "=" * 50)
                print("TEST 4: GET /api/supabase/fights/{fight_id}/judgments")
                print("=" * 50)
                resp = await client.get(f"{BASE_URL}/api/supabase/fights/{fight_id}/judgments")
                print(f"Status: {resp.status_code}")
                print(f"Body: {resp.text}")
            else:
                print("\n(Skipping judgment tests - no fight_id from creation response)")

            print("\n" + "=" * 50)
            print("SMOKE TESTS COMPLETE")
            print("=" * 50)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase_endpoints())
