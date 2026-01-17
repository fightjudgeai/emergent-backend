#!/usr/bin/env python3
"""
FightJudgeAI PRO Mission-Critical Backend Systems Test Suite
Comprehensive testing for all 7 major backend systems as specified in review request
"""

import requests
import sys
import json
import time
from datetime import datetime

class FightJudgeAIProTester:
    def __init__(self, base_url="https://mmascore.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []
        self.performance_metrics = {}

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            success = response.status_code == expected_status
            
            result = {
                'test': name,
                'success': success,
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'response_time_ms': response_time_ms,
                'url': url
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code} ({response_time_ms:.2f}ms)")
                try:
                    result['response'] = response.json()
                except:
                    result['response'] = response.text[:200]
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                result['error'] = response.text[:200]

            self.results.append(result)
            return success, response.json() if success and response.text else {}, response_time_ms

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                'test': name,
                'success': False,
                'error': str(e),
                'url': url
            }
            self.results.append(result)
            return False, {}, 0

    # PHASE 1: Event Deduplication Engine Tests
    def test_enhanced_event_logging(self):
        """Test Enhanced Event Logging (POST /api/events/v2/log)"""
        print("\n🔍 Testing Enhanced Event Logging...")
        
        # Create a test bout
        bout_id = "test_bout_001"
        round_id = 1
        
        # Test 1: Log a new event with all required fields
        event_data = {
            "bout_id": bout_id,
            "round_id": round_id,
            "judge_id": "JUDGE_TEST",
            "fighter_id": "fighter1",
            "event_type": "Jab",
            "timestamp_ms": 1234567890000,
            "device_id": "test_device_001",
            "metadata": {"significant": True}
        }
        
        success1, response1, perf1 = self.run_test("Enhanced Event Logging - New Event", "POST", "events/v2/log", 200, event_data)
        
        if not success1 or not response1:
            return False
        
        # Store performance metric
        self.performance_metrics['event_logging'] = perf1
        
        # Verify response structure
        required_fields = ['success', 'event_id', 'is_duplicate', 'sequence_index', 'event_hash']
        missing_fields = [field for field in required_fields if field not in response1]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        if response1.get('is_duplicate') != False:
            print(f"   ❌ Expected is_duplicate=false for new event")
            return False
        
        print(f"   ✅ New event logged successfully")
        print(f"   Event ID: {response1.get('event_id')}")
        print(f"   Sequence Index: {response1.get('sequence_index')}")
        print(f"   Event Hash: {response1.get('event_hash')}")
        
        # Store for duplicate test
        original_event_hash = response1.get('event_hash')
        
        # Test 2: Log the EXACT SAME event again (duplicate test)
        success2, response2, _ = self.run_test("Enhanced Event Logging - Duplicate Event", "POST", "events/v2/log", 200, event_data)
        
        if not success2 or not response2:
            return False
        
        if response2.get('is_duplicate') != True:
            print(f"   ❌ Expected is_duplicate=true for duplicate event")
            return False
        
        if response2.get('event_hash') != original_event_hash:
            print(f"   ❌ Duplicate event should have same hash")
            return False
        
        print(f"   ✅ Duplicate detection working correctly")
        
        return True

    def test_event_chain_integrity(self):
        """Test Event Chain Integrity (GET /api/events/v2/verify/{bout_id}/{round_id})"""
        print("\n🔗 Testing Event Chain Integrity...")
        
        bout_id = "test_bout_001"
        round_id = 1
        
        # Log 5 different events for same bout/round
        events = [
            {"event_type": "Cross", "timestamp_ms": 1234567891000, "fighter_id": "fighter1"},
            {"event_type": "Hook", "timestamp_ms": 1234567892000, "fighter_id": "fighter2"},
            {"event_type": "KD", "timestamp_ms": 1234567893000, "fighter_id": "fighter1", "metadata": {"tier": "Hard"}},
            {"event_type": "Takedown Landed", "timestamp_ms": 1234567894000, "fighter_id": "fighter2"},
            {"event_type": "Submission Attempt", "timestamp_ms": 1234567895000, "fighter_id": "fighter1", "metadata": {"tier": "Deep"}}
        ]
        
        logged_events = 0
        for i, event in enumerate(events):
            event_data = {
                "bout_id": bout_id,
                "round_id": round_id,
                "judge_id": "JUDGE_TEST",
                "device_id": "test_device_001",
                **event
            }
            
            success, response, _ = self.run_test(f"Log Event #{i+1}", "POST", "events/v2/log", 200, event_data)
            if success and not response.get('is_duplicate'):
                logged_events += 1
        
        print(f"   ✅ Logged {logged_events} events")
        
        # Verify chain integrity
        success, response, _ = self.run_test("Verify Event Chain", "GET", f"events/v2/verify/{bout_id}/{round_id}", 200)
        
        if not success or not response:
            return False
        
        required_fields = ['chain_valid', 'total_events', 'bout_id', 'round_id']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        if not response.get('chain_valid'):
            print(f"   ❌ Event chain validation failed")
            return False
        
        expected_events = logged_events + 1  # +1 for the original event from previous test
        if response.get('total_events') < expected_events:
            print(f"   ❌ Expected at least {expected_events} events, got {response.get('total_events')}")
            return False
        
        print(f"   ✅ Event chain is valid")
        print(f"   Total events: {response.get('total_events')}")
        
        return True

    def test_get_events_in_order(self):
        """Test Get Events in Order (GET /api/events/v2/{bout_id}/{round_id})"""
        print("\n📋 Testing Get Events in Order...")
        
        bout_id = "test_bout_001"
        round_id = 1
        
        success, response, _ = self.run_test("Get Events in Order", "GET", f"events/v2/{bout_id}/{round_id}", 200)
        
        if not success or not response:
            return False
        
        required_fields = ['events', 'count', 'bout_id', 'round_id']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        events = response.get('events', [])
        if not events:
            print(f"   ❌ No events returned")
            return False
        
        # Verify events are ordered by sequence_index
        for i in range(len(events) - 1):
            current_seq = events[i].get('sequence_index', 0)
            next_seq = events[i + 1].get('sequence_index', 0)
            if current_seq >= next_seq:
                print(f"   ❌ Events not ordered by sequence_index")
                return False
        
        # Verify all required fields are present
        first_event = events[0]
        required_event_fields = ['event_hash', 'event_fingerprint', 'previous_event_hash', 'sequence_index']
        missing_event_fields = [field for field in required_event_fields if field not in first_event]
        
        if missing_event_fields:
            print(f"   ❌ Missing fields in event: {missing_event_fields}")
            return False
        
        print(f"   ✅ Retrieved {len(events)} events in correct order")
        print(f"   First event: {first_event.get('event_type')} (seq: {first_event.get('sequence_index')})")
        print(f"   Last event: {events[-1].get('event_type')} (seq: {events[-1].get('sequence_index')})")
        
        return True

    # PHASE 2: Round Replay Engine Tests
    def test_replay_generation(self):
        """Test Replay Generation (GET /api/replay/{bout_id}/{round_id})"""
        print("\n🎬 Testing Replay Generation...")
        
        # Create test bout with multiple events across different seconds
        bout_id = "test_bout_replay"
        round_id = 1
        
        # Log diverse events across different seconds
        replay_events = [
            {"event_type": "Jab", "timestamp_ms": 10000, "fighter_id": "fighter1", "metadata": {"significant": True}},
            {"event_type": "Cross", "timestamp_ms": 15000, "fighter_id": "fighter2", "metadata": {"significant": True}},
            {"event_type": "KD", "timestamp_ms": 30000, "fighter_id": "fighter1", "metadata": {"tier": "Hard"}},
            {"event_type": "Ground Top Control", "timestamp_ms": 35000, "fighter_id": "fighter1", "metadata": {"type": "start"}},
            {"event_type": "Ground Top Control", "timestamp_ms": 65000, "fighter_id": "fighter1", "metadata": {"type": "stop", "duration": 30}},
            {"event_type": "Submission Attempt", "timestamp_ms": 90000, "fighter_id": "fighter2", "metadata": {"tier": "Deep"}},
            {"event_type": "Takedown Landed", "timestamp_ms": 120000, "fighter_id": "fighter2"},
            {"event_type": "Hook", "timestamp_ms": 150000, "fighter_id": "fighter1", "metadata": {"significant": True}},
            {"event_type": "Elbow", "timestamp_ms": 180000, "fighter_id": "fighter2", "metadata": {"significant": True}},
            {"event_type": "Cage Control Time", "timestamp_ms": 200000, "fighter_id": "fighter1", "metadata": {"type": "stop", "duration": 20}}
        ]
        
        logged_count = 0
        for i, event in enumerate(replay_events):
            event_data = {
                "bout_id": bout_id,
                "round_id": round_id,
                "judge_id": "JUDGE_REPLAY",
                "device_id": "replay_device_001",
                **event
            }
            
            success, response, _ = self.run_test(f"Log Replay Event #{i+1}", "POST", "events/v2/log", 200, event_data)
            if success and not response.get('is_duplicate'):
                logged_count += 1
        
        print(f"   ✅ Logged {logged_count} events for replay")
        
        # Generate replay
        success, response, performance_ms = self.run_test("Generate Replay", "GET", f"replay/{bout_id}/{round_id}", 200)
        
        # Store performance metric
        self.performance_metrics['replay_generation'] = performance_ms
        
        if not success or not response:
            return False
        
        # Verify response structure
        required_fields = ['bout_id', 'round_id', 'timeline', 'round_summary', 'event_count']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        timeline = response.get('timeline', [])
        round_summary = response.get('round_summary', {})
        
        # Verify timeline structure
        if not timeline:
            print(f"   ❌ Empty timeline")
            return False
        
        # Verify timeline has entries for each second
        timeline_seconds = [entry.get('second') for entry in timeline]
        if len(set(timeline_seconds)) != len(timeline):
            print(f"   ❌ Timeline should have unique seconds")
            return False
        
        # Verify round summary structure
        required_summary_fields = ['damage_score', 'grappling_score', 'control_score', 'total_score', 'winner_recommendation']
        missing_summary_fields = [field for field in required_summary_fields if field not in round_summary]
        
        if missing_summary_fields:
            print(f"   ❌ Missing fields in round_summary: {missing_summary_fields}")
            return False
        
        # Verify accumulated scores increase over time (for fighter with events)
        red_totals = [entry['damage_totals']['red'] + entry['grappling_totals']['red'] + entry['control_totals']['red'] for entry in timeline]
        if red_totals[-1] <= red_totals[0]:
            print(f"   ❌ Accumulated scores should increase over time")
            return False
        
        # Verify performance requirement (< 150ms)
        if performance_ms > 150:
            print(f"   ⚠️  Performance warning: {performance_ms:.2f}ms (target: <150ms)")
        else:
            print(f"   ✅ Performance target met: {performance_ms:.2f}ms")
        
        print(f"   ✅ Replay generated successfully")
        print(f"   Timeline entries: {len(timeline)}")
        print(f"   Winner recommendation: {round_summary.get('winner_recommendation')}")
        print(f"   Red total: {round_summary.get('total_score', {}).get('red', 0)}")
        print(f"   Blue total: {round_summary.get('total_score', {}).get('blue', 0)}")
        
        return True

    # PHASE 3: Broadcast API Tests
    def test_live_broadcast_data(self):
        """Test Live Broadcast Data (GET /api/live/{bout_id})"""
        print("\n📡 Testing Live Broadcast Data...")
        
        bout_id = "test_bout_live"
        
        # Log recent events (within last 5 seconds)
        current_time_ms = int(time.time() * 1000)
        recent_events = [
            {"event_type": "Jab", "timestamp_ms": current_time_ms - 2000, "fighter_id": "fighter1"},
            {"event_type": "KD", "timestamp_ms": current_time_ms - 1000, "fighter_id": "fighter1", "metadata": {"tier": "Hard"}},
            {"event_type": "Cross", "timestamp_ms": current_time_ms - 500, "fighter_id": "fighter2"}
        ]
        
        for i, event in enumerate(recent_events):
            event_data = {
                "bout_id": bout_id,
                "round_id": 1,
                "judge_id": "JUDGE_LIVE",
                "device_id": "live_device_001",
                **event
            }
            
            self.run_test(f"Log Live Event #{i+1}", "POST", "events/v2/log", 200, event_data)
        
        # Test live broadcast endpoint
        success, response, performance_ms = self.run_test("Get Live Broadcast Data", "GET", f"live/{bout_id}", 200)
        
        # Store performance metric
        self.performance_metrics['broadcast_data'] = performance_ms
        
        if not success or not response:
            return False
        
        # Verify response structure
        required_fields = ['red_totals', 'blue_totals', 'round_status', 'events_last_5_sec', 'redline_moments']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        red_totals = response.get('red_totals', {})
        blue_totals = response.get('blue_totals', {})
        events_last_5_sec = response.get('events_last_5_sec', 0)
        redline_moments = response.get('redline_moments', [])
        
        # Verify totals structure
        required_total_fields = ['damage', 'grappling', 'control', 'total']
        for totals, fighter in [(red_totals, 'red'), (blue_totals, 'blue')]:
            missing_total_fields = [field for field in required_total_fields if field not in totals]
            if missing_total_fields:
                print(f"   ❌ Missing fields in {fighter}_totals: {missing_total_fields}")
                return False
        
        # Verify recent events count
        if events_last_5_sec < 3:  # We logged 3 recent events
            print(f"   ❌ Expected at least 3 recent events, got {events_last_5_sec}")
            return False
        
        # Verify redline moments captured KD events
        kd_moments = [moment for moment in redline_moments if moment.get('event_type') == 'KD']
        if len(kd_moments) < 1:
            print(f"   ❌ Expected at least 1 KD in redline moments")
            return False
        
        # Verify performance requirement (< 100ms)
        if performance_ms > 100:
            print(f"   ⚠️  Performance warning: {performance_ms:.2f}ms (target: <100ms)")
        else:
            print(f"   ✅ Performance target met: {performance_ms:.2f}ms")
        
        print(f"   ✅ Live broadcast data retrieved successfully")
        print(f"   Recent events (last 5s): {events_last_5_sec}")
        print(f"   Redline moments: {len(redline_moments)}")
        print(f"   Red total: {red_totals.get('total', 0)}")
        print(f"   Blue total: {blue_totals.get('total', 0)}")
        
        return True

    def test_final_results(self):
        """Test Final Results (GET /api/final/{bout_id})"""
        print("\n🏁 Testing Final Results...")
        
        bout_id = "test_bout_final"
        
        # Create completed bout with judge scores (simulate multiple rounds)
        for round_id in [1, 2, 3]:
            events = [
                {"event_type": "Jab", "timestamp_ms": 10000 + (round_id * 1000), "fighter_id": "fighter1"},
                {"event_type": "Cross", "timestamp_ms": 20000 + (round_id * 1000), "fighter_id": "fighter2"},
                {"event_type": "Hook", "timestamp_ms": 30000 + (round_id * 1000), "fighter_id": "fighter1"}
            ]
            
            for event in events:
                event_data = {
                    "bout_id": bout_id,
                    "round_id": round_id,
                    "judge_id": "JUDGE_FINAL",
                    "device_id": "final_device_001",
                    **event
                }
                
                self.run_test(f"Log Final Event R{round_id}", "POST", "events/v2/log", 200, event_data)
        
        # Test final results endpoint
        success, response, _ = self.run_test("Get Final Results", "GET", f"final/{bout_id}", 200)
        
        if not success or not response:
            return False
        
        # Verify response structure
        required_fields = ['bout_id', 'fighter_names', 'final_scores', 'full_event_log_hash_chain_valid']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        fighter_names = response.get('fighter_names', {})
        final_scores = response.get('final_scores', [])
        chain_valid = response.get('full_event_log_hash_chain_valid', False)
        
        # Verify fighter names structure
        if 'fighter1' not in fighter_names or 'fighter2' not in fighter_names:
            print(f"   ❌ Missing fighter names")
            return False
        
        # Verify final scores structure
        if not final_scores:
            print(f"   ❌ No final scores returned")
            return False
        
        for score in final_scores:
            required_score_fields = ['round', 'red_score', 'blue_score', 'winner']
            missing_score_fields = [field for field in required_score_fields if field not in score]
            if missing_score_fields:
                print(f"   ❌ Missing fields in final score: {missing_score_fields}")
                return False
        
        # Verify hash chain validation
        if not chain_valid:
            print(f"   ❌ Event log hash chain validation failed")
            return False
        
        print(f"   ✅ Final results retrieved successfully")
        print(f"   Fighter 1: {fighter_names.get('fighter1', 'Unknown')}")
        print(f"   Fighter 2: {fighter_names.get('fighter2', 'Unknown')}")
        print(f"   Rounds scored: {len(final_scores)}")
        print(f"   Hash chain valid: {chain_valid}")
        
        return True

    # PHASE 4: Judge Session & Hot-Swap Tests
    def test_create_judge_session(self):
        """Test Create Judge Session (POST /api/judge-session/create)"""
        print("\n👨‍⚖️ Testing Create Judge Session...")
        
        session_data = {
            "judge_session_id": "session_test_001",
            "judge_id": "JUDGE_TEST",
            "bout_id": "test_bout_001",
            "round_id": 1,
            "last_event_sequence": 10,
            "session_state": "OPEN",
            "unsent_event_queue": []
        }
        
        success, response, _ = self.run_test("Create Judge Session", "POST", "judge-session/create", 200, session_data)
        
        if not success or not response:
            return False
        
        # Verify response structure
        required_fields = ['success', 'session_id', 'message']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        if not response.get('success'):
            print(f"   ❌ Session creation failed")
            return False
        
        print(f"   ✅ Judge session created successfully")
        print(f"   Session ID: {response.get('session_id')}")
        
        # Store session ID for restore test
        self.test_session_id = session_data['judge_session_id']
        
        return True

    def test_restore_judge_session(self):
        """Test Restore Judge Session (GET /api/judge-session/{session_id})"""
        print("\n🔄 Testing Restore Judge Session...")
        
        if not hasattr(self, 'test_session_id'):
            print("   ❌ No session ID available from create test")
            return False
        
        # Test restoring existing session
        success, response, performance_ms = self.run_test("Restore Judge Session", "GET", f"judge-session/{self.test_session_id}", 200)
        
        # Store performance metric
        self.performance_metrics['session_restore'] = performance_ms
        
        if not success or not response:
            return False
        
        # Verify response structure
        required_fields = ['judge_session_id', 'judge_id', 'bout_id', 'round_id', 'session_state']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        # Verify session data matches what we created
        if response.get('judge_session_id') != self.test_session_id:
            print(f"   ❌ Session ID mismatch")
            return False
        
        if response.get('judge_id') != 'JUDGE_TEST':
            print(f"   ❌ Judge ID mismatch")
            return False
        
        # Verify performance requirement (< 200ms)
        if performance_ms > 200:
            print(f"   ⚠️  Performance warning: {performance_ms:.2f}ms (target: <200ms)")
        else:
            print(f"   ✅ Performance target met: {performance_ms:.2f}ms")
        
        print(f"   ✅ Judge session restored successfully")
        print(f"   Judge ID: {response.get('judge_id')}")
        print(f"   Bout ID: {response.get('bout_id')}")
        print(f"   Session State: {response.get('session_state')}")
        
        # Test 404 for non-existent session
        success_404, _, _ = self.run_test("Restore Non-existent Session", "GET", "judge-session/non-existent-session", 404)
        
        return success and success_404

    # PHASE 5: Telemetry Tests
    def test_report_telemetry(self):
        """Test Report Telemetry (POST /api/telemetry/report)"""
        print("\n📊 Testing Report Telemetry...")
        
        telemetry_data = {
            "device_id": "test_device_001",
            "judge_id": "JUDGE_TEST",
            "bout_id": "test_bout_001",
            "battery_percent": 15,  # Low battery to trigger alert
            "network_strength_percent": 85,
            "latency_ms": 120,
            "fps": 60,
            "dropped_event_count": 0,
            "event_rate_per_second": 0.5
        }
        
        success, response, performance_ms = self.run_test("Report Telemetry", "POST", "telemetry/report", 200, telemetry_data)
        
        # Store performance metric
        self.performance_metrics['telemetry_report'] = performance_ms
        
        if not success or not response:
            return False
        
        # Verify response structure
        required_fields = ['success', 'alerts', 'message']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        alerts = response.get('alerts', [])
        
        # Verify battery_low alert is present (battery was 15%)
        battery_alerts = [alert for alert in alerts if alert.get('type') == 'battery_low']
        if not battery_alerts:
            print(f"   ❌ Expected battery_low alert for 15% battery")
            return False
        
        # Verify performance requirement (< 20ms)
        if performance_ms > 20:
            print(f"   ⚠️  Performance warning: {performance_ms:.2f}ms (target: <20ms)")
        else:
            print(f"   ✅ Performance target met: {performance_ms:.2f}ms")
        
        print(f"   ✅ Telemetry reported successfully")
        print(f"   Alerts generated: {len(alerts)}")
        for alert in alerts:
            print(f"   - {alert.get('type')}: {alert.get('message')}")
        
        return True

    def test_get_telemetry(self):
        """Test Get Telemetry (GET /api/telemetry/{bout_id})"""
        print("\n📈 Testing Get Telemetry...")
        
        bout_id = "test_bout_001"
        
        success, response, _ = self.run_test("Get Telemetry", "GET", f"telemetry/{bout_id}", 200)
        
        if not success or not response:
            return False
        
        # Verify response structure
        required_fields = ['bout_id', 'devices', 'summary']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in response: {missing_fields}")
            return False
        
        devices = response.get('devices', [])
        
        # Verify reported device appears in list
        test_device = None
        for device in devices:
            if device.get('device_id') == 'test_device_001':
                test_device = device
                break
        
        if not test_device:
            print(f"   ❌ Test device not found in telemetry list")
            return False
        
        # Verify device structure
        required_device_fields = ['device_id', 'judge_id', 'battery_percent', 'network_strength_percent']
        missing_device_fields = [field for field in required_device_fields if field not in test_device]
        
        if missing_device_fields:
            print(f"   ❌ Missing fields in device: {missing_device_fields}")
            return False
        
        print(f"   ✅ Telemetry retrieved successfully")
        print(f"   Devices tracked: {len(devices)}")
        print(f"   Test device battery: {test_device.get('battery_percent')}%")
        print(f"   Test device network: {test_device.get('network_strength_percent')}%")
        
        return True

    # PHASE 6: Backward Compatibility Tests
    def test_legacy_event_logging(self):
        """Test Legacy Event Logging Still Works"""
        print("\n🔄 Testing Legacy Event Logging Compatibility...")
        
        # Test with legacy calculate-score endpoint to ensure it can read new events
        legacy_events = [
            {
                "bout_id": "test_bout_legacy",
                "round_num": 1,
                "fighter": "fighter1",
                "event_type": "Jab",
                "timestamp": 30.0,
                "metadata": {"significant": True}
            },
            {
                "bout_id": "test_bout_legacy",
                "round_num": 1,
                "fighter": "fighter2",
                "event_type": "Cross",
                "timestamp": 60.0,
                "metadata": {"significant": True}
            }
        ]
        
        score_request = {
            "bout_id": "test_bout_legacy",
            "round_num": 1,
            "events": legacy_events,
            "round_duration": 300
        }
        
        success, response, _ = self.run_test("Legacy Calculate Score", "POST", "calculate-score", 200, score_request)
        
        if not success or not response:
            return False
        
        # Verify legacy scoring still works
        required_fields = ['bout_id', 'round_num', 'fighter1_score', 'fighter2_score']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing fields in legacy response: {missing_fields}")
            return False
        
        print(f"   ✅ Legacy event logging compatibility verified")
        print(f"   Legacy scoring working with new engine")
        
        return True

    # PHASE 7: Error Handling Tests
    def test_invalid_requests(self):
        """Test Invalid Requests"""
        print("\n❌ Testing Invalid Requests...")
        
        all_success = True
        
        # Test 1: POST /api/events/v2/log with missing required fields
        invalid_event = {
            "bout_id": "test_bout_invalid",
            # Missing required fields: round_id, judge_id, fighter_id, event_type, timestamp_ms, device_id
        }
        
        success1, _, _ = self.run_test("Invalid Event - Missing Fields", "POST", "events/v2/log", 422, invalid_event)
        if not success1:
            all_success = False
        
        # Test 2: GET endpoints with non-existent bout_id
        success2, _, _ = self.run_test("Invalid Bout - Events", "GET", "events/v2/non-existent-bout/1", 404)
        if not success2:
            all_success = False
        
        success3, _, _ = self.run_test("Invalid Bout - Replay", "GET", "replay/non-existent-bout/1", 404)
        if not success3:
            all_success = False
        
        success4, _, _ = self.run_test("Invalid Bout - Live", "GET", "live/non-existent-bout", 404)
        if not success4:
            all_success = False
        
        success5, _, _ = self.run_test("Invalid Bout - Final", "GET", "final/non-existent-bout", 404)
        if not success5:
            all_success = False
        
        # Test 3: Invalid telemetry data
        invalid_telemetry = {
            "device_id": "test_device",
            # Missing required fields
        }
        
        success6, _, _ = self.run_test("Invalid Telemetry", "POST", "telemetry/report", 422, invalid_telemetry)
        if not success6:
            all_success = False
        
        if all_success:
            print(f"   ✅ All error handling tests passed")
        
        return all_success

    # PHASE 8: Performance Validation
    def test_performance_validation(self):
        """Test Performance Validation"""
        print("\n⚡ Testing Performance Validation...")
        
        bout_id = "test_bout_performance"
        round_id = 1
        
        # Test 1: Log 100 events sequentially and measure average time
        print("   📊 Testing event logging performance (100 events)...")
        
        total_time = 0
        successful_logs = 0
        
        for i in range(100):
            event_data = {
                "bout_id": bout_id,
                "round_id": round_id,
                "judge_id": "JUDGE_PERF",
                "fighter_id": "fighter1" if i % 2 == 0 else "fighter2",
                "event_type": "Jab",
                "timestamp_ms": int(time.time() * 1000) + i,
                "device_id": "perf_device_001",
                "metadata": {"significant": True}
            }
            
            success, response, perf_time = self.run_test(f"Perf Event #{i+1}", "POST", "events/v2/log", 200, event_data)
            
            if success and not response.get('is_duplicate'):
                total_time += perf_time
                successful_logs += 1
        
        avg_event_time = total_time / successful_logs if successful_logs > 0 else 0
        
        print(f"   Average event logging time: {avg_event_time:.2f}ms")
        if avg_event_time > 10:
            print(f"   ⚠️  Performance warning: {avg_event_time:.2f}ms (target: <10ms)")
        else:
            print(f"   ✅ Event logging performance target met")
        
        # Test 2: Generate replay for round with 100+ events
        print("   🎬 Testing replay generation performance...")
        
        success, response, replay_time = self.run_test("Performance Replay", "GET", f"replay/{bout_id}/{round_id}", 200)
        
        print(f"   Replay generation time: {replay_time:.2f}ms")
        if replay_time > 150:
            print(f"   ⚠️  Performance warning: {replay_time:.2f}ms (target: <150ms)")
        else:
            print(f"   ✅ Replay performance target met")
        
        # Test 3: Broadcast data performance
        print("   📡 Testing broadcast performance...")
        
        success, response, broadcast_time = self.run_test("Performance Broadcast", "GET", f"live/{bout_id}", 200)
        
        print(f"   Broadcast data time: {broadcast_time:.2f}ms")
        if broadcast_time > 100:
            print(f"   ⚠️  Performance warning: {broadcast_time:.2f}ms (target: <100ms)")
        else:
            print(f"   ✅ Broadcast performance target met")
        
        # Store final performance metrics
        self.performance_metrics.update({
            'avg_event_logging': avg_event_time,
            'replay_generation_perf': replay_time,
            'broadcast_data_perf': broadcast_time
        })
        
        # Summary
        all_targets_met = (
            avg_event_time <= 10 and
            replay_time <= 150 and
            broadcast_time <= 100
        )
        
        if all_targets_met:
            print(f"   🎉 All performance targets met!")
        else:
            print(f"   ⚠️  Some performance targets missed")
        
        return True

    def run_comprehensive_test_suite(self):
        """Run all FightJudgeAI PRO mission-critical backend system tests"""
        print("🥊 FIGHTJUDGEAI PRO MISSION-CRITICAL BACKEND SYSTEMS TEST SUITE")
        print("="*80)
        print(f"   Base URL: {self.base_url}")
        print(f"   API URL: {self.api_url}")
        
        all_success = True
        
        # PHASE 1: Event Deduplication Engine Tests
        print("\n📋 PHASE 1: EVENT DEDUPLICATION ENGINE TESTS")
        if not self.test_enhanced_event_logging():
            all_success = False
        if not self.test_event_chain_integrity():
            all_success = False
        if not self.test_get_events_in_order():
            all_success = False
        
        # PHASE 2: Round Replay Engine Tests
        print("\n🎬 PHASE 2: ROUND REPLAY ENGINE TESTS")
        if not self.test_replay_generation():
            all_success = False
        
        # PHASE 3: Broadcast API Tests
        print("\n📡 PHASE 3: BROADCAST API TESTS")
        if not self.test_live_broadcast_data():
            all_success = False
        if not self.test_final_results():
            all_success = False
        
        # PHASE 4: Judge Session & Hot-Swap Tests
        print("\n🔄 PHASE 4: JUDGE SESSION & HOT-SWAP TESTS")
        if not self.test_create_judge_session():
            all_success = False
        if not self.test_restore_judge_session():
            all_success = False
        
        # PHASE 5: Telemetry Tests
        print("\n📊 PHASE 5: TELEMETRY TESTS")
        if not self.test_report_telemetry():
            all_success = False
        if not self.test_get_telemetry():
            all_success = False
        
        # PHASE 6: Backward Compatibility Tests
        print("\n🔄 PHASE 6: BACKWARD COMPATIBILITY TESTS")
        if not self.test_legacy_event_logging():
            all_success = False
        
        # PHASE 7: Error Handling Tests
        print("\n❌ PHASE 7: ERROR HANDLING TESTS")
        if not self.test_invalid_requests():
            all_success = False
        
        # PHASE 8: Performance Validation
        print("\n⚡ PHASE 8: PERFORMANCE VALIDATION")
        if not self.test_performance_validation():
            all_success = False
        
        # Print final results
        print(f"\n{'='*80}")
        print(f"🏁 FIGHTJUDGEAI PRO TEST RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Performance Summary
        print(f"\n📊 PERFORMANCE METRICS SUMMARY:")
        for metric, value in self.performance_metrics.items():
            print(f"   {metric}: {value:.2f}ms")
        
        # Success Criteria Summary
        print(f"\n✅ SUCCESS CRITERIA:")
        criteria_met = []
        criteria_failed = []
        
        if all_success:
            criteria_met.append("All endpoints return 200 OK for valid requests")
        else:
            criteria_failed.append("Some endpoints failed")
        
        # Check performance targets
        perf_targets = {
            'event_logging': 10,
            'replay_generation': 150,
            'broadcast_data': 100,
            'session_restore': 200,
            'telemetry_report': 20
        }
        
        for metric, target in perf_targets.items():
            if metric in self.performance_metrics:
                if self.performance_metrics[metric] <= target:
                    criteria_met.append(f"{metric} < {target}ms")
                else:
                    criteria_failed.append(f"{metric} > {target}ms")
        
        for criteria in criteria_met:
            print(f"   ✅ {criteria}")
        
        for criteria in criteria_failed:
            print(f"   ❌ {criteria}")
        
        if all_success and len(criteria_failed) == 0:
            print(f"\n🎉 ALL SUCCESS CRITERIA MET! FightJudgeAI PRO systems are production-ready.")
        else:
            print(f"\n⚠️  Some criteria not met. Review issues above.")
        
        return all_success

if __name__ == "__main__":
    tester = FightJudgeAIProTester()
    success = tester.run_comprehensive_test_suite()
    sys.exit(0 if success else 1)