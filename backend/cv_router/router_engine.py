"""
CV Router - Main Router Engine
Coordinate stream ingestion, worker management, and frame routing
"""

import asyncio
from typing import Optional
import logging
from datetime import datetime, timezone

from .worker_manager import WorkerManager
from .stream_ingestor import StreamIngestor
from .models import Frame, RouterMetrics

logger = logging.getLogger(__name__)


class CVRouterEngine:
    """Main CV Router coordination engine"""
    
    def __init__(self):
        self.worker_manager = WorkerManager()
        self.stream_ingestor = StreamIngestor()
        
        # Set frame callback
        self.stream_ingestor.set_frame_callback(self._on_frame_received)
        
        # Metrics
        self.total_frames_routed = 0
        self.frames_dropped = 0
        self.routing_latencies = []
        
        # WebSocket connection to E2 (CV Analytics)
        self.e2_websocket = None
    
    async def _on_frame_received(self, frame: Frame):
        """Handle incoming frame from stream"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Select worker
            worker = self.worker_manager.select_worker(frame.frame_id)
            
            if not worker:
                self.frames_dropped += 1
                logger.warning(f"Frame {frame.frame_id} dropped - no workers available")
                return
            
            # Route frame to worker (mocked)
            await self._route_to_worker(worker.worker_id, frame)
            
            # Update metrics
            self.total_frames_routed += 1
            routing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self.routing_latencies.append(routing_time)
            
            # Keep only recent latencies
            if len(self.routing_latencies) > 100:
                self.routing_latencies = self.routing_latencies[-100:]
        
        except Exception as e:
            logger.error(f"Error routing frame {frame.frame_id}: {e}")
            self.frames_dropped += 1
    
    async def _route_to_worker(self, worker_id: str, frame: Frame):
        """Route frame to CV worker (mocked)"""
        # In production: send frame to worker via HTTP/WebSocket
        # For now: simulate processing
        await asyncio.sleep(0.01)  # Simulate network latency
        
        # Simulate worker processing and send to E2
        if self.e2_websocket:
            # In production: receive CV output from worker, send to E2
            pass
    
    def get_metrics(self) -> RouterMetrics:
        """Get comprehensive system metrics"""
        worker_metrics = self.worker_manager.get_metrics()
        stream_stats = self.stream_ingestor.get_stream_stats()
        
        avg_routing_latency = (
            sum(self.routing_latencies) / len(self.routing_latencies)
            if self.routing_latencies else 0.0
        )
        
        return RouterMetrics(
            total_workers=worker_metrics["total_workers"],
            healthy_workers=worker_metrics["healthy_workers"],
            total_streams=len(self.stream_ingestor.streams),
            active_streams=len([s for s in self.stream_ingestor.streams.values() if s.active]),
            total_frames_routed=self.total_frames_routed,
            avg_routing_latency_ms=avg_routing_latency,
            frames_dropped=self.frames_dropped,
            camera_stats=stream_stats
        )
