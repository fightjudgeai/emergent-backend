"""
API Key Authentication and Authorization
Handles API key validation, RBAC, and rate limiting
"""

import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, status, Request
from functools import wraps

logger = logging.getLogger(__name__)


class APIKeyAuth:
    """API Key authentication and authorization service"""
    
    # Access matrix for different tiers
    TIER_PERMISSIONS = {
        'public': {
            'endpoints': ['/v1/public/*'],
            'can_access_fantasy': False,
            'can_access_markets': False,
            'can_access_events': False,
            'can_access_websocket': False,
            'description': 'Public UFCstats-style pages only'
        },
        'dev': {
            'endpoints': ['/v1/public/*', '/v1/fights/*', '/v1/events/*'],
            'can_access_fantasy': False,
            'can_access_markets': False,
            'can_access_events': False,
            'can_access_websocket': False,
            'description': 'Delayed mock stats only'
        },
        'fantasy.basic': {
            'endpoints': ['/v1/public/*', '/v1/fights/*', '/v1/fantasy/*'],
            'can_access_fantasy': True,
            'can_access_markets': False,
            'can_access_events': False,
            'can_access_websocket': True,  # Delayed
            'description': 'Fantasy scoring + delayed WebSocket'
        },
        'fantasy.advanced': {
            'endpoints': ['/v1/public/*', '/v1/fights/*', '/v1/fantasy/*', '/v1/events/*'],
            'can_access_fantasy': True,
            'can_access_markets': False,
            'can_access_events': True,
            'can_access_websocket': True,  # Live
            'description': 'Live fantasy + historical stats'
        },
        'sportsbook.pro': {
            'endpoints': ['/v1/public/*', '/v1/fights/*', '/v1/fantasy/*', '/v1/markets/*', '/v1/events/*'],
            'can_access_fantasy': True,
            'can_access_markets': True,
            'can_access_events': True,
            'can_access_websocket': True,  # Live
            'description': 'Full access: fantasy + markets + WebSocket'
        },
        'promotion.enterprise': {
            'endpoints': ['/*'],  # All endpoints
            'can_access_fantasy': True,
            'can_access_markets': True,
            'can_access_events': True,
            'can_access_websocket': True,
            'can_access_enterprise': True,
            'description': 'Full access + branding + exports'
        }
    }
    
    def __init__(self, db_client):
        """
        Initialize API key auth service
        
        Args:
            db_client: Supabase database client
        """
        self.db = db_client
    
    async def validate_api_key(
        self,
        api_key: str
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate API key and return client info
        
        Args:
            api_key: API key from request header
        
        Returns:
            Tuple of (is_valid, tier, client_info)
        """
        try:
            # Query api_clients table
            response = self.db.client.table('api_clients')\
                .select('id, name, tier, status, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day')\
                .eq('api_key', api_key)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
                return False, None, None
            
            client = response.data[0]
            
            # Check if client is active
            if client['status'] != 'ACTIVE':
                logger.warning(f"Inactive API key attempted: {client['name']} (status: {client['status']})")
                return False, None, None
            
            # Update last_used_at
            self.db.client.table('api_clients')\
                .update({'last_used_at': datetime.utcnow().isoformat()})\
                .eq('id', client['id'])\
                .execute()
            
            client_info = {
                'id': client['id'],
                'name': client['name'],
                'tier': client['tier'],
                'rate_limit_per_minute': client['rate_limit_per_minute'],
                'rate_limit_per_hour': client.get('rate_limit_per_hour', 3600),
                'rate_limit_per_day': client.get('rate_limit_per_day', 50000)
            }
            
            return True, client['tier'], client_info
        
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False, None, None
    
    def check_endpoint_access(self, tier: str, endpoint: str) -> bool:
        """
        Check if tier has access to endpoint
        
        Args:
            tier: Client tier
            endpoint: Request endpoint path
        
        Returns:
            True if access allowed, False otherwise
        """
        if tier not in self.TIER_PERMISSIONS:
            return False
        
        allowed_patterns = self.TIER_PERMISSIONS[tier]['endpoints']
        
        # Check if endpoint matches any allowed pattern
        for pattern in allowed_patterns:
            if pattern == '/*':
                return True
            
            if pattern.endswith('*'):
                prefix = pattern[:-1]
                if endpoint.startswith(prefix):
                    return True
            else:
                if endpoint == pattern:
                    return True
        
        return False
    
    async def check_rate_limit(
        self,
        client_id: str,
        period: str,
        limit: int
    ) -> Tuple[bool, int, int, datetime]:
        """
        Check if client has exceeded rate limit
        
        Args:
            client_id: Client UUID
            period: 'minute', 'hour', or 'day'
            limit: Rate limit for this period
        
        Returns:
            Tuple of (is_allowed, current_count, limit, reset_at)
        """
        try:
            # Calculate cutoff time
            now = datetime.utcnow()
            if period == 'minute':
                cutoff = now - timedelta(minutes=1)
                reset_at = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            elif period == 'hour':
                cutoff = now - timedelta(hours=1)
                reset_at = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            elif period == 'day':
                cutoff = now - timedelta(days=1)
                reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                raise ValueError(f"Invalid period: {period}")
            
            # Count requests in time window
            response = self.db.client.table('api_usage_logs')\
                .select('id', count='exact')\
                .eq('client_id', client_id)\
                .gt('timestamp', cutoff.isoformat())\
                .execute()
            
            current_count = response.count if response.count else 0
            
            is_allowed = current_count < limit
            
            return is_allowed, current_count, limit, reset_at
        
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # On error, allow the request (fail open)
            return True, 0, limit, datetime.utcnow()
    
    async def log_api_usage(
        self,
        client_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log API usage for analytics and rate limiting
        
        Args:
            client_id: Client UUID
            endpoint: Request endpoint
            method: HTTP method
            status_code: Response status code
            response_time_ms: Response time in milliseconds
            ip_address: Client IP address
            user_agent: User agent string
        """
        try:
            self.db.client.table('api_usage_logs').insert({
                'client_id': client_id,
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'response_time_ms': response_time_ms,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
        
        except Exception as e:
            # Don't fail request if logging fails
            logger.error(f"Error logging API usage: {e}")
    
    def get_tier_description(self, tier: str) -> str:
        """Get human-readable description of tier"""
        return self.TIER_PERMISSIONS.get(tier, {}).get('description', 'Unknown tier')


# Dependency for FastAPI endpoints
async def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Dependency to require and validate API key
    
    Accepts API key from either:
    - X-API-Key header
    - Authorization: Bearer {key} header
    
    Returns:
        Client info dictionary
    
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Extract API key from headers
    api_key = x_api_key
    
    if not api_key and authorization:
        if authorization.startswith('Bearer '):
            api_key = authorization.replace('Bearer ', '')
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header or Authorization: Bearer <key>",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # This will be injected by middleware
    # For now, return a placeholder
    return {"api_key": api_key}


def require_tier(required_tier: str):
    """
    Decorator to require specific tier or higher
    
    Tier hierarchy (low to high):
    public < dev < fantasy.basic < fantasy.advanced < sportsbook.pro < promotion.enterprise
    """
    tier_order = ['public', 'dev', 'fantasy.basic', 'fantasy.advanced', 'sportsbook.pro', 'promotion.enterprise']
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Client info should be injected by middleware
            # Check if tier is sufficient
            # This is a placeholder - actual check done in middleware
            return await func(*args, **kwargs)
        return wrapper
    return decorator
