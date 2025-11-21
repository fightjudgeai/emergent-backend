"""
Comprehensive Tests for Enterprise Services
Advanced Audit, Scoring Simulator, Failover Engine, Time Sync
"""

import pytest
import asyncio
import time
import sys
sys.path.append('/app/backend')

from advanced_audit.audit_engine import AdvancedAuditEngine
from scoring_simulator.simulator_engine import ScoringSimulatorEngine
from scoring_simulator.models import SimulationScript
from failover_engine.failover_manager import FailoverManager
from failover_engine.models import CVEngineMode
from time_sync.sync_engine import TimeSyncEngine
from fjai.models import CombatEvent, EventType, EventSource


class TestAdvancedAudit:
    """Test Advanced Audit Logger"""
    
    def test_blockchain_chain_creation(self):
        """Test: Blockchain chain is created correctly"""
        audit = AdvancedAuditEngine()
        
        # Log first event
        entry1 = audit.log_event(
            "test_bout",
            "event_logged",
            {"event_type": "strike", "severity": 0.8}
        )
        
        assert entry1.sequence_num == 1
        assert entry1.previous_hash == audit.GENESIS_HASH
        assert len(entry1.current_hash) == 64  # SHA256
        
        print(f"✓ Chain created: seq={entry1.sequence_num}, hash={entry1.current_hash[:16]}...")
    
    def test_hash_chaining(self):
        """Test: Hashes are properly chained"""
        audit = AdvancedAuditEngine()
        
        # Log multiple events
        entry1 = audit.log_event("test_bout", "event1", {"data": "first"})
        entry2 = audit.log_event("test_bout", "event2", {"data": "second"})
        entry3 = audit.log_event("test_bout", "event3", {"data": "third"})
        
        # Chain should link correctly
        assert entry2.previous_hash == entry1.current_hash
        assert entry3.previous_hash == entry2.current_hash
        
        print(f"✓ Hash chaining: 3 entries properly linked")
    
    def test_tamper_detection(self):
        """Test: Tamper detection works"""
        audit = AdvancedAuditEngine()
        
        # Create chain
        audit.log_event("test_bout", "event1", {"data": "first"})
        audit.log_event("test_bout", "event2", {"data": "second"})
        
        # Tamper with chain
        chain = audit.chains["test_bout"]
        chain[1].payload["data"] = "TAMPERED"  # Change data without recalculating hash
        
        # Verify - should detect tamper
        result = audit.verify_chain("test_bout")
        
        assert result.tampered == True
        assert result.valid == False
        assert result.tamper_detected_at is not None
        
        print(f"✓ Tamper detected at entry {result.tamper_detected_at}")
    
    def test_chain_verification_valid(self):
        """Test: Valid chain passes verification"""
        audit = AdvancedAuditEngine()
        
        # Create valid chain
        for i in range(5):
            audit.log_event("test_bout", f"event_{i}", {"seq": i})
        
        result = audit.verify_chain("test_bout")
        
        assert result.valid == True
        assert result.tampered == False
        assert result.verified_entries == 5
        
        print(f"✓ Valid chain: {result.verified_entries}/{result.total_entries} verified")
    
    def test_metadata_tracking(self):
        """Test: Tracks CV version, judge device, etc."""
        audit = AdvancedAuditEngine()
        
        entry = audit.log_event(
            "test_bout",
            "scoring_output",
            {"score": "10-9"},
            actor="scoring_engine",
            cv_version="1.0.0",
            judge_device_id="JUDGE_TABLET_001",
            scoring_engine_version="1.0.0"
        )
        
        assert entry.cv_version == "1.0.0"
        assert entry.judge_device_id == "JUDGE_TABLET_001"
        assert entry.scoring_engine_version == "1.0.0"
        
        print(f"✓ Metadata tracked: CV={entry.cv_version}, Judge={entry.judge_device_id}")


