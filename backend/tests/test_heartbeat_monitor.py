"""
Comprehensive Test Suite for Heartbeat Monitor
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app

client = TestClient(app)


# ============================================================================
# HEARTBEAT MONITOR TESTS
# ============================================================================

def test_heartbeat_monitor_health():
    """Test Heartbeat Monitor health check"""
    response = client.get("/api/heartbeat/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Heartbeat Monitor"
    assert data["version"] == "1.0.0"
    print("✅ Heartbeat Monitor health check passed")


def test_send_heartbeat_cv_router():
    """Test sending a heartbeat from CV Router"""
    heartbeat_data = {
        "service_name": "CV Router",
        "status": "ok",
        "metrics": {
            "event_count": 1250,
            "error_count": 0,
            "latency_ms": 45,
            "uptime_seconds": 3600
        }
    }
    
    response = client.post("/api/heartbeat", json=heartbeat_data)
    assert response.status_code == 201
    data = response.json()
    
    # Check response structure
    assert "id" in data
    assert data["service_name"] == "CV Router"
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "received_at" in data
    assert data["metrics"]["event_count"] == 1250
    
    print("✅ CV Router heartbeat recorded successfully")


def test_send_heartbeat_all_services():
    """Test sending heartbeats from all services"""
    services = [
        "CV Router",
        "CV Analytics",
        "Scoring Engine",
        "Replay Worker",
        "Highlight Worker",
        "Storage Manager",
        "Supervisor Console"
    ]
    
    for service_name in services:
        heartbeat_data = {
            "service_name": service_name,
            "status": "ok",
            "metrics": {
                "event_count": 100,
                "error_count": 0,
                "latency_ms": 30
            }
        }
        
        response = client.post("/api/heartbeat", json=heartbeat_data)
        assert response.status_code == 201
        assert response.json()["service_name"] == service_name
    
    print(f"✅ All {len(services)} service heartbeats recorded successfully")


def test_get_heartbeat_summary():
    """Test getting heartbeat summary"""
    # Send a heartbeat first
    client.post("/api/heartbeat", json={
        "service_name": "CV Router",
        "status": "ok",
        "metrics": {"event_count": 500}
    })
    
    # Get summary
    response = client.get("/api/heartbeat/summary")
    assert response.status_code == 200
    data = response.json()
    
    # Check summary structure
    assert "total_services" in data
    assert "healthy_services" in data
    assert "warning_services" in data
    assert "error_services" in data
    assert "offline_services" in data
    assert "services" in data
    assert "last_updated" in data
    
    # Should have 7 expected services
    assert data["total_services"] == 7
    assert isinstance(data["services"], list)
    assert len(data["services"]) == 7
    
    print("✅ Heartbeat summary retrieved successfully")
    print(f"   Total: {data['total_services']}, Healthy: {data['healthy_services']}, Offline: {data['offline_services']}")


def test_service_status_tracking():
    """Test service status tracking"""
    # Send heartbeats with different statuses
    client.post("/api/heartbeat", json={
        "service_name": "CV Router",
        "status": "ok",
        "metrics": {}
    })
    
    client.post("/api/heartbeat", json={
        "service_name": "CV Analytics",
        "status": "warning",
        "metrics": {"error_count": 5}
    })
    
    client.post("/api/heartbeat", json={
        "service_name": "Scoring Engine",
        "status": "error",
        "metrics": {"error_count": 20}
    })
    
    # Get summary
    response = client.get("/api/heartbeat/summary")
    data = response.json()
    
    # Find services in summary
    cv_router = next(s for s in data["services"] if s["service_name"] == "CV Router")
    cv_analytics = next(s for s in data["services"] if s["service_name"] == "CV Analytics")
    scoring_engine = next(s for s in data["services"] if s["service_name"] == "Scoring Engine")
    
    assert cv_router["status"] == "ok"
    assert cv_analytics["status"] == "warning"
    assert scoring_engine["status"] == "error"
    
    print("✅ Service status tracking working correctly")


def test_heartbeat_with_metrics():
    """Test heartbeat with various metrics"""
    heartbeat_data = {
        "service_name": "Storage Manager",
        "status": "ok",
        "metrics": {
            "event_count": 5000,
            "error_count": 2,
            "latency_ms": 15,
            "memory_mb": 256,
            "uptime_seconds": 7200,
            "storage_used_gb": 45.3
        }
    }
    
    response = client.post("/api/heartbeat", json=heartbeat_data)
    assert response.status_code == 201
    data = response.json()
    
    # Verify all metrics preserved
    assert data["metrics"]["event_count"] == 5000
    assert data["metrics"]["error_count"] == 2
    assert data["metrics"]["latency_ms"] == 15
    assert data["metrics"]["memory_mb"] == 256
    assert data["metrics"]["uptime_seconds"] == 7200
    assert data["metrics"]["storage_used_gb"] == 45.3
    
    print("✅ Heartbeat with complex metrics recorded successfully")


def test_service_time_tracking():
    """Test time since last heartbeat"""
    # Send a heartbeat
    client.post("/api/heartbeat", json={
        "service_name": "Replay Worker",
        "status": "ok",
        "metrics": {}
    })
    
    # Get summary immediately
    response = client.get("/api/heartbeat/summary")
    data = response.json()
    
    replay_worker = next(s for s in data["services"] if s["service_name"] == "Replay Worker")
    
    # Should have received heartbeat recently
    assert replay_worker["last_heartbeat"] is not None
    assert replay_worker["time_since_last_heartbeat_sec"] is not None
    assert replay_worker["time_since_last_heartbeat_sec"] < 5  # Less than 5 seconds ago
    
    print(f"✅ Time tracking working: {replay_worker['time_since_last_heartbeat_sec']:.2f}s since last heartbeat")


def test_invalid_service_name():
    """Test heartbeat with invalid service name"""
    heartbeat_data = {
        "service_name": "Invalid Service",
        "status": "ok",
        "metrics": {}
    }
    
    response = client.post("/api/heartbeat", json=heartbeat_data)
    # Should fail validation
    assert response.status_code == 422
    
    print("✅ Invalid service name validation working correctly")


def test_invalid_status():
    """Test heartbeat with invalid status"""
    heartbeat_data = {
        "service_name": "CV Router",
        "status": "invalid_status",
        "metrics": {}
    }
    
    response = client.post("/api/heartbeat", json=heartbeat_data)
    # Should fail validation
    assert response.status_code == 422
    
    print("✅ Invalid status validation working correctly")


def test_heartbeat_summary_structure():
    """Test heartbeat summary structure comprehensively"""
    # Send heartbeats from multiple services
    for i, service in enumerate(["CV Router", "CV Analytics", "Scoring Engine"]):
        client.post("/api/heartbeat", json={
            "service_name": service,
            "status": "ok" if i == 0 else "warning",
            "metrics": {"event_count": 100 * (i + 1)}
        })
    
    response = client.get("/api/heartbeat/summary")
    data = response.json()
    
    # Verify summary calculations
    assert data["total_services"] == 7  # All expected services
    assert data["healthy_services"] >= 1  # At least CV Router
    
    # Verify each service has required fields
    for service in data["services"]:
        assert "service_name" in service
        assert "status" in service
        assert "is_healthy" in service
        assert service["status"] in ["ok", "warning", "error", "offline"]
    
    print("✅ Heartbeat summary structure validated")


def test_multiple_heartbeats_same_service():
    """Test sending multiple heartbeats from same service"""
    # Send first heartbeat
    response1 = client.post("/api/heartbeat", json={
        "service_name": "Highlight Worker",
        "status": "ok",
        "metrics": {"event_count": 100}
    })
    assert response1.status_code == 201
    
    # Wait a moment
    time.sleep(0.1)
    
    # Send second heartbeat with updated metrics
    response2 = client.post("/api/heartbeat", json={
        "service_name": "Highlight Worker",
        "status": "ok",
        "metrics": {"event_count": 150}
    })
    assert response2.status_code == 201
    
    # Get summary - should show latest heartbeat
    summary = client.get("/api/heartbeat/summary")
    data = summary.json()
    
    highlight_worker = next(s for s in data["services"] if s["service_name"] == "Highlight Worker")
    assert highlight_worker["metrics"]["event_count"] == 150  # Updated value
    
    print("✅ Multiple heartbeats from same service handled correctly")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE: HEARTBEAT MONITOR")
    print("="*80 + "\n")
    
    # Run all tests
    pytest.main([__file__, "-v", "-s"])
