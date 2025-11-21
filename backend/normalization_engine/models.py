"""
Normalization Engine - Data Models
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent


class NormalizedEvent(BaseModel):
    """Normalized event with weight breakdown"""
    original_event: CombatEvent
    
    # Normalized weights (0-1)
    damage_weight: float = 0.0
    control_weight: float = 0.0
    aggression_weight: float = 0.0
    defense_weight: float = 0.0
    
    # Total normalized weight
    total_weight: float = 0.0
    
    # Weight breakdown for transparency
    breakdown: Dict[str, float] = Field(default_factory=dict)
    
    # Adjustments applied
    severity_multiplier: float = 1.0
    confidence_boost: float = 1.0
    capped: bool = False


class NormalizationConfig(BaseModel):
    """Normalization configuration"""
    global_caps: Dict[str, float]
    event_weights: Dict[str, float]
    cv_intensity_mapping: Dict[str, float]
    severity_multipliers: Dict[str, float]
    confidence_boosts: Dict[str, float]
