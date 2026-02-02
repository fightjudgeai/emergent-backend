"""
Fight Judge AI - Scoring Service API Tests
==========================================

Tests for the scoring service API endpoints:
- /api/scoring/config - GET scoring configuration
- /api/scoring/round - POST score a round
- /api/scoring/calculate-delta - POST calculate point differential
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestScoringConfig:
    """Tests for /api/scoring/config endpoint"""
    
    def test_get_config_returns_200(self):
        """Config endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/scoring/config")
        assert response.status_code == 200
    
    def test_config_has_version(self):
        """Config should include version"""
        response = requests.get(f"{BASE_URL}/api/scoring/config")
        data = response.json()
        assert "version" in data
        assert data["version"] == "2.0"
    
    def test_config_has_thresholds(self):
        """Config should include scoring thresholds"""
        response = requests.get(f"{BASE_URL}/api/scoring/config")
        data = response.json()
        config = data.get("config", {})
        
        assert "draw_threshold" in config
        assert "threshold_10_8" in config
        assert "threshold_10_7" in config
    
    def test_config_has_event_points(self):
        """Config should include event point values"""
        response = requests.get(f"{BASE_URL}/api/scoring/config")
        data = response.json()
        config = data.get("config", {})
        
        assert "event_points" in config
        event_points = config["event_points"]
        
        # Check key strike types
        assert "Jab" in event_points
        assert "Cross" in event_points
        assert "Knockdown" in event_points


class TestScoreRound:
    """Tests for /api/scoring/round endpoint"""
    
    def test_score_round_returns_200(self):
        """Score round endpoint should return 200"""
        payload = {
            "round_number": 1,
            "red_significant_strikes": 10,
            "blue_significant_strikes": 5,
            "preview_only": True
        }
        response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=payload
        )
        assert response.status_code == 200
    
    def test_score_round_red_wins(self):
        """Red should win with more strikes"""
        payload = {
            "round_number": 1,
            "red_significant_strikes": 20,
            "blue_significant_strikes": 5,
            "preview_only": True
        }
        response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=payload
        )
        data = response.json()
        
        assert data["winner"] == "RED"
        assert data["red_score"] == 10
        assert data["blue_score"] == 9
    
    def test_score_round_blue_wins(self):
        """Blue should win with more strikes"""
        payload = {
            "round_number": 1,
            "red_significant_strikes": 5,
            "blue_significant_strikes": 20,
            "preview_only": True
        }
        response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=payload
        )
        data = response.json()
        
        assert data["winner"] == "BLUE"
        assert data["red_score"] == 9
        assert data["blue_score"] == 10
    
    def test_score_round_with_knockdown(self):
        """Knockdown should heavily favor winner"""
        payload = {
            "round_number": 1,
            "red_significant_strikes": 10,
            "blue_significant_strikes": 10,
            "red_knockdowns": 1,
            "blue_knockdowns": 0,
            "preview_only": True
        }
        response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=payload
        )
        data = response.json()
        
        assert data["winner"] == "RED"
    
    def test_score_round_returns_breakdown(self):
        """Score should include breakdown"""
        payload = {
            "round_number": 1,
            "red_significant_strikes": 15,
            "blue_significant_strikes": 10,
            "preview_only": True
        }
        response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=payload
        )
        data = response.json()
        
        assert "breakdown" in data
    
    def test_score_round_with_events(self):
        """Score round using events list"""
        payload = {
            "round_number": 1,
            "events": [
                {"corner": "RED", "event_type": "Jab", "metadata": {}},
                {"corner": "RED", "event_type": "Cross", "metadata": {}},
                {"corner": "BLUE", "event_type": "Jab", "metadata": {}}
            ],
            "preview_only": True
        }
        response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=payload
        )
        data = response.json()
        
        assert response.status_code == 200
        assert data["winner"] == "RED"
    
    def test_score_round_invalid_round_number(self):
        """Invalid round number should return error"""
        payload = {
            "round_number": 0,  # Invalid
            "red_significant_strikes": 10,
            "preview_only": True
        }
        response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=payload
        )
        assert response.status_code == 422  # Validation error


