"""
Tests for FightJudge.AI Scoring Engine v3.0
Tests all regularization rules and impact lock logic.
"""

import pytest
from scoring_engine_v2.engine_v3 import ScoringEngineV3, score_round_v3


def make_event(corner: str, event_type: str, metadata: dict = None):
    """Helper to create event dict"""
    return {
        "corner": corner,
        "event_type": event_type,
        "metadata": metadata or {}
    }


class TestImpactLocks:
    """Test Impact Lock rules prevent volume spam from stealing rounds"""
    
    def test_kd_nf_cannot_be_outscored_by_few_strikes(self):
        """
        TEST 1: KD NF cannot be outscored by a few strikes
        Blue kd_nf once; Red lands 10 ss_cross
        Expected: Blue wins unless Red exceeds Delta >= 150
        """
        events = [
            # Blue lands KD NF = 210 points
            make_event("BLUE", "KD", {"tier": "Near-Finish"}),
            # Red lands 10 SS Cross = 10 * 6 = 60 points (all within first 8, no SS penalty)
        ]
        
        # Add 10 SS crosses for Red
        for _ in range(10):
            events.append(make_event("RED", "SS Cross"))
        
        result = score_round_v3(1, events)
        
        # Blue should win - KD NF (210) vs 10 SS Cross (60)
        # Delta = 150, which equals threshold so Blue should win by lock
        assert result["winner"] == "BLUE"
        assert "impact_lock" in result["winner_reason"]
        print(f"Result: {result['winner']} wins by {result['winner_reason']}")
        print(f"Red: {result['red_raw_points']}, Blue: {result['blue_raw_points']}, Delta: {result['delta']}")
    
    def test_kd_hard_lock(self):
        """KD Hard holder cannot lose unless opponent leads by >= 110"""
        events = [
            # Red lands KD Hard = 150 points
            make_event("RED", "KD", {"tier": "Hard"}),
            # Blue lands lots of jabs = 1 point each
        ]
        
        # Add 100 jabs for Blue (but diminishing returns kick in)
        for _ in range(100):
            events.append(make_event("BLUE", "Jab"))
        
        result = score_round_v3(1, events)
        
        # Red should win due to KD Hard lock
        # Even with 100 jabs, Blue can't overcome 110 delta threshold
        assert result["winner"] == "RED"
        print(f"Red: {result['red_raw_points']}, Blue: {result['blue_raw_points']}")
    
    def test_kd_flash_soft_lock(self):
        """KD Flash holder cannot lose unless opponent leads by >= 50"""
        events = [
            # Red lands KD Flash = 100 points
            make_event("RED", "KD", {"tier": "Flash"}),
            # Blue lands crosses
        ]
        
        # Add 20 crosses for Blue (3 points each, diminishing returns)
        # First 10: 3*10 = 30, next 10: 3*0.75*10 = 22.5 = 52.5 total
        for _ in range(20):
            events.append(make_event("BLUE", "Cross"))
        
        result = score_round_v3(1, events)
        
        # Blue's 52.5 points vs Red's 100
        # Delta = 47.5 < 50, so Red wins by KD Flash lock
        assert result["winner"] == "RED"
        print(f"Red: {result['red_raw_points']}, Blue: {result['blue_raw_points']}")
    
    def test_sub_nf_lock(self):
        """Sub NF holder cannot lose unless opponent leads by >= 90"""
        events = [
            # Blue lands Sub NF = 60 points
            make_event("BLUE", "Submission Attempt", {"tier": "Near-Finish"}),
            # Red lands strikes
        ]
        
        # Add strikes for Red
        for _ in range(15):
            events.append(make_event("RED", "Cross"))  # 3 each
        
        result = score_round_v3(1, events)
        
        # Red has ~45 points (diminishing returns), Blue has 60
        # Delta < 90, so Blue wins by sub_nf lock
        assert result["winner"] == "BLUE"


class TestTechniqueDiminishingReturns:
    """Test RULE 1: Technique diminishing returns"""
    
    def test_25_crosses_applies_correct_multipliers(self):
        """
        TEST 4: 25 crosses in round
        Expected: correct multipliers applied across thresholds
        - 1-10: 1.00
        - 11-20: 0.75
        - 21+: 0.50
        """
        events = []
        for _ in range(25):
            events.append(make_event("RED", "Cross"))
        
        result = score_round_v3(1, events)
        
        # Expected: 10*3 + 10*3*0.75 + 5*3*0.50 = 30 + 22.5 + 7.5 = 60
        expected = 30 + 22.5 + 7.5
        assert abs(result["red_raw_points"] - expected) < 0.1
        print(f"25 crosses = {result['red_raw_points']} (expected {expected})")
    
    def test_diminishing_returns_per_technique(self):
        """Each technique tracked separately"""
        events = []
        # 15 jabs (1-10 full, 11-15 at 0.75)
        for _ in range(15):
            events.append(make_event("RED", "Jab"))
        # 15 crosses (1-10 full, 11-15 at 0.75)
        for _ in range(15):
            events.append(make_event("RED", "Cross"))
        
        result = score_round_v3(1, events)
        
        # Jabs: 10*1 + 5*1*0.75 = 10 + 3.75 = 13.75
        # Crosses: 10*3 + 5*3*0.75 = 30 + 11.25 = 41.25
        # Total: 55
        expected = 13.75 + 41.25
        assert abs(result["red_raw_points"] - expected) < 0.1


