"""
Auth RBAC - Middleware & Decorators
"""

from functools import wraps
from fastapi import HTTPException, Header
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

from .models import ROLE_PERMISSIONS

def check_permission(user_role: str, required_permission: str) -> bool:
    """
    Check if user role has required permission
    
    Args:
        user_role: User's role
        required_permission: Permission to check
    
    Returns:
        True if allowed, False otherwise
    """
    if user_role == "admin":
        return True  # Admin has all permissions
    
    role_perms = ROLE_PERMISSIONS.get(user_role, [])
    
    # Check exact match
    if required_permission in role_perms:
        return True
    
    # Check wildcard (e.g., "view:*" matches "view:bouts")
    for perm in role_perms:
        if perm.endswith(":*"):
            prefix = perm[:-1]
            if required_permission.startswith(prefix):
                return True
    
    return False

def require_role(allowed_roles: List[str]):
    """
    Decorator to require specific roles
    
    Usage:
        @require_role(["admin", "supervisor"])
        async def admin_only_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, x_user_role: Optional[str] = Header(None), **kwargs):
            if not x_user_role:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            if x_user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required roles: {allowed_roles}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_permission(permission: str):
    """
    Decorator to require specific permission
    
    Usage:
        @require_permission("lock:scores")
        async def lock_score_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, x_user_role: Optional[str] = Header(None), **kwargs):
            if not x_user_role:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            if not check_permission(x_user_role, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required permission: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
