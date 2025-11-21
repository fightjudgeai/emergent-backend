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
    """NTP-like time synchronization"""
    
    def __init__(self):
        self.clients: Dict[str, ClientSync] = {}
        
        # Drift history for jitter calculation
        self.drift_history: Dict[str, deque] = {}
    
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
