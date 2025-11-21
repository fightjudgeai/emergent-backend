"""
Calibration API - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class CalibrationConfig(BaseModel):
    """System calibration configuration"""
    
    # Detection thresholds
    kd_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="KD detection threshold")
    rocked_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Rocked detection threshold")
    highimpact_strike_threshold: float = Field(default=0.70, ge=0.0, le=1.0, description="High-impact strike threshold")
    
    # Timing windows (milliseconds)
    momentum_swing_window_ms: int = Field(default=1200, ge=500, le=3000, description="Momentum swing detection window")
    multicam_merge_window_ms: int = Field(default=150, ge=50, le=500, description="Multi-camera merge timing")
    
    # Event pipeline
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum event confidence")
    deduplication_window_ms: int = Field(default=100, ge=50, le=500, description="Event deduplication window")
    
    # Metadata
    version: str = "1.0.0"
    last_modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_by: str = "system"


class CalibrationHistory(BaseModel):
    """Calibration change history"""
    timestamp: datetime
    parameter: str
    old_value: float
    new_value: float
    modified_by: str
