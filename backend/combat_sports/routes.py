"""
Combat Sports API Routes

Endpoints for managing sport types and organizations.
"""

from fastapi import APIRouter, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import logging

from combat_sports import SPORT_TYPES
from combat_sports.filters import validate_sport_type, validate_organization

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sports", tags=["Combat Sports"])

# Global instances
db: Optional[AsyncIOMotorDatabase] = None


def init_combat_sports(database: AsyncIOMotorDatabase):
    """Initialize combat sports with database"""
    global db
    db = database
    logger.info("✅ Combat Sports initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Combat Sports",
        "version": "1.0.0",
        "status": "operational",
        "supported_sports": list(SPORT_TYPES.keys())
    }


@router.get("/types")
async def get_sport_types():
    """
    Get all supported sport types
    
    Returns:
    - List of sport types with metadata
    - Supported organizations per sport
    - Scoring categories per sport
    """
    
    return {
        "sport_types": SPORT_TYPES,
        "count": len(SPORT_TYPES)
    }


@router.get("/types/{sport_type}")
async def get_sport_type_details(sport_type: str):
    """
    Get details for a specific sport type
    
    Args:
        sport_type: Sport type (mma, boxing, etc.)
        
    Returns:
        Sport configuration and metadata
    """
    
    if not validate_sport_type(sport_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sport type. Must be one of: {', '.join(SPORT_TYPES.keys())}"
        )
    
    return {
        "sport_type": sport_type,
        **SPORT_TYPES[sport_type]
    }


@router.get("/types/{sport_type}/organizations")
async def get_sport_organizations(sport_type: str):
    """
    Get organizations for a sport type
    
    Args:
        sport_type: Sport type
        
    Returns:
        List of organizations for this sport
    """
    
    if not validate_sport_type(sport_type):
        raise HTTPException(status_code=400, detail="Invalid sport type")
    
    organizations = SPORT_TYPES[sport_type].get('organizations', [])
    
    # Get stats for each organization
    if db is not None:
        org_stats = []
        for org_id in organizations:
            event_count = await db.events.count_documents({
                'sport_type': sport_type,
                'organization_id': org_id
            })
            
            fight_count = await db.fight_stats.count_documents({
                'sport_type': sport_type,
                'organization_id': org_id
            })
            
            org_stats.append({
                'organization_id': org_id,
                'total_events': event_count,
                'total_fights': fight_count
            })
        
        return {
            'sport_type': sport_type,
            'organizations': org_stats,
            'count': len(org_stats)
        }
    
    return {
        'sport_type': sport_type,
        'organizations': [{'organization_id': org} for org in organizations],
        'count': len(organizations)
    }


@router.get("/stats/summary")
async def get_sport_stats_summary(
    sport_type: Optional[str] = Query(None, description="Filter by sport type"),
    organization_id: Optional[str] = Query(None, description="Filter by organization")
):
    """
    Get statistics summary across all sports or filtered by sport/org
    
    Query Parameters:
    - sport_type: Filter by sport (optional)
    - organization_id: Filter by organization (optional)
    
    Returns:
        Statistics summary
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Validate inputs
        if sport_type and not validate_sport_type(sport_type):
            raise HTTPException(status_code=400, detail="Invalid sport type")
        
        if sport_type and organization_id:
            if not validate_organization(sport_type, organization_id):
                raise HTTPException(status_code=400, detail="Invalid organization for this sport")
        
        # Build query
        query = {}
        if sport_type:
            query['sport_type'] = sport_type
        if organization_id:
            query['organization_id'] = organization_id
        
        # Get counts
        total_events = await db.events.count_documents(query)
        total_fights = await db.fight_stats.count_documents(query)
        
        # Get unique fighters
        unique_fighters = await db.events.distinct('fighter_id', query)
        
        # Get breakdown by sport if no filter
        sport_breakdown = []
        if not sport_type:
            for st in SPORT_TYPES.keys():
                st_query = {'sport_type': st}
                if organization_id:
                    st_query['organization_id'] = organization_id
                
                st_events = await db.events.count_documents(st_query)
                st_fights = await db.fight_stats.count_documents(st_query)
                
                if st_events > 0 or st_fights > 0:
                    sport_breakdown.append({
                        'sport_type': st,
                        'sport_name': SPORT_TYPES[st]['name'],
                        'total_events': st_events,
                        'total_fights': st_fights
                    })
        
        return {
            'filters': {
                'sport_type': sport_type,
                'organization_id': organization_id
            },
            'summary': {
                'total_events': total_events,
                'total_fights': total_fights,
                'total_fighters': len(unique_fighters)
            },
            'sport_breakdown': sport_breakdown
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sport stats summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_sport_events(
    sport_type: Optional[str] = Query(None, description="Filter by sport type"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events")
):
    """
    Get events filtered by sport and/or organization
    
    Query Parameters:
    - sport_type: Sport type filter (optional)
    - organization_id: Organization filter (optional)
    - limit: Maximum results
    
    Returns:
        Filtered events
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Build query
        query = {}
        if sport_type:
            if not validate_sport_type(sport_type):
                raise HTTPException(status_code=400, detail="Invalid sport type")
            query['sport_type'] = sport_type
        
        if organization_id:
            query['organization_id'] = organization_id
        
        # Get events
        events = await db.events.find(
            query,
            {'_id': 0}
        ).sort('timestamp', -1).limit(limit).to_list(length=limit)
        
        return {
            'filters': {
                'sport_type': sport_type,
                'organization_id': organization_id
            },
            'count': len(events),
            'events': events
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sport events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fighters")
async def get_sport_fighters(
    sport_type: Optional[str] = Query(None, description="Filter by sport type"),
    organization_id: Optional[str] = Query(None, description="Filter by organization")
):
    """
    Get fighters filtered by sport and/or organization
    
    Query Parameters:
    - sport_type: Sport type filter (optional)
    - organization_id: Organization filter (optional)
    
    Returns:
        Filtered fighters
    """
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Build query
        query = {}
        if sport_type:
            if not validate_sport_type(sport_type):
                raise HTTPException(status_code=400, detail="Invalid sport type")
            query['sport_type'] = sport_type
        
        if organization_id:
            query['organization_id'] = organization_id
        
        # Get unique fighter IDs
        fighter_ids = await db.events.distinct('fighter_id', query)
        
        # Get fighter details
        fighters = await db.fighters.find(
            {'id': {'$in': fighter_ids}},
            {'_id': 0}
        ).to_list(length=1000)
        
        return {
            'filters': {
                'sport_type': sport_type,
                'organization_id': organization_id
            },
            'count': len(fighters),
            'fighters': fighters
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sport fighters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
