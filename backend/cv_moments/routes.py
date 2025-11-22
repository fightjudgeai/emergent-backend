"""
CV Moments - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent
from .detection_engine import MomentDetectionEngine
from .models import (
    SignificantMoment,
    HighlightReel,
    MomentAnalysis
)

logger = logging.getLogger(__name__)

cv_moments_api = APIRouter(tags=["CV Moments - AI Detection"])
detection_engine: Optional[MomentDetectionEngine] = None

def get_detection_engine():
    if detection_engine is None:
        raise HTTPException(status_code=500, detail="CV Moments engine not initialized")
    return detection_engine

# ============================================================================
# Moment Analysis
# ============================================================================

@cv_moments_api.post("/highlights/analyze", response_model=MomentAnalysis)
async def analyze_bout_moments(
    bout_id: str,
    events: List[CombatEvent],
    judge_scores: Optional[List[dict]] = None
):
    """
    Analyze bout for all significant moments
    
    Detects:
    - Knockdowns
    - Big strikes
    - Submission attempts
    - Controversies
    
    Returns complete analysis with excitement scores
    """
    engine = get_detection_engine()
    
    if not events:
        raise HTTPException(status_code=400, detail="No events provided")
    
    analysis = await engine.analyze_bout(bout_id, events, judge_scores)
    return analysis

# ============================================================================
# Highlight Retrieval
# ============================================================================

@cv_moments_api.get("/highlights/{bout_id}", response_model=HighlightReel)
async def get_highlight_reel(bout_id: str):
    """Get complete highlight reel for a bout"""
    engine = get_detection_engine()
    
    reel = await engine.get_highlight_reel(bout_id)
    
    if not reel:
        raise HTTPException(status_code=404, detail=f"No highlights found for bout: {bout_id}")
    
    return reel

@cv_moments_api.get("/highlights/{bout_id}/knockdowns")
async def get_knockdowns(bout_id: str):
    """Get all knockdowns for a bout"""
    engine = get_detection_engine()
    
    reel = await engine.get_highlight_reel(bout_id)
    
    if not reel:
        return []
    
    return reel.knockdowns

@cv_moments_api.get("/highlights/{bout_id}/strikes")
async def get_big_strikes(bout_id: str):
    """Get all significant strikes for a bout"""
    engine = get_detection_engine()
    
    reel = await engine.get_highlight_reel(bout_id)
    
    if not reel:
        return []
    
    return reel.big_strikes

@cv_moments_api.get("/highlights/{bout_id}/submissions")
async def get_submissions(bout_id: str):
    """Get all submission attempts for a bout"""
    engine = get_detection_engine()
    
    reel = await engine.get_highlight_reel(bout_id)
    
    if not reel:
        return []
    
    return reel.submission_attempts

@cv_moments_api.get("/highlights/{bout_id}/controversies")
async def get_controversies(bout_id: str):
    """Get all controversial moments for a bout"""
    engine = get_detection_engine()
    
    reel = await engine.get_highlight_reel(bout_id)
    
    if not reel:
        return []
    
    return reel.controversies

# ============================================================================
# Statistics & Insights
# ============================================================================

@cv_moments_api.get("/highlights/{bout_id}/stats")
async def get_bout_stats(bout_id: str):
    """Get statistical summary of bout moments"""
    engine = get_detection_engine()
    
    reel = await engine.get_highlight_reel(bout_id)
    
    if not reel:
        raise HTTPException(status_code=404, detail=f"No data found for bout: {bout_id}")
    
    return {
        "bout_id": bout_id,
        "total_moments": reel.total_moments,
        "knockdowns": len(reel.knockdowns),
        "big_strikes": len(reel.big_strikes),
        "submission_attempts": len(reel.submission_attempts),
        "controversies": len(reel.controversies),
        "most_exciting_round": reel.most_exciting_round,
        "momentum_shifts": reel.momentum_shifts
    }

@cv_moments_api.get("/highlights/{bout_id}/timeline")
async def get_moment_timeline(bout_id: str):
    """Get chronological timeline of all moments"""
    engine = get_detection_engine()
    
    if not engine.db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = engine.db.significant_moments.find(
            {"bout_id": bout_id},
            {"_id": 0}
        ).sort("timestamp_ms", 1)
        
        moments = await cursor.to_list(length=1000)
        
        return {
            "bout_id": bout_id,
            "total_moments": len(moments),
            "timeline": moments
        }
    
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve timeline")

# ============================================================================
# Auto-Clip Generation
# ============================================================================

@cv_moments_api.get("/highlights/{bout_id}/clips")
async def get_video_clips(bout_id: str, min_severity: float = 0.7):
    """
    Get video clip timestamps for significant moments
    
    Returns clip start/end times for video editing
    """
    engine = get_detection_engine()
    
    if not engine.db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = engine.db.significant_moments.find(
            {
                "bout_id": bout_id,
                "severity": {"$gte": min_severity}
            },
            {"_id": 0}
        ).sort("severity", -1)
        
        moments = await cursor.to_list(length=100)
        
        clips = []
        for moment in moments:
            clips.append({
                "moment_type": moment['moment_type'],
                "description": moment['description'],
                "severity": moment['severity'],
                "round_num": moment['round_num'],
                "clip_start_ms": moment.get('clip_start_ms'),
                "clip_end_ms": moment.get('clip_end_ms'),
                "duration_ms": moment.get('clip_end_ms', 0) - moment.get('clip_start_ms', 0)
            })
        
        return {
            "bout_id": bout_id,
            "total_clips": len(clips),
            "clips": clips
        }
    
    except Exception as e:
        logger.error(f"Error getting clips: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve clips")

@cv_moments_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "CV Moments AI", "version": "1.0.0"}