class TestCalculateDelta:
    """Tests for /api/scoring/calculate-delta endpoint"""
    
    def test_calculate_delta_returns_200(self):
        """Calculate delta endpoint should return 200"""
        events = [
            {"corner": "RED", "event_type": "Jab", "metadata": {}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        assert response.status_code == 200
    
    def test_calculate_delta_red_jab(self):
        """Red jab should give 10 points"""
        events = [
            {"corner": "RED", "event_type": "Jab", "metadata": {}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        
        assert data["red_delta"] == 10
        assert data["blue_delta"] == 0
        assert data["net_delta"] == 10
    
    def test_calculate_delta_blue_cross(self):
        """Blue cross should give 14 points"""
        events = [
            {"corner": "BLUE", "event_type": "Cross", "metadata": {}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        
        assert data["red_delta"] == 0
        assert data["blue_delta"] == 14
        assert data["net_delta"] == -14
    
    def test_calculate_delta_knockdown_tiers(self):
        """Knockdown tiers should have different values"""
        # Flash knockdown
        events = [
            {"corner": "RED", "event_type": "Knockdown", "metadata": {"tier": "Flash"}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        assert data["red_delta"] == 50
        
        # Hard knockdown
        events = [
            {"corner": "RED", "event_type": "Knockdown", "metadata": {"tier": "Hard"}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        assert data["red_delta"] == 75
        
        # Near-Finish knockdown
        events = [
            {"corner": "RED", "event_type": "Knockdown", "metadata": {"tier": "Near-Finish"}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        assert data["red_delta"] == 100
    
    def test_calculate_delta_mixed_events(self):
        """Mixed events should calculate correctly"""
        events = [
            {"corner": "RED", "event_type": "Jab", "metadata": {}},
            {"corner": "RED", "event_type": "Cross", "metadata": {}},
            {"corner": "BLUE", "event_type": "Knockdown", "metadata": {"tier": "Flash"}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        
        # Red: 10 (Jab) + 14 (Cross) = 24
        # Blue: 50 (Flash KD)
        assert data["red_delta"] == 24
        assert data["blue_delta"] == 50
        assert data["net_delta"] == -26
    
    def test_calculate_delta_returns_breakdown(self):
        """Delta calculation should include breakdown"""
        events = [
            {"corner": "RED", "event_type": "Takedown", "metadata": {}},
            {"corner": "BLUE", "event_type": "Jab", "metadata": {}}
        ]
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        
        assert "breakdown" in data
        breakdown = data["breakdown"]
        assert "red" in breakdown
        assert "blue" in breakdown
    
    def test_calculate_delta_empty_events(self):
        """Empty events should return zero delta"""
        events = []
        response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        data = response.json()
        
        assert data["red_delta"] == 0
        assert data["blue_delta"] == 0
        assert data["net_delta"] == 0


class TestScoringIntegration:
    """Integration tests for scoring workflow"""
    
    def test_full_round_scoring_workflow(self):
        """Test complete round scoring workflow"""
        # Step 1: Get config
        config_response = requests.get(f"{BASE_URL}/api/scoring/config")
        assert config_response.status_code == 200
        
        # Step 2: Calculate delta from events
        events = [
            {"corner": "RED", "event_type": "Jab", "metadata": {}},
            {"corner": "RED", "event_type": "Cross", "metadata": {}},
            {"corner": "RED", "event_type": "Takedown", "metadata": {}},
            {"corner": "BLUE", "event_type": "Jab", "metadata": {}},
            {"corner": "BLUE", "event_type": "Jab", "metadata": {}}
        ]
        delta_response = requests.post(
            f"{BASE_URL}/api/scoring/calculate-delta",
            json=events
        )
        assert delta_response.status_code == 200
        delta_data = delta_response.json()
        
        # Red should be ahead
        assert delta_data["net_delta"] > 0
        
        # Step 3: Score the round
        round_payload = {
            "round_number": 1,
            "events": events,
            "preview_only": True
        }
        round_response = requests.post(
            f"{BASE_URL}/api/scoring/round",
            json=round_payload
        )
        assert round_response.status_code == 200
        round_data = round_response.json()
        
        # Verify round score matches delta
        assert round_data["winner"] == "RED"
        assert round_data["red_score"] == 10
        assert round_data["blue_score"] == 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
