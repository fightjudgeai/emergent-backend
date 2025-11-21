"""
Comprehensive Tests for All Microservices
CV Router, Event Harmonizer, Normalization Engine
"""

import pytest
import asyncio
import sys
sys.path.append('/app/backend')

# CV Router imports
from cv_router.worker_manager import WorkerManager
from cv_router.stream_ingestor import StreamIngestor
from cv_router.models import Frame, StreamType

# Event Harmonizer imports
from event_harmonizer.conflict_resolver import ConflictResolver
from event_harmonizer.harmonizer_engine import EventHarmonizerEngine
from fjai.models import CombatEvent, EventType, EventSource

# Normalization Engine imports
from normalization_engine.normalization_engine import NormalizationEngine


class TestCVRouter:
    """Test CV Router microservice"""
    
    @pytest.mark.asyncio
    async def test_worker_registration(self):
        """Test: Worker can be registered"""
        manager = WorkerManager()
        worker = await manager.register_worker("http://worker1:8000")
        
        assert worker.worker_id in manager.workers
        assert worker.endpoint == "http://worker1:8000"
        print("✓ Worker registration successful")
    
    @pytest.mark.asyncio
    async def test_worker_selection_load_balancing(self):
        """Test: Worker selection uses load balancing"""
        manager = WorkerManager()
        
        # Register 3 workers with different loads
        w1 = await manager.register_worker("http://worker1:8000")
        w2 = await manager.register_worker("http://worker2:8000")
        w3 = await manager.register_worker("http://worker3:8000")
        
        # Simulate different loads
        await manager.update_worker_metrics(w1.worker_id, latency_ms=50, queue_size=2)
        await manager.update_worker_metrics(w2.worker_id, latency_ms=100, queue_size=5)
        await manager.update_worker_metrics(w3.worker_id, latency_ms=30, queue_size=1)
        
        # Select worker - should choose w3 (lowest load)
        selected = manager.select_worker("frame_001")
        assert selected.worker_id == w3.worker_id
        
        print(f"✓ Load balancing working: selected worker with lowest load")
    
    @pytest.mark.asyncio
    async def test_worker_failover(self):
        """Test: System handles worker failure"""
        manager = WorkerManager()
        
        w1 = await manager.register_worker("http://worker1:8000")
        w2 = await manager.register_worker("http://worker2:8000")
        
        # Mark w1 as unhealthy
        manager.workers[w1.worker_id].status = "unhealthy"
        
        # Should select w2
        selected = manager.select_worker("frame_001")
        assert selected.worker_id == w2.worker_id
        
        print("✓ Failover working: unhealthy workers avoided")
    
    @pytest.mark.asyncio
    async def test_stream_ingestion(self):
        """Test: Mock stream ingestion"""
        ingestor = StreamIngestor()
        
        # Track frames
        frames_received = []
        
        async def frame_callback(frame):
            frames_received.append(frame)
        
        ingestor.set_frame_callback(frame_callback)
        
        # Add mock stream
        stream = await ingestor.add_stream(
            "cam_1",
            StreamType.MOCK,
            "mock://camera1"
        )
        
        # Wait for some frames
        await asyncio.sleep(0.2)
        
        # Should have received frames
        assert len(frames_received) > 0
        assert stream.camera_id == "cam_1"
        
        # Cleanup
        await ingestor.remove_stream("cam_1")
        
        print(f"✓ Stream ingestion working: received {len(frames_received)} frames")


class TestEventHarmonizer:
    """Test Event Harmonizer microservice"""
    
    def test_conflict_detection_type_contradiction(self):
        """Test: Detects KD tier contradictions"""
        resolver = ConflictResolver(proximity_window_ms=200)
        
        # Judge says KD_flash
        judge_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_FLASH,
            severity=0.6,
            confidence=0.85,
            timestamp_ms=1000,
            source=EventSource.MANUAL
        )
        
        # CV says KD_hard
        cv_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_HARD,
            severity=0.8,
            confidence=0.92,
            timestamp_ms=1050,  # 50ms later
            source=EventSource.CV_SYSTEM
        )
        
        conflict_type, analysis = resolver.detect_conflict(judge_event, cv_event)
        
        assert conflict_type.value == "type_contradiction"
        assert analysis is not None
        
        print("✓ Type contradiction detected: KD_flash vs KD_hard")
    
    def test_judge_override_resolution(self):
        """Test: Judge override strategy"""
        resolver = ConflictResolver()
        
        # High confidence judge event
        judge_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_FLASH,
            severity=0.6,
            confidence=0.95,  # High confidence
            timestamp_ms=1000,
            source=EventSource.MANUAL
        )
        
        cv_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_HARD,
            severity=0.8,
            confidence=0.75,
            timestamp_ms=1050,
            source=EventSource.CV_SYSTEM
        )
        
        conflict_type, analysis = resolver.detect_conflict(judge_event, cv_event)
        harmonized = resolver.resolve_conflict(analysis)
        
        # Should use judge event
        assert harmonized.resolution_strategy.value == "judge_override"
        assert harmonized.harmonized_event.event_type == EventType.KD_FLASH
        
        print("✓ Judge override: high confidence judge event wins")
    
    def test_hybrid_merge_resolution(self):
        """Test: Hybrid merge strategy"""
        resolver = ConflictResolver()
        
        # Medium confidence events
        judge_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_HIGHIMPACT,
            severity=0.7,
            confidence=0.75,
            timestamp_ms=1000,
            source=EventSource.MANUAL
        )
        
        cv_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_HIGHIMPACT,
            severity=0.9,
            confidence=0.80,
            timestamp_ms=1050,
            source=EventSource.CV_SYSTEM
        )
        
        conflict_type, analysis = resolver.detect_conflict(judge_event, cv_event)
        
        if analysis:
            harmonized = resolver.resolve_conflict(analysis)
            
            # Severity should be weighted average
            expected_severity = 0.7 * 0.6 + 0.9 * 0.4  # Judge 60%, CV 40%
            assert abs(harmonized.harmonized_event.severity - expected_severity) < 0.1
            
            print(f"✓ Hybrid merge: severity {harmonized.harmonized_event.severity:.2f}")
    
    @pytest.mark.asyncio
    async def test_harmonizer_engine_end_to_end(self):
        """Test: Complete harmonization pipeline"""
        engine = EventHarmonizerEngine()
        
        harmonized_outputs = []
        
        async def output_callback(harmonized):
            harmonized_outputs.append(harmonized)
        
        engine.set_output_callback(output_callback)
        
        # Send judge event
        judge_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_FLASH,
            severity=0.6,
            confidence=0.85,
            timestamp_ms=1000,
            source=EventSource.MANUAL
        )
        await engine.process_judge_event(judge_event)
        
        # Send conflicting CV event
        cv_event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_HARD,
            severity=0.8,
            confidence=0.90,
            timestamp_ms=1050,
            source=EventSource.CV_SYSTEM
        )
        await engine.process_cv_event(cv_event)
        
        # Should have harmonized outputs
        assert len(harmonized_outputs) > 0
        stats = engine.get_stats()
        assert stats.conflicts_detected > 0
        
        print(f"✓ Harmonizer pipeline: {stats.conflicts_detected} conflicts resolved")


