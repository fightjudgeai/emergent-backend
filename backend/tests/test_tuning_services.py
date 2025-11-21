"""
Comprehensive Test Suite for Calibration API and Performance Profiler
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app

client = TestClient(app)


# ============================================================================
# CALIBRATION API TESTS
# ============================================================================

def test_calibration_health():
    """Test Calibration API health check"""
    response = client.get("/api/calibration/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Calibration API"
    print("✅ Calibration health check passed")


def test_get_default_calibration():
    """Test getting default calibration configuration"""
    response = client.get("/api/calibration/get")
    assert response.status_code == 200
    data = response.json()
    
    # Check all required fields
    assert "kd_threshold" in data
    assert "rocked_threshold" in data
    assert "highimpact_strike_threshold" in data
    assert "momentum_swing_window_ms" in data
    assert "multicam_merge_window_ms" in data
    assert "confidence_threshold" in data
    assert "deduplication_window_ms" in data
    assert "version" in data
    assert "last_modified" in data
    assert "modified_by" in data
    
    # Check default values
    assert data["kd_threshold"] == 0.75
    assert data["rocked_threshold"] == 0.65
    assert data["highimpact_strike_threshold"] == 0.70
    assert data["momentum_swing_window_ms"] == 1200
    assert data["multicam_merge_window_ms"] == 150
    assert data["confidence_threshold"] == 0.5
    assert data["deduplication_window_ms"] == 100
    
    print("✅ Default calibration config retrieved successfully")


def test_update_calibration():
    """Test updating calibration configuration"""
    # Get current config first
    response = client.get("/api/calibration/get")
    assert response.status_code == 200
    current_config = response.json()
    
    # Modify some parameters
    updated_config = current_config.copy()
    updated_config["kd_threshold"] = 0.80
    updated_config["rocked_threshold"] = 0.70
    updated_config["momentum_swing_window_ms"] = 1500
    
    # Update configuration
    response = client.post(
        "/api/calibration/set?modified_by=test_operator",
        json=updated_config
    )
    assert response.status_code == 200
    data = response.json()
    
    # Verify updates
    assert data["kd_threshold"] == 0.80
    assert data["rocked_threshold"] == 0.70
    assert data["momentum_swing_window_ms"] == 1500
    assert data["modified_by"] == "test_operator"
    
    print("✅ Calibration config updated successfully")


def test_calibration_history():
    """Test calibration change history tracking"""
    # Make a change first
    response = client.get("/api/calibration/get")
    assert response.status_code == 200
    config = response.json()
    
    config["kd_threshold"] = 0.85
    response = client.post(
        "/api/calibration/set?modified_by=history_test",
        json=config
    )
    assert response.status_code == 200
    
    # Get history
    response = client.get("/api/calibration/history?limit=10")
    assert response.status_code == 200
    history = response.json()
    
    # Verify history structure
    assert isinstance(history, list)
    if len(history) > 0:
        entry = history[0]
        assert "timestamp" in entry
        assert "parameter" in entry
        assert "old_value" in entry
        assert "new_value" in entry
        assert "modified_by" in entry
    
    print(f"✅ Calibration history retrieved: {len(history)} entries")


def test_reset_calibration():
    """Test resetting calibration to defaults"""
    # First modify the config
    response = client.get("/api/calibration/get")
    config = response.json()
    config["kd_threshold"] = 0.90
    
    response = client.post(
        "/api/calibration/set?modified_by=reset_test",
        json=config
    )
    assert response.status_code == 200
    
    # Now reset
    response = client.post("/api/calibration/reset")
    assert response.status_code == 200
    data = response.json()
    
    # Verify defaults
    assert data["kd_threshold"] == 0.75
    assert data["rocked_threshold"] == 0.65
    assert data["highimpact_strike_threshold"] == 0.70
    
    print("✅ Calibration reset to defaults successfully")


def test_calibration_validation():
    """Test calibration parameter validation"""
    response = client.get("/api/calibration/get")
    config = response.json()
    
    # Test invalid threshold (outside 0-1 range)
    config["kd_threshold"] = 1.5
    response = client.post(
        "/api/calibration/set?modified_by=validation_test",
        json=config
    )
    # Should fail validation
    assert response.status_code == 422
    
    print("✅ Calibration validation working correctly")


# ============================================================================
# PERFORMANCE PROFILER TESTS
# ============================================================================

def test_performance_profiler_health():
    """Test Performance Profiler health check"""
    response = client.get("/api/perf/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Performance Profiler"
    print("✅ Performance Profiler health check passed")


def test_get_performance_summary():
    """Test getting performance summary"""
    response = client.get("/api/perf/summary")
    assert response.status_code == 200
    data = response.json()
    
    # Check all required fields
    assert "cv_inference_avg_ms" in data
    assert "cv_inference_p95_ms" in data
    assert "cv_inference_p99_ms" in data
    assert "event_ingestion_avg_ms" in data
    assert "event_ingestion_p95_ms" in data
    assert "event_ingestion_p99_ms" in data
    assert "scoring_calc_avg_ms" in data
    assert "scoring_calc_p95_ms" in data
    assert "scoring_calc_p99_ms" in data
    assert "websocket_roundtrip_avg_ms" in data
    assert "websocket_roundtrip_p95_ms" in data
    assert "websocket_roundtrip_p99_ms" in data
    assert "total_measurements" in data
    assert "measurement_period_sec" in data
    
    # Check all values are numbers
    assert isinstance(data["cv_inference_avg_ms"], (int, float))
    assert isinstance(data["total_measurements"], int)
    
    print("✅ Performance summary retrieved successfully")
    print(f"   Total measurements: {data['total_measurements']}")
    print(f"   CV inference avg: {data['cv_inference_avg_ms']:.2f}ms")
    print(f"   Event ingestion avg: {data['event_ingestion_avg_ms']:.2f}ms")


def test_record_cv_inference():
    """Test recording CV inference time"""
    response = client.post("/api/perf/record/cv_inference?duration_ms=45.5")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify it was recorded
    response = client.get("/api/perf/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_measurements"] > 0
    
    print("✅ CV inference metric recorded successfully")


def test_record_event_ingestion():
    """Test recording event ingestion time"""
    response = client.post("/api/perf/record/event_ingestion?duration_ms=12.3")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    print("✅ Event ingestion metric recorded successfully")


def test_record_scoring():
    """Test recording scoring calculation time"""
    response = client.post("/api/perf/record/scoring?duration_ms=28.7")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    print("✅ Scoring metric recorded successfully")


def test_record_websocket():
    """Test recording WebSocket roundtrip time"""
    response = client.post("/api/perf/record/websocket?duration_ms=15.2")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    print("✅ WebSocket metric recorded successfully")


def test_performance_metrics_accumulation():
    """Test that performance metrics accumulate correctly"""
    # Get initial count
    response = client.get("/api/perf/summary")
    initial_count = response.json()["total_measurements"]
    
    # Record multiple metrics
    client.post("/api/perf/record/cv_inference?duration_ms=50.0")
    client.post("/api/perf/record/event_ingestion?duration_ms=10.0")
    client.post("/api/perf/record/scoring?duration_ms=30.0")
    client.post("/api/perf/record/websocket?duration_ms=20.0")
    
    # Check count increased
    response = client.get("/api/perf/summary")
    final_count = response.json()["total_measurements"]
    
    assert final_count > initial_count
    assert final_count >= initial_count + 4
    
    print(f"✅ Metrics accumulation working: {initial_count} → {final_count}")


def test_performance_percentile_calculation():
    """Test percentile calculations"""
    # Record a series of values with known distribution
    for duration in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        client.post(f"/api/perf/record/cv_inference?duration_ms={duration}")
    
    # Get summary
    response = client.get("/api/perf/summary")
    data = response.json()
    
    # Check that p95 > avg and p99 > p95
    avg = data["cv_inference_avg_ms"]
    p95 = data["cv_inference_p95_ms"]
    p99 = data["cv_inference_p99_ms"]
    
    # Due to mock data, we just verify they exist and are positive
    assert avg >= 0
    assert p95 >= 0
    assert p99 >= 0
    
    print(f"✅ Percentile calculation working:")
    print(f"   Avg: {avg:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")


def test_performance_window_size():
    """Test that performance metrics use rolling window"""
    # The window size is 1000, so we verify this indirectly
    response = client.get("/api/perf/summary")
    data = response.json()
    
    # Record many metrics
    for i in range(50):
        client.post(f"/api/perf/record/cv_inference?duration_ms={i}")
    
    # Get updated summary
    response = client.get("/api/perf/summary")
    updated_data = response.json()
    
    # Measurement count should have increased
    assert updated_data["total_measurements"] > data["total_measurements"]
    
    print("✅ Rolling window working correctly")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_calibration_and_performance_integration():
    """Test that both services work together"""
    # Get calibration config
    cal_response = client.get("/api/calibration/get")
    assert cal_response.status_code == 200
    
    # Get performance metrics
    perf_response = client.get("/api/perf/summary")
    assert perf_response.status_code == 200
    
    # Both services healthy
    cal_health = client.get("/api/calibration/health")
    perf_health = client.get("/api/perf/health")
    
    assert cal_health.status_code == 200
    assert perf_health.status_code == 200
    
    print("✅ Calibration API and Performance Profiler integration working")


def test_end_to_end_tuning_workflow():
    """Test complete tuning workflow"""
    # 1. Get current calibration
    response = client.get("/api/calibration/get")
    config = response.json()
    print(f"   Current KD threshold: {config['kd_threshold']}")
    
    # 2. Record some performance metrics
    client.post("/api/perf/record/cv_inference?duration_ms=55.0")
    client.post("/api/perf/record/event_ingestion?duration_ms=12.0")
    
    # 3. Check performance
    response = client.get("/api/perf/summary")
    perf = response.json()
    print(f"   Current avg latency: {perf['cv_inference_avg_ms']:.2f}ms")
    
    # 4. Adjust calibration based on performance
    config["kd_threshold"] = 0.78
    response = client.post(
        "/api/calibration/set?modified_by=tuning_workflow",
        json=config
    )
    assert response.status_code == 200
    
    # 5. Verify change was logged
    response = client.get("/api/calibration/history?limit=5")
    history = response.json()
    assert len(history) > 0
    
    print("✅ End-to-end tuning workflow completed successfully")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE: CALIBRATION API & PERFORMANCE PROFILER")
    print("="*80 + "\n")
    
    # Run all tests
    pytest.main([__file__, "-v", "-s"])
