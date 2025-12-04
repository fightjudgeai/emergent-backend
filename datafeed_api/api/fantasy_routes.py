"""
Fantasy Scoring API Routes
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends, Query

from models.fantasy_models import (
    FantasyScoringProfile,
    FantasyScoringProfileResponse,
    FantasyFightStatsResponse,
    FantasyLeaderboardResponse,
    CalculateFantasyPointsRequest,
    BulkCalculateFantasyPointsRequest,
    FantasyPointsCalculationResponse,
    FantasyPointsBreakdown
)
from services.fantasy_scoring_service import FantasyScoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fantasy", tags=["Fantasy Scoring"])

# Global service instance (will be injected)
fantasy_service: Optional[FantasyScoringService] = None


def set_fantasy_service(service: FantasyScoringService):
    """Set the fantasy scoring service"""
    global fantasy_service
    fantasy_service = service


# ========================================
# SCORING PROFILES ENDPOINTS
# ========================================

@router.get("/profiles", response_model=List[FantasyScoringProfile])
async def list_scoring_profiles():
    """
    Get all fantasy scoring profiles
    
    Returns list of available scoring profiles with their configurations.
    """
    try:
        profiles = fantasy_service.get_all_profiles()
        return profiles
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scoring profiles"
        )


@router.get("/profiles/{profile_id}", response_model=FantasyScoringProfile)
async def get_scoring_profile(profile_id: str):
    """
    Get a specific fantasy scoring profile
    
    - **profile_id**: Profile ID (e.g., fantasy.basic, fantasy.advanced, sportsbook.pro)
    """
    try:
        profile = fantasy_service.get_profile(profile_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile {profile_id} not found"
            )
        
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scoring profile"
        )


# ========================================
# FANTASY POINTS CALCULATION
# ========================================

@router.post("/calculate", response_model=FantasyPointsCalculationResponse)
async def calculate_fantasy_points(request: CalculateFantasyPointsRequest):
    """
    Calculate fantasy points for a fighter in a fight
    
    Calculates fantasy points based on the specified scoring profile
    and saves the result to the database.
    
    - **fight_id**: UUID of the fight
    - **fighter_id**: UUID of the fighter
    - **profile_id**: Scoring profile to use
    """
    try:
        result = fantasy_service.calculate_and_save(
            request.fight_id,
            request.fighter_id,
            request.profile_id
        )
        
        return FantasyPointsCalculationResponse(
            success=result['success'],
            fighter_id=result['fighter_id'],
            fight_id=result['fight_id'],
            profile_id=result['profile_id'],
            fantasy_points=result['fantasy_points'],
            breakdown=FantasyPointsBreakdown(**result['breakdown'])
        )
    
    except Exception as e:
        logger.error(f"Error calculating fantasy points: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate fantasy points: {str(e)}"
        )


@router.post("/calculate/fight/{fight_id}", response_model=List[FantasyPointsCalculationResponse])
async def calculate_fight_fantasy_points(
    fight_id: UUID,
    profile_ids: List[str] = Query(default=["fantasy.basic", "fantasy.advanced", "sportsbook.pro"])
):
    """
    Calculate fantasy points for all fighters in a fight
    
    Calculates fantasy points for both fighters across specified profiles.
    
    - **fight_id**: UUID of the fight
    - **profile_ids**: List of scoring profile IDs to calculate (default: all 3 profiles)
    """
    try:
        results = fantasy_service.calculate_for_fight(fight_id, profile_ids)
        
        response = []
        for result in results:
            if result.get('success'):
                response.append(FantasyPointsCalculationResponse(
                    success=True,
                    fighter_id=result['fighter_id'],
                    fight_id=result['fight_id'],
                    profile_id=result['profile_id'],
                    fantasy_points=result['fantasy_points'],
                    breakdown=FantasyPointsBreakdown(**result['breakdown'])
                ))
            else:
                response.append(FantasyPointsCalculationResponse(
                    success=False,
                    fighter_id=result['fighter_id'],
                    fight_id=result['fight_id'],
                    profile_id=result['profile_id'],
                    fantasy_points=0,
                    breakdown=FantasyPointsBreakdown(),
                    message=result.get('error', 'Calculation failed')
                ))
        
        return response
    
    except Exception as e:
        logger.error(f"Error calculating fight fantasy points: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate fight fantasy points: {str(e)}"
        )


# ========================================
# FANTASY STATS RETRIEVAL
# ========================================

@router.get("/stats/fight/{fight_id}")
async def get_fight_fantasy_stats(
    fight_id: UUID,
    profile_id: Optional[str] = Query(None, description="Filter by profile ID")
):
    """
    Get fantasy stats for a specific fight
    
    Returns fantasy stats for all fighters in the fight,
    optionally filtered by scoring profile.
    
    - **fight_id**: UUID of the fight
    - **profile_id**: Optional profile ID filter
    """
    try:
        stats = fantasy_service.get_fantasy_stats(
            fight_id=fight_id,
            profile_id=profile_id
        )
        
        return {
            "fight_id": str(fight_id),
            "profile_id": profile_id,
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"Error getting fight fantasy stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fantasy stats"
        )


# ========================================
# STREAMLINED API ENDPOINT
# ========================================

@router.get("/{fight_id}/{profile_id}")
async def get_fantasy_breakdown(fight_id: str, profile_id: str):
    """
    Get fantasy points breakdown for a fight
    
    Streamlined endpoint for real-time fantasy data.
    Returns fantasy points for both fighters with detailed breakdown.
    
    **Path:**
    - `/api/fantasy/{fight_id}/{profile_id}`
    
    **Example:**
    - `/api/fantasy/PFC50-F1/fantasy.basic`
    
    **Response:**
    ```json
    {
      "fight_code": "PFC50-F1",
      "profile_id": "fantasy.basic",
      "fantasy_points": {
        "red": 84.5,
        "blue": 63.2
      },
      "breakdown": {
        "red": {...},
        "blue": {...}
      }
    }
    ```
    """
    try:
        # Get fight by code or ID
        from database.supabase_client import SupabaseDB
        db = fantasy_service.db
        
        fight = db.get_fight_by_code_or_id(fight_id)
        
        if not fight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fight {fight_id} not found"
            )
        
        # Get fantasy stats for both fighters
        stats = fantasy_service.get_fantasy_stats(
            fight_id=UUID(fight['id']),
            profile_id=profile_id
        )
        
        # Build response
        response = {
            "fight_code": fight.get('code', fight_id),
            "fight_id": fight['id'],
            "profile_id": profile_id,
            "fantasy_points": {},
            "breakdown": {}
        }
        
        # Organize by corner
        for stat in stats:
            # Determine corner
            if stat['fighter_id'] == fight['red_fighter_id']:
                corner = 'red'
            elif stat['fighter_id'] == fight['blue_fighter_id']:
                corner = 'blue'
            else:
                continue
            
            response['fantasy_points'][corner] = float(stat['fantasy_points'])
            response['breakdown'][corner] = stat['breakdown']
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fantasy breakdown: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve fantasy breakdown: {str(e)}"
        )


@router.get("/stats/fighter/{fighter_id}")
async def get_fighter_fantasy_stats(
    fighter_id: UUID,
    profile_id: Optional[str] = Query(None, description="Filter by profile ID")
):
    """
    Get fantasy stats for a specific fighter
    
    Returns all fantasy stats for the fighter across all their fights,
    optionally filtered by scoring profile.
    
    - **fighter_id**: UUID of the fighter
    - **profile_id**: Optional profile ID filter
    """
    try:
        stats = fantasy_service.get_fantasy_stats(
            fighter_id=fighter_id,
            profile_id=profile_id
        )
        
        return {
            "fighter_id": str(fighter_id),
            "profile_id": profile_id,
            "stats": stats,
            "total_fights": len(stats),
            "total_points": sum(float(s['fantasy_points']) for s in stats)
        }
    
    except Exception as e:
        logger.error(f"Error getting fighter fantasy stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fantasy stats"
        )


# ========================================
# LEADERBOARDS
# ========================================

@router.get("/leaderboard/{profile_id}", response_model=FantasyLeaderboardResponse)
async def get_fantasy_leaderboard(
    profile_id: str,
    event_code: Optional[str] = Query(None, description="Filter by event code"),
    limit: int = Query(10, ge=1, le=100, description="Number of top fighters to return")
):
    """
    Get fantasy leaderboard for a scoring profile
    
    Returns the top fighters ranked by fantasy points for the specified profile.
    Can be filtered to a specific event.
    
    - **profile_id**: Scoring profile ID
    - **event_code**: Optional event code filter (e.g., PFC50)
    - **limit**: Number of top fighters to return (1-100, default 10)
    """
    try:
        leaderboard = fantasy_service.get_fantasy_leaderboard(
            profile_id=profile_id,
            event_code=event_code,
            limit=limit
        )
        
        return leaderboard
    
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve leaderboard: {str(e)}"
        )


# ========================================
# BULK OPERATIONS
# ========================================

@router.post("/calculate/event/{event_code}")
async def calculate_event_fantasy_points(
    event_code: str,
    profile_ids: List[str] = Query(default=["fantasy.basic", "fantasy.advanced", "sportsbook.pro"])
):
    """
    Calculate fantasy points for all fights in an event
    
    Batch calculation for an entire event across specified profiles.
    
    - **event_code**: Event code (e.g., PFC50)
    - **profile_ids**: List of scoring profile IDs to calculate
    """
    try:
        from database.supabase_client import SupabaseDB
        
        # Get event
        db = fantasy_service.db
        event = db.get_event(event_code)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_code} not found"
            )
        
        # Get all fights for event
        fights = db.get_event_fights(event['id'])
        
        all_results = []
        for fight in fights:
            fight_id = UUID(fight['id'])
            results = fantasy_service.calculate_for_fight(fight_id, profile_ids)
            all_results.extend(results)
        
        successful = sum(1 for r in all_results if r.get('success'))
        failed = len(all_results) - successful
        
        return {
            "event_code": event_code,
            "total_calculations": len(all_results),
            "successful": successful,
            "failed": failed,
            "results": all_results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating event fantasy points: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate event fantasy points: {str(e)}"
        )


# ========================================
# MANUAL RECOMPUTATION
# ========================================

@router.post("/recompute")
async def manual_recompute_fantasy_stats(
    fight_id: Optional[UUID] = Query(None, description="Specific fight ID to recompute"),
    event_code: Optional[str] = Query(None, description="Event code to recompute all fights")
):
    """
    Manually trigger fantasy stats recomputation
    
    Uses the SQL function to recompute fantasy stats for:
    - Specific fight (if fight_id provided)
    - All fights in event (if event_code provided)
    - All fights (if neither provided)
    
    This bypasses the automatic triggers and forces recalculation.
    
    - **fight_id**: Optional fight UUID
    - **event_code**: Optional event code
    """
    try:
        db = fantasy_service.db
        
        # Call the recompute SQL function
        params = {}
        if fight_id:
            params['p_fight_id'] = str(fight_id)
        if event_code:
            params['p_event_code'] = event_code
        
        result = db.client.rpc('recompute_all_fantasy_stats', params).execute()
        
        if result.data:
            successful = sum(1 for r in result.data if r.get('status') == 'success')
            failed = len(result.data) - successful
            
            return {
                "success": True,
                "scope": "fight" if fight_id else ("event" if event_code else "all"),
                "fight_id": str(fight_id) if fight_id else None,
                "event_code": event_code,
                "total_recomputed": len(result.data),
                "successful": successful,
                "failed": failed,
                "details": result.data
            }
        else:
            return {
                "success": True,
                "message": "No fights found to recompute"
            }
    
    except Exception as e:
        logger.error(f"Error in manual recompute: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recompute fantasy stats: {str(e)}"
        )
