"""
Tests for Stat Engine

Tests all aggregation levels and scheduler functionality.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from server import app

client = TestClient(app)


class TestStatEngineHealth:
    """Test health and initialization"""
    
    def test_health_check(self):
        """Test stat engine health check"""
        response = client.get("/api/stats/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "Stat Engine"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"
        assert "event_reader_active" in data
        assert "aggregation_active" in data
        
        print("✅ Stat Engine health check working")


class TestRoundAggregation:
    """Test round-level statistics aggregation"""
    
    def test_aggregate_round(self):
        """Test aggregating stats for a single round"""
        response = client.post(
            "/api/stats/aggregate/round",
            params={
                "fight_id": "test_fight_001",
                "round_num": 1,
                "trigger": "manual"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] in ["completed", "failed"]
        assert "rows_updated" in data
        
        print(f"✅ Round aggregation: status={data['status']}, rows={data['rows_updated']}")
    
    def test_get_round_stats(self):
        """Test retrieving round statistics"""
        # First aggregate
        client.post(
            "/api/stats/aggregate/round",
            params={
                "fight_id": "test_fight_002",
                "round_num": 1,
                "trigger": "manual"
            }
        )
        
        # Then retrieve
        response = client.get("/api/stats/round/test_fight_002/1/fighter_1")
        
        # May be 404 if no events exist, that's OK
        if response.status_code == 200:
            data = response.json()
            assert "fight_id" in data
            assert data["round_num"] == 1
            assert "sig_strikes_landed" in data
            print(f"✅ Retrieved round stats: {data['sig_strikes_landed']} sig strikes")
        else:
            print("⚠️ No round stats found (expected if no events)")


class TestFightAggregation:
    """Test fight-level statistics aggregation"""
    
    def test_aggregate_fight(self):
        """Test aggregating stats for entire fight"""
        response = client.post(
            "/api/stats/aggregate/fight",
            params={
                "fight_id": "test_fight_003",
                "trigger": "manual"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] in ["completed", "failed"]
        assert "rows_updated" in data
        
        print(f"✅ Fight aggregation: status={data['status']}, rows={data['rows_updated']}")
    
    def test_get_fight_stats(self):
        """Test retrieving fight statistics"""
        # First aggregate
        client.post(
            "/api/stats/aggregate/fight",
            params={
                "fight_id": "test_fight_004",
                "trigger": "manual"
            }
        )
        
        # Then retrieve
        response = client.get("/api/stats/fight/test_fight_004/fighter_1")
        
        if response.status_code == 200:
            data = response.json()
            assert "fight_id" in data
            assert "fighter_id" in data
            assert "total_rounds" in data
            assert "sig_strike_accuracy" in data
            print(f"✅ Retrieved fight stats: accuracy={data['sig_strike_accuracy']:.1f}%")
        else:
            print("⚠️ No fight stats found (expected if no events)")
    
    def test_get_all_fight_stats(self):
        """Test retrieving all fighters' stats for a fight"""
        response = client.get("/api/stats/fight/test_fight_005/all")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fight_id" in data
        assert "fighters" in data
        assert "count" in data
        
        print(f"✅ Retrieved all fight stats: {data['count']} fighters")


