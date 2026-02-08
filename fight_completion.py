"""
Fight Completion and Archival System
Saves all fight data to database for future reference
"""

from datetime import datetime
from typing import Optional, Dict, List, Any

async def save_completed_fight(db, bout_id: str):
    """
    Save completed fight with all stats to database
    
    Args:
        db: MongoDB database instance
        bout_id: Bout identifier
        
    Returns:
        dict: Saved fight record
    """
    
    # Get bout data
    bout = await db.bouts.find_one({"_id": bout_id})
    if not bout:
        raise ValueError(f"Bout {bout_id} not found")
    
    # Get all events for this bout
    events = await db.events.find({"boutId": bout_id}, {"_id": 0}).to_list(None)
    
    # Get all round scores
    rounds = await db.round_state.find({"boutId": bout_id}, {"_id": 0}).to_list(None)
    
    # Get judge scores
    judge_scores = await db.judge_scores.find({"boutId": bout_id}, {"_id": 0}).to_list(None)
    
    # Calculate final statistics
    fighter1_stats = calculate_fighter_stats(events, 'fighter1')
    fighter2_stats = calculate_fighter_stats(events, 'fighter2')
    
    # Create completed fight record
    completed_fight = {
        "_id": bout_id,
        "bout_id": bout_id,
        "completed_at": datetime.utcnow(),
        
        # Fighter Information
        "fighter1": {
            "name": bout.get('fighter1', 'Fighter 1'),
            "weight_class": bout.get('weightClass', 'Not specified'),
            "corner": "red",
            "stats": fighter1_stats
        },
        "fighter2": {
            "name": bout.get('fighter2', 'Fighter 2'),
            "weight_class": bout.get('weightClass', 'Not specified'),
            "corner": "blue",
            "stats": fighter2_stats
        },
        
        # Event Information
        "event": {
            "event_id": bout.get('eventId'),
            "event_name": bout.get('eventName', 'Unknown Event'),
            "date": bout.get('date', datetime.utcnow())
        },
        
        # Fight Details
        "fight_details": {
            "total_rounds": bout.get('totalRounds', 3),
            "current_round": bout.get('currentRound', 1),
            "status": "completed",
            "method": bout.get('method', 'Decision'),
            "winner": determine_winner(rounds)
        },
        
        # All Events (comprehensive log)
        "events": events,
        
        # Round by Round Scores
        "rounds": rounds,
        
        # Judge Scores
        "judge_scores": judge_scores,
        
        # Metadata
        "metadata": {
            "total_events": len(events),
            "duration_seconds": bout.get('duration'),
            "officials": bout.get('officials', []),
            "location": bout.get('location'),
            "notes": bout.get('notes', [])
        }
    }
    
    # Save to completed_fights collection
    await db.completed_fights.replace_one(
        {"_id": bout_id},
        completed_fight,
        upsert=True
    )
    
    # Update original bout status
    await db.bouts.update_one(
        {"_id": bout_id},
        {
            "$set": {
                "status": "completed",
                "completedAt": datetime.utcnow(),
                "archived": True
            }
        }
    )
    
    return completed_fight


