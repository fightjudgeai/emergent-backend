"""
FastAPI Dependencies for Authentication and Rate Limiting
Uses dependency injection instead of middleware
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status, Request
from datetime import datetime

logger = logging.getLogger(__name__)

# Global services (set during startup)
_auth_service = None
_security_service = None


def set_auth_service(auth_service):
    """Set global auth service"""
    global _auth_service
    _auth_service = auth_service


def set_security_service(security_service):
    """Set global security service"""
    global _security_service
    _security_service = security_service


async def get_api_key_optional(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Optional API key extraction (for public endpoints with optional fantasy)
    
    Returns:
        Client info if API key provided and valid, None otherwise
    """
    # Extract API key
    api_key = x_api_key
    
    if not api_key and authorization:
        if authorization.startswith('Bearer '):
            api_key = authorization.replace('Bearer ', '')
    
    if not api_key:
        return None
    
    # Validate API key
    is_valid, tier, client_info = await _auth_service.validate_api_key(api_key)
    
    if not is_valid:
        return None
    
    # Check rate limits
    client_id = client_info['id']
    
    is_allowed_minute, count_minute, limit_minute, reset_minute = await _auth_service.check_rate_limit(
        client_id,
        'minute',
        client_info['rate_limit_per_minute']
    )
    
    if not is_allowed_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_minute.timestamp())),
                "Retry-After": str(int((reset_minute - datetime.utcnow()).total_seconds()))
            }
        )
    
    # Log usage
    await _auth_service.log_api_usage(
        client_id=client_id,
        endpoint=request.url.path,
        method=request.method,
        status_code=200,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get('User-Agent')
    )
    
    return client_info


async def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Require valid API key
    
    Returns:
        Client info
    
    Raises:
        HTTPException if no API key or invalid
    """
    # Extract API key
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
    
    # Validate API key
    is_valid, tier, client_info = await _auth_service.validate_api_key(api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Check endpoint access
    if not _auth_service.check_endpoint_access(tier, request.url.path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tier '{tier}' does not have access to this endpoint. Consider upgrading."
        )
    
    # Check rate limits
    client_id = client_info['id']
    
    # Check minute limit
    is_allowed_minute, count_minute, limit_minute, reset_minute = await _auth_service.check_rate_limit(
        client_id,
        'minute',
        client_info['rate_limit_per_minute']
    )
    
    if not is_allowed_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit_minute} requests per minute",
            headers={
                "X-RateLimit-Limit": str(limit_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_minute.timestamp())),
                "Retry-After": str(int((reset_minute - datetime.utcnow()).total_seconds()))
            }
        )
    
    # Check hour limit
    is_allowed_hour, count_hour, limit_hour, reset_hour = await _auth_service.check_rate_limit(
        client_id,
        'hour',
        client_info['rate_limit_per_hour']
    )
    
    if not is_allowed_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Hourly rate limit exceeded: {limit_hour} requests per hour"
        )
    
    # Check day limit
    is_allowed_day, count_day, limit_day, reset_day = await _auth_service.check_rate_limit(
        client_id,
        'day',
        client_info['rate_limit_per_day']
    )
    
    if not is_allowed_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily rate limit exceeded: {limit_day} requests per day"
        )
    
    # Log usage
    await _auth_service.log_api_usage(
        client_id=client_id,
        endpoint=request.url.path,
        method=request.method,
        status_code=200,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get('User-Agent')
    )
    
    return client_info
