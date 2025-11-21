"""
Calibration API - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from .calibration_manager import CalibrationManager
from .models import CalibrationConfig, CalibrationHistory

logger = logging.getLogger(__name__)

calibration_api = APIRouter(tags=["Calibration API"])
calibration_manager: Optional[CalibrationManager] = None

def get_calibration_manager():
    if calibration_manager is None:
        raise HTTPException(status_code=500, detail="Calibration API not initialized")
    return calibration_manager

@calibration_api.get("/get", response_model=CalibrationConfig)
async def get_calibration():
    """
    Get current calibration configuration
    
    Returns:
        Current CalibrationConfig
    """
    manager = get_calibration_manager()
    return manager.get_config()

@calibration_api.post("/set", response_model=CalibrationConfig)
async def set_calibration(
    config: CalibrationConfig,
    modified_by: str = "operator"
):
    """
    Update calibration configuration
    
    Args:
        config: New calibration parameters
        modified_by: User making the change
    
    Returns:
        Updated CalibrationConfig
    """
    manager = get_calibration_manager()
    return await manager.set_config(config, modified_by)

@calibration_api.post("/reset", response_model=CalibrationConfig)
async def reset_calibration():
    """
    Reset calibration to defaults
    
    Returns:
        Default CalibrationConfig
    """
    manager = get_calibration_manager()
    return await manager.reset_config()

@calibration_api.get("/history", response_model=List[CalibrationHistory])
async def get_calibration_history(limit: int = 50):
    """
    Get calibration change history
    
    Args:
        limit: Number of recent changes to return
    
    Returns:
        List of CalibrationHistory
    """
    manager = get_calibration_manager()
    return manager.get_history(limit)

@calibration_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Calibration API", "version": "1.0.0"}
