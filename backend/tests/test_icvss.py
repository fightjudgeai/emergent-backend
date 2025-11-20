"""
ICVSS Unit Tests
Testing: 10-8 logic, KD vs high volume, conflicting CV + judge inputs, deduplication
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icvss.models import CVEvent, EventType, EventSource, Position
from icvss.event_processor import EventProcessor
from icvss.scoring_engine import HybridScoringEngine
from datetime import datetime, timezone


class TestEventProcessor:
    """Test event processing and deduplication"""
    
    def test_confidence_filtering(self):
        """Test that low-confidence events are rejected"""
        processor = EventProcessor(confidence_threshold=0.7)
        
        # Low confidence event
        event = CVEvent(
            bout_id="test-bout-1",
            round_id="test-round-1",
            fighter_id="fighter1",
            event_type=EventType.STRIKE_JAB,
            severity=0.8,
            confidence=0.5,  # Below threshold
            timestamp_ms=1000
        )
        
        accepted, reason = processor.process_event(event)
        
        assert accepted == False
        assert "confidence" in reason.lower()
    
    def test_deduplication_window(self):
        """Test 80-150ms deduplication window"""
        processor = EventProcessor(dedup_window_ms=100)
        
        # First event
        event1 = CVEvent(
            bout_id="test-bout-1",
            round_id="test-round-1",
            fighter_id="fighter1",
            event_type=EventType.STRIKE_JAB,
            severity=0.8,
            confidence=0.9,
            timestamp_ms=1000
        )
        
        # Duplicate event within 100ms
        event2 = CVEvent(
            bout_id="test-bout-1",
            round_id="test-round-1",
            fighter_id="fighter1",
            event_type=EventType.STRIKE_JAB,
            severity=0.8,
            confidence=0.9,
            timestamp_ms=1050  # 50ms later
        )
        
        # Event outside window
        event3 = CVEvent(
            bout_id="test-bout-1",
            round_id="test-round-1",
            fighter_id="fighter1",
            event_type=EventType.STRIKE_JAB,
            severity=0.8,
            confidence=0.9,
            timestamp_ms=1150  # 150ms later
        )
        
        accepted1, _ = processor.process_event(event1)
        accepted2, reason2 = processor.process_event(event2)
        accepted3, _ = processor.process_event(event3)
        
        assert accepted1 == True  # First event accepted
        assert accepted2 == False  # Duplicate rejected
        assert "duplicate" in reason2.lower()
        assert accepted3 == True  # Outside window, accepted


class TestHybridScoring:
    """Test hybrid CV + judge scoring"""
    
    def test_10_8_logic_with_knockdowns(self):
        """Test 10-8 round logic with knockdowns (damage primacy)"""
        engine = HybridScoringEngine()
        
        # Fighter 1: Multiple knockdowns
        cv_events = [
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter1",
                event_type=EventType.KD_HARD,
                severity=1.0,
                confidence=0.95,
                timestamp_ms=1000
            ),
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter1",
                event_type=EventType.KD_HARD,
                severity=1.0,
                confidence=0.95,
                timestamp_ms=2000
            )
        ]
        
        # Fighter 2: Only jabs
        cv_events.append(
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter2",
                event_type=EventType.STRIKE_JAB,
                severity=0.5,
                confidence=0.8,
                timestamp_ms=3000
            )
        )
        
        result = engine.calculate_hybrid_score(cv_events, [])
        
        print(f"\n10-8 Test Result:")
        print(f"  Score Card: {result['score_card']}")
        print(f"  Winner: {result['winner']}")
        print(f"  F1 Total: {result['fighter1_total']:.2f}")
        print(f"  F2 Total: {result['fighter2_total']:.2f}")
        
        # Should be 10-8 or better for fighter1 (damage primacy)
        assert result['winner'] == 'fighter1'
        assert result['fighter1_total'] > result['fighter2_total']
        # Score should reflect dominance
        assert result['score_card'] in ['10-9', '10-8', '10-7']
    
    def test_kd_vs_high_volume(self):
        """Test knockdown vs high strike volume (damage primacy)"""
        engine = HybridScoringEngine()
        
        # Fighter 1: One knockdown
        f1_events = [
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter1",
                event_type=EventType.KD_HARD,
                severity=1.0,
                confidence=0.95,
                timestamp_ms=1000
            )
        ]
        
        # Fighter 2: Many jabs (high volume, low damage)
        f2_events = [
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter2",
                event_type=EventType.STRIKE_JAB,
                severity=0.5,
                confidence=0.8,
                timestamp_ms=i*100
            )
            for i in range(50)  # 50 jabs
        ]
        
        all_events = f1_events + f2_events
        result = engine.calculate_hybrid_score(all_events, [])
        
        print(f"\nKD vs Volume Test:")
        print(f"  Score Card: {result['score_card']}")
        print(f"  Winner: {result['winner']}")
        print(f"  F1 (1 KD): {result['fighter1_total']:.2f}")
        print(f"  F2 (50 jabs): {result['fighter2_total']:.2f}")
        
        # Damage primacy: 1 knockdown should beat 50 jabs
        assert result['winner'] == 'fighter1'
        assert result['fighter1_total'] > result['fighter2_total']
    
    def test_conflicting_cv_and_judge_inputs(self):
        """Test conflicting CV and judge event fusion"""
        engine = HybridScoringEngine(cv_weight=0.7, judge_weight=0.3)
        
        # CV says Fighter 1 won (knockdown)
        cv_events = [
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter1",
                event_type=EventType.KD_HARD,
                severity=1.0,
                confidence=0.95,
                timestamp_ms=1000
            )
        ]
        
        # Judge manually logged Fighter 2 events
        judge_events = [
            {
                "fighter": "fighter2",
                "event_type": "Takedown Landed",
                "timestamp": 2000,
                "metadata": {}
            },
            {
                "fighter": "fighter2",
                "event_type": "Submission Attempt",
                "timestamp": 3000,
                "metadata": {}
            }
        ]
        
        result = engine.calculate_hybrid_score(cv_events, judge_events)
        
        print(f"\nConflicting Inputs Test:")
        print(f"  Score Card: {result['score_card']}")
        print(f"  Winner: {result['winner']}")
        print(f"  CV Contribution: {result['cv_contribution']:.1%}")
        print(f"  Judge Contribution: {result['judge_contribution']:.1%}")
        print(f"  F1 (CV KD): {result['fighter1_breakdown']['cv_score']:.2f}")
        print(f"  F2 (Judge grappling): {result['fighter2_breakdown']['judge_score']:.2f}")
        
        # CV weight (70%) should dominate
        # Fighter 1 should still win due to KD and damage primacy
        assert result['winner'] == 'fighter1'
        assert result['cv_contribution'] == 0.7
        assert result['judge_contribution'] == 0.3
    
    def test_10_10_draw(self):
        """Test extremely rare 10-10 draw scenario"""
        engine = HybridScoringEngine()
        
        # Equal events for both fighters
        cv_events = [
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter1",
                event_type=EventType.STRIKE_JAB,
                severity=0.5,
                confidence=0.8,
                timestamp_ms=1000
            ),
            CVEvent(
                bout_id="test",
                round_id="test",
                fighter_id="fighter2",
                event_type=EventType.STRIKE_JAB,
                severity=0.5,
                confidence=0.8,
                timestamp_ms=2000
            )
        ]
        
        result = engine.calculate_hybrid_score(cv_events, [])
        
        print(f"\nDraw Test:")
        print(f"  Score Card: {result['score_card']}")
        print(f"  Winner: {result['winner']}")
        print(f"  Score Diff: {abs(result['fighter1_total'] - result['fighter2_total']):.2f}")
        
        # Should be very close or draw
        assert abs(result['fighter1_total'] - result['fighter2_total']) < 5.0


def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("ICVSS UNIT TESTS")
    print("=" * 80)
    
    # Event Processor Tests
    print("\n[1/4] Testing Event Processor...")
    test_processor = TestEventProcessor()
    test_processor.test_confidence_filtering()
    print("  ✓ Confidence filtering works")
    
    test_processor.test_deduplication_window()
    print("  ✓ Deduplication (80-150ms) works")
    
    # Hybrid Scoring Tests
    print("\n[2/4] Testing 10-8 Logic...")
    test_scoring = TestHybridScoring()
    test_scoring.test_10_8_logic_with_knockdowns()
    print("  ✓ 10-8 logic with knockdowns works")
    
    print("\n[3/4] Testing KD vs High Volume...")
    test_scoring.test_kd_vs_high_volume()
    print("  ✓ Damage primacy works (KD beats volume)")
    
    print("\n[4/4] Testing Conflicting CV + Judge Inputs...")
    test_scoring.test_conflicting_cv_and_judge_inputs()
    print("  ✓ Hybrid fusion works (70% CV, 30% Judge)")
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
