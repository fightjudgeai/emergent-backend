"""
Control window aggregation and offense detection for Scoring Engine V2
"""

from typing import List, Dict, Any, Optional, Tuple
from .types import Corner, ControlType, ControlWindow, QualityTag
from .weights import CONTROL_RATES, CONTROL_OFFENSE_MULTIPLIER


def parse_control_windows(
    events: List[Dict[str, Any]],
    round_events: List[Dict[str, Any]]
) -> List[ControlWindow]:
    """
    Parse control windows from events.
    
    Handles two patterns:
    1. Explicit CTRL_START/CTRL_END events with duration
    2. Control events with metadata.duration
    
    Args:
        events: All events for the round
        round_events: All events (for detecting offense during windows)
        
    Returns:
        List of ControlWindow objects
    """
    windows = []
    
    # Track active control timers
    active_timers: Dict[Tuple[str, str], Dict] = {}  # (fighter, control_type) -> start_info
    
    for event in events:
        event_type = event.get("event_type", "")
        corner = event.get("corner", "").upper()
        metadata = event.get("metadata", {}) or {}
        
        # Normalize corner
        if corner not in ["RED", "BLUE"]:
            fighter = event.get("fighter", "")
            corner = "RED" if fighter == "fighter1" else "BLUE" if fighter == "fighter2" else ""
        
        if not corner:
            continue
            
        fighter = Corner.RED if corner == "RED" else Corner.BLUE
        
        # Check for control events with duration in metadata
        if event_type in ["Top Control", "Back Control", "Cage Control", 
                          "Ground Top Control", "Ground Back Control", "Cage Control Time"]:
            duration = metadata.get("duration", 0)
            if duration > 0:
                # Map event type to control type
                if "Back" in event_type:
                    ctrl_type = ControlType.BACK
                elif "Cage" in event_type:
                    ctrl_type = ControlType.CAGE
                else:
                    ctrl_type = ControlType.TOP
                
                # Create window
                timestamp = event.get("timestamp", 0)
                window = ControlWindow(
                    fighter=fighter,
                    control_type=ctrl_type,
                    start_time=timestamp - duration,
                    end_time=timestamp,
                    duration_seconds=duration,
                    has_offense=False,
                    offense_events=[]
                )
                windows.append(window)
        
        # Handle CTRL_START/CTRL_END pattern
        elif event_type == "CTRL_START":
            ctrl_type_str = metadata.get("control_type", "TOP")
            ctrl_type = ControlType[ctrl_type_str] if ctrl_type_str in ["TOP", "BACK", "CAGE"] else ControlType.TOP
            key = (corner, ctrl_type_str)
            active_timers[key] = {
                "fighter": fighter,
                "control_type": ctrl_type,
                "start_time": event.get("timestamp", 0)
            }
        
        elif event_type == "CTRL_END":
            ctrl_type_str = metadata.get("control_type", "TOP")
            key = (corner, ctrl_type_str)
            if key in active_timers:
                start_info = active_timers.pop(key)
                end_time = event.get("timestamp", 0)
                duration = end_time - start_info["start_time"]
                if duration > 0:
                    window = ControlWindow(
                        fighter=start_info["fighter"],
                        control_type=start_info["control_type"],
                        start_time=start_info["start_time"],
                        end_time=end_time,
                        duration_seconds=duration,
                        has_offense=False,
                        offense_events=[]
                    )
                    windows.append(window)
    
    # Detect offense during each window
    windows = detect_offense_in_windows(windows, round_events)
    
    return windows


