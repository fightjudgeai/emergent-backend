"""
Receipt generation for Scoring Engine V2

Generates explainable "Round Receipts" with top drivers and gate messages.
"""

from typing import List, Dict, Any
from .types import (
    RoundReceipt, 
    PlanBreakdown, 
    ContributionItem, 
    Corner
)


def get_top_drivers(
    contributions: List[ContributionItem],
    winner: str,
    top_n: int = 8
) -> List[ContributionItem]:
    """
    Get top N scoring contributors, prioritizing winner's contributions.
    
    Args:
        contributions: All contribution items from scoring
        winner: "RED", "BLUE", or "DRAW"
        top_n: Number of top items to return (3-8)
        
    Returns:
        List of top contributing items sorted by points
    """
    if not contributions:
        return []
    
    # Sort all contributions by absolute points
    sorted_contribs = sorted(
        contributions,
        key=lambda x: abs(x.points),
        reverse=True
    )
    
    # If we have a winner, prioritize their contributions
    if winner in ["RED", "BLUE"]:
        winner_corner = Corner.RED if winner == "RED" else Corner.BLUE
        
        # Get winner's contributions
        winner_contribs = [c for c in sorted_contribs if c.fighter == winner_corner]
        loser_contribs = [c for c in sorted_contribs if c.fighter != winner_corner]
        
        # Take more from winner (5-6), some from loser (2-3)
        result = winner_contribs[:min(6, len(winner_contribs))]
        remaining = top_n - len(result)
        result.extend(loser_contribs[:remaining])
        
        return result[:top_n]
    else:
        # Draw - take from both equally
        red_contribs = [c for c in sorted_contribs if c.fighter == Corner.RED]
        blue_contribs = [c for c in sorted_contribs if c.fighter == Corner.BLUE]
        
        result = []
        for i in range(top_n // 2):
            if i < len(red_contribs):
                result.append(red_contribs[i])
            if i < len(blue_contribs):
                result.append(blue_contribs[i])
        
        return result[:top_n]


def generate_receipt(
    round_number: int,
    winner: str,
    score_string: str,
    red_breakdown: PlanBreakdown,
    blue_breakdown: PlanBreakdown,
    delta_plan_a: float,
    delta_plan_b: float,
    delta_plan_c: float,
    plan_b_allowed: bool,
    plan_c_allowed: bool,
    red_impact_adv: bool,
    blue_impact_adv: bool,
    impact_reason: str,
    gate_messages: List[str],
    contributions: List[ContributionItem]
) -> RoundReceipt:
    """
    Generate a complete round receipt for explainability.
    
    Args:
        round_number: The round number
        winner: "RED", "BLUE", or "DRAW"
        score_string: e.g., "10-9 RED"
        red_breakdown: Red fighter's plan breakdown
        blue_breakdown: Blue fighter's plan breakdown
        delta_plan_a: Plan A delta
        delta_plan_b: Plan B delta (0 if disabled)
        delta_plan_c: Plan C delta (0 if disabled)
        plan_b_allowed: Was Plan B allowed?
        plan_c_allowed: Was Plan C allowed?
        red_impact_adv: Does red have impact advantage?
        blue_impact_adv: Does blue have impact advantage?
        impact_reason: Reason for impact advantage status
        gate_messages: Messages from gate logic
        contributions: All contribution items
        
    Returns:
        Complete RoundReceipt
    """
    # Get top drivers
    top_drivers = get_top_drivers(contributions, winner)
    
    # Build receipt
    receipt = RoundReceipt(
        round_number=round_number,
        winner=winner,
        score=score_string,
        red_plan_a=red_breakdown.plan_a_total,
        blue_plan_a=blue_breakdown.plan_a_total,
        delta_plan_a=delta_plan_a,
        plan_b_applied=delta_plan_b,
        plan_c_applied=delta_plan_c,
        plan_b_allowed=plan_b_allowed,
        plan_c_allowed=plan_c_allowed,
        red_has_impact_advantage=red_impact_adv,
        blue_has_impact_advantage=blue_impact_adv,
        impact_advantage_reason=impact_reason,
        top_drivers=top_drivers,
        gate_messages=gate_messages,
        red_breakdown=red_breakdown,
        blue_breakdown=blue_breakdown
    )
    
    return receipt


def receipt_to_dict(receipt: RoundReceipt) -> Dict[str, Any]:
    """
    Convert RoundReceipt to dictionary for JSON serialization.
    """
    return {
        "round_number": receipt.round_number,
        "winner": receipt.winner,
        "score": receipt.score,
        "red_plan_a": round(receipt.red_plan_a, 2),
        "blue_plan_a": round(receipt.blue_plan_a, 2),
        "delta_plan_a": round(receipt.delta_plan_a, 2),
        "plan_b_applied": round(receipt.plan_b_applied, 2),
        "plan_c_applied": round(receipt.plan_c_applied, 2),
        "plan_b_allowed": receipt.plan_b_allowed,
        "plan_c_allowed": receipt.plan_c_allowed,
        "red_has_impact_advantage": receipt.red_has_impact_advantage,
        "blue_has_impact_advantage": receipt.blue_has_impact_advantage,
        "impact_advantage_reason": receipt.impact_advantage_reason,
        "top_drivers": [
            {
                "id": d.id,
                "fighter": d.fighter.value,
                "label": d.label,
                "points": round(d.points, 2),
                "category": d.category
            }
            for d in receipt.top_drivers
        ],
        "gate_messages": receipt.gate_messages,
        "red_breakdown": breakdown_to_dict(receipt.red_breakdown),
        "blue_breakdown": breakdown_to_dict(receipt.blue_breakdown)
    }


def breakdown_to_dict(breakdown: PlanBreakdown) -> Dict[str, Any]:
    """
    Convert PlanBreakdown to dictionary for JSON serialization.
    """
    return {
        "striking_score": round(breakdown.striking_score, 2),
        "grappling_score": round(breakdown.grappling_score, 2),
        "control_score": round(breakdown.control_score, 2),
        "impact_score": round(breakdown.impact_score, 2),
        "plan_a_total": round(breakdown.plan_a_total, 2),
        "plan_b_value": round(breakdown.plan_b_value, 2),
        "plan_c_value": round(breakdown.plan_c_value, 2),
        "strike_breakdown": breakdown.strike_breakdown,
        "grappling_breakdown": breakdown.grappling_breakdown,
        "control_breakdown": breakdown.control_breakdown,
        "impact_breakdown": breakdown.impact_breakdown,
        "kd_flash_count": breakdown.kd_flash_count,
        "kd_hard_count": breakdown.kd_hard_count,
        "kd_nf_count": breakdown.kd_nf_count,
        "rocked_count": breakdown.rocked_count,
        "total_kd_count": breakdown.total_kd_count,
        "heavy_strike_count": breakdown.heavy_strike_count,
        "solid_strike_count": breakdown.solid_strike_count,
        "sub_nf_count": breakdown.sub_nf_count,
    }