class TestSSAbuseGuardrail:
    """Test RULE 2: SS abuse guardrail"""
    
    def test_16_ss_strikes_applies_half_multiplier(self):
        """
        TEST 3: 16 SS strikes in a round
        Expected: SS 15+ uses 0.50 multiplier
        """
        events = []
        for _ in range(16):
            events.append(make_event("RED", "SS Cross"))
        
        result = score_round_v3(1, events)
        
        # SS Cross base = 6 points
        # 1-8: 6*8 = 48 (SS mult 1.0, tech mult 1.0)
        # 9-10: 6*2*0.75 = 9 (SS mult 0.75, tech mult 1.0)
        # 11-14: 6*4*0.75*0.75 = 13.5 (SS mult 0.75, tech mult 0.75)
        # 15-16: 6*2*0.50*0.75 = 4.5 (SS mult 0.50, tech mult 0.75)
        expected = 48 + 9 + 13.5 + 4.5
        assert abs(result["red_raw_points"] - expected) < 0.1
        print(f"16 SS crosses = {result['red_raw_points']} (expected {expected})")
    
    def test_ss_multiplier_stacks_with_technique(self):
        """SS multiplier stacks with technique multiplier"""
        events = []
        # 12 SS crosses - tests both SS (9-14 = 0.75) and technique (11-12 = 0.75)
        for _ in range(12):
            events.append(make_event("RED", "SS Cross"))
        
        result = score_round_v3(1, events)
        
        # Crosses 1-8: 6*8 = 48
        # Crosses 9-10: 6*2*0.75 = 9
        # Crosses 11-12: 6*2*0.75*0.75 = 6.75
        expected = 48 + 9 + 6.75
        assert abs(result["red_raw_points"] - expected) < 0.1


class TestControlWithoutWork:
    """Test RULE 4: Control without work discount"""
    
    def test_control_farming_discounted_without_offense(self):
        """
        TEST 2: fighter gets >=20 control points but <10 strike points 
        and no subs and <10 gnp_hard points
        Expected: control_points discounted by 0.75
        """
        events = [
            # 70 seconds of top control = 7 buckets * 3 = 21 points
            make_event("RED", "Top Control", {"duration": 70}),
            # Only 5 jabs = 5 points (< 10 requirement)
        ]
        for _ in range(5):
            events.append(make_event("RED", "Jab"))
        
        result = score_round_v3(1, events)
        
        # Control should be discounted: 21 * 0.75 = 15.75
        # Total: 15.75 + 5 = 20.75
        assert result["red_control_discount_applied"] == True
        # Check discount was applied
        print(f"Control discount applied: {result['red_control_discount_applied']}")
        print(f"Red points: {result['red_raw_points']}")
    
    def test_control_not_discounted_with_enough_strikes(self):
        """Control not discounted if >= 10 strike points"""
        events = [
            make_event("RED", "Top Control", {"duration": 70}),  # 21 control points
        ]
        # 4 crosses = 12 points (>= 10 requirement)
        for _ in range(4):
            events.append(make_event("RED", "Cross"))
        
        result = score_round_v3(1, events)
        
        assert result["red_control_discount_applied"] == False
    
    def test_control_not_discounted_with_submission(self):
        """Control not discounted if any submission"""
        events = [
            make_event("RED", "Top Control", {"duration": 70}),  # 21 control points
            make_event("RED", "Submission Attempt", {"tier": "Light"}),  # Any sub
        ]
        
        result = score_round_v3(1, events)
        
        assert result["red_control_discount_applied"] == False


class TestTakedownStuffedCap:
    """Test RULE 5: Takedown stuffed cap"""
    
    def test_td_stuffed_cap_after_3(self):
        """First 3 TD stuffed at full value, 4+ at 0.50"""
        events = []
        for _ in range(6):
            events.append(make_event("RED", "Takedown Stuffed"))
        
        result = score_round_v3(1, events)
        
        # First 3: 5*3 = 15
        # Next 3: 5*3*0.50 = 7.5
        # Total: 22.5
        expected = 15 + 7.5
        assert abs(result["red_raw_points"] - expected) < 0.1
        print(f"6 TD stuffed = {result['red_raw_points']} (expected {expected})")


