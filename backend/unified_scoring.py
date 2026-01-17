"""
Unified Scoring System - Server-Authoritative
All 4 operator laptops' events combine into ONE unified score.
This is the SINGLE SOURCE OF TRUTH for all scoring computations.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import logging

# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class Corner(str, Enum):
    RED = "RED"
    BLUE = "BLUE"

class Aspect(str, Enum):
    STRIKING = "STRIKING"
    GRAPPLING = "GRAPPLING"

class DeviceRole(str, Enum):
    RED_STRIKING = "RED_STRIKING"
    RED_GRAPPLING = "RED_GRAPPLING"
    BLUE_STRIKING = "BLUE_STRIKING"
    BLUE_GRAPPLING = "BLUE_GRAPPLING"

# Event type weights for delta scoring
EVENT_WEIGHTS = {
    # Knockdowns - highest impact
    "KD": {"category": "striking", "Near-Finish": 100.0, "Hard": 70.0, "Flash": 40.0, "default": 40.0},
    "Rocked/Stunned": {"category": "striking", "value": 30.0},
    
    # Significant strikes
    "Cross": {"category": "striking", "sig": 14.0, "non_sig": 7.0, "default": 10.0},
    "Hook": {"category": "striking", "sig": 14.0, "non_sig": 7.0, "default": 10.0},
    "Uppercut": {"category": "striking", "sig": 14.0, "non_sig": 7.0, "default": 10.0},
    "Elbow": {"category": "striking", "sig": 14.0, "non_sig": 7.0, "default": 10.0},
    "Jab": {"category": "striking", "sig": 10.0, "non_sig": 5.0, "default": 7.0},
    "Knee": {"category": "striking", "sig": 10.0, "non_sig": 5.0, "default": 7.0},
    "Head Kick": {"category": "striking", "sig": 15.0, "non_sig": 8.0, "default": 12.0},
    "Body Kick": {"category": "striking", "sig": 12.0, "non_sig": 6.0, "default": 9.0},
    "Low Kick": {"category": "striking", "sig": 8.0, "non_sig": 4.0, "default": 6.0},
    "Leg Kick": {"category": "striking", "sig": 8.0, "non_sig": 4.0, "default": 6.0},
    
    # Grappling
    "TD": {"category": "grappling", "value": 25.0, "default": 25.0},
    "Takedown": {"category": "grappling", "value": 25.0, "default": 25.0},
    "Takedown Landed": {"category": "grappling", "value": 25.0, "default": 25.0},
    "Submission Attempt": {"category": "grappling", "Near-Finish": 100.0, "Deep": 60.0, "Light": 25.0, "default": 40.0},
    "Sweep/Reversal": {"category": "grappling", "value": 15.0, "default": 15.0},
    "Guard Passing": {"category": "grappling", "value": 10.0, "default": 10.0},
    "Ground Back Control": {"category": "grappling", "value": 20.0, "default": 20.0},
    "Ground Top Control": {"category": "grappling", "value": 15.0, "default": 15.0},
    
    # Other/Control
    "Cage Control Time": {"category": "other", "value": 5.0, "default": 5.0},
    "Takedown Stuffed": {"category": "other", "value": 8.0, "default": 8.0},
    "CTRL_START": {"category": "other", "value": 0.0, "default": 0.0},
    "CTRL_END": {"category": "other", "value": 0.0, "default": 0.0},
}

# =============================================================================
# MODELS
# =============================================================================

class UnifiedEvent(BaseModel):
    """Standard event schema for unified scoring"""
    bout_id: str
    round_number: int
    corner: str  # RED or BLUE
    aspect: str  # STRIKING or GRAPPLING
    event_type: str
    value: float = 0.0
    device_role: str  # RED_STRIKING, RED_GRAPPLING, etc.
    metadata: Optional[Dict[str, Any]] = {}
    created_at: Optional[str] = None
    created_by: Optional[str] = None  # For audit only, NEVER filter by this

class RoundResult(BaseModel):
    """Computed round result - server authoritative"""
    bout_id: str
    round_number: int
    red_points: int  # 10, 9, 8
    blue_points: int  # 10, 9, 8
    delta: float  # Positive = red advantage, negative = blue advantage
    red_total: float  # Raw delta score for red
    blue_total: float  # Raw delta score for blue
    red_breakdown: Dict[str, Any] = {}
    blue_breakdown: Dict[str, Any] = {}
    total_events: int = 0
    computed_at: str = ""
    
class FightResult(BaseModel):
    """Final fight result"""
    bout_id: str
    final_red: int
    final_blue: int
    winner: str  # "RED", "BLUE", or "DRAW"
    winner_name: str = ""
    rounds: List[Dict[str, Any]] = []
    finalized_at: str = ""

# =============================================================================
# SCORING LOGIC
# =============================================================================

def get_event_value(event_type: str, metadata: Dict[str, Any] = None) -> float:
    """Calculate the delta value for an event type"""
    metadata = metadata or {}
    
    if event_type not in EVENT_WEIGHTS:
        return 5.0  # Default value for unknown events
    
    weights = EVENT_WEIGHTS[event_type]
    
    # Check for tier-based values (KD, Submission Attempt)
    tier = metadata.get("tier", "")
    if tier and tier in weights:
        return weights[tier]
    
    # Check for significant flag
    is_sig = metadata.get("significant", True)
    if "sig" in weights and "non_sig" in weights:
        return weights["sig"] if is_sig else weights["non_sig"]
    
    # Return value or default
    return weights.get("value", weights.get("default", 5.0))


def compute_round_from_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute round score from ALL events.
    This is the SINGLE scoring function - no duplicates allowed.
    
    Args:
        events: List of all events for a bout_id + round_number
        
    Returns:
        Round result with scores, delta, breakdown
    """
    if not events:
        return {
            "red_points": 10,
            "blue_points": 10,
            "delta": 0.0,
            "red_total": 0.0,
            "blue_total": 0.0,
            "red_breakdown": {},
            "blue_breakdown": {},
            "total_events": 0,
            "winner": "DRAW"
        }
    
    # Aggregate by corner
    red_total = 0.0
    blue_total = 0.0
    red_breakdown = {}
    blue_breakdown = {}
    red_kd_count = 0
    blue_kd_count = 0
    red_strikes = 0
    blue_strikes = 0
    
    strike_types = ["Jab", "Cross", "Hook", "Uppercut", "Elbow", "Knee", 
                    "Head Kick", "Body Kick", "Low Kick", "Leg Kick"]
    
    for event in events:
        corner = event.get("corner", "").upper()
        if corner not in ["RED", "BLUE"]:
            # Try to infer from fighter field
            fighter = event.get("fighter", "")
            if fighter == "fighter1":
                corner = "RED"
            elif fighter == "fighter2":
                corner = "BLUE"
            else:
                continue
        
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {})
        value = get_event_value(event_type, metadata)
        
        if corner == "RED":
            red_total += value
            red_breakdown[event_type] = red_breakdown.get(event_type, 0) + 1
            if event_type == "KD":
                red_kd_count += 1
            if event_type in strike_types:
                red_strikes += 1
        else:
            blue_total += value
            blue_breakdown[event_type] = blue_breakdown.get(event_type, 0) + 1
            if event_type == "KD":
                blue_kd_count += 1
            if event_type in strike_types:
                blue_strikes += 1
    
    # Calculate delta (positive = red advantage)
    delta = red_total - blue_total
    
    # Determine round score using delta thresholds
    kd_differential = abs(red_kd_count - blue_kd_count)
    strike_differential = abs(red_strikes - blue_strikes)
    allow_extreme = (kd_differential >= 2) or (strike_differential >= 100)
    
    abs_delta = abs(delta)
    
    if abs_delta <= 3.0:
        # Very close - 10-10 draw
        red_points, blue_points = 10, 10
        winner = "DRAW"
    elif abs_delta < 140.0:
        # Standard round - 10-9
        if delta > 0:
            red_points, blue_points = 10, 9
            winner = "RED"
        else:
            red_points, blue_points = 9, 10
            winner = "BLUE"
    elif abs_delta < 200.0:
        # Dominant round
        if delta > 0:
            if allow_extreme:
                red_points, blue_points = 10, 8
            else:
                red_points, blue_points = 10, 9
            winner = "RED"
        else:
            if allow_extreme:
                red_points, blue_points = 8, 10
            else:
                red_points, blue_points = 9, 10
            winner = "BLUE"
    else:
        # Extreme dominance
        if delta > 0:
            if allow_extreme and abs_delta >= 250.0:
                red_points, blue_points = 10, 7
            elif allow_extreme:
                red_points, blue_points = 10, 8
            else:
                red_points, blue_points = 10, 9
            winner = "RED"
        else:
            if allow_extreme and abs_delta >= 250.0:
                red_points, blue_points = 7, 10
            elif allow_extreme:
                red_points, blue_points = 8, 10
            else:
                red_points, blue_points = 9, 10
            winner = "BLUE"
    
    return {
        "red_points": red_points,
        "blue_points": blue_points,
        "delta": round(delta, 2),
        "red_total": round(red_total, 2),
        "blue_total": round(blue_total, 2),
        "red_breakdown": red_breakdown,
        "blue_breakdown": blue_breakdown,
        "total_events": len(events),
        "winner": winner,
        "red_kd": red_kd_count,
        "blue_kd": blue_kd_count
    }


def compute_fight_totals(round_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute final fight totals from all round results.
    
    Args:
        round_results: List of RoundResult dicts
        
    Returns:
        Fight totals with winner
    """
    if not round_results:
        return {
            "final_red": 0,
            "final_blue": 0,
            "winner": "DRAW",
            "total_rounds": 0
        }
    
    final_red = sum(r.get("red_points", 0) for r in round_results)
    final_blue = sum(r.get("blue_points", 0) for r in round_results)
    
    if final_red > final_blue:
        winner = "RED"
    elif final_blue > final_red:
        winner = "BLUE"
    else:
        winner = "DRAW"
    
    return {
        "final_red": final_red,
        "final_blue": final_blue,
        "winner": winner,
        "total_rounds": len(round_results),
        "rounds": round_results
    }
