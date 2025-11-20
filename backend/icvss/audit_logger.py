"""
ICVSS Audit Logger with SHA256 Integrity
"""

import hashlib
import json
from typing import Dict, List, Any
from datetime import datetime, timezone
import logging
from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditLogger:
    """Immutable audit logging with SHA256 hashing"""
    
    def __init__(self, db):
        self.db = db
    
    async def log_action(self, bout_id: str, round_id: str, action: str, actor: str, data: Dict) -> AuditLog:
        """Log an action with SHA256 hash"""
        # Create log entry
        log_entry = AuditLog(
            bout_id=bout_id,
            round_id=round_id,
            action=action,
            actor=actor,
            data=data,
            data_hash=self._generate_hash(data)
        )
        
        # Store in database
        await self.db.icvss_audit_logs.insert_one(log_entry.model_dump())
        
        logger.info(f"Audit log: {action} by {actor} - hash: {log_entry.data_hash[:16]}...")
        return log_entry
    
    def _generate_hash(self, data: Dict) -> str:
        """Generate SHA256 hash of data"""
        # Sort keys for consistent hashing
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def generate_event_hash(self, events: List[Any]) -> str:
        """Generate SHA256 hash of event stream"""
        # Convert events to dicts if needed
        event_dicts = []
        for event in events:
            if hasattr(event, 'model_dump'):
                event_dicts.append(event.model_dump())
            else:
                event_dicts.append(event)
        
        # Sort by timestamp for consistent ordering
        event_dicts.sort(key=lambda x: x.get('timestamp_ms', 0))
        
        # Generate hash
        combined_str = json.dumps(event_dicts, sort_keys=True)
        return hashlib.sha256(combined_str.encode()).hexdigest()
    
    async def verify_integrity(self, round_id: str) -> bool:
        """Verify round event integrity"""
        # Get round data
        round_doc = await self.db.icvss_rounds.find_one({"round_id": round_id})
        if not round_doc:
            return False
        
        stored_hash = round_doc.get("event_hash")
        if not stored_hash:
            logger.warning(f"No hash found for round {round_id}")
            return False
        
        # Recalculate hash
        events = round_doc.get("cv_events", []) + round_doc.get("judge_events", [])
        calculated_hash = self.generate_event_hash(events)
        
        # Compare
        is_valid = stored_hash == calculated_hash
        
        if is_valid:
            logger.info(f"Round {round_id} integrity verified ✓")
        else:
            logger.error(f"Round {round_id} integrity FAILED ✗")
        
        return is_valid
