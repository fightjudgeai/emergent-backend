#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class JudgeProfileTester:
    def __init__(self, base_url="https://judgepro.preview.emergentagent.com"):
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
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)

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
                    return success, response.json()
                except:
                    result['response'] = response.text[:200]
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                result['error'] = response.text[:200]
                self.results.append(result)
                return False, {}

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

    def test_judge_profile_apis(self):
        """Test all Judge Profile Management APIs"""
        print("👨‍⚖️ Testing Judge Profile Management APIs")
        print("=" * 60)
        
        # Test data
        judge_profiles = [
            {
                "judgeId": "JUDGE001",
                "judgeName": "Sarah Mitchell",
                "organization": "Nevada State Athletic Commission",
                "email": "sarah.mitchell@nsac.nv.gov",
                "certifications": ["MMA Level 1", "Boxing Level 2", "Muay Thai"]
            },
            {
                "judgeId": "JUDGE002", 
                "judgeName": "Carlos Rodriguez",
                "organization": "California State Athletic Commission",
                "email": "carlos.rodriguez@csac.ca.gov",
                "certifications": ["MMA Level 2", "BJJ Black Belt"]
            },
            {
                "judgeId": "owner-001",
                "judgeName": "Owner Judge",
                "organization": "System Administrator",
                "email": "owner@judgesync.com",
                "certifications": ["System Admin", "MMA Level 3"]
            }
        ]
        
        created_judges = []
        
        # Test 1: Create judge profiles
        print("\n📝 Step 1: Creating Judge Profiles")
        for profile_data in judge_profiles:
            success, response = self.run_test(
                f"POST /api/judges - {profile_data['judgeName']}", 
                "POST", 
                "judges", 
                200, 
                profile_data
            )
            
            if success and response:
                print(f"   ✅ Created: {profile_data['judgeName']}")
                print(f"   Judge ID: {response.get('judgeId')}")
                print(f"   Message: {response.get('message')}")
                created_judges.append(profile_data['judgeId'])
            else:
                print(f"   ❌ Failed to create: {profile_data['judgeName']}")
        
        # Test 2: Get judge profiles with stats
        print("\n📊 Step 2: Getting Judge Profiles with Stats")
        for judge_id in created_judges:
            success, response = self.run_test(
                f"GET /api/judges/{judge_id}", 
                "GET", 
                f"judges/{judge_id}", 
                200
            )
            
            if success and response:
                print(f"   ✅ Retrieved profile for: {judge_id}")
                print(f"   Name: {response.get('judgeName')}")
                print(f"   Organization: {response.get('organization')}")
                print(f"   Total Rounds: {response.get('totalRoundsJudged', 0)}")
                print(f"   Avg Accuracy: {response.get('averageAccuracy', 0)}%")
                print(f"   Perfect Matches: {response.get('perfectMatches', 0)}")
            else:
                print(f"   ❌ Failed to get profile for: {judge_id}")
        
        # Test 3: Update judge profile
        print("\n✏️ Step 3: Updating Judge Profile")
        if created_judges:
            judge_id = created_judges[0]
            update_data = {
                "judgeName": "Sarah Mitchell-Johnson",
                "organization": "Nevada State Athletic Commission - Senior Judge",
                "email": "sarah.mitchell.johnson@nsac.nv.gov"
            }
            
            success, response = self.run_test(
                f"PUT /api/judges/{judge_id}", 
                "PUT", 
                f"judges/{judge_id}", 
                200, 
                update_data
            )
            
            if success and response:
                print(f"   ✅ Updated profile for: {judge_id}")
                print(f"   Message: {response.get('message')}")
                
                # Verify the update by getting the profile again
                success_verify, response_verify = self.run_test(
                    f"GET /api/judges/{judge_id} (verify update)", 
                    "GET", 
                    f"judges/{judge_id}", 
                    200
                )
                
                if success_verify and response_verify:
                    print(f"   ✅ Verified update - Name: {response_verify.get('judgeName')}")
                    print(f"   Updated Organization: {response_verify.get('organization')}")
            else:
                print(f"   ❌ Failed to update profile for: {judge_id}")
        
        # Test 4: Get judge scoring history
        print("\n📈 Step 4: Getting Judge Scoring History")
        
        # First, let's create some shadow judging data for testing
        print("   Creating test shadow judging data...")
        
        # Get a training round ID first
        success_rounds, response_rounds = self.run_test(
            "GET training rounds for history test", 
            "GET", 
            "training-library/rounds", 
            200
        )
        
        if success_rounds and response_rounds and len(response_rounds) > 0:
            round_id = response_rounds[0]['id']
            print(f"   Using round ID: {round_id}")
            
            # Submit some test scores for the first judge
            if created_judges:
                judge_id = created_judges[0]
                test_scores = [
                    {"myScore": "10-9", "officialScore": "10-9", "mae": 0.0, "sensitivity108": True, "accuracy": 100.0, "match": True},
                    {"myScore": "10-8", "officialScore": "10-9", "mae": 1.0, "sensitivity108": False, "accuracy": 85.0, "match": False},
                ]
                
                for i, score_data in enumerate(test_scores):
                    submission_data = {
                        "judgeId": judge_id,
                        "judgeName": "Sarah Mitchell-Johnson",
                        "roundId": round_id,
                        **score_data
                    }
                    
                    success_submit, response_submit = self.run_test(
                        f"Submit test score #{i+1} for {judge_id}", 
                        "POST", 
                        "training-library/submit-score", 
                        200, 
                        submission_data
                    )
                    
                    if success_submit:
                        print(f"   ✅ Submitted test score #{i+1}")
        
        # Now test getting history for all judges
        for judge_id in created_judges:
            success, response = self.run_test(
                f"GET /api/judges/{judge_id}/history", 
                "GET", 
                f"judges/{judge_id}/history", 
                200
            )
            
            if success and response:
                print(f"   ✅ Retrieved history for: {judge_id}")
                history = response.get('history', [])
                stats = response.get('stats', {})
                print(f"   History entries: {len(history)}")
                print(f"   Stats - Total: {stats.get('totalAttempts', 0)}, Accuracy: {stats.get('averageAccuracy', 0)}%")
                
                if history:
                    print(f"   Latest entry: {history[0].get('myScore')} vs {history[0].get('officialScore')}")
            else:
                print(f"   ❌ Failed to get history for: {judge_id}")
        
        # Test 5: Owner access control for audit logs
        print("\n🔒 Step 5: Testing Owner Access Control for Audit Logs")
        
        # Test owner access (should work)
        success_owner, response_owner = self.run_test(
            "GET /api/audit/logs (owner access)", 
            "GET", 
            "audit/logs?judge_id=owner-001", 
            200
        )
        
        if success_owner and response_owner:
            print(f"   ✅ Owner access granted")
            logs = response_owner.get('logs', [])
            print(f"   Retrieved {len(logs)} audit logs")
        else:
            print(f"   ❌ Owner access failed")
        
        # Test non-owner access (should return 403)
        success_non_owner, response_non_owner = self.run_test(
            "GET /api/audit/logs (non-owner access)", 
            "GET", 
            "audit/logs?judge_id=JUDGE001", 
            403
        )
        
        if success_non_owner:
            print(f"   ✅ Non-owner access correctly denied (403)")
        else:
            print(f"   ❌ Non-owner access should return 403")
        
        # Test owner access to audit stats
        success_owner_stats, response_owner_stats = self.run_test(
            "GET /api/audit/stats (owner access)", 
            "GET", 
            "audit/stats?judge_id=owner-001", 
            200
        )
        
        if success_owner_stats:
            print(f"   ✅ Owner access to stats granted")
        else:
            print(f"   ❌ Owner access to stats failed")
        
        # Test non-owner access to audit stats (should return 403)
        success_non_owner_stats, response_non_owner_stats = self.run_test(
            "GET /api/audit/stats (non-owner access)", 
            "GET", 
            "audit/stats?judge_id=JUDGE001", 
            403
        )
        
        if success_non_owner_stats:
            print(f"   ✅ Non-owner access to stats correctly denied (403)")
        else:
            print(f"   ❌ Non-owner access to stats should return 403")
        
        # Test 6: Error cases
        print("\n❌ Step 6: Testing Error Cases")
        
        # Test 404 for non-existent judge
        success_404, response_404 = self.run_test(
            "GET /api/judges/NON_EXISTENT (404 test)", 
            "GET", 
            "judges/NON_EXISTENT", 
            404
        )
        
        if success_404:
            print(f"   ✅ 404 correctly returned for non-existent judge")
        else:
            print(f"   ❌ Should return 404 for non-existent judge")
        
        # Test updating non-existent judge
        success_404_update, response_404_update = self.run_test(
            "PUT /api/judges/NON_EXISTENT (404 test)", 
            "PUT", 
            "judges/NON_EXISTENT", 
            404,
            {"judgeName": "Test"}
        )
        
        if success_404_update:
            print(f"   ✅ 404 correctly returned for updating non-existent judge")
        else:
            print(f"   ❌ Should return 404 for updating non-existent judge")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Judge Profile Management Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All Judge Profile Management tests passed!")
            return True
        else:
            print("❌ Some Judge Profile Management tests failed")
            return False

def main():
    tester = JudgeProfileTester()
    success = tester.test_judge_profile_apis()
    
    # Save results to file
    results = {
        'total_tests': tester.tests_run,
        'passed_tests': tester.tests_passed,
        'success_rate': (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0,
        'results': tester.results
    }
    
    with open('/app/judge_profile_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())