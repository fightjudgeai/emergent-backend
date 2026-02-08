import json
import sys
import traceback
import httpx


BASE = "http://127.0.0.1:8000/api/v1/supabase"


def main():
    try:
        client = httpx.Client(timeout=10)

        print("TEST: POST /fights")
        payload = {"external_id": "smoke-1", "metadata": {"note": "smoke test"}}
        resp = client.post(f"{BASE}/fights", json=payload)
        print(resp.status_code)
        print(resp.text)

        if resp.status_code == 200:
            data = resp.json().get("data", {})
            fight_id = data.get("id")
            if fight_id:
                print(f"Created fight id: {fight_id}")
                print("TEST: GET /fights/{fight_id}")
                r2 = client.get(f"{BASE}/fights/{fight_id}")
                print(r2.status_code)
                print(r2.text)

        print("TEST: GET /fights (list)")
        r3 = client.get(f"{BASE}/fights?limit=5")
        print(r3.status_code)
        print(r3.text)

    except Exception:
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
