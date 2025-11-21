"""
Event Harmonizer - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional, List
import logging
from datetime import datetime, timezone
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent
from .harmonizer_engine import EventHarmonizerEngine
from .models import HarmonizerStats

logger = logging.getLogger(__name__)

# Create router
event_harmonizer_api = APIRouter(tags=["Event Harmonizer"])

# Global engine
harmonizer_engine: Optional[EventHarmonizerEngine] = None

def get_harmonizer_engine():
    if harmonizer_engine is None:
        raise HTTPException(status_code=500, detail="Event Harmonizer not initialized")
    return harmonizer_engine

# POST /events/harmonize - Unified endpoint for harmonizing events
@event_harmonizer_api.post("/events/harmonize")
async def harmonize_events(
    judge_events: List[CombatEvent] = [],
    cv_events: List[CombatEvent] = []
):
    """
    Unified endpoint for harmonizing judge and CV events
    
    Args:
        judge_events: List of judge events
        cv_events: List of CV events
    
    Returns:
        Harmonized event list
    """
    engine = get_harmonizer_engine()
    
    # Process all events
    for event in judge_events:
        await engine.process_judge_event(event)
    
    for event in cv_events:
        await engine.process_cv_event(event)
    
    # Get harmonized results
    harmonized = engine.get_harmonized_events(limit=1000)
    
    return {
        "success": True,
        "judge_events_count": len(judge_events),
        "cv_events_count": len(cv_events),
        "harmonized_events_count": len(harmonized),
        "harmonized_events": harmonized
    }

# POST /cv/events - Receive CV events (backward compatibility)
@event_harmonizer_api.post("/cv/events")
async def receive_cv_event(event: CombatEvent):
    engine = get_harmonizer_engine()
    await engine.process_cv_event(event)
    return {"success": True, "event_id": event.event_id}

# POST /judge/events - Receive judge events (backward compatibility)
@event_harmonizer_api.post("/judge/events")
async def receive_judge_event(event: CombatEvent):
    engine = get_harmonizer_engine()
    await engine.process_judge_event(event)
    return {"success": True, "event_id": event.event_id}

# GET /harmonized/events - Get harmonized events
@event_harmonizer_api.get("/harmonized/events")
async def get_harmonized_events(limit: int = 100):
    engine = get_harmonizer_engine()
    return engine.harmonized_events[-limit:]

# GET /stats
@event_harmonizer_api.get("/stats", response_model=HarmonizerStats)
async def get_stats():
    engine = get_harmonizer_engine()
    return engine.get_stats()

# GET /health
@event_harmonizer_api.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Event Harmonizer",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# WebSocket /ws/harmonized
@event_harmonizer_api.websocket("/ws/harmonized")
async def websocket_harmonized_feed(websocket: WebSocket):
    await websocket.accept()
    # Stream harmonized events in production
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
