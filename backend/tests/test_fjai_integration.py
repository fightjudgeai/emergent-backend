"""
Integration Tests for Fight Judge AI + CV Analytics Pipeline
Tests the complete E2 → E1 flow
"""

import pytest
import sys
sys.path.append('/app/backend')

from fjai.models import CombatEvent, EventType, EventSource, RoundScore
from fjai.event_pipeline import EventPipeline
from fjai.scoring_engine import WeightedScoringEngine, ScoringWeights
from cv_analytics.models import RawCVInput, ActionType, ImpactLevel
from cv_analytics.analytics_engine import CVAnalyticsEngine
from cv_analytics.mock_generator import MockCVDataGenerator


class TestFJAIIntegration:
    """Test Fight Judge AI integration"""
    
    def test_kd_vs_volume_scoring(self):
        """Test: Single KD vs volume striking"""
        scoring_engine = WeightedScoringEngine()
        
        # Fighter A: 1 Hard KD
        fighter_a_events = [
            CombatEvent(
                bout_id="test_bout",
                round_id="test_round",
                fighter_id="fighter_a",
                event_type=EventType.KD_HARD,
                severity=0.9,
                confidence=0.95,
                timestamp_ms=5000,
                source=EventSource.CV_SYSTEM
            )
        ]
        
        # Fighter B: 10 significant strikes
        fighter_b_events = [
            CombatEvent(
                bout_id="test_bout",
                round_id="test_round",
                fighter_id="fighter_b",
                event_type=EventType.STRIKE_SIG,
                severity=0.6,
                confidence=0.85,
                timestamp_ms=1000 + (i * 500),
                source=EventSource.CV_SYSTEM
            )
            for i in range(10)
        ]
        
        all_events = fighter_a_events + fighter_b_events
        
        # Calculate score
        score = scoring_engine.calculate_round_score(all_events, "test_bout", "test_round", 1)
        
        # KD should win due to damage primacy
        assert score.winner == "fighter_a"
        assert score.fighter_a_breakdown.damage > score.fighter_b_breakdown.damage
        print(f"✓ KD vs Volume: {score.score_card} for fighter_a")
    
    def test_momentum_swing_scoring_boost(self):
        """Test: Momentum swing gives scoring boost"""
        scoring_engine = WeightedScoringEngine()
        
        # Fighter A: 3 regular strikes + momentum swing
        events = [
            CombatEvent(
                bout_id="test_bout",
                round_id="test_round",
                fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG,
                severity=0.6,
                confidence=0.85,
                timestamp_ms=1000 + (i * 300),
                source=EventSource.CV_SYSTEM
            )
            for i in range(3)
        ] + [
            CombatEvent(
                bout_id="test_bout",
                round_id="test_round",
                fighter_id="fighter_a",
                event_type=EventType.MOMENTUM_SWING,
                severity=0.8,
                confidence=0.88,
                timestamp_ms=2000,
                source=EventSource.ANALYTICS
            )
        ]
        
        score = scoring_engine.calculate_round_score(events, "test_bout", "test_round", 1)
        
        # Check momentum contributed to aggression
        assert score.fighter_a_breakdown.aggression > 0
        print(f"✓ Momentum swing detected: aggression = {score.fighter_a_breakdown.aggression:.2f}")
    
    def test_event_deduplication(self):
        """Test: Event pipeline deduplication"""
        pipeline = EventPipeline(dedup_window_ms=100)
        
        # Create two identical events 50ms apart
        event1 = CombatEvent(
            bout_id="test_bout",
            round_id="test_round",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_SIG,
            severity=0.7,
            confidence=0.9,
            timestamp_ms=1000,
            source=EventSource.CV_SYSTEM
        )
        
        event2 = CombatEvent(
            bout_id="test_bout",
            round_id="test_round",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_SIG,
            severity=0.7,
            confidence=0.9,
            timestamp_ms=1050,  # 50ms later
            source=EventSource.CV_SYSTEM
        )
        
        # First event should be accepted
        accepted1, _ = pipeline.process_event(event1)
        assert accepted1 == True
        
        # Second event should be rejected as duplicate
        accepted2, reason = pipeline.process_event(event2)
        assert accepted2 == False
        assert "duplicate" in reason.lower()
        
        print(f"✓ Deduplication working: rejected duplicate within 100ms window")
    
    def test_multicam_fusion(self):
        """Test: Multi-camera event fusion"""
        pipeline = EventPipeline()
        
        # Create 3 views of same punch from different cameras
        events = [
            CombatEvent(
                bout_id="test_bout",
                round_id="test_round",
                fighter_id="fighter_a",
                event_type=EventType.STRIKE_HIGHIMPACT,
                severity=0.8,
                confidence=0.85 + (i * 0.03),  # Varying confidence
                timestamp_ms=1000 + (i * 30),  # Slightly offset
                source=EventSource.CV_SYSTEM,
                camera_id=f"cam_{i+1}",
                angle=120.0 * i  # Different angles
            )
            for i in range(3)
        ]
        
        # Fuse events
        fused = pipeline.fuse_multicamera_events(events)
        
        # Should result in 1 canonical event
        assert len(fused) == 1
        assert fused[0].canonical == True
        
        print(f"✓ Multi-camera fusion: {len(events)} views → 1 canonical event")
    
    def test_confidence_threshold_filtering(self):
        """Test: Low confidence events rejected"""
        pipeline = EventPipeline(confidence_threshold=0.6)
        
        # Low confidence event
        low_conf_event = CombatEvent(
            bout_id="test_bout",
            round_id="test_round",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_SIG,
            severity=0.7,
            confidence=0.4,  # Below threshold
            timestamp_ms=1000,
            source=EventSource.CV_SYSTEM
        )
        
        accepted, reason = pipeline.process_event(low_conf_event)
        assert accepted == False
        assert "confidence" in reason.lower()
        
        print(f"✓ Confidence filtering: rejected event with confidence 0.4")