class TestScoringSimulator:
    """Test Scoring Simulator"""
    
    @pytest.mark.asyncio
    async def test_simulation_execution(self):
        """Test: Simulation runs successfully"""
        simulator = ScoringSimulatorEngine()
        
        # Create mock events
        events = [
            CombatEvent(
                bout_id="SIM_001",
                round_id="round_1",
                fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG,
                severity=0.6,
                confidence=0.85,
                timestamp_ms=1000 + (i * 1000),
                source=EventSource.MANUAL
            )
            for i in range(10)
        ]
        
        script = SimulationScript(
            bout_id="SIM_001",
            event_name="Test Simulation",
            fighters={"fighter_a": "Fighter A", "fighter_b": "Fighter B"},
            events=events,
            speed_multiplier=5.0  # 5x speed
        )
        
        result = await simulator.run_simulation(script)
        
        assert result.bout_id == "SIM_001"
        assert len(result.round_results) > 0
        assert result.total_events_processed == 10
        
        print(f"✓ Simulation: {result.total_events_processed} events in {result.simulation_duration_sec:.2f}s")
    
    @pytest.mark.asyncio
    async def test_speed_multiplier(self):
        """Test: Speed multiplier affects duration"""
        simulator = ScoringSimulatorEngine()
        
        events = [
            CombatEvent(
                bout_id="SPEED_TEST",
                round_id="round_1",
                fighter_id="fighter_a",
                event_type=EventType.STRIKE_SIG,
                severity=0.6,
                confidence=0.85,
                timestamp_ms=1000 + (i * 1000),
                source=EventSource.MANUAL
            )
            for i in range(5)
        ]
        
        # 1x speed
        script_1x = SimulationScript(
            bout_id="SPEED_1X",
            event_name="Test",
            fighters={"fighter_a": "A", "fighter_b": "B"},
            events=events,
            speed_multiplier=1.0
        )
        
        # 5x speed
        script_5x = SimulationScript(
            bout_id="SPEED_5X",
            event_name="Test",
            fighters={"fighter_a": "A", "fighter_b": "B"},
            events=events,
            speed_multiplier=5.0
        )
        
        result_1x = await simulator.run_simulation(script_1x)
        result_5x = await simulator.run_simulation(script_5x)
        
        # 5x should be faster
        assert result_5x.simulation_duration_sec < result_1x.simulation_duration_sec
        
        print(f"✓ Speed test: 1x={result_1x.simulation_duration_sec:.2f}s, 5x={result_5x.simulation_duration_sec:.2f}s")


class TestFailoverEngine:
    """Test Failover Engine"""
    
    def test_default_cloud_mode(self):
        """Test: Starts in cloud mode"""
        failover = FailoverManager()
        
        status = failover.get_status()
        
        assert status.current_mode == CVEngineMode.CLOUD
        assert status.cloud_health.healthy == True
        
        print(f"✓ Default mode: {status.current_mode.value}")
    
    @pytest.mark.asyncio
    async def test_failover_cloud_to_local(self):
        """Test: Failover from cloud to local"""
        failover = FailoverManager()
        
        # Manually trigger failover
        await failover._failover(CVEngineMode.LOCAL, "Cloud failed (test)")
        
        status = failover.get_status()
        
        # Should have failed over to local
        assert status.current_mode == CVEngineMode.LOCAL
        assert status.failover_count == 1
        
        print(f"✓ Failover: CLOUD → LOCAL (count={status.failover_count})")
    
    @pytest.mark.asyncio
    async def test_failover_to_manual(self):
        """Test: Failover to manual when both fail"""
        failover = FailoverManager()
        
        # Manually trigger failover to manual
        await failover._failover(CVEngineMode.MANUAL, "Both failed (test)")
        
        status = failover.get_status()
        
        # Should fallback to manual
        assert status.current_mode == CVEngineMode.MANUAL
        
        print(f"✓ Failover: BOTH FAILED → MANUAL")
    
    @pytest.mark.asyncio
    async def test_heartbeat_updates(self):
        """Test: Heartbeat updates health"""
        failover = FailoverManager()
        
        await failover.update_cloud_heartbeat(response_time_ms=45.0, error_rate=0.05)
        
        status = failover.get_status()
        
        assert status.cloud_health.response_time_ms == 45.0
        assert status.cloud_health.error_rate == 0.05
        
        print(f"✓ Heartbeat: response={status.cloud_health.response_time_ms}ms, errors={status.cloud_health.error_rate}")


