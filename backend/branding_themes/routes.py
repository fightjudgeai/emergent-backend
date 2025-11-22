"""
Branding & Themes - API Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .theme_engine import ThemeEngine
from .models import BrandTheme

logger = logging.getLogger(__name__)

branding_api = APIRouter(tags=["Branding & Themes"])
theme_engine: Optional[ThemeEngine] = None

def get_theme_engine():
    if theme_engine is None:
        raise HTTPException(status_code=500, detail="Theme engine not initialized")
    return theme_engine

@branding_api.post("/branding/themes", response_model=BrandTheme, status_code=201)
async def create_theme(theme: BrandTheme):
    """Create a custom brand theme"""
    engine = get_theme_engine()
    return await engine.create_theme(theme)

@branding_api.post("/branding/themes/{theme_id}/activate")
async def activate_theme(theme_id: str):
    """Activate a theme"""
    engine = get_theme_engine()
    success = await engine.activate_theme(theme_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    return {"success": True, "theme_id": theme_id}

@branding_api.get("/branding/themes/active")
async def get_active_theme():
    """Get active theme"""
    engine = get_theme_engine()
    theme = engine.get_active_theme()
    
    if not theme:
        return {"message": "No active theme"}
    
    return theme

@branding_api.get("/branding/themes/{theme_id}/css")
async def get_theme_css(theme_id: str):
    """Get generated CSS for theme"""
    engine = get_theme_engine()
    
    if theme_id not in engine.themes_cache:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    theme = engine.themes_cache[theme_id]
    css = engine.generate_css(theme)
    
    return {"theme_id": theme_id, "css": css}

@branding_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Branding & Themes", "version": "1.0.0"}
