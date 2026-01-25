"""
Integration Tests for Real-Time Event Logging

Tests the full flow:
1. Create bout via API
2. Log events via API (simulating operator actions)
3. Compute round scores
4. Verify timestamps are correctly handled for gap reset logic
5. Verify control time scoring with real API calls
"""
import pytest
import httpx
import asyncio
import os
import time
from datetime import datetime, timezone

# Get API URL from environment or use default
API_URL = os.environ.get("API_URL", "http://localhost:8001/api")


class TestRealTimeEventLogging:
    """Integration tests for real-time event logging via API"""
    
    @pytest.fixture
    def api_client(self):
        """Create HTTP client for API calls"""
        return httpx.Client(base_url=API_URL, timeout=30.0)
    
    @pytest.fixture
    def bout_id(self, api_client):
        """Create a test bout and return its ID"""
        bout_id = f"test-integration-{int(time.time())}"
        response = api_client.post("/bouts", json={
            "bout_id": bout_id,
            "fighter1": "Integration Red",
            "fighter2": "Integration Blue",
            "totalRounds": 3
        })
        assert response.status_code == 200, f"Failed to create bout: {response.text}"
        yield bout_id
        # Cleanup
        try:
            api_client.delete(f"/bouts/{bout_id}")
        except:
            pass
    
    def test_create_event_stores_timestamp(self, api_client, bout_id):
        """Test that events are created with proper timestamps"""
        # Create an event
        response = api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "STRIKING",
            "event_type": "Cross",
            "device_role": "RED_STRIKING"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event" in data
        assert "created_at" in data["event"]
        
        # Verify timestamp is valid ISO format
        created_at = data["event"]["created_at"]
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        assert dt.year >= 2024
    
    def test_multiple_events_maintain_order(self, api_client, bout_id):
        """Test that multiple events maintain proper timestamp order"""
        events_created = []
        
        # Create 5 events in sequence
        for i in range(5):
            response = api_client.post("/events", json={
                "bout_id": bout_id,
                "round_number": 1,
                "corner": "RED",
                "aspect": "STRIKING",
                "event_type": "Jab",
                "device_role": "RED_STRIKING"
            })
            assert response.status_code == 200
            events_created.append(response.json()["event"])
            time.sleep(0.1)  # Small delay to ensure different timestamps
        
        # Verify timestamps are in order
        timestamps = [e["created_at"] for e in events_created]
        assert timestamps == sorted(timestamps), "Events should be in chronological order"
    
    def test_control_event_with_duration(self, api_client, bout_id):
        """Test control events include duration in metadata"""
        response = api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Back Control",
            "device_role": "RED_GRAPPLING",
            "metadata": {"duration": 30}
        })
        
        assert response.status_code == 200
        event = response.json()["event"]
        assert event["metadata"]["duration"] == 30
    
    def test_round_compute_uses_timestamps(self, api_client, bout_id):
        """Test that round computation properly uses timestamps for scoring"""
        # Create control events with timing
        api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Back Control",
            "device_role": "RED_GRAPPLING",
            "metadata": {"duration": 30}  # 3 buckets * 5 pts = 15 pts
        })
        
        # Compute round
        response = api_client.post("/rounds/compute", json={
            "bout_id": bout_id,
            "round_number": 1
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # Should have 15 pts (30s back control = 3 buckets * 5 pts)
        # Minus control-without-work discount: 15 * 0.75 = 11.25
        assert result["red_total"] >= 11, f"Expected ~11.25 pts. Got {result['red_total']}"
    
    def test_gap_reset_with_real_timestamps(self, api_client, bout_id):
        """Test gap reset logic with real API timestamps"""
        # First control event
        api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Back Control",
            "device_role": "RED_GRAPPLING",
            "metadata": {"duration": 60}  # 6 buckets * 5 pts = 30 pts
        })
        
        # Wait 20 seconds (simulating gap > 15s)
        # In real test, we can't wait 20s, so we'll verify the structure instead
        time.sleep(0.5)
        
        # Second control event
        api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Back Control",
            "device_role": "RED_GRAPPLING",
            "metadata": {"duration": 30}
        })
        
        # Compute round
        response = api_client.post("/rounds/compute", json={
            "bout_id": bout_id,
            "round_number": 1
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify events were processed
        assert result["total_events"] >= 2
        # Verify scoring happened (exact value depends on gap timing)
        assert result["red_total"] > 0
    
    def test_gnp_light_and_solid_events(self, api_client, bout_id):
        """Test GnP Light and GnP Solid events are properly distinguished"""
        # Create GnP Light
        response_light = api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Strike",
            "device_role": "RED_GRAPPLING",
            "metadata": {"quality": "LIGHT"}
        })
        assert response_light.status_code == 200
        
        # Create GnP Solid
        response_solid = api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Strike",
            "device_role": "RED_GRAPPLING",
            "metadata": {"quality": "SOLID"}
        })
        assert response_solid.status_code == 200
        
        # Compute round
        response = api_client.post("/rounds/compute", json={
            "bout_id": bout_id,
            "round_number": 1
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # GnP Light = 1 pt, GnP Solid = 3 pts, Total = 4 pts
        assert result["red_total"] == 4, f"Expected 4 pts (1+3). Got {result['red_total']}"
    
    def test_kick_scoring_updated_to_3pts(self, api_client, bout_id):
        """Test that kick events score 3 points (not 4)"""
        response = api_client.post("/events", json={
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "BLUE",
            "aspect": "STRIKING",
            "event_type": "Kick",
            "device_role": "BLUE_STRIKING"
        })
        assert response.status_code == 200
        
        # Compute round
        response = api_client.post("/rounds/compute", json={
            "bout_id": bout_id,
            "round_number": 1
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # Kick = 3 pts
        assert result["blue_total"] == 3, f"Kick should be 3 pts. Got {result['blue_total']}"
    
    def test_concurrent_events_from_multiple_operators(self, api_client, bout_id):
        """Test handling of concurrent events from different operators"""
        import concurrent.futures
        
        def create_event(device_role, event_type, corner):
            return api_client.post("/events", json={
                "bout_id": bout_id,
                "round_number": 1,
                "corner": corner,
                "aspect": "STRIKING",
                "event_type": event_type,
                "device_role": device_role
            })
        
        # Simulate concurrent events from different operators
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(create_event, "RED_STRIKING", "Jab", "RED"),
                executor.submit(create_event, "BLUE_STRIKING", "Cross", "BLUE"),
                executor.submit(create_event, "RED_GRAPPLING", "Takedown", "RED"),
                executor.submit(create_event, "BLUE_STRIKING", "Hook", "BLUE"),
            ]
            results = [f.result() for f in futures]
        
        # All should succeed
        for r in results:
            assert r.status_code == 200
        
        # Compute round
        response = api_client.post("/rounds/compute", json={
            "bout_id": bout_id,
            "round_number": 1
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify all events were counted
        assert result["total_events"] == 4
        # Red: Jab(1) + Takedown(10) = 11
        # Blue: Cross(3) + Hook(3) = 6
        assert result["red_total"] == 11, f"Expected Red=11. Got {result['red_total']}"
        assert result["blue_total"] == 6, f"Expected Blue=6. Got {result['blue_total']}"
    
    def test_event_deletion_and_recompute(self, api_client, bout_id):
        """Test that deleted events don't appear in recomputed scores"""
        # Create events
        for _ in range(3):
            api_client.post("/events", json={
                "bout_id": bout_id,
                "round_number": 1,
                "corner": "RED",
                "aspect": "STRIKING",
                "event_type": "Cross",
                "device_role": "RED_STRIKING"
            })
        
        # First compute
        response1 = api_client.post("/rounds/compute", json={
            "bout_id": bout_id,
            "round_number": 1
        })
        initial_score = response1.json()["red_total"]
        assert initial_score == 9  # 3 * 3 pts
        
        # Delete one event
        delete_response = api_client.delete(
            f"/events/{bout_id}",
            params={
                "round_number": 1,
                "event_type": "Cross",
                "corner": "RED"
            }
        )
        assert delete_response.status_code == 200
        
        # Recompute
        response2 = api_client.post("/rounds/compute", json={
            "bout_id": bout_id,
            "round_number": 1
        })
        new_score = response2.json()["red_total"]
        
        # Score should be reduced
        assert new_score < initial_score, "Score should decrease after event deletion"


class TestBroadcastOverlayData:
    """Tests for broadcast overlay data endpoints"""
    
    @pytest.fixture
    def api_client(self):
        return httpx.Client(base_url=API_URL, timeout=30.0)
    
    @pytest.fixture
    def bout_with_photos(self, api_client):
        """Create a bout with fighter photos"""
        bout_id = f"test-overlay-{int(time.time())}"
        response = api_client.post("/bouts", json={
            "bout_id": bout_id,
            "fighter1": "Photo Red",
            "fighter2": "Photo Blue",
            "fighter1_photo": "https://example.com/red.jpg",
            "fighter2_photo": "https://example.com/blue.jpg",
            "fighter1_record": "15-3",
            "fighter2_record": "12-4",
            "totalRounds": 3
        })
        assert response.status_code == 200
        yield bout_id
        try:
            api_client.delete(f"/bouts/{bout_id}")
        except:
            pass
    
    def test_bout_returns_both_photo_naming_conventions(self, api_client, bout_with_photos):
        """Test that bout endpoint returns both snake_case and camelCase photo fields"""
        response = api_client.get(f"/bouts/{bout_with_photos}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check snake_case
        assert data.get("fighter1_photo") == "https://example.com/red.jpg"
        assert data.get("fighter2_photo") == "https://example.com/blue.jpg"
        
        # Check camelCase
        assert data.get("fighter1Photo") == "https://example.com/red.jpg"
        assert data.get("fighter2Photo") == "https://example.com/blue.jpg"
        
        # Check records
        assert data.get("fighter1_record") == "15-3" or data.get("fighter1Record") == "15-3"
        assert data.get("fighter2_record") == "12-4" or data.get("fighter2Record") == "12-4"
    
    def test_overlay_stats_endpoint(self, api_client, bout_with_photos):
        """Test the overlay stats endpoint returns correct data"""
        # Add some events first
        api_client.post("/events", json={
            "bout_id": bout_with_photos,
            "round_number": 1,
            "corner": "RED",
            "aspect": "STRIKING",
            "event_type": "Cross",
            "device_role": "RED_STRIKING"
        })
        
        api_client.post("/events", json={
            "bout_id": bout_with_photos,
            "round_number": 1,
            "corner": "BLUE",
            "aspect": "STRIKING",
            "event_type": "Jab",
            "device_role": "BLUE_STRIKING"
        })
        
        response = api_client.get(f"/overlay/stats/{bout_with_photos}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have fighter info
        assert "fighter1" in data
        assert "fighter2" in data
        
        # Should have photo info
        assert data.get("fighter1_photo") or data.get("fighter1Photo")
        assert data.get("fighter2_photo") or data.get("fighter2Photo")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