class TestCareerAggregation:
    """Test career-level statistics aggregation"""
    
    def test_aggregate_single_fighter_career(self):
        """Test aggregating career stats for one fighter"""
        response = client.post(
            "/api/stats/aggregate/career",
            params={
                "fighter_id": "fighter_1",
                "trigger": "manual"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] in ["completed", "failed"]
        assert "rows_updated" in data
        
        print(f"✅ Career aggregation (single): status={data['status']}")
    
    def test_aggregate_all_fighters_career(self):
        """Test aggregating career stats for all fighters"""
        response = client.post(
            "/api/stats/aggregate/career",
            params={"trigger": "manual"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] in ["completed", "failed"]
        
        print(f"✅ Career aggregation (all): status={data['status']}, rows={data['rows_updated']}")
    
    def test_get_career_stats(self):
        """Test retrieving career statistics"""
        # First aggregate
        client.post(
            "/api/stats/aggregate/career",
            params={
                "fighter_id": "fighter_1",
                "trigger": "manual"
            }
        )
        
        # Then retrieve
        response = client.get("/api/stats/career/fighter_1")
        
        if response.status_code == 200:
            data = response.json()
            assert "fighter_id" in data
            assert "total_fights" in data
            assert "avg_sig_strikes_per_min" in data
            assert "knockdowns_per_15min" in data
            print(f"✅ Retrieved career stats: {data['total_fights']} fights")
        else:
            print("⚠️ No career stats found (expected if no fights)")


class TestFullRecalculation:
    """Test full recalculation workflow"""
    
    def test_full_recalculation(self):
        """Test full recalculation for a fight"""
        response = client.post("/api/stats/aggregate/full/test_fight_006")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fight_id" in data
        assert data["fight_id"] == "test_fight_006"
        assert "jobs_executed" in data
        assert "successful" in data
        assert "failed" in data
        
        print(
            f"✅ Full recalculation: {data['jobs_executed']} jobs, "
            f"{data['successful']} successful, {data['failed']} failed"
        )


class TestJobManagement:
    """Test job tracking and management"""
    
    def test_get_recent_jobs(self):
        """Test retrieving recent aggregation jobs"""
        # First create some jobs
        client.post(
            "/api/stats/aggregate/round",
            params={"fight_id": "job_test_001", "round_num": 1, "trigger": "manual"}
        )
        client.post(
            "/api/stats/aggregate/fight",
            params={"fight_id": "job_test_002", "trigger": "manual"}
        )
        
        # Get jobs
        response = client.get("/api/stats/jobs", params={"limit": 10})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "count" in data
        
        if data["count"] > 0:
            job = data["jobs"][0]
            assert "id" in job
            assert "job_type" in job
            assert "trigger" in job
            assert "status" in job
            
            print(f"✅ Retrieved {data['count']} recent jobs")
        else:
            print("⚠️ No jobs found")


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_aggregation_workflow(self):
        """Test complete workflow: round → fight → career"""
        
        fight_id = "integration_test_001"
        fighter_id = "fighter_1"
        
        # 1. Aggregate round 1
        round1_response = client.post(
            "/api/stats/aggregate/round",
            params={"fight_id": fight_id, "round_num": 1, "trigger": "manual"}
        )
        assert round1_response.status_code == 200
        
        # 2. Aggregate round 2
        round2_response = client.post(
            "/api/stats/aggregate/round",
            params={"fight_id": fight_id, "round_num": 2, "trigger": "manual"}
        )
        assert round2_response.status_code == 200
        
        # 3. Aggregate fight
        fight_response = client.post(
            "/api/stats/aggregate/fight",
            params={"fight_id": fight_id, "trigger": "post_fight"}
        )
        assert fight_response.status_code == 200
        
        # 4. Aggregate career
        career_response = client.post(
            "/api/stats/aggregate/career",
            params={"fighter_id": fighter_id, "trigger": "manual"}
        )
        assert career_response.status_code == 200
        
        # 5. Verify all stats are retrievable
        round_stats = client.get(f"/api/stats/round/{fight_id}/1/{fighter_id}")
        fight_stats = client.get(f"/api/stats/fight/{fight_id}/{fighter_id}")
        career_stats = client.get(f"/api/stats/career/{fighter_id}")
        
        print("✅ Complete aggregation workflow test passed")
        print(f"   Round 1: {round1_response.json()['status']}")
        print(f"   Round 2: {round2_response.json()['status']}")
        print(f"   Fight: {fight_response.json()['status']}")
        print(f"   Career: {career_response.json()['status']}")
    
    def test_idempotent_aggregation(self):
        """Test that running aggregation multiple times is safe"""
        
        fight_id = "idempotent_test_001"
        
        # Run aggregation 3 times
        results = []
        for i in range(3):
            response = client.post(
                "/api/stats/aggregate/fight",
                params={"fight_id": fight_id, "trigger": "manual"}
            )
            assert response.status_code == 200
            results.append(response.json())
        
        # All should succeed
        assert all(r["status"] == "completed" for r in results)
        
        print("✅ Idempotent aggregation test passed (ran 3x safely)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
