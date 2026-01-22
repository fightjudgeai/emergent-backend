"""
Impact scoring and Impact Advantage detection for Scoring Engine V2
"""

from typing import List, Dict, Any, Tuple
from .types import Corner, KnockdownTier, ContributionItem
from .weights import IMPACT_VALUES, NF_SEQUENCE_WINDOW_SECONDS


def compute_impact_score(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute impact scores and counts for each fighter.
    
    Args:
        events: All events for the round
        
    Returns:
        Dict with scores and counts per fighter
    """
    result = {
        "red": {
            "score": 0.0,
            "kd_flash": 0,
            "kd_hard": 0,
            "kd_nf": 0,
            "rocked": 0,
            "total_kd": 0,
            "contributions": []
        },
        "blue": {
            "score": 0.0,
            "kd_flash": 0,
            "kd_hard": 0,
            "kd_nf": 0,
            "rocked": 0,
            "total_kd": 0,
            "contributions": []
        }
    }
    
    for event in events:
        event_type = event.get("event_type", "")
        
        # Only process impact events
        if event_type not in ["KD", "Rocked/Stunned", "Rocked", "ROCKED"]:
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
        
        if event_type == "KD":
            tier = metadata.get("tier", "Flash")
            
            if tier in ["Near-Finish", "NF"]:
                value = IMPACT_VALUES["KD_NF"]
                result[fighter_key]["kd_nf"] += 1
                label = "KD_NF (Near-Finish Knockdown)"
            elif tier == "Hard":
                value = IMPACT_VALUES["KD_HARD"]
                result[fighter_key]["kd_hard"] += 1
                label = "KD_HARD (Hard Knockdown)"
            else:  # Flash or default
                value = IMPACT_VALUES["KD_FLASH"]
                result[fighter_key]["kd_flash"] += 1
                label = "KD_FLASH (Flash Knockdown)"
            
            result[fighter_key]["total_kd"] += 1
            result[fighter_key]["score"] += value
            result[fighter_key]["contributions"].append(
                ContributionItem(
                    id=event_id,
                    fighter=Corner.RED if corner == "RED" else Corner.BLUE,
                    label=label,
                    points=value,
                    category="impact"
                )
            )
        
        elif event_type in ["Rocked/Stunned", "Rocked", "ROCKED"]:
            value = IMPACT_VALUES["ROCKED"]
            result[fighter_key]["rocked"] += 1
            result[fighter_key]["score"] += value
            result[fighter_key]["contributions"].append(
                ContributionItem(
                    id=event_id,
                    fighter=Corner.RED if corner == "RED" else Corner.BLUE,
                    label="ROCKED (Stunned/Hurt)",
                    points=value,
                    category="impact"
                )
            )
    
    return result


def check_impact_advantage(impact_result: Dict[str, Any]) -> Tuple[bool, bool, str]:
    """
    Check if either fighter has Impact Advantage.
    
    Impact Advantage exists if ANY:
    - >=1 KD_HARD
    - >=1 KD_NF
    - >=2 ROCKED
    - KD_FLASH count advantage >= 2
    
    Args:
        impact_result: Result from compute_impact_score()
        
    Returns:
        Tuple of (red_has_advantage, blue_has_advantage, reason)
    """
    red = impact_result["red"]
    blue = impact_result["blue"]
    
    red_advantage = False
    blue_advantage = False
    reasons = []
    
    # Check KD_HARD
    if red["kd_hard"] >= 1:
        red_advantage = True
        reasons.append(f"RED has {red['kd_hard']} KD_HARD")
    if blue["kd_hard"] >= 1:
        blue_advantage = True
        reasons.append(f"BLUE has {blue['kd_hard']} KD_HARD")
    
    # Check KD_NF
    if red["kd_nf"] >= 1:
        red_advantage = True
        reasons.append(f"RED has {red['kd_nf']} KD_NF")
    if blue["kd_nf"] >= 1:
        blue_advantage = True
        reasons.append(f"BLUE has {blue['kd_nf']} KD_NF")
    
    # Check ROCKED >= 2
    if red["rocked"] >= 2:
        red_advantage = True
        reasons.append(f"RED has {red['rocked']} ROCKED")
    if blue["rocked"] >= 2:
        blue_advantage = True
        reasons.append(f"BLUE has {blue['rocked']} ROCKED")
    
    # Check KD_FLASH advantage >= 2
    flash_diff = red["kd_flash"] - blue["kd_flash"]
    if flash_diff >= 2:
        red_advantage = True
        reasons.append(f"RED has KD_FLASH advantage of {flash_diff}")
    elif flash_diff <= -2:
        blue_advantage = True
        reasons.append(f"BLUE has KD_FLASH advantage of {-flash_diff}")
    
    reason_str = "; ".join(reasons) if reasons else "No impact advantage"
    
    return red_advantage, blue_advantage, reason_str


def count_nf_sequences(events: List[Dict[str, Any]], fighter: str) -> int:
    """
    Count near-finish sequences for a fighter.
    
    A sequence is:
    - KD_NF counts as 1 near-finish
    - Sub NEAR_FINISH counts as 1 near-finish
    - KD events within NF_SEQUENCE_WINDOW_SECONDS count as a sequence
    
    Args:
        events: All events for the round
        fighter: "RED" or "BLUE"
        
    Returns:
        Count of near-finish sequences
    """
    nf_count = 0
    kd_events = []
    
    for event in events:
        corner = event.get("corner", "").upper()
        if corner not in ["RED", "BLUE"]:
            f = event.get("fighter", "")
            corner = "RED" if f == "fighter1" else "BLUE" if f == "fighter2" else ""
        
        if corner != fighter:
            continue
        
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {}) or {}
        timestamp = event.get("timestamp", 0)
        
        if event_type == "KD":
            tier = metadata.get("tier", "Flash")
            if tier in ["Near-Finish", "NF"]:
                nf_count += 1
            kd_events.append({"tier": tier, "timestamp": timestamp})
        
        elif event_type == "Submission Attempt":
            depth = metadata.get("tier", metadata.get("depth", "Light"))
            if depth in ["Near-Finish", "NF", "NEAR_FINISH"]:
                nf_count += 1
    
    # Count KD sequences (multiple KDs within window)
    # Sort by timestamp
    kd_events.sort(key=lambda x: x.get("timestamp", 0))
    
    # Count sequences
    if len(kd_events) >= 2:
        for i in range(len(kd_events) - 1):
            t1 = kd_events[i].get("timestamp", 0)
            t2 = kd_events[i + 1].get("timestamp", 0)
            if t1 > 0 and t2 > 0:
                if t2 - t1 <= NF_SEQUENCE_WINDOW_SECONDS:
                    # This is a sequence - add bonus
                    nf_count += 1
    
    return nf_count