class TestTimeSyncService:
    """Test Time Sync Service"""
    
    def test_get_current_time(self):
        """Test: Get unified timestamp"""
        sync = TimeSyncEngine()
        
        time_sync = sync.get_current_time()
        
        assert time_sync.server_timestamp_ms > 0
        assert len(time_sync.server_time_iso) > 0
        assert time_sync.response_sent_ms >= time_sync.request_received_ms
        
        print(f"✓ Timestamp: {time_sync.server_time_iso}")
    
    def test_client_sync_drift_calculation(self):
        """Test: Calculates client drift"""
        sync = TimeSyncEngine()
        
        # Client with 500ms lag
        server_time = int(time.time() * 1000)
        client_time = server_time - 500
        
        client_sync = sync.register_client_sync(
            "judge_tablet_1",
            "judge_tablet",
            client_time
        )
        
        # Should detect ~500ms drift
        assert abs(client_sync.drift_ms - 500) < 100  # Allow 100ms tolerance
        
        print(f"✓ Drift calculation: {client_sync.drift_ms:.0f}ms")
    
    def test_drift_correction(self):
        """Test: Applies correction for large drift"""
        sync = TimeSyncEngine()
        
        # Client with 200ms drift (>100ms threshold)
        server_time = int(time.time() * 1000)
        client_time = server_time - 200
        
        client_sync = sync.register_client_sync(
            "cv_engine_1",
            "cv_engine",
            client_time
        )
        
        assert client_sync.correction_applied == True
        assert abs(client_sync.corrected_drift_ms) > 0
        
        print(f"✓ Correction applied: {client_sync.corrected_drift_ms:.0f}ms")
    
    def test_jitter_calculation(self):
        """Test: Calculates jitter from drift history"""
        sync = TimeSyncEngine()
        
        server_time = int(time.time() * 1000)
        
        # Multiple syncs with varying drift
        for i in range(5):
            client_time = server_time - (100 + (i * 10))  # 100, 110, 120, 130, 140ms drift
            sync.register_client_sync("device_1", "cv_engine", client_time)
            time.sleep(0.01)
        
        # Get stats
        stats = sync.get_stats()
        
        assert stats.synced_clients == 1
        assert stats.avg_jitter_ms >= 0
        
        print(f"✓ Jitter: {stats.avg_jitter_ms:.2f}ms")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ENTERPRISE SERVICES TEST SUITE")
    print("="*80 + "\n")
    
    test_audit = TestAdvancedAudit()
    test_simulator = TestScoringSimulator()
    test_failover = TestFailoverEngine()
    test_time_sync = TestTimeSyncService()
    
    print("Testing Advanced Audit Logger...")
    test_audit.test_blockchain_chain_creation()
    test_audit.test_hash_chaining()
    test_audit.test_tamper_detection()
    test_audit.test_chain_verification_valid()
    test_audit.test_metadata_tracking()
    
    print("\nTesting Scoring Simulator...")
    asyncio.run(test_simulator.test_simulation_execution())
    asyncio.run(test_simulator.test_speed_multiplier())
    
    print("\nTesting Failover Engine...")
    test_failover.test_default_cloud_mode()
    asyncio.run(test_failover.test_failover_cloud_to_local())
    asyncio.run(test_failover.test_failover_to_manual())
    asyncio.run(test_failover.test_heartbeat_updates())
    
    print("\nTesting Time Sync Service...")
    test_time_sync.test_get_current_time()
    test_time_sync.test_client_sync_drift_calculation()
    test_time_sync.test_drift_correction()
    test_time_sync.test_jitter_calculation()
    
    print("\n" + "="*80)
    print("✅ ALL ENTERPRISE SERVICE TESTS PASSED")
    print("="*80 + "\n")
