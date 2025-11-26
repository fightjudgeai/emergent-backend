"""
Production Database Models

Defines all database schemas with proper types, validation, and relations.
Designed for MongoDB with UPSERT-safe operations.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class EventType(str, Enum):
    """Event types from judge logging"""
    # Strikes
    HEAD_KICK = "Head Kick"
    BODY_KICK = "Body Kick"
    LOW_KICK = "Low Kick"
    FRONT_KICK = "Front Kick"
    ELBOW = "Elbow"
    KNEE = "Knee"
    HOOK = "Hook"
    CROSS = "Cross"
    JAB = "Jab"
    UPPERCUT = "Uppercut"
    
    # Damage
    KD = "KD"
    ROCKED = "Rocked/Stunned"
    
    # Grappling
    TAKEDOWN_LANDED = "Takedown Landed"
    TAKEDOWN_STUFFED = "Takedown Stuffed"
    SUBMISSION_ATTEMPT = "Submission Attempt"
    SWEEP_REVERSAL = "Sweep/Reversal"
    
    # Control
    GROUND_TOP_CONTROL = "Ground Top Control"
    GROUND_BACK_CONTROL = "Ground Back Control"
    CAGE_CONTROL = "Cage Control Time"
    
    # Other
    TOTAL_STRIKES = "TS"


class Position(str, Enum):
    """Fight position"""
    DISTANCE = "distance"
    CLINCH = "clinch"
    GROUND = "ground"


class Target(str, Enum):
    """Strike target"""
    HEAD = "head"
    BODY = "body"
    LEG = "leg"


class Source(str, Enum):
    """Event source"""
    JUDGE_SOFTWARE = "judge_software"
    STAT_OPERATOR = "stat_operator"
    AI_CV = "ai_cv"
    HYBRID = "hybrid"


class Stance(str, Enum):
    """Fighter stance"""
    ORTHODOX = "orthodox"
    SOUTHPAW = "southpaw"
    SWITCH = "switch"


class Division(str, Enum):
    """Weight divisions"""
    FLYWEIGHT = "Flyweight"
    BANTAMWEIGHT = "Bantamweight"
    FEATHERWEIGHT = "Featherweight"
    LIGHTWEIGHT = "Lightweight"
    WELTERWEIGHT = "Welterweight"
    MIDDLEWEIGHT = "Middleweight"
    LIGHT_HEAVYWEIGHT = "Light Heavyweight"
    HEAVYWEIGHT = "Heavyweight"
    
    # Women's
    WOMENS_STRAWWEIGHT = "Women's Strawweight"
    WOMENS_FLYWEIGHT = "Women's Flyweight"
    WOMENS_BANTAMWEIGHT = "Women's Bantamweight"
    WOMENS_FEATHERWEIGHT = "Women's Featherweight"


# ============================================================================
# FIGHTERS TABLE
# ============================================================================

class Fighter(BaseModel):
    """
    Fighter profile with biographical and physical data
    
    Indexes:
    - id (unique)
    - name (text search)
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Basic Info
    name: str
    nickname: Optional[str] = None
    gym: Optional[str] = None
    
    # Record
    record: Optional[str] = None  # "25-3-0" format (wins-losses-draws)
    
    # Physical
    division: Optional[Division] = None
    height_cm: Optional[float] = None
    reach_cm: Optional[float] = None
    stance: Optional[Stance] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @validator('record')
    def validate_record(cls, v):
        """Validate record format"""
        if v and '-' not in v:
            raise ValueError('Record must be in format "W-L-D"')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Conor McGregor",
                "nickname": "The Notorious",
                "gym": "SBG Ireland",
                "record": "22-6-0",
                "division": "Lightweight",
                "height_cm": 175,
                "reach_cm": 188,
                "stance": "southpaw"
            }
        }


# ============================================================================
# EVENTS TABLE
# ============================================================================

