"""
Audit Logger for Stat Engine

Logs all supervisor actions for compliance and debugging.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """Logs all stat recalculation actions"""
    
    def __init__(self, db):
        self.db = db
        logger.info("Audit Logger initialized")
    
    async def log_action(
        self,
        action_type: str,
        trigger: str,
        user: Optional[str] = None,
        fight_id: Optional[str] = None,
        round_num: Optional[int] = None,
        fighter_id: Optional[str] = None,
        result: Dict[str, Any] = None
    ) -> str:
        """
        Log a supervisor action
        
        Args:
            action_type: Type of action (round_aggregation, fight_aggregation, career_aggregation)
            trigger: manual | round_locked | post_fight | nightly
            user: User who triggered the action (optional)
            fight_id: Fight ID (if applicable)
            round_num: Round number (if applicable)
            fighter_id: Fighter ID (if applicable)
            result: Action result (job_id, status, rows_updated, etc.)
        
        Returns:
            Audit log entry ID
        """
        
        if not self.db:
            logger.warning("Database not available for audit logging")
            return None
        
        try:
            audit_entry = {
                "action_type": action_type,
                "trigger": trigger,
                "user": user or "supervisor",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                
                # Action scope
                "fight_id": fight_id,
                "round_num": round_num,
                "fighter_id": fighter_id,
                
                # Result
                "result": result or {},
                
                # Metadata
                "ip_address": None,  # Can be added from request context
                "user_agent": None,  # Can be added from request context
            }
            
            # Insert into audit_logs collection
            result = await self.db.audit_logs.insert_one(audit_entry)
            
            log_id = str(result.inserted_id)
            
            logger.info(
                f"Audit logged: {action_type} | trigger={trigger} | "
                f"fight={fight_id} | round={round_num} | fighter={fighter_id} | "
                f"audit_id={log_id}"
            )
            
            return log_id
        
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
            return None
    
    async def get_recent_actions(self, limit: int = 50) -> list:
        """
        Get recent audit log entries
        
        Args:
            limit: Maximum number of entries to return
        
        Returns:
            List of audit log entries
        """
        
        if not self.db:
            return []
        
        try:
            cursor = self.db.audit_logs.find().sort("timestamp", -1).limit(limit)
            logs = await cursor.to_list(length=limit)
            
            # Remove MongoDB _id
            for log in logs:
                log.pop('_id', None)
            
            return logs
        
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []
    
    async def get_actions_by_user(self, user: str, limit: int = 50) -> list:
        """Get audit logs for a specific user"""
        
        if not self.db:
            return []
        
        try:
            cursor = self.db.audit_logs.find({"user": user}).sort("timestamp", -1).limit(limit)
            logs = await cursor.to_list(length=limit)
            
            for log in logs:
                log.pop('_id', None)
            
            return logs
        
        except Exception as e:
            logger.error(f"Error fetching user audit logs: {e}")
            return []
    
    async def get_actions_by_fight(self, fight_id: str) -> list:
        """Get all audit logs for a specific fight"""
        
        if not self.db:
            return []
        
        try:
            cursor = self.db.audit_logs.find({"fight_id": fight_id}).sort("timestamp", -1)
            logs = await cursor.to_list(length=None)
            
            for log in logs:
                log.pop('_id', None)
            
            return logs
        
        except Exception as e:
            logger.error(f"Error fetching fight audit logs: {e}")
            return []