def detect_offense_in_windows(
    windows: List[ControlWindow],
    all_events: List[Dict[str, Any]]
) -> List[ControlWindow]:
    """
    Detect if meaningful offense occurred during each control window.
    
    Offense = SOLID strike OR any submission attempt by controlling fighter.
    
    Args:
        windows: List of control windows
        all_events: All events in the round
        
    Returns:
        Updated windows with has_offense flag set
    """
    for window in windows:
        offense_events = []
        
        for event in all_events:
            # Get event corner
            corner = event.get("corner", "").upper()
            if corner not in ["RED", "BLUE"]:
                fighter = event.get("fighter", "")
                corner = "RED" if fighter == "fighter1" else "BLUE" if fighter == "fighter2" else ""
            
            if not corner:
                continue
            
            event_fighter = Corner.RED if corner == "RED" else Corner.BLUE
            
            # Only count events from controlling fighter
            if event_fighter != window.fighter:
                continue
            
            # Check if event is within window timeframe
            # If no timestamps, use event ordering (all events during "active" control count)
            event_time = event.get("timestamp", 0)
            if event_time > 0 and window.start_time > 0:
                # Has timestamps - check if in window
                if not (window.start_time <= event_time <= window.end_time):
                    continue
            
            event_type = event.get("event_type", "")
            metadata = event.get("metadata", {}) or {}
            quality = metadata.get("quality", "SOLID")
            
            # Check for SOLID strike
            if is_strike_event(event_type):
                if quality == "SOLID":
                    offense_events.append(event.get("event_id", str(id(event))))
            
            # Check for any submission attempt
            elif event_type == "Submission Attempt":
                offense_events.append(event.get("event_id", str(id(event))))
            
            # Check for ground strikes (GnP)
            elif "Ground" in event_type and "Strike" in event_type:
                if quality == "SOLID":
                    offense_events.append(event.get("event_id", str(id(event))))
        
        window.has_offense = len(offense_events) > 0
        window.offense_events = offense_events
    
    return windows


def is_strike_event(event_type: str) -> bool:
    """Check if event type is a strike"""
    strike_types = {
        "Jab", "Cross", "Hook", "Uppercut", "Overhand",
        "Head Kick", "Body Kick", "Leg Kick", "Low Kick", "Kick",
        "Elbow", "Knee", "Ground Strike"
    }
    return event_type in strike_types


def compute_control_score(windows: List[ControlWindow], plan_c_only: bool = False) -> Dict[str, float]:
    """
    Compute control scores for each fighter.
    
    Control earns HALF points if no offense occurred during window.
    If offense occurred, apply base rate * duration * offense multiplier (1.10x).
    
    Args:
        windows: List of control windows
        plan_c_only: If True, only count CAGE control (for Plan C)
        
    Returns:
        Dict with 'red' and 'blue' control scores
    """
    scores = {"red": 0.0, "blue": 0.0}
    
    # Multiplier for control WITHOUT offense (half value)
    NO_OFFENSE_MULTIPLIER = 0.5
    
    for window in windows:
        # Skip non-cage control if plan_c_only
        if plan_c_only and window.control_type != ControlType.CAGE:
            continue
        
        # Skip cage control in Plan A (only used for Plan C)
        if not plan_c_only and window.control_type == ControlType.CAGE:
            continue
        
        # Calculate score based on offense
        rate = CONTROL_RATES.get(window.control_type.value, 0.02)
        
        if window.has_offense:
            # Full value with offense multiplier
            score = window.duration_seconds * rate * CONTROL_OFFENSE_MULTIPLIER
        else:
            # Half value without offense
            score = window.duration_seconds * rate * NO_OFFENSE_MULTIPLIER
        
        if window.fighter == Corner.RED:
            scores["red"] += score
        else:
            scores["blue"] += score
    
    return scores


def get_control_breakdown(windows: List[ControlWindow]) -> Dict[str, Any]:
    """
    Get detailed control breakdown for receipts.
    
    Returns breakdown per fighter per control type.
    """
    breakdown = {
        "red": {"top": 0.0, "back": 0.0, "cage": 0.0, "total_seconds": 0.0, "windows_with_offense": 0},
        "blue": {"top": 0.0, "back": 0.0, "cage": 0.0, "total_seconds": 0.0, "windows_with_offense": 0}
    }
    
    for window in windows:
        fighter_key = "red" if window.fighter == Corner.RED else "blue"
        ctrl_key = window.control_type.value.lower()
        
        breakdown[fighter_key][ctrl_key] += window.duration_seconds
        breakdown[fighter_key]["total_seconds"] += window.duration_seconds
        
        if window.has_offense:
            breakdown[fighter_key]["windows_with_offense"] += 1
    
    return breakdown
