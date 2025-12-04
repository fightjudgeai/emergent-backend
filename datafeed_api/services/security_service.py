"""
Security Service
Handles audit logging, kill-switch enforcement, and fail-safe rules
"""

import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityService:
    """
    Service for security operations and audit logging
    
    Implements:
    - Audit trail logging
    - Kill-switch enforcement
    - Duplicate settlement prevention
    - Fail-safe rules
    """
    
    def __init__(self, db_client):
        """
        Initialize security service
        
        Args:
            db_client: Database client
        """
        self.db = db_client
    
    async def log_security_event(
        self,
        event_type: str,
        action: str,
        client_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = 'success',
        error_message: Optional[str] = None
    ):
        """
        Log security event to audit trail
        
        Args:
            event_type: Type of event (api_call, websocket_connect, etc.)
            action: Specific action
            client_id: Client UUID
            resource_type: Type of resource accessed
            resource_id: Resource identifier
            details: Additional context
            ip_address: Client IP
            user_agent: User agent string
            status: Event status (success, failure, blocked)
            error_message: Error message if failed
        """
        try:
            self.db.client.table('security_audit_log').insert({
                'event_type': event_type,
                'client_id': client_id,
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'details': details,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'status': status,
                'error_message': error_message,
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
        
        except Exception as e:
            # Don't fail request if logging fails, but log error
            logger.error(f"Failed to log security event: {e}")
    
    async def check_system_status(self, component: str) -> tuple[bool, str, Optional[str]]:
        """
        Check if system component is active (kill-switch)
        
        Args:
            component: Component name (api, websocket, fantasy, markets, settlement)
        
        Returns:
            Tuple of (is_active, status, reason)
        """
        try:
            response = self.db.client.table('system_status')\
                .select('*')\
                .eq('component', component)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                # Default to active if not found
                return True, 'active', None
            
            status_record = response.data[0]
            is_active = status_record['status'] == 'active'
            
            return is_active, status_record['status'], status_record.get('reason')
        
        except Exception as e:
            logger.error(f"Error checking system status: {e}")
            # Fail open - allow if check fails
            return True, 'unknown', None
    
    async def emergency_stop(
        self,
        component: str,
        reason: str,
        admin_user: str
    ) -> bool:
        """
        Emergency stop for system component (kill-switch)
        
        Args:
            component: Component to stop
            reason: Reason for emergency stop
            admin_user: Admin user initiating stop
        
        Returns:
            True if successful
        """
        try:
            # Update system status
            self.db.client.table('system_status')\
                .update({
                    'status': 'emergency_stop',
                    'reason': reason,
                    'updated_by': admin_user,
                    'updated_at': datetime.utcnow().isoformat()
                })\
                .eq('component', component)\
                .execute()
            
            # Log admin action
            self.db.client.table('admin_actions').insert({
                'admin_user': admin_user,
                'action_type': 'emergency_stop',
                'new_value': {'component': component, 'reason': reason},
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
            
            # Log security event
            await self.log_security_event(
                event_type='admin_action',
                action='emergency_stop',
                details={'component': component, 'reason': reason, 'admin': admin_user},
                status='success'
            )
            
            logger.critical(f"EMERGENCY STOP: {component} stopped by {admin_user}: {reason}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error executing emergency stop: {e}")
            return False
    
    async def reactivate_component(
        self,
        component: str,
        admin_user: str
    ) -> bool:
        """
        Reactivate stopped component
        
        Args:
            component: Component to reactivate
            admin_user: Admin user
        
        Returns:
            True if successful
        """
        try:
            self.db.client.table('system_status')\
                .update({
                    'status': 'active',
                    'reason': None,
                    'updated_by': admin_user,
                    'updated_at': datetime.utcnow().isoformat()
                })\
                .eq('component', component)\
                .execute()
            
            # Log admin action
            self.db.client.table('admin_actions').insert({
                'admin_user': admin_user,
                'action_type': 'reactivate_component',
                'new_value': {'component': component},
                'reason': 'Component reactivated',
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"Component reactivated: {component} by {admin_user}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error reactivating component: {e}")
            return False
    
    async def check_settlement_duplicate(
        self,
        market_id: str,
        fight_id: str
    ) -> bool:
        """
        Check if settlement already executed (prevent duplicates)
        
        Args:
            market_id: Market UUID
            fight_id: Fight UUID
        
        Returns:
            True if duplicate, False if safe to proceed
        """
        try:
            response = self.db.client.table('settlement_executions')\
                .select('id', count='exact')\
                .eq('market_id', market_id)\
                .eq('status', 'completed')\
                .execute()
            
            return response.count > 0 if response.count else False
        
        except Exception as e:
            logger.error(f"Error checking settlement duplicate: {e}")
            # Fail safe - assume duplicate to prevent double settlement
            return True
    
    async def record_settlement(
        self,
        market_id: str,
        fight_id: str,
        executed_by: str,
        result_payload: Dict
    ) -> Optional[str]:
        """
        Record settlement execution (prevents duplicates)
        
        Args:
            market_id: Market UUID
            fight_id: Fight UUID
            executed_by: User/system executing settlement
            result_payload: Settlement result
        
        Returns:
            Execution ID if successful, None if duplicate
        """
        try:
            # Check for duplicate
            if await self.check_settlement_duplicate(market_id, fight_id):
                logger.warning(f"Duplicate settlement blocked: market={market_id}")
                
                # Log blocked event
                await self.log_security_event(
                    event_type='settlement',
                    action='duplicate_settlement_blocked',
                    resource_type='market',
                    resource_id=market_id,
                    details={'fight_id': fight_id},
                    status='blocked'
                )
                
                return None
            
            # Generate execution hash
            execution_hash = hashlib.md5(f"{market_id}{fight_id}".encode()).hexdigest()
            
            # Record execution
            response = self.db.client.table('settlement_executions').insert({
                'market_id': market_id,
                'fight_id': fight_id,
                'execution_hash': execution_hash,
                'executed_by': executed_by,
                'result_payload': result_payload,
                'status': 'completed',
                'executed_at': datetime.utcnow().isoformat()
            }).execute()
            
            if not response.data:
                return None
            
            execution_id = response.data[0]['id']
            
            # Log settlement
            await self.log_security_event(
                event_type='settlement',
                action='market_settled',
                resource_type='market',
                resource_id=market_id,
                details={'fight_id': fight_id, 'execution_id': execution_id},
                status='success'
            )
            
            return execution_id
        
        except Exception as e:
            logger.error(f"Error recording settlement: {e}")
            return None
    
    async def record_fantasy_computation(
        self,
        fight_id: str,
        profile_id: str,
        client_id: Optional[str],
        result: Dict
    ) -> str:
        """
        Record fantasy computation for audit
        
        Args:
            fight_id: Fight UUID
            profile_id: Fantasy profile
            client_id: Client UUID (optional)
            result: Computation result
        
        Returns:
            Computation ID
        """
        try:
            # Generate computation hash
            comp_hash = hashlib.md5(f"{fight_id}{profile_id}{datetime.utcnow().isoformat()}".encode()).hexdigest()
            
            response = self.db.client.table('fantasy_computations').insert({
                'fight_id': fight_id,
                'profile_id': profile_id,
                'computation_hash': comp_hash,
                'client_id': client_id,
                'result': result,
                'computed_at': datetime.utcnow().isoformat()
            }).execute()
            
            if response.data:
                computation_id = response.data[0]['id']
                
                # Log computation
                await self.log_security_event(
                    event_type='fantasy_compute',
                    action='fantasy_calculated',
                    client_id=client_id,
                    resource_type='fight',
                    resource_id=fight_id,
                    details={'profile': profile_id, 'computation_id': computation_id},
                    status='success'
                )
                
                return computation_id
            
            return comp_hash
        
        except Exception as e:
            logger.error(f"Error recording fantasy computation: {e}")
            return 'error'
    
    def get_fantasy_profile_fallback(self, requested_profile: str) -> str:
        """
        Fail-safe: Return fallback profile if requested profile missing
        
        Args:
            requested_profile: Requested fantasy profile
        
        Returns:
            Valid profile (requested or fallback)
        """
        valid_profiles = [
            'fantasy.basic',
            'fantasy.advanced',
            'sportsbook.pro'
        ]
        
        if requested_profile in valid_profiles:
            return requested_profile
        
        logger.warning(f"Invalid fantasy profile '{requested_profile}', falling back to fantasy.basic")
        return 'fantasy.basic'
