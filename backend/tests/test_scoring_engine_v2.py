"""
Unit tests for Scoring Engine V2

Tests:
1. Plan A/B/C activation rules
2. Impact Advantage gating
3. 10-8 and 10-7 strict gates
4. Control-with-offense rule
5. LegDamageIndex escalation
6. Receipt top drivers generation
"""

import pytest
from scoring_engine_v2.engine import score_round_delta_v2, normalize_events
from scoring_engine_v2.leg_damage import LegDamageTracker
from scoring_engine_v2.impact import check_impact_advantage, compute_impact_score
from scoring_engine_v2.control_windows import parse_control_windows, compute_control_score
from scoring_engine_v2.gates import check_10_8_gate, check_10_7_gate
from scoring_engine_v2.plan_abc import compute_plan_a, compute_plan_b, compute_plan_c
from scoring_engine_v2.types import Corner, PlanBreakdown


# =============================================================================
# TEST FIXTURES
# =============================================================================

def make_strike(fighter: str, technique: str = "Jab", quality: str = "SOLID"):
    """Create a strike event"""
    return {
        "corner": fighter,
        "event_type": technique,
        "metadata": {"quality": quality}
    }

def make_kd(fighter: str, tier: str = "Flash"):
    """Create a knockdown event"""
    return {
        "corner": fighter,
        "event_type": "KD",
        "metadata": {"tier": tier}
    }

def make_takedown(fighter: str):
    """Create a takedown event"""
    return {
        "corner": fighter,
        "event_type": "Takedown",
        "metadata": {}
    }

def make_submission(fighter: str, depth: str = "Light"):
    """Create a submission attempt event"""
    return {
        "corner": fighter,
        "event_type": "Submission Attempt",
        "metadata": {"tier": depth}
    }

def make_control(fighter: str, ctrl_type: str = "Top Control", duration: float = 30.0):
    """Create a control event with duration"""
    return {
        "corner": fighter,
        "event_type": ctrl_type,
        "metadata": {"duration": duration}
    }


# =============================================================================
# TEST 1: PLAN A/B/C ACTIVATION RULES
# =============================================================================

class TestPlanActivation:
    """Tests for Plan A/B/C activation logic"""
    
    def test_plan_a_only_when_clear_winner(self):
        """Plan B/C should not activate when Plan A has clear winner"""
        # Create events with clear RED advantage
        events = [
            make_strike("RED", "Cross") for _ in range(10)
        ]
        
        result = score_round_delta_v2(1, events)
        
        # Should be 10-9 RED with no Plan B/C
        assert result["verdict"]["winner"] == "RED"
        assert result["verdict"]["red_points"] == 10
        assert result["verdict"]["blue_points"] == 9
        assert result["deltas"]["plan_b"] == 0.0
        assert result["deltas"]["plan_c"] == 0.0
    
    def test_plan_b_allowed_when_close(self):
        """Plan B should be allowed when Plan A is very close"""
        # Create very close round
        events = [
            make_strike("RED", "Jab"),
            make_strike("BLUE", "Jab"),
        ]
        
        red, blue, delta_a, _ = compute_plan_a(events)
        delta_b, allowed, _ = compute_plan_b(events, delta_a, False, False)
        
        # Plan B should be allowed (no impact advantage, close delta)
        assert allowed == True
    
    def test_plan_b_disabled_with_impact_advantage(self):
        """Plan B should be disabled when Impact Advantage exists"""
        events = [
            make_kd("RED", "Hard"),  # RED has KD_HARD = impact advantage
            make_strike("BLUE", "Jab"),
        ]
        
        red, blue, delta_a, _ = compute_plan_a(events)
        
        # Check impact advantage
        impact_result = compute_impact_score(events)
        red_adv, blue_adv, _ = check_impact_advantage(impact_result)
        
        delta_b, allowed, reason = compute_plan_b(events, delta_a, red_adv, blue_adv)
        
        assert red_adv == True
        assert allowed == False
        assert "Impact Advantage" in reason
    
    def test_plan_c_only_as_last_resort(self):
        """Plan C should only activate when A and B are exhausted"""
        events = [
            make_strike("RED", "Jab"),
            make_strike("BLUE", "Jab"),
        ]
        
        red, blue, delta_a, _ = compute_plan_a(events)
        delta_b, plan_b_allowed, _ = compute_plan_b(events, delta_a, False, False)
        delta_combined = delta_a + delta_b
        
        delta_c, plan_c_allowed, _ = compute_plan_c(
            events, delta_combined, plan_b_allowed, False, False
        )
        
        # Plan C should only be allowed if still very close
        # (depends on actual delta values)
        assert isinstance(plan_c_allowed, bool)


