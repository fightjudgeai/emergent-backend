"""
Branding & Themes - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid

class BrandTheme(BaseModel):
    """Custom brand theme"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    organization: str = "Default Organization"
    
    # Colors
    primary_color: str = "#FF0000"
    secondary_color: str = "#000000"
    accent_color: str = "#FFFFFF"
    background_color: str = "#1a1a1a"
    text_color: str = "#FFFFFF"
    
    # Logo
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    
    # Typography
    font_family: str = "Arial, sans-serif"
    heading_font: str = "Arial, sans-serif"
    
    # Custom CSS
    custom_css: Optional[str] = None
    
    is_active: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
