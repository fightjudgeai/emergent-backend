"""
Sportsbook Market Models
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


# ========================================
# ENUMS
# ========================================

class MarketType(str, Enum):
    """Market types"""
    WINNER = "WINNER"
    TOTAL_SIG_STRIKES = "TOTAL_SIG_STRIKES"
    KD_OVER_UNDER = "KD_OVER_UNDER"
    SUB_ATT_OVER_UNDER = "SUB_ATT_OVER_UNDER"


class MarketStatus(str, Enum):
    """Market status"""
    OPEN = "OPEN"
    SUSPENDED = "SUSPENDED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"


# ========================================
# MARKET MODELS
# ========================================

class Market(BaseModel):
    """Market database model"""
    id: UUID
    fight_id: UUID
    market_type: MarketType
    params: Dict[str, Any]
    status: MarketStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MarketSettlement(BaseModel):
    """Market settlement database model"""
    id: UUID
    market_id: UUID
    result_payload: Dict[str, Any]
    settled_at: datetime
    
    class Config:
        from_attributes = True


# ========================================
# REQUEST MODELS
# ========================================

class CreateMarketRequest(BaseModel):
    """Request to create a market"""
    fight_id: UUID = Field(..., description="Fight UUID")
    market_type: MarketType = Field(..., description="Type of market")
    params: Dict[str, Any] = Field(..., description="Market parameters (line, odds, etc.)")
    status: MarketStatus = Field(default=MarketStatus.OPEN, description="Initial status")


class CreateStandardMarketsRequest(BaseModel):
    """Request to create standard market set for a fight"""
    fight_id: UUID = Field(..., description="Fight UUID")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional configuration for lines and odds")


class UpdateMarketStatusRequest(BaseModel):
    """Request to update market status"""
    status: MarketStatus = Field(..., description="New status")


class SettleMarketRequest(BaseModel):
    """Request to manually settle a market"""
    market_id: UUID = Field(..., description="Market UUID")


class SettleFightMarketsRequest(BaseModel):
    """Request to settle all markets for a fight"""
    fight_id: UUID = Field(..., description="Fight UUID")


# ========================================
# RESPONSE MODELS
# ========================================

class MarketResponse(BaseModel):
    """Market response with fight details"""
    id: UUID
    fight_id: UUID
    fight_code: Optional[str] = None
    market_type: MarketType
    params: Dict[str, Any]
    status: MarketStatus
    created_at: datetime
    updated_at: datetime
    settlement: Optional[Dict[str, Any]] = None


class SettlementResult(BaseModel):
    """Settlement result details"""
    market_type: MarketType
    winning_side: Optional[str] = Field(None, description="Winning side (RED/BLUE for WINNER, OVER/UNDER for prop bets)")
    actual_value: Optional[Any] = Field(None, description="Actual statistical value")
    line: Optional[float] = Field(None, description="Over/under line")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional settlement details")
    settled_at: datetime


class MarketSettlementResponse(BaseModel):
    """Market with settlement details"""
    market: MarketResponse
    settlement: Optional[SettlementResult] = None


class SettleMarketResponse(BaseModel):
    """Response from market settlement"""
    success: bool
    market_id: UUID
    settlement: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BulkSettlementResponse(BaseModel):
    """Response from bulk settlement operation"""
    fight_id: UUID
    total_markets: int
    settled: int
    failed: int
    results: List[SettleMarketResponse]


# ========================================
# PARAMETER MODELS
# ========================================

class WinnerMarketParams(BaseModel):
    """Parameters for WINNER market"""
    red_odds: float = Field(..., description="Odds for red corner")
    blue_odds: float = Field(..., description="Odds for blue corner")


class OverUnderMarketParams(BaseModel):
    """Parameters for over/under markets"""
    line: float = Field(..., description="Over/under line")
    over_odds: float = Field(default=1.91, description="Odds for over")
    under_odds: float = Field(default=1.91, description="Odds for under")


# ========================================
# STATISTICS MODELS
# ========================================

class MarketStatistics(BaseModel):
    """Market statistics"""
    total_markets: int
    open_markets: int
    settled_markets: int
    suspended_markets: int
    cancelled_markets: int
    by_type: Dict[str, int]


class SettlementStatistics(BaseModel):
    """Settlement statistics"""
    total_settlements: int
    settlements_today: int
    avg_settlement_time_minutes: Optional[float] = None
    settlement_accuracy: Optional[float] = Field(None, description="Percentage of successful settlements")
