"""
ICVSS Data Models - Standardized Event Schema
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid


class EventType(str, Enum):
    """Standardized event types for CV vendors"""
    # Strikes
    STRIKE_JAB = "strike_jab"
    STRIKE_CROSS = "strike_cross"
    STRIKE_HOOK = "strike_hook"
    STRIKE_UPPERCUT = "strike_uppercut"
    STRIKE_ELBOW = "strike_elbow"
    STRIKE_KNEE = "strike_knee"
    
    # Kicks
    KICK_HEAD = "kick_head"
    KICK_BODY = "kick_body"
    KICK_LOW = "kick_low"
    KICK_FRONT = "kick_front"
    
    # Damage
    ROCK = "rock"
    KD_FLASH = "KD_flash"
    KD_HARD = "KD_hard"
    KD_NEARFINISH = "KD_nearfinish"
    
    # Grappling
    TD_ATTEMPT = "td_attempt"
    TD_LANDED = "td_landed"
    TD_STUFFED = "td_stuffed"
    SUB_ATTEMPT_LIGHT = "sub_attempt_light"
    SUB_ATTEMPT_DEEP = "sub_attempt_deep"
    SUB_ATTEMPT_NEARFINISH = "sub_attempt_nearfinish"
    SWEEP = "sweep"
    
    # Control
    CONTROL_START = "control_start"
    CONTROL_END = "control_end"
    CONTROL_TOP = "control_top"
    CONTROL_BACK = "control_back"
    CONTROL_CAGE = "control_cage"
    
    # Special
    POINT_DEDUCTION = "point_deduction"
    WARNING = "warning"


class Position(str, Enum):
    """Fight position"""
    DISTANCE = "distance"
    CLINCH = "clinch"
    GROUND = "ground"
    GROUND_TOP = "ground_top"
    GROUND_BOTTOM = "ground_bottom"
    GROUND_BACK = "ground_back"


class EventSource(str, Enum):
    """Event source type"""
    CV_SYSTEM = "cv_system"
    JUDGE_MANUAL = "judge_manual"
    OPERATOR = "operator"


class CVEvent(BaseModel):
    """Standardized CV Event Schema"""
    model_config = ConfigDict(extra="ignore", json_encoders={datetime: lambda v: v.isoformat()})
    
    # Core identifiers
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_id: str
    fighter_id: str  # fighter1 or fighter2
    
    # Event details
    event_type: EventType
    severity: float = Field(ge=0.0, le=1.0, description="Event severity/impact 0-1")
    confidence: float = Field(ge=0.0, le=1.0, description="CV confidence score 0-1")
    
    # Position & context
    position: Optional[Position] = Position.DISTANCE
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Timing
    timestamp_ms: int = Field(description="Event timestamp in milliseconds")
    
    # Source tracking
    source: EventSource = EventSource.CV_SYSTEM
    vendor_id: Optional[str] = None  # CV vendor identifier
    
    # Processing
    deduplicated: bool = False
    processed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ICVSSRound(BaseModel):
    """ICVSS Round with hybrid CV + Judge data"""
    model_config = ConfigDict(extra="ignore", json_encoders={datetime: lambda v: v.isoformat()})
    
    round_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    
    # Round status
    status: Literal["open", "active", "locked", "finalized"] = "open"
    
    # Events
    cv_events: List[CVEvent] = Field(default_factory=list)
    judge_events: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Scores
    fighter1_score: Optional[int] = None
    fighter2_score: Optional[int] = None
    score_card: Optional[str] = None  # e.g., "10-9"
    winner: Optional[str] = None
    
    # Scoring breakdown
    score_breakdown: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    
    # Timing
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    locked_at: Optional[datetime] = None
    
    # Audit
    event_hash: Optional[str] = None  # SHA256 of event stream


class ScoreRequest(BaseModel):
    """Request to calculate score"""
    bout_id: str
    round_id: str
    include_cv: bool = True
    include_judge: bool = True


class ScoreResponse(BaseModel):
    """Hybrid score calculation response"""
    model_config = ConfigDict(extra="ignore", json_encoders={datetime: lambda v: v.isoformat()})
    bout_id: str
    round_id: str
    round_num: int
    
    # Final scores
    fighter1_score: int
    fighter2_score: int
    score_card: str
    winner: str
    
    # Component breakdown
    fighter1_breakdown: Dict[str, float]
    fighter2_breakdown: Dict[str, float]
    
    # Metadata
    confidence: float
    cv_event_count: int
    judge_event_count: int
    total_events: int
    
    # Sources
    cv_contribution: float  # 0-1
    judge_contribution: float  # 0-1
    
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(BaseModel):
    """Immutable audit log entry"""
    model_config = ConfigDict(extra="ignore", json_encoders={datetime: lambda v: v.isoformat()})
    
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_id: str
    
    action: str  # "event_added", "round_locked", "score_calculated"
    actor: str  # "cv_system", "judge", "operator"
    
    data: Dict[str, Any]
    data_hash: str  # SHA256 hash
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: Literal["cv_event", "judge_event", "score_update", "round_status", "broadcast"]
    bout_id: str
    round_id: Optional[str] = None
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
