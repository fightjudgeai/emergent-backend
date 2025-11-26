"""
Post-Fight Review Interface API Routes

Endpoints for video playback, event editing, versioning, and approval workflow.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging
import os
import uuid
import shutil
from pathlib import Path

from .review_manager import ReviewManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["Post-Fight Review"])

# Global instances
db: Optional[AsyncIOMotorDatabase] = None
review_manager: Optional[ReviewManager] = None

# Video storage path
VIDEO_STORAGE_PATH = "/app/backend/uploads/videos"


class EventUpdate(BaseModel):
    """Event update model"""
    updates: Dict[str, Any]
    supervisor_id: str
    reason: str


class MergeRequest(BaseModel):
    """Merge events request"""
    event_ids: List[str]
    supervisor_id: str
    merged_data: Dict[str, Any]


def init_review_interface(database: AsyncIOMotorDatabase):
    """Initialize review interface with database"""
    global db, review_manager
    db = database
    review_manager = ReviewManager(database)
    
    # Ensure video storage directory exists
    Path(VIDEO_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    
    logger.info("✅ Post-Fight Review Interface initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Post-Fight Review Interface",
        "version": "1.0.0",
        "status": "operational",
        "review_manager_active": review_manager is not None
    }


@router.get("/timeline/{fight_id}")
async def get_fight_timeline(fight_id: str):
    """
    Get complete timeline of all events for a fight
    
    Returns:
    - All events in chronological order
    - Grouped by rounds
    - Includes deleted events (marked)
    """
    
    if not review_manager:
        raise HTTPException(status_code=500, detail="Review manager not initialized")
    
    try:
        timeline = await review_manager.get_fight_timeline(fight_id)
        
        if 'error' in timeline:
            raise HTTPException(status_code=500, detail=timeline['error'])
        
        return timeline
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/events/{event_id}")
async def edit_event(event_id: str, update: EventUpdate):
    """
    Edit an event with versioning
    
    All edits are:
    - Versioned (original kept in event_versions)
    - Logged by supervisor_id
    - Tracked in audit log
    
    Args:
        event_id: Event ID to edit
        update: Updates, supervisor ID, and reason
    """
    
    if not review_manager:
        raise HTTPException(status_code=500, detail="Review manager not initialized")
    
    try:
        result = await review_manager.edit_event(
            event_id=event_id,
            updates=update.updates,
            supervisor_id=update.supervisor_id,
            reason=update.reason
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    supervisor_id: str,
    reason: str
):
    """
    Delete incorrect event (soft delete with versioning)
    
    Args:
        event_id: Event ID to delete
        supervisor_id: Supervisor performing deletion
        reason: Reason for deletion
    """
    
    if not review_manager:
        raise HTTPException(status_code=500, detail="Review manager not initialized")
    
    try:
        result = await review_manager.delete_event(
            event_id=event_id,
            supervisor_id=supervisor_id,
            reason=reason
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/merge")
async def merge_duplicate_events(merge_request: MergeRequest):
    """
    Merge duplicate events into single event
    
    Args:
        merge_request: Event IDs, supervisor ID, and merged data
    """
    
    if not review_manager:
        raise HTTPException(status_code=500, detail="Review manager not initialized")
    
    try:
        result = await review_manager.merge_duplicate_events(
            event_ids=merge_request.event_ids,
            supervisor_id=merge_request.supervisor_id,
            merged_data=merge_request.merged_data
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fights/{fight_id}/approve")
async def approve_and_rerun_stats(
    fight_id: str,
    supervisor_id: str
):
    """
    Approve all edits and trigger stat engine re-run
    
    After approval:
    - All edits are finalized
    - Stat engine recalculates all stats
    - Fight marked as reviewed
    """
    
    if not review_manager:
        raise HTTPException(status_code=500, detail="Review manager not initialized")
    
    try:
        result = await review_manager.approve_and_rerun_stats(
            fight_id=fight_id,
            supervisor_id=supervisor_id
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_id}/history")
async def get_event_history(event_id: str):
    """
    Get version history for an event
    
    Returns all versions with:
    - Original data
    - Changes made
    - Supervisor who made changes
    - Timestamp
    """
    
    if not review_manager:
        raise HTTPException(status_code=500, detail="Review manager not initialized")
    
    try:
        history = await review_manager.get_event_history(event_id)
        
        return {
            'event_id': event_id,
            'version_count': len(history),
            'versions': history
        }
    
    except Exception as e:
        logger.error(f"Error getting event history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/upload")
async def upload_video(
    fight_id: str = Form(...),
    video: UploadFile = File(...)
):
    """
    Upload fight video for review
    
    Manual video upload for post-fight analysis
    
    Args:
        fight_id: Fight identifier
        video: Video file
    """
    
    try:
        # Generate unique filename
        file_extension = os.path.splitext(video.filename)[1]
        unique_filename = f"{fight_id}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(VIDEO_STORAGE_PATH, unique_filename)
        
        # Save video file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        # Store video metadata in database
        video_doc = {
            'video_id': str(uuid.uuid4()),
            'fight_id': fight_id,
            'filename': unique_filename,
            'original_filename': video.filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'uploaded_at': datetime.now(timezone.utc).isoformat()
        }
        
        if db:
            await db.fight_videos.insert_one(video_doc)
        
        logger.info(f"Video uploaded for fight {fight_id}: {unique_filename}")
        
        return {
            'status': 'success',
            'video_id': video_doc['video_id'],
            'filename': unique_filename,
            'file_size': video_doc['file_size']
        }
    
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{fight_id}")
async def get_fight_videos(fight_id: str):
    """
    Get all videos for a fight
    
    Returns list of uploaded videos
    """
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        videos = await db.fight_videos.find(
            {'fight_id': fight_id}
        ).to_list(length=50)
        
        return {
            'fight_id': fight_id,
            'video_count': len(videos),
            'videos': videos
        }
    
    except Exception as e:
        logger.error(f"Error getting videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/stream/{video_id}")
async def stream_video(video_id: str):
    """
    Stream video file
    
    Returns video file for playback
    """
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        video = await db.fight_videos.find_one({'video_id': video_id})
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        file_path = video['file_path']
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Video file not found on disk")
        
        return FileResponse(
            file_path,
            media_type='video/mp4',
            filename=video['original_filename']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from datetime import datetime, timezone
