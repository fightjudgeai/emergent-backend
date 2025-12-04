"""
Fantasy Scoring Models
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ========================================
# SCORING PROFILE MODELS
# ========================================

class ScoringWeights(BaseModel):
    """Stat weights for fantasy scoring"""
    sig_strike: float = Field(..., description="Points per significant strike")
    knockdown: float = Field(..., description="Points per knockdown")
    takedown: float = Field(..., description="Points per takedown")
    control_minute: float = Field(..., description="Points per minute of control")
    submission_attempt: float = Field(..., description="Points per submission attempt")
    
    # Optional advanced weights
    ai_damage_multiplier: Optional[float] = Field(None, description="Multiplier for AI damage score")
    ai_control_multiplier: Optional[float] = Field(None, description="Multiplier for AI control score")
    strike_accuracy_multiplier: Optional[float] = Field(None, description="Bonus for strike accuracy")
    defense_multiplier: Optional[float] = Field(None, description="Bonus for defensive stats")


class ScoringBonuses(BaseModel):
    """Bonus points for achievements"""
    win_bonus: float = Field(..., description="Bonus for winning")
    finish_bonus: float = Field(..., description="Bonus for finishing (KO/TKO/SUB)")
    ko_bonus: Optional[float] = Field(None, description="Additional bonus for KO/TKO")
    submission_bonus: Optional[float] = Field(None, description="Additional bonus for submission")
    dominant_round_bonus: Optional[float] = Field(None, description="Bonus per dominant round")
    clean_sweep_bonus: Optional[float] = Field(None, description="Bonus for winning all rounds")


class ScoringPenalties(BaseModel):
    """Penalty points for infractions"""
    point_deduction: Optional[float] = Field(None, description="Penalty for official point deduction")
    foul: Optional[float] = Field(None, description="Penalty per foul")


class ScoringThresholds(BaseModel):
    """Thresholds for bonuses/penalties"""
    dominant_damage_threshold: Optional[float] = Field(None, description="AI damage score for dominant round")
    dominant_control_threshold: Optional[int] = Field(None, description="Control seconds for dominant round")
    clean_sweep_rounds: Optional[int] = Field(None, description="Rounds needed for clean sweep bonus")


class MarketSettlementConfig(BaseModel):
    """Sportsbook market settlement configuration"""
    min_rounds_for_decision: int = Field(..., description="Minimum rounds for decision settlement")
    judge_score_weight: float = Field(..., description="Weight given to judge scores")


class FantasyScoringConfig(BaseModel):
    """Complete fantasy scoring profile configuration"""
    description: str
    weights: ScoringWeights
    bonuses: ScoringBonuses
    penalties: Optional[ScoringPenalties] = None
    thresholds: Optional[ScoringThresholds] = None
    market_settlement: Optional[MarketSettlementConfig] = None
    version: str = "1.0"


class FantasyScoringProfile(BaseModel):
    """Fantasy scoring profile"""
    id: str = Field(..., description="Profile ID (e.g., fantasy.basic)")
    name: str = Field(..., description="Human-readable profile name")
    config: Dict[str, Any] = Field(..., description="Scoring configuration as JSON")
    created_at: datetime
    
    class Config:
        from_attributes = True


class FantasyScoringProfileResponse(BaseModel):
    """Fantasy scoring profile with parsed config"""
    id: str
    name: str
    config: FantasyScoringConfig
    created_at: datetime


# ========================================
# FANTASY STATS MODELS
# ========================================

class FantasyPointsBreakdown(BaseModel):
    """Breakdown of fantasy points by category"""
    sig_strikes: Optional[float] = Field(None, description="Points from significant strikes")
    knockdowns: Optional[float] = Field(None, description="Points from knockdowns")
    takedowns: Optional[float] = Field(None, description="Points from takedowns")
    control: Optional[float] = Field(None, description="Points from control time")
    submission_attempts: Optional[float] = Field(None, description="Points from submission attempts")
    win_bonus: Optional[float] = Field(None, description="Win bonus points")
    finish_bonus: Optional[float] = Field(None, description="Finish bonus points")
    ko_bonus: Optional[float] = Field(None, description="KO bonus points")
    submission_bonus: Optional[float] = Field(None, description="Submission bonus points")
    dominant_round_bonus: Optional[float] = Field(None, description="Dominant round bonus")
    clean_sweep_bonus: Optional[float] = Field(None, description="Clean sweep bonus")
    penalties: Optional[float] = Field(None, description="Penalty points")
    
    raw_stats: Optional[Dict[str, Any]] = Field(None, description="Raw stats used in calculation")


class FantasyFightStats(BaseModel):
    """Fantasy stats for a fighter in a fight"""
    id: UUID
    fight_id: UUID
    fighter_id: UUID
    profile_id: str
    fantasy_points: Decimal
    breakdown: Dict[str, Any]
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FantasyFightStatsResponse(BaseModel):
    """Fantasy stats response with fighter details"""
    fighter: Dict[str, Any] = Field(..., description="Fighter details")
    profile_id: str
    fantasy_points: float
    breakdown: FantasyPointsBreakdown
    updated_at: datetime


class FantasyLeaderboard(BaseModel):
    """Fantasy leaderboard entry"""
    fighter_id: UUID
    fighter_name: str
    fighter_nickname: Optional[str]
    fantasy_points: float
    fights_count: int
    avg_points_per_fight: float


class FantasyLeaderboardResponse(BaseModel):
    """Fantasy leaderboard response"""
    profile_id: str
    profile_name: str
    event_code: Optional[str] = None
    leaderboard: list[FantasyLeaderboard]
    total_fighters: int


# ========================================
# API REQUEST MODELS
# ========================================

class CalculateFantasyPointsRequest(BaseModel):
    """Request to calculate fantasy points"""
    fight_id: UUID = Field(..., description="Fight ID")
    fighter_id: UUID = Field(..., description="Fighter ID")
    profile_id: str = Field(..., description="Scoring profile ID", examples=["fantasy.basic", "fantasy.advanced", "sportsbook.pro"])


class BulkCalculateFantasyPointsRequest(BaseModel):
    """Request to calculate fantasy points for all fighters in a fight"""
    fight_id: UUID = Field(..., description="Fight ID")
    profile_ids: list[str] = Field(default=["fantasy.basic", "fantasy.advanced", "sportsbook.pro"], description="Scoring profile IDs")


class FantasyPointsCalculationResponse(BaseModel):
    """Response from fantasy points calculation"""
    success: bool
    fighter_id: UUID
    fight_id: UUID
    profile_id: str
    fantasy_points: float
    breakdown: FantasyPointsBreakdown
    message: Optional[str] = None
