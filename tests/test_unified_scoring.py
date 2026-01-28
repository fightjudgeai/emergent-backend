"""
Test Suite for Unified Scoring API - Fight Judge AI
Tests the server-authoritative multi-operator scoring system.

Features tested:
- POST /api/events - Create unified event from any device role
- GET /api/events - Get ALL events for a bout/round (NO device filter)
- POST /api/rounds/compute - Server-authoritative round computation from ALL events
- GET /api/rounds - Get all computed round results for a bout
- POST /api/fights/finalize - Finalize fight with winner determination
- Events from different device roles (RED_STRIKING, BLUE_GRAPPLING, etc.) are combined
- Round score computation uses delta-based scoring system
"""

import pytest
import requests
import os
import time
import uuid
from datetime import datetime

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://fight-scoring-pro.preview.emergentagent.com"


class TestUnifiedScoringAPI:
    """Test suite for unified scoring API endpoints"""
    
    # Generate unique bout ID for this test run
    TEST_BOUT_ID = f"test-unified-{uuid.uuid4().hex[:8]}"
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        yield
        self.session.close()
    
    # =========================================================================
    # 1. Test POST /api/events - Create events from different device roles
    # =========================================================================
    
    def test_create_event_red_striking(self):
        """Test creating event from RED_STRIKING device role"""
        event_data = {
            "bout_id": self.TEST_BOUT_ID,
            "round_number": 1,
            "corner": "RED",
            "aspect": "STRIKING",
            "event_type": "Jab",
            "device_role": "RED_STRIKING",
            "metadata": {"significant": True}
        }
        
        response = self.session.post(f"{BASE_URL}/api/events", json=event_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "event" in data
        assert data["event"]["corner"] == "RED"
        assert data["event"]["event_type"] == "Jab"
        assert data["event"]["device_role"] == "RED_STRIKING"
        print(f"[PASS] Created RED_STRIKING event: {data['event']['event_type']}")
    
    def test_create_event_red_grappling(self):
        """Test creating event from RED_GRAPPLING device role"""
        event_data = {
            "bout_id": self.TEST_BOUT_ID,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Takedown",
            "device_role": "RED_GRAPPLING",
            "metadata": {}
        }
        
        response = self.session.post(f"{BASE_URL}/api/events", json=event_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data["event"]["corner"] == "RED"
        assert data["event"]["event_type"] == "Takedown"
        assert data["event"]["device_role"] == "RED_GRAPPLING"
        print(f"[PASS] Created RED_GRAPPLING event: {data['event']['event_type']}")
    
    def test_create_event_blue_striking(self):
        """Test creating event from BLUE_STRIKING device role"""
        event_data = {
            "bout_id": self.TEST_BOUT_ID,
            "round_number": 1,
            "corner": "BLUE",
            "aspect": "STRIKING",
            "event_type": "Cross",
            "device_role": "BLUE_STRIKING",
            "metadata": {"significant": True}
        }
        
        response = self.session.post(f"{BASE_URL}/api/events", json=event_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data["event"]["corner"] == "BLUE"
        assert data["event"]["event_type"] == "Cross"
        assert data["event"]["device_role"] == "BLUE_STRIKING"
        print(f"[PASS] Created BLUE_STRIKING event: {data['event']['event_type']}")
    
    def test_create_event_blue_grappling(self):
        """Test creating event from BLUE_GRAPPLING device role"""
        event_data = {
            "bout_id": self.TEST_BOUT_ID,
            "round_number": 1,
            "corner": "BLUE",
            "aspect": "GRAPPLING",
            "event_type": "Submission Attempt",
            "device_role": "BLUE_GRAPPLING",
            "metadata": {"tier": "Deep"}
        }
        
        response = self.session.post(f"{BASE_URL}/api/events", json=event_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data["event"]["corner"] == "BLUE"
        assert data["event"]["event_type"] == "Submission Attempt"
        assert data["event"]["device_role"] == "BLUE_GRAPPLING"
        print(f"[PASS] Created BLUE_GRAPPLING event: {data['event']['event_type']}")
    
    def test_create_knockdown_event(self):
        """Test creating a knockdown event with tier metadata"""
        event_data = {
            "bout_id": self.TEST_BOUT_ID,
            "round_number": 1,
            "corner": "RED",
            "aspect": "STRIKING",
            "event_type": "KD",
            "device_role": "RED_STRIKING",
            "metadata": {"tier": "Hard"}
        }
        
        response = self.session.post(f"{BASE_URL}/api/events", json=event_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data["event"]["event_type"] == "KD"
        # Verify value was calculated (Hard KD = 70.0)
        assert data["event"]["value"] == 70.0, f"Expected KD value 70.0, got {data['event']['value']}"
        print(f"[PASS] Created KD event with value: {data['event']['value']}")
    
    # =========================================================================
    # 2. Test GET /api/events - Retrieve ALL events (NO device filter)
    # =========================================================================
    
    def test_get_all_events_no_device_filter(self):
        """Test that GET /api/events returns ALL events from ALL devices"""
        # First create events from multiple devices
        devices = ["RED_STRIKING", "RED_GRAPPLING", "BLUE_STRIKING", "BLUE_GRAPPLING"]
        for device in devices:
            corner = "RED" if "RED" in device else "BLUE"
            aspect = "STRIKING" if "STRIKING" in device else "GRAPPLING"
            event_data = {
                "bout_id": self.TEST_BOUT_ID,
                "round_number": 2,
                "corner": corner,
                "aspect": aspect,
                "event_type": "Jab" if aspect == "STRIKING" else "Takedown",
                "device_role": device,
                "metadata": {}
            }
            self.session.post(f"{BASE_URL}/api/events", json=event_data)
        
        # Now get all events
        response = self.session.get(f"{BASE_URL}/api/events", params={
            "bout_id": self.TEST_BOUT_ID,
            "round_number": 2
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "events" in data
        assert "total_events" in data
        assert data["total_events"] >= 4, f"Expected at least 4 events, got {data['total_events']}"
        
        # Verify events from ALL device roles are present
        device_roles_found = set()
        for event in data["events"]:
            if event.get("device_role"):
                device_roles_found.add(event["device_role"])
        
        print(f"[PASS] GET /api/events returned {data['total_events']} events from devices: {device_roles_found}")
        assert len(device_roles_found) >= 4, f"Expected events from 4 devices, found: {device_roles_found}"
    
    def test_get_events_for_specific_round(self):
        """Test filtering events by round number"""
        response = self.session.get(f"{BASE_URL}/api/events", params={
            "bout_id": self.TEST_BOUT_ID,
            "round_number": 1
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["round_number"] == 1
        # All events should be from round 1
        for event in data["events"]:
            assert event.get("round_number") == 1, f"Event from wrong round: {event}"
        
        print(f"[PASS] GET /api/events filtered by round 1: {data['total_events']} events")
    
    # =========================================================================
    # 3. Test POST /api/rounds/compute - Server-authoritative round computation
    # =========================================================================
    
    def test_compute_round_aggregates_all_events(self):
        """Test that round computation uses ALL events from ALL devices"""
        # Create a fresh bout for this test
        test_bout = f"test-compute-{uuid.uuid4().hex[:8]}"
        
        # Create events from all 4 device roles
        events_to_create = [
            {"corner": "RED", "aspect": "STRIKING", "event_type": "Jab", "device_role": "RED_STRIKING"},
            {"corner": "RED", "aspect": "STRIKING", "event_type": "Cross", "device_role": "RED_STRIKING"},
            {"corner": "RED", "aspect": "GRAPPLING", "event_type": "Takedown", "device_role": "RED_GRAPPLING"},
            {"corner": "BLUE", "aspect": "STRIKING", "event_type": "Hook", "device_role": "BLUE_STRIKING"},
            {"corner": "BLUE", "aspect": "GRAPPLING", "event_type": "Sweep/Reversal", "device_role": "BLUE_GRAPPLING"},
        ]
        
        for evt in events_to_create:
            event_data = {
                "bout_id": test_bout,
                "round_number": 1,
                "corner": evt["corner"],
                "aspect": evt["aspect"],
                "event_type": evt["event_type"],
                "device_role": evt["device_role"],
                "metadata": {}
            }
            resp = self.session.post(f"{BASE_URL}/api/events", json=event_data)
            assert resp.status_code == 200, f"Failed to create event: {resp.text}"
        
        # Compute the round
        compute_response = self.session.post(f"{BASE_URL}/api/rounds/compute", json={
            "bout_id": test_bout,
            "round_number": 1
        })
        
        assert compute_response.status_code == 200, f"Expected 200, got {compute_response.status_code}: {compute_response.text}"
        result = compute_response.json()
        
        # Verify result structure
        assert "red_points" in result
        assert "blue_points" in result
        assert "delta" in result
        assert "total_events" in result
        assert "red_breakdown" in result
        assert "blue_breakdown" in result
        
        # Verify ALL events were counted
        assert result["total_events"] == 5, f"Expected 5 events, got {result['total_events']}"
        
        # Verify breakdown includes events from both corners
        assert len(result["red_breakdown"]) > 0, "Red breakdown should have events"
        assert len(result["blue_breakdown"]) > 0, "Blue breakdown should have events"
        
        print(f"[PASS] Round computed: {result['red_points']}-{result['blue_points']} (delta: {result['delta']}) from {result['total_events']} events")
        print(f"       Red breakdown: {result['red_breakdown']}")
        print(f"       Blue breakdown: {result['blue_breakdown']}")
    
    def test_compute_round_delta_scoring(self):
        """Test that delta scoring system works correctly"""
        test_bout = f"test-delta-{uuid.uuid4().hex[:8]}"
        
        # Create events that should give RED a clear advantage
        # RED: 2 KDs (Hard) = 140 points
        # BLUE: 2 Jabs = 14 points
        events = [
            {"corner": "RED", "event_type": "KD", "device_role": "RED_STRIKING", "metadata": {"tier": "Hard"}},
            {"corner": "RED", "event_type": "KD", "device_role": "RED_STRIKING", "metadata": {"tier": "Hard"}},
            {"corner": "BLUE", "event_type": "Jab", "device_role": "BLUE_STRIKING", "metadata": {}},
            {"corner": "BLUE", "event_type": "Jab", "device_role": "BLUE_STRIKING", "metadata": {}},
        ]
        
        for evt in events:
            event_data = {
                "bout_id": test_bout,
                "round_number": 1,
                "corner": evt["corner"],
                "aspect": "STRIKING",
                "event_type": evt["event_type"],
                "device_role": evt["device_role"],
                "metadata": evt.get("metadata", {})
            }
            self.session.post(f"{BASE_URL}/api/events", json=event_data)
        
        # Compute round
        response = self.session.post(f"{BASE_URL}/api/rounds/compute", json={
            "bout_id": test_bout,
            "round_number": 1
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # RED should win with significant delta
        assert result["winner"] == "RED", f"Expected RED to win, got {result['winner']}"
        assert result["delta"] > 0, f"Expected positive delta for RED, got {result['delta']}"
        assert result["red_points"] == 10, f"Expected RED to get 10 points, got {result['red_points']}"
        
        # With 2 KDs, could be 10-8 if guardrails allow
        print(f"[PASS] Delta scoring: RED {result['red_points']}-{result['blue_points']} BLUE (delta: {result['delta']})")
    
    def test_compute_round_idempotent(self):
        """Test that computing the same round multiple times gives same result"""
        test_bout = f"test-idempotent-{uuid.uuid4().hex[:8]}"
        
        # Create some events
        for i in range(3):
            self.session.post(f"{BASE_URL}/api/events", json={
                "bout_id": test_bout,
                "round_number": 1,
                "corner": "RED",
                "aspect": "STRIKING",
                "event_type": "Jab",
                "device_role": "RED_STRIKING",
                "metadata": {}
            })
        
        # Compute twice
        result1 = self.session.post(f"{BASE_URL}/api/rounds/compute", json={
            "bout_id": test_bout,
            "round_number": 1
        }).json()
        
        result2 = self.session.post(f"{BASE_URL}/api/rounds/compute", json={
            "bout_id": test_bout,
            "round_number": 1
        }).json()
        
        # Results should be identical
        assert result1["red_points"] == result2["red_points"]
        assert result1["blue_points"] == result2["blue_points"]
        assert result1["delta"] == result2["delta"]
        assert result1["total_events"] == result2["total_events"]
        
        print(f"[PASS] Round computation is idempotent: {result1['red_points']}-{result1['blue_points']}")
    
    # =========================================================================
    # 4. Test GET /api/rounds - Get all computed round results
    # =========================================================================
    
    def test_get_all_rounds(self):
        """Test retrieving all computed rounds for a bout"""
        test_bout = f"test-rounds-{uuid.uuid4().hex[:8]}"
        
        # Create and compute 3 rounds
        for round_num in range(1, 4):
            # Create events for this round
            self.session.post(f"{BASE_URL}/api/events", json={
                "bout_id": test_bout,
                "round_number": round_num,
                "corner": "RED",
                "aspect": "STRIKING",
                "event_type": "Jab",
                "device_role": "RED_STRIKING",
                "metadata": {}
            })
            self.session.post(f"{BASE_URL}/api/events", json={
                "bout_id": test_bout,
                "round_number": round_num,
                "corner": "BLUE",
                "aspect": "STRIKING",
                "event_type": "Cross",
                "device_role": "BLUE_STRIKING",
                "metadata": {}
            })
            
            # Compute the round
            self.session.post(f"{BASE_URL}/api/rounds/compute", json={
                "bout_id": test_bout,
                "round_number": round_num
            })
        
        # Get all rounds
        response = self.session.get(f"{BASE_URL}/api/rounds", params={"bout_id": test_bout})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "rounds" in data
        assert len(data["rounds"]) == 3, f"Expected 3 rounds, got {len(data['rounds'])}"
        assert "running_red" in data
        assert "running_blue" in data
        
        # Verify rounds are sorted
        round_numbers = [r["round_number"] for r in data["rounds"]]
        assert round_numbers == [1, 2, 3], f"Rounds not sorted: {round_numbers}"
        
        print(f"[PASS] GET /api/rounds returned {len(data['rounds'])} rounds, totals: RED {data['running_red']} - BLUE {data['running_blue']}")
    
    # =========================================================================
    # 5. Test POST /api/fights/finalize - Finalize fight with winner
    # =========================================================================
    
    def test_finalize_fight(self):
        """Test finalizing a fight and determining winner"""
        test_bout = f"test-finalize-{uuid.uuid4().hex[:8]}"
        
        # Create and compute 3 rounds with RED winning each
        for round_num in range(1, 4):
            # RED gets more events
            for _ in range(3):
                self.session.post(f"{BASE_URL}/api/events", json={
                    "bout_id": test_bout,
                    "round_number": round_num,
                    "corner": "RED",
                    "aspect": "STRIKING",
                    "event_type": "Cross",
                    "device_role": "RED_STRIKING",
                    "metadata": {"significant": True}
                })
            
            # BLUE gets fewer events
            self.session.post(f"{BASE_URL}/api/events", json={
                "bout_id": test_bout,
                "round_number": round_num,
                "corner": "BLUE",
                "aspect": "STRIKING",
                "event_type": "Jab",
                "device_role": "BLUE_STRIKING",
                "metadata": {}
            })
            
            # Compute round
            self.session.post(f"{BASE_URL}/api/rounds/compute", json={
                "bout_id": test_bout,
                "round_number": round_num
            })
        
        # Finalize the fight
        response = self.session.post(f"{BASE_URL}/api/fights/finalize", json={
            "bout_id": test_bout
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        assert "final_red" in result
        assert "final_blue" in result
        assert "winner" in result
        assert "winner_name" in result
        assert "total_rounds" in result
        assert "finalized_at" in result
        
        # RED should win (30 vs 27 or similar)
        assert result["final_red"] >= result["final_blue"], f"Expected RED to win: {result['final_red']} vs {result['final_blue']}"
        
        print(f"[PASS] Fight finalized: RED {result['final_red']} - BLUE {result['final_blue']} | Winner: {result['winner_name']}")
    
    def test_get_fight_result(self):
        """Test retrieving finalized fight result"""
        test_bout = f"test-result-{uuid.uuid4().hex[:8]}"
        
        # Create, compute, and finalize a fight
        for round_num in range(1, 3):
            self.session.post(f"{BASE_URL}/api/events", json={
                "bout_id": test_bout,
                "round_number": round_num,
                "corner": "RED",
                "aspect": "STRIKING",
                "event_type": "Jab",
                "device_role": "RED_STRIKING",
                "metadata": {}
            })
            self.session.post(f"{BASE_URL}/api/rounds/compute", json={
                "bout_id": test_bout,
                "round_number": round_num
            })
        
        self.session.post(f"{BASE_URL}/api/fights/finalize", json={"bout_id": test_bout})
        
        # Get fight result
        response = self.session.get(f"{BASE_URL}/api/fights/{test_bout}/result")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        assert result.get("finalized") == True, "Fight should be marked as finalized"
        assert "final_red" in result
        assert "final_blue" in result
        
        print(f"[PASS] GET /api/fights/{test_bout}/result: finalized={result['finalized']}")
    
    # =========================================================================
    # 6. Test multi-device event combination
    # =========================================================================
    
    def test_events_from_all_four_devices_combined(self):
        """Test that events from all 4 device roles are combined in scoring"""
        test_bout = f"test-4devices-{uuid.uuid4().hex[:8]}"
        
        # Create events from all 4 device roles
        device_events = [
            {"device_role": "RED_STRIKING", "corner": "RED", "aspect": "STRIKING", "event_type": "Jab"},
            {"device_role": "RED_GRAPPLING", "corner": "RED", "aspect": "GRAPPLING", "event_type": "Takedown"},
            {"device_role": "BLUE_STRIKING", "corner": "BLUE", "aspect": "STRIKING", "event_type": "Hook"},
            {"device_role": "BLUE_GRAPPLING", "corner": "BLUE", "aspect": "GRAPPLING", "event_type": "Guard Passing"},
        ]
        
        for evt in device_events:
            response = self.session.post(f"{BASE_URL}/api/events", json={
                "bout_id": test_bout,
                "round_number": 1,
                "corner": evt["corner"],
                "aspect": evt["aspect"],
                "event_type": evt["event_type"],
                "device_role": evt["device_role"],
                "metadata": {}
            })
            assert response.status_code == 200, f"Failed to create event from {evt['device_role']}"
        
        # Compute round
        compute_response = self.session.post(f"{BASE_URL}/api/rounds/compute", json={
            "bout_id": test_bout,
            "round_number": 1
        })
        
        assert compute_response.status_code == 200
        result = compute_response.json()
        
        # Verify all 4 events were counted
        assert result["total_events"] == 4, f"Expected 4 events from 4 devices, got {result['total_events']}"
        
        # Verify both corners have events in breakdown
        assert "Jab" in result["red_breakdown"] or "Takedown" in result["red_breakdown"], "RED events missing"
        assert "Hook" in result["blue_breakdown"] or "Guard Passing" in result["blue_breakdown"], "BLUE events missing"
        
        print(f"[PASS] All 4 device roles combined: {result['total_events']} events")
        print(f"       RED: {result['red_breakdown']}")
        print(f"       BLUE: {result['blue_breakdown']}")
    
    # =========================================================================
    # 7. Test edge cases
    # =========================================================================
    
    def test_compute_round_no_events(self):
        """Test computing a round with no events returns 10-10 draw"""
        test_bout = f"test-empty-{uuid.uuid4().hex[:8]}"
        
        response = self.session.post(f"{BASE_URL}/api/rounds/compute", json={
            "bout_id": test_bout,
            "round_number": 1
        })
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["red_points"] == 10
        assert result["blue_points"] == 10
        assert result["winner"] == "DRAW"
        assert result["total_events"] == 0
        
        print(f"[PASS] Empty round computed as 10-10 DRAW")
    
    def test_event_value_calculation(self):
        """Test that event values are calculated correctly based on type and metadata"""
        test_bout = f"test-values-{uuid.uuid4().hex[:8]}"
        
        # Test different event types and their expected values
        test_cases = [
            {"event_type": "KD", "metadata": {"tier": "Near-Finish"}, "expected_value": 100.0},
            {"event_type": "KD", "metadata": {"tier": "Hard"}, "expected_value": 70.0},
            {"event_type": "KD", "metadata": {"tier": "Flash"}, "expected_value": 40.0},
            {"event_type": "Jab", "metadata": {"significant": True}, "expected_value": 10.0},
            {"event_type": "Jab", "metadata": {"significant": False}, "expected_value": 5.0},
            {"event_type": "Takedown", "metadata": {}, "expected_value": 25.0},
            {"event_type": "Submission Attempt", "metadata": {"tier": "Deep"}, "expected_value": 60.0},
        ]
        
        for i, tc in enumerate(test_cases):
            response = self.session.post(f"{BASE_URL}/api/events", json={
                "bout_id": test_bout,
                "round_number": 1,
                "corner": "RED",
                "aspect": "STRIKING",
                "event_type": tc["event_type"],
                "device_role": "RED_STRIKING",
                "metadata": tc["metadata"]
            })
            
            assert response.status_code == 200
            result = response.json()
            
            actual_value = result["event"]["value"]
            assert actual_value == tc["expected_value"], \
                f"Event {tc['event_type']} with {tc['metadata']}: expected {tc['expected_value']}, got {actual_value}"
            
            print(f"[PASS] {tc['event_type']} ({tc['metadata']}): value = {actual_value}")


class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print(f"[PASS] API root endpoint: {response.json()}")
    
    def test_status_endpoint(self):
        """Test status check endpoint"""
        response = requests.post(f"{BASE_URL}/api/status", json={
            "client_name": "pytest-unified-scoring"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["client_name"] == "pytest-unified-scoring"
        print(f"[PASS] Status endpoint: {data['id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
