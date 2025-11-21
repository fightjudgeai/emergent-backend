"""
Scoring Simulator - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent


class SimulationScript(BaseModel):
    """Fight simulation script"""
    bout_id: str
    event_name: str
    fighters: Dict[str, str]
    events: List[CombatEvent]
    
    # Simulation settings
    speed_multiplier: float = 1.0  # 1x, 2x, 5x


class RoundSimulationResult(BaseModel):
    """Single round simulation result"""
    round_num: int
    score_card: str
    winner: str
    confidence: float
    
    # Breakdowns
    fighter_a_total: float
    fighter_b_total: float
    
    # Event counts
    total_events: int
    judge_events: int
    cv_events: int


class SimulationResult(BaseModel):
    """Complete simulation result"""
    bout_id: str
    
    # Round results
    round_results: List[RoundSimulationResult]
    
    # Final result
    final_score: str
    winner: str
    
    # Statistics
    total_events_processed: int
    simulation_duration_sec: float
    
    # Event correlations
    event_correlations: Dict[str, int] = Field(default_factory=dict)
    
    completed_at: datetime = Field(default_factory=datetime.now)
