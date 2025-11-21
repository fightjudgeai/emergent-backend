"""
Comprehensive Tests for Production Services
Round Validator, Report Generator, Highlight Worker, Replay Service, Storage Manager
"""

import pytest
import asyncio
import sys
sys.path.append('/app/backend')

from fjai.models import CombatEvent, EventType, EventSource
from round_validator.validator_engine import RoundValidatorEngine
from round_validator.models import ValidationSeverity
from report_generator.generator_engine import ReportGeneratorEngine
from report_generator.models import FightReport, ReportFormat, RoundScore
from highlight_worker.worker_engine import HighlightWorkerEngine
from replay_service.replay_engine import ReplayEngine
from storage_manager.manager_engine import StorageManagerEngine
from datetime import datetime


class TestRoundValidator:
    """Test Round Validator"""
    
    def test_minimum_events_check(self):
        """Test: Validates minimum events"""
        validator = RoundValidatorEngine()
        
        # Too few events
        events = [
            CombatEvent(
                bout_id="test", round_id="r1", fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG, severity=0.6, confidence=0.85,
                timestamp_ms=1000, source=EventSource.MANUAL
            )
        ]
        
        result = validator.validate_round("r1", "test", 1, events)
        
        assert not result.valid
        assert result.errors > 0
        print(f"✓ Minimum events check: {result.errors} errors detected")
    
    def test_judge_inactivity_detection(self):
        """Test: Detects judge inactivity"""
        validator = RoundValidatorEngine()
        
        # Events with large gap
        events = [
            CombatEvent(
                bout_id="test", round_id="r1", fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG, severity=0.6, confidence=0.85,
                timestamp_ms=1000, source=EventSource.MANUAL
            ),
            CombatEvent(
                bout_id="test", round_id="r1", fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG, severity=0.6, confidence=0.85,
                timestamp_ms=100000,  # 99s gap
                source=EventSource.MANUAL
            )
        ]
        
        result = validator.validate_round("r1", "test", 1, events)
        
        # Should have inactivity warning
        inactivity_issues = [i for i in result.issues if "inactivity" in i.message.lower()]
        assert len(inactivity_issues) > 0
        print(f"✓ Judge inactivity detected: {len(inactivity_issues)} warnings")
    
    def test_can_lock_logic(self):
        """Test: Can lock logic based on validation"""
        validator = RoundValidatorEngine()
        
        # Good events
        events = [
            CombatEvent(
                bout_id="test", round_id="r1", fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG, severity=0.6, confidence=0.85,
                timestamp_ms=1000 + (i * 5000), source=EventSource.MANUAL
            )
            for i in range(10)
        ]
        
        result = validator.validate_round("r1", "test", 1, events)
        
        assert result.can_lock
        assert result.critical_issues == 0
        print(f"✓ Can lock: {result.can_lock} (critical={result.critical_issues})")


class TestReportGenerator:
    """Test Report Generator"""
    
    def test_json_report_generation(self):
        """Test: Generate JSON report"""
        generator = ReportGeneratorEngine()
        
        report = FightReport(
            bout_id="TEST_001",
            event_name="Test Event",
            fighters={"fighter_a": "Fighter A", "fighter_b": "Fighter B"},
            date=datetime.now(),
            round_scores=[],
            final_result="30-27",
            major_events=[],
            kd_timeline=[],
            rocked_timeline=[],
            momentum_swings=[],
            total_events=50,
            strike_counts={"fighter_a": 25, "fighter_b": 25},
            control_time={"fighter_a": 60.0, "fighter_b": 30.0},
            model_versions={"cv": "1.0.0"},
            audit_log_reference="audit_001"
        )
        
        json_output = generator.generate_report(report, ReportFormat.JSON)
        
        assert len(json_output) > 0
        assert "TEST_001" in json_output
        print(f"✓ JSON report generated: {len(json_output)} bytes")
    
    def test_html_report_generation(self):
        """Test: Generate HTML report"""
        generator = ReportGeneratorEngine()
        
        report = FightReport(
            bout_id="TEST_001",
            event_name="Test Event",
            fighters={"fighter_a": "Fighter A", "fighter_b": "Fighter B"},
            date=datetime.now(),
            round_scores=[
                RoundScore(round_num=1, judge_scores={}, ai_composite_score="10-9", winner="fighter_a", confidence=0.85)
            ],
            final_result="30-27",
            major_events=[],
            kd_timeline=[],
            rocked_timeline=[],
            momentum_swings=[],
            total_events=50,
            strike_counts={"fighter_a": 25, "fighter_b": 25},
            control_time={"fighter_a": 60.0, "fighter_b": 30.0},
            model_versions={"cv": "1.0.0"},
            audit_log_reference="audit_001"
        )
        
        html_output = generator.generate_report(report, ReportFormat.HTML)
        
        assert "<html>" in html_output
        assert "TEST_001" in html_output
        print(f"✓ HTML report generated: {len(html_output)} bytes")


