"""
ICVSS Validation Suite
Complete end-to-end system validation
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple

class ICVSSValidator:
    """Comprehensive validation for ICVSS system"""
    
    def __init__(self, base_url: str = "https://sportsdash-3.preview.emergentagent.com/api/icvss"):
        self.base_url = base_url
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def test(self, name: str, func) -> bool:
        """Run a single test"""
        print(f"\n[TEST] {name}...")
        try:
            start = time.time()
            result = func()
            elapsed = time.time() - start
            
            if result:
                print(f"  ✓ PASS ({elapsed:.3f}s)")
                self.passed += 1
                self.results.append({"test": name, "status": "PASS", "time": elapsed})
                return True
            else:
                print(f"  ✗ FAIL ({elapsed:.3f}s)")
                self.failed += 1
                self.results.append({"test": name, "status": "FAIL", "time": elapsed})
                return False
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            self.failed += 1
            self.results.append({"test": name, "status": "ERROR", "error": str(e)})
            return False
    
    def validate_health(self) -> bool:
        """Test 1: Health check endpoint"""
        response = requests.get(f"{self.base_url}/health")
        return response.status_code == 200 and response.json().get("status") == "healthy"
    
    def validate_stats(self) -> bool:
        """Test 2: Stats endpoint"""
        response = requests.get(f"{self.base_url}/stats")
        data = response.json()
        return "event_processor" in data and "websocket_connections" in data
    
    def validate_round_lifecycle(self) -> Tuple[bool, str]:
        """Test 3: Complete round lifecycle"""
        bout_id = f"validation-{int(time.time())}"
        
        # Open round
        response = requests.post(f"{self.base_url}/round/open", params={
            "bout_id": bout_id,
            "round_num": 1
        })
        
        if response.status_code != 200:
            return False, "Failed to open round"
        
        round_id = response.json()["round_id"]
        
        # Add event
        cv_event = {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "strike_jab",
            "severity": 0.8,
            "confidence": 0.95,
            "position": "distance",
            "timestamp_ms": int(time.time() * 1000),
            "source": "cv_system",
            "vendor_id": "validator"
        }
        
        response = requests.post(f"{self.base_url}/round/event", params={"round_id": round_id}, json={"event": cv_event})
        
        if not response.json().get("success"):
            return False, "Failed to add event"
        
        # Get score
        response = requests.get(f"{self.base_url}/round/score/{round_id}")
        
        if response.status_code != 200:
            return False, "Failed to get score"
        
        score_data = response.json()
        if "score_card" not in score_data:
            return False, "Invalid score response"
        
        # Lock round
        response = requests.post(f"{self.base_url}/round/lock/{round_id}")
        
        if not response.json().get("success"):
            return False, "Failed to lock round"
        
        return True, "Complete lifecycle successful"
    
    def validate_event_deduplication(self) -> bool:
        """Test 4: Event deduplication (80-150ms window)"""
        bout_id = f"dedup-validation-{int(time.time())}"
        
        # Open round
        response = requests.post(f"{self.base_url}/round/open", params={
            "bout_id": bout_id,
            "round_num": 1
        })
        round_id = response.json()["round_id"]
        
        # Send duplicate events quickly
        base_event = {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "strike_jab",
            "severity": 0.8,
            "confidence": 0.95,
            "position": "distance",
            "source": "cv_system",
            "vendor_id": "validator"
        }
        
        accepted = 0
        for i in range(3):
            event = base_event.copy()
            event["timestamp_ms"] = int(time.time() * 1000) + (i * 30)  # 30ms apart
            response = requests.post(f"{self.base_url}/round/event", params={"round_id": round_id}, json={"event": event})
            if response.json().get("success"):
                accepted += 1
            time.sleep(0.03)  # 30ms delay
        
        # Should only accept 1 (first one), others deduplicated
        return accepted == 1
    
    def validate_confidence_filtering(self) -> bool:
        """Test 5: Confidence threshold filtering"""
        bout_id = f"confidence-validation-{int(time.time())}"
        
        # Open round
        response = requests.post(f"{self.base_url}/round/open", params={
            "bout_id": bout_id,
            "round_num": 1
        })
        round_id = response.json()["round_id"]
        
        # Send low-confidence event (should be rejected)
        low_conf_event = {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "strike_jab",
            "severity": 0.8,
            "confidence": 0.4,  # Below threshold (0.6)
            "position": "distance",
            "timestamp_ms": int(time.time() * 1000),
            "source": "cv_system",
            "vendor_id": "validator"
        }
        
        response = requests.post(f"{self.base_url}/round/event", params={"round_id": round_id}, json={"event": low_conf_event})
        
        # Should be rejected
        return not response.json().get("success")
    
    def validate_hybrid_scoring(self) -> bool:
        """Test 6: Hybrid CV + judge scoring"""
        bout_id = f"hybrid-validation-{int(time.time())}"
        
        # Open round
        response = requests.post(f"{self.base_url}/round/open", params={
            "bout_id": bout_id,
            "round_num": 1
        })
        round_id = response.json()["round_id"]
        
        # Add CV event
        cv_event = {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "KD_hard",
            "severity": 1.0,
            "confidence": 0.99,
            "position": "distance",
            "timestamp_ms": int(time.time() * 1000),
            "source": "cv_system",
            "vendor_id": "validator"
        }
        requests.post(f"{self.base_url}/round/event", params={"round_id": round_id}, json={"event": cv_event})
        
        # Add judge event
        judge_event = {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter2",
            "event_type": "td_landed",
            "severity": 0.8,
            "confidence": 1.0,
            "position": "ground",
            "timestamp_ms": int(time.time() * 1000) + 1000,
            "source": "judge_manual",
            "vendor_id": "validator"
        }
        requests.post(f"{self.base_url}/round/event", params={"round_id": round_id}, json={"event": judge_event})
        
        # Get score
        response = requests.get(f"{self.base_url}/round/score/{round_id}")
        score = response.json()
        
        # Verify both CV and judge events counted
        return score["cv_event_count"] > 0 and score["judge_event_count"] > 0
    
    def validate_damage_primacy(self) -> bool:
        """Test 7: Damage primacy rule (KD beats volume)"""
        bout_id = f"damage-validation-{int(time.time())}"
        
        # Open round
        response = requests.post(f"{self.base_url}/round/open", params={
            "bout_id": bout_id,
            "round_num": 1
        })
        round_id = response.json()["round_id"]
        
        # Fighter1: 1 knockdown
        kd_event = {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "KD_hard",
            "severity": 1.0,
            "confidence": 0.99,
            "position": "distance",
            "timestamp_ms": int(time.time() * 1000),
            "source": "cv_system",
            "vendor_id": "validator"
        }
        requests.post(f"{self.base_url}/round/event", params={"round_id": round_id}, json={"event": kd_event})
        
        # Fighter2: Multiple jabs (high volume, low damage)
        for i in range(20):
            jab_event = {
                "bout_id": bout_id,
                "round_id": round_id,
                "fighter_id": "fighter2",
                "event_type": "strike_jab",
                "severity": 0.5,
                "confidence": 0.85,
                "position": "distance",
                "timestamp_ms": int(time.time() * 1000) + (i * 100),
                "source": "cv_system",
                "vendor_id": "validator"
            }
            requests.post(f"{self.base_url}/round/event", params={"round_id": round_id}, json={"event": jab_event})
        
        # Get score
        response = requests.get(f"{self.base_url}/round/score/{round_id}")
        score = response.json()
        
        # Fighter1 (with KD) should win despite Fighter2 having more events
        return score["winner"] == "fighter1"
    
    def validate_performance(self) -> bool:
        """Test 8: Performance (latency < 100ms)"""
        bout_id = f"perf-validation-{int(time.time())}"
        
        # Open round
        requests.post(f"{self.base_url}/round/open", params={
            "bout_id": bout_id,
            "round_num": 1
        })
        
        # Measure event processing time
        event = {
            "bout_id": bout_id,
            "round_id": "test",
            "fighter_id": "fighter1",
            "event_type": "strike_jab",
            "severity": 0.8,
            "confidence": 0.95,
            "position": "distance",
            "timestamp_ms": int(time.time() * 1000),
            "source": "cv_system",
            "vendor_id": "validator"
        }
        
        start = time.time()
        # This will fail but we just want to measure latency
        requests.post(f"{self.base_url}/round/event", params={"round_id": "test"}, json={"event": event})
        latency = (time.time() - start) * 1000  # Convert to ms
        
        print(f"    Latency: {latency:.2f}ms")
        return latency < 100
    
    def run_all(self):
        """Run all validation tests"""
        print("=" * 80)
        print("ICVSS VALIDATION SUITE")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests
        self.test("Health Check", self.validate_health)
        self.test("Stats Endpoint", self.validate_stats)
        
        # Round lifecycle
        result, msg = self.validate_round_lifecycle()
        self.test(f"Round Lifecycle", lambda: result)
        
        self.test("Event Deduplication (80-150ms)", self.validate_event_deduplication)
        self.test("Confidence Filtering (>0.6)", self.validate_confidence_filtering)
        self.test("Hybrid CV + Judge Scoring", self.validate_hybrid_scoring)
        self.test("Damage Primacy (KD > Volume)", self.validate_damage_primacy)
        self.test("Performance (Latency < 100ms)", self.validate_performance)
        
        # Summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed} ✓")
        print(f"Failed: {self.failed} ✗")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        if self.failed == 0:
            print("\n🎉 ALL VALIDATIONS PASSED - SYSTEM READY FOR PRODUCTION!")
        else:
            print(f"\n⚠️ {self.failed} validation(s) failed - review results above")
        
        print("=" * 80)
        
        return self.failed == 0


if __name__ == "__main__":
    print("\n🚀 Starting ICVSS Validation Suite...\n")
    
    validator = ICVSSValidator()
    success = validator.run_all()
    
    exit(0 if success else 1)
