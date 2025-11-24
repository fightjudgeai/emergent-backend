"""
Real-Time CV - API Routes

Endpoints for professional-grade combat sports computer vision:
- Stream management (start/stop video analysis)
- Frame processing (analyze single frames)
- Detection retrieval (get detected actions)
- Model management (list/switch CV models)
- Statistics (bout-level analytics)
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
import base64
from datetime import datetime, timezone

from .models import *
from .cv_engine import RealtimeCVEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/realtime-cv", tags=["Realtime CV"])

# Global engine instance (initialized in server.py startup)
cv_engine: Optional[RealtimeCVEngine] = None


def init_cv_engine(db):
    """Initialize CV engine with database connection"""
    global cv_engine
    cv_engine = RealtimeCVEngine(db=db)
    logger.info("✅ Real-Time CV Engine initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Real-Time CV",
        "version": "1.0.0",
        "status": "operational",
        "models_loaded": len(cv_engine.loaded_models) if cv_engine else 0,
        "active_streams": len(cv_engine.active_streams) if cv_engine else 0
    }


@router.post("/streams/start")
async def start_stream_analysis(config: StreamConfig):
    """
    Start analyzing a video stream
    
    Body:
    - stream_url: Video stream URL (RTSP/RTMP/HTTP/webcam)
    - bout_id: Bout identifier
    - camera_id: Camera identifier (main, corner_red, corner_blue, overhead)
    - fps_target: Target FPS for processing
    - analysis_fps: Frames per second to analyze
    - enable_pose_estimation: Enable pose detection
    - enable_action_detection: Enable action detection
    
    Returns:
    - stream_id: Unique stream identifier
    - status: Stream status
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    try:
        success = await cv_engine.start_stream_analysis(config)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start stream analysis")
        
        return {
            "stream_id": config.stream_id,
            "bout_id": config.bout_id,
            "camera_id": config.camera_id,
            "status": "active",
            "message": "Stream analysis started successfully",
            "config": {
                "fps_target": config.fps_target,
                "analysis_fps": config.analysis_fps,
                "pose_estimation": config.enable_pose_estimation,
                "action_detection": config.enable_action_detection
            }
        }
    
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/streams/stop/{stream_id}")
async def stop_stream_analysis(stream_id: str):
    """
    Stop analyzing a video stream
    
    Path:
    - stream_id: Stream identifier to stop
    
    Returns:
    - success: Boolean indicating success
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    try:
        success = await cv_engine.stop_stream_analysis(stream_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        return {
            "stream_id": stream_id,
            "status": "stopped",
            "message": "Stream analysis stopped successfully"
        }
    
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streams/active")
async def get_active_streams():
    """
    Get list of all active video streams
    
    Returns:
    - active_streams: List of currently active streams
    - count: Number of active streams
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    streams = [
        {
            "stream_id": stream.stream_id,
            "bout_id": stream.bout_id,
            "camera_id": stream.camera_id,
            "stream_url": stream.stream_url,
            "is_active": stream.is_active,
            "fps_target": stream.fps_target,
            "analysis_fps": stream.analysis_fps
        }
        for stream in cv_engine.active_streams.values()
    ]
    
    return {
        "active_streams": streams,
        "count": len(streams)
    }


