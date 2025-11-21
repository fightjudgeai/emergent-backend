"""
Failover Engine - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .failover_manager import FailoverManager
from .models import FailoverStatus

logger = logging.getLogger(__name__)

failover_engine_api = APIRouter(tags=["Failover Engine"])
failover_manager: Optional[FailoverManager] = None

def get_failover_manager():
    if failover_manager is None:
        raise HTTPException(status_code=500, detail="Failover Engine not initialized")
    return failover_manager

@failover_engine_api.get("/status", response_model=FailoverStatus)
async def get_failover_status():
    """Get current failover status"""
    manager = get_failover_manager()
    return manager.get_status()

@failover_engine_api.post("/heartbeat/cloud")
async def cloud_heartbeat(response_time_ms: float, error_rate: float = 0.0):
    """Cloud CV engine heartbeat"""
    manager = get_failover_manager()
    await manager.update_cloud_heartbeat(response_time_ms, error_rate)
    return {"success": True}

@failover_engine_api.post("/heartbeat/local")
async def local_heartbeat(response_time_ms: float, error_rate: float = 0.0):
    """Local GPU heartbeat"""
    manager = get_failover_manager()
    await manager.update_local_heartbeat(response_time_ms, error_rate)
    return {"success": True}

@failover_engine_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Failover Engine", "version": "1.0.0"}
