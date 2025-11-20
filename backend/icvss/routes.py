"""
ICVSS FastAPI Routes
REST API + WebSocket endpoints
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from typing import Optional, List
import logging
from datetime import datetime, timezone

from .models import CVEvent, ICVSSRound, ScoreRequest, ScoreResponse, EventType
from .round_engine import RoundEngine
from .websocket_manager import ws_manager
from .event_processor import EventNormalizer

logger = logging.getLogger(__name__)

# Create ICVSS router
icvss_router = APIRouter(prefix="/icvss", tags=["ICVSS"])

# Global round engine (will be initialized with db)
round_engine: Optional[RoundEngine] = None


def get_round_engine():
    """Dependency to get round engine"""
    if round_engine is None:
        raise HTTPException(status_code=500, detail="ICVSS not initialized")
    return round_engine


# ============================================================================
# ROUND LIFECYCLE ENDPOINTS
# ============================================================================

@icvss_router.post("/round/open", response_model=ICVSSRound)
async def open_round(bout_id: str, round_num: int, engine: RoundEngine = Depends(get_round_engine)):
    """
    Open a new ICVSS round
    
    Args:
        bout_id: Bout identifier
        round_num: Round number (1-5)
    
    Returns:
        ICVSSRound object
    """
    try:
        round_data = await engine.open_round(bout_id, round_num)
        
        # Notify via WebSocket
        await ws_manager.broadcast_to_display(bout_id, {
            "action": "round_opened",
            "round_id": round_data.round_id,
            "round_num": round_num
        })
        
        return round_data
    except Exception as e:
        logger.error(f"Error opening round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@icvss_router.post("/round/event")
async def add_event(round_id: str, event: CVEvent, engine: RoundEngine = Depends(get_round_engine)):
    """
    Add a CV or judge event to a round
    
    Args:
        round_id: Round identifier
        event: CVEvent object
    
    Returns:
        Success status
    """
    try:
        accepted = await engine.add_event(round_id, event)
        
        if accepted:
            # Get round to get bout_id
            round_data = await engine.get_round(round_id)
            
            # Broadcast to appropriate feed
            if event.source.value == "cv_system":
                await ws_manager.broadcast_cv_event(
                    round_data.bout_id,
                    round_id,
                    event.model_dump()
                )
            else:
                await ws_manager.broadcast_judge_event(
                    round_data.bout_id,
                    round_id,
                    event.model_dump()
                )
            
            return {"success": True, "message": "Event accepted"}
        else:
            return {"success": False, "message": "Event rejected"}
    
    except Exception as e:
        logger.error(f"Error adding event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@icvss_router.post("/round/event/batch")
async def add_events_batch(round_id: str, events: List[CVEvent], engine: RoundEngine = Depends(get_round_engine)):
    """
    Add multiple events at once (batch processing)
    
    Args:
        round_id: Round identifier
        events: List of CVEvent objects
    
    Returns:
        Summary of accepted/rejected events
    """
    try:
        accepted_count = 0
        rejected_count = 0
        
        for event in events:
            accepted = await engine.add_event(round_id, event)
            if accepted:
                accepted_count += 1
            else:
                rejected_count += 1
        
        return {
            "success": True,
            "accepted": accepted_count,
            "rejected": rejected_count,
            "total": len(events)
        }
    
    except Exception as e:
        logger.error(f"Error adding batch events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@icvss_router.get("/round/score/{round_id}", response_model=ScoreResponse)
async def get_round_score(round_id: str, engine: RoundEngine = Depends(get_round_engine)):
    """
    Calculate current score for a round
    
    Args:
        round_id: Round identifier
    
    Returns:
        ScoreResponse with fighter scores and breakdown
    """
    try:
        score = await engine.calculate_score(round_id)
        
        if not score:
            raise HTTPException(status_code=404, detail="Round not found")
        
        # Broadcast score update
        round_data = await engine.get_round(round_id)
        await ws_manager.broadcast_score_update(
            round_data.bout_id,
            round_id,
            score.model_dump()
        )
        
        # Also broadcast to display
        await ws_manager.broadcast_to_display(
            round_data.bout_id,
            {
                "action": "score_updated",
                "round_id": round_id,
                "score_card": score.score_card,
                "winner": score.winner
            }
        )
        
        return score
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@icvss_router.post("/round/lock/{round_id}")
async def lock_round(round_id: str, engine: RoundEngine = Depends(get_round_engine)):
    """
    Lock a round (finalize score)
    
    Args:
        round_id: Round identifier
    
    Returns:
        Success status with event hash
    """
    try:
        success = await engine.lock_round(round_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Round not found or already locked")
        
        # Get round data for hash
        round_data = await engine.get_round(round_id)
        
        # Broadcast lock event
        await ws_manager.broadcast_to_display(
            round_data.bout_id,
            {
                "action": "round_locked",
                "round_id": round_id,
                "event_hash": round_data.event_hash,
                "final_score": round_data.score_card
            }
        )
        
        return {
            "success": True,
            "round_id": round_id,
            "event_hash": round_data.event_hash,
            "locked_at": round_data.locked_at.isoformat() if round_data.locked_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error locking round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@icvss_router.get("/round/{round_id}", response_model=ICVSSRound)
async def get_round(round_id: str, engine: RoundEngine = Depends(get_round_engine)):
    """
    Get round data
    
    Args:
        round_id: Round identifier
    
    Returns:
        ICVSSRound object
    """
    round_data = await engine.get_round(round_id)
    
    if not round_data:
        raise HTTPException(status_code=404, detail="Round not found")
    
    return round_data


# ============================================================================
# CV VENDOR ENDPOINTS
# ============================================================================

@icvss_router.post("/cv/event")
async def receive_cv_event(vendor_id: str, raw_data: dict, x_api_key: Optional[str] = Header(None)):
    """
    Receive event from CV vendor (vendor-specific format)
    
    Args:
        vendor_id: CV vendor identifier
        raw_data: Raw event data from vendor
        x_api_key: API key for authentication
    
    Returns:
        Success status
    """
    # TODO: Validate API key
    # if not validate_api_key(vendor_id, x_api_key):
    #     raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        # Normalize vendor event to CVEvent
        normalized_event = EventNormalizer.normalize_from_vendor(vendor_id, raw_data)
        
        # Add to round
        round_id = raw_data.get("round_id")
        if not round_id:
            raise HTTPException(status_code=400, detail="Missing round_id")
        
        # Use existing add_event endpoint
        result = await add_event(round_id, normalized_event, get_round_engine())
        
        return result
    
    except Exception as e:
        logger.error(f"Error receiving CV event from {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@icvss_router.websocket("/ws/cv-feed/{bout_id}")
async def websocket_cv_feed(websocket: WebSocket, bout_id: str, auth_token: Optional[str] = None):
    """
    WebSocket feed for CV events
    
    Args:
        websocket: WebSocket connection
        bout_id: Bout identifier
        auth_token: Optional authentication token
    """
    await ws_manager.connect(websocket, "cv_event", bout_id, auth_token)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@icvss_router.websocket("/ws/judge-feed/{bout_id}")
async def websocket_judge_feed(websocket: WebSocket, bout_id: str, auth_token: Optional[str] = None):
    """
    WebSocket feed for judge events
    """
    await ws_manager.connect(websocket, "judge_event", bout_id, auth_token)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@icvss_router.websocket("/ws/score-feed/{bout_id}")
async def websocket_score_feed(websocket: WebSocket, bout_id: str, auth_token: Optional[str] = None):
    """
    WebSocket feed for score updates
    """
    await ws_manager.connect(websocket, "score_update", bout_id, auth_token)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@icvss_router.websocket("/ws/broadcast/{bout_id}")
async def websocket_broadcast_feed(websocket: WebSocket, bout_id: str):
    """
    WebSocket feed for broadcast overlays (public, no auth required)
    """
    await ws_manager.connect(websocket, "broadcast", bout_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@icvss_router.get("/stats")
async def get_icvss_stats(engine: RoundEngine = Depends(get_round_engine)):
    """
    Get ICVSS system statistics
    
    Returns:
        System stats including connections, processed events, etc.
    """
    processor_stats = engine.event_processor.get_stats()
    ws_stats = ws_manager.get_connection_count()
    
    return {
        "event_processor": processor_stats,
        "websocket_connections": ws_stats,
        "active_rounds": len(engine.active_rounds),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@icvss_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ICVSS",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