@router.post("/frames/analyze")
async def analyze_single_frame(frame: VideoFrame):
    """
    Analyze a single video frame
    
    Body:
    - frame_id: Frame identifier (auto-generated if not provided)
    - bout_id: Bout identifier
    - camera_id: Camera identifier
    - timestamp_ms: Timestamp in milliseconds
    - frame_number: Frame sequence number
    - frame_data: Base64 encoded frame data (optional)
    - frame_url: URL to frame image (optional)
    
    Returns:
    - detections: List of detected actions
    - poses: Detected poses (keypoints)
    - processing_time_ms: Analysis duration
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    try:
        start_time = datetime.now(timezone.utc)
        
        # Analyze frame
        detections = await cv_engine.analyze_frame(frame)
        
        end_time = datetime.now(timezone.utc)
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        return {
            "frame_id": frame.frame_id,
            "bout_id": frame.bout_id,
            "timestamp_ms": frame.timestamp_ms,
            "detections": [
                {
                    "id": det.id,
                    "action_type": det.action_type,
                    "fighter_id": det.fighter_id,
                    "confidence": det.confidence,
                    "velocity_estimate": det.velocity_estimate,
                    "power_estimate": det.power_estimate,
                    "detected_at": det.detected_at.isoformat()
                }
                for det in detections
            ],
            "detection_count": len(detections),
            "processing_time_ms": round(processing_time, 2)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frames/analyze/upload")
async def analyze_frame_upload(
    bout_id: str = Form(...),
    camera_id: str = Form(...),
    timestamp_ms: int = Form(...),
    frame_number: int = Form(...),
    frame_file: UploadFile = File(...)
):
    """
    Analyze a frame uploaded as multipart file
    
    Form Data:
    - bout_id: Bout identifier
    - camera_id: Camera identifier
    - timestamp_ms: Timestamp in milliseconds
    - frame_number: Frame sequence number
    - frame_file: Image file (JPEG, PNG)
    
    Returns:
    - detections: List of detected actions
    - processing_time_ms: Analysis duration
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    try:
        # Read file
        file_bytes = await frame_file.read()
        
        # Encode to base64
        frame_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Create VideoFrame object
        frame = VideoFrame(
            bout_id=bout_id,
            camera_id=camera_id,
            timestamp_ms=timestamp_ms,
            frame_number=frame_number,
            frame_data=frame_data
        )
        
        start_time = datetime.now(timezone.utc)
        
        # Analyze
        detections = await cv_engine.analyze_frame(frame)
        
        end_time = datetime.now(timezone.utc)
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        return {
            "frame_id": frame.frame_id,
            "detections": [
                {
                    "action_type": det.action_type,
                    "fighter_id": det.fighter_id,
                    "confidence": det.confidence,
                    "power_estimate": det.power_estimate
                }
                for det in detections
            ],
            "detection_count": len(detections),
            "processing_time_ms": round(processing_time, 2)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing uploaded frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detections/{bout_id}")
async def get_bout_detections(
    bout_id: str,
    limit: int = 100,
    action_type: Optional[str] = None,
    fighter_id: Optional[str] = None
):
    """
    Get recent detections for a bout
    
    Path:
    - bout_id: Bout identifier
    
    Query:
    - limit: Maximum number of detections to return (default 100)
    - action_type: Filter by action type
    - fighter_id: Filter by fighter
    
    Returns:
    - detections: List of detected actions
    - count: Number of detections
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    try:
        # Get recent detections from cache
        if bout_id not in cv_engine.recent_detections:
            return {
                "bout_id": bout_id,
                "detections": [],
                "count": 0
            }
        
        detections = cv_engine.recent_detections[bout_id]
        
        # Apply filters
        if action_type:
            detections = [d for d in detections if d.action_type == action_type]
        
        if fighter_id:
            detections = [d for d in detections if d.fighter_id == fighter_id]
        
        # Apply limit
        detections = detections[-limit:]
        
        return {
            "bout_id": bout_id,
            "detections": [
                {
                    "id": det.id,
                    "timestamp_ms": det.timestamp_ms,
                    "action_type": det.action_type,
                    "fighter_id": det.fighter_id,
                    "confidence": det.confidence,
                    "velocity_estimate": det.velocity_estimate,
                    "power_estimate": det.power_estimate,
                    "detected_at": det.detected_at.isoformat()
                }
                for det in detections
            ],
            "count": len(detections)
        }
    
    except Exception as e:
        logger.error(f"Error getting detections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{bout_id}")
async def get_detection_stats(bout_id: str):
    """
    Get detection statistics for a bout
    
    Path:
    - bout_id: Bout identifier
    
    Returns:
    - total_detections: Total number of detected actions
    - actions: Breakdown by action type
    - avg_confidence: Average detection confidence
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    try:
        stats = cv_engine.get_detection_stats(bout_id)
        return stats
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_loaded_models():
    """
    Get information about loaded CV models
    
    Returns:
    - models: List of loaded models with details
    - count: Number of loaded models
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    models = [
        {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "framework": model.framework,
            "version": model.version,
            "inference_time_ms": model.inference_time_ms,
            "accuracy": model.accuracy,
            "is_loaded": model.is_loaded
        }
        for model in cv_engine.loaded_models.values()
    ]
    
    return {
        "models": models,
        "count": len(models),
        "total_loaded": sum(1 for m in models if m["is_loaded"])
    }


@router.post("/simulate/frame")
async def simulate_frame_analysis(
    bout_id: str,
    camera_id: str = "main",
    frame_count: int = 1
):
    """
    Simulate frame analysis for testing
    
    Query:
    - bout_id: Bout identifier
    - camera_id: Camera identifier
    - frame_count: Number of frames to simulate
    
    Returns:
    - frames_analyzed: Number of frames processed
    - total_detections: Total actions detected
    - detections: List of all detected actions
    """
    
    if not cv_engine:
        raise HTTPException(status_code=500, detail="CV engine not initialized")
    
    try:
        all_detections = []
        
        for i in range(frame_count):
            # Create simulated frame
            frame = VideoFrame(
                bout_id=bout_id,
                camera_id=camera_id,
                timestamp_ms=i * 100,  # 100ms intervals
                frame_number=i
            )
            
            # Analyze
            detections = await cv_engine.analyze_frame(frame)
            all_detections.extend(detections)
        
        return {
            "bout_id": bout_id,
            "frames_analyzed": frame_count,
            "total_detections": len(all_detections),
            "detections": [
                {
                    "action_type": det.action_type,
                    "fighter_id": det.fighter_id,
                    "confidence": det.confidence,
                    "power_estimate": det.power_estimate
                }
                for det in all_detections
            ]
        }
    
    except Exception as e:
        logger.error(f"Error simulating frames: {e}")
        raise HTTPException(status_code=500, detail=str(e))