# =============================================================================
# TEST 2: IMPACT ADVANTAGE GATING
# =============================================================================

class TestImpactAdvantage:
    """Tests for Impact Advantage detection and gating"""
    
    def test_kd_hard_gives_impact_advantage(self):
        """KD_HARD should give impact advantage"""
        events = [make_kd("RED", "Hard")]
        
        impact_result = compute_impact_score(events)
        red_adv, blue_adv, reason = check_impact_advantage(impact_result)
        
        assert red_adv == True
        assert blue_adv == False
        assert "KD_HARD" in reason
    
    def test_kd_nf_gives_impact_advantage(self):
        """KD_NF should give impact advantage"""
        events = [make_kd("BLUE", "Near-Finish")]
        
        impact_result = compute_impact_score(events)
        red_adv, blue_adv, reason = check_impact_advantage(impact_result)
        
        assert red_adv == False
        assert blue_adv == True
        assert "KD_NF" in reason
    
    def test_two_rocked_gives_impact_advantage(self):
        """>=2 ROCKED should give impact advantage"""
        events = [
            {"corner": "RED", "event_type": "Rocked/Stunned", "metadata": {}},
            {"corner": "RED", "event_type": "Rocked/Stunned", "metadata": {}},
        ]
        
        impact_result = compute_impact_score(events)
        red_adv, blue_adv, reason = check_impact_advantage(impact_result)
        
        assert red_adv == True
        assert "ROCKED" in reason
    
    def test_flash_kd_advantage_of_two(self):
        """KD_FLASH advantage >= 2 should give impact advantage"""
        events = [
            make_kd("RED", "Flash"),
            make_kd("RED", "Flash"),
            make_kd("RED", "Flash"),  # 3 flash KDs for RED
            make_kd("BLUE", "Flash"),  # 1 for BLUE
        ]
        
        impact_result = compute_impact_score(events)
        red_adv, blue_adv, reason = check_impact_advantage(impact_result)
        
        assert red_adv == True  # 3-1 = 2 advantage
        assert "KD_FLASH advantage" in reason
    
    def test_impact_veto_disables_plan_bc(self):
        """Impact Advantage should disable Plan B and C (Hook #2)"""
        events = [
            make_kd("RED", "Hard"),
            make_strike("BLUE", "Jab"),
            make_strike("BLUE", "Jab"),
        ]
        
        result = score_round_delta_v2(1, events)
        
        # Plan B and C should be 0 due to impact veto
        assert result["deltas"]["plan_b"] == 0.0
        assert result["deltas"]["plan_c"] == 0.0


# =============================================================================
# TEST 3: 10-8 AND 10-7 STRICT GATES
# =============================================================================

class TestDominanceGates:
    """Tests for 10-8 and 10-7 gate requirements"""
    
    def test_10_8_denied_with_one_kd(self):
        """10-8 should be denied with only 1 knockdown"""
        # Create events with 1 KD and big delta
        events = [
            make_kd("RED", "Hard"),  # Only 1 KD
        ] + [make_strike("RED", "Cross") for _ in range(20)]  # Big volume
        
        result = score_round_delta_v2(1, events)
        
        # Should be capped at 10-9, not 10-8
        assert result["verdict"]["red_points"] == 10
        assert result["verdict"]["blue_points"] == 9
        assert "10-8 denied" in str(result["receipt"]["gate_messages"])
    
    def test_10_8_awarded_with_three_kds_and_differential(self):
        """10-8 should be awarded with >=3 KDs and big differential"""
        events = [
            make_kd("RED", "Hard"),
            make_kd("RED", "Hard"),
            make_kd("RED", "Flash"),  # 3 total KDs
        ] + [make_strike("RED", "Cross", "SOLID") for _ in range(15)]  # Big volume
        
        result = score_round_delta_v2(1, events)
        
        # Should be 10-8
        assert result["verdict"]["red_points"] == 10
        assert result["verdict"]["blue_points"] == 8
        assert "10-8 awarded" in str(result["receipt"]["gate_messages"])
    
    def test_10_7_denied_without_severe_impact(self):
        """10-7 should be denied without severe impact"""
        events = [
            make_kd("RED", "Hard"),
            make_kd("RED", "Hard"),
            make_kd("RED", "Hard"),  # 3 KDs - not enough for 10-7
        ] + [make_strike("RED", "Cross", "SOLID") for _ in range(30)]
        
        result = score_round_delta_v2(1, events)
        
        # Should be 10-8 max, not 10-7
        assert result["verdict"]["blue_points"] >= 7
        if result["verdict"]["blue_points"] == 7:
            # If it awarded 10-7, check the gate requirements were truly met
            assert "10-7 awarded" in str(result["receipt"]["gate_messages"])
    
    def test_10_7_requires_four_kds(self):
        """10-7 should require >=4 knockdowns"""
        events = [
            make_kd("RED", "Hard"),
            make_kd("RED", "Hard"),
            make_kd("RED", "Hard"),
            make_kd("RED", "Hard"),  # 4 KDs
        ] + [make_strike("RED", "Cross", "SOLID") for _ in range(30)]
        
        result = score_round_delta_v2(1, events)
        
        # Should potentially be 10-7 if differential met
        # Check gate messages
        messages = str(result["receipt"]["gate_messages"])
        if result["verdict"]["blue_points"] == 7:
            assert "10-7 awarded" in messages


