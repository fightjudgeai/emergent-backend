"""
Round Replay Engine
Reconstructs a round second-by-second from event logs
"""
from typing import List, Dict, Any
import logging

SCORING_CONFIG = {
    "Jab": {"sig": 0.10, "non_sig": 0.05},
    "Cross": {"sig": 0.14, "non_sig": 0.07},
    "Hook": {"sig": 0.14, "non_sig": 0.07},
    "Uppercut": {"sig": 0.14, "non_sig": 0.07},
    "Elbow": {"sig": 0.14, "non_sig": 0.07},
    "Knee": {"sig": 0.10, "non_sig": 0.05},
    "Head Kick": {"sig": 0.15, "non_sig": 0.08},
    "Body Kick": {"sig": 0.12, "non_sig": 0.06},
    "Low Kick": {"sig": 0.10, "non_sig": 0.05},
    "Front Kick/Teep": {"sig": 0.08, "non_sig": 0.04},
    "Rocked/Stunned": 0.30,
    "KD": {"Flash": 0.40, "Hard": 0.70, "Near-Finish": 1.00},
    "Submission Attempt": {"Light": 0.25, "Deep": 0.60, "Near-Finish": 1.00},
    "Takedown Landed": 0.25,
    "Sweep/Reversal": 0.05,
    "Ground Back Control": {"value_per_sec": 0.012},
    "Ground Top Control": {"value_per_sec": 0.010},
    "Cage Control Time": {"value_per_sec": 0.006},
    "Takedown Stuffed": 0.04
}


