"""
CV Router - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
import logging
from datetime import datetime, timezone

from .models import CVWorker, CameraStream, Frame, StreamType, RouterMetrics
from .router_engine import CVRouterEngine

logger = logging.getLogger(__name__)

# Create router
cv_router_api = APIRouter(tags=["CV Router"])

# Global router engine
router_engine: Optional[CVRouterEngine] = None


def get_router_engine():
    """Get router engine instance"""
    if router_engine is None:
        raise HTTPException(status_code=500, detail="CV Router not initialized")
    return router_engine


# ============================================================================
# WORKER MANAGEMENT
# ============================================================================

@cv_router_api.post("/register_worker", response_model=CVWorker)
async def register_worker(endpoint: str):
    """
    Register new CV worker
    
    Args:
        endpoint: Worker HTTP/WebSocket endpoint
    
    Returns:
        CVWorker registration details
    """
    engine = get_router_engine()
    worker = await engine.worker_manager.register_worker(endpoint)
    return worker


@cv_router_api.delete("/worker/{worker_id}")
async def deregister_worker(worker_id: str):
    """
    Deregister CV worker
    
    Args:
        worker_id: Worker identifier
    """
    engine = get_router_engine()
    success = await engine.worker_manager.deregister_worker(worker_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    return {"success": True, "worker_id": worker_id}


@cv_router_api.post("/worker/{worker_id}/heartbeat")
async def worker_heartbeat(
    worker_id: str,
    latency_ms: float,
    queue_size: int
):
    """
    Worker heartbeat with performance metrics
    
    Args:
        worker_id: Worker identifier
        latency_ms: Average processing latency
        queue_size: Current queue size
    """
    engine = get_router_engine()
    await engine.worker_manager.update_worker_metrics(
        worker_id, latency_ms, queue_size
    )
    return {"success": True}


@cv_router_api.post("/worker/{worker_id}/error")
async def report_worker_error(worker_id: str):
    """
    Report worker error
    
    Args:
        worker_id: Worker identifier
    """
    engine = get_router_engine()
    await engine.worker_manager.report_worker_error(worker_id)
    return {"success": True}


# ============================================================================
# STREAM MANAGEMENT
# ============================================================================

@cv_router_api.post("/stream/add", response_model=CameraStream)
async def add_stream(
    camera_id: str,
    stream_type: StreamType,
    stream_url: str
):
    """
    Add camera stream
    
    Args:
        camera_id: Camera identifier
        stream_type: RTMP/SRT/WebSocket/Mock
        stream_url: Stream URL
    """
    engine = get_router_engine()
    stream = await engine.stream_ingestor.add_stream(
        camera_id, stream_type, stream_url
    )
    return stream


@cv_router_api.delete("/stream/{camera_id}")
async def remove_stream(camera_id: str):
    """
    Remove camera stream
    
    Args:
        camera_id: Camera identifier
    """
    engine = get_router_engine()
    success = await engine.stream_ingestor.remove_stream(camera_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    return {"success": True, "camera_id": camera_id}


# ============================================================================
# FRAME ROUTING
# ============================================================================

@cv_router_api.post("/ingest_frame")
async def ingest_frame(frame: Frame):
    """
    Manually ingest single frame
    
    Args:
        frame: Video frame data
    """
    engine = get_router_engine()
    await engine._on_frame_received(frame)
    return {"success": True, "frame_id": frame.frame_id}


@cv_router_api.post("/route_frame")
async def route_frame(frame_id: str):
    """
    Force routing of specific frame
    
    Args:
        frame_id: Frame identifier
    """
    engine = get_router_engine()
    worker = engine.worker_manager.select_worker(frame_id)
    
    if not worker:
        raise HTTPException(status_code=503, detail="No workers available")
    
    return {
        "success": True,
        "frame_id": frame_id,
        "worker_id": worker.worker_id,
        "worker_endpoint": worker.endpoint
    }


# ============================================================================
# METRICS & HEALTH
# ============================================================================

@cv_router_api.get("/metrics", response_model=RouterMetrics)
async def get_metrics():
    """
    Get comprehensive router metrics
    
    Returns:
        System-wide performance metrics
    """
    engine = get_router_engine()
    return engine.get_metrics()


@cv_router_api.get("/health")
async def health_check():
    """Health check endpoint"""
    engine = get_router_engine()
    metrics = engine.get_metrics()
    
    # Determine health status
    if metrics.healthy_workers == 0:
        status = "unhealthy"
    elif metrics.healthy_workers < metrics.total_workers * 0.5:
        status = "degraded"
    else:
        status = "healthy"
    
    return {
        "status": status,
        "service": "CV Router",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "healthy_workers": metrics.healthy_workers,
        "total_workers": metrics.total_workers,
        "active_streams": metrics.active_streams
    }


# ============================================================================
# WEBSOCKET
# ============================================================================

@cv_router_api.websocket("/ws/frames")
async def websocket_frame_feed(websocket: WebSocket):
    """
    WebSocket feed for routed frames
    """
    await websocket.accept()
    
    # In production: stream frames to E2
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming data
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