class TestCVAnalyticsPipeline:
    """Test CV Analytics Engine (E2)"""
    
    def test_raw_cv_to_combat_event_conversion(self):
        """Test: Raw CV input converts to CombatEvent"""
        engine = CVAnalyticsEngine()
        
        # Create mock raw input (send 5 frames to fill temporal buffer)
        events = []
        for i in range(5):
            raw_input = RawCVInput(
                frame_id=i+1,
                timestamp_ms=1000 + (i * 100),
                camera_id="cam_1",
                fighter_id="fighter_a",
                action_type=ActionType.PUNCH,
                action_logits={"punch": 0.92, "kick": 0.05, "knee": 0.03},
                fighter_bbox=[0.3, 0.4, 0.2, 0.4],
                keypoints=[(0.5, 0.5, 0.9) for _ in range(17)],
                impact_detected=True,
                impact_level=ImpactLevel.HEAVY,
                motion_vectors={"vx": 5.0, "vy": -2.0, "magnitude": 7.5},
                camera_angle=90.0,
                camera_distance=5.0
            )
            
            # Process
            frame_events = engine.process_raw_input(raw_input, "test_bout", "test_round")
            events.extend(frame_events)
        
        # Should generate combat event after temporal smoothing
        assert len(events) >= 1
        assert events[0].event_type == EventType.STRIKE_HIGHIMPACT
        assert events[0].source == EventSource.CV_SYSTEM
        
        print(f"✓ Raw CV → CombatEvent: PUNCH → {events[0].event_type}")
    
    def test_kd_tier_classification(self):
        """Test: KD correctly classified by impact level"""
        engine = CVAnalyticsEngine()
        
        # Send 5 frames to fill temporal buffer
        events = []
        for i in range(5):
            flash_kd = RawCVInput(
                frame_id=i+1,
                timestamp_ms=1000 + (i * 100),
                camera_id="cam_1",
                fighter_id="fighter_a",
                action_type=ActionType.KNOCKDOWN,
                action_logits={"knockdown": 0.95},
                fighter_bbox=[0.3, 0.4, 0.2, 0.4],
                keypoints=[(0.5, 0.5, 0.9) for _ in range(17)],
                impact_detected=True,
                impact_level=ImpactLevel.LIGHT,
                camera_angle=90.0,
                camera_distance=5.0
            )
            
            frame_events = engine.process_raw_input(flash_kd, "test_bout", "test_round")
            events.extend(frame_events)
        
        assert len(events) >= 1
        assert events[0].event_type == EventType.KD_FLASH
        
        print(f"✓ KD classification: LIGHT impact → KD_FLASH")
    
    def test_momentum_swing_detection(self):
        """Test: Flurry triggers momentum swing"""
        engine = CVAnalyticsEngine()
        
        # Create 5 rapid strikes
        for i in range(5):
            raw_input = RawCVInput(
                frame_id=i+1,
                timestamp_ms=1000 + (i * 200),  # 200ms apart
                camera_id="cam_1",
                fighter_id="fighter_a",
                action_type=ActionType.PUNCH,
                action_logits={"punch": 0.9},
                fighter_bbox=[0.3, 0.4, 0.2, 0.4],
                keypoints=[(0.5, 0.5, 0.9) for _ in range(17)],
                impact_detected=True,
                impact_level=ImpactLevel.MEDIUM,
                camera_angle=90.0,
                camera_distance=5.0
            )
            
            events = engine.process_raw_input(raw_input, "test_bout", "test_round")
        
        # Check if momentum swing was generated
        momentum_events = [e for e in events if e.event_type == EventType.MOMENTUM_SWING]
        assert len(momentum_events) > 0
        
        print(f"✓ Momentum detection: 5 strikes in 1s → momentum swing event")
    
    def test_fighter_style_classification(self):
        """Test: Fighter style correctly classified"""
        engine = CVAnalyticsEngine()
        
        # Create striker profile (all strikes)
        strike_events = [
            CombatEvent(
                bout_id="test_bout",
                round_id="test_round",
                fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG,
                severity=0.6,
                confidence=0.85,
                timestamp_ms=1000 + (i * 1000),
                source=EventSource.CV_SYSTEM
            )
            for i in range(10)
        ]
        
        analytics = engine.generate_analytics(strike_events)
        assert analytics.fighter_style == "striker"
        
        print(f"✓ Style classification: 10 strikes → {analytics.fighter_style}")


