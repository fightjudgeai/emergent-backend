"""Heartbeat Monitor - Data Models"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import datetime, timezone
import uuid


class HeartbeatData(BaseModel):
    """Heartbeat data from a service"""
    service_name: Literal[
        "CV Router",
        "CV Analytics",
        "Scoring Engine",
        "Replay Worker",
        "Highlight Worker",
        "Storage Manager",
        "Supervisor Console"
    ]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["ok", "warning", "error"] = "ok"
    metrics: Optional[Dict] = Field(default_factory=dict)


class HeartbeatRecord(BaseModel):
    """Stored heartbeat record with ID"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str
    timestamp: datetime
    status: str
    metrics: Dict
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceStatus(BaseModel):
    """Current status of a service"""
    service_name: str
    status: Literal["ok", "warning", "error", "offline"]
    last_heartbeat: Optional[datetime] = None
    time_since_last_heartbeat_sec: Optional[float] = None
    metrics: Optional[Dict] = None
    is_healthy: bool = True


class HeartbeatSummary(BaseModel):
    """Summary of all service statuses"""
    total_services: int
    healthy_services: int
    warning_services: int
    error_services: int
    offline_services: int
    services: List[ServiceStatus]
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