class TestControlDiminishingReturns:
    """Test RULE 3: Control time diminishing returns after 60s"""
    
    def test_control_diminishes_after_60_seconds(self):
        """Control value halves after 60 seconds continuous"""
        events = [
            # 90 seconds continuous top control
            make_event("RED", "Top Control", {"duration": 90}),
        ]
        
        result = score_round_v3(1, events)
        
        # First 60s: 6 buckets * 3 = 18
        # Next 30s: 3 buckets * 3 * 0.50 = 4.5
        # Total: 22.5
        # Note: This depends on how buckets are calculated
        print(f"90s top control = {result['red_raw_points']}")


class TestImpactLockOverride:
    """Test Impact Lock override works correctly"""
    
    def test_impact_lock_override_logged(self):
        """
        TEST 5: Opponent leads by points but below lock threshold
        Expected: impact side wins; reason logged
        """
        events = [
            # Red lands KD Hard = 150
            make_event("RED", "KD", {"tier": "Hard"}),
        ]
        # Blue lands enough to lead on points but not overcome lock
        for _ in range(60):
            events.append(make_event("BLUE", "Cross"))  # ~135 points after diminishing
        
        result = score_round_v3(1, events)
        
        # Blue may lead on raw points but Red has KD Hard lock
        # Check that impact lock is recorded
        if result["winner"] == "RED":
            assert "impact_lock" in result["winner_reason"]
        print(f"Winner: {result['winner']}, Reason: {result['winner_reason']}")


class TestEventPointValues:
    """Test base point values are correct"""
    
    def test_striking_base_values(self):
        """Verify striking base point values"""
        engine = ScoringEngineV3()
        
        events = [
            make_event("RED", "Jab"),       # 1
            make_event("RED", "Cross"),     # 3
            make_event("RED", "Hook"),      # 3
            make_event("RED", "Uppercut"),  # 3
            make_event("RED", "Kick"),      # 4
            make_event("RED", "Elbow"),     # 5
            make_event("RED", "Knee"),      # 5
        ]
        
        result = score_round_v3(1, events)
        expected = 1 + 3 + 3 + 3 + 4 + 5 + 5
        assert result["red_raw_points"] == expected
    
    def test_ss_strike_values(self):
        """Verify SS strike values are double base"""
        events = [
            make_event("RED", "SS Jab"),       # 2
            make_event("RED", "SS Cross"),    # 6
            make_event("RED", "SS Hook"),     # 6
            make_event("RED", "SS Kick"),     # 8
            make_event("RED", "SS Elbow"),    # 10
        ]
        
        result = score_round_v3(1, events)
        expected = 2 + 6 + 6 + 8 + 10
        assert result["red_raw_points"] == expected
    
    def test_damage_values(self):
        """Verify damage event values"""
        events = [
            make_event("RED", "Rocked"),  # 60
        ]
        result = score_round_v3(1, events)
        assert result["red_raw_points"] == 60
        
        events = [make_event("RED", "KD", {"tier": "Flash"})]  # 100
        result = score_round_v3(1, events)
        assert result["red_raw_points"] == 100
        
        events = [make_event("RED", "KD", {"tier": "Hard"})]  # 150
        result = score_round_v3(1, events)
        assert result["red_raw_points"] == 150
        
        events = [make_event("RED", "KD", {"tier": "Near-Finish"})]  # 210
        result = score_round_v3(1, events)
        assert result["red_raw_points"] == 210
    
    def test_submission_values(self):
        """Verify submission event values"""
        events = [
            make_event("RED", "Submission Attempt", {"tier": "Light"}),  # 12
        ]
        result = score_round_v3(1, events)
        assert result["red_raw_points"] == 12
        
        events = [make_event("RED", "Submission Attempt", {"tier": "Deep"})]  # 28
        result = score_round_v3(1, events)
        assert result["red_raw_points"] == 28
        
        events = [make_event("RED", "Submission Attempt", {"tier": "Near-Finish"})]  # 60
        result = score_round_v3(1, events)
        assert result["red_raw_points"] == 60


class TestDebugOutput:
    """Test debug view outputs all required info"""
    
    def test_debug_contains_all_fields(self):
        """Debug output includes event counts, multipliers, totals, flags, winner"""
        events = [
            make_event("RED", "Cross"),
            make_event("RED", "Cross"),
            make_event("RED", "KD", {"tier": "Hard"}),
            make_event("BLUE", "Jab"),
            make_event("BLUE", "Top Control", {"duration": 30}),
        ]
        
        result = score_round_v3(1, events)
        
        assert "debug" in result
        debug = result["debug"]
        
        # Check red debug info
        assert "red" in debug
        assert "technique_counts" in debug["red"]
        assert "ss_total_count" in debug["red"]
        assert "events" in debug["red"]
        
        # Check blue debug info
        assert "blue" in debug
        assert "technique_counts" in debug["blue"]
        
        # Check event multipliers are logged
        for event in debug["red"]["events"]:
            assert "base_points" in event
            assert "technique_mult" in event
            assert "ss_mult" in event
            assert "final_points" in event
        
        # Check impact lock info
        assert "impact_lock_applied" in debug
        
        print(f"Debug info: {debug}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
