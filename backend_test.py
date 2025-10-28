import requests
import sys
import json
from datetime import datetime

class CombatJudgingAPITester:
    def __init__(self, base_url="https://ringside-tech.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            
            result = {
                'test': name,
                'success': success,
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'url': url
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    result['response'] = response.json()
                except:
                    result['response'] = response.text[:200]
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                result['error'] = response.text[:200]

            self.results.append(result)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                'test': name,
                'success': False,
                'error': str(e),
                'url': url
            }
            self.results.append(result)
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_status_endpoints(self):
        """Test status check endpoints"""
        # Test POST status
        status_data = {"client_name": f"test_client_{datetime.now().strftime('%H%M%S')}"}
        success, response = self.run_test("Create Status Check", "POST", "status", 200, status_data)
        
        if success:
            # Test GET status
            self.run_test("Get Status Checks", "GET", "status", 200)
        
        return success

    def test_calculate_score_endpoint(self):
        """Test the main scoring endpoint with sample data"""
        # Sample event data for testing
        sample_events = [
            {
                "bout_id": "test_bout_123",
                "round_num": 1,
                "fighter": "fighter1",
                "event_type": "KD",
                "timestamp": 30.0,
                "metadata": {"severity": "hard"}
            },
            {
                "bout_id": "test_bout_123",
                "round_num": 1,
                "fighter": "fighter1",
                "event_type": "ISS Head",
                "timestamp": 45.0,
                "metadata": {"power_strike": True}
            },
            {
                "bout_id": "test_bout_123",
                "round_num": 1,
                "fighter": "fighter2",
                "event_type": "Takedown",
                "timestamp": 60.0,
                "metadata": {"immediate_pass": True}
            },
            {
                "bout_id": "test_bout_123",
                "round_num": 1,
                "fighter": "fighter2",
                "event_type": "Submission Attempt",
                "timestamp": 90.0,
                "metadata": {"depth": "tight", "duration": 15}
            }
        ]

        score_request = {
            "bout_id": "test_bout_123",
            "round_num": 1,
            "events": sample_events,
            "round_duration": 300
        }

        success, response = self.run_test("Calculate Score", "POST", "calculate-score", 200, score_request)
        
        if success and response:
            print(f"   ✅ Score calculation successful")
            print(f"   Fighter 1 Score: {response.get('fighter1_score', {}).get('final_score', 'N/A')}")
            print(f"   Fighter 2 Score: {response.get('fighter2_score', {}).get('final_score', 'N/A')}")
            print(f"   Score Gap: {response.get('score_gap', 'N/A')}")
            print(f"   Gap Label: {response.get('gap_label', 'N/A')}")
            
            # Validate response structure
            required_fields = ['bout_id', 'round_num', 'fighter1_score', 'fighter2_score', 'score_gap', 'gap_label']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in response: {missing_fields}")
                return False
            
            # Validate subscores
            for fighter_key in ['fighter1_score', 'fighter2_score']:
                fighter_score = response.get(fighter_key, {})
                subscores = fighter_score.get('subscores', {})
                expected_subscores = ['KD', 'ISS', 'GCQ', 'TDQ', 'SUBQ', 'OC', 'AGG', 'RP', 'TSR']
                missing_subscores = [sub for sub in expected_subscores if sub not in subscores]
                
                if missing_subscores:
                    print(f"   ⚠️  Missing subscores for {fighter_key}: {missing_subscores}")
                    return False
                    
                print(f"   {fighter_key} subscores: {subscores}")
        
        return success

    def test_edge_cases(self):
        """Test edge cases for the scoring system"""
        print("\n🧪 Testing Edge Cases...")
        
        # Test with no events
        empty_request = {
            "bout_id": "test_bout_empty",
            "round_num": 1,
            "events": [],
            "round_duration": 300
        }
        
        success1, _ = self.run_test("Empty Events List", "POST", "calculate-score", 200, empty_request)
        
        # Test with invalid event type
        invalid_events = [{
            "bout_id": "test_bout_invalid",
            "round_num": 1,
            "fighter": "fighter1",
            "event_type": "INVALID_EVENT",
            "timestamp": 30.0,
            "metadata": {}
        }]
        
        invalid_request = {
            "bout_id": "test_bout_invalid",
            "round_num": 1,
            "events": invalid_events,
            "round_duration": 300
        }
        
        success2, _ = self.run_test("Invalid Event Type", "POST", "calculate-score", 200, invalid_request)
        
        return success1 and success2

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Combat Judging API Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test basic connectivity
        self.test_root_endpoint()
        
        # Test status endpoints
        self.test_status_endpoints()
        
        # Test main scoring functionality
        self.test_calculate_score_endpoint()
        
        # Test edge cases
        self.test_edge_cases()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1

    def get_results(self):
        """Get detailed test results"""
        return {
            'total_tests': self.tests_run,
            'passed_tests': self.tests_passed,
            'success_rate': (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            'results': self.results
        }

def main():
    tester = CombatJudgingAPITester()
    exit_code = tester.run_all_tests()
    
    # Save results to file
    results = tester.get_results()
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())