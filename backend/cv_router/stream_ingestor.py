"""
CV Router - Stream Ingestor
Ingest frames from RTMP/SRT/WebSocket streams
"""

import asyncio
from typing import Dict, Callable, Optional
import logging
from datetime import datetime, timezone
import random
import base64
from .models import CameraStream, Frame, StreamType

logger = logging.getLogger(__name__)


class StreamIngestor:
    """Ingest video streams from multiple cameras"""
    
    def __init__(self):
        self.streams: Dict[str, CameraStream] = {}
        self.frame_callback: Optional[Callable] = None
        self.ingestion_tasks: Dict[str, asyncio.Task] = {}
    
    async def add_stream(
        self,
        camera_id: str,
        stream_type: StreamType,
        stream_url: str
    ) -> CameraStream:
        """Add new camera stream"""
        stream = CameraStream(
            camera_id=camera_id,
            stream_type=stream_type,
            stream_url=stream_url
        )
        
        self.streams[camera_id] = stream
        
        # Start ingestion task
        task = asyncio.create_task(self._ingest_stream(stream))
        self.ingestion_tasks[camera_id] = task
        
        logger.info(f"Stream added: {camera_id} ({stream_type}) at {stream_url}")
        return stream
    
    async def remove_stream(self, camera_id: str) -> bool:
        """Remove camera stream"""
        if camera_id in self.streams:
            self.streams[camera_id].active = False
            
            # Cancel ingestion task
            if camera_id in self.ingestion_tasks:
                self.ingestion_tasks[camera_id].cancel()
                del self.ingestion_tasks[camera_id]
            
            del self.streams[camera_id]
            logger.info(f"Stream removed: {camera_id}")
            return True
        
        return False
    
    def set_frame_callback(self, callback: Callable):
        """Set callback for incoming frames"""
        self.frame_callback = callback
    
    async def _ingest_stream(self, stream: CameraStream):
        """Ingest frames from stream (mocked for now)"""
        sequence_num = 0
        
        try:
            while stream.active:
                # Mock frame generation
                if stream.stream_type == StreamType.MOCK:
                    frame = await self._generate_mock_frame(stream, sequence_num)
                else:
                    # In production, this would handle RTMP/SRT/WebSocket
                    frame = await self._generate_mock_frame(stream, sequence_num)
                
                # Update stream stats
                now = datetime.now(timezone.utc)
                if stream.last_frame_time:
                    delta = (now - stream.last_frame_time).total_seconds()
                    if delta > 0:
                        stream.fps = 0.9 * stream.fps + 0.1 * (1.0 / delta)
                
                stream.last_frame_time = now
                stream.total_frames += 1
                sequence_num += 1
                
                # Send frame to callback
                if self.frame_callback:
                    await self.frame_callback(frame)
                
                # Simulate frame rate (30 FPS)
                await asyncio.sleep(1.0 / 30.0)
        
        except asyncio.CancelledError:
            logger.info(f"Stream ingestion cancelled: {stream.camera_id}")
        except Exception as e:
            logger.error(f"Stream ingestion error for {stream.camera_id}: {e}")
            stream.active = False
    
    async def _generate_mock_frame(self, stream: CameraStream, sequence_num: int) -> Frame:
        """Generate mock frame for testing"""
        # Create fake frame data (small base64 string)
        fake_data = base64.b64encode(b"mock_frame_data_" + str(sequence_num).encode()).decode()
        
        frame = Frame(
            camera_id=stream.camera_id,
            timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
            data=fake_data,
            width=1920,
            height=1080,
            format="jpeg",
            sequence_num=sequence_num,
            camera_angle=random.uniform(0, 360)
        )
        
        return frame
    
    def get_stream_stats(self) -> Dict:
        """Get statistics for all streams"""
        stats = {}
        for camera_id, stream in self.streams.items():
            stats[camera_id] = {
                "active": stream.active,
                "fps": stream.fps,
                "latency_ms": stream.latency_ms,
                "dropped_frames": stream.dropped_frames,
                "total_frames": stream.total_frames,
                "stream_type": stream.stream_type.value
            }
        return stats
