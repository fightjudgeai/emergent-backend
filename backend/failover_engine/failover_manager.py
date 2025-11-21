"""
Failover Engine - Failover Manager
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from .models import CVEngineMode, EngineHealth, FailoverStatus, FailoverEvent

logger = logging.getLogger(__name__)


class FailoverManager:
    """Manage CV engine failover"""
    
    def __init__(self, health_check_interval: int = 5):
        self.health_check_interval = health_check_interval
        
        # Current mode
        self.current_mode = CVEngineMode.CLOUD
        
        # Engine health
        self.cloud_health = EngineHealth(
            mode=CVEngineMode.CLOUD,
            healthy=True,
            last_heartbeat=datetime.now(timezone.utc),
            response_time_ms=50.0,
            error_rate=0.0
        )
        
        self.local_health = EngineHealth(
            mode=CVEngineMode.LOCAL,
            healthy=True,
            last_heartbeat=datetime.now(timezone.utc),
            response_time_ms=30.0,
            error_rate=0.0
        )
        
        # Failover history
        self.failover_history: List[FailoverEvent] = []
        self.alerts = []
        
        # Start health monitoring
        asyncio.create_task(self._health_monitor())
    
    async def _health_monitor(self):
        """Background health monitoring"""
        while True:
            await asyncio.sleep(self.health_check_interval)
            await self._check_engines()
    
    async def _check_engines(self):
        """Check engine health and trigger failover if needed"""
        # Check cloud
        cloud_ok = await self._check_cloud_health()
        
        # Check local
        local_ok = await self._check_local_health()
        
        # Failover logic
        if self.current_mode == CVEngineMode.CLOUD and not cloud_ok:
            if local_ok:
                await self._failover(CVEngineMode.LOCAL, "Cloud CV engine failed")
            else:
                await self._failover(CVEngineMode.MANUAL, "Both cloud and local failed")
        
        elif self.current_mode == CVEngineMode.LOCAL and not local_ok:
            if cloud_ok:
                await self._failover(CVEngineMode.CLOUD, "Local GPU node failed")
            else:
                await self._failover(CVEngineMode.MANUAL, "Both cloud and local failed")
        
        # Auto-recover to cloud if available
        elif self.current_mode == CVEngineMode.MANUAL and cloud_ok:
            await self._failover(CVEngineMode.CLOUD, "Cloud CV engine recovered")
    
    async def _check_cloud_health(self) -> bool:
        """Check cloud CV engine health (mocked)"""
        # In production: actual health check to cloud API
        now = datetime.now(timezone.utc)
        time_since_heartbeat = (now - self.cloud_health.last_heartbeat).total_seconds()
        
        # Mock: assume healthy if recent heartbeat
        healthy = time_since_heartbeat < 30 and self.cloud_health.error_rate < 0.1
        self.cloud_health.healthy = healthy
        
        return healthy
    
    async def _check_local_health(self) -> bool:
        """Check local GPU node health (mocked)"""
        # In production: actual health check to local GPU
        now = datetime.now(timezone.utc)
        time_since_heartbeat = (now - self.local_health.last_heartbeat).total_seconds()
        
        healthy = time_since_heartbeat < 30 and self.local_health.error_rate < 0.1
        self.local_health.healthy = healthy
        
        return healthy
    
    async def _failover(self, new_mode: CVEngineMode, reason: str):
        """Execute failover"""
        old_mode = self.current_mode
        
        # Record failover event
        event = FailoverEvent(
            from_mode=old_mode,
            to_mode=new_mode,
            reason=reason
        )
        
        self.failover_history.append(event)
        self.current_mode = new_mode
        
        # Create alert
        alert = {
            "level": "critical" if new_mode == CVEngineMode.MANUAL else "warning",
            "message": f"Failover: {old_mode.value} → {new_mode.value}",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 10:
            self.alerts = self.alerts[-10:]
        
        logger.warning(f"FAILOVER: {old_mode.value} → {new_mode.value} ({reason})")
    
    def get_status(self) -> FailoverStatus:
        """Get current failover status"""
        last_failover = self.failover_history[-1].timestamp if self.failover_history else None
        
        return FailoverStatus(
            current_mode=self.current_mode,
            cloud_health=self.cloud_health,
            local_health=self.local_health,
            last_failover=last_failover,
            failover_count=len(self.failover_history),
            alerts=self.alerts
        )
    
    async def update_cloud_heartbeat(self, response_time_ms: float, error_rate: float):
        """Update cloud health from heartbeat"""
        self.cloud_health.last_heartbeat = datetime.now(timezone.utc)
        self.cloud_health.response_time_ms = response_time_ms
        self.cloud_health.error_rate = error_rate
    
    async def update_local_heartbeat(self, response_time_ms: float, error_rate: float):
        """Update local health from heartbeat"""
        self.local_health.last_heartbeat = datetime.now(timezone.utc)
        self.local_health.response_time_ms = response_time_ms
        self.local_health.error_rate = error_rate
