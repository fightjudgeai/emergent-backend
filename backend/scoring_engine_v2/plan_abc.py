"""
Plan A/B/C computation for Scoring Engine V2
"""

from typing import List, Dict, Any, Tuple
from .types import Corner, PlanBreakdown, ContributionItem, QualityTag
from .weights import (
    STRIKE_BASE_WEIGHTS, 
    QUALITY_MULTIPLIERS, 
    HEAVY_STRIKE_TECHNIQUES,
    GRAPPLING_WEIGHTS,
    SUBMISSION_WEIGHTS,
    PLAN_B_THRESHOLD,
    PLAN_B_CAP,
    PLAN_C_THRESHOLD,
    AGGRESSION_EVENT_VALUE
)
from .leg_damage import LegDamageTracker
from .control_windows import parse_control_windows, compute_control_score, get_control_breakdown
from .impact import compute_impact_score, check_impact_advantage


def compute_striking_score(
    events: List[Dict[str, Any]],
    ldi_tracker: LegDamageTracker
) -> Dict[str, Any]:
    """
    Compute Plan A striking scores for both fighters.
    
    Args:
        events: All events for the round
        ldi_tracker: Leg Damage Index tracker
        
    Returns:
        Dict with scores and breakdowns per fighter
    """
    result = {
        "red": {
            "score": 0.0,
            "heavy_count": 0,
            "solid_count": 0,
            "breakdown": {},
            "contributions": []
        },
        "blue": {
            "score": 0.0,
            "heavy_count": 0,
            "solid_count": 0,
            "breakdown": {},
            "contributions": []
        }
    }
    
    # Map legacy event types to techniques
    technique_map = {
        "Jab": "jab",
        "Cross": "cross",
        "Hook": "hook",
        "Uppercut": "uppercut",
        "Overhand": "overhand",
        "Head Kick": "head_kick",
        "Body Kick": "body_kick",
        "Leg Kick": "leg_kick",
        "Low Kick": "leg_kick",
        "Kick": "head_kick",
        "Elbow": "elbow",
        "Knee": "knee",
        "Ground Strike": "ground_strike",
    }
    
    for event in events:
        event_type = event.get("event_type", "")
        
        # Skip non-strike events
        if event_type not in technique_map:
            continue
        
        corner = event.get("corner", "").upper()
        if corner not in ["RED", "BLUE"]:
            fighter = event.get("fighter", "")
            corner = "RED" if fighter == "fighter1" else "BLUE" if fighter == "fighter2" else ""
        
        if not corner:
            continue
        
        fighter_key = corner.lower()
        metadata = event.get("metadata", {}) or {}
        event_id = event.get("event_id", str(id(event)))
        
        # Get technique and base weight
        technique = technique_map[event_type]
        base_weight = STRIKE_BASE_WEIGHTS.get(technique, 1.0)
        
        # Get quality multiplier (default to SOLID if missing)
        quality = metadata.get("quality", "SOLID")
        quality_mult = QUALITY_MULTIPLIERS.get(quality, 1.0)
        
        # Apply LDI escalation for leg kicks
        ldi_mult = 1.0
        if technique == "leg_kick":
            attacker = Corner.RED if corner == "RED" else Corner.BLUE
            ldi_mult = ldi_tracker.record_leg_kick(attacker)
        
        # Calculate final value
        value = base_weight * quality_mult * ldi_mult
        
        result[fighter_key]["score"] += value
        result[fighter_key]["breakdown"][event_type] = result[fighter_key]["breakdown"].get(event_type, 0) + 1
        
        # Track heavy strikes (SOLID only)
        if quality == "SOLID":
            result[fighter_key]["solid_count"] += 1
            if technique in HEAVY_STRIKE_TECHNIQUES:
                result[fighter_key]["heavy_count"] += 1
        
        # Create contribution
        label = f"{event_type}"
        if quality == "LIGHT":
            label += " (LIGHT)"
        if ldi_mult > 1.0:
            label += f" (LDI x{ldi_mult:.2f})"
        
        result[fighter_key]["contributions"].append(
            ContributionItem(
                id=event_id,
                fighter=Corner.RED if corner == "RED" else Corner.BLUE,
                label=label,
                points=value,
                category="striking"
            )
        )
    
    return result


