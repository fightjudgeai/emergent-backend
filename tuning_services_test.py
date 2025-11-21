import requests
import sys
import json
import time
from datetime import datetime

class TuningServicesAPITester:
    def __init__(self, base_url="https://combatscore.preview.emergentagent.com"):
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
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

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

    def test_calibration_api_health(self):
        """Test Calibration API health endpoint"""
        print("\n🔧 Testing Calibration API - Health Check...")
        success, response = self.run_test("Calibration API Health", "GET", "calibration/health", 200)
        
        if success and response:
            print(f"   ✅ Health check successful")
            print(f"   Status: {response.get('status', 'N/A')}")
            print(f"   Service: {response.get('service', 'N/A')}")
            print(f"   Version: {response.get('version', 'N/A')}")
            
            # Verify response structure
            required_fields = ['status', 'service', 'version']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in health response: {missing_fields}")
                return False
            
            if response.get('service') != 'Calibration API':
                print(f"   ⚠️  Incorrect service name: expected 'Calibration API', got '{response.get('service')}'")
                return False
        
        return success

    def test_calibration_api_get_config(self):
        """Test getting current calibration configuration"""
        print("\n📋 Testing Calibration API - Get Configuration...")
        success, response = self.run_test("Get Calibration Config", "GET", "calibration/get", 200)
        
        if success and response:
            print(f"   ✅ Configuration retrieved successfully")
            
            # Verify response structure
            required_fields = ['kd_threshold', 'rocked_threshold', 'highimpact_strike_threshold', 
                             'momentum_swing_window_ms', 'multicam_merge_window_ms', 'confidence_threshold',
                             'deduplication_window_ms', 'version', 'last_modified', 'modified_by']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in config response: {missing_fields}")
                return False
            
            # Verify default values
            expected_defaults = {
                'kd_threshold': 0.75,
                'rocked_threshold': 0.65,
                'highimpact_strike_threshold': 0.70,
                'momentum_swing_window_ms': 1200,
                'multicam_merge_window_ms': 150,
                'confidence_threshold': 0.5,
                'deduplication_window_ms': 100,
                'version': '1.0.0'
            }
            
            for field, expected_value in expected_defaults.items():
                actual_value = response.get(field)
                if actual_value != expected_value:
                    print(f"   ⚠️  Incorrect default value for {field}: expected {expected_value}, got {actual_value}")
                    return False
                else:
                    print(f"   ✅ {field}: {actual_value}")
        
        return success

    def test_calibration_api_set_config(self):
        """Test updating calibration configuration"""
        print("\n⚙️ Testing Calibration API - Set Configuration...")
        
        # Test data with modified parameters
        new_config = {
            "kd_threshold": 0.80,
            "rocked_threshold": 0.70,
            "highimpact_strike_threshold": 0.75,
            "momentum_swing_window_ms": 1500,
            "multicam_merge_window_ms": 200,
            "confidence_threshold": 0.6,
            "deduplication_window_ms": 120,
            "version": "1.0.0",
            "modified_by": "test_operator"
        }
        
        success, response = self.run_test("Set Calibration Config", "POST", "calibration/set?modified_by=test_operator", 200, new_config)
        
        if success and response:
            print(f"   ✅ Configuration updated successfully")
            
            # Verify updated values
            for field, expected_value in new_config.items():
                if field in ['last_modified']:  # Skip timestamp fields
                    continue
                actual_value = response.get(field)
                if actual_value != expected_value:
                    print(f"   ⚠️  Update failed for {field}: expected {expected_value}, got {actual_value}")
                    return False
                else:
                    print(f"   ✅ Updated {field}: {actual_value}")
            
            # Verify modified_by was set
            if response.get('modified_by') != 'test_operator':
                print(f"   ⚠️  modified_by not set correctly")
                return False
            
            # Verify last_modified was updated
            if not response.get('last_modified'):
                print(f"   ⚠️  last_modified timestamp missing")
                return False
        
        return success

    def test_calibration_api_parameter_validation(self):
        """Test parameter validation for calibration config"""
        print("\n🔍 Testing Calibration API - Parameter Validation...")
        
        # Test invalid threshold (> 1.0)
        invalid_config = {
            "kd_threshold": 1.5,  # Invalid: > 1.0
            "rocked_threshold": 0.65,
            "highimpact_strike_threshold": 0.70,
            "momentum_swing_window_ms": 1200,
            "multicam_merge_window_ms": 150,
            "confidence_threshold": 0.5,
            "deduplication_window_ms": 100,
            "version": "1.0.0"
        }
        
        success1, _ = self.run_test("Invalid Threshold (>1.0)", "POST", "calibration/set", 422, invalid_config)
        
        # Test invalid threshold (< 0.0)
        invalid_config2 = {
            "kd_threshold": -0.1,  # Invalid: < 0.0
            "rocked_threshold": 0.65,
            "highimpact_strike_threshold": 0.70,
            "momentum_swing_window_ms": 1200,
            "multicam_merge_window_ms": 150,
            "confidence_threshold": 0.5,
            "deduplication_window_ms": 100,
            "version": "1.0.0"
        }
        
        success2, _ = self.run_test("Invalid Threshold (<0.0)", "POST", "calibration/set", 422, invalid_config2)
        
        # Test invalid timing window (too small)
        invalid_config3 = {
            "kd_threshold": 0.75,
            "rocked_threshold": 0.65,
            "highimpact_strike_threshold": 0.70,
            "momentum_swing_window_ms": 100,  # Invalid: < 500
            "multicam_merge_window_ms": 150,
            "confidence_threshold": 0.5,
            "deduplication_window_ms": 100,
            "version": "1.0.0"
        }
        
        success3, _ = self.run_test("Invalid Timing Window (too small)", "POST", "calibration/set", 422, invalid_config3)
        
        return success1 and success2 and success3

    def test_calibration_api_reset(self):
        """Test resetting calibration to defaults"""
        print("\n🔄 Testing Calibration API - Reset Configuration...")
        
        success, response = self.run_test("Reset Calibration Config", "POST", "calibration/reset", 200)
        
        if success and response:
            print(f"   ✅ Configuration reset successfully")
            
            # Verify default values are restored
            expected_defaults = {
                'kd_threshold': 0.75,
                'rocked_threshold': 0.65,
                'highimpact_strike_threshold': 0.70,
                'momentum_swing_window_ms': 1200,
                'multicam_merge_window_ms': 150,
                'confidence_threshold': 0.5,
                'deduplication_window_ms': 100,
                'version': '1.0.0'
            }
            
            for field, expected_value in expected_defaults.items():
                actual_value = response.get(field)
                if actual_value != expected_value:
                    print(f"   ⚠️  Reset failed for {field}: expected {expected_value}, got {actual_value}")
                    return False
                else:
                    print(f"   ✅ Reset {field}: {actual_value}")
        
        return success

    def test_calibration_api_history(self):
        """Test getting calibration change history"""
        print("\n📚 Testing Calibration API - Change History...")
        
        success, response = self.run_test("Get Calibration History", "GET", "calibration/history?limit=50", 200)
        
        if success and response:
            print(f"   ✅ History retrieved successfully")
            print(f"   History entries: {len(response)}")
            
            # Verify history structure if entries exist
            if response:
                first_entry = response[0]
                required_fields = ['timestamp', 'parameter', 'old_value', 'new_value', 'modified_by']
                missing_fields = [field for field in required_fields if field not in first_entry]
                
                if missing_fields:
                    print(f"   ⚠️  Missing fields in history entry: {missing_fields}")
                    return False
                
                print(f"   Sample entry: {first_entry['parameter']} changed from {first_entry['old_value']} to {first_entry['new_value']} by {first_entry['modified_by']}")
            else:
                print(f"   ℹ️  No history entries found (expected for fresh system)")
        
        return success

    def test_performance_profiler_health(self):
        """Test Performance Profiler health endpoint"""
        print("\n⚡ Testing Performance Profiler - Health Check...")
        success, response = self.run_test("Performance Profiler Health", "GET", "perf/health", 200)
        
        if success and response:
            print(f"   ✅ Health check successful")
            print(f"   Status: {response.get('status', 'N/A')}")
            print(f"   Service: {response.get('service', 'N/A')}")
            print(f"   Version: {response.get('version', 'N/A')}")
            
            # Verify response structure
            required_fields = ['status', 'service', 'version']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in health response: {missing_fields}")
                return False
            
            if response.get('service') != 'Performance Profiler':
                print(f"   ⚠️  Incorrect service name: expected 'Performance Profiler', got '{response.get('service')}'")
                return False
        
        return success

    def test_performance_profiler_record_metrics(self):
        """Test recording performance metrics"""
        print("\n📊 Testing Performance Profiler - Record Metrics...")
        
        # Test CV inference recording
        success1, response1 = self.run_test("Record CV Inference", "POST", "perf/record/cv_inference?duration_ms=45.5", 200)
        if success1 and response1:
            if not response1.get('success'):
                print(f"   ⚠️  CV inference recording failed")
                return False
            print(f"   ✅ CV inference recorded: 45.5ms")
        
        # Test event ingestion recording
        success2, response2 = self.run_test("Record Event Ingestion", "POST", "perf/record/event_ingestion?duration_ms=12.3", 200)
        if success2 and response2:
            if not response2.get('success'):
                print(f"   ⚠️  Event ingestion recording failed")
                return False
            print(f"   ✅ Event ingestion recorded: 12.3ms")
        
        # Test scoring calculation recording
        success3, response3 = self.run_test("Record Scoring Calc", "POST", "perf/record/scoring?duration_ms=28.7", 200)
        if success3 and response3:
            if not response3.get('success'):
                print(f"   ⚠️  Scoring calculation recording failed")
                return False
            print(f"   ✅ Scoring calculation recorded: 28.7ms")
        
        # Test WebSocket roundtrip recording
        success4, response4 = self.run_test("Record WebSocket Roundtrip", "POST", "perf/record/websocket?duration_ms=18.9", 200)
        if success4 and response4:
            if not response4.get('success'):
                print(f"   ⚠️  WebSocket roundtrip recording failed")
                return False
            print(f"   ✅ WebSocket roundtrip recorded: 18.9ms")
        
        return success1 and success2 and success3 and success4

    def test_performance_profiler_summary(self):
        """Test getting performance summary with statistics"""
        print("\n📈 Testing Performance Profiler - Performance Summary...")
        
        success, response = self.run_test("Get Performance Summary", "GET", "perf/summary", 200)
        
        if success and response:
            print(f"   ✅ Performance summary retrieved successfully")
            
            # Verify response structure
            required_fields = [
                'cv_inference_avg_ms', 'cv_inference_p95_ms', 'cv_inference_p99_ms',
                'event_ingestion_avg_ms', 'event_ingestion_p95_ms', 'event_ingestion_p99_ms',
                'scoring_calc_avg_ms', 'scoring_calc_p95_ms', 'scoring_calc_p99_ms',
                'websocket_roundtrip_avg_ms', 'websocket_roundtrip_p95_ms', 'websocket_roundtrip_p99_ms',
                'total_measurements', 'measurement_period_sec'
            ]
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields in summary response: {missing_fields}")
                return False
            
            # Display metrics
            print(f"   CV Inference - Avg: {response['cv_inference_avg_ms']:.2f}ms, P95: {response['cv_inference_p95_ms']:.2f}ms, P99: {response['cv_inference_p99_ms']:.2f}ms")
            print(f"   Event Ingestion - Avg: {response['event_ingestion_avg_ms']:.2f}ms, P95: {response['event_ingestion_p95_ms']:.2f}ms, P99: {response['event_ingestion_p99_ms']:.2f}ms")
            print(f"   Scoring Calc - Avg: {response['scoring_calc_avg_ms']:.2f}ms, P95: {response['scoring_calc_p95_ms']:.2f}ms, P99: {response['scoring_calc_p99_ms']:.2f}ms")
            print(f"   WebSocket Roundtrip - Avg: {response['websocket_roundtrip_avg_ms']:.2f}ms, P95: {response['websocket_roundtrip_p95_ms']:.2f}ms, P99: {response['websocket_roundtrip_p99_ms']:.2f}ms")
            print(f"   Total Measurements: {response['total_measurements']}")
            print(f"   Measurement Period: {response['measurement_period_sec']:.2f}s")
            
            # Verify percentile logic (p99 >= p95 >= avg)
            metrics = ['cv_inference', 'event_ingestion', 'scoring_calc', 'websocket_roundtrip']
            for metric in metrics:
                avg = response[f'{metric}_avg_ms']
                p95 = response[f'{metric}_p95_ms']
                p99 = response[f'{metric}_p99_ms']
                
                if avg > 0:  # Only check if we have data
                    if not (p99 >= p95 >= avg):
                        print(f"   ⚠️  Percentile logic error for {metric}: avg={avg}, p95={p95}, p99={p99}")
                        return False
                    print(f"   ✅ {metric} percentiles valid")
        
        return success

    def test_performance_profiler_metrics_accumulation(self):
        """Test that metrics accumulate correctly"""
        print("\n🔢 Testing Performance Profiler - Metrics Accumulation...")
        
        # Get initial summary
        success1, initial_summary = self.run_test("Initial Summary", "GET", "perf/summary", 200)
        if not success1:
            return False
        
        initial_total = initial_summary.get('total_measurements', 0)
        print(f"   Initial total measurements: {initial_total}")
        
        # Record several metrics
        test_metrics = [
            ("cv_inference", 35.2),
            ("event_ingestion", 8.7),
            ("scoring", 22.1),
            ("websocket", 15.4),
            ("cv_inference", 42.8),
            ("event_ingestion", 11.3)
        ]
        
        for metric_type, duration in test_metrics:
            success, response = self.run_test(f"Record {metric_type}", "POST", f"perf/record/{metric_type}?duration_ms={duration}", 200)
            if not success or not response.get('success'):
                print(f"   ❌ Failed to record {metric_type}: {duration}ms")
                return False
        
        print(f"   ✅ Recorded {len(test_metrics)} metrics")
        
        # Get updated summary
        success2, updated_summary = self.run_test("Updated Summary", "GET", "perf/summary", 200)
        if not success2:
            return False
        
        updated_total = updated_summary.get('total_measurements', 0)
        print(f"   Updated total measurements: {updated_total}")
        
        # Verify total increased
        expected_increase = len(test_metrics)
        actual_increase = updated_total - initial_total
        
        if actual_increase != expected_increase:
            print(f"   ⚠️  Measurement count mismatch: expected increase of {expected_increase}, got {actual_increase}")
            return False
        
        print(f"   ✅ Metrics accumulated correctly (+{actual_increase})")
        
        # Verify specific metrics have realistic values
        if updated_summary['cv_inference_avg_ms'] > 0:
            print(f"   ✅ CV inference metrics updated: avg={updated_summary['cv_inference_avg_ms']:.2f}ms")
        
        if updated_summary['event_ingestion_avg_ms'] > 0:
            print(f"   ✅ Event ingestion metrics updated: avg={updated_summary['event_ingestion_avg_ms']:.2f}ms")
        
        return True

    def test_calibration_and_performance_integration(self):
        """Test integration between Calibration API and Performance Profiler"""
        print("\n🔗 Testing Calibration & Performance Integration...")
        
        # Step 1: Get initial calibration config
        success1, initial_config = self.run_test("Get Initial Config", "GET", "calibration/get", 200)
        if not success1:
            return False
        
        print(f"   ✅ Initial config retrieved")
        
        # Step 2: Record some performance metrics
        performance_data = [
            ("cv_inference", 55.3),
            ("event_ingestion", 14.2),
            ("scoring", 31.8),
            ("websocket", 19.7)
        ]
        
        for metric_type, duration in performance_data:
            success, response = self.run_test(f"Record {metric_type}", "POST", f"perf/record/{metric_type}?duration_ms={duration}", 200)
            if not success:
                return False
        
        print(f"   ✅ Performance metrics recorded")
        
        # Step 3: Adjust calibration based on "performance analysis"
        adjusted_config = {
            "kd_threshold": 0.78,  # Slightly higher based on "performance data"
            "rocked_threshold": 0.68,
            "highimpact_strike_threshold": 0.72,
            "momentum_swing_window_ms": 1300,
            "multicam_merge_window_ms": 180,
            "confidence_threshold": 0.55,
            "deduplication_window_ms": 110,
            "version": "1.0.0",
            "modified_by": "performance_tuner"
        }
        
        success2, updated_config = self.run_test("Adjust Config", "POST", "calibration/set?modified_by=performance_tuner", 200, adjusted_config)
        if not success2:
            return False
        
        print(f"   ✅ Calibration adjusted based on performance data")
        
        # Step 4: Verify history was tracked
        success3, history = self.run_test("Get History", "GET", "calibration/history?limit=10", 200)
        if not success3:
            return False
        
        if not history:
            print(f"   ⚠️  No calibration history found after changes")
            return False
        
        print(f"   ✅ Calibration history tracked: {len(history)} entries")
        
        # Step 5: Get final performance summary
        success4, final_summary = self.run_test("Final Performance Summary", "GET", "perf/summary", 200)
        if not success4:
            return False
        
        print(f"   ✅ Final performance summary retrieved")
        print(f"   Total measurements: {final_summary.get('total_measurements', 0)}")
        
        # Verify end-to-end workflow
        print(f"   🎉 End-to-end tuning workflow completed successfully!")
        print(f"   - Retrieved calibration config ✅")
        print(f"   - Recorded performance metrics ✅") 
        print(f"   - Adjusted calibration parameters ✅")
        print(f"   - Verified change history ✅")
        print(f"   - Confirmed performance tracking ✅")
        
        return True

    def test_calibration_api_complete_flow(self):
        """Test complete Calibration API functionality"""
        print("\n🔧 Testing Complete Calibration API Flow...")
        
        # Step 1: Health check
        if not self.test_calibration_api_health():
            return False
        
        # Step 2: Get initial config
        if not self.test_calibration_api_get_config():
            return False
        
        # Step 3: Update config
        if not self.test_calibration_api_set_config():
            return False
        
        # Step 4: Test parameter validation
        if not self.test_calibration_api_parameter_validation():
            return False
        
        # Step 5: Get history
        if not self.test_calibration_api_history():
            return False
        
        # Step 6: Reset config
        if not self.test_calibration_api_reset():
            return False
        
        print("   🎉 Complete Calibration API flow test passed!")
        return True

    def test_performance_profiler_complete_flow(self):
        """Test complete Performance Profiler functionality"""
        print("\n⚡ Testing Complete Performance Profiler Flow...")
        
        # Step 1: Health check
        if not self.test_performance_profiler_health():
            return False
        
        # Step 2: Record metrics
        if not self.test_performance_profiler_record_metrics():
            return False
        
        # Step 3: Get summary
        if not self.test_performance_profiler_summary():
            return False
        
        # Step 4: Test metrics accumulation
        if not self.test_performance_profiler_metrics_accumulation():
            return False
        
        print("   🎉 Complete Performance Profiler flow test passed!")
        return True

    def run_all_tests(self):
        """Run all tuning services tests"""
        print("🚀 Starting Tuning Services API Tests...")
        print(f"   Base URL: {self.base_url}")
        print(f"   API URL: {self.api_url}")
        
        # Calibration API tests
        self.test_calibration_api_complete_flow()
        
        # Performance Profiler tests
        self.test_performance_profiler_complete_flow()
        
        # Integration tests
        self.test_calibration_and_performance_integration()
        
        # Print final results
        print(f"\n{'='*60}")
        print(f"🏁 TUNING SERVICES TEST RESULTS")
        print(f"{'='*60}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"🎯 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print(f"🎉 ALL TUNING SERVICES TESTS PASSED!")
        else:
            print(f"⚠️  Some tests failed. Check the output above for details.")
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = TuningServicesAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)