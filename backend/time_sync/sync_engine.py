"""
Time Sync Service - Synchronization Engine
"""

import time
import logging
from typing import Dict, List
from datetime import datetime, timezone
from collections import deque
from .models import TimeSync, ClientSync, TimeSyncStats

logger = logging.getLogger(__name__)


class TimeSyncEngine:
    """NTP-like time synchronization + FightClock"""
    
    def __init__(self):
        self.clients: Dict[str, ClientSync] = {}
        
        # Drift history for jitter calculation
        self.drift_history: Dict[str, deque] = {}
        
        # FightClock state
        self.timer_start_time: int = 0  # Timestamp when timer started
        self.timer_pause_time: int = 0  # Timestamp when paused
        self.timer_elapsed_ms: int = 0  # Total elapsed time
        self.is_running: bool = False
        self.is_paused: bool = False
        
        # WebSocket connections for broadcasting
        self.websocket_connections: List = []
    
    def get_current_time(self) -> TimeSync:
        """
        Get current unified timestamp
        
        Returns:
            TimeSync with server timestamps
        """
        # High-precision timestamp
        request_time = int(time.time() * 1000)
        
        # Current time
        now = datetime.now(timezone.utc)
        current_ms = int(now.timestamp() * 1000)
        
        # Response time
        response_time = int(time.time() * 1000)
        
        return TimeSync(
            server_timestamp_ms=current_ms,
            server_time_iso=now.isoformat(),
            request_received_ms=request_time,
            response_sent_ms=response_time
        )
    
    def register_client_sync(
        self,
        client_id: str,
        device_type: str,
        client_timestamp_ms: int
    ) -> ClientSync:
        """
        Register client synchronization
        
        Args:
            client_id: Client identifier
            device_type: Type of device
            client_timestamp_ms: Client's current timestamp
        
        Returns:
            ClientSync with drift correction
        """
        # Calculate drift
        server_time_ms = int(time.time() * 1000)
        drift_ms = server_time_ms - client_timestamp_ms
        
        # Track drift history for jitter calculation
        if client_id not in self.drift_history:
            self.drift_history[client_id] = deque(maxlen=10)
        
        self.drift_history[client_id].append(drift_ms)
        
        # Calculate jitter (standard deviation of drift)
        drift_list = list(self.drift_history[client_id])
        if len(drift_list) > 1:
            avg_drift = sum(drift_list) / len(drift_list)
            jitter = (sum((d - avg_drift) ** 2 for d in drift_list) / len(drift_list)) ** 0.5
        else:
            jitter = 0.0
        
        # Apply correction if drift > 100ms
        correction_applied = abs(drift_ms) > 100
        corrected_drift = drift_ms if correction_applied else 0.0
        
        client_sync = ClientSync(
            client_id=client_id,
            device_type=device_type,
            last_sync=datetime.now(timezone.utc),
            drift_ms=drift_ms,
            jitter_ms=jitter,
            correction_applied=correction_applied,
            corrected_drift_ms=corrected_drift
        )
        
        self.clients[client_id] = client_sync
        
        if correction_applied:
            logger.info(f"Time correction applied for {client_id}: {corrected_drift}ms drift")
        
        return client_sync
    
    def get_stats(self) -> TimeSyncStats:
        """Get sync statistics"""
        if not self.clients:
            return TimeSyncStats(
                synced_clients=0,
                avg_drift_ms=0.0,
                max_drift_ms=0.0,
                avg_jitter_ms=0.0
            )
        
        drifts = [abs(c.drift_ms) for c in self.clients.values()]
        jitters = [c.jitter_ms for c in self.clients.values()]
        
        return TimeSyncStats(
            synced_clients=len(self.clients),
            avg_drift_ms=sum(drifts) / len(drifts),
            max_drift_ms=max(drifts),
            avg_jitter_ms=sum(jitters) / len(jitters),
            client_stats=list(self.clients.values())
        )

    # =========================================================================
    # FightClock Features
    # =========================================================================
    
    def start_timer(self) -> dict:
        """Start or resume the round timer"""
        current_time = int(time.time() * 1000)
        
        if self.is_paused:
            # Resume from pause
            pause_duration = current_time - self.timer_pause_time
            self.timer_start_time += pause_duration
            self.is_paused = False
            self.is_running = True
            logger.info(f"Timer resumed after {pause_duration}ms pause")
        else:
            # Fresh start
            self.timer_start_time = current_time
            self.timer_elapsed_ms = 0
            self.is_running = True
            self.is_paused = False
            logger.info("Timer started")
        
        return self.get_timer_state()
    
    def pause_timer(self) -> dict:
        """Pause the round timer"""
        if not self.is_running:
            return {"error": "Timer not running"}
        
        current_time = int(time.time() * 1000)
        self.timer_pause_time = current_time
        self.timer_elapsed_ms = current_time - self.timer_start_time
        self.is_paused = True
        self.is_running = False
        
        logger.info(f"Timer paused at {self.timer_elapsed_ms}ms")
        return self.get_timer_state()
    
    def reset_timer(self) -> dict:
        """Reset the round timer"""
        self.timer_start_time = 0
        self.timer_pause_time = 0
        self.timer_elapsed_ms = 0
        self.is_running = False
        self.is_paused = False
        
        logger.info("Timer reset")
        return self.get_timer_state()
    
    def get_timer_state(self) -> dict:
        """Get current timer state"""
        current_time = int(time.time() * 1000)
        
        if self.is_running and not self.is_paused:
            # Calculate current elapsed time
            elapsed = current_time - self.timer_start_time
        elif self.is_paused:
            # Use stored elapsed time
            elapsed = self.timer_elapsed_ms
        else:
            # Timer not running
            elapsed = 0
        
        return {
            "elapsed_ms": elapsed,
            "elapsed_seconds": round(elapsed / 1000, 2),
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "server_time_ms": current_time,
            "server_time_iso": datetime.now(timezone.utc).isoformat()
        }
    
    def get_clock_now(self) -> dict:
        """Get current unified time + timer state"""
        time_sync = self.get_current_time()
        timer_state = self.get_timer_state()
        
        return {
            **time_sync.model_dump(),
            "timer": timer_state
        }

