"""
Highlight Worker - Background Worker Engine
"""

import asyncio
from typing import List
import logging
import uuid
from datetime import datetime
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent, EventType
from .models import VideoClip, ClipStatus

logger = logging.getLogger(__name__)


class HighlightWorkerEngine:
    """Background worker for highlight generation"""
    
    # Major events that trigger highlight generation
    HIGHLIGHT_EVENTS = {
        EventType.KD_FLASH,
        EventType.KD_HARD,
        EventType.KD_NF,
        EventType.ROCKED,
        EventType.MOMENTUM_SWING,
        EventType.SUB_ATTEMPT
    }
    
    def __init__(self):
        self.clips: List[VideoClip] = []
        self.processing_queue = asyncio.Queue()
        
        # Start background worker
        asyncio.create_task(self._process_queue())
    
    async def watch_event(self, event: CombatEvent):
        """
        Watch event and generate clip if major event
        
        Args:
            event: Combat event
        """
        if event.event_type in self.HIGHLIGHT_EVENTS:
            clip = self._create_clip_metadata(event)
            await self.processing_queue.put(clip)
            logger.info(f"Queued clip generation for {event.event_type.value}")
    
    def _create_clip_metadata(self, event: CombatEvent) -> VideoClip:
        """Create clip metadata from event"""
        # 5s before, 10s after = 15s total
        start_time = event.timestamp_ms - 5000
        end_time = event.timestamp_ms + 10000
        
        clip = VideoClip(
            clip_id=str(uuid.uuid4()),
            bout_id=event.bout_id,
            round_id=event.round_id,
            event_type=event.event_type,
            fighter_id=event.fighter_id,
            timestamp_ms=event.timestamp_ms,
            start_time_ms=start_time,
            end_time_ms=end_time,
            duration_sec=15.0,
            camera_angles=["cam_1", "cam_2"],  # Mock
            status=ClipStatus.PENDING
        )
        
        self.clips.append(clip)
        return clip
    
    async def _process_queue(self):
        """Background processor for clip generation"""
        while True:
            try:
                clip = await self.processing_queue.get()
                await self._generate_clip(clip)
            except Exception as e:
                logger.error(f"Error processing clip: {e}")
    
    async def _generate_clip(self, clip: VideoClip):
        """
        Generate video clip (mocked)
        
        In production:
        - Extract video segments from full-res sources
        - Stitch multi-camera views
        - Upload to S3
        - Update metadata
        """
        clip.status = ClipStatus.PROCESSING
        
        # Simulate processing
        await asyncio.sleep(2)
        
        # Mock S3 URL
        clip.storage_url = f"s3://fight-highlights/{clip.bout_id}/{clip.clip_id}.mp4"
        clip.status = ClipStatus.COMPLETED
        clip.processed_at = datetime.now()
        
        logger.info(f"Clip generated: {clip.clip_id}")
    
    def get_clips(self, bout_id: str) -> List[VideoClip]:
        """Get all clips for bout"""
        return [c for c in self.clips if c.bout_id == bout_id]
    
    async def generate_manual_clip(
        self,
        bout_id: str,
        round_id: str,
        timestamp_ms: int,
        event_type: EventType
    ) -> VideoClip:
        """Manually trigger clip generation"""
        from fjai.models import CombatEvent, EventSource
        
        mock_event = CombatEvent(
            bout_id=bout_id,
            round_id=round_id,
            fighter_id="fighter_a",
            event_type=event_type,
            severity=0.8,
            confidence=0.9,
            timestamp_ms=timestamp_ms,
            source=EventSource.MANUAL
        )
        
        await self.watch_event(mock_event)
        return self.clips[-1]
