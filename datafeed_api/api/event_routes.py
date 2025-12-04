"""
Event Normalization API Routes
Endpoints for the normalized event stream and stat engine
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel

from services.event_service import EventService

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instance
event_service: Optional[EventService] = None


def set_event_service(service: EventService):
    """Set the event service instance"""
    global event_service
    event_service = service


class GenerateEventsRequest(BaseModel):
    """Request to generate events from round state"""
    fight_id: str
    round_num: int
    round_state: dict


@router.get("/events/{fight_id}")
async def get_fight_events(
    fight_id: str,
    round: Optional[int] = None,
    event_type: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    Get normalized event stream for a fight
    
    Query params:
    - round: Optional filter for specific round
    - event_type: Optional filter for event type
    
    Returns chronological event stream with UFCstats vocabulary
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        events = event_service.get_fight_events(
            UUID(fight_id),
            round_num=round,
            event_type=event_type
        )
        
        return {
            "fight_id": fight_id,
            "round": round,
            "event_type_filter": event_type,
            "total_events": len(events),
            "events": events
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {fight_id}"
        )
    except Exception as e:
        logger.error(f"Error fetching fight events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/events/{fight_id}/summary")
async def get_event_summary(
    fight_id: str,
    authorization: str = Header(None)
):
    """
    Get event stream summary for a fight
    
    Returns aggregated statistics and event counts
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        summary = event_service.get_event_stream_summary(UUID(fight_id))
        
        return summary
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {fight_id}"
        )
    except Exception as e:
        logger.error(f"Error fetching event summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/events/{fight_id}/round/{round_num}/aggregate")
async def aggregate_round_stats(
    fight_id: str,
    round_num: int,
    authorization: str = Header(None)
):
    """
    Aggregate cumulative stats from normalized events
    
    Returns round statistics calculated from the event stream.
    This is the reverse operation - rebuilding round_state from events.
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        stats = event_service.aggregate_stats_from_events(
            UUID(fight_id),
            round_num
        )
        
        return {
            "fight_id": fight_id,
            "round": round_num,
            "stats": stats
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {fight_id}"
        )
    except Exception as e:
        logger.error(f"Error aggregating stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/events/{fight_id}/round/{round_num}/control-validation")
async def validate_control_time(
    fight_id: str,
    round_num: int,
    authorization: str = Header(None)
):
    """
    Validate control time integrity for a round
    
    Checks:
    - RED + BLUE control ≤ round duration (300 seconds)
    - Paired CTRL_START/CTRL_END events
    - No overlapping control periods
    
    Returns validation result with details
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        validation = event_service.validate_control_overlap(
            UUID(fight_id),
            round_num
        )
        
        return {
            "fight_id": fight_id,
            "round": round_num,
            "validation": validation
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {fight_id}"
        )
    except Exception as e:
        logger.error(f"Error validating control time: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/events/generate-from-round-state")
async def generate_events(
    request: GenerateEventsRequest,
    authorization: str = Header(None)
):
    """
    Generate normalized events from cumulative round_state stats
    
    This is a bridge function for migrating existing data into
    the normalized event model.
    
    Body:
    {
        "fight_id": "uuid",
        "round_num": 1,
        "round_state": {
            "red_sig_strikes": 25,
            "blue_sig_strikes": 18,
            "red_knockdowns": 1,
            "blue_knockdowns": 0,
            "red_control_sec": 120,
            "blue_control_sec": 45
        }
    }
    
    Returns number of events created
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        events_created = event_service.generate_events_from_round_state(
            UUID(request.fight_id),
            request.round_num,
            request.round_state
        )
        
        return {
            "fight_id": request.fight_id,
            "round": request.round_num,
            "events_created": events_created,
            "status": "success" if events_created > 0 else "no_new_events"
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error generating events: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