async def reconstruct_round_timeline(db, bout_id: str, round_id: int, round_length: int = 300) -> Dict[str, Any]:
    """
    Reconstruct a round second-by-second from event logs
    
    Args:
        db: Database connection
        bout_id: Bout identifier
        round_id: Round number
        round_length: Length of round in seconds (default 300 = 5 min)
    
    Returns:
        Replay JSON object with timeline and summary
    """
    try:
        # Fetch all events in correct sequence order
        events = await db.events_v2.find({
            "bout_id": bout_id,
            "round_id": round_id
        }).sort("sequence_index", 1).to_list(10000)
        
        if not events:
            # Try legacy events collection as fallback
            events = await db.events.find({
                "boutId": bout_id,
                "round": round_id
            }).sort("createdAt", 1).to_list(10000)
        
        # Initialize timeline array
        timeline = []
        
        # Initialize accumulators
        red_damage = 0
        blue_damage = 0
        red_grappling = 0
        blue_grappling = 0
        red_control = 0
        blue_control = 0
        
        # Track control timer states
        control_timers = {
            "fighter1": {"active": False, "start_time": None, "type": None},
            "fighter2": {"active": False, "start_time": None, "type": None}
        }
        
        # Group events by second
        events_by_second = {}
        for event in events:
            # Get timestamp - try both v2 and legacy formats
            timestamp = event.get('client_timestamp_ms', event.get('timestamp', 0))
            if isinstance(timestamp, dict):
                # Legacy format with seconds/milliseconds
                timestamp = timestamp.get('_seconds', 0) * 1000
            
            second = int(timestamp / 1000) if timestamp else 0
            
            if second not in events_by_second:
                events_by_second[second] = []
            events_by_second[second].append(event)
        
        # Build timeline second by second
        for second in range(round_length + 1):
            second_events = events_by_second.get(second, [])
            
            # Process events in this second
            for event in second_events:
                fighter_id = event.get('fighter_id', event.get('fighter', 'fighter1'))
                event_type = event.get('event_type', event.get('event_type', 'Unknown'))
                metadata = event.get('metadata', {})
                
                # Calculate score contribution
                score = 0
                category = "other"
                
                # Striking
                if event_type in ["Jab", "Cross", "Hook", "Uppercut", "Elbow", "Knee", "Head Kick", "Body Kick", "Low Kick", "Front Kick/Teep"]:
                    is_sig = metadata.get('significant', False)
                    config = SCORING_CONFIG.get(event_type, {})
                    if isinstance(config, dict):
                        score = config.get('sig' if is_sig else 'non_sig', 0)
                    category = "damage"
                
                # Damage events
                elif event_type == "Rocked/Stunned":
                    score = SCORING_CONFIG["Rocked/Stunned"]
                    category = "damage"
                
                elif event_type == "KD":
                    tier = metadata.get('tier', 'Flash')
                    score = SCORING_CONFIG["KD"].get(tier, 0.40)
                    category = "damage"
                
                # Grappling
                elif event_type == "Submission Attempt":
                    tier = metadata.get('tier', 'Light')
                    score = SCORING_CONFIG["Submission Attempt"].get(tier, 0.25)
                    category = "grappling"
                
                elif event_type == "Takedown Landed":
                    score = SCORING_CONFIG["Takedown Landed"]
                    category = "grappling"
                
                elif event_type == "Sweep/Reversal":
                    score = SCORING_CONFIG["Sweep/Reversal"]
                    category = "grappling"
                
                # Control events (handle as time-based)
                elif event_type in ["Ground Back Control", "Ground Top Control", "Cage Control Time"]:
                    if metadata.get('type') == 'start':
                        control_timers[fighter_id] = {
                            "active": True,
                            "start_time": second,
                            "type": event_type
                        }
                    elif metadata.get('type') == 'stop' or 'duration' in metadata:
                        duration = metadata.get('duration', 0)
                        config = SCORING_CONFIG.get(event_type, {})
                        if isinstance(config, dict):
                            score = config.get('value_per_sec', 0) * duration
                        category = "control" if "Control" in event_type else "grappling"
                        control_timers[fighter_id] = {"active": False, "start_time": None, "type": None}
                
                elif event_type == "Takedown Stuffed":
                    score = SCORING_CONFIG["Takedown Stuffed"]
                    category = "control"
                
                # Accumulate scores
                if fighter_id == "fighter1":
                    if category == "damage":
                        red_damage += score
                    elif category == "grappling":
                        red_grappling += score
                    elif category == "control":
                        red_control += score
                else:
                    if category == "damage":
                        blue_damage += score
                    elif category == "grappling":
                        blue_grappling += score
                    elif category == "control":
                        blue_control += score
            
            # Calculate active control time up to this second
            for fighter_id, timer in control_timers.items():
                if timer["active"] and timer["start_time"] is not None:
                    duration = second - timer["start_time"]
                    config = SCORING_CONFIG.get(timer["type"], {})
                    if isinstance(config, dict):
                        control_score = config.get('value_per_sec', 0) * duration
                        if fighter_id == "fighter1":
                            red_control = control_score
                        else:
                            blue_control = control_score
            
            # Create timeline entry
            timeline.append({
                "second": second,
                "events": [
                    {
                        "event_type": e.get('event_type', e.get('event_type', 'Unknown')),
                        "fighter_id": e.get('fighter_id', e.get('fighter', 'fighter1')),
                        "metadata": e.get('metadata', {})
                    }
                    for e in second_events
                ],
                "damage_totals": {"red": round(red_damage, 2), "blue": round(blue_damage, 2)},
                "grappling_totals": {"red": round(red_grappling, 2), "blue": round(blue_grappling, 2)},
                "control_totals": {"red": round(red_control, 2), "blue": round(blue_control, 2)}
            })
        
        # Calculate final round summary
        total_red = red_damage + red_grappling + red_control
        total_blue = blue_damage + blue_grappling + blue_control
        score_diff = total_red - total_blue
        
        # Determine winner recommendation
        if abs(score_diff) <= 3.0:
            winner_recommendation = "10-10 (Draw)"
        elif abs(score_diff) < 140.0:
            winner_recommendation = "10-9" if score_diff > 0 else "9-10"
        elif abs(score_diff) < 200.0:
            winner_recommendation = "10-8" if score_diff > 0 else "8-10"
        else:
            winner_recommendation = "10-7" if score_diff > 0 else "7-10"
        
        # Build result
        result = {
            "bout_id": bout_id,
            "round_id": round_id,
            "timeline": timeline,
            "round_summary": {
                "damage_score": {"red": round(red_damage, 2), "blue": round(blue_damage, 2)},
                "grappling_score": {"red": round(red_grappling, 2), "blue": round(blue_grappling, 2)},
                "control_score": {"red": round(red_control, 2), "blue": round(blue_control, 2)},
                "total_score": {"red": round(total_red, 2), "blue": round(total_blue, 2)},
                "score_differential": round(score_diff, 2),
                "winner_recommendation": winner_recommendation
            },
            "event_count": len(events)
        }
        
        return result
        
    except Exception as e:
        logging.error(f"Error reconstructing timeline: {str(e)}")
        raise e
