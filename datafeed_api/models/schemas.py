"""
Pydantic schemas for data validation and serialization
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, Literal, Dict, Any
from datetime import datetime
from decimal import Decimal


# ========================================
# DATABASE MODELS
# ========================================

class Event(BaseModel):
    id: UUID4
    code: str
    name: str
    venue: Optional[str] = None
    promotion: Optional[str] = None
    start_time_utc: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Fighter(BaseModel):
    id: UUID4
    first_name: str
    last_name: str
    nickname: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Fight(BaseModel):
    id: UUID4
    event_id: UUID4
    bout_order: int
    code: str
    red_fighter_id: UUID4
    blue_fighter_id: UUID4
    scheduled_rounds: int
    weight_class: Optional[str] = None
    rule_set: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoundState(BaseModel):
    id: UUID4
    fight_id: UUID4
    round: int
    ts_ms: int
    seq: int
    red_strikes: int = 0
    red_sig_strikes: int = 0
    red_knockdowns: int = 0
    red_control_sec: int = 0
    red_ai_damage: Decimal = Decimal('0.0')
    red_ai_win_prob: Decimal = Decimal('0.5')
    blue_strikes: int = 0
    blue_sig_strikes: int = 0
    blue_knockdowns: int = 0
    blue_control_sec: int = 0
    blue_ai_damage: Decimal = Decimal('0.0')
    blue_ai_win_prob: Decimal = Decimal('0.5')
    round_locked: bool = False
    created_at: datetime
    source: str = 'fightjudge.ai'

    class Config:
        from_attributes = True


class FightResult(BaseModel):
    id: UUID4
    fight_id: UUID4
    winner_side: Literal['RED', 'BLUE', 'DRAW', 'NC']
    method: str
    round: Optional[int] = None
    time: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class APIClient(BaseModel):
    id: UUID4
    name: str
    api_key: str
    scope: Literal['fantasy.basic', 'fantasy.advanced', 'sportsbook.pro']
    active: bool
    rate_limit_per_min: int
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========================================
# WEBSOCKET PAYLOADS
# ========================================

class CornerState(BaseModel):
    fighter_id: UUID4
    strikes: int
    sig_strikes: int
    knockdowns: int
    control_sec: int
    ai_damage: Optional[float] = None
    ai_win_prob: Optional[float] = None


class RoundStatePayload(BaseModel):
    fight_code: str
    event_code: str
    round: int
    seq: int
    ts_ms: int
    state: Dict[Literal['red', 'blue'], CornerState]
    meta: Dict[str, Any] = {
        'round_locked': False,
        'source': 'fightjudge.ai',
        'version': '1.0.0'
    }


class FightResultPayload(BaseModel):
    fight_code: str
    event_code: str
    winner: Literal['RED', 'BLUE', 'DRAW', 'NC']
    method: str
    round: Optional[int] = None
    time: Optional[str] = None


class WebSocketMessage(BaseModel):
    type: Literal['round_state', 'round_locked', 'fight_result', 'auth_ok', 'auth_error', 'subscribe_ok', 'error']
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AuthMessage(BaseModel):
    type: Literal['auth']
    api_key: str


class SubscribeMessage(BaseModel):
    type: Literal['subscribe']
    channel: Literal['fight', 'event']
    filters: Dict[str, str] = Field(default_factory=dict)
