"""
Replay Service - Data Models
"""

from pydantic import BaseModel
from typing import List, Dict


class CameraAngle(BaseModel):
    camera_id: str
    angle_name: str
    url: str
    quality: str = "1080p"


class ReplayClip(BaseModel):
    """Multi-angle replay clip"""
    bout_id: str
    round_id: str
    timestamp_ms: int
    
    # Clip window (5s before, 10s after)
    start_time_ms: int
    end_time_ms: int
    duration_sec: float = 15.0
    
    # Camera angles
    camera_angles: List[CameraAngle]
    
    # Metadata
    event_description: str = ""
    fighter_id: str = ""