class TestHighlightWorker:
    """Test Highlight Worker"""
    
    @pytest.mark.asyncio
    async def test_major_event_triggers_clip(self):
        """Test: Major events trigger clip generation"""
        worker = HighlightWorkerEngine()
        
        # Create KD event
        event = CombatEvent(
            bout_id="test", round_id="r1", fighter_id="fighter_a",
            event_type=EventType.KD_HARD, severity=0.9, confidence=0.95,
            timestamp_ms=10000, source=EventSource.CV_SYSTEM
        )
        
        await worker.watch_event(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        clips = worker.get_clips("test")
        assert len(clips) > 0
        print(f"✓ Clip generated: {clips[0].clip_id} for {event.event_type.value}")
    
    @pytest.mark.asyncio
    async def test_clip_metadata_correct(self):
        """Test: Clip metadata is correct"""
        worker = HighlightWorkerEngine()
        
        event = CombatEvent(
            bout_id="test", round_id="r1", fighter_id="fighter_a",
            event_type=EventType.KD_HARD, severity=0.9, confidence=0.95,
            timestamp_ms=10000, source=EventSource.CV_SYSTEM
        )
        
        await worker.watch_event(event)
        
        clips = worker.get_clips("test")
        clip = clips[0]
        
        # Should be 5s before, 10s after
        assert clip.start_time_ms == 10000 - 5000
        assert clip.end_time_ms == 10000 + 10000
        assert clip.duration_sec == 15.0
        print(f"✓ Clip timing: {clip.start_time_ms} to {clip.end_time_ms}")


class TestReplayService:
    """Test Replay Service"""
    
    def test_replay_generation(self):
        """Test: Generate multi-angle replay"""
        replay_engine = ReplayEngine()
        
        replay = replay_engine.generate_replay("test", "r1", 10000)
        
        assert replay.bout_id == "test"
        assert len(replay.camera_angles) >= 2
        assert replay.duration_sec == 15.0
        print(f"✓ Replay generated: {len(replay.camera_angles)} camera angles")
    
    def test_replay_timing(self):
        """Test: Replay timing is correct"""
        replay_engine = ReplayEngine()
        
        timestamp = 10000
        replay = replay_engine.generate_replay("test", "r1", timestamp)
        
        # Should be 5s before, 10s after
        assert replay.start_time_ms == timestamp - 5000
        assert replay.end_time_ms == timestamp + 10000
        print(f"✓ Replay timing: 5s before → 10s after")


class TestStorageManager:
    """Test Storage Manager"""
    
    def test_storage_status(self):
        """Test: Get storage status"""
        manager = StorageManagerEngine()
        
        status = manager.get_status()
        
        assert status.total_space_gb > 0
        assert status.used_percentage >= 0
        assert status.alert_level in ["normal", "warning", "critical"]
        print(f"✓ Storage status: {status.used_percentage:.1f}% used ({status.alert_level})")
    
    @pytest.mark.asyncio
    async def test_cleanup_operation(self):
        """Test: Cleanup expired files"""
        manager = StorageManagerEngine()
        
        initial_used = manager.used_space_gb
        result = await manager.cleanup_expired(days=7)
        
        assert result.files_deleted > 0
        assert result.space_freed_gb > 0
        assert manager.used_space_gb < initial_used
        print(f"✓ Cleanup: {result.files_deleted} files, {result.space_freed_gb}GB freed")
    
    @pytest.mark.asyncio
    async def test_archive_operation(self):
        """Test: Archive bout"""
        manager = StorageManagerEngine()
        
        result = await manager.archive_bout("TEST_BOUT_001")
        
        assert result.bout_id == "TEST_BOUT_001"
        assert "s3://" in result.archive_url
        assert result.archive_size_gb > 0
        print(f"✓ Archive: {result.archive_size_gb}GB at {result.archive_url}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PRODUCTION SERVICES TEST SUITE")
    print("="*80 + "\n")
    
    test_validator = TestRoundValidator()
    test_reports = TestReportGenerator()
    test_highlights = TestHighlightWorker()
    test_replay = TestReplayService()
    test_storage = TestStorageManager()
    
    print("Testing Round Validator...")
    test_validator.test_minimum_events_check()
    test_validator.test_judge_inactivity_detection()
    test_validator.test_can_lock_logic()
    
    print("\nTesting Report Generator...")
    test_reports.test_json_report_generation()
    test_reports.test_html_report_generation()
    
    print("\nTesting Highlight Worker...")
    asyncio.run(test_highlights.test_major_event_triggers_clip())
    asyncio.run(test_highlights.test_clip_metadata_correct())
    
    print("\nTesting Replay Service...")
    test_replay.test_replay_generation()
    test_replay.test_replay_timing()
    
    print("\nTesting Storage Manager...")
    test_storage.test_storage_status()
    asyncio.run(test_storage.test_cleanup_operation())
    asyncio.run(test_storage.test_archive_operation())
    
    print("\n" + "="*80)
    print("✅ ALL PRODUCTION SERVICE TESTS PASSED")
    print("="*80 + "\n")
