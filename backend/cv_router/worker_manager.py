"""
CV Router - Worker Manager
Manage CV worker pool with health monitoring and load balancing
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
import logging
from .models import CVWorker, WorkerStatus, RoutingDecision

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manage CV worker pool"""
    
    def __init__(self, health_check_interval: int = 10):
        self.workers: Dict[str, CVWorker] = {}
        self.health_check_interval = health_check_interval
        self.routing_history: List[RoutingDecision] = []
        
        # Start health monitor
        asyncio.create_task(self._health_monitor())
    
    async def register_worker(self, endpoint: str) -> CVWorker:
        """Register new CV worker"""
        worker = CVWorker(endpoint=endpoint)
        self.workers[worker.worker_id] = worker
        
        logger.info(f"Worker registered: {worker.worker_id} at {endpoint}")
        return worker
    
    async def deregister_worker(self, worker_id: str) -> bool:
        """Remove worker from pool"""
        if worker_id in self.workers:
            del self.workers[worker_id]
            logger.info(f"Worker deregistered: {worker_id}")
            return True
        return False
    
    async def update_worker_metrics(
        self,
        worker_id: str,
        latency_ms: float,
        queue_size: int
    ):
        """Update worker performance metrics"""
        if worker_id not in self.workers:
            return
        
        worker = self.workers[worker_id]
        
        # Update metrics with exponential moving average
        alpha = 0.3  # Smoothing factor
        worker.avg_latency_ms = (
            alpha * latency_ms + (1 - alpha) * worker.avg_latency_ms
        )
        worker.queue_size = queue_size
        worker.frames_processed += 1
        worker.last_heartbeat = datetime.now(timezone.utc)
    
    async def report_worker_error(self, worker_id: str):
        """Report worker error"""
        if worker_id in self.workers:
            self.workers[worker_id].errors += 1
            
            # Check if worker should be marked unhealthy
            worker = self.workers[worker_id]
            error_rate = worker.errors / max(worker.frames_processed, 1)
            
            if error_rate > 0.1:  # >10% error rate
                worker.status = WorkerStatus.UNHEALTHY
                logger.warning(f"Worker {worker_id} marked UNHEALTHY (error rate: {error_rate:.2%})")
    
    def select_worker(self, frame_id: str) -> Optional[CVWorker]:
        """Select best worker for frame using load balancing"""
        healthy_workers = [
            w for w in self.workers.values()
            if w.status == WorkerStatus.HEALTHY
        ]
        
        if not healthy_workers:
            # Try degraded workers as fallback
            healthy_workers = [
                w for w in self.workers.values()
                if w.status == WorkerStatus.DEGRADED
            ]
        
        if not healthy_workers:
            logger.error("No healthy workers available")
            return None
        
        # Calculate load score for each worker
        # Lower is better: latency + queue_size penalty
        def load_score(worker: CVWorker) -> float:
            latency_weight = 0.6
            queue_weight = 0.4
            return (
                worker.avg_latency_ms * latency_weight +
                worker.queue_size * 10 * queue_weight  # 10ms penalty per queued frame
            )
        
        # Select worker with lowest load
        selected_worker = min(healthy_workers, key=load_score)
        
        # Record routing decision
        decision = RoutingDecision(
            frame_id=frame_id,
            worker_id=selected_worker.worker_id,
            worker_load_score=load_score(selected_worker),
            worker_latency=selected_worker.avg_latency_ms,
            worker_queue_size=selected_worker.queue_size
        )
        self.routing_history.append(decision)
        
        # Keep only recent history
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]
        
        logger.debug(f"Routed frame {frame_id} to worker {selected_worker.worker_id} (load: {load_score(selected_worker):.2f})")
        return selected_worker
    
    async def _health_monitor(self):
        """Background task to monitor worker health"""
        while True:
            await asyncio.sleep(self.health_check_interval)
            
            now = datetime.now(timezone.utc)
            for worker in self.workers.values():
                # Check heartbeat
                time_since_heartbeat = (now - worker.last_heartbeat).total_seconds()
                
                if time_since_heartbeat > 30:
                    worker.status = WorkerStatus.OFFLINE
                    logger.warning(f"Worker {worker.worker_id} marked OFFLINE (no heartbeat for {time_since_heartbeat:.0f}s)")
                
                elif time_since_heartbeat > 15:
                    worker.status = WorkerStatus.DEGRADED
                
                # Check latency
                elif worker.avg_latency_ms > 200:  # >200ms latency
                    worker.status = WorkerStatus.DEGRADED
                    logger.warning(f"Worker {worker.worker_id} marked DEGRADED (high latency: {worker.avg_latency_ms:.0f}ms)")
                
                elif worker.status != WorkerStatus.HEALTHY:
                    # Recover if metrics improved
                    worker.status = WorkerStatus.HEALTHY
                    logger.info(f"Worker {worker.worker_id} recovered to HEALTHY")
    
    def get_metrics(self) -> Dict:
        """Get worker pool metrics"""
        status_counts = {status: 0 for status in WorkerStatus}
        for worker in self.workers.values():
            status_counts[worker.status] += 1
        
        return {
            "total_workers": len(self.workers),
            "healthy_workers": status_counts[WorkerStatus.HEALTHY],
            "degraded_workers": status_counts[WorkerStatus.DEGRADED],
            "unhealthy_workers": status_counts[WorkerStatus.UNHEALTHY],
            "offline_workers": status_counts[WorkerStatus.OFFLINE],
            "avg_latency_ms": sum(w.avg_latency_ms for w in self.workers.values()) / len(self.workers) if self.workers else 0,
            "total_frames_processed": sum(w.frames_processed for w in self.workers.values()),
            "total_errors": sum(w.errors for w in self.workers.values())
        }
