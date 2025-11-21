"""
Replay Service - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .replay_engine import ReplayEngine
from .models import ReplayClip

logger = logging.getLogger(__name__)

replay_service_api = APIRouter(tags=["Replay Service"])
replay_engine: Optional[ReplayEngine] = None

def get_replay_engine():
    if replay_engine is None:
        raise HTTPException(status_code=500, detail="Replay Service not initialized")
    return replay_engine

@replay_service_api.get("/replay", response_model=ReplayClip)
async def get_replay(
    bout_id: str,
    round_id: str,
    timestamp_ms: int
):
    """Get multi-angle replay clip"""
    engine = get_replay_engine()
    return engine.generate_replay(bout_id, round_id, timestamp_ms)

@replay_service_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Replay Service", "version": "1.0.0"}
