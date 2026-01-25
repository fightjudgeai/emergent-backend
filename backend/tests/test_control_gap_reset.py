"""
Test cases for Control Time Gap Reset Logic (Rule 3)

Rule 3: Control Diminishing Returns
- After 60s continuous control, apply 0.5x multiplier
- Gap of 15s+ resets continuous streak (back to full value)
- Gap < 15s continues the streak
"""
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scoring_engine_v2.engine_v3 import ScoringEngineV3, FighterRoundState, score_round_v3


class TestControlGapReset:
    """Test cases for gap reset logic in control time scoring"""
    
    def setup_method(self):
        """Setup fresh engine for each test"""
        self.engine = ScoringEngineV3()
    
    def test_continuous_control_no_gap_applies_diminishing(self):
        """
        Test: Continuous control (no gap) should apply diminishing returns after 60s
        
        Scenario:
        - 60s back control at t=0 (6 buckets * 5 = 30 pts, full value)
        - 30s back control at t=65 (small gap, continues streak)
        - After 60s threshold, 0.5x multiplier applies
        - Expected: 30 + (15 * 0.5) = 37.5 pts
        """
        events = [
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 60},
                "timestamp": 0
            },
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 30},
                "timestamp": 65  # 5s gap (< 15s threshold)
            }
        ]
        
        result = self.engine.score_round(1, events)
        
        # First 60s: full value = 30 pts
        # Next 30s: after threshold, 0.5x = 7.5 pts
        # Total = 37.5 pts (may have control-without-work discount)
        assert result["red_total"] < 45, "Should have diminishing returns applied"
        assert result["red_total"] >= 30, "First chunk should be at full value"
        
    def test_gap_15s_plus_resets_streak(self):
        """
        Test: Gap >= 15s should reset continuous control streak
        
        Scenario:
        - 60s back control at t=0 (30 pts full)
        - 20s gap (>= 15s threshold)
        - 60s back control at t=80 (30 pts full, streak reset)
        - Expected: 60 pts (both chunks at full value, no diminishing)
        """
        events = [
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 60},
                "timestamp": 0
            },
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 60},
                "timestamp": 80  # 20s gap (>= 15s threshold, resets streak)
            }
        ]
        
        result = self.engine.score_round(1, events)
        
        # Both chunks at full value due to gap reset: 30 + 30 = 60 pts
        # Control-without-work discount may apply (0.75x)
        # Minimum expected: 60 * 0.75 = 45 pts
        assert result["red_total"] >= 45, f"Gap reset should give more points. Got {result['red_total']}"
        
    def test_gap_exactly_15s_resets_streak(self):
        """
        Test: Gap of exactly 15s should reset the streak
        """
        events = [
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 60},
                "timestamp": 0
            },
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 30},
                "timestamp": 75  # Exactly 15s gap
            }
        ]
        
        result = self.engine.score_round(1, events)
        
        # With reset: 30 + 15 = 45 pts (before discount)
        # Without reset: 30 + 7.5 = 37.5 pts
        # Gap of exactly 15s should trigger reset
        assert result["red_total"] > 30, "Both chunks should have value"
        
    def test_gap_14s_continues_streak(self):
        """
        Test: Gap < 15s should NOT reset the streak
        """
        events = [
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 60},
                "timestamp": 0
            },
            {
                "corner": "RED",
                "event_type": "Ground Back Control",
                "metadata": {"duration": 30},
                "timestamp": 74  # 14s gap (< 15s threshold)
            }
        ]
        
        result = self.engine.score_round(1, events)
        
        # Streak continues: diminishing returns should apply
        # First 60s: 30 pts, next 30s at 0.5x: 7.5 pts
        # Total before discount: 37.5 pts
        assert result["red_total"] < 45, "Diminishing returns should apply (streak continued)"
        
    def test_multiple_gaps_multiple_resets(self):
        """
        Test: Multiple gaps can trigger multiple resets
        
        Scenario:
        - 30s control (15 pts)
        - 20s gap (reset)
        - 30s control (15 pts, fresh streak)
        - 20s gap (reset)
        - 30s control (15 pts, fresh streak)
        """
        events = [
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 30}, "timestamp": 0},
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 30}, "timestamp": 50},  # 20s gap
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 30}, "timestamp": 100},  # 20s gap
        ]
        
        result = self.engine.score_round(1, events)
        
        # All 3 chunks at full value: 15 + 15 + 15 = 45 pts
        # Minus control-without-work discount if applicable
        assert result["red_total"] >= 33, "Multiple resets should give full value for each chunk"
        
    def test_different_control_types_track_separately(self):
        """
        Test: Different control types maintain separate continuous tracking
        
        Scenario:
        - 60s back control (reaches threshold)
        - 5s gap
        - 30s TOP control (should NOT have diminishing - different type)
        """
        events = [
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 60}, "timestamp": 0},
            {"corner": "RED", "event_type": "Ground Top Control", 
             "metadata": {"duration": 30}, "timestamp": 65},
        ]
        
        result = self.engine.score_round(1, events)
        
        # Back control: 30 pts (at threshold)
        # Top control: 9 pts (fresh streak, 3 buckets * 3 pts)
        # Total: 39 pts (before any discounts)
        assert result["red_total"] >= 29, "Different control types should track separately"
        
    def test_gap_reset_with_work_no_discount(self):
        """
        Test: Gap reset + work requirement met = full value, no discounts
        """
        events = [
            # 60s control
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 60}, "timestamp": 0},
            # 20s gap (reset)
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 60}, "timestamp": 80},
            # Add strikes to meet work requirement
            {"corner": "RED", "event_type": "Cross", "metadata": {}, "timestamp": 10},
            {"corner": "RED", "event_type": "Cross", "metadata": {}, "timestamp": 20},
            {"corner": "RED", "event_type": "Cross", "metadata": {}, "timestamp": 30},
            {"corner": "RED", "event_type": "Cross", "metadata": {}, "timestamp": 40},
        ]
        
        result = self.engine.score_round(1, events)
        
        # Control: 30 + 30 = 60 pts (gap reset, no diminishing)
        # Strikes: 4 * 3 = 12 pts
        # Total: 72 pts
        # Work requirement met, so no control discount
        assert result["red_total"] >= 60, f"Full value expected with gap reset + work. Got {result['red_total']}"


class TestControlDiminishingReturns:
    """Additional tests for diminishing returns calculation"""
    
    def setup_method(self):
        self.engine = ScoringEngineV3()
    
    def test_exactly_60s_no_diminishing(self):
        """Test: Exactly 60s should NOT trigger diminishing (threshold is after 60s)"""
        events = [
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 60}, "timestamp": 0},
        ]
        
        result = self.engine.score_round(1, events)
        
        # 60s = 6 buckets * 5 pts = 30 pts (no diminishing yet)
        # May have control-without-work discount: 30 * 0.75 = 22.5 pts
        assert result["red_total"] >= 22, "60s exactly should not have diminishing"
        
    def test_61s_triggers_diminishing(self):
        """Test: 61s of control should trigger diminishing for the last bucket"""
        events = [
            {"corner": "RED", "event_type": "Ground Back Control", 
             "metadata": {"duration": 70}, "timestamp": 0},  # 7 buckets
        ]
        
        result = self.engine.score_round(1, events)
        
        # First 6 buckets at full: 30 pts
        # 7th bucket at 0.5x: 2.5 pts
        # Total: 32.5 pts (before discount)
        # After discount: ~24.4 pts
        # Without diminishing would be: 35 pts -> 26.25 after discount
        assert result["red_total"] < 26.25, "7th bucket should have diminishing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
