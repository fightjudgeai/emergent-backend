"""
Time Sync Service - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .sync_engine import TimeSyncEngine
from .models import TimeSync, ClientSync, TimeSyncStats

logger = logging.getLogger(__name__)

time_sync_api = APIRouter(tags=["Time Sync"])
sync_engine: Optional[TimeSyncEngine] = None

def get_sync_engine():
    if sync_engine is None:
        raise HTTPException(status_code=500, detail="Time Sync not initialized")
    return sync_engine

@time_sync_api.get("/now", response_model=TimeSync)
async def get_current_time():
    """Get unified timestamp"""
    engine = get_sync_engine()
    return engine.get_current_time()

@time_sync_api.post("/sync", response_model=ClientSync)
async def sync_client(
    client_id: str,
    device_type: str,
    client_timestamp_ms: int
):
    """Sync client with server time"""
    engine = get_sync_engine()
    return engine.register_client_sync(client_id, device_type, client_timestamp_ms)

@time_sync_api.get("/stats", response_model=TimeSyncStats)
async def get_sync_stats():
    """Get synchronization statistics"""
    engine = get_sync_engine()
    return engine.get_stats()

@time_sync_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Time Sync", "version": "1.0.0"}