def calculate_fighter_stats(events: List[Dict], fighter: str) -> Dict[str, Any]:
    """Calculate comprehensive stats for a fighter"""
    
    fighter_events = [e for e in events if e.get('fighter') == fighter]
    
    stats = {
        # Striking Stats
        "striking": {
            "total_strikes": 0,
            "significant_strikes": 0,
            "jabs": 0,
            "ss_jabs": 0,
            "crosses": 0,
            "ss_crosses": 0,
            "hooks": 0,
            "ss_hooks": 0,
            "uppercuts": 0,
            "ss_uppercuts": 0,
            "elbows": 0,
            "ss_elbows": 0,
            "knees": 0,
            "ss_knees": 0,
            "kicks": 0,
            "ss_kicks": 0
        },
        
        # Damage Stats
        "damage": {
            "knockdowns": 0,
            "kd_flash": 0,
            "kd_hard": 0,
            "kd_near_finish": 0,
            "rocked": 0
        },
        
        # Grappling Stats
        "grappling": {
            "takedowns_landed": 0,
            "takedowns_stuffed": 0,
            "submission_attempts": 0,
            "sub_light": 0,
            "sub_deep": 0,
            "sub_near_finish": 0,
            "sweeps": 0,
            "guard_passes": 0
        },
        
        # Control Stats
        "control": {
            "ground_top_seconds": 0,
            "ground_back_seconds": 0,
            "cage_control_seconds": 0,
            "total_control_seconds": 0
        },
        
        # Summary
        "summary": {
            "total_events": len(fighter_events),
            "offensive_actions": 0,
            "defensive_actions": 0
        }
    }
    
    # Count events
    for event in fighter_events:
        event_type = event.get('eventType', '')
        metadata = event.get('metadata', {})
        is_significant = metadata.get('significant', False)
        tier = metadata.get('tier')
        duration = metadata.get('duration', 0)
        
        # Striking
        if event_type == 'Jab':
            stats['striking']['jabs'] += 1
            if is_significant:
                stats['striking']['ss_jabs'] += 1
                stats['striking']['significant_strikes'] += 1
            stats['striking']['total_strikes'] += 1
            
        elif event_type == 'Cross':
            stats['striking']['crosses'] += 1
            if is_significant:
                stats['striking']['ss_crosses'] += 1
                stats['striking']['significant_strikes'] += 1
            stats['striking']['total_strikes'] += 1
            
        elif event_type == 'Hook':
            stats['striking']['hooks'] += 1
            if is_significant:
                stats['striking']['ss_hooks'] += 1
                stats['striking']['significant_strikes'] += 1
            stats['striking']['total_strikes'] += 1
            
        elif event_type == 'Uppercut':
            stats['striking']['uppercuts'] += 1
            if is_significant:
                stats['striking']['ss_uppercuts'] += 1
                stats['striking']['significant_strikes'] += 1
            stats['striking']['total_strikes'] += 1
            
        elif event_type == 'Elbow':
            stats['striking']['elbows'] += 1
            if is_significant:
                stats['striking']['ss_elbows'] += 1
                stats['striking']['significant_strikes'] += 1
            stats['striking']['total_strikes'] += 1
            
        elif event_type == 'Knee':
            stats['striking']['knees'] += 1
            if is_significant:
                stats['striking']['ss_knees'] += 1
                stats['striking']['significant_strikes'] += 1
            stats['striking']['total_strikes'] += 1
            
        elif event_type == 'Kick':
            stats['striking']['kicks'] += 1
            if is_significant:
                stats['striking']['ss_kicks'] += 1
                stats['striking']['significant_strikes'] += 1
            stats['striking']['total_strikes'] += 1
            
        # Damage
        elif event_type == 'KD':
            stats['damage']['knockdowns'] += 1
            if tier == 'Flash':
                stats['damage']['kd_flash'] += 1
            elif tier == 'Hard':
                stats['damage']['kd_hard'] += 1
            elif tier == 'Near-Finish':
                stats['damage']['kd_near_finish'] += 1
                
        elif event_type == 'Rocked/Stunned':
            stats['damage']['rocked'] += 1
            
        # Grappling
        elif event_type == 'Takedown Landed':
            stats['grappling']['takedowns_landed'] += 1
            
        elif event_type == 'Takedown Stuffed':
            stats['grappling']['takedowns_stuffed'] += 1
            
        elif event_type == 'Submission Attempt':
            stats['grappling']['submission_attempts'] += 1
            if tier == 'Light':
                stats['grappling']['sub_light'] += 1
            elif tier == 'Deep':
                stats['grappling']['sub_deep'] += 1
            elif tier == 'Near-Finish':
                stats['grappling']['sub_near_finish'] += 1
                
        elif event_type == 'Sweep/Reversal':
            stats['grappling']['sweeps'] += 1
            
        elif event_type == 'Guard Passing':
            stats['grappling']['guard_passes'] += 1
            
        # Control
        elif event_type == 'Ground Top Control':
            stats['control']['ground_top_seconds'] += duration
            stats['control']['total_control_seconds'] += duration
            
        elif event_type == 'Ground Back Control':
            stats['control']['ground_back_seconds'] += duration
            stats['control']['total_control_seconds'] += duration
            
        elif event_type == 'Cage Control Time':
            stats['control']['cage_control_seconds'] += duration
            stats['control']['total_control_seconds'] += duration
    
    # Calculate summary
    stats['summary']['offensive_actions'] = (
        stats['striking']['total_strikes'] +
        stats['damage']['knockdowns'] +
        stats['grappling']['takedowns_landed'] +
        stats['grappling']['submission_attempts']
    )
    
    stats['summary']['defensive_actions'] = (
        stats['grappling']['takedowns_stuffed']
    )
    
    return stats


def determine_winner(rounds: List[Dict]) -> str:
    """Determine fight winner from round scores"""
    if not rounds:
        return "undecided"
    
    fighter1_rounds = sum(1 for r in rounds if r.get('fighter1_score', 0) > r.get('fighter2_score', 0))
    fighter2_rounds = sum(1 for r in rounds if r.get('fighter2_score', 0) > r.get('fighter1_score', 0))
    
    if fighter1_rounds > fighter2_rounds:
        return "fighter1"
    elif fighter2_rounds > fighter1_rounds:
        return "fighter2"
    else:
        return "draw"