def compute_grappling_score(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute Plan A grappling scores (takedowns + submission attempts).
    
    Args:
        events: All events for the round
        
    Returns:
        Dict with scores and breakdowns per fighter
    """
    result = {
        "red": {
            "score": 0.0,
            "takedowns": 0,
            "td_stuffed": 0,
            "sub_light": 0,
            "sub_deep": 0,
            "sub_nf": 0,
            "breakdown": {},
            "contributions": []
        },
        "blue": {
            "score": 0.0,
            "takedowns": 0,
            "td_stuffed": 0,
            "sub_light": 0,
            "sub_deep": 0,
            "sub_nf": 0,
            "breakdown": {},
            "contributions": []
        }
    }
    
    grappling_types = {"TD", "Takedown", "Takedown Landed", "Takedown Stuffed", 
                       "Takedown Defended", "Submission Attempt"}
    
    for event in events:
        event_type = event.get("event_type", "")
        
        if event_type not in grappling_types:
            continue
        
        corner = event.get("corner", "").upper()
        if corner not in ["RED", "BLUE"]:
            fighter = event.get("fighter", "")
            corner = "RED" if fighter == "fighter1" else "BLUE" if fighter == "fighter2" else ""
        
        if not corner:
            continue
        
        fighter_key = corner.lower()
        metadata = event.get("metadata", {}) or {}
        event_id = event.get("event_id", str(id(event)))
        
        value = 0.0
        label = event_type
        
        if event_type in ["TD", "Takedown", "Takedown Landed"]:
            value = GRAPPLING_WEIGHTS["takedown"]
            result[fighter_key]["takedowns"] += 1
            label = "Takedown"
        
        elif event_type in ["Takedown Stuffed", "Takedown Defended"]:
            value = GRAPPLING_WEIGHTS["takedown_stuffed"]
            result[fighter_key]["td_stuffed"] += 1
            label = "Takedown Stuffed (defensive)"
        
        elif event_type == "Submission Attempt":
            tier = metadata.get("tier", metadata.get("depth", "Light"))
            
            if tier in ["Near-Finish", "NF", "NEAR_FINISH"]:
                value = SUBMISSION_WEIGHTS["NEAR_FINISH"]
                result[fighter_key]["sub_nf"] += 1
                label = "Submission Attempt (Near-Finish)"
            elif tier in ["Deep", "DEEP"]:
                value = SUBMISSION_WEIGHTS["DEEP"]
                result[fighter_key]["sub_deep"] += 1
                label = "Submission Attempt (Deep)"
            else:
                value = SUBMISSION_WEIGHTS["LIGHT"]
                result[fighter_key]["sub_light"] += 1
                label = "Submission Attempt (Light)"
        
        result[fighter_key]["score"] += value
        result[fighter_key]["breakdown"][event_type] = result[fighter_key]["breakdown"].get(event_type, 0) + 1
        
        result[fighter_key]["contributions"].append(
            ContributionItem(
                id=event_id,
                fighter=Corner.RED if corner == "RED" else Corner.BLUE,
                label=label,
                points=value,
                category="grappling"
            )
        )
    
    return result


def compute_plan_a(
    events: List[Dict[str, Any]]
) -> Tuple[PlanBreakdown, PlanBreakdown, float, List[ContributionItem]]:
    """
    Compute full Plan A for both fighters.
    
    Plan A = Striking + Grappling + Control (with offense) + Impact
    
    Returns:
        Tuple of (red_breakdown, blue_breakdown, delta_plan_a, all_contributions)
    """
    # Initialize tracker
    ldi_tracker = LegDamageTracker()
    
    # Compute each component
    striking = compute_striking_score(events, ldi_tracker)
    grappling = compute_grappling_score(events)
    impact = compute_impact_score(events)
    
    # Parse control windows and compute scores
    control_windows = parse_control_windows(events, events)
    control_scores = compute_control_score(control_windows, plan_c_only=False)
    control_breakdown = get_control_breakdown(control_windows)
    
    # Build breakdowns
    all_contributions = []
    
    red = PlanBreakdown(
        striking_score=striking["red"]["score"],
        grappling_score=grappling["red"]["score"],
        control_score=control_scores["red"],
        impact_score=impact["red"]["score"],
        strike_breakdown=striking["red"]["breakdown"],
        grappling_breakdown=grappling["red"]["breakdown"],
        control_breakdown=control_breakdown["red"],
        impact_breakdown={
            "kd_flash": impact["red"]["kd_flash"],
            "kd_hard": impact["red"]["kd_hard"],
            "kd_nf": impact["red"]["kd_nf"],
            "rocked": impact["red"]["rocked"],
        },
        kd_flash_count=impact["red"]["kd_flash"],
        kd_hard_count=impact["red"]["kd_hard"],
        kd_nf_count=impact["red"]["kd_nf"],
        rocked_count=impact["red"]["rocked"],
        total_kd_count=impact["red"]["total_kd"],
        heavy_strike_count=striking["red"]["heavy_count"],
        solid_strike_count=striking["red"]["solid_count"],
        sub_nf_count=grappling["red"]["sub_nf"],
    )
    red.plan_a_total = red.striking_score + red.grappling_score + red.control_score + red.impact_score
    
    blue = PlanBreakdown(
        striking_score=striking["blue"]["score"],
        grappling_score=grappling["blue"]["score"],
        control_score=control_scores["blue"],
        impact_score=impact["blue"]["score"],
        strike_breakdown=striking["blue"]["breakdown"],
        grappling_breakdown=grappling["blue"]["breakdown"],
        control_breakdown=control_breakdown["blue"],
        impact_breakdown={
            "kd_flash": impact["blue"]["kd_flash"],
            "kd_hard": impact["blue"]["kd_hard"],
            "kd_nf": impact["blue"]["kd_nf"],
            "rocked": impact["blue"]["rocked"],
        },
        kd_flash_count=impact["blue"]["kd_flash"],
        kd_hard_count=impact["blue"]["kd_hard"],
        kd_nf_count=impact["blue"]["kd_nf"],
        rocked_count=impact["blue"]["rocked"],
        total_kd_count=impact["blue"]["total_kd"],
        heavy_strike_count=striking["blue"]["heavy_count"],
        solid_strike_count=striking["blue"]["solid_count"],
        sub_nf_count=grappling["blue"]["sub_nf"],
    )
    blue.plan_a_total = blue.striking_score + blue.grappling_score + blue.control_score + blue.impact_score
    
    # Collect all contributions
    all_contributions.extend(striking["red"]["contributions"])
    all_contributions.extend(striking["blue"]["contributions"])
    all_contributions.extend(grappling["red"]["contributions"])
    all_contributions.extend(grappling["blue"]["contributions"])
    all_contributions.extend(impact["red"]["contributions"])
    all_contributions.extend(impact["blue"]["contributions"])
    
    # Add control contributions
    for window in control_windows:
        if window.has_offense and window.duration_seconds > 0:
            from .weights import CONTROL_RATES, CONTROL_OFFENSE_MULTIPLIER
            rate = CONTROL_RATES.get(window.control_type.value, 0.02)
            points = window.duration_seconds * rate * CONTROL_OFFENSE_MULTIPLIER
            
            all_contributions.append(
                ContributionItem(
                    id=f"ctrl_{window.control_type.value}_{window.start_time}",
                    fighter=window.fighter,
                    label=f"{window.control_type.value} Control w/ offense ({window.duration_seconds:.0f}s)",
                    points=points,
                    category="control"
                )
            )
    
    delta_plan_a = red.plan_a_total - blue.plan_a_total
    
    return red, blue, delta_plan_a, all_contributions


def compute_plan_b(
    events: List[Dict[str, Any]],
    delta_plan_a: float,
    red_impact_adv: bool,
    blue_impact_adv: bool
) -> Tuple[float, bool, str]:
    """
    Compute Plan B (Effective Aggressiveness) if allowed.
    
    Plan B only activates when:
    1. No Impact Advantage exists for either fighter
    2. |delta_plan_a| < PLAN_B_THRESHOLD
    
    Args:
        events: All events for the round
        delta_plan_a: Plan A delta
        red_impact_adv: Does red have impact advantage?
        blue_impact_adv: Does blue have impact advantage?
        
    Returns:
        Tuple of (delta_plan_b, allowed, reason)
    """
    # Check if allowed
    if red_impact_adv or blue_impact_adv:
        return 0.0, False, "Plan B disabled: Impact Advantage present"
    
    if abs(delta_plan_a) >= PLAN_B_THRESHOLD:
        return 0.0, False, f"Plan B disabled: Plan A delta ({delta_plan_a:.2f}) >= threshold ({PLAN_B_THRESHOLD})"
    
    # Plan B is allowed - compute aggression
    # If app tracks aggression events, use them; otherwise return 0
    red_aggr = 0
    blue_aggr = 0
    
    # Look for aggression-specific events (if they exist in the app)
    for event in events:
        event_type = event.get("event_type", "")
        if event_type in ["Aggression", "Pressing", "Forward Movement"]:
            corner = event.get("corner", "").upper()
            if corner not in ["RED", "BLUE"]:
                fighter = event.get("fighter", "")
                corner = "RED" if fighter == "fighter1" else "BLUE" if fighter == "fighter2" else ""
            
            if corner == "RED":
                red_aggr += 1
            elif corner == "BLUE":
                blue_aggr += 1
    
    delta_plan_b = (red_aggr - blue_aggr) * AGGRESSION_EVENT_VALUE
    
    # Cap Plan B
    if delta_plan_b > PLAN_B_CAP:
        delta_plan_b = PLAN_B_CAP
    elif delta_plan_b < -PLAN_B_CAP:
        delta_plan_b = -PLAN_B_CAP
    
    return delta_plan_b, True, "Plan B applied (aggressiveness)"


def compute_plan_c(
    events: List[Dict[str, Any]],
    delta_combined: float,
    plan_b_allowed: bool,
    red_impact_adv: bool,
    blue_impact_adv: bool
) -> Tuple[float, bool, str]:
    """
    Compute Plan C (Cage Control) if allowed.
    
    Plan C only activates when:
    1. Plan B either not allowed or applied and still close
    2. No Impact Advantage exists
    3. |delta_plan_a + delta_plan_b| < PLAN_C_THRESHOLD
    
    Args:
        events: All events for the round  
        delta_combined: Plan A + Plan B delta
        plan_b_allowed: Was Plan B allowed?
        red_impact_adv: Does red have impact advantage?
        blue_impact_adv: Does blue have impact advantage?
        
    Returns:
        Tuple of (delta_plan_c, allowed, reason)
    """
    # Check if allowed
    if red_impact_adv or blue_impact_adv:
        return 0.0, False, "Plan C disabled: Impact Advantage present"
    
    if abs(delta_combined) >= PLAN_C_THRESHOLD:
        return 0.0, False, f"Plan C disabled: Combined delta ({delta_combined:.2f}) >= threshold ({PLAN_C_THRESHOLD})"
    
    # Plan C is allowed - compute cage control only
    control_windows = parse_control_windows(events, events)
    control_scores = compute_control_score(control_windows, plan_c_only=True)
    
    delta_plan_c = control_scores["red"] - control_scores["blue"]
    
    return delta_plan_c, True, "Plan C applied (cage control)"
