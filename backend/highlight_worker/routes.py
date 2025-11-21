"""
Highlight Worker - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
import sys
sys.path.append('/app/backend')
from fjai.models import EventType
from .worker_engine import HighlightWorkerEngine
from .models import VideoClip

logger = logging.getLogger(__name__)

highlight_worker_api = APIRouter(tags=["Highlight Worker"])
highlight_engine: Optional[HighlightWorkerEngine] = None

def get_highlight_engine():
    if highlight_engine is None:
        raise HTTPException(status_code=500, detail="Highlight Worker not initialized")
    return highlight_engine

@highlight_worker_api.get("/clips/{bout_id}", response_model=List[VideoClip])
async def get_clips(bout_id: str):
    """Get all clips for bout"""
    engine = get_highlight_engine()
    return engine.get_clips(bout_id)

@highlight_worker_api.post("/clips/generate", response_model=VideoClip)
async def generate_clip(
    bout_id: str,
    round_id: str,
    timestamp_ms: int,
    event_type: EventType
):
    """Manually generate clip"""
    engine = get_highlight_engine()
    return await engine.generate_manual_clip(bout_id, round_id, timestamp_ms, event_type)

@highlight_worker_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Highlight Worker", "version": "1.0.0"}
