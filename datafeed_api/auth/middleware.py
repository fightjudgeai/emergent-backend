"""
API Key Authentication Middleware
"""

import logging
from typing import Optional, Tuple
from fastapi import HTTPException, status
from datetime import datetime

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Handles API key authentication and scope validation"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Validate API key and return scope
        
        Returns:
            (is_valid, scope, client_info)
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, name, scope, active, rate_limit_per_min
                    FROM api_clients
                    WHERE api_key = $1 AND active = TRUE
                    """,
                    api_key
                )
                
                if not row:
                    return False, None, None
                
                # Update last_used_at
                await conn.execute(
                    "UPDATE api_clients SET last_used_at = NOW() WHERE id = $1",
                    row['id']
                )
                
                client_info = {
                    'id': str(row['id']),
                    'name': row['name'],
                    'scope': row['scope'],
                    'rate_limit': row['rate_limit_per_min']
                }
                
                return True, row['scope'], client_info
        
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False, None, None
    
    def check_field_access(self, scope: str, field: str) -> bool:
        """
        Check if scope has access to specific field
        
        Scope hierarchy:
        - fantasy.basic: strikes, sig_strikes, knockdowns, control_sec, round_locked
        - fantasy.advanced: + ai_damage, ai_win_prob
        - sportsbook.pro: all fields + timeline + audit logs
        """
        basic_fields = {
            'strikes', 'sig_strikes', 'knockdowns', 'control_sec',
            'round_locked', 'fight_code', 'event_code', 'round', 'seq', 'ts_ms'
        }
        
        advanced_fields = basic_fields | {'ai_damage', 'ai_win_prob'}
        
        if scope == 'fantasy.basic':
            return field in basic_fields
        elif scope == 'fantasy.advanced':
            return field in advanced_fields
        elif scope == 'sportsbook.pro':
            return True  # Full access
        
        return False
    
    def filter_payload_by_scope(self, payload: dict, scope: str) -> dict:
        """
        Filter payload fields based on API key scope
        """
        if scope == 'sportsbook.pro':
            return payload  # No filtering
        
        filtered = payload.copy()
        
        # Filter state fields
        if 'state' in filtered:
            for corner in ['red', 'blue']:
                if corner in filtered['state']:
                    corner_data = filtered['state'][corner].copy()
                    
                    # Remove AI fields for basic scope
                    if scope == 'fantasy.basic':
                        corner_data.pop('ai_damage', None)
                        corner_data.pop('ai_win_prob', None)
                    
                    filtered['state'][corner] = corner_data
        
        return filtered


async def verify_api_key(api_key: str, auth_middleware: AuthMiddleware) -> dict:
    """
    FastAPI dependency for API key verification
    """
    is_valid, scope, client_info = await auth_middleware.validate_api_key(api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    return client_info
