"""
Storage Manager - Data Models
"""

from pydantic import BaseModel, Field
from typing import Dict, List
from datetime import datetime


class StorageStats(BaseModel):
    """Storage statistics"""
    total_space_gb: float
    used_space_gb: float
    free_space_gb: float
    used_percentage: float
    
    # Alert status
    alert_level: str = "normal"  # normal/warning/critical
    
    # Breakdown
    recordings_gb: float = 0.0
    highlights_gb: float = 0.0
    replays_gb: float = 0.0
    archives_gb: float = 0.0


class CleanupResult(BaseModel):
    """Cleanup operation result"""
    files_deleted: int
    space_freed_gb: float
    errors: List[str] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=datetime.now)


class ArchiveResult(BaseModel):
    """Archive operation result"""
    bout_id: str
    archive_url: str
    archive_size_gb: float
    completed_at: datetime = Field(default_factory=datetime.now)
