"""
10-8 and 10-7 gate logic for Scoring Engine V2

These gates enforce strict requirements for dominant round scores.
"""

from typing import Dict, Any, Tuple, List
from .types import PlanBreakdown, Corner
from .weights import GATE_10_8, GATE_10_7
from .impact import count_nf_sequences


def check_10_8_gate(
    winner: str,
    winner_breakdown: PlanBreakdown,
    loser_breakdown: PlanBreakdown,
    plan_a_lead: float,
    events: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Check if a round qualifies for 10-8.
    
    10-8 requires BOTH:
    (i) Impact requirement (must have ONE of):
        - >=3 knockdowns total (flash/hard combined)
        - >=3 KD_HARD + >=2 KD_NF/NF_SUB
        - >=3 SUB_NF + heavy strike differential dominance
    
    AND (ii) Big differential requirement (must have ONE of):
        - Winner's PlanA lead >= +4.0
        - Meaningful strike differential >= +12
        - Heavy strike advantage >= +5
    
    Args:
        winner: "RED" or "BLUE"
        winner_breakdown: PlanBreakdown for winning fighter
        loser_breakdown: PlanBreakdown for losing fighter
        plan_a_lead: Absolute Plan A lead for winner
        events: All events for the round
        
    Returns:
        Tuple of (qualifies, reason)
    """
    # Check impact requirement
    impact_met = False
    impact_reason = ""
    
    total_kd = winner_breakdown.total_kd_count
    kd_hard = winner_breakdown.kd_hard_count
    kd_nf = winner_breakdown.kd_nf_count
    sub_nf = winner_breakdown.sub_nf_count
    
    # Option 1: >=3 knockdowns total
    if total_kd >= GATE_10_8["min_total_kd"]:
        impact_met = True
        impact_reason = f"{total_kd} total knockdowns"
    
    # Option 2: >=3 KD_HARD + >=2 KD_NF/NF_SUB
    elif kd_hard >= GATE_10_8["alt_kd_hard_min"] and (kd_nf + sub_nf) >= GATE_10_8["alt_kd_nf_min"]:
        impact_met = True
        impact_reason = f"{kd_hard} KD_HARD + {kd_nf + sub_nf} near-finishes"
    
    # Option 3: >=3 SUB_NF + heavy strike dominance
    elif sub_nf >= GATE_10_8["alt_sub_nf_min"]:
        heavy_diff = winner_breakdown.heavy_strike_count - loser_breakdown.heavy_strike_count
        if heavy_diff >= GATE_10_8["min_heavy_strike_advantage"]:
            impact_met = True
            impact_reason = f"{sub_nf} near-finish submissions + {heavy_diff} heavy strike advantage"
    
    if not impact_met:
        return False, f"10-8 denied: Impact requirement not met (need {GATE_10_8['min_total_kd']} KDs or equivalent, got {total_kd} KDs)"
    
    # Check differential requirement
    diff_met = False
    diff_reason = ""
    
    # Option 1: Plan A lead >= 4.0
    if plan_a_lead >= GATE_10_8["min_plan_a_lead"]:
        diff_met = True
        diff_reason = f"Plan A lead of {plan_a_lead:.2f}"
    
    # Option 2: SOLID+HEAVY strike differential >= 12
    solid_heavy_diff = winner_breakdown.solid_strike_count - loser_breakdown.solid_strike_count
    if solid_heavy_diff >= GATE_10_8["min_solid_heavy_differential"]:
        diff_met = True
        diff_reason = f"SOLID strike differential of {solid_heavy_diff}"
    
    # Option 3: Heavy strike advantage >= 5
    heavy_diff = winner_breakdown.heavy_strike_count - loser_breakdown.heavy_strike_count
    if heavy_diff >= GATE_10_8["min_heavy_strike_advantage"]:
        diff_met = True
        diff_reason = f"Heavy strike advantage of {heavy_diff}"
    
    if not diff_met:
        return False, f"10-8 denied: Differential requirement not met (need Plan A lead >= {GATE_10_8['min_plan_a_lead']} or strike diff >= {GATE_10_8['min_solid_heavy_differential']})"
    
    return True, f"10-8 awarded: {impact_reason} + {diff_reason}"


def check_10_7_gate(
    winner: str,
    winner_breakdown: PlanBreakdown,
    loser_breakdown: PlanBreakdown,
    plan_a_lead: float,
    events: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Check if a round qualifies for 10-7.
    
    10-7 requires BOTH:
    (i) Severe impact requirement (must have ONE of):
        - >=4 knockdowns total
        - >=3 KD_HARD + >=4 near-finish sequences
        - >=3 "NF + KD in same sequence"
    
    AND (ii) Massive differential requirement (must have ONE of):
        - Plan A lead >= +8.0
        - Meaningful strike differential >= +25
        - Heavy strike advantage >= +10
    
    Args:
        winner: "RED" or "BLUE"
        winner_breakdown: PlanBreakdown for winning fighter
        loser_breakdown: PlanBreakdown for losing fighter
        plan_a_lead: Absolute Plan A lead for winner
        events: All events for the round
        
    Returns:
        Tuple of (qualifies, reason)
    """
    # Check severe impact requirement
    impact_met = False
    impact_reason = ""
    
    total_kd = winner_breakdown.total_kd_count
    kd_hard = winner_breakdown.kd_hard_count
    
    # Count near-finish sequences
    nf_sequences = count_nf_sequences(events, winner)
    
    # Option 1: >=4 knockdowns total
    if total_kd >= GATE_10_7["min_total_kd"]:
        impact_met = True
        impact_reason = f"{total_kd} total knockdowns"
    
    # Option 2: >=3 KD_HARD + >=4 near-finish sequences
    elif kd_hard >= GATE_10_7["alt_kd_hard_min"] and nf_sequences >= GATE_10_7["alt_nf_sequence_min"]:
        impact_met = True
        impact_reason = f"{kd_hard} KD_HARD + {nf_sequences} near-finish sequences"
    
    # Option 3: >=3 NF + KD in same sequence
    elif nf_sequences >= GATE_10_7["alt_nf_kd_sequence_min"]:
        impact_met = True
        impact_reason = f"{nf_sequences} NF+KD sequences"
    
    if not impact_met:
        return False, f"10-7 denied: Severe impact requirement not met (need {GATE_10_7['min_total_kd']} KDs or equivalent)"
    
    # Check massive differential requirement
    diff_met = False
    diff_reason = ""
    
    # Option 1: Plan A lead >= 8.0
    if plan_a_lead >= GATE_10_7["min_plan_a_lead"]:
        diff_met = True
        diff_reason = f"Plan A lead of {plan_a_lead:.2f}"
    
    # Option 2: SOLID strike differential >= 25
    solid_diff = winner_breakdown.solid_strike_count - loser_breakdown.solid_strike_count
    if solid_diff >= GATE_10_7["min_solid_heavy_differential"]:
        diff_met = True
        diff_reason = f"SOLID strike differential of {solid_diff}"
    
    # Option 3: Heavy strike advantage >= 10
    heavy_diff = winner_breakdown.heavy_strike_count - loser_breakdown.heavy_strike_count
    if heavy_diff >= GATE_10_7["min_heavy_strike_advantage"]:
        diff_met = True
        diff_reason = f"Heavy strike advantage of {heavy_diff}"
    
    if not diff_met:
        return False, f"10-7 denied: Massive differential requirement not met (need Plan A lead >= {GATE_10_7['min_plan_a_lead']} or strike diff >= {GATE_10_7['min_solid_heavy_differential']})"
    
    return True, f"10-7 awarded: {impact_reason} + {diff_reason}"


def apply_gates(
    delta_round: float,
    red_breakdown: PlanBreakdown,
    blue_breakdown: PlanBreakdown,
    red_impact_adv: bool,
    blue_impact_adv: bool,
    events: List[Dict[str, Any]]
) -> Tuple[int, int, str, List[str]]:
    """
    Apply gate logic to determine final round score.
    
    Flow:
    1. If |delta| < DRAW_THRESHOLD and no impact advantage: 10-10
    2. Determine winner by delta sign
    3. Check 10-7 gate (if passes, award 10-7)
    4. Check 10-8 gate (if passes, award 10-8)
    5. Default to 10-9
    
    Args:
        delta_round: Final round delta
        red_breakdown: Red fighter's breakdown
        blue_breakdown: Blue fighter's breakdown
        red_impact_adv: Does red have impact advantage?
        blue_impact_adv: Does blue have impact advantage?
        events: All events for the round
        
    Returns:
        Tuple of (red_points, blue_points, winner, gate_messages)
    """
    from .weights import DRAW_THRESHOLD
    
    gate_messages = []
    
    # Check for draw
    if abs(delta_round) < DRAW_THRESHOLD and not red_impact_adv and not blue_impact_adv:
        gate_messages.append(f"10-10 Draw: Delta ({delta_round:.2f}) < threshold ({DRAW_THRESHOLD}) with no impact advantage")
        return 10, 10, "DRAW", gate_messages
    
    # Determine winner
    if delta_round > 0:
        winner = "RED"
        winner_breakdown = red_breakdown
        loser_breakdown = blue_breakdown
    else:
        winner = "BLUE"
        winner_breakdown = blue_breakdown
        loser_breakdown = red_breakdown
    
    plan_a_lead = abs(delta_round)  # Using round delta as proxy for Plan A lead
    
    # Try 10-7 first
    qualifies_10_7, reason_10_7 = check_10_7_gate(
        winner, winner_breakdown, loser_breakdown, plan_a_lead, events
    )
    
    if qualifies_10_7:
        gate_messages.append(reason_10_7)
        if winner == "RED":
            return 10, 7, winner, gate_messages
        else:
            return 7, 10, winner, gate_messages
    else:
        gate_messages.append(reason_10_7)
    
    # Try 10-8
    qualifies_10_8, reason_10_8 = check_10_8_gate(
        winner, winner_breakdown, loser_breakdown, plan_a_lead, events
    )
    
    if qualifies_10_8:
        gate_messages.append(reason_10_8)
        if winner == "RED":
            return 10, 8, winner, gate_messages
        else:
            return 8, 10, winner, gate_messages
    else:
        gate_messages.append(reason_10_8)
    
    # Default to 10-9
    gate_messages.append(f"10-9 {winner}: Standard round victory")
    if winner == "RED":
        return 10, 9, winner, gate_messages
    else:
        return 9, 10, winner, gate_messages
