"""
Tests for Real-Time CV System

Tests both the CV analysis engine and data collection system.
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


class TestRealtimeCVHealth:
    """Test health endpoints"""
    
    def test_cv_health(self):
        """Test CV engine health check"""
        response = client.get("/api/realtime-cv/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Real-Time CV"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"
        assert "models_loaded" in data
        assert "active_streams" in data
        print(f"✅ CV health check working: {data['models_loaded']} models loaded")
    
    def test_data_collector_health(self):
        """Test data collector health check"""
        response = client.get("/api/cv-data/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "CV Data Collection"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"
        print("✅ Data collector health check working")


class TestCVModels:
    """Test CV model management"""
    
    def test_get_loaded_models(self):
        """Test retrieving loaded CV models"""
        response = client.get("/api/realtime-cv/models")
        assert response.status_code == 200
        data = response.json()
        
        assert "models" in data
        assert "count" in data
        assert "total_loaded" in data
        
        # Should have MediaPipe, YOLO, and custom action model
        assert data["count"] >= 2  # At least MediaPipe and YOLO
        
        # Verify model structure
        models = data["models"]
        for model in models:
            assert "model_id" in model
            assert "model_name" in model
            assert "model_type" in model
            assert "framework" in model
            assert "version" in model
            assert "inference_time_ms" in model
            assert "is_loaded" in model
        
        print(f"✅ Loaded models: {data['count']}, Active: {data['total_loaded']}")
        for model in models:
            print(f"   - {model['model_name']} ({model['framework']}) - {model['model_type']}")


class TestStreamManagement:
    """Test video stream management"""
    
    def test_start_stream_analysis(self):
        """Test starting a video stream analysis"""
        stream_config = {
            "bout_id": "test_bout_001",
            "camera_id": "main_camera",
            "stream_url": "rtsp://example.com/stream",
            "stream_type": "rtsp",
            "fps_target": 30,
            "analysis_fps": 10,
            "enable_pose_estimation": True,
            "enable_action_detection": True,
            "enable_object_tracking": True
        }
        
        response = client.post("/api/realtime-cv/streams/start", json=stream_config)
        assert response.status_code == 200
        data = response.json()
        
        assert "stream_id" in data
        assert data["bout_id"] == "test_bout_001"
        assert data["camera_id"] == "main_camera"
        assert data["status"] == "active"
        assert "config" in data
        
        print(f"✅ Stream started: {data['stream_id']}")
        
        # Store stream_id for later tests
        self.stream_id = data["stream_id"]
        return data["stream_id"]
    
    def test_get_active_streams(self):
        """Test retrieving active streams"""
        # Start a stream first
        stream_id = self.test_start_stream_analysis()
        
        response = client.get("/api/realtime-cv/streams/active")
        assert response.status_code == 200
        data = response.json()
        
        assert "active_streams" in data
        assert "count" in data
        assert data["count"] >= 1
        
        # Verify stream is in the list
        stream_ids = [s["stream_id"] for s in data["active_streams"]]
        assert stream_id in stream_ids
        
        print(f"✅ Active streams: {data['count']}")
    
    def test_stop_stream_analysis(self):
        """Test stopping a video stream"""
        # Start a stream first
        stream_id = self.test_start_stream_analysis()
        
        response = client.post(f"/api/realtime-cv/streams/stop/{stream_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["stream_id"] == stream_id
        assert data["status"] == "stopped"
        
        print(f"✅ Stream stopped: {stream_id}")
    
    def test_stop_nonexistent_stream(self):
        """Test stopping a stream that doesn't exist"""
        response = client.post("/api/realtime-cv/streams/stop/nonexistent_stream_123")
        assert response.status_code == 404
        print("✅ Non-existent stream returns 404")


