"""
Time Sync Service - Data Models
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional


class TimeSync(BaseModel):
    """Time synchronization response"""
    server_timestamp_ms: int
    server_time_iso: str
    
    # For drift calculation
    request_received_ms: int
    response_sent_ms: int


class ClientSync(BaseModel):
    """Client synchronization record"""
    client_id: str
    device_type: str  # judge_tablet, cv_engine, scoring_engine, overlay
    
    # Sync stats
    last_sync: datetime
    drift_ms: float  # Client drift from server
    jitter_ms: float  # Variability in drift
    
    # Correction
    correction_applied: bool
    corrected_drift_ms: float = 0.0


class TimeSyncStats(BaseModel):
    """Time sync statistics"""
    synced_clients: int
    avg_drift_ms: float
    max_drift_ms: float
    avg_jitter_ms: float
    
    # Per device type
    client_stats: List[ClientSync] = Field(default_factory=list)