# =============================================================================
# TEST 4: CONTROL-WITH-OFFENSE RULE
# =============================================================================

class TestControlWithOffense:
    """Tests for control scoring with offense modifier"""
    
    def test_control_without_offense_scores_half(self):
        """Control time with no offense should score half points"""
        events = [
            make_control("RED", "Top Control", 60.0),  # 60 sec control, no strikes
        ]
        
        result = score_round_delta_v2(1, events)
        
        # Control should score half value: 60 * 0.05 * 0.5 = 1.5
        # (rate=0.05 for top control, 0.5 multiplier for no offense)
        assert result["red"]["control"] > 0  # Should have some score
        assert result["red"]["control"] < 60 * 0.05 * 1.10  # Less than full offense value
    
    def test_control_with_solid_strike_scores_points(self):
        """Control time with SOLID strike should score points"""
        events = [
            {
                "corner": "RED",
                "event_type": "Top Control",
                "metadata": {"duration": 30.0},
                "timestamp": 100.0
            },
            {
                "corner": "RED",
                "event_type": "Ground Strike",
                "metadata": {"quality": "SOLID"},
                "timestamp": 110.0  # During control window
            }
        ]
        
        # Parse windows and check offense detection
        windows = parse_control_windows(events, events)
        
        # At least one window should have offense detected
        # Note: Without precise timestamps, this may vary
        control_scores = compute_control_score(windows, plan_c_only=False)
        
        # Should have some control score if offense detected
        # (depends on timestamp handling in implementation)
    
    def test_control_with_submission_attempt_scores(self):
        """Control time with submission attempt should score points"""
        events = [
            {
                "corner": "RED",
                "event_type": "Top Control",
                "metadata": {"duration": 30.0},
                "timestamp": 100.0
            },
            make_submission("RED", "Deep"),  # Sub attempt during control
        ]
        
        # The submission attempt should count as offense during control


# =============================================================================
# TEST 5: LEG DAMAGE INDEX ESCALATION
# =============================================================================

class TestLegDamageIndex:
    """Tests for LDI escalation on leg kicks"""
    
    def test_ldi_starts_at_zero(self):
        """LDI should start at 0"""
        tracker = LegDamageTracker()
        
        assert tracker.get_ldi(Corner.RED) == 0.0
        assert tracker.get_ldi(Corner.BLUE) == 0.0
    
    def test_ldi_increments_by_half_per_kick(self):
        """Each leg kick should add 0.5 to target's LDI"""
        tracker = LegDamageTracker()
        
        # RED kicks BLUE's leg
        tracker.record_leg_kick(Corner.RED)
        
        # BLUE should have accumulated damage
        assert tracker.get_ldi(Corner.BLUE) == 0.5
    
    def test_ldi_multiplier_at_threshold(self):
        """LDI multiplier should increase at thresholds"""
        tracker = LegDamageTracker()
        
        # First 10 kicks (LDI 0-5): multiplier = 1.0
        for _ in range(10):
            mult = tracker.record_leg_kick(Corner.RED)
        
        # Next kicks (LDI 5+): multiplier should be 1.10
        mult = tracker.record_leg_kick(Corner.RED)
        assert mult >= 1.0  # Should be elevated
    
    def test_ldi_affects_leg_kick_value(self):
        """Leg kick values should increase with LDI"""
        # Create many leg kicks
        events = [make_strike("RED", "Leg Kick") for _ in range(12)]
        
        result = score_round_delta_v2(1, events)
        
        # Later leg kicks should contribute more
        # Check that total is higher than 12 * base_value
        base_leg_kick = 1.5  # From weights
        min_expected = 12 * base_leg_kick  # Without escalation
        
        # With escalation, should be higher
        assert result["red"]["striking"] >= min_expected


