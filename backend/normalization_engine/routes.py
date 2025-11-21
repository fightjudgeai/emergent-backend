"""
Normalization Engine - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from datetime import datetime, timezone
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent
from .normalization_engine import NormalizationEngine
from .models import NormalizedEvent

logger = logging.getLogger(__name__)

normalization_api = APIRouter(tags=["Normalization Engine"])

# Global engine
norm_engine: Optional[NormalizationEngine] = None

def get_norm_engine():
    if norm_engine is None:
        raise HTTPException(status_code=500, detail="Normalization Engine not initialized")
    return norm_engine

@normalization_api.post("/normalize", response_model=NormalizedEvent)
async def normalize_event(event: CombatEvent):
    """Normalize single event"""
    engine = get_norm_engine()
    return engine.normalize_event(event)

@normalization_api.post("/normalize/batch", response_model=List[NormalizedEvent])
async def normalize_batch(events: List[CombatEvent]):
    """Normalize batch of events"""
    engine = get_norm_engine()
    return [engine.normalize_event(e) for e in events]

@normalization_api.get("/weights")
async def get_cumulative_weights():
    """Get cumulative weights"""
    engine = get_norm_engine()
    return engine.get_cumulative_weights()

@normalization_api.post("/weights/reset")
async def reset_weights():
    """Reset cumulative weights"""
    engine = get_norm_engine()
    engine.reset_cumulative_weights()
    return {"success": True}

@normalization_api.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Normalization Engine",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
