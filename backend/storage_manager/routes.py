"""
Storage Manager - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .manager_engine import StorageManagerEngine
from .models import StorageStats, CleanupResult, ArchiveResult

logger = logging.getLogger(__name__)

storage_manager_api = APIRouter(tags=["Storage Manager"])
storage_engine: Optional[StorageManagerEngine] = None

def get_storage_engine():
    if storage_engine is None:
        raise HTTPException(status_code=500, detail="Storage Manager not initialized")
    return storage_engine

@storage_manager_api.get("/status", response_model=StorageStats)
async def get_storage_status():
    """Get storage status"""
    engine = get_storage_engine()
    return engine.get_status()

@storage_manager_api.post("/cleanup", response_model=CleanupResult)
async def cleanup_storage(days: int = 7):
    """Clean up expired files"""
    engine = get_storage_engine()
    return await engine.cleanup_expired(days)

@storage_manager_api.post("/archive", response_model=ArchiveResult)
async def archive_bout(bout_id: str):
    """Archive full fight bundle"""
    engine = get_storage_engine()
    return await engine.archive_bout(bout_id)

@storage_manager_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Storage Manager", "version": "1.0.0"}