class TestEndToEndPipeline:
    """Test complete E2 → E1 pipeline"""
    
    def test_mock_to_score_pipeline(self):
        """Test: Mock CV data → Raw processing → Event pipeline → Scoring"""
        # Generate mock data
        generator = MockCVDataGenerator("test_bout", "test_round")
        mock_data = generator.generate_event_sequence("balanced")
        
        # E2: Process through CV Analytics
        cv_engine = CVAnalyticsEngine()
        all_events = []
        for raw_input in mock_data:
            events = cv_engine.process_raw_input(raw_input, "test_bout", "test_round")
            all_events.extend(events)
        
        # E1: Process through scoring engine
        scoring_engine = WeightedScoringEngine()
        score = scoring_engine.calculate_round_score(all_events, "test_bout", "test_round", 1)
        
        # Verify complete pipeline
        assert len(all_events) > 0
        assert score.score_card in ["10-10", "10-9", "9-10", "10-8", "8-10", "10-7", "7-10"]
        assert score.confidence > 0.0
        
        print(f"✓ End-to-end pipeline:")
        print(f"  Mock frames: {len(mock_data)}")
        print(f"  Generated events: {len(all_events)}")
        print(f"  Final score: {score.score_card}")
        print(f"  Winner: {score.winner}")
        print(f"  Confidence: {score.confidence:.2f}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FIGHT JUDGE AI - Integration Test Suite")
    print("="*60 + "\n")
    
    # Run tests
    test_fjai = TestFJAIIntegration()
    test_cv = TestCVAnalyticsPipeline()
    test_e2e = TestEndToEndPipeline()
    
    print("Testing FJAI Integration...")
    test_fjai.test_kd_vs_volume_scoring()
    test_fjai.test_momentum_swing_scoring_boost()
    test_fjai.test_event_deduplication()
    test_fjai.test_multicam_fusion()
    test_fjai.test_confidence_threshold_filtering()
    
    print("\nTesting CV Analytics Pipeline...")
    test_cv.test_raw_cv_to_combat_event_conversion()
    test_cv.test_kd_tier_classification()
    test_cv.test_momentum_swing_detection()
    test_cv.test_fighter_style_classification()
    
    print("\nTesting End-to-End Pipeline...")
    test_e2e.test_mock_to_score_pipeline()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60 + "\n")
