"""
CV Router - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone
from enum import Enum
import uuid


class WorkerStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class StreamType(str, Enum):
    RTMP = "rtmp"
    SRT = "srt"
    WEBSOCKET = "websocket"
    MOCK = "mock"


class CVWorker(BaseModel):
    """CV Worker registration"""
    worker_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    endpoint: str
    status: WorkerStatus = WorkerStatus.HEALTHY
    
    # Performance metrics
    avg_latency_ms: float = 0.0
    queue_size: int = 0
    frames_processed: int = 0
    errors: int = 0
    
    # Health tracking
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CameraStream(BaseModel):
    """Camera stream configuration"""
    camera_id: str
    stream_type: StreamType
    stream_url: str
    
    # Stream health
    fps: float = 0.0
    latency_ms: float = 0.0
    dropped_frames: int = 0
    total_frames: int = 0
    
    # Status
    active: bool = True
    last_frame_time: Optional[datetime] = None


class Frame(BaseModel):
    """Video frame for processing"""
    frame_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    camera_id: str
    timestamp_ms: int
    
    # Frame data (base64 encoded or path)
    data: str
    width: int
    height: int
    format: str = "jpeg"
    
    # Metadata
    sequence_num: int
    camera_angle: float
    

class RoutingDecision(BaseModel):
    """Frame routing decision"""
    frame_id: str
    worker_id: str
    route_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Decision factors
    worker_load_score: float
    worker_latency: float
    worker_queue_size: int


class RouterMetrics(BaseModel):
    """System-wide metrics"""
    total_workers: int
    healthy_workers: int
    total_streams: int
    active_streams: int
    
    # Performance
    total_frames_routed: int
    avg_routing_latency_ms: float
    frames_dropped: int
    
    # Per-camera stats
    camera_stats: Dict[str, Dict] = Field(default_factory=dict)
