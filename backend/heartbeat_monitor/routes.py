"""Heartbeat Monitor - FastAPI Routes"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from .monitor_engine import HeartbeatMonitor
from .models import HeartbeatData, HeartbeatRecord, HeartbeatSummary

logger = logging.getLogger(__name__)

heartbeat_api = APIRouter(tags=["Heartbeat Monitor"])
monitor: Optional[HeartbeatMonitor] = None

def get_monitor():
    if monitor is None:
        raise HTTPException(status_code=500, detail="Heartbeat Monitor not initialized")
    return monitor

@heartbeat_api.post("/heartbeat", response_model=HeartbeatRecord, status_code=201)
async def receive_heartbeat(heartbeat: HeartbeatData):
    """
    Receive a heartbeat from a service
    
    Args:
        heartbeat: Service heartbeat data
    
    Returns:
        HeartbeatRecord with generated ID
    """
    mon = get_monitor()
    return await mon.record_heartbeat(heartbeat)

@heartbeat_api.get("/heartbeat/summary", response_model=HeartbeatSummary)
async def get_heartbeat_summary():
    """
    Get summary of all service statuses
    
    Returns:
        HeartbeatSummary with service health status
    """
    mon = get_monitor()
    return mon.get_summary()

@heartbeat_api.get("/heartbeat/history/{service_name}", response_model=List[HeartbeatRecord])
async def get_service_history(service_name: str, limit: int = 100):
    """
    Get heartbeat history for a specific service
    
    Args:
        service_name: Name of the service
        limit: Maximum number of records to return
    
    Returns:
        List of HeartbeatRecord
    """
    mon = get_monitor()
    return await mon.get_service_history(service_name, limit)

@heartbeat_api.get("/heartbeat/health")
async def health_check():
    return {"status": "healthy", "service": "Heartbeat Monitor", "version": "1.0.0"}