class TestFrameAnalysis:
    """Test single frame analysis"""
    
    def test_analyze_frame(self):
        """Test analyzing a single video frame"""
        frame_data = {
            "bout_id": "test_bout_002",
            "camera_id": "main_camera",
            "timestamp_ms": 1000,
            "frame_number": 30,
            "width": 1920,
            "height": 1080
        }
        
        response = client.post("/api/realtime-cv/frames/analyze", json=frame_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "frame_id" in data
        assert data["bout_id"] == "test_bout_002"
        assert data["timestamp_ms"] == 1000
        assert "detections" in data
        assert "detection_count" in data
        assert "processing_time_ms" in data
        
        # Verify detection structure
        if data["detection_count"] > 0:
            detection = data["detections"][0]
            assert "id" in detection
            assert "action_type" in detection
            assert "fighter_id" in detection
            assert "confidence" in detection
            assert "detected_at" in detection
        
        print(f"✅ Frame analyzed: {data['detection_count']} detections, {data['processing_time_ms']}ms")
    
    def test_simulate_frame_analysis(self):
        """Test simulated frame analysis"""
        response = client.post(
            "/api/realtime-cv/simulate/frame",
            params={
                "bout_id": "test_bout_003",
                "camera_id": "main",
                "frame_count": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["bout_id"] == "test_bout_003"
        assert data["frames_analyzed"] == 5
        assert "total_detections" in data
        assert "detections" in data
        
        print(f"✅ Simulated {data['frames_analyzed']} frames: {data['total_detections']} total detections")


class TestDetectionRetrieval:
    """Test detection retrieval"""
    
    def test_get_bout_detections(self):
        """Test retrieving detections for a bout"""
        # First, simulate some frames to generate detections
        client.post(
            "/api/realtime-cv/simulate/frame",
            params={"bout_id": "test_bout_004", "frame_count": 10}
        )
        
        # Get detections
        response = client.get("/api/realtime-cv/detections/test_bout_004")
        assert response.status_code == 200
        data = response.json()
        
        assert data["bout_id"] == "test_bout_004"
        assert "detections" in data
        assert "count" in data
        
        print(f"✅ Retrieved {data['count']} detections for bout")
    
    def test_get_detections_with_filter(self):
        """Test retrieving detections with filters"""
        # Generate detections
        client.post(
            "/api/realtime-cv/simulate/frame",
            params={"bout_id": "test_bout_005", "frame_count": 10}
        )
        
        # Get detections with limit
        response = client.get(
            "/api/realtime-cv/detections/test_bout_005",
            params={"limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["count"] <= 5
        print(f"✅ Filtered detections: {data['count']} (limit: 5)")
    
    def test_get_detection_stats(self):
        """Test getting detection statistics"""
        # Generate detections
        client.post(
            "/api/realtime-cv/simulate/frame",
            params={"bout_id": "test_bout_006", "frame_count": 20}
        )
        
        # Get stats
        response = client.get("/api/realtime-cv/stats/test_bout_006")
        assert response.status_code == 200
        data = response.json()
        
        assert data["bout_id"] == "test_bout_006"
        assert "total_detections" in data
        assert "actions" in data
        assert "avg_confidence" in data
        
        print(f"✅ Detection stats: {data['total_detections']} total, avg confidence: {data['avg_confidence']:.2f}")
        if data["actions"]:
            print(f"   Action breakdown: {data['actions']}")


class TestDataCollection:
    """Test training data collection"""
    
    def test_list_datasets(self):
        """Test listing available datasets"""
        response = client.get("/api/cv-data/datasets")
        assert response.status_code == 200
        data = response.json()
        
        assert "datasets" in data
        assert "count" in data
        assert data["count"] > 0  # Should have predefined datasets
        
        # Verify dataset structure
        dataset = data["datasets"][0]
        assert "source_id" in dataset
        assert "source_type" in dataset
        assert "name" in dataset
        assert "description" in dataset
        assert "categories" in dataset
        assert "is_downloaded" in dataset
        assert "is_processed" in dataset
        
        print(f"✅ Found {data['count']} available datasets")
        for ds in data["datasets"][:3]:
            print(f"   - {ds['name']} ({ds['source_type']})")
    
    def test_get_dataset_info(self):
        """Test getting detailed dataset information"""
        # First get list of datasets
        list_response = client.get("/api/cv-data/datasets")
        datasets = list_response.json()["datasets"]
        
        if datasets:
            source_id = datasets[0]["source_id"]
            
            response = client.get(f"/api/cv-data/datasets/{source_id}")
            assert response.status_code == 200
            data = response.json()
            
            assert data["source_id"] == source_id
            assert "name" in data
            assert "description" in data
            assert "url" in data or "local_path" in data
            assert "categories" in data
            
            print(f"✅ Dataset info retrieved: {data['name']}")
    
    def test_get_nonexistent_dataset(self):
        """Test getting info for non-existent dataset"""
        response = client.get("/api/cv-data/datasets/nonexistent_dataset_xyz")
        assert response.status_code == 404
        print("✅ Non-existent dataset returns 404")
    
    def test_download_dataset(self):
        """Test downloading a dataset"""
        # Get first dataset
        list_response = client.get("/api/cv-data/datasets")
        datasets = list_response.json()["datasets"]
        
        if datasets:
            source_id = datasets[0]["source_id"]
            
            response = client.post(f"/api/cv-data/datasets/{source_id}/download")
            assert response.status_code == 200
            data = response.json()
            
            assert data["source_id"] == source_id
            assert data["success"] is True
            
            print(f"✅ Dataset downloaded: {source_id}")
    
    def test_process_dataset(self):
        """Test processing a downloaded dataset"""
        # Get first dataset and download it
        list_response = client.get("/api/cv-data/datasets")
        datasets = list_response.json()["datasets"]
        
        if datasets:
            source_id = datasets[0]["source_id"]
            
            # Download first
            client.post(f"/api/cv-data/datasets/{source_id}/download")
            
            # Then process
            response = client.post(f"/api/cv-data/datasets/{source_id}/process")
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "stats" in data
            
            stats = data["stats"]
            assert "total_samples" in stats
            assert "train_samples" in stats
            assert "val_samples" in stats
            assert "test_samples" in stats
            assert "categories" in stats
            
            print(f"✅ Dataset processed: {stats['total_samples']} samples")
            print(f"   Train: {stats['train_samples']}, Val: {stats['val_samples']}, Test: {stats['test_samples']}")
    
    def test_get_collection_stats(self):
        """Test getting overall collection statistics"""
        response = client.get("/api/cv-data/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_datasets" in data
        assert "downloaded" in data
        assert "processed" in data
        assert "pending" in data
        assert "total_files" in data
        assert "total_size_mb" in data
        assert "categories" in data
        assert "storage_dir" in data
        
        print(f"✅ Collection stats:")
        print(f"   Total datasets: {data['total_datasets']}")
        print(f"   Downloaded: {data['downloaded']}, Processed: {data['processed']}, Pending: {data['pending']}")
        print(f"   Total size: {data['total_size_mb']}MB")
        print(f"   Categories: {', '.join(data['categories'][:5])}")


class TestIntegration:
    """Integration tests"""
    
    def test_complete_cv_workflow(self):
        """Test complete workflow: start stream -> analyze frames -> get detections"""
        bout_id = "integration_test_001"
        
        # 1. Start stream
        stream_config = {
            "bout_id": bout_id,
            "camera_id": "main",
            "stream_url": "rtsp://test.com/stream",
            "stream_type": "rtsp",
            "fps_target": 30,
            "analysis_fps": 10,
            "enable_pose_estimation": True,
            "enable_action_detection": True
        }
        
        start_response = client.post("/api/realtime-cv/streams/start", json=stream_config)
        assert start_response.status_code == 200
        stream_id = start_response.json()["stream_id"]
        
        # 2. Simulate frames
        simulate_response = client.post(
            "/api/realtime-cv/simulate/frame",
            params={"bout_id": bout_id, "frame_count": 10}
        )
        assert simulate_response.status_code == 200
        
        # 3. Get detections
        detections_response = client.get(f"/api/realtime-cv/detections/{bout_id}")
        assert detections_response.status_code == 200
        detections = detections_response.json()
        
        # 4. Get stats
        stats_response = client.get(f"/api/realtime-cv/stats/{bout_id}")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # 5. Stop stream
        stop_response = client.post(f"/api/realtime-cv/streams/stop/{stream_id}")
        assert stop_response.status_code == 200
        
        print("✅ Complete CV workflow test passed")
        print(f"   Stream: {stream_id}")
        print(f"   Detections: {detections['count']}")
        print(f"   Stats: {stats['total_detections']} total detections")
    
    def test_complete_data_collection_workflow(self):
        """Test complete data collection workflow"""
        # 1. List datasets
        list_response = client.get("/api/cv-data/datasets")
        assert list_response.status_code == 200
        datasets = list_response.json()["datasets"]
        
        if datasets:
            source_id = datasets[1]["source_id"] if len(datasets) > 1 else datasets[0]["source_id"]
            
            # 2. Get dataset info
            info_response = client.get(f"/api/cv-data/datasets/{source_id}")
            assert info_response.status_code == 200
            
            # 3. Download
            download_response = client.post(f"/api/cv-data/datasets/{source_id}/download")
            assert download_response.status_code == 200
            
            # 4. Process
            process_response = client.post(f"/api/cv-data/datasets/{source_id}/process")
            assert process_response.status_code == 200
            
            # 5. Get stats
            stats_response = client.get("/api/cv-data/stats")
            assert stats_response.status_code == 200
            
            print("✅ Complete data collection workflow test passed")
            print(f"   Dataset: {source_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
