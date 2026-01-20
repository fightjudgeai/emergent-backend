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

# Event type weights for percentage-based scoring
# Values are percentages (0.14 = 14%)
EVENT_WEIGHTS = {
    # Category weights
    "CATEGORY_WEIGHTS": {"striking": 0.50, "grappling": 0.40, "other": 0.10},
    
    # Knockdowns - highest impact (striking)
    "KD": {"category": "striking", "Near-Finish": 1.00, "Hard": 0.70, "Flash": 0.40, "default": 0.40},
    "Rocked/Stunned": {"category": "striking", "value": 0.30},
    
    # Strikes (striking) - all use single "value" now
    "Cross": {"category": "striking", "value": 0.14},
    "Hook": {"category": "striking", "value": 0.14},
    "Uppercut": {"category": "striking", "value": 0.14},
    "Elbow": {"category": "striking", "value": 0.14},
    "Kick": {"category": "striking", "value": 0.14},
    "Head Kick": {"category": "striking", "value": 0.14},
    "Body Kick": {"category": "striking", "value": 0.14},
    "Low Kick": {"category": "striking", "value": 0.14},
    "Leg Kick": {"category": "striking", "value": 0.14},
    "Jab": {"category": "striking", "value": 0.10},
    "Knee": {"category": "striking", "value": 0.14},
    "Ground Strike": {"category": "striking", "value": 0.08},
    
    # Grappling
    "Submission Attempt": {"category": "grappling", "Near-Finish": 1.00, "Deep": 0.60, "Light": 0.25, "Standard": 0.25, "default": 0.25},
    "TD": {"category": "grappling", "value": 0.25},
    "Takedown": {"category": "grappling", "value": 0.25},
    "Takedown Landed": {"category": "grappling", "value": 0.25},
    "Sweep/Reversal": {"category": "grappling", "value": 0.05},
    "Guard Passing": {"category": "grappling", "value": 0.05},
    "Back Control": {"category": "grappling", "value_per_sec": 0.012},
    "Top Control": {"category": "grappling", "value_per_sec": 0.010},
    "Cage Control": {"category": "other", "value_per_sec": 0.006},
    "Ground Back Control": {"category": "grappling", "value_per_sec": 0.012},
    "Ground Top Control": {"category": "grappling", "value_per_sec": 0.010},
    
    # Other/Control
    "Cage Control Time": {"category": "other", "value_per_sec": 0.006},
    "Takedown Stuffed": {"category": "other", "value": 0.04},
    "Takedown Defended": {"category": "other", "value": 0.04},
    "CTRL_START": {"category": "other", "value": 0.0},
    "CTRL_END": {"category": "other", "value": 0.0},
}

