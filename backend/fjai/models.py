"""
Fight Judge AI - Core Data Models
Standardized event schema compatible with Jabbr/CombatIQ
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid


class EventType(str, Enum):
    """Standardized event types"""
    # Knockdowns (with tiers)
    KD_FLASH = "kd_flash"
    KD_HARD = "kd_hard"
    KD_NF = "kd_nf"  # Near-finish
    
    # Damage events
    ROCKED = "rocked"
    STRIKE_SIG = "strike_sig"  # Significant strike
    STRIKE_HIGHIMPACT = "strike_highimpact"
    
    # Grappling
    TD_ATTEMPT = "td_attempt"
    TD_LAND = "td_land"
    SUB_ATTEMPT = "sub_attempt"
    
    # Control
    CONTROL_START = "control_start"
    CONTROL_END = "control_end"
    
    # Dynamics
    MOMENTUM_SWING = "momentum_swing"


class EventSource(str, Enum):
    """Event source types"""
    MANUAL = "manual"
    CV_SYSTEM = "cv_system"
    ANALYTICS = "analytics"


class CombatEvent(BaseModel):
    """Standardized combat event schema"""
    model_config = ConfigDict(extra="ignore", json_encoders={datetime: lambda v: v.isoformat()})
    
    # Core identifiers
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_id: str
    fighter_id: str  # fighter_a or fighter_b
    
    # Event details
    event_type: EventType
    severity: float = Field(ge=0.0, le=1.0, description="Event severity 0-1")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence")
    
    # Metadata
    timestamp_ms: int = Field(description="Event timestamp in milliseconds")
    source: EventSource
    camera_id: Optional[str] = None
    position: Optional[str] = Field(default=None, description="Octagon position")
    angle: Optional[float] = Field(default=None, description="Camera angle in degrees")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing flags
    deduplicated: bool = False
    canonical: bool = False  # True if this is the canonical event from multi-camera
    processed_at: Optional[datetime] = None


class RoundState(BaseModel):
    """Round state tracking"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    round_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    status: Literal["open", "scoring", "locked"] = "open"
    
    # Events
    events: List[CombatEvent] = Field(default_factory=list)
    
    # Scores
    fighter_a_score: Optional[float] = None
    fighter_b_score: Optional[float] = None
    score_card: Optional[str] = None  # e.g., "10-9"
    winner: Optional[str] = None
    
    # Metadata
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    locked_at: Optional[datetime] = None
    event_hash: Optional[str] = None


class ScoreBreakdown(BaseModel):
    """Detailed score breakdown by category"""
    damage: float = 0.0
    control: float = 0.0
    aggression: float = 0.0
    defense: float = 0.0
    total: float = 0.0


class ScoringWeights(BaseModel):
    """Scoring system weights"""
    damage: float = Field(default=0.50, ge=0.0, le=1.0)
    control: float = Field(default=0.25, ge=0.0, le=1.0)
    aggression: float = Field(default=0.15, ge=0.0, le=1.0)
    defense: float = Field(default=0.10, ge=0.0, le=1.0)
    damage_primacy_threshold: float = Field(default=0.30, description="Damage score needed to override other categories")


class RoundScore(BaseModel):
    """Complete round scoring output"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    round_id: str
    bout_id: str
    round_num: int
    
    # Scores
    fighter_a_score: float
    fighter_b_score: float
    score_card: str  # "10-9", "10-8", etc.
    winner: str
    confidence: float
    
    # Breakdowns
    fighter_a_breakdown: ScoreBreakdown
    fighter_b_breakdown: ScoreBreakdown
    
    # Event counts
    total_events: int
    manual_events: int
    cv_events: int
    
    # Damage primacy flag
    damage_override: bool = False
    
    # Timestamp
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogEntry(BaseModel):
    """Immutable audit log entry"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_id: str
    action: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any]
    signature: str  # SHA256 hash
