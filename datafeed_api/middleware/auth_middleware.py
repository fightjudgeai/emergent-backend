"""
Authentication and Rate Limiting Middleware
Processes all requests for API key validation and rate limiting
"""

import logging
import time
from datetime import datetime
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication and rate limiting
    
    Processes requests in this order:
    1. Check if endpoint is public (no auth required)
    2. Validate API key
    3. Check tier access permissions
    4. Check rate limits (minute, hour, day)
    5. Log API usage
    """
    
    # Endpoints that don't require authentication
    PUBLIC_ENDPOINTS = [
        '/health',
        '/docs',
        '/redoc',
        '/openapi.json',
        '/',
        '/v1/public/fight/',
        '/v1/public/fighter/',
        '/v1/public/fights'
    ]
    
    def __init__(self, app, auth_service):
        """
        Initialize middleware
        
        Args:
            app: FastAPI application
            auth_service: APIKeyAuth service instance
        """
        super().__init__(app)
        self.auth_service = auth_service
    
    def is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no auth required)"""
        # Exact match
        if path in self.PUBLIC_ENDPOINTS:
            return True
        
        # Prefix match for public endpoints
        for public_path in self.PUBLIC_ENDPOINTS:
            if path.startswith(public_path):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication and rate limiting"""
        start_time = time.time()
        
        # Skip auth for public endpoints
        if self.is_public_endpoint(request.url.path):
            response = await call_next(request)
            return response
        
        # Extract API key from headers
        api_key = request.headers.get('X-API-Key') or request.headers.get('x-api-key')
        
        # Also check Authorization header (Bearer token)
        if not api_key:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                api_key = auth_header.replace('Bearer ', '')
        
        # Require API key for non-public endpoints
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "API key required. Provide X-API-Key header or Authorization: Bearer <key>",
                    "error": "unauthorized"
                },
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # Validate API key
        is_valid, tier, client_info = await self.auth_service.validate_api_key(api_key)
        
        if not is_valid:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Invalid or inactive API key",
                    "error": "unauthorized"
                },
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # Check tier access to endpoint
        if not self.auth_service.check_endpoint_access(tier, request.url.path):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": f"Tier '{tier}' does not have access to this endpoint",
                    "error": "forbidden",
                    "tier": tier,
                    "endpoint": request.url.path,
                    "upgrade": "Consider upgrading your tier for access"
                }
            )
        
        # Check rate limits (minute, hour, day)
        client_id = client_info['id']
        
        # Check per-minute limit
        is_allowed_minute, count_minute, limit_minute, reset_minute = await self.auth_service.check_rate_limit(
            client_id,
            'minute',
            client_info['rate_limit_per_minute']
        )
        
        if not is_allowed_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "error": "rate_limit_exceeded",
                    "period": "minute",
                    "limit": limit_minute,
                    "current": count_minute,
                    "reset_at": reset_minute.isoformat()
                },
                headers={
                    "X-RateLimit-Limit": str(limit_minute),
                    "X-RateLimit-Remaining": str(max(0, limit_minute - count_minute)),
                    "X-RateLimit-Reset": str(int(reset_minute.timestamp())),
                    "Retry-After": str(int((reset_minute - datetime.utcnow()).total_seconds()))
                }
            )
        
        # Check per-hour limit
        is_allowed_hour, count_hour, limit_hour, reset_hour = await self.auth_service.check_rate_limit(
            client_id,
            'hour',
            client_info['rate_limit_per_hour']
        )
        
        if not is_allowed_hour:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Hourly rate limit exceeded",
                    "error": "rate_limit_exceeded",
                    "period": "hour",
                    "limit": limit_hour,
                    "current": count_hour,
                    "reset_at": reset_hour.isoformat()
                }
            )
        
        # Check per-day limit
        is_allowed_day, count_day, limit_day, reset_day = await self.auth_service.check_rate_limit(
            client_id,
            'day',
            client_info['rate_limit_per_day']
        )
        
        if not is_allowed_day:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Daily rate limit exceeded",
                    "error": "rate_limit_exceeded",
                    "period": "day",
                    "limit": limit_day,
                    "current": count_day,
                    "reset_at": reset_day.isoformat()
                }
            )
        
        # Inject client info into request state for use in endpoints
        request.state.client = client_info
        request.state.tier = tier
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit_minute - count_minute - 1))
        response.headers["X-RateLimit-Reset"] = str(int(reset_minute.timestamp()))
        response.headers["X-Tier"] = tier
        
        # Log API usage (async, don't block response)
        try:
            await self.auth_service.log_api_usage(
                client_id=client_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception as e:
            logger.error(f"Error logging API usage: {e}")
        
        return response
