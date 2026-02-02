"""
Fight Judge AI - Scoring Service API Routes
============================================

FastAPI endpoints for the scoring service.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from .core import (
    RoundStats, RoundScore, FightScore,
    score_round, score_fight, calculate_delta,
    validate_round_stats, round_stats_from_dict,
    SCORING_CONFIG
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scoring", tags=["Scoring Service"])

# Database reference
db = None

def init_scoring_routes(database):
    global db
    db = database
    logger.info("✅ Scoring Service routes initialized")


# ============== Request Models ==============

class RoundStatsRequest(BaseModel):
    """Request model for scoring a round"""
    round_number: int = Field(..., ge=1, le=10)
    bout_id: Optional[str] = None
    
    # Strikes
    red_significant_strikes: int = Field(default=0, ge=0)
    blue_significant_strikes: int = Field(default=0, ge=0)
    red_total_strikes: int = Field(default=0, ge=0)
    blue_total_strikes: int = Field(default=0, ge=0)
    red_knockdowns: int = Field(default=0, ge=0)
    blue_knockdowns: int = Field(default=0, ge=0)
    
    # Grappling
    red_takedowns: int = Field(default=0, ge=0)
    blue_takedowns: int = Field(default=0, ge=0)
    red_submission_attempts: int = Field(default=0, ge=0)
    blue_submission_attempts: int = Field(default=0, ge=0)
    
    # Control
    red_control_time_seconds: int = Field(default=0, ge=0)
    blue_control_time_seconds: int = Field(default=0, ge=0)
    
    # Impact
    red_near_finishes: int = Field(default=0, ge=0)
    blue_near_finishes: int = Field(default=0, ge=0)
    
    # Fouls
    red_point_deductions: int = Field(default=0, ge=0)
    blue_point_deductions: int = Field(default=0, ge=0)
    
    # Events (optional - for detailed scoring)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Options
    require_10_8_approval: bool = Field(default=True)
    preview_only: bool = Field(default=False)


class EventScoreRequest(BaseModel):
    """Request model for scoring from events only"""
    bout_id: str
    round_number: int = Field(..., ge=1, le=10)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    require_10_8_approval: bool = Field(default=True)
    preview_only: bool = Field(default=False)


class FightFinalizeRequest(BaseModel):
    """Request model for finalizing a fight"""
    bout_id: str
    finish_method: Optional[str] = None  # KO, TKO, SUB, DEC, etc.
    finish_winner: Optional[str] = None  # RED or BLUE
    finish_round: Optional[int] = None
    finish_time: Optional[str] = None
    rounds: Optional[List[Dict]] = None  # Pre-scored rounds (if not fetching from DB)


class ApproveScoreRequest(BaseModel):
    """Request to approve or modify a 10-8 score"""
    bout_id: str
    round_number: int
    approved: bool  # True = approve 10-8, False = change to 10-9
    modified_red_score: Optional[int] = None
    modified_blue_score: Optional[int] = None


# ============== Endpoints ==============

@router.post("/round")
async def score_round_endpoint(request: RoundStatsRequest):
    """
    Score a single round based on provided statistics.
    
    This endpoint calculates the 10-point must score for a round
    based on strikes, takedowns, control, and other factors.
    
    Returns:
        - red_score: Points for red corner (7-10)
        - blue_score: Points for blue corner (7-10)
        - winner: RED, BLUE, or DRAW
        - delta: Point differential
        - is_10_8: Flag if round is 10-8 or worse
        - requires_approval: Flag if supervisor approval needed
        - breakdown: Detailed scoring breakdown
    """
    try:
        # Convert request to RoundStats
        stats = round_stats_from_dict(request.model_dump())
        
        # Score the round
        score = score_round(
            stats, 
            require_10_8_approval=request.require_10_8_approval
        )
        
        result = score.to_dict()
        result["preview_only"] = request.preview_only
        
        # Save to database if not preview
        if not request.preview_only and request.bout_id and db:
            await _save_round_score(request.bout_id, score)
        
        return result
        
    except Exception as e:
        logger.error(f"Error scoring round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/round/events")
async def score_round_from_events(request: EventScoreRequest):
    """
    Score a round using only logged events.
    
    This endpoint fetches events from the database (or uses provided events)
    and calculates the round score based on the delta.
    """
    try:
        events = request.events
        
        # Fetch events from DB if not provided
        if not events and db:
            cursor = db.unified_events.find({
                "bout_id": request.bout_id,
                "round_number": request.round_number
            })
            events = await cursor.to_list(1000)
        
        # Create stats with events
        stats = RoundStats(
            round_number=request.round_number,
            events=events
        )
        
        # Score the round
        score = score_round(
            stats,
            require_10_8_approval=request.require_10_8_approval
        )
        
        result = score.to_dict()
        result["preview_only"] = request.preview_only
        result["total_events"] = len(events)
        
        # Save if not preview
        if not request.preview_only and db:
            await _save_round_score(request.bout_id, score)
        
        return result
        
    except Exception as e:
        logger.error(f"Error scoring round from events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/round/approve")
async def approve_round_score(request: ApproveScoreRequest):
    """
    Approve or modify a 10-8 round score.
    
    Supervisors must approve 10-8 rounds before they are finalized.
    They can either approve the calculated score or change it to 10-9.
    """
    try:
        if not db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Get existing round score
        existing = await db.round_results.find_one({
            "bout_id": request.bout_id,
            "round_number": request.round_number
        })
        
        if not existing:
            raise HTTPException(status_code=404, detail="Round score not found")
        
        # Update based on approval
        if request.approved:
            # Keep the 10-8 score
            update = {
                "supervisor_approved": True,
                "approved_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Change to 10-9
            if existing.get("winner") == "RED":
                red_score = request.modified_red_score or 10
                blue_score = request.modified_blue_score or 9
            else:
                red_score = request.modified_red_score or 9
                blue_score = request.modified_blue_score or 10
            
            update = {
                "red_points": red_score,
                "blue_points": blue_score,
                "red_score": red_score,
                "blue_score": blue_score,
                "supervisor_modified": True,
                "original_red": existing.get("red_points"),
                "original_blue": existing.get("blue_points"),
                "modified_at": datetime.now(timezone.utc).isoformat()
            }
        
        await db.round_results.update_one(
            {"bout_id": request.bout_id, "round_number": request.round_number},
            {"$set": update}
        )
        
        return {
            "success": True,
            "bout_id": request.bout_id,
            "round_number": request.round_number,
            "approved": request.approved,
            "update": update
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving round score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fight/finalize")
async def finalize_fight(request: FightFinalizeRequest):
    """
    Finalize a fight and calculate the final outcome.
    
    This endpoint aggregates all round scores, applies the finish method
    (if any), and returns the final fight result.
    
    Returns:
        - red_total: Total points for red corner
        - blue_total: Total points for blue corner
        - winner: RED, BLUE, or DRAW
        - result: Detailed result (RED_DECISION, BLUE_KO_TKO, etc.)
        - finish_method: DEC, KO, TKO, SUB, etc.
        - rounds: List of all round scores
    """
    try:
        rounds_data = request.rounds
        
        # Fetch rounds from DB if not provided
        if not rounds_data and db:
            cursor = db.round_results.find(
                {"bout_id": request.bout_id}
            ).sort("round_number", 1)
            rounds_data = await cursor.to_list(20)
        
        if not rounds_data:
            raise HTTPException(status_code=400, detail="No rounds to score")
        
        # Convert to RoundScore objects
        round_scores = []
        for rd in rounds_data:
            round_scores.append(RoundScore(
                round_number=rd.get("round_number", len(round_scores) + 1),
                red_score=rd.get("red_points", rd.get("red_score", 10)),
                blue_score=rd.get("blue_points", rd.get("blue_score", 9)),
                winner=rd.get("winner", "RED"),
                result=_get_round_result(rd),
                delta=rd.get("delta", 0),
                is_10_8=rd.get("is_10_8", False),
                is_10_7=rd.get("is_10_7", False)
            ))
        
        # Score the fight
        fight_score = score_fight(
            rounds=round_scores,
            finish_method=request.finish_method,
            finish_winner=request.finish_winner,
            finish_round=request.finish_round,
            finish_time=request.finish_time
        )
        
        result = fight_score.to_dict()
        
        # Save to database
        if db:
            await _save_fight_result(request.bout_id, fight_score, request)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finalizing fight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_scoring_config():
    """
    Get the current scoring configuration.
    
    Returns point values, thresholds, and other scoring parameters.
    """
    return {
        "config": SCORING_CONFIG,
        "version": "2.0",
        "description": "Fight Judge AI Scoring Configuration"
    }


@router.post("/calculate-delta")
async def calculate_delta_endpoint(events: List[Dict[str, Any]]):
    """
    Calculate point differential from a list of events.
    
    Useful for previewing scores without saving.
    """
    try:
        red_delta, blue_delta, breakdown = calculate_delta(events)
        
        return {
            "red_delta": red_delta,
            "blue_delta": blue_delta,
            "net_delta": red_delta - blue_delta,
            "breakdown": breakdown
        }
    except Exception as e:
        logger.error(f"Error calculating delta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Helper Functions ==============

def _get_round_result(rd: Dict):
    """Convert stored round data to RoundResult enum"""
    from .core import RoundResult
    
    winner = rd.get("winner", "DRAW")
    red = rd.get("red_points", rd.get("red_score", 10))
    blue = rd.get("blue_points", rd.get("blue_score", 10))
    
    if winner == "RED":
        if blue <= 7:
            return RoundResult.RED_WIN_10_7
        elif blue == 8:
            return RoundResult.RED_WIN_10_8
        else:
            return RoundResult.RED_WIN_10_9
    elif winner == "BLUE":
        if red <= 7:
            return RoundResult.BLUE_WIN_10_7
        elif red == 8:
            return RoundResult.BLUE_WIN_10_8
        else:
            return RoundResult.BLUE_WIN_10_9
    else:
        return RoundResult.DRAW


async def _save_round_score(bout_id: str, score: RoundScore):
    """Save round score to database"""
    if not db:
        return
    
    doc = score.to_dict()
    doc["bout_id"] = bout_id
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.round_results.update_one(
        {"bout_id": bout_id, "round_number": score.round_number},
        {"$set": doc},
        upsert=True
    )


async def _save_fight_result(bout_id: str, fight_score: FightScore, request: FightFinalizeRequest):
    """Save final fight result to database"""
    if not db:
        return
    
    # Update bout document
    update = {
        "status": "completed",
        "final_red": fight_score.red_total,
        "final_blue": fight_score.blue_total,
        "winner": fight_score.winner,
        "result": fight_score.result.value,
        "finish_method": fight_score.finish_method.value,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    if request.finish_round:
        update["finish_round"] = request.finish_round
    if request.finish_time:
        update["finish_time"] = request.finish_time
    
    await db.bouts.update_one(
        {"bout_id": bout_id},
        {"$set": update}
    )
