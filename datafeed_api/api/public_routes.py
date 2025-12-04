"""
Public Stats API Routes
UFCstats-style public fight statistics endpoint (no auth required)
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import Optional

from services.public_stats_service import PublicStatsService

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instance
public_stats_service: Optional[PublicStatsService] = None


def set_public_stats_service(service: PublicStatsService):
    """Set the public stats service instance"""
    global public_stats_service
    public_stats_service = service


@router.get("/public/fight/{fight_id}")
async def get_public_fight_stats(fight_id: str):
    """
    Get public fight statistics in UFCstats format
    
    This endpoint is PUBLIC - no authentication required.
    
    Args:
        fight_id: Fight ID (UUID) or fight code (e.g., "UFC309_JONES_MIOCIC")
    
    Returns:
        Fight statistics in UFCstats format with round-by-round breakdown
        
    Example Response:
    {
        "fight": {
            "event": "PFC 50",
            "weight_class": "Welterweight",
            "rounds": 3,
            "result": "DEC"
        },
        "fighters": {
            "red": {"name": "John Doe", "winner": true},
            "blue": {"name": "Mike Smith", "winner": false}
        },
        "rounds": [
            {
                "round": 1,
                "red": {
                    "sig": "24/55",
                    "total": "39/88",
                    "td": "2/5",
                    "sub": 1,
                    "kd": 1,
                    "ctrl": "1:11",
                    "acc_sig": 0.44,
                    "acc_td": 0.40
                },
                "blue": {
                    "sig": "15/44",
                    "total": "22/67",
                    "td": "0/2",
                    "sub": 0,
                    "kd": 0,
                    "ctrl": "0:19",
                    "acc_sig": 0.34,
                    "acc_td": 0.00
                }
            }
        ]
    }
    
    Notes:
    - Strike attempts are currently estimated from landed strikes
    - Takedown and submission data will show 0/0 until event system is active
    - Use the event normalization system for accurate attempt counts
    """
    try:
        stats = public_stats_service.get_fight_stats(fight_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fight not found: {fight_id}"
            )
        
        # Add metadata note about data limitations
        stats['_note'] = (
            "Strike attempts are estimated. Takedown/submission data "
            "requires event normalization system (migration 005)."
        )
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in public fight stats endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/public/fights")
async def list_public_fights(
    event_code: Optional[str] = None,
    limit: int = 50
):
    """
    List recent fights with basic info (public endpoint)
    
    Query params:
    - event_code: Optional filter by event code
    - limit: Maximum number of fights to return (default 50)
    
    Returns:
        List of fights with basic metadata
    """
    try:
        # This would need implementation in the database client
        # For now, return a placeholder
        return {
            "fights": [],
            "total": 0,
            "note": "Fight listing endpoint - implementation pending"
        }
    
    except Exception as e:
        logger.error(f"Error listing public fights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
