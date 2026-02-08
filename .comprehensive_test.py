#!/usr/bin/env python3
"""
Comprehensive test suite for Emergent backend.
Tests server health, Supabase integration, and key endpoints.
"""
import asyncio
import httpx
import json
import subprocess
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_section(title):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{title.center(60)}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_test(name, passed, details=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} {name}")
    if details:
        print(f"  {details}")

async def test_server_health():
    """Test 1: Server health check"""
    print_section("TEST 1: SERVER HEALTH")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/docs")
            health = resp.status_code == 200
            print_test("Server /docs endpoint", health, f"Status: {resp.status_code}")
            return health
    except Exception as e:
        print_test("Server /docs endpoint", False, f"Error: {e}")
        return False

async def test_supabase_health():
    """Test 2: Supabase connectivity"""
    print_section("TEST 2: SUPABASE CONNECTIVITY")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Test list fights (should work even if empty)
            resp = await client.get(f"{BASE_URL}/api/supabase/fights")
            health = resp.status_code == 200
            data = resp.json() if resp.status_code == 200 else {}
            count = data.get("count", 0) if isinstance(data, dict) else len(data.get("data", []))
            
            print_test("Supabase connectivity", health, f"Status: {resp.status_code}, Fights: {count}")
            return health
    except Exception as e:
        print_test("Supabase connectivity", False, f"Error: {e}")
        return False

async def test_supabase_crud():
    """Test 3: Supabase full CRUD workflow"""
    print_section("TEST 3: SUPABASE CRUD WORKFLOW")
    
    all_passed = True
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # CREATE fight
            fight_payload = {
                "external_id": f"test_comprehensive_{int(time.time())}",
                "metadata": {"test": "comprehensive", "timestamp": time.time()}
            }
            resp = await client.post(f"{BASE_URL}/api/supabase/fights", json=fight_payload)
            fight_created = resp.status_code == 200
            print_test("POST /api/supabase/fights (create)", fight_created, f"Status: {resp.status_code}")
            all_passed &= fight_created
            
            fight_id = None
            if fight_created:
                fight_data = resp.json().get("data", {})
                fight_id = fight_data.get("id")
                print(f"  Fight ID: {fight_id}")
            
            # READ fight
            if fight_id:
                resp = await client.get(f"{BASE_URL}/api/supabase/fights/{fight_id}")
                fight_read = resp.status_code == 200
                print_test("GET /api/supabase/fights/{fight_id} (read)", fight_read, f"Status: {resp.status_code}")
                all_passed &= fight_read
            
            # CREATE judgment
            if fight_id:
                judgment_payload = {
                    "fight_id": fight_id,
                    "judge": "test_judge",
                    "scores": {"round_1": 10, "round_2": 9, "round_3": 10}
                }
                resp = await client.post(f"{BASE_URL}/api/supabase/judgments", json=judgment_payload)
                judgment_created = resp.status_code == 200
                print_test("POST /api/supabase/judgments (create)", judgment_created, f"Status: {resp.status_code}")
                all_passed &= judgment_created
                
                judgment_id = None
                if judgment_created:
                    judgment_data = resp.json().get("data", {})
                    judgment_id = judgment_data.get("id")
            
            # READ judgments for fight
            if fight_id:
                resp = await client.get(f"{BASE_URL}/api/supabase/fights/{fight_id}/judgments")
                judgments_read = resp.status_code == 200
                count = resp.json().get("count", 0) if resp.status_code == 200 else 0
                print_test("GET /api/supabase/fights/{fight_id}/judgments (read)", judgments_read, f"Status: {resp.status_code}, Count: {count}")
                all_passed &= judgments_read
            
            return all_passed
    except Exception as e:
        print_test("Supabase CRUD workflow", False, f"Error: {e}")
        return False

async def test_key_endpoints():
    """Test 4: Key important endpoints"""
    print_section("TEST 4: KEY ENDPOINTS")
    
    endpoints_to_test = [
        ("GET /api/ping", "/api/ping"),
        ("GET /openapi.json (schema)", "/openapi.json"),
    ]
    
    all_passed = True
    async with httpx.AsyncClient(timeout=10) as client:
        for name, path in endpoints_to_test:
            try:
                resp = await client.get(f"{BASE_URL}{path}")
                passed = resp.status_code == 200
                print_test(name, passed, f"Status: {resp.status_code}")
                all_passed &= passed
            except Exception as e:
                print_test(name, False, f"Error: {e}")
                all_passed = False
    
    return all_passed

def test_scoring_engine():
    """Test 5: Scoring engine v3 tests"""
    print_section("TEST 5: SCORING ENGINE V3")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_scoring_engine_v3.py", "-v", "--tb=short"],
            cwd=".",
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse output for pass/fail count
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        
        if passed:
            # Extract test count from output
            if "passed" in output:
                lines = output.split('\n')
                for line in lines[-10:]:
                    if "passed" in line:
                        print_test("Scoring engine v3 tests", True, line.strip())
                        break
            else:
                print_test("Scoring engine v3 tests", True, "All tests passed")
        else:
            print_test("Scoring engine v3 tests", False, "Some tests failed")
            print(f"  Output: {output[-500:]}")
        
        return passed
    except subprocess.TimeoutExpired:
        print_test("Scoring engine v3 tests", False, "Test timeout")
        return False
    except Exception as e:
        print_test("Scoring engine v3 tests", False, f"Error: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print(f"{Colors.BLUE}")
    print(r"""
     _____ _   _ __  __ __  __ _____ ____  _____ _   _______
    / ____| \ | |  \/  |  \/  |  __ \|  _ \|_   _| | |  ______|
   | |  __| \| | |\/| | |\/| | |  | | |_) | | | | | | |__     
   | | |_ |     | |  | | |  | | |  | |  _ <  | | | | |  __|    
   | |__| |     | |  | | |  | | |__| | |_) | | | | |_| |       
    \_____|     |_|  |_|_|  |_|_____/|____/  |_|  \___/|_|       
                                                                  
    Comprehensive Test Suite - February 7, 2026
    """)
    print(f"{Colors.END}\n")
    
    results = {}
    
    # Test server health
    results["Server Health"] = await test_server_health()
    time.sleep(1)
    
    # Test Supabase connectivity
    results["Supabase Health"] = await test_supabase_health()
    time.sleep(1)
    
    # Test Supabase CRUD
    results["Supabase CRUD"] = await test_supabase_crud()
    time.sleep(1)
    
    # Test key endpoints
    results["Key Endpoints"] = await test_key_endpoints()
    time.sleep(1)
    
    # Test scoring engine (sync)
    results["Scoring Engine V3"] = test_scoring_engine()
    
    # Summary
    print_section("SUMMARY")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}✓{Colors.END}" if result else f"{Colors.RED}✗{Colors.END}"
        print(f"{status} {test_name}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} test suites passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}🎉 ALL TESTS PASSED 🎉{Colors.END}")
        return 0
    else:
        print(f"{Colors.YELLOW}⚠️  {total - passed} test suite(s) failed{Colors.END}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
