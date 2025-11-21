"""
Fight Judge AI - FastAPI Routes
Round lifecycle, event ingestion, scoring, audit, WebSocket feeds
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from typing import Optional, List
import logging
from datetime import datetime, timezone

from .models import CombatEvent, RoundState, RoundScore, ScoringWeights
from .round_manager import RoundManager
from .websocket_manager import fjai_ws_manager

logger = logging.getLogger(__name__)

# Create router
fjai_router = APIRouter(tags=["Fight Judge AI"])

# Global round manager (will be initialized with db)
round_manager: Optional[RoundManager] = None


def get_round_manager():
    """Dependency to get round manager"""
    if round_manager is None:
        raise HTTPException(status_code=500, detail="Fight Judge AI not initialized")
    return round_manager


# ============================================================================
# ROUND LIFECYCLE ENDPOINTS
# ============================================================================

@fjai_router.post("/round/open", response_model=RoundState)
async def open_round(bout_id: str, round_num: int, manager: RoundManager = Depends(get_round_manager)):
    """
    Open new round
    
    Args:
        bout_id: Bout identifier
        round_num: Round number (1-5)
    
    Returns:
        RoundState object
    """
    try:
        round_state = await manager.open_round(bout_id, round_num)
        
        # Notify via WebSocket
        await fjai_ws_manager.broadcast_to_displays(bout_id, {
            "action": "round_opened",
            "round_id": round_state.round_id,
            "round_num": round_num
        })
        
        return round_state
    except Exception as e:
        logger.error(f"Error opening round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@fjai_router.post("/round/event")
async def add_event(round_id: str, event: CombatEvent, manager: RoundManager = Depends(get_round_manager)):
    """
    Add combat event to round
    
    Args:
        round_id: Round identifier
        event: CombatEvent object
    
    Returns:
        Success status
    """
    try:
        accepted = await manager.add_event(round_id, event)
        
        if accepted:
            # Get round to get bout_id
            round_state = await manager._get_round(round_id)
            
            # Broadcast to appropriate feed
            if event.source.value == "cv_system":
                await fjai_ws_manager.broadcast_cv_event(
                    round_state.bout_id,
                    event.model_dump()
                )
            elif event.source.value == "manual":
                await fjai_ws_manager.broadcast_judge_event(
                    round_state.bout_id,
                    event.model_dump()
                )
            
            return {"success": True, "message": "Event accepted"}
        else:
            return {"success": False, "message": "Event rejected"}
    
    except Exception as e:
        logger.error(f"Error adding event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@fjai_router.get("/round/score/{round_id}", response_model=RoundScore)
async def get_round_score(round_id: str, manager: RoundManager = Depends(get_round_manager)):
    """
    Calculate live round score
    
    Args:
        round_id: Round identifier
    
    Returns:
        RoundScore object
    """
    try:
        score = await manager.calculate_score(round_id)
        
        if not score:
            raise HTTPException(status_code=404, detail="Round not found")
        
        # Broadcast score update
        round_state = await manager._get_round(round_id)
        await fjai_ws_manager.broadcast_score_update(
            round_state.bout_id,
            score.model_dump()
        )
        
        return score
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@fjai_router.post("/round/lock/{round_id}")
async def lock_round(round_id: str, manager: RoundManager = Depends(get_round_manager)):
    """
    Lock round (finalize score)
    
    Args:
        round_id: Round identifier
    
    Returns:
        Success status with event hash
    """
    try:
        success = await manager.lock_round(round_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Round not found or already locked")
        
        # Get round data
        round_state = await manager._get_round(round_id)
        
        # Broadcast lock event
        await fjai_ws_manager.broadcast_to_displays(
            round_state.bout_id,
            {
                "action": "round_locked",
                "round_id": round_id,
                "event_hash": round_state.event_hash,
                "final_score": round_state.score_card
            }
        )
        
        return {
            "success": True,
            "round_id": round_id,
            "event_hash": round_state.event_hash,
            "locked_at": round_state.locked_at.isoformat() if round_state.locked_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error locking round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AUDIT ENDPOINTS
# ============================================================================

@fjai_router.get("/audit/export/{bout_id}")
async def export_audit_bundle(bout_id: str, manager: RoundManager = Depends(get_round_manager)):
    """
    Export complete audit trail for bout
    
    Args:
        bout_id: Bout identifier
    
    Returns:
        Complete audit bundle with all logs
    """
    try:
        bundle = await manager.audit_layer.export_audit_bundle(bout_id)
        return bundle
    except Exception as e:
        logger.error(f"Error exporting audit bundle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@fjai_router.get("/audit/verify/{log_id}")
async def verify_audit_log(log_id: str, manager: RoundManager = Depends(get_round_manager)):
    """
    Verify audit log signature
    
    Args:
        log_id: Log identifier
    
    Returns:
        Verification result
    """
    try:
        valid = await manager.audit_layer.verify_signature(log_id)
        return {
            "log_id": log_id,
            "signature_valid": valid
        }
    except Exception as e:
        logger.error(f"Error verifying audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM STATUS
# ============================================================================

@fjai_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Fight Judge AI",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@fjai_router.get("/system/status")
async def get_system_status(manager: RoundManager = Depends(get_round_manager)):
    """
    Get comprehensive system status
    
    Returns:
        System health metrics
    """
    try:
        # Get active rounds count
        active_rounds = len([r for r in manager.active_rounds.values() if r.status == "open"])
        
        # Get pipeline stats
        pipeline_stats = manager.event_pipeline.get_stats()
        
        # Get WebSocket stats
        ws_stats = fjai_ws_manager.get_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_rounds": active_rounds,
            "event_pipeline": pipeline_stats,
            "websocket": ws_stats,
            "scoring_engine": {
                "damage_weight": manager.scoring_engine.weights.damage,
                "control_weight": manager.scoring_engine.weights.control,
                "aggression_weight": manager.scoring_engine.weights.aggression,
                "defense_weight": manager.scoring_engine.weights.defense,
                "damage_primacy_enabled": True
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@fjai_router.websocket("/ws/cv/{bout_id}")
async def websocket_cv_feed(websocket: WebSocket, bout_id: str):
    """WebSocket feed for incoming CV events"""
    await fjai_ws_manager.connect(websocket, "cv", bout_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Process incoming CV data if needed
            logger.debug(f"CV feed received: {data}")
    except WebSocketDisconnect:
        fjai_ws_manager.disconnect(websocket, "cv", bout_id)


@fjai_router.websocket("/ws/judge/{bout_id}")
async def websocket_judge_feed(websocket: WebSocket, bout_id: str):
    """WebSocket feed for incoming judge events"""
    await fjai_ws_manager.connect(websocket, "judge", bout_id)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Judge feed received: {data}")
    except WebSocketDisconnect:
        fjai_ws_manager.disconnect(websocket, "judge", bout_id)


@fjai_router.websocket("/ws/score/{bout_id}")
async def websocket_score_feed(websocket: WebSocket, bout_id: str):
    """WebSocket feed for outgoing score updates"""
    await fjai_ws_manager.connect(websocket, "score", bout_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        fjai_ws_manager.disconnect(websocket, "score", bout_id)


@fjai_router.websocket("/ws/broadcast/{bout_id}")
async def websocket_broadcast_feed(websocket: WebSocket, bout_id: str):
    """WebSocket feed for broadcast layer stats"""
    await fjai_ws_manager.connect(websocket, "broadcast", bout_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        fjai_ws_manager.disconnect(websocket, "broadcast", bout_id)
