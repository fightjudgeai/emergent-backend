"""
Failover Engine - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class CVEngineMode(str, Enum):
    CLOUD = "cloud"
    LOCAL = "local"
    MANUAL = "manual"  # Fallback to judge-only


class EngineHealth(BaseModel):
    """Health status of CV engine"""
    mode: CVEngineMode
    healthy: bool
    last_heartbeat: datetime
    response_time_ms: float
    error_rate: float


class FailoverStatus(BaseModel):
    """Current failover status"""
    current_mode: CVEngineMode
    
    # Engine health
    cloud_health: EngineHealth
    local_health: EngineHealth
    
    # Failover history
    last_failover: Optional[datetime] = None
    failover_count: int = 0
    
    # Alerts
    alerts: list = Field(default_factory=list)


class FailoverEvent(BaseModel):
    """Failover event record"""
    from_mode: CVEngineMode
    to_mode: CVEngineMode
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
