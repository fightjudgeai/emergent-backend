"""
Scoring Engine V2 - Main Entry Point

This is the single stable entry function that the rest of the app calls.
Implements UWID Rules-based scoring with Plan A/B/C hierarchy.
"""

from typing import List, Dict, Any, Optional
from .types import (
    RoundScoreResult,
    RoundReceipt,
    PlanBreakdown,
    Verdict,
    Corner
)
from .plan_abc import compute_plan_a, compute_plan_b, compute_plan_c
from .impact import compute_impact_score, check_impact_advantage
from .gates import apply_gates
from .receipt import generate_receipt, receipt_to_dict


def score_round_delta_v2(
    round_number: int,
    events: List[Dict[str, Any]],
    control_windows: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main scoring function - computes round score using UWID rules.
    
    This function is:
    - Deterministic: same inputs => same outputs
    - Pure compute: no DB queries inside
    - O(n) over events
    
    Args:
        round_number: The round number being scored
        events: List of operator events for the round
        control_windows: Optional pre-parsed control windows
        
    Returns:
        Complete scoring result with breakdowns and receipt
    """
    # Handle empty events
    if not events:
        return _empty_result(round_number)
    
    # Normalize events (ensure consistent format)
    normalized_events = normalize_events(events)
    
    # Step 1: Compute Plan A (Effective Striking + Grappling + Control + Impact)
    red_breakdown, blue_breakdown, delta_plan_a, contributions = compute_plan_a(normalized_events)
    
    # Step 2: Check for Impact Advantage
    impact_result = compute_impact_score(normalized_events)
    red_impact_adv, blue_impact_adv, impact_reason = check_impact_advantage(impact_result)
    
    # Step 3: Compute Plan B (if allowed)
    delta_plan_b, plan_b_allowed, plan_b_reason = compute_plan_b(
        normalized_events, delta_plan_a, red_impact_adv, blue_impact_adv
    )
    
    # Step 4: Compute Plan C (if allowed)
    delta_combined = delta_plan_a + delta_plan_b
    delta_plan_c, plan_c_allowed, plan_c_reason = compute_plan_c(
        normalized_events, delta_combined, plan_b_allowed, red_impact_adv, blue_impact_adv
    )
    
    # Update breakdowns with Plan B/C values
    if delta_plan_b != 0:
        if delta_plan_b > 0:
            red_breakdown.plan_b_value = delta_plan_b
        else:
            blue_breakdown.plan_b_value = abs(delta_plan_b)
    
    if delta_plan_c != 0:
        if delta_plan_c > 0:
            red_breakdown.plan_c_value = delta_plan_c
        else:
            blue_breakdown.plan_c_value = abs(delta_plan_c)
    
    # Step 5: Calculate final round delta
    delta_round = delta_plan_a + delta_plan_b + delta_plan_c
    
    # Step 6: Apply gates to determine final score
    red_points, blue_points, winner, gate_messages = apply_gates(
        delta_round,
        red_breakdown,
        blue_breakdown,
        red_impact_adv,
        blue_impact_adv,
        normalized_events
    )
    
    # Build score string
    if winner == "DRAW":
        score_string = "10-10"
    elif winner == "RED":
        score_string = f"{red_points}-{blue_points} RED"
    else:
        score_string = f"{blue_points}-{red_points} BLUE"
    
    # Step 7: Generate receipt
    receipt = generate_receipt(
        round_number=round_number,
        winner=winner,
        score_string=score_string,
        red_breakdown=red_breakdown,
        blue_breakdown=blue_breakdown,
        delta_plan_a=delta_plan_a,
        delta_plan_b=delta_plan_b,
        delta_plan_c=delta_plan_c,
        plan_b_allowed=plan_b_allowed,
        plan_c_allowed=plan_c_allowed,
        red_impact_adv=red_impact_adv,
        blue_impact_adv=blue_impact_adv,
        impact_reason=impact_reason,
        gate_messages=gate_messages,
        contributions=contributions
    )
    
    # Build result
    return {
        "red": breakdown_to_result_dict(red_breakdown),
        "blue": breakdown_to_result_dict(blue_breakdown),
        "deltas": {
            "plan_a": round(delta_plan_a, 2),
            "plan_b": round(delta_plan_b, 2),
            "plan_c": round(delta_plan_c, 2),
            "round": round(delta_round, 2)
        },
        "verdict": {
            "winner": winner,
            "score_string": score_string,
            "red_points": red_points,
            "blue_points": blue_points
        },
        "receipt": receipt_to_dict(receipt),
        
        # Backwards compatibility fields
        "red_points": red_points,
        "blue_points": blue_points,
        "delta": round(delta_round, 2),
        "red_total": round(red_breakdown.plan_a_total, 2),
        "blue_total": round(blue_breakdown.plan_a_total, 2),
        "red_breakdown": red_breakdown.strike_breakdown,
        "blue_breakdown": blue_breakdown.strike_breakdown,
        "total_events": len(events),
        "winner": winner,
        "red_kd": red_breakdown.total_kd_count,
        "blue_kd": blue_breakdown.total_kd_count,
        "red_categories": {
            "striking": round(red_breakdown.striking_score, 2),
            "grappling": round(red_breakdown.grappling_score, 2),
            "control": round(red_breakdown.control_score, 2),
            "impact": round(red_breakdown.impact_score, 2)
        },
        "blue_categories": {
            "striking": round(blue_breakdown.striking_score, 2),
            "grappling": round(blue_breakdown.grappling_score, 2),
            "control": round(blue_breakdown.control_score, 2),
            "impact": round(blue_breakdown.impact_score, 2)
        }
    }


def normalize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize events to consistent format.
    
    Handles:
    - Legacy event type names
    - Missing quality tags (default to SOLID)
    - Missing timestamps
    - Corner normalization
    """
    normalized = []
    
    for event in events:
        norm_event = dict(event)
        
        # Normalize corner
        corner = event.get("corner", "").upper()
        if corner not in ["RED", "BLUE"]:
            fighter = event.get("fighter", "")
            if fighter == "fighter1":
                corner = "RED"
            elif fighter == "fighter2":
                corner = "BLUE"
            else:
                # Skip events without valid corner
                continue
        norm_event["corner"] = corner
        
        # Ensure metadata exists
        if "metadata" not in norm_event or norm_event["metadata"] is None:
            norm_event["metadata"] = {}
        
        # Default quality to SOLID if missing
        metadata = norm_event["metadata"]
        if "quality" not in metadata:
            metadata["quality"] = "SOLID"
        
        # Generate event_id if missing
        if "event_id" not in norm_event:
            norm_event["event_id"] = str(id(event))
        
        normalized.append(norm_event)
    
    return normalized


def breakdown_to_result_dict(breakdown: PlanBreakdown) -> Dict[str, Any]:
    """Convert PlanBreakdown to result dictionary"""
    return {
        "plan_a": round(breakdown.plan_a_total, 2),
        "plan_b": round(breakdown.plan_b_value, 2),
        "plan_c": round(breakdown.plan_c_value, 2),
        "total": round(
            breakdown.plan_a_total + breakdown.plan_b_value + breakdown.plan_c_value, 
            2
        ),
        "striking": round(breakdown.striking_score, 2),
        "grappling": round(breakdown.grappling_score, 2),
        "control": round(breakdown.control_score, 2),
        "impact": round(breakdown.impact_score, 2),
        "kd_count": breakdown.total_kd_count,
        "heavy_strikes": breakdown.heavy_strike_count,
        "solid_strikes": breakdown.solid_strike_count
    }


def _empty_result(round_number: int) -> Dict[str, Any]:
    """Return result for empty round (no events)"""
    empty_breakdown = {
        "plan_a": 0.0,
        "plan_b": 0.0,
        "plan_c": 0.0,
        "total": 0.0,
        "striking": 0.0,
        "grappling": 0.0,
        "control": 0.0,
        "impact": 0.0,
        "kd_count": 0,
        "heavy_strikes": 0,
        "solid_strikes": 0
    }
    
    return {
        "red": empty_breakdown,
        "blue": empty_breakdown,
        "deltas": {
            "plan_a": 0.0,
            "plan_b": 0.0,
            "plan_c": 0.0,
            "round": 0.0
        },
        "verdict": {
            "winner": "DRAW",
            "score_string": "10-10",
            "red_points": 10,
            "blue_points": 10
        },
        "receipt": {
            "round_number": round_number,
            "winner": "DRAW",
            "score": "10-10",
            "red_plan_a": 0.0,
            "blue_plan_a": 0.0,
            "delta_plan_a": 0.0,
            "plan_b_applied": 0.0,
            "plan_c_applied": 0.0,
            "plan_b_allowed": False,
            "plan_c_allowed": False,
            "red_has_impact_advantage": False,
            "blue_has_impact_advantage": False,
            "impact_advantage_reason": "No events",
            "top_drivers": [],
            "gate_messages": ["10-10 Draw: No events logged"],
            "red_breakdown": {},
            "blue_breakdown": {}
        },
        
        # Backwards compatibility
        "red_points": 10,
        "blue_points": 10,
        "delta": 0.0,
        "red_total": 0.0,
        "blue_total": 0.0,
        "red_breakdown": {},
        "blue_breakdown": {},
        "total_events": 0,
        "winner": "DRAW",
        "red_kd": 0,
        "blue_kd": 0,
        "red_categories": {"striking": 0.0, "grappling": 0.0, "control": 0.0, "impact": 0.0},
        "blue_categories": {"striking": 0.0, "grappling": 0.0, "control": 0.0, "impact": 0.0}
    }


# Convenience function matching old API signature
def compute_round_from_events_v2(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Wrapper for backwards compatibility with old compute_round_from_events signature.
    Uses round_number=1 by default since it's not provided.
    """
    return score_round_delta_v2(round_number=1, events=events)