class TestNormalizationEngine:
    """Test Normalization Engine"""
    
    def test_event_normalization_basic(self):
        """Test: Basic event normalization"""
        engine = NormalizationEngine()
        
        # Create test event
        event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_HARD,
            severity=0.8,
            confidence=0.9,
            timestamp_ms=1000,
            source=EventSource.CV_SYSTEM
        )
        
        normalized = engine.normalize_event(event)
        
        # Should have weight assigned
        assert normalized.total_weight > 0
        assert normalized.damage_weight > 0
        assert "base_weight" in normalized.breakdown
        
        print(f"✓ Event normalized: weight={normalized.total_weight:.3f}, damage={normalized.damage_weight:.3f}")
    
    def test_severity_multiplier(self):
        """Test: Severity affects weight"""
        engine = NormalizationEngine()
        
        # Low severity event
        event_low = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_SIG,
            severity=0.3,  # Low
            confidence=0.85,
            timestamp_ms=1000,
            source=EventSource.CV_SYSTEM
        )
        
        # High severity event
        event_high = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_SIG,
            severity=0.9,  # High
            confidence=0.85,
            timestamp_ms=2000,
            source=EventSource.CV_SYSTEM
        )
        
        norm_low = engine.normalize_event(event_low)
        norm_high = engine.normalize_event(event_high)
        
        # High severity should have higher weight
        assert norm_high.total_weight > norm_low.total_weight
        
        print(f"✓ Severity multiplier: low={norm_low.total_weight:.3f}, high={norm_high.total_weight:.3f}")
    
    def test_confidence_boost(self):
        """Test: Confidence boosts weight"""
        engine = NormalizationEngine()
        
        # High confidence event
        event_high_conf = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_SIG,
            severity=0.7,
            confidence=0.95,  # Very high
            timestamp_ms=1000,
            source=EventSource.CV_SYSTEM
        )
        
        # Low confidence event
        event_low_conf = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.STRIKE_SIG,
            severity=0.7,
            confidence=0.65,  # Low
            timestamp_ms=2000,
            source=EventSource.CV_SYSTEM
        )
        
        norm_high = engine.normalize_event(event_high_conf)
        norm_low = engine.normalize_event(event_low_conf)
        
        assert norm_high.confidence_boost > norm_low.confidence_boost
        
        print(f"✓ Confidence boost: high={norm_high.confidence_boost}, low={norm_low.confidence_boost}")
    
    def test_weight_breakdown_transparency(self):
        """Test: Weight breakdown provided"""
        engine = NormalizationEngine()
        
        event = CombatEvent(
            bout_id="test",
            round_id="r1",
            fighter_id="fighter_a",
            event_type=EventType.KD_HARD,
            severity=0.8,
            confidence=0.9,
            timestamp_ms=1000,
            source=EventSource.CV_SYSTEM
        )
        
        normalized = engine.normalize_event(event)
        
        # Should have complete breakdown
        assert "base_weight" in normalized.breakdown
        assert "severity_adjustment" in normalized.breakdown
        assert "confidence_adjustment" in normalized.breakdown
        assert "final_damage" in normalized.breakdown
        
        print(f"✓ Weight breakdown: {list(normalized.breakdown.keys())}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("MICROSERVICES TEST SUITE")
    print("="*80 + "\n")
    
    # Run tests
    test_cv_router = TestCVRouter()
    test_harmonizer = TestEventHarmonizer()
    test_norm = TestNormalizationEngine()
    
    print("Testing CV Router...")
    asyncio.run(test_cv_router.test_worker_registration())
    asyncio.run(test_cv_router.test_worker_selection_load_balancing())
    asyncio.run(test_cv_router.test_worker_failover())
    asyncio.run(test_cv_router.test_stream_ingestion())
    
    print("\nTesting Event Harmonizer...")
    test_harmonizer.test_conflict_detection_type_contradiction()
    test_harmonizer.test_judge_override_resolution()
    test_harmonizer.test_hybrid_merge_resolution()
    asyncio.run(test_harmonizer.test_harmonizer_engine_end_to_end())
    
    print("\nTesting Normalization Engine...")
    test_norm.test_event_normalization_basic()
    test_norm.test_severity_multiplier()
    test_norm.test_confidence_boost()
    test_norm.test_weight_breakdown_transparency()
    
    print("\n" + "="*80)
    print("✅ ALL MICROSERVICE TESTS PASSED")
    print("="*80 + "\n")