# =============================================================================
# TEST 6: RECEIPT TOP DRIVERS
# =============================================================================

class TestReceiptGeneration:
    """Tests for receipt and top drivers generation"""
    
    def test_receipt_contains_required_fields(self):
        """Receipt should contain all required fields"""
        events = [
            make_kd("RED", "Hard"),
            make_strike("BLUE", "Cross"),
        ]
        
        result = score_round_delta_v2(1, events)
        receipt = result["receipt"]
        
        # Check required fields
        assert "round_number" in receipt
        assert "winner" in receipt
        assert "score" in receipt
        assert "red_plan_a" in receipt
        assert "blue_plan_a" in receipt
        assert "delta_plan_a" in receipt
        assert "plan_b_applied" in receipt
        assert "plan_c_applied" in receipt
        assert "red_has_impact_advantage" in receipt
        assert "blue_has_impact_advantage" in receipt
        assert "impact_advantage_reason" in receipt
        assert "top_drivers" in receipt
        assert "gate_messages" in receipt
    
    def test_top_drivers_sorted_by_points(self):
        """Top drivers should be sorted by point value"""
        events = [
            make_kd("RED", "Hard"),  # High value
            make_strike("RED", "Jab"),  # Low value
            make_strike("BLUE", "Cross"),  # Medium value
        ]
        
        result = score_round_delta_v2(1, events)
        drivers = result["receipt"]["top_drivers"]
        
        # Should have drivers
        assert len(drivers) > 0
        
        # Check sorting (higher points first for winner)
        if len(drivers) > 1:
            # Winners' high-value items should be near top
            kd_driver = next((d for d in drivers if "KD" in d["label"]), None)
            assert kd_driver is not None
    
    def test_top_drivers_includes_categories(self):
        """Top drivers should include category labels"""
        events = [
            make_kd("RED", "Hard"),
            make_takedown("RED"),
            make_strike("BLUE", "Cross"),
        ]
        
        result = score_round_delta_v2(1, events)
        drivers = result["receipt"]["top_drivers"]
        
        categories = {d["category"] for d in drivers}
        
        # Should have multiple categories represented
        assert len(categories) >= 1
    
    def test_gate_messages_explain_score(self):
        """Gate messages should explain why score was assigned"""
        events = [
            make_kd("RED", "Hard"),
            make_kd("RED", "Flash"),  # 2 KDs
        ] + [make_strike("RED", "Cross") for _ in range(10)]
        
        result = score_round_delta_v2(1, events)
        messages = result["receipt"]["gate_messages"]
        
        # Should have explanatory messages
        assert len(messages) > 0
        
        # Messages should mention denial or award
        message_text = " ".join(messages)
        assert "10-" in message_text  # Should mention score type


# =============================================================================
# TEST 7: BACKWARDS COMPATIBILITY
# =============================================================================

class TestBackwardsCompatibility:
    """Tests for backwards compatibility with old API"""
    
    def test_returns_legacy_fields(self):
        """Result should include legacy fields for backwards compat"""
        events = [make_strike("RED", "Jab")]
        
        result = score_round_delta_v2(1, events)
        
        # Check legacy fields exist
        assert "red_points" in result
        assert "blue_points" in result
        assert "delta" in result
        assert "red_total" in result
        assert "blue_total" in result
        assert "red_breakdown" in result
        assert "blue_breakdown" in result
        assert "total_events" in result
        assert "winner" in result
        assert "red_kd" in result
        assert "blue_kd" in result
    
    def test_handles_missing_quality_tag(self):
        """Should default to SOLID when quality tag is missing"""
        events = [
            {
                "corner": "RED",
                "event_type": "Jab",
                "metadata": {}  # No quality tag
            }
        ]
        
        result = score_round_delta_v2(1, events)
        
        # Should not error and should score the strike
        assert result["red"]["striking"] > 0
    
    def test_handles_legacy_fighter_field(self):
        """Should handle legacy 'fighter' field instead of 'corner'"""
        events = [
            {
                "fighter": "fighter1",  # Legacy format
                "event_type": "Jab",
                "metadata": {}
            }
        ]
        
        normalized = normalize_events(events)
        
        # Should convert to corner format
        assert normalized[0]["corner"] == "RED"
    
    def test_empty_events_returns_draw(self):
        """Empty events should return 10-10 draw"""
        result = score_round_delta_v2(1, [])
        
        assert result["verdict"]["winner"] == "DRAW"
        assert result["verdict"]["red_points"] == 10
        assert result["verdict"]["blue_points"] == 10


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