# Round scoring thresholds (percentage delta)
# Delta = (red_total - blue_total) * 100 where totals are weighted category sums
# Example: 10 jabs (1.0 striking) * 0.5 weight = 0.5 total, delta = 50 if opponent has 0
# To get 10-8, need massive one-sided dominance (multiple near-finishes)
# To get 10-7, need EXTRAORDINARY dominance (should almost never happen)
ROUND_THRESHOLDS = {
    "draw_max": 5.0,        # ≤5% = 10-10
    "standard_max": 200.0,  # 5-200% = 10-9 (vast majority of rounds)
    "dominant_max": 300.0,  # 200-300% = 10-8 (extremely rare - multiple near-finishes required)
    # >300% = 10-7 (practically impossible without actually finishing the fight)
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

def get_event_value(event_type: str, metadata: Dict[str, Any] = None) -> tuple[float, str]:
    """
    Calculate the percentage value for an event type.
    Returns: (value, category)
    """
    metadata = metadata or {}
    
    if event_type not in EVENT_WEIGHTS:
        return 0.05, "other"  # Default 5% for unknown events
    
    weights = EVENT_WEIGHTS[event_type]
    category = weights.get("category", "other")
    
    # Check for tier-based values (KD, Submission Attempt)
    tier = metadata.get("tier", "")
    if tier and tier in weights:
        return weights[tier], category
    
    # Check for duration-based values (control time)
    if "value_per_sec" in weights:
        duration = metadata.get("duration", 0)
        return weights["value_per_sec"] * duration, category
    
    # Return standard value or default
    return weights.get("value", weights.get("default", 0.05)), category


def compute_round_from_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute round score from ALL events using percentage-based scoring.
    
    Args:
        events: List of all events for a bout_id + round_number
        
    Returns:
        Round result with percentage scores, category breakdowns
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
            "red_categories": {"striking": 0.0, "grappling": 0.0, "other": 0.0},
            "blue_categories": {"striking": 0.0, "grappling": 0.0, "other": 0.0},
            "total_events": 0,
            "winner": "DRAW"
        }
    
    # Category accumulators
    red_categories = {"striking": 0.0, "grappling": 0.0, "other": 0.0}
    blue_categories = {"striking": 0.0, "grappling": 0.0, "other": 0.0}
    red_breakdown = {}
    blue_breakdown = {}
    red_kd_count = 0
    blue_kd_count = 0
    
    for event in events:
        corner = event.get("corner", "").upper()
        if corner not in ["RED", "BLUE"]:
            fighter = event.get("fighter", "")
            if fighter == "fighter1":
                corner = "RED"
            elif fighter == "fighter2":
                corner = "BLUE"
            else:
                continue
        
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {})
        value, category = get_event_value(event_type, metadata)
        
        if corner == "RED":
            red_categories[category] = red_categories.get(category, 0.0) + value
            red_breakdown[event_type] = red_breakdown.get(event_type, 0) + 1
            if event_type == "KD":
                red_kd_count += 1
        else:
            blue_categories[category] = blue_categories.get(category, 0.0) + value
            blue_breakdown[event_type] = blue_breakdown.get(event_type, 0) + 1
            if event_type == "KD":
                blue_kd_count += 1
    
    # Apply category weights (50% striking, 40% grappling, 10% other)
    cat_weights = EVENT_WEIGHTS["CATEGORY_WEIGHTS"]
    red_total = (
        red_categories["striking"] * cat_weights["striking"] +
        red_categories["grappling"] * cat_weights["grappling"] +
        red_categories["other"] * cat_weights["other"]
    )
    blue_total = (
        blue_categories["striking"] * cat_weights["striking"] +
        blue_categories["grappling"] * cat_weights["grappling"] +
        blue_categories["other"] * cat_weights["other"]
    )
    
    # Calculate delta as percentage (convert to 0-100 scale for display)
    delta = (red_total - blue_total) * 100
    abs_delta = abs(delta)
    
    # Determine which corner is winning and their KD count
    winning_corner = "RED" if delta > 0 else "BLUE"
    winning_kd_count = red_kd_count if delta > 0 else blue_kd_count
    
    # HARD REQUIREMENT: 10-8 and 10-7 are IMPOSSIBLE without 2+ knockdowns
    # Even with massive delta, must have knockdowns to score 10-8 or 10-7
    min_kd_for_10_8 = 2  # Must have at least 2 KDs for 10-8
    min_kd_for_10_7 = 3  # Must have at least 3 KDs for 10-7
    
    # Determine round score
    if abs_delta <= ROUND_THRESHOLDS["draw_max"]:
        # Very close - 10-10 draw
        red_points, blue_points = 10, 10
        winner = "DRAW"
    elif abs_delta <= ROUND_THRESHOLDS["standard_max"]:
        # Standard round - 10-9
        if delta > 0:
            red_points, blue_points = 10, 9
            winner = "RED"
        else:
            red_points, blue_points = 9, 10
            winner = "BLUE"
    elif abs_delta <= ROUND_THRESHOLDS["dominant_max"]:
        # Potentially dominant round - but REQUIRES 2+ KDs for 10-8
        if winning_kd_count >= min_kd_for_10_8:
            # Has enough KDs - can be 10-8
            if delta > 0:
                red_points, blue_points = 10, 8
                winner = "RED"
            else:
                red_points, blue_points = 8, 10
                winner = "BLUE"
        else:
            # Not enough KDs - capped at 10-9 regardless of delta
            if delta > 0:
                red_points, blue_points = 10, 9
                winner = "RED"
            else:
                red_points, blue_points = 9, 10
                winner = "BLUE"
    else:
        # Extreme dominance - but REQUIRES 3+ KDs for 10-7, 2+ for 10-8
        if winning_kd_count >= min_kd_for_10_7:
            # Has enough KDs for 10-7
            if delta > 0:
                red_points, blue_points = 10, 7
                winner = "RED"
            else:
                red_points, blue_points = 7, 10
                winner = "BLUE"
        elif winning_kd_count >= min_kd_for_10_8:
            # Has enough KDs for 10-8 but not 10-7
            if delta > 0:
                red_points, blue_points = 10, 8
                winner = "RED"
            else:
                red_points, blue_points = 8, 10
                winner = "BLUE"
        else:
            # Not enough KDs - capped at 10-9 regardless of delta
            if delta > 0:
                red_points, blue_points = 10, 9
                winner = "RED"
            else:
                red_points, blue_points = 9, 10
                winner = "BLUE"
    
    return {
        "red_points": red_points,
        "blue_points": blue_points,
        "delta": round(delta, 2),
        "red_total": round(red_total * 100, 2),
        "blue_total": round(blue_total * 100, 2),
        "red_breakdown": red_breakdown,
        "blue_breakdown": blue_breakdown,
        "red_categories": {k: round(v * 100, 2) for k, v in red_categories.items()},
        "blue_categories": {k: round(v * 100, 2) for k, v in blue_categories.items()},
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
