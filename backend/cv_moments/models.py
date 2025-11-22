"""
CV Moments - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid


class SignificantMoment(BaseModel):
    """A significant moment detected in a fight"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    timestamp_ms: int  # Time in round
    moment_type: Literal["knockdown", "big_strike", "submission_attempt", "controversy", "round_end"]
    severity: float  # 0.0-1.0 scale
    confidence: float  # 0.0-1.0 scale
    
    # Participants
    fighter_1_id: Optional[str] = None
    fighter_2_id: Optional[str] = None
    
    # Description
    description: str
    
    # Metadata
    metadata: dict = Field(default_factory=dict)
    
    # Video clip info
    clip_start_ms: Optional[int] = None
    clip_end_ms: Optional[int] = None
    
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Knockdown(BaseModel):
    """Knockdown moment details"""
    moment_id: str
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    # Who scored the knockdown
    aggressor_id: str
    victim_id: str
    
    # Details
    strike_type: Optional[str] = None  # "punch", "kick", etc.
    impact_severity: float
    recovery_time_ms: Optional[int] = None
    
    # Context
    was_flash_knockdown: bool = False
    led_to_finish: bool = False


class BigStrike(BaseModel):
    """Significant strike details"""
    moment_id: str
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    striker_id: str
    target_id: str
    
    strike_type: str  # "punch", "kick", "elbow", "knee"
    target_area: str  # "head", "body", "leg"
    impact_score: float  # 0.0-1.0
    
    combo_strikes: int = 1  # Number of strikes in combo
    momentum_shift: bool = False


class SubmissionAttempt(BaseModel):
    """Submission attempt details"""
    moment_id: str
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    attacker_id: str
    defender_id: str
    
    submission_type: str  # "rear_naked_choke", "armbar", etc.
    danger_level: float  # How close to finishing (0.0-1.0)
    duration_ms: int
    
    was_successful: bool = False
    escape_method: Optional[str] = None


class ControversyMoment(BaseModel):
    """Controversial moment details"""
    moment_id: str
    bout_id: str
    round_num: Optional[int] = None
    
    controversy_type: Literal[
        "split_decision",
        "close_round",
        "score_variance",
        "questionable_stoppage",
        "foul_not_called"
    ]
    
    description: str
    severity: float
    
    # Score related
    judge_scores: Optional[List[int]] = None
    score_variance: Optional[float] = None


class HighlightReel(BaseModel):
    """Complete highlight reel for a bout"""
    bout_id: str
    
    total_moments: int
    knockdowns: List[Knockdown]
    big_strikes: List[BigStrike]
    submission_attempts: List[SubmissionAttempt]
    controversies: List[ControversyMoment]
    
    # Statistics
    most_exciting_round: Optional[int] = None
    momentum_shifts: int = 0
    
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MomentAnalysis(BaseModel):
    """Analysis results for a bout"""
    bout_id: str
    total_rounds: int
    
    moments_detected: int
    knockdowns_count: int
    big_strikes_count: int
    submission_attempts_count: int
    controversies_count: int
    
    excitement_score: float  # 0-100 scale
    competitiveness_score: float  # 0-100 scale
    
    top_moments: List[SignificantMoment]
    
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
