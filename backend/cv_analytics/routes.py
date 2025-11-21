"""
CV Analytics Engine - FastAPI Routes
Process raw CV data and output standardized events
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from datetime import datetime, timezone

from .models import RawCVInput, AnalyticsOutput
from .analytics_engine import CVAnalyticsEngine
from .mock_generator import MockCVDataGenerator
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent

logger = logging.getLogger(__name__)

# Create router
cv_analytics_router = APIRouter(tags=["CV Analytics"])

# Global analytics engine
analytics_engine = CVAnalyticsEngine()


# ============================================================================
# CV DATA PROCESSING ENDPOINTS
# ============================================================================

@cv_analytics_router.post("/process", response_model=List[CombatEvent])
async def process_cv_frame(
    bout_id: str,
    round_id: str,
    raw_input: RawCVInput
):
    """
    Process single raw CV frame
    
    Args:
        bout_id: Bout identifier
        round_id: Round identifier
        raw_input: Raw CV model output
    
    Returns:
        List of standardized CombatEvent objects
    """
    try:
        events = analytics_engine.process_raw_input(raw_input, bout_id, round_id)
        logger.info(f"Processed frame {raw_input.frame_id}: {len(events)} events generated")
        return events
    except Exception as e:
        logger.error(f"Error processing CV frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@cv_analytics_router.post("/process/batch", response_model=List[CombatEvent])
async def process_multicamera_batch(
    bout_id: str,
    round_id: str,
    raw_inputs: List[RawCVInput]
):
    """
    Process batch of multi-camera frames
    
    Args:
        bout_id: Bout identifier
        round_id: Round identifier
        raw_inputs: List of raw CV inputs from multiple cameras
    
    Returns:
        Fused list of CombatEvent objects
    """
    try:
        events = analytics_engine.process_multicamera_batch(raw_inputs, bout_id, round_id)
        logger.info(f"Processed {len(raw_inputs)} camera views: {len(events)} fused events")
        return events
    except Exception as e:
        logger.error(f"Error processing multi-camera batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@cv_analytics_router.post("/analytics", response_model=AnalyticsOutput)
async def generate_analytics(events: List[CombatEvent], window_seconds: int = 60):
    """
    Generate analytics from event stream
    
    Args:
        events: List of recent combat events
        window_seconds: Time window for analysis
    
    Returns:
        Analytics output with pace, style, control metrics
    """
    try:
        analytics = analytics_engine.generate_analytics(events, window_seconds)
        return analytics
    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MOCK DATA GENERATOR ENDPOINTS (TESTING)
# ============================================================================

@cv_analytics_router.get("/mock/scenario/{scenario}", response_model=List[RawCVInput])
async def generate_mock_scenario(
    bout_id: str,
    round_id: str,
    scenario: str = "balanced"
):
    """
    Generate mock CV data for testing
    
    Args:
        bout_id: Bout identifier
        round_id: Round identifier
        scenario: balanced/striker_dominance/grappler_control/war
    
    Returns:
        List of mock raw CV inputs
    """
    try:
        generator = MockCVDataGenerator(bout_id, round_id)
        mock_data = generator.generate_event_sequence(scenario)
        logger.info(f"Generated {len(mock_data)} mock CV frames for scenario: {scenario}")
        return mock_data
    except Exception as e:
        logger.error(f"Error generating mock data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@cv_analytics_router.get("/mock/multicam", response_model=List[RawCVInput])
async def generate_mock_multicamera(
    bout_id: str,
    round_id: str,
    fighter_id: str,
    action: str = "punch",
    impact: str = "heavy",
    num_cameras: int = 3
):
    """
    Generate mock multi-camera frame
    
    Args:
        bout_id: Bout identifier
        round_id: Round identifier
        fighter_id: Fighter identifier
        action: Action type
        impact: Impact level
        num_cameras: Number of camera views
    
    Returns:
        List of mock multi-camera frames
    """
    try:
        from .models import ActionType, ImpactLevel
        
        generator = MockCVDataGenerator(bout_id, round_id)
        
        # Parse action and impact
        action_type = ActionType(action.lower())
        impact_level = ImpactLevel(impact.lower())
        
        mock_frames = generator.generate_multicamera_frame(
            fighter_id, action_type, impact_level, num_cameras
        )
        
        logger.info(f"Generated {len(mock_frames)} camera views")
        return mock_frames
    except Exception as e:
        logger.error(f"Error generating multi-camera mock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM STATUS
# ============================================================================

@cv_analytics_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CV Analytics Engine",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@cv_analytics_router.get("/status")
async def get_status():
    """Get CV Analytics Engine status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_stats": {
            "recent_strikes_buffer": len(analytics_engine.recent_strikes),
            "cumulative_damage": analytics_engine.cumulative_damage
        },
        "temporal_smoother": {
            "window_size": analytics_engine.temporal_smoother.window_size,
            "confidence_threshold": analytics_engine.temporal_smoother.confidence_threshold,
            "buffer_size": len(analytics_engine.temporal_smoother.frame_buffer)
        },
        "multicam_fusion": {
            "fusion_window_ms": analytics_engine.multicam_fusion.fusion_window_ms
        }
    }
