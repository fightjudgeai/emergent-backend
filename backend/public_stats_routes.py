"""
Public Stats API Routes

Endpoints for public-facing statistics pages.
"""

from fastapi import APIRouter, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Public Stats"])

# Import org filters
try:
    from organization_stats.filters import add_org_filter, get_org_query
except ImportError:
    # Fallback if module not available
    def add_org_filter(query, org_id):
        if org_id:
            query['organization_id'] = org_id
        return query
    
    def get_org_query(org_id=None):
        return {'organization_id': org_id} if org_id else {}

# Database instance (initialized in server.py)
db: Optional[AsyncIOMotorDatabase] = None


def init_public_stats_routes(database: AsyncIOMotorDatabase):
    """Initialize the public stats routes with database"""
    global db
    db = database
    logger.info("✅ Public Stats Routes initialized")


@router.get("/events")
async def get_events(
    sport_type: Optional[str] = Query(None, description="Filter by sport type (mma, boxing, etc.)"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID")
):
    """
    Get all events with fight count and total strikes per card
    
    Query Parameters:
    - sport_type: Filter by sport type (mma, boxing, dirty_boxing, bkfc, karate_combat, other)
    - organization_id: Filter events by organization (optional)
    
    Returns:
    - List of events with:
      - event_name
      - event_date
      - fight_count
      - total_strikes (across all fights in the event)
      - sport_type (if filtered)
      - organization_id (if filtered)
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Build match stage with sport and org filter
        match_stage = {}
        if sport_type:
            match_stage['sport_type'] = sport_type
        if organization_id:
            match_stage['organization_id'] = organization_id
        
        # Aggregate events from fight_stats collection
        # Group by event to get fight counts and total strikes
        pipeline = []
        
        # Add match stage if filtering by org
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        pipeline.extend([
            {
                "$group": {
                    "_id": "$event_name",
                    "fight_count": {"$sum": 1},
                    "total_strikes": {"$sum": "$total_strikes"},
                    "first_seen": {"$min": "$created_at"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "event_name": "$_id",
                    "fight_count": 1,
                    "total_strikes": 1,
                    "event_date": "$first_seen"
                }
            },
            {
                "$sort": {"event_date": -1}
            }
        ]
        
        cursor = db.fight_stats.aggregate(pipeline)
        events = await cursor.to_list(length=None)
        
        # If no events from fight_stats, try to get from fights collection
        if not events:
            # Get all unique bout_ids from events collection
            bout_ids = await db.events.distinct("bout_id")
            
            events_data = []
            for bout_id in bout_ids:
                # Count fights per event (assuming bout_id contains event info)
                # Get event info from first event
                first_event = await db.events.find_one({"bout_id": bout_id})
                
                if first_event:
                    # Count total strikes for this bout
                    total_strikes = await db.events.count_documents({
                        "bout_id": bout_id,
                        "event_type": {"$in": [
                            "Head Kick", "Body Kick", "Low Kick", "Front Kick/Teep",
                            "Elbow", "Knee", "Hook", "Cross", "Jab", "Uppercut"
                        ]}
                    })
                    
                    events_data.append({
                        "event_name": bout_id,
                        "fight_count": 1,  # Each bout_id is one fight
                        "total_strikes": total_strikes,
                        "event_date": first_event.get("timestamp", datetime.now(timezone.utc))
                    })
            
            # Group by event name pattern if possible
            # For now, return individual fights
            events = events_data
        
        return {
            "events": events,
            "count": len(events)
        }
    
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fights/{fight_id}/stats")
async def get_fight_stats(
    fight_id: str,
    sport_type: Optional[str] = Query(None, description="Filter by sport type"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID")
):
    """
    Get detailed fight statistics
    
    Query Parameters:
    - sport_type: Filter by sport type (optional)
    - organization_id: Filter by organization (optional)
    
    Returns:
    - Fight info (fighters, event, etc.)
    - Round-by-round statistics:
      - Significant strikes
      - Takedowns
      - Control time
    - Total fight statistics
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Build query with sport and org filter
        query = {"fight_id": fight_id}
        if sport_type:
            query['sport_type'] = sport_type
        add_org_filter(query, organization_id)
        
        # Get fight_stats for both fighters
        fight_stats_cursor = db.fight_stats.find(query)
        fight_stats_docs = await fight_stats_cursor.to_list(length=None)
        
        if not fight_stats_docs:
            raise HTTPException(status_code=404, detail="Fight not found")
        
        # Get round_stats for all rounds
        round_stats_cursor = db.round_stats.find({"fight_id": fight_id})
        round_stats_docs = await round_stats_cursor.to_list(length=None)
        
        # Organize data by fighter
        fighters_data = {}
        
        for fight_stat in fight_stats_docs:
            fighter_id = fight_stat['fighter_id']
            fighters_data[fighter_id] = {
                "fighter_id": fighter_id,
                "fighter_name": fight_stat.get('fighter_name', fighter_id),
                "total_stats": {
                    "significant_strikes": fight_stat.get('total_significant_strikes', 0),
                    "total_strikes": fight_stat.get('total_strikes', 0),
                    "takedowns": fight_stat.get('total_takedowns', 0),
                    "takedown_attempts": fight_stat.get('total_takedown_attempts', 0),
                    "control_time_seconds": fight_stat.get('total_control_time', 0),
                    "knockdowns": fight_stat.get('total_knockdowns', 0),
                    "submission_attempts": fight_stat.get('total_submission_attempts', 0)
                },
                "rounds": []
            }
        
        # Add round-by-round stats
        for round_stat in round_stats_docs:
            fighter_id = round_stat['fighter_id']
            
            if fighter_id in fighters_data:
                fighters_data[fighter_id]['rounds'].append({
                    "round": round_stat.get('round', round_stat.get('round_num', 1)),
                    "significant_strikes": round_stat.get('significant_strikes', 0),
                    "total_strikes": round_stat.get('total_strikes', 0),
                    "takedowns": round_stat.get('takedowns', 0),
                    "takedown_attempts": round_stat.get('takedown_attempts', 0),
                    "control_time_seconds": round_stat.get('control_time', 0),
                    "knockdowns": round_stat.get('knockdowns', 0),
                    "submission_attempts": round_stat.get('submission_attempts', 0)
                })
        
        # Sort rounds for each fighter
        for fighter_id in fighters_data:
            fighters_data[fighter_id]['rounds'].sort(key=lambda x: x['round'])
        
        return {
            "fight_id": fight_id,
            "fighters": list(fighters_data.values()),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fight stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fighters/{fighter_id}/stats")
async def get_fighter_stats(
    fighter_id: str,
    organization_id: Optional[str] = Query(None, description="Filter by organization ID")
):
    """
    Get career statistics for a fighter
    
    Query Parameters:
    - organization_id: Filter stats by organization (optional)
    
    Returns:
    - Fighter profile info
    - Career metrics:
      - Total fights
      - Win/loss record
      - Average strikes per fight
      - Average takedowns per fight
      - Average control time
    - Per-minute rates
    - Last 5 fights summary (filtered by org if specified)
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Build query with org filter
        query = {"fighter_id": fighter_id}
        add_org_filter(query, organization_id)
        
        # Get career stats
        career_stats = await db.career_stats.find_one(query)
        
        if not career_stats:
            # Try to get fighter info from fighters collection
            fighter = await db.fighters.find_one({"id": fighter_id})
            
            if not fighter:
                raise HTTPException(status_code=404, detail="Fighter not found")
            
            # Return basic fighter info with empty stats
            return {
                "fighter_id": fighter_id,
                "fighter_name": fighter.get('name', fighter_id),
                "career_metrics": {
                    "total_fights": 0,
                    "total_rounds": 0,
                    "avg_strikes_per_fight": 0.0,
                    "avg_takedowns_per_fight": 0.0,
                    "avg_control_time_per_fight": 0.0,
                    "total_knockdowns": 0,
                    "total_submission_attempts": 0
                },
                "per_minute_rates": {
                    "strikes_per_minute": 0.0,
                    "significant_strikes_per_minute": 0.0,
                    "takedowns_per_minute": 0.0
                },
                "last_5_fights": [],
                "record": fighter.get('record', 'N/A')
            }
        
        # Calculate per-minute rates
        total_rounds = career_stats.get('total_rounds', 0)
        total_time_minutes = total_rounds * 5  # Assuming 5-minute rounds
        
        per_minute_rates = {
            "strikes_per_minute": (career_stats.get('total_strikes', 0) / total_time_minutes) if total_time_minutes > 0 else 0.0,
            "significant_strikes_per_minute": (career_stats.get('total_significant_strikes', 0) / total_time_minutes) if total_time_minutes > 0 else 0.0,
            "takedowns_per_minute": (career_stats.get('total_takedowns', 0) / total_time_minutes) if total_time_minutes > 0 else 0.0
        }
        
        # Get last 5 fights
        last_fights_cursor = db.fight_stats.find(
            {"fighter_id": fighter_id}
        ).sort("created_at", -1).limit(5)
        
        last_fights_docs = await last_fights_cursor.to_list(length=5)
        
        last_5_fights = [
            {
                "fight_id": fight.get('fight_id'),
                "event_name": fight.get('event_name', 'Unknown Event'),
                "opponent": fight.get('opponent_name', 'Unknown Opponent'),
                "result": fight.get('result', 'N/A'),
                "significant_strikes": fight.get('total_significant_strikes', 0),
                "takedowns": fight.get('total_takedowns', 0),
                "control_time": fight.get('total_control_time', 0),
                "date": fight.get('created_at', datetime.now(timezone.utc)).isoformat() if isinstance(fight.get('created_at'), datetime) else fight.get('created_at', 'N/A')
            }
            for fight in last_fights_docs
        ]
        
        # Get fighter name
        fighter = await db.fighters.find_one({"id": fighter_id})
        fighter_name = fighter.get('name', fighter_id) if fighter else fighter_id
        
        return {
            "fighter_id": fighter_id,
            "fighter_name": fighter_name,
            "career_metrics": {
                "total_fights": career_stats.get('total_fights', 0),
                "total_rounds": total_rounds,
                "avg_strikes_per_fight": career_stats.get('avg_strikes_per_fight', 0.0),
                "avg_takedowns_per_fight": career_stats.get('avg_takedowns_per_fight', 0.0),
                "avg_control_time_per_fight": career_stats.get('avg_control_time_per_fight', 0.0),
                "total_knockdowns": career_stats.get('total_knockdowns', 0),
                "total_submission_attempts": career_stats.get('total_submission_attempts', 0)
            },
            "per_minute_rates": per_minute_rates,
            "last_5_fights": last_5_fights,
            "record": fighter.get('record', 'N/A') if fighter else 'N/A'
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fighter stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
