"""
Highlight Worker - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import sys
sys.path.append('/app/backend')
from fjai.models import EventType


class ClipStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoClip(BaseModel):
    """Video clip metadata"""
    clip_id: str
    bout_id: str
    round_id: str
    
    # Event info
    event_type: EventType
    fighter_id: str
    timestamp_ms: int
    
    # Clip details
    start_time_ms: int  # 5s before event
    end_time_ms: int  # 10s after event
    duration_sec: float
    
    # Camera angles
    camera_angles: List[str] = Field(default_factory=list)
    
    # Storage
    storage_url: Optional[str] = None
    bucket: str = "fight-highlights"
    
    # Status
    status: ClipStatus = ClipStatus.PENDING
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
