"""
AI Merge Engine API Routes

Endpoints for receiving and merging AI-generated events from Colab/Kaggle.
"""

from fastapi import APIRouter, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from .merge_engine import MergeEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-merge", tags=["AI Merge Engine"])

# Global instances
db: Optional[AsyncIOMotorDatabase] = None
merge_engine: Optional[MergeEngine] = None


class AIEventBatch(BaseModel):
    """AI event batch from Colab/Kaggle"""
    fight_id: str
    events: List[Dict[str, Any]]
    submitted_by: str = "colab_ai"
    metadata: Optional[Dict[str, Any]] = None


def init_ai_merge_engine(database: AsyncIOMotorDatabase):
    """Initialize AI merge engine with database"""
    global db, merge_engine
    db = database
    merge_engine = MergeEngine(database)
    logger.info("✅ AI Merge Engine initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "AI Merge Engine",
        "version": "1.0.0",
        "status": "operational",
        "merge_engine_active": merge_engine is not None
    }


@router.post("/submit-batch")
async def submit_ai_batch(batch: AIEventBatch):
    """
    Submit batch of AI-generated events from Colab/Kaggle
    
    Merge Rules:
    - If AI + human agree within tolerance → auto approve
    - If conflict → mark for review
    - Never overwrite human source directly
    
    All approved AI events:
    - Enter events table with source='ai_cv'
    - Trigger stat recalculations automatically
    
    Example JSON from Colab:
    ```json
    {
      "fight_id": "fight_123",
      "events": [
        {
          "fighter_id": "fighter_1",
          "round": 1,
          "timestamp": "2025-01-15T10:30:45.123Z",
          "event_type": "jab",
          "target": "head",
          "confidence": 0.92,
          "position": "distance"
        }
      ],
      "submitted_by": "roboflow_cv",
      "metadata": {
        "model": "yolov8",
        "version": "1.2.3"
      }
    }
    ```
    """
    
    if not merge_engine:
        raise HTTPException(status_code=500, detail="Merge engine not initialized")
    
    try:
        result = await merge_engine.merge_ai_batch(
            ai_events=batch.events,
            fight_id=batch.fight_id,
            submitted_by=batch.submitted_by
        )
        
        return {
            "status": "success",
            "fight_id": batch.fight_id,
            **result
        }
    
    except Exception as e:
        logger.error(f"Error processing AI batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review-items")
async def get_review_items(
    fight_id: Optional[str] = None,
    status: str = "pending",
    limit: int = 50
):
    """
    Get AI events that require human review
    
    Args:
        fight_id: Filter by fight (optional)
        status: Filter by status (pending, approved, rejected)
        limit: Maximum results
        
    Returns:
        List of review items with conflicts
    """
    
    if not merge_engine:
        raise HTTPException(status_code=500, detail="Merge engine not initialized")
    
    try:
        items = await merge_engine.get_review_items(
            fight_id=fight_id,
            status=status,
            limit=limit
        )
        
        return {
            "count": len(items),
            "items": items
        }
    
    except Exception as e:
        logger.error(f"Error getting review items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review-items/{review_id}/approve")
async def approve_review_item(
    review_id: str,
    approved_version: str,
    approved_by: str
):
    """
    Approve a review item after human decision
    
    Args:
        review_id: Review item ID
        approved_version: 'ai' or 'human' (which version to use)
        approved_by: Supervisor ID
        
    Returns:
        Success status
    """
    
    if not merge_engine:
        raise HTTPException(status_code=500, detail="Merge engine not initialized")
    
    if approved_version not in ['ai', 'human']:
        raise HTTPException(status_code=400, detail="approved_version must be 'ai' or 'human'")
    
    try:
        success = await merge_engine.approve_review_item(
            review_id=review_id,
            approved_version=approved_version,
            approved_by=approved_by
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Review item not found")
        
        return {
            "status": "success",
            "review_id": review_id,
            "approved_version": approved_version
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving review item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_merge_stats():
    """Get AI merge statistics"""
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Count auto-approved events
        auto_approved = await db.events.count_documents({
            'source': 'ai_cv',
            'auto_approved': True
        })
        
        # Count pending reviews
        pending_reviews = await db.ai_event_reviews.count_documents({
            'status': 'pending'
        })
        
        # Count approved reviews
        approved_reviews = await db.ai_event_reviews.count_documents({
            'status': 'approved'
        })
        
        return {
            'auto_approved_events': auto_approved,
            'pending_reviews': pending_reviews,
            'approved_reviews': approved_reviews,
            'total_ai_events': auto_approved + approved_reviews
        }
    
    except Exception as e:
        logger.error(f"Error getting merge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
