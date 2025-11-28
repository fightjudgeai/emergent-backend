"""
Organization Stats API Routes

Endpoints for managing and querying organization-specific statistics.
"""

from fastapi import APIRouter, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations", tags=["Organization Stats"])

# Global instances
db: Optional[AsyncIOMotorDatabase] = None


def init_organization_stats(database: AsyncIOMotorDatabase):
    """Initialize organization stats with database"""
    global db
    db = database
    logger.info("✅ Organization Stats initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Organization Stats",
        "version": "1.0.0",
        "status": "operational"
    }


@router.get("/list")
async def list_organizations():
    """
    List all organizations with stats
    
    Returns:
    - List of organizations with event/fight counts
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Get unique organization IDs from events
        org_ids = await db.events.distinct("organization_id")
        
        organizations = []
        
        for org_id in org_ids:
            if not org_id:
                continue
            
            # Count events per org
            event_count = await db.events.count_documents({"organization_id": org_id})
            
            # Count fights per org
            fight_count = await db.fight_stats.count_documents({"organization_id": org_id})
            
            # Get fighters per org
            fighter_ids = await db.events.distinct("fighter_id", {"organization_id": org_id})
            
            organizations.append({
                "organization_id": org_id,
                "total_events": event_count,
                "total_fights": fight_count,
                "total_fighters": len(fighter_ids)
            })
        
        return {
            "count": len(organizations),
            "organizations": organizations
        }
    
    except Exception as e:
        logger.error(f"Error listing organizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{organization_id}/summary")
async def get_organization_summary(organization_id: str):
    """
    Get summary statistics for an organization
    
    Args:
        organization_id: Organization ID
        
    Returns:
        Complete statistics summary for the organization
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Event counts
        total_events = await db.events.count_documents({"organization_id": organization_id})
        
        # Fight counts
        total_fights = await db.fight_stats.count_documents({"organization_id": organization_id})
        
        # Fighter counts
        unique_fighters = await db.events.distinct("fighter_id", {"organization_id": organization_id})
        
        # Recent events
        recent_events = await db.events.find(
            {"organization_id": organization_id}
        ).sort("timestamp", -1).limit(10).to_list(length=10)
        
        # Top fighters by event count
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            {"$group": {
                "_id": "$fighter_id",
                "event_count": {"$sum": 1}
            }},
            {"$sort": {"event_count": -1}},
            {"$limit": 10}
        ]
        
        top_fighters = await db.events.aggregate(pipeline).to_list(length=10)
        
        return {
            "organization_id": organization_id,
            "summary": {
                "total_events": total_events,
                "total_fights": total_fights,
                "total_fighters": len(unique_fighters)
            },
            "recent_events": [
                {
                    "fighter_id": e.get("fighter_id"),
                    "event_type": e.get("event_type"),
                    "round": e.get("round"),
                    "timestamp": e.get("timestamp").isoformat() if e.get("timestamp") else None
                }
                for e in recent_events[:5]
            ],
            "top_fighters": [
                {
                    "fighter_id": f["_id"],
                    "event_count": f["event_count"]
                }
                for f in top_fighters
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting organization summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{organization_id}/events")
async def get_organization_events(
    organization_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return")
):
    """
    Get events for a specific organization
    
    Args:
        organization_id: Organization ID
        limit: Maximum results
        
    Returns:
        List of events for the organization
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        events = await db.events.find(
            {"organization_id": organization_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return {
            "organization_id": organization_id,
            "count": len(events),
            "events": events
        }
    
    except Exception as e:
        logger.error(f"Error getting organization events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{organization_id}/fighters")
async def get_organization_fighters(organization_id: str):
    """
    Get all fighters for an organization
    
    Args:
        organization_id: Organization ID
        
    Returns:
        List of fighters who have competed in this organization
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Get unique fighter IDs
        fighter_ids = await db.events.distinct("fighter_id", {"organization_id": organization_id})
        
        # Get fighter details
        fighters = await db.fighters.find(
            {"id": {"$in": fighter_ids}},
            {"_id": 0}
        ).to_list(length=1000)
        
        return {
            "organization_id": organization_id,
            "count": len(fighters),
            "fighters": fighters
        }
    
    except Exception as e:
        logger.error(f"Error getting organization fighters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
