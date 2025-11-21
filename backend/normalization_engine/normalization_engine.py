"""
Normalization Engine - Main Engine
Map events to unified scoring weights
"""

import yaml
import logging
from pathlib import Path
from typing import Dict
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent, EventType
from .models import NormalizedEvent, NormalizationConfig

logger = logging.getLogger(__name__)


class NormalizationEngine:
    """Normalize events to 0-1 weight scale"""
    
    def __init__(self, config_path: str = None):
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        self.config = NormalizationConfig(**config_dict)
        
        # Track cumulative weights to apply caps
        self.cumulative_weights = {
            "damage": 0.0,
            "control": 0.0,
            "aggression": 0.0,
            "defense": 0.0
        }
    
    def normalize_event(self, event: CombatEvent) -> NormalizedEvent:
        """
        Normalize event to 0-1 weight scale
        
        Args:
            event: Combat event
        
        Returns:
            Normalized event with weight breakdown
        """
        # Get base weight for event type
        base_weight = self._get_base_weight(event.event_type)
        
        # Apply severity multiplier
        severity_multiplier = self._calculate_severity_multiplier(event.severity)
        adjusted_weight = base_weight * severity_multiplier
        
        # Apply confidence boost
        confidence_boost = self._calculate_confidence_boost(event.confidence)
        adjusted_weight *= confidence_boost
        
        # Categorize weight
        damage_weight = 0.0
        control_weight = 0.0
        aggression_weight = 0.0
        defense_weight = 0.0
        
        category = self._categorize_event(event.event_type)
        
        if category == "damage":
            damage_weight = adjusted_weight
        elif category == "control":
            control_weight = adjusted_weight
        elif category == "aggression":
            aggression_weight = adjusted_weight
        elif category == "defense":
            defense_weight = adjusted_weight
        
        # Apply global caps
        capped = False
        if damage_weight > 0:
            self.cumulative_weights["damage"] += damage_weight
            if self.cumulative_weights["damage"] > self.config.global_caps["damage_max"]:
                overflow = self.cumulative_weights["damage"] - self.config.global_caps["damage_max"]
                damage_weight -= overflow
                self.cumulative_weights["damage"] = self.config.global_caps["damage_max"]
                capped = True
        
        # Similar for other categories...
        
        # Calculate total weight
        total_weight = damage_weight + control_weight + aggression_weight + defense_weight
        
        # Create breakdown
        breakdown = {
            "base_weight": base_weight,
            "severity_adjustment": base_weight * (severity_multiplier - 1.0),
            "confidence_adjustment": adjusted_weight * (confidence_boost - 1.0),
            "final_damage": damage_weight,
            "final_control": control_weight,
            "final_aggression": aggression_weight,
            "final_defense": defense_weight
        }
        
        return NormalizedEvent(
            original_event=event,
            damage_weight=damage_weight,
            control_weight=control_weight,
            aggression_weight=aggression_weight,
            defense_weight=defense_weight,
            total_weight=total_weight,
            breakdown=breakdown,
            severity_multiplier=severity_multiplier,
            confidence_boost=confidence_boost,
            capped=capped
        )
    
    def _get_base_weight(self, event_type: EventType) -> float:
        """Get base weight for event type"""
        type_key = event_type.value
        return self.config.event_weights.get(type_key, 0.1)
    
    def _calculate_severity_multiplier(self, severity: float) -> float:
        """Calculate severity multiplier"""
        # Linear interpolation between min and max
        min_mult = self.config.severity_multipliers["min"]
        max_mult = self.config.severity_multipliers["max"]
        
        return min_mult + (max_mult - min_mult) * severity
    
    def _calculate_confidence_boost(self, confidence: float) -> float:
        """Calculate confidence boost"""
        if confidence >= 0.9:
            return self.config.confidence_boosts["high_confidence"]
        elif confidence >= 0.7:
            return self.config.confidence_boosts["medium_confidence"]
        else:
            return self.config.confidence_boosts["low_confidence"]
    
    def _categorize_event(self, event_type: EventType) -> str:
        """Categorize event into scoring category"""
        if event_type in [EventType.KD_FLASH, EventType.KD_HARD, EventType.KD_NF,
                          EventType.ROCKED, EventType.STRIKE_HIGHIMPACT]:
            return "damage"
        
        elif event_type in [EventType.TD_LAND, EventType.SUB_ATTEMPT,
                           EventType.CONTROL_START, EventType.CONTROL_END]:
            return "control"
        
        elif event_type in [EventType.STRIKE_SIG, EventType.MOMENTUM_SWING]:
            return "aggression"
        
        elif event_type == EventType.TD_ATTEMPT:
            return "defense"  # Failed TD is defensive win
        
        return "aggression"  # Default
    
    def reset_cumulative_weights(self):
        """Reset cumulative weights (call at round end)"""
        self.cumulative_weights = {
            "damage": 0.0,
            "control": 0.0,
            "aggression": 0.0,
            "defense": 0.0
        }
    
    def get_cumulative_weights(self) -> Dict[str, float]:
        """Get current cumulative weights"""
        return self.cumulative_weights.copy()
