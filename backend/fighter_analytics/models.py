"""
Fighter Analytics - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid


class FighterProfile(BaseModel):
    """Fighter profile and basic info"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    nickname: Optional[str] = None
    weight_class: str  # e.g., "Lightweight", "Welterweight"
    nationality: Optional[str] = None
    team: Optional[str] = None
    record_wins: int = 0
    record_losses: int = 0
    record_draws: int = 0
    total_fights: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BoutResult(BaseModel):
    """Single bout result for a fighter"""
    bout_id: str
    event_name: str
    opponent_id: str
    opponent_name: str
    date: datetime
    result: str  # "win", "loss", "draw", "no_contest"
    method: Optional[str] = None  # "KO", "TKO", "Submission", "Decision"
    round_ended: Optional[int] = None
    strikes_landed: int = 0
    strikes_attempted: int = 0
    takedowns_landed: int = 0
    takedowns_attempted: int = 0
    control_time_seconds: int = 0
    knockdowns_scored: int = 0
    submission_attempts: int = 0
    judge_scores: Optional[List[int]] = None


class PerformanceStats(BaseModel):
    """Aggregated performance statistics"""
    fighter_id: str
    fighter_name: str
    
    # Record
    total_fights: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    
    # Striking
    total_strikes_landed: int
    total_strikes_attempted: int
    strike_accuracy: float
    avg_strikes_per_fight: float
    knockdowns_total: int
    
    # Grappling
    total_takedowns_landed: int
    total_takedowns_attempted: int
    takedown_success_rate: float
    avg_control_time_seconds: float
    submission_attempts_total: int
    
    # Finish stats
    ko_tko_wins: int
    submission_wins: int
    decision_wins: int
    finish_rate: float
    
    # Trends
    last_5_results: List[str]  # ["W", "W", "L", "W", "W"]
    current_streak: str  # "3W" or "2L"
    
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LeaderboardEntry(BaseModel):
    """Leaderboard entry for rankings"""
    rank: int
    fighter_id: str
    fighter_name: str
    weight_class: str
    record: str  # "15-3-0"
    win_rate: float
    strike_accuracy: float
    takedown_success_rate: float
    finish_rate: float
    total_fights: int


class FighterComparison(BaseModel):
    """Head-to-head comparison between two fighters"""
    fighter_1: PerformanceStats
    fighter_2: PerformanceStats
    
    # Advantages
    fighter_1_advantages: List[str]
    fighter_2_advantages: List[str]
    
    # Previous meetings
    previous_meetings: List[BoutResult]
    meetings_count: int
