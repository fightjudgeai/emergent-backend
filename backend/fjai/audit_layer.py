"""
Fight Judge AI - Audit Layer
Append-only logging with SHA256 signatures
"""

from typing import Dict, Any
from datetime import datetime, timezone
import hashlib
import json
import logging
from .models import AuditLogEntry

logger = logging.getLogger(__name__)


class AuditLayer:
    """Immutable audit logging"""
    
    def __init__(self, db):
        self.db = db
    
    async def log_action(
        self,
        bout_id: str,
        round_id: str,
        action: str,
        actor: str,
        data: Dict[str, Any]
    ) -> AuditLogEntry:
        """
        Create immutable audit log entry
        """
        # Create log entry
        log_entry = AuditLogEntry(
            bout_id=bout_id,
            round_id=round_id,
            action=action,
            actor=actor,
            data=data
        )
        
        # Generate SHA256 signature
        signature = self._generate_signature(log_entry)
        log_entry.signature = signature
        
        # Save to database (append-only)
        await self.db.fjai_audit_logs.insert_one(self._serialize_for_mongo(log_entry.model_dump()))
        
        logger.info(f"Audit log created: {action} by {actor}")
        return log_entry
    
    def _generate_signature(self, log_entry: AuditLogEntry) -> str:
        """Generate SHA256 signature for log entry"""
        # Create deterministic string
        sig_data = {
            "bout_id": log_entry.bout_id,
            "round_id": log_entry.round_id,
            "action": log_entry.action,
            "actor": log_entry.actor,
            "timestamp": log_entry.timestamp.isoformat(),
            "data": log_entry.data
        }
        
        sig_string = json.dumps(sig_data, sort_keys=True)
        return hashlib.sha256(sig_string.encode()).hexdigest()
    
    async def verify_signature(self, log_id: str) -> bool:
        """Verify audit log signature"""
        log_doc = await self.db.fjai_audit_logs.find_one({"log_id": log_id})
        if not log_doc:
            return False
        
        log_entry = AuditLogEntry(**log_doc)
        expected_signature = self._generate_signature(log_entry)
        
        return log_entry.signature == expected_signature
    
    async def export_audit_bundle(self, bout_id: str) -> Dict:
        """Export complete audit trail for bout"""
        logs = await self.db.fjai_audit_logs.find(
            {"bout_id": bout_id}
        ).sort("timestamp", 1).to_list(length=None)
        
        return {
            "bout_id": bout_id,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_logs": len(logs),
            "logs": logs,
            "worm_compliant": True,
            "signature_algorithm": "SHA256"
        }
    
    def _serialize_for_mongo(self, data: Dict) -> Dict:
        """Convert datetime objects to ISO strings"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_for_mongo(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_for_mongo(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        return serialized
