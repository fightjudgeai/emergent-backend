"""Heartbeat Monitor - Monitoring Engine"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from .models import HeartbeatData, HeartbeatRecord, ServiceStatus, HeartbeatSummary

logger = logging.getLogger(__name__)

# Heartbeat timeout (consider service offline after 15 seconds without heartbeat)
HEARTBEAT_TIMEOUT_SEC = 15

# Expected services
EXPECTED_SERVICES = [
    "CV Router",
    "CV Analytics",
    "Scoring Engine",
    "Replay Worker",
    "Highlight Worker",
    "Storage Manager",
    "Supervisor Console"
]


class HeartbeatMonitor:
    """Monitor service health via heartbeats"""
    
    def __init__(self, db=None):
        self.db = db
        
        # In-memory cache of latest heartbeats
        self.latest_heartbeats: Dict[str, HeartbeatRecord] = {}
        
        logger.info("Heartbeat Monitor initialized")
    
    async def record_heartbeat(self, heartbeat: HeartbeatData) -> HeartbeatRecord:
        """
        Record a heartbeat from a service
        
        Args:
            heartbeat: Heartbeat data from service
        
        Returns:
            HeartbeatRecord with generated ID
        """
        # Create record
        record = HeartbeatRecord(
            service_name=heartbeat.service_name,
            timestamp=heartbeat.timestamp,
            status=heartbeat.status,
            metrics=heartbeat.metrics or {}
        )
        
        # Update in-memory cache
        self.latest_heartbeats[heartbeat.service_name] = record
        
        # Store in database if available
        if self.db is not None:
            try:
                # Convert to dict for MongoDB
                record_dict = record.model_dump()
                record_dict['timestamp'] = record_dict['timestamp'].isoformat()
                record_dict['received_at'] = record_dict['received_at'].isoformat()
                
                await self.db.heartbeats.insert_one(record_dict)
                
                # Keep only last 1000 heartbeats per service (cleanup)
                await self.db.heartbeats.delete_many({
                    "service_name": heartbeat.service_name,
                    "received_at": {"$lt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
                })
            except Exception as e:
                logger.error(f"Error storing heartbeat in database: {e}")
        
        logger.debug(f"Heartbeat recorded: {heartbeat.service_name} [{heartbeat.status}]")
        return record
    
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """
        Get current status of a specific service
        
        Args:
            service_name: Name of the service
        
        Returns:
            ServiceStatus
        """
        # Get latest heartbeat
        latest = self.latest_heartbeats.get(service_name)
        
        if not latest:
            # No heartbeat received yet
            return ServiceStatus(
                service_name=service_name,
                status="offline",
                is_healthy=False
            )
        
        # Calculate time since last heartbeat
        now = datetime.now(timezone.utc)
        time_since = (now - latest.received_at).total_seconds()
        
        # Determine if service is offline (no heartbeat for > HEARTBEAT_TIMEOUT_SEC)
        if time_since > HEARTBEAT_TIMEOUT_SEC:
            return ServiceStatus(
                service_name=service_name,
                status="offline",
                last_heartbeat=latest.timestamp,
                time_since_last_heartbeat_sec=time_since,
                metrics=latest.metrics,
                is_healthy=False
            )
        
        # Service is online, use reported status
        is_healthy = latest.status == "ok"
        
        return ServiceStatus(
            service_name=service_name,
            status=latest.status,
            last_heartbeat=latest.timestamp,
            time_since_last_heartbeat_sec=time_since,
            metrics=latest.metrics,
            is_healthy=is_healthy
        )
    
    def get_summary(self) -> HeartbeatSummary:
        """
        Get summary of all service statuses
        
        Returns:
            HeartbeatSummary with counts and service list
        """
        services = []
        healthy_count = 0
        warning_count = 0
        error_count = 0
        offline_count = 0
        
        # Check all expected services
        for service_name in EXPECTED_SERVICES:
            status = self.get_service_status(service_name)
            services.append(status)
            
            if status.status == "ok":
                healthy_count += 1
            elif status.status == "warning":
                warning_count += 1
            elif status.status == "error":
                error_count += 1
            elif status.status == "offline":
                offline_count += 1
        
        return HeartbeatSummary(
            total_services=len(EXPECTED_SERVICES),
            healthy_services=healthy_count,
            warning_services=warning_count,
            error_services=error_count,
            offline_services=offline_count,
            services=services
        )
    
    async def get_service_history(self, service_name: str, limit: int = 100) -> List[HeartbeatRecord]:
        """
        Get heartbeat history for a service
        
        Args:
            service_name: Name of the service
            limit: Maximum number of records to return
        
        Returns:
            List of HeartbeatRecord
        """
        if self.db is None:
            # Return in-memory data only
            latest = self.latest_heartbeats.get(service_name)
            return [latest] if latest else []
        
        try:
            # Query database
            cursor = self.db.heartbeats.find(
                {"service_name": service_name},
                {"_id": 0}
            ).sort("received_at", -1).limit(limit)
            
            records = await cursor.to_list(length=limit)
            
            # Convert to HeartbeatRecord objects
            return [
                HeartbeatRecord(
                    id=r["id"],
                    service_name=r["service_name"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    status=r["status"],
                    metrics=r["metrics"],
                    received_at=datetime.fromisoformat(r["received_at"])
                )
                for r in records
            ]
        except Exception as e:
            logger.error(f"Error fetching service history: {e}")
            return []
