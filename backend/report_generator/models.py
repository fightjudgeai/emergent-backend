"""
Report Generator - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class ReportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class RoundScore(BaseModel):
    round_num: int
    judge_scores: Dict[str, str]  # judge_id -> score_card
    ai_composite_score: str
    winner: str
    confidence: float


class MajorEvent(BaseModel):
    timestamp_ms: int
    event_type: str
    fighter_id: str
    severity: float
    description: str


class FightReport(BaseModel):
    """Complete fight report"""
    bout_id: str
    event_name: str
    fighters: Dict[str, str]  # fighter_a/b -> name
    date: datetime
    
    # Scores
    round_scores: List[RoundScore]
    final_result: str
    
    # Events
    major_events: List[MajorEvent]
    kd_timeline: List[MajorEvent]
    rocked_timeline: List[MajorEvent]
    momentum_swings: List[MajorEvent]
    
    # Statistics
    total_events: int
    strike_counts: Dict[str, int]
    control_time: Dict[str, float]
    
    # Metadata
    model_versions: Dict[str, str]
    audit_log_reference: str
    generated_at: datetime = Field(default_factory=datetime.now)