class Event(BaseModel):
    """
    Individual fight event logged during a round
    
    Indexes:
    - (fight_id, round, timestamp_in_round)
    - (fighter_id)
    - (event_type)
    - (created_at)
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Relations
    fight_id: str  # References bout/fight
    fighter_id: str  # References fighters.id
    
    # Timing
    round: int  # Round number (1, 2, 3, etc.)
    timestamp_in_round: float  # Seconds into the round (0-300)
    
    # Event Details
    event_type: str  # Use EventType enum values
    
    # Context
    position: Optional[Position] = None  # distance, clinch, ground
    target: Optional[Target] = None  # head, body, leg (for strikes)
    source: Source = Source.JUDGE_SOFTWARE  # Event origin
    
    # Additional Data
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    # metadata examples:
    # - significant: bool (for strikes)
    # - tier: str (for KD: flash, hard, near_finish)
    # - depth: str (for submissions)
    # - duration: int (for control events)
    # - type: str (start/stop for control)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @validator('round')
    def validate_round(cls, v):
        """Validate round number"""
        if v < 1 or v > 12:
            raise ValueError('Round must be between 1 and 12')
        return v
    
    @validator('timestamp_in_round')
    def validate_timestamp(cls, v):
        """Validate timestamp"""
        if v < 0 or v > 300:
            raise ValueError('Timestamp must be between 0 and 300 seconds')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "fight_id": "ufc301_main",
                "fighter_id": "fighter_123",
                "round": 1,
                "timestamp_in_round": 45.5,
                "event_type": "Head Kick",
                "position": "distance",
                "target": "head",
                "source": "judge_software",
                "metadata": {"significant": True, "landed": True}
            }
        }


# ============================================================================
# ROUND STATS TABLE
# ============================================================================

class RoundStat(BaseModel):
    """
    Aggregated statistics for a fighter in a specific round
    
    Indexes:
    - (fight_id, round, fighter_id) - UNIQUE
    - (fighter_id)
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Relations
    fight_id: str
    round: int
    fighter_id: str  # References fighters.id
    
    # Strike Statistics
    total_strikes_attempted: int = 0
    total_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    sig_strikes_landed: int = 0
    
    # Significant Strike Breakdown by Target
    sig_head_attempted: int = 0
    sig_head_landed: int = 0
    sig_body_attempted: int = 0
    sig_body_landed: int = 0
    sig_leg_attempted: int = 0
    sig_leg_landed: int = 0
    
    # Significant Strike Breakdown by Position
    sig_distance_attempted: int = 0
    sig_distance_landed: int = 0
    sig_clinch_attempted: int = 0
    sig_clinch_landed: int = 0
    sig_ground_attempted: int = 0
    sig_ground_landed: int = 0
    
    # Power Strikes
    knockdowns: int = 0
    knockdown_tiers: Dict[str, int] = Field(default_factory=dict)  # flash, hard, near_finish
    rocked_events: int = 0
    
    # Takedown Statistics
    td_attempts: int = 0
    td_landed: int = 0
    td_stuffed: int = 0
    
    # Submission Attempts
    sub_attempts: int = 0
    sub_attempts_by_type: Dict[str, int] = Field(default_factory=dict)  # armbar, guillotine, etc.
    
    # Control Time (seconds)
    ground_control_secs: int = 0
    clinch_control_secs: int = 0
    cage_control_secs: int = 0
    back_control_secs: int = 0
    mount_secs: int = 0
    total_control_secs: int = 0
    
    # Position Time (seconds)
    distance_time_secs: int = 0
    clinch_time_secs: int = 0
    ground_time_secs: int = 0
    
    # Computed Metrics (cached)
    sig_strike_accuracy: float = 0.0  # percentage
    sig_strike_defense: float = 0.0  # percentage
    td_accuracy: float = 0.0  # percentage
    control_time_percentage: float = 0.0  # of 300 seconds
    
    # Metadata
    source_event_count: int = 0  # Number of events processed
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_schema_extra = {
            "example": {
                "fight_id": "ufc301_main",
                "round": 1,
                "fighter_id": "fighter_123",
                "sig_strikes_landed": 18,
                "knockdowns": 1,
                "total_control_secs": 120
            }
        }


# ============================================================================
# FIGHT STATS TABLE
# ============================================================================

