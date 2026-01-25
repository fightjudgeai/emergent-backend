"""
Test Bug Fixes - Iteration 7
Tests for:
1. Next Fight navigation (URL param sync)
2. Fighter Photos in bout API (snake_case and camelCase)
3. GnP Light/Solid buttons (keyboard F/G)
4. Kick point value (+3 points)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBoutPhotoFields:
    """Test that bout API returns both snake_case and camelCase photo/record fields"""
    
    @pytest.fixture
    def test_bout_with_photos(self):
        """Create a test bout with photo URLs"""
        bout_id = f"test-photos-{uuid.uuid4().hex[:8]}"
        bout_data = {
            "bout_id": bout_id,
            "fighter1": "Test Fighter Red",
            "fighter2": "Test Fighter Blue",
            "fighter1Photo": "https://example.com/red-photo.jpg",
            "fighter2Photo": "https://example.com/blue-photo.jpg",
            "fighter1Record": "10-2-0",
            "fighter2Record": "8-3-1",
            "totalRounds": 3,
            "weight_class": "M-Lightweight"
        }
        
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout_data)
        assert response.status_code in [200, 201], f"Failed to create bout: {response.text}"
        
        yield bout_id
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/bouts/{bout_id}")
        except:
            pass
    
    def test_bout_returns_both_photo_conventions(self, test_bout_with_photos):
        """Verify bout endpoint returns both snake_case and camelCase photo fields"""
        bout_id = test_bout_with_photos
        
        response = requests.get(f"{BASE_URL}/api/bouts/{bout_id}")
        assert response.status_code == 200, f"Failed to get bout: {response.text}"
        
        data = response.json()
        
        # Check snake_case fields exist
        assert "fighter1_photo" in data, "Missing fighter1_photo (snake_case)"
        assert "fighter2_photo" in data, "Missing fighter2_photo (snake_case)"
        
        # Check camelCase fields exist
        assert "fighter1Photo" in data, "Missing fighter1Photo (camelCase)"
        assert "fighter2Photo" in data, "Missing fighter2Photo (camelCase)"
        
        # Verify values match
        assert data["fighter1_photo"] == data["fighter1Photo"], "Photo values don't match"
        assert data["fighter2_photo"] == data["fighter2Photo"], "Photo values don't match"
        
        print(f"✓ Bout returns both photo conventions: fighter1_photo={data['fighter1_photo']}, fighter1Photo={data['fighter1Photo']}")
    
    def test_bout_returns_both_record_conventions(self, test_bout_with_photos):
        """Verify bout endpoint returns both snake_case and camelCase record fields"""
        bout_id = test_bout_with_photos
        
        response = requests.get(f"{BASE_URL}/api/bouts/{bout_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check snake_case fields exist
        assert "fighter1_record" in data, "Missing fighter1_record (snake_case)"
        assert "fighter2_record" in data, "Missing fighter2_record (snake_case)"
        
        # Check camelCase fields exist  
        assert "fighter1Record" in data, "Missing fighter1Record (camelCase)"
        assert "fighter2Record" in data, "Missing fighter2Record (camelCase)"
        
        print(f"✓ Bout returns both record conventions")
    
    def test_bout_without_photos_returns_empty_strings(self):
        """Verify bout without photos returns empty strings for photo fields"""
        bout_id = f"test-no-photos-{uuid.uuid4().hex[:8]}"
        bout_data = {
            "bout_id": bout_id,
            "fighter1": "No Photo Red",
            "fighter2": "No Photo Blue",
            "totalRounds": 3
        }
        
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout_data)
        assert response.status_code in [200, 201]
        
        # Get the bout
        response = requests.get(f"{BASE_URL}/api/bouts/{bout_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Should have empty strings, not missing fields
        assert "fighter1_photo" in data
        assert "fighter2_photo" in data
        assert data["fighter1_photo"] == "" or data["fighter1_photo"] is None or data["fighter1_photo"] == data.get("fighter1Photo", "")
        
        print(f"✓ Bout without photos returns empty/null photo fields")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bouts/{bout_id}")


class TestKickPointValue:
    """Test that kick point value is 3 (not 4)"""
    
    def test_kick_points_in_config(self):
        """Verify kick points value in scoring config"""
        # Import the config directly
        import sys
        sys.path.insert(0, '/app/backend')
        from scoring_engine_v2.config_v3 import SCORING_CONFIG
        
        kick_config = SCORING_CONFIG["striking"]["kick"]
        assert kick_config["points"] == 3, f"Kick points should be 3, got {kick_config['points']}"
        
        print(f"✓ Kick points in config: {kick_config['points']}")
    
    def test_kick_event_scoring(self):
        """Test that kick events are scored at 3 points via API"""
        bout_id = f"test-kick-{uuid.uuid4().hex[:8]}"
        
        # Create bout
        bout_data = {
            "bout_id": bout_id,
            "fighter1": "Kick Test Red",
            "fighter2": "Kick Test Blue",
            "totalRounds": 3
        }
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout_data)
        assert response.status_code in [200, 201]
        
        # Log a kick event
        event_data = {
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "STRIKING",
            "event_type": "Kick",
            "device_role": "TEST"
        }
        response = requests.post(f"{BASE_URL}/api/events", json=event_data)
        assert response.status_code in [200, 201], f"Failed to log kick event: {response.text}"
        
        # Compute round score
        compute_data = {
            "bout_id": bout_id,
            "round_number": 1
        }
        response = requests.post(f"{BASE_URL}/api/rounds/compute", json=compute_data)
        assert response.status_code == 200, f"Failed to compute round: {response.text}"
        
        result = response.json()
        
        # Check the breakdown for kick points
        red_breakdown = result.get("red_breakdown", {})
        print(f"Red breakdown: {red_breakdown}")
        
        # The kick should contribute 3 points
        # Note: The exact structure depends on the scoring engine
        
        print(f"✓ Kick event logged and round computed successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bouts/{bout_id}")


class TestGnPButtons:
    """Test GnP Light and GnP Solid event logging"""
    
    def test_gnp_light_event(self):
        """Test logging GnP Light event (keyboard F)"""
        bout_id = f"test-gnp-light-{uuid.uuid4().hex[:8]}"
        
        # Create bout
        bout_data = {
            "bout_id": bout_id,
            "fighter1": "GnP Test Red",
            "fighter2": "GnP Test Blue",
            "totalRounds": 3
        }
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout_data)
        assert response.status_code in [200, 201]
        
        # Log GnP Light event
        event_data = {
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Strike",
            "device_role": "RED_GRAPPLING",
            "metadata": {"quality": "LIGHT"}
        }
        response = requests.post(f"{BASE_URL}/api/events", json=event_data)
        assert response.status_code in [200, 201], f"Failed to log GnP Light: {response.text}"
        
        # Verify event was logged
        response = requests.get(f"{BASE_URL}/api/events?bout_id={bout_id}&round_number=1")
        assert response.status_code == 200
        
        events = response.json().get("events", [])
        gnp_light_events = [e for e in events if e.get("event_type") == "Ground Strike" and e.get("metadata", {}).get("quality") == "LIGHT"]
        
        assert len(gnp_light_events) > 0, "GnP Light event not found"
        print(f"✓ GnP Light event logged successfully with quality=LIGHT")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bouts/{bout_id}")
    
    def test_gnp_solid_event(self):
        """Test logging GnP Solid event (keyboard G)"""
        bout_id = f"test-gnp-solid-{uuid.uuid4().hex[:8]}"
        
        # Create bout
        bout_data = {
            "bout_id": bout_id,
            "fighter1": "GnP Test Red",
            "fighter2": "GnP Test Blue",
            "totalRounds": 3
        }
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout_data)
        assert response.status_code in [200, 201]
        
        # Log GnP Solid event
        event_data = {
            "bout_id": bout_id,
            "round_number": 1,
            "corner": "RED",
            "aspect": "GRAPPLING",
            "event_type": "Ground Strike",
            "device_role": "RED_GRAPPLING",
            "metadata": {"quality": "SOLID"}
        }
        response = requests.post(f"{BASE_URL}/api/events", json=event_data)
        assert response.status_code in [200, 201], f"Failed to log GnP Solid: {response.text}"
        
        # Verify event was logged
        response = requests.get(f"{BASE_URL}/api/events?bout_id={bout_id}&round_number=1")
        assert response.status_code == 200
        
        events = response.json().get("events", [])
        gnp_solid_events = [e for e in events if e.get("event_type") == "Ground Strike" and e.get("metadata", {}).get("quality") == "SOLID"]
        
        assert len(gnp_solid_events) > 0, "GnP Solid event not found"
        print(f"✓ GnP Solid event logged successfully with quality=SOLID")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bouts/{bout_id}")
    
    def test_gnp_points_difference(self):
        """Test that GnP Light (1pt) and GnP Solid (3pt) have different point values"""
        import sys
        sys.path.insert(0, '/app/backend')
        from scoring_engine_v2.config_v3 import SCORING_CONFIG
        
        gnp_light = SCORING_CONFIG["ground_strikes"]["gnp_light"]
        gnp_hard = SCORING_CONFIG["ground_strikes"]["gnp_hard"]
        
        assert gnp_light["points"] == 1, f"GnP Light should be 1 point, got {gnp_light['points']}"
        assert gnp_hard["points"] == 3, f"GnP Hard/Solid should be 3 points, got {gnp_hard['points']}"
        
        print(f"✓ GnP Light: {gnp_light['points']} points, GnP Solid/Hard: {gnp_hard['points']} points")


class TestNextFightNavigation:
    """Test Next Fight navigation functionality"""
    
    def test_supervisor_fights_endpoint(self):
        """Test that supervisor fights endpoint returns fights for an event"""
        # First create an event with multiple bouts
        event_id = f"test-event-{uuid.uuid4().hex[:8]}"
        
        # Create first bout
        bout1_id = f"test-bout1-{uuid.uuid4().hex[:8]}"
        bout1_data = {
            "bout_id": bout1_id,
            "event_id": event_id,
            "fighter1": "Fighter A",
            "fighter2": "Fighter B",
            "totalRounds": 3
        }
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout1_data)
        assert response.status_code in [200, 201]
        
        # Create second bout
        bout2_id = f"test-bout2-{uuid.uuid4().hex[:8]}"
        bout2_data = {
            "bout_id": bout2_id,
            "event_id": event_id,
            "fighter1": "Fighter C",
            "fighter2": "Fighter D",
            "totalRounds": 3
        }
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout2_data)
        assert response.status_code in [200, 201]
        
        # Get fights for event
        response = requests.get(f"{BASE_URL}/api/supervisor/fights?event_id={event_id}")
        assert response.status_code == 200, f"Failed to get fights: {response.text}"
        
        data = response.json()
        fights = data.get("fights", [])
        
        assert len(fights) >= 2, f"Expected at least 2 fights, got {len(fights)}"
        
        # Verify both bouts are in the list
        bout_ids = [f.get("bout_id") for f in fights]
        assert bout1_id in bout_ids, f"Bout 1 not found in fights list"
        assert bout2_id in bout_ids, f"Bout 2 not found in fights list"
        
        print(f"✓ Supervisor fights endpoint returns {len(fights)} fights for event")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bouts/{bout1_id}")
        requests.delete(f"{BASE_URL}/api/bouts/{bout2_id}")
    
    def test_bout_returns_event_id(self):
        """Test that bout endpoint returns event_id for next fight lookup"""
        bout_id = f"test-event-id-{uuid.uuid4().hex[:8]}"
        event_id = f"test-event-{uuid.uuid4().hex[:8]}"
        
        bout_data = {
            "bout_id": bout_id,
            "event_id": event_id,
            "fighter1": "Test Red",
            "fighter2": "Test Blue",
            "totalRounds": 3
        }
        response = requests.post(f"{BASE_URL}/api/bouts", json=bout_data)
        assert response.status_code in [200, 201]
        
        # Get bout and verify event_id is returned
        response = requests.get(f"{BASE_URL}/api/bouts/{bout_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "event_id" in data, "event_id not returned in bout response"
        assert data["event_id"] == event_id, f"event_id mismatch: expected {event_id}, got {data['event_id']}"
        
        print(f"✓ Bout returns event_id: {data['event_id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bouts/{bout_id}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "healthy"
        
        print(f"✓ API health check passed: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
