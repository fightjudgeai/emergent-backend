"""
Leg Damage Index (LDI) tracking for scoring engine V2
"""

from typing import Dict
from .types import Corner, StrikeEvent
from .weights import LDI_INCREMENT, get_ldi_multiplier


class LegDamageTracker:
    """
    Tracks Leg Damage Index (LDI) per fighter per round.
    
    Each leg kick landed against a fighter increases their opponent's
    LDI multiplier for subsequent leg kicks.
    """
    
    def __init__(self):
        # LDI[fighter] = damage received by that fighter from leg kicks
        # Higher LDI = opponent's subsequent leg kicks do more damage
        self._ldi: Dict[Corner, float] = {
            Corner.RED: 0.0,
            Corner.BLUE: 0.0,
        }
    
    def reset(self):
        """Reset LDI for new round"""
        self._ldi = {Corner.RED: 0.0, Corner.BLUE: 0.0}
    
    def get_ldi(self, target: Corner) -> float:
        """Get current LDI for a target fighter"""
        return self._ldi.get(target, 0.0)
    
    def record_leg_kick(self, attacker: Corner) -> float:
        """
        Record a leg kick and return the multiplier to apply.
        
        Args:
            attacker: The fighter who landed the leg kick
            
        Returns:
            Multiplier to apply to this leg kick's base value
        """
        # Determine target (opponent)
        target = Corner.BLUE if attacker == Corner.RED else Corner.RED
        
        # Get current LDI before incrementing
        current_ldi = self._ldi[target]
        
        # Calculate multiplier based on current LDI
        multiplier = get_ldi_multiplier(current_ldi)
        
        # Increment LDI for future kicks
        self._ldi[target] += LDI_INCREMENT
        
        return multiplier
    
    def get_state(self) -> Dict[str, float]:
        """Get current LDI state for receipts"""
        return {
            "red_ldi_received": self._ldi[Corner.RED],
            "blue_ldi_received": self._ldi[Corner.BLUE],
        }


def apply_leg_kick_escalation(
    strikes: list,
    tracker: LegDamageTracker
) -> Dict[str, float]:
    """
    Process strikes in order and apply LDI escalation to leg kicks.
    
    Args:
        strikes: List of strike events (must include technique and fighter)
        tracker: LegDamageTracker instance
        
    Returns:
        Dict mapping event_id to multiplier applied (for receipts)
    """
    multipliers = {}
    
    for strike in strikes:
        technique = strike.get("technique", "").lower()
        fighter_str = strike.get("fighter", "")
        event_id = strike.get("event_id", str(id(strike)))
        
        # Normalize fighter to Corner enum
        if fighter_str in ["RED", "fighter1"]:
            fighter = Corner.RED
        elif fighter_str in ["BLUE", "fighter2"]:
            fighter = Corner.BLUE
        else:
            continue
        
        if technique == "leg_kick":
            mult = tracker.record_leg_kick(fighter)
            multipliers[event_id] = mult
        else:
            multipliers[event_id] = 1.0
    
    return multipliers