class FightStat(BaseModel):
    """
    Aggregated statistics for a fighter across an entire fight
    
    Indexes:
    - (fight_id, fighter_id) - UNIQUE
    - (fighter_id)
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Relations
    fight_id: str
    fighter_id: str  # References fighters.id
    
    # Fight Metadata
    total_rounds: int = 0
    fight_duration_secs: int = 0  # Total seconds fought
    
    # Strike Statistics (aggregated from all rounds)
    total_strikes_attempted: int = 0
    total_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    sig_strikes_landed: int = 0
    
    # Significant Strike Breakdown by Target
    sig_head_attempted: int = 0
    sig_head_landed: int = 0
    sig_body_attempted: int = 0
    sig_body_landed: int = 0
    sig_leg_attempted: int = 0
    sig_leg_landed: int = 0
    
    # Significant Strike Breakdown by Position
    sig_distance_attempted: int = 0
    sig_distance_landed: int = 0
    sig_clinch_attempted: int = 0
    sig_clinch_landed: int = 0
    sig_ground_attempted: int = 0
    sig_ground_landed: int = 0
    
    # Power Strikes
    knockdowns: int = 0
    knockdown_tiers: Dict[str, int] = Field(default_factory=dict)
    rocked_events: int = 0
    
    # Takedown Statistics
    td_attempts: int = 0
    td_landed: int = 0
    td_stuffed: int = 0
    
    # Submission Attempts
    sub_attempts: int = 0
    sub_attempts_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Control Time (seconds)
    ground_control_secs: int = 0
    clinch_control_secs: int = 0
    cage_control_secs: int = 0
    back_control_secs: int = 0
    mount_secs: int = 0
    total_control_secs: int = 0
    
    # Position Time (seconds)
    distance_time_secs: int = 0
    clinch_time_secs: int = 0
    ground_time_secs: int = 0
    
    # Computed Metrics
    sig_strike_accuracy: float = 0.0  # percentage
    sig_strike_defense: float = 0.0  # percentage
    td_accuracy: float = 0.0  # percentage
    td_defense: float = 0.0  # percentage
    control_time_percentage: float = 0.0  # of total fight time
    
    # Per-Minute Rates
    sig_strikes_per_minute: float = 0.0
    total_strikes_per_minute: float = 0.0
    td_per_15min: float = 0.0
    
    # Metadata
    rounds_aggregated: int = 0
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_schema_extra = {
            "example": {
                "fight_id": "ufc301_main",
                "fighter_id": "fighter_123",
                "total_rounds": 3,
                "sig_strikes_landed": 54,
                "sig_strike_accuracy": 64.3,
                "knockdowns": 2
            }
        }


# ============================================================================
# CAREER STATS TABLE
# ============================================================================

class CareerStat(BaseModel):
    """
    Lifetime aggregated statistics for a fighter
    
    Indexes:
    - (fighter_id) - UNIQUE
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Relations
    fighter_id: str  # References fighters.id - UNIQUE
    
    # Career Summary
    total_fights: int = 0
    total_rounds: int = 0
    total_fight_time_secs: int = 0
    
    # Win/Loss (if tracked)
    wins: int = 0
    losses: int = 0
    draws: int = 0
    
    # Strike Statistics (lifetime)
    total_strikes_attempted: int = 0
    total_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    sig_strikes_landed: int = 0
    
    # Significant Strike Breakdown by Target
    sig_head_attempted: int = 0
    sig_head_landed: int = 0
    sig_body_attempted: int = 0
    sig_body_landed: int = 0
    sig_leg_attempted: int = 0
    sig_leg_landed: int = 0
    
    # Significant Strike Breakdown by Position
    sig_distance_attempted: int = 0
    sig_distance_landed: int = 0
    sig_clinch_attempted: int = 0
    sig_clinch_landed: int = 0
    sig_ground_attempted: int = 0
    sig_ground_landed: int = 0
    
    # Power Strikes
    knockdowns: int = 0
    knockdown_tiers: Dict[str, int] = Field(default_factory=dict)
    rocked_events: int = 0
    
    # Takedown Statistics
    td_attempts: int = 0
    td_landed: int = 0
    td_stuffed: int = 0
    
    # Submission Attempts
    sub_attempts: int = 0
    sub_attempts_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Control Time (seconds)
    ground_control_secs: int = 0
    clinch_control_secs: int = 0
    cage_control_secs: int = 0
    back_control_secs: int = 0
    mount_secs: int = 0
    total_control_secs: int = 0
    
    # Advanced Career Metrics
    avg_sig_strike_accuracy: float = 0.0  # percentage
    avg_sig_strike_defense: float = 0.0  # percentage
    avg_td_accuracy: float = 0.0  # percentage
    avg_td_defense: float = 0.0  # percentage
    
    # Per-Minute Career Rates
    avg_sig_strikes_per_min: float = 0.0
    avg_total_strikes_per_min: float = 0.0
    avg_td_per_15min: float = 0.0
    knockdowns_per_15min: float = 0.0
    
    # Per-Fight Averages
    avg_control_time_per_fight: float = 0.0  # seconds
    avg_knockdowns_per_fight: float = 0.0
    avg_td_per_fight: float = 0.0
    avg_sub_attempts_per_fight: float = 0.0
    
    # Derived JSON (additional computed metrics)
    derived_metrics: Dict[str, Any] = Field(default_factory=dict)
    # derived_metrics can include:
    # - finish_rate
    # - ko_rate
    # - submission_rate
    # - decision_rate
    # - early_pressure_rate
    # - late_rally_rate
    
    # Metadata
    fights_aggregated: int = 0
    last_fight_date: Optional[datetime] = None
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_schema_extra = {
            "example": {
                "fighter_id": "fighter_123",
                "total_fights": 25,
                "total_rounds": 68,
                "avg_sig_strikes_per_min": 4.2,
                "avg_sig_strike_accuracy": 58.3,
                "knockdowns_per_15min": 0.35
            }
        }


# ============================================================================
# HELPER MODELS
# ============================================================================

class DatabaseHealth(BaseModel):
    """Database health check response"""
    status: str = "healthy"
    collections: Dict[str, int] = Field(default_factory=dict)  # collection: count
    indexes: Dict[str, List[str]] = Field(default_factory=dict)  # collection: [indexes]
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
