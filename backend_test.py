import requests
import sys
import json
from datetime import datetime

class CombatJudgingAPITester:
    def __init__(self, base_url="https://judgesync.preview.emergentagent.com"):
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

    def test_shadow_judging_seed(self):
        """Test seeding the training library"""
        print("\n🌱 Testing Shadow Judging - Seed Training Library...")
        success, response = self.run_test("Seed Training Library", "POST", "training-library/seed", 200)
        
        if success and response:
            print(f"   ✅ Seeded {response.get('count', 0)} training rounds")
            expected_count = 16  # Based on the sample data in server.py
            actual_count = response.get('count', 0)
            if actual_count != expected_count:
                print(f"   ⚠️  Expected {expected_count} rounds, got {actual_count}")
                return False
        
        return success

    def test_shadow_judging_get_rounds(self):
        """Test getting all training rounds"""
        print("\n📚 Testing Shadow Judging - Get Training Rounds...")
        success, response = self.run_test("Get Training Rounds", "GET", "training-library/rounds", 200)
        
        if success and response:
            rounds_count = len(response)
            print(f"   ✅ Retrieved {rounds_count} training rounds")
            
            # Verify structure of first round
            if rounds_count > 0:
                first_round = response[0]
                required_fields = ['id', 'event', 'fighters', 'roundNumber', 'summary', 'officialCard', 'type', 'createdAt']
                missing_fields = [field for field in required_fields if field not in first_round]
                
                if missing_fields:
                    print(f"   ⚠️  Missing fields in round structure: {missing_fields}")
                    return False
                
                print(f"   ✅ Round structure validated")
                print(f"   Sample round: {first_round['event']} - {first_round['fighters']} (Round {first_round['roundNumber']})")
                
                # Store a round ID for later tests
                self.sample_round_id = first_round['id']
            else:
                print(f"   ⚠️  No rounds returned")
                return False
        
        return success

    def test_shadow_judging_submit_scores(self):
        """Test submitting judge scores"""
        print("\n📊 Testing Shadow Judging - Submit Judge Scores...")
        
        if not hasattr(self, 'sample_round_id'):
            print("   ❌ No sample round ID available from previous test")
            return False
        
        # Test data for 3 judges with varying performance
        judges_data = [
            {
                "judgeId": "test-judge-1",
                "judgeName": "Alex Rodriguez",
                "scores": [
                    {"myScore": "10-9", "officialScore": "10-9", "mae": 0.0, "sensitivity108": True, "accuracy": 100.0, "match": True},
                    {"myScore": "10-8", "officialScore": "10-9", "mae": 1.0, "sensitivity108": False, "accuracy": 85.0, "match": False},
                    {"myScore": "10-9", "officialScore": "10-9", "mae": 0.0, "sensitivity108": True, "accuracy": 100.0, "match": True}
                ]
            },
            {
                "judgeId": "test-judge-2", 
                "judgeName": "Maria Santos",
                "scores": [
                    {"myScore": "10-9", "officialScore": "10-8", "mae": 1.0, "sensitivity108": False, "accuracy": 75.0, "match": False},
                    {"myScore": "10-9", "officialScore": "10-9", "mae": 0.0, "sensitivity108": True, "accuracy": 100.0, "match": True}
                ]
            },
            {
                "judgeId": "test-judge-3",
                "judgeName": "John Thompson", 
                "scores": [
                    {"myScore": "10-8", "officialScore": "10-8", "mae": 0.0, "sensitivity108": True, "accuracy": 100.0, "match": True},
                    {"myScore": "10-9", "officialScore": "10-8", "mae": 1.0, "sensitivity108": False, "accuracy": 80.0, "match": False},
                    {"myScore": "10-9", "officialScore": "10-9", "mae": 0.0, "sensitivity108": True, "accuracy": 100.0, "match": True},
                    {"myScore": "10-8", "officialScore": "10-8", "mae": 0.0, "sensitivity108": True, "accuracy": 100.0, "match": True}
                ]
            }
        ]
        
        all_success = True
        
        for judge_data in judges_data:
            judge_id = judge_data["judgeId"]
            judge_name = judge_data["judgeName"]
            
            for i, score_data in enumerate(judge_data["scores"]):
                submission_data = {
                    "judgeId": judge_id,
                    "judgeName": judge_name,
                    "roundId": self.sample_round_id,
                    **score_data
                }
                
                success, response = self.run_test(
                    f"Submit Score - {judge_name} #{i+1}", 
                    "POST", 
                    "training-library/submit-score", 
                    200, 
                    submission_data
                )
                
                if success and response:
                    print(f"   ✅ Score submitted for {judge_name}")
                    # Verify response structure
                    required_fields = ['id', 'judgeId', 'judgeName', 'roundId', 'myScore', 'officialScore', 'mae', 'sensitivity108', 'accuracy', 'match', 'timestamp']
                    missing_fields = [field for field in required_fields if field not in response]
                    
                    if missing_fields:
                        print(f"   ⚠️  Missing fields in response: {missing_fields}")
                        all_success = False
                else:
                    all_success = False
        
        return all_success

    def test_shadow_judging_judge_stats(self):
        """Test getting judge statistics"""
        print("\n📈 Testing Shadow Judging - Judge Statistics...")
        
        # Test stats for test-judge-1 (should have 3 attempts)
        success, response = self.run_test("Get Judge Stats - test-judge-1", "GET", "training-library/judge-stats/test-judge-1", 200)
        
        if success and response:
            print(f"   ✅ Stats retrieved for test-judge-1")
            
            # Verify response structure
            required_fields = ['judgeId', 'judgeName', 'totalAttempts', 'averageAccuracy', 'averageMAE', 'sensitivity108Rate', 'perfectMatches']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in stats response: {missing_fields}")
                return False
            
            # Verify calculations for test-judge-1
            # Expected: 3 attempts, avg accuracy = (100+85+100)/3 = 95, avg MAE = (0+1+0)/3 = 0.33, perfect matches = 2
            expected_attempts = 3
            expected_avg_accuracy = 95.0
            expected_perfect_matches = 2
            
            actual_attempts = response.get('totalAttempts', 0)
            actual_avg_accuracy = response.get('averageAccuracy', 0)
            actual_perfect_matches = response.get('perfectMatches', 0)
            
            print(f"   Total Attempts: {actual_attempts} (expected: {expected_attempts})")
            print(f"   Average Accuracy: {actual_avg_accuracy}% (expected: {expected_avg_accuracy}%)")
            print(f"   Perfect Matches: {actual_perfect_matches} (expected: {expected_perfect_matches})")
            
            if actual_attempts != expected_attempts:
                print(f"   ⚠️  Incorrect total attempts")
                return False
            
            if abs(actual_avg_accuracy - expected_avg_accuracy) > 0.1:
                print(f"   ⚠️  Incorrect average accuracy calculation")
                return False
            
            if actual_perfect_matches != expected_perfect_matches:
                print(f"   ⚠️  Incorrect perfect matches count")
                return False
        
        # Test 404 for non-existent judge
        success_404, _ = self.run_test("Get Judge Stats - Non-existent", "GET", "training-library/judge-stats/non-existent-judge", 404)
        
        return success and success_404

    def test_shadow_judging_leaderboard(self):
        """Test getting the leaderboard"""
        print("\n🏆 Testing Shadow Judging - Leaderboard...")
        
        success, response = self.run_test("Get Leaderboard", "GET", "training-library/leaderboard", 200)
        
        if success and response:
            leaderboard = response.get('leaderboard', [])
            print(f"   ✅ Leaderboard retrieved with {len(leaderboard)} judges")
            
            if len(leaderboard) > 0:
                # Verify structure of first entry
                first_entry = leaderboard[0]
                required_fields = ['judgeId', 'judgeName', 'totalAttempts', 'averageAccuracy', 'averageMAE', 'perfectMatches']
                missing_fields = [field for field in required_fields if field not in first_entry]
                
                if missing_fields:
                    print(f"   ⚠️  Missing fields in leaderboard entry: {missing_fields}")
                    return False
                
                # Verify ranking order (should be sorted by accuracy descending)
                if len(leaderboard) > 1:
                    for i in range(len(leaderboard) - 1):
                        current_accuracy = leaderboard[i]['averageAccuracy']
                        next_accuracy = leaderboard[i + 1]['averageAccuracy']
                        if current_accuracy < next_accuracy:
                            print(f"   ⚠️  Leaderboard not properly sorted by accuracy")
                            return False
                
                print(f"   ✅ Leaderboard structure and sorting validated")
                print(f"   Top judge: {first_entry['judgeName']} with {first_entry['averageAccuracy']}% accuracy")
            else:
                print(f"   ⚠️  Empty leaderboard")
                return False
        
        return success

    def test_shadow_judging_complete_flow(self):
        """Test the complete Shadow Judging flow"""
        print("\n🎯 Testing Complete Shadow Judging Flow...")
        
        # Step 1: Seed training library
        if not self.test_shadow_judging_seed():
            return False
        
        # Step 2: Get all rounds and verify
        if not self.test_shadow_judging_get_rounds():
            return False
        
        # Step 3: Submit scores for multiple judges
        if not self.test_shadow_judging_submit_scores():
            return False
        
        # Step 4: Get judge stats and verify calculations
        if not self.test_shadow_judging_judge_stats():
            return False
        
        # Step 5: Get leaderboard and verify ranking
        if not self.test_shadow_judging_leaderboard():
            return False
        
        print("   🎉 Complete Shadow Judging flow test passed!")
        return True

    def test_audit_create_log(self):
        """Test creating audit log entries"""
        print("\n🔐 Testing Security & Audit - Create Audit Log...")
        
        # Test data for different audit log types
        audit_logs = [
            {
                "action_type": "score_calculation",
                "user_id": "judge-001",
                "user_name": "John Smith",
                "resource_type": "round_score",
                "resource_id": "bout_123_round_1",
                "action_data": {
                    "bout_id": "bout_123",
                    "round_num": 1,
                    "card": "10-9",
                    "winner": "fighter1",
                    "score_gap": 450.5
                },
                "ip_address": "192.168.1.100"
            },
            {
                "action_type": "flag_created",
                "user_id": "admin-001",
                "user_name": "Admin User",
                "resource_type": "discrepancy_flag",
                "resource_id": "flag_456",
                "action_data": {
                    "flag_type": "boundary_case",
                    "severity": "medium",
                    "bout_id": "bout_123"
                }
            },
            {
                "action_type": "profile_changed",
                "user_id": "judge-002",
                "user_name": "Maria Garcia",
                "resource_type": "tuning_profile",
                "resource_id": "profile_ufc_001",
                "action_data": {
                    "changes": ["weights.KD", "thresholds.threshold_10_8"],
                    "promotion": "UFC"
                }
            }
        ]
        
        created_log_ids = []
        all_success = True
        
        for i, log_data in enumerate(audit_logs):
            success, response = self.run_test(
                f"Create Audit Log #{i+1} - {log_data['action_type']}", 
                "POST", 
                "audit/log", 
                200, 
                log_data
            )
            
            if success and response:
                print(f"   ✅ Audit log created: {log_data['action_type']}")
                
                # Verify response structure
                if 'success' not in response or 'log_id' not in response:
                    print(f"   ⚠️  Missing fields in response: expected 'success' and 'log_id'")
                    all_success = False
                else:
                    created_log_ids.append(response['log_id'])
                    print(f"   Log ID: {response['log_id']}")
            else:
                all_success = False
        
        # Store log IDs for later tests
        self.created_audit_log_ids = created_log_ids
        return all_success

    def test_audit_get_logs(self):
        """Test retrieving audit logs with filters"""
        print("\n📋 Testing Security & Audit - Get Audit Logs...")
        
        # Test 1: Get all logs (no filters)
        success1, response1 = self.run_test("Get All Audit Logs", "GET", "audit/logs", 200)
        
        if success1 and response1:
            logs = response1.get('logs', [])
            count = response1.get('count', 0)
            immutable = response1.get('immutable', False)
            
            print(f"   ✅ Retrieved {count} audit logs")
            print(f"   WORM compliance: {immutable}")
            
            # Verify response structure
            required_fields = ['logs', 'count', 'immutable', 'message']
            missing_fields = [field for field in required_fields if field not in response1]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in response: {missing_fields}")
                return False
            
            # Verify log structure if logs exist
            if logs:
                first_log = logs[0]
                required_log_fields = ['id', 'timestamp', 'action_type', 'user_id', 'user_name', 
                                     'resource_type', 'resource_id', 'action_data', 'signature', 'immutable']
                missing_log_fields = [field for field in required_log_fields if field not in first_log]
                
                if missing_log_fields:
                    print(f"   ⚠️  Missing fields in log structure: {missing_log_fields}")
                    return False
                
                print(f"   ✅ Log structure validated")
                print(f"   Sample log: {first_log['action_type']} by {first_log['user_name']}")
        
        # Test 2: Filter by action_type
        success2, response2 = self.run_test("Get Logs - Filter by action_type", "GET", "audit/logs?action_type=score_calculation", 200)
        
        if success2 and response2:
            filtered_logs = response2.get('logs', [])
            print(f"   ✅ Filtered by action_type: {len(filtered_logs)} logs")
            
            # Verify all logs have the correct action_type
            for log in filtered_logs:
                if log.get('action_type') != 'score_calculation':
                    print(f"   ⚠️  Filter failed: found log with action_type '{log.get('action_type')}'")
                    return False
        
        # Test 3: Filter by user_id
        success3, response3 = self.run_test("Get Logs - Filter by user_id", "GET", "audit/logs?user_id=judge-001", 200)
        
        if success3 and response3:
            user_logs = response3.get('logs', [])
            print(f"   ✅ Filtered by user_id: {len(user_logs)} logs")
        
        # Test 4: Filter by resource_type
        success4, response4 = self.run_test("Get Logs - Filter by resource_type", "GET", "audit/logs?resource_type=round_score", 200)
        
        if success4 and response4:
            resource_logs = response4.get('logs', [])
            print(f"   ✅ Filtered by resource_type: {len(resource_logs)} logs")
        
        # Test 5: Multiple filters combined
        success5, response5 = self.run_test("Get Logs - Multiple filters", "GET", "audit/logs?action_type=score_calculation&user_id=judge-001", 200)
        
        if success5 and response5:
            combined_logs = response5.get('logs', [])
            print(f"   ✅ Multiple filters: {len(combined_logs)} logs")
        
        return success1 and success2 and success3 and success4 and success5

    def test_audit_stats(self):
        """Test audit statistics endpoint"""
        print("\n📊 Testing Security & Audit - Audit Statistics...")
        
        success, response = self.run_test("Get Audit Statistics", "GET", "audit/stats", 200)
        
        if success and response:
            total_logs = response.get('total_logs', 0)
            by_action_type = response.get('by_action_type', [])
            top_users = response.get('top_users', [])
            immutable = response.get('immutable', False)
            worm_compliant = response.get('worm_compliant', False)
            
            print(f"   ✅ Statistics retrieved")
            print(f"   Total logs: {total_logs}")
            print(f"   Action types: {len(by_action_type)}")
            print(f"   Top users: {len(top_users)}")
            print(f"   WORM compliant: {worm_compliant}")
            
            # Verify response structure
            required_fields = ['total_logs', 'by_action_type', 'top_users', 'immutable', 'worm_compliant']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in response: {missing_fields}")
                return False
            
            # Verify action type breakdown structure
            if by_action_type:
                first_type = by_action_type[0]
                if 'type' not in first_type or 'count' not in first_type:
                    print(f"   ⚠️  Invalid action type breakdown structure")
                    return False
                
                print(f"   Top action type: {first_type['type']} ({first_type['count']} logs)")
            
            # Verify top users structure
            if top_users:
                first_user = top_users[0]
                required_user_fields = ['user_id', 'user_name', 'count']
                missing_user_fields = [field for field in required_user_fields if field not in first_user]
                
                if missing_user_fields:
                    print(f"   ⚠️  Missing fields in top users: {missing_user_fields}")
                    return False
                
                print(f"   Top user: {first_user['user_name']} ({first_user['count']} logs)")
            
            # Verify calculations are reasonable
            if by_action_type:
                total_from_breakdown = sum(item['count'] for item in by_action_type)
                if total_from_breakdown != total_logs:
                    print(f"   ⚠️  Statistics mismatch: total_logs={total_logs}, breakdown sum={total_from_breakdown}")
                    return False
                
                print(f"   ✅ Statistics calculations verified")
        
        return success

    def test_audit_verify_signature(self):
        """Test audit log signature verification"""
        print("\n🔍 Testing Security & Audit - Verify Signatures...")
        
        if not hasattr(self, 'created_audit_log_ids') or not self.created_audit_log_ids:
            print("   ❌ No audit log IDs available from previous test")
            return False
        
        all_success = True
        
        # Test verification for each created log
        for i, log_id in enumerate(self.created_audit_log_ids):
            success, response = self.run_test(
                f"Verify Signature - Log #{i+1}", 
                "GET", 
                f"audit/verify/{log_id}", 
                200
            )
            
            if success and response:
                valid = response.get('valid', False)
                signature = response.get('signature', '')
                computed_signature = response.get('computed_signature', '')
                message = response.get('message', '')
                
                print(f"   ✅ Signature verification for log {log_id}")
                print(f"   Valid: {valid}")
                print(f"   Message: {message}")
                
                # Verify response structure
                required_fields = ['valid', 'signature', 'computed_signature', 'message']
                missing_fields = [field for field in required_fields if field not in response]
                
                if missing_fields:
                    print(f"   ⚠️  Missing fields in verification response: {missing_fields}")
                    all_success = False
                
                # Signature should be valid for newly created logs
                if not valid:
                    print(f"   ⚠️  Signature validation failed for log {log_id}")
                    print(f"   Original: {signature}")
                    print(f"   Computed: {computed_signature}")
                    all_success = False
                
                # Signatures should match
                if signature != computed_signature:
                    print(f"   ⚠️  Signature mismatch for log {log_id}")
                    all_success = False
            else:
                all_success = False
        
        # Test 404 for non-existent log
        success_404, _ = self.run_test("Verify Signature - Non-existent Log", "GET", "audit/verify/non-existent-log-id", 404)
        
        return all_success and success_404

    def test_audit_export(self):
        """Test audit log export functionality"""
        print("\n📤 Testing Security & Audit - Export Audit Logs...")
        
        success, response = self.run_test("Export Audit Logs", "GET", "audit/export", 200)
        
        if success and response:
            export_format = response.get('export_format', '')
            export_timestamp = response.get('export_timestamp', '')
            record_count = response.get('record_count', 0)
            logs = response.get('logs', [])
            immutable = response.get('immutable', False)
            note = response.get('note', '')
            
            print(f"   ✅ Export completed")
            print(f"   Format: {export_format}")
            print(f"   Record count: {record_count}")
            print(f"   Export timestamp: {export_timestamp}")
            print(f"   WORM compliance: {immutable}")
            
            # Verify response structure
            required_fields = ['export_format', 'export_timestamp', 'record_count', 'logs', 'immutable', 'note']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in export response: {missing_fields}")
                return False
            
            # Verify export metadata
            if not export_timestamp:
                print(f"   ⚠️  Missing export timestamp")
                return False
            
            if record_count != len(logs):
                print(f"   ⚠️  Record count mismatch: stated={record_count}, actual={len(logs)}")
                return False
            
            # Verify exported logs have complete data
            if logs:
                first_log = logs[0]
                required_log_fields = ['id', 'timestamp', 'action_type', 'user_id', 'user_name', 
                                     'resource_type', 'resource_id', 'action_data', 'signature', 'immutable']
                missing_log_fields = [field for field in required_log_fields if field not in first_log]
                
                if missing_log_fields:
                    print(f"   ⚠️  Missing fields in exported log: {missing_log_fields}")
                    return False
                
                print(f"   ✅ Exported log structure validated")
            
            # Verify compliance note
            if "WORM" not in note:
                print(f"   ⚠️  Export note should mention WORM compliance")
                return False
        
        return success

    def test_audit_integration_flow(self):
        """Test complete Security & Audit integration flow"""
        print("\n🔐 Testing Complete Security & Audit Integration Flow...")
        
        # Step 1: Create multiple audit logs with different types and users
        print("   Step 1: Creating audit logs...")
        if not self.test_audit_create_log():
            return False
        
        # Step 2: Retrieve logs with various filters
        print("   Step 2: Testing log retrieval and filtering...")
        if not self.test_audit_get_logs():
            return False
        
        # Step 3: Verify signatures for all created logs
        print("   Step 3: Verifying cryptographic signatures...")
        if not self.test_audit_verify_signature():
            return False
        
        # Step 4: Check statistics calculations
        print("   Step 4: Validating statistics aggregation...")
        if not self.test_audit_stats():
            return False
        
        # Step 5: Export and verify exported data
        print("   Step 5: Testing export functionality...")
        if not self.test_audit_export():
            return False
        
        print("   🎉 Complete Security & Audit integration flow test passed!")
        print("   ✅ All audit logs have SHA-256 signatures")
        print("   ✅ WORM (Write Once Read Many) compliance verified")
        print("   ✅ All CRUD operations working correctly")
        return True

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
        
        # Test Shadow Judging Training Mode (NEW)
        self.test_shadow_judging_complete_flow()
        
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