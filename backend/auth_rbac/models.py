"""
Auth RBAC - Data Models
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid

UserRole = Literal["admin", "supervisor", "operator", "judge", "analyst"]

class User(BaseModel):
    """User model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: UserRole
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RolePermissions(BaseModel):
    """Role-based permissions"""
    role: UserRole
    permissions: List[str]
    description: str

# Default role permissions
ROLE_PERMISSIONS = {
    "admin": [
        "*"  # All permissions
    ],
    "supervisor": [
        "view:all",
        "manage:bouts",
        "manage:judges",
        "view:analytics",
        "export:reports"
    ],
    "operator": [
        "view:bouts",
        "manage:scoring",
        "manage:events",
        "lock:scores"
    ],
    "judge": [
        "view:assigned_bouts",
        "submit:scores",
        "view:own_scores"
    ],
    "analyst": [
        "view:all",
        "view:analytics",
        "export:data"
    ]
}
