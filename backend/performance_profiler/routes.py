"""
Performance Profiler - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
import logging
import asyncio
from .profiler_engine import PerformanceProfiler
from .models import PerformanceSummary, LiveMetric

logger = logging.getLogger(__name__)

performance_profiler_api = APIRouter(tags=["Performance Profiler"])
profiler: Optional[PerformanceProfiler] = None

def get_profiler():
    if profiler is None:
        raise HTTPException(status_code=500, detail="Performance Profiler not initialized")
    return profiler

@performance_profiler_api.get("/summary", response_model=PerformanceSummary)
async def get_performance_summary():
    """
    Get performance summary with statistics
    
    Returns:
        PerformanceSummary with avg, p95, p99 for all metrics
    """
    prof = get_profiler()
    return prof.get_summary()

@performance_profiler_api.post("/record/cv_inference")
async def record_cv_inference(duration_ms: float):
    """Record CV inference time"""
    prof = get_profiler()
    prof.record_cv_inference(duration_ms)
    return {"success": True}

@performance_profiler_api.post("/record/event_ingestion")
async def record_event_ingestion(duration_ms: float):
    """Record event ingestion time"""
    prof = get_profiler()
    prof.record_event_ingestion(duration_ms)
    return {"success": True}

@performance_profiler_api.post("/record/scoring")
async def record_scoring(duration_ms: float):
    """Record scoring calculation time"""
    prof = get_profiler()
    prof.record_scoring_calc(duration_ms)
    return {"success": True}

@performance_profiler_api.post("/record/websocket")
async def record_websocket(duration_ms: float):
    """Record WebSocket roundtrip time"""
    prof = get_profiler()
    prof.record_websocket_roundtrip(duration_ms)
    return {"success": True}

@performance_profiler_api.websocket("/live")
async def performance_live_stream(websocket: WebSocket):
    """
    WebSocket endpoint for live performance metrics
    
    Streams real-time performance data to connected clients
    """
    prof = get_profiler()
    
    await websocket.accept()
    prof.live_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
            
            # Send periodic summary
            summary = prof.get_summary()
            await websocket.send_json({
                "type": "summary",
                "data": summary.model_dump()
            })
    
    except WebSocketDisconnect:
        prof.live_connections.remove(websocket)
        logger.info("Performance profiler WebSocket disconnected")

@performance_profiler_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Performance Profiler", "version": "1.0.0"}
