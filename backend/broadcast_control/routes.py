"""
Broadcast Control - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from .broadcast_engine import BroadcastEngine
from .models import (
    Camera,
    CameraLayout,
    GraphicsOverlay,
    SponsorLogo,
    BroadcastConfig,
    LowerThird,
    Scoreboard
)

logger = logging.getLogger(__name__)

broadcast_control_api = APIRouter(tags=["Broadcast Control"])
broadcast_engine: Optional[BroadcastEngine] = None

def get_broadcast_engine():
    if broadcast_engine is None:
        raise HTTPException(status_code=500, detail="Broadcast engine not initialized")
    return broadcast_engine

# ============================================================================
# Camera Management
# ============================================================================

@broadcast_control_api.post("/broadcast/cameras", response_model=Camera, status_code=201)
async def register_camera(camera: Camera):
    """Register a camera feed"""
    engine = get_broadcast_engine()
    return await engine.register_camera(camera)

@broadcast_control_api.get("/broadcast/cameras", response_model=List[Camera])
async def list_cameras():
    """List all registered cameras"""
    engine = get_broadcast_engine()
    return await engine.list_cameras()

@broadcast_control_api.get("/broadcast/cameras/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str):
    """Get camera by ID"""
    engine = get_broadcast_engine()
    camera = await engine.get_camera(camera_id)
    
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")
    
    return camera

@broadcast_control_api.post("/broadcast/cameras/{camera_id}/activate")
async def activate_camera(camera_id: str):
    """Switch to this camera as the active feed"""
    engine = get_broadcast_engine()
    success = await engine.switch_active_camera(camera_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")
    
    return {"success": True, "active_camera_id": camera_id}

# ============================================================================
# Camera Layouts
# ============================================================================

@broadcast_control_api.post("/broadcast/layouts", response_model=CameraLayout, status_code=201)
async def create_layout(layout: CameraLayout):
    """
    Create a camera layout
    
    Supports: single, pip, split_screen, quad, custom
    """
    engine = get_broadcast_engine()
    return await engine.create_layout(layout)

@broadcast_control_api.post("/broadcast/layouts/{layout_id}/activate")
async def activate_layout(layout_id: str):
    """Activate a camera layout"""
    engine = get_broadcast_engine()
    success = await engine.activate_layout(layout_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Layout not found: {layout_id}")
    
    return {"success": True, "active_layout_id": layout_id}

# ============================================================================
# Graphics Overlays
# ============================================================================

@broadcast_control_api.post("/broadcast/overlays", response_model=GraphicsOverlay, status_code=201)
async def create_overlay(overlay: GraphicsOverlay):
    """Create a graphics overlay"""
    engine = get_broadcast_engine()
    return await engine.create_overlay(overlay)

@broadcast_control_api.post("/broadcast/overlays/lower_third", response_model=GraphicsOverlay, status_code=201)
async def create_lower_third(data: LowerThird):
    """
    Create a lower third overlay
    
    Shows fighter name, record, country, etc.
    """
    engine = get_broadcast_engine()
    return await engine.create_lower_third(data)

@broadcast_control_api.post("/broadcast/overlays/scoreboard", response_model=GraphicsOverlay, status_code=201)
async def create_scoreboard(data: Scoreboard):
    """
    Create a scoreboard overlay
    
    Shows current scores, round, time
    """
    engine = get_broadcast_engine()
    return await engine.create_scoreboard(data)

@broadcast_control_api.post("/broadcast/overlays/{overlay_id}/show")
async def show_overlay(overlay_id: str):
    """Show an overlay"""
    engine = get_broadcast_engine()
    success = await engine.show_overlay(overlay_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Overlay not found: {overlay_id}")
    
    return {"success": True, "overlay_id": overlay_id, "visible": True}

@broadcast_control_api.post("/broadcast/overlays/{overlay_id}/hide")
async def hide_overlay(overlay_id: str):
    """Hide an overlay"""
    engine = get_broadcast_engine()
    success = await engine.hide_overlay(overlay_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Overlay not found: {overlay_id}")
    
    return {"success": True, "overlay_id": overlay_id, "visible": False}

# ============================================================================
# Sponsor Management
# ============================================================================

@broadcast_control_api.post("/broadcast/sponsors", response_model=SponsorLogo, status_code=201)
async def add_sponsor(sponsor: SponsorLogo):
    """Add a sponsor logo"""
    engine = get_broadcast_engine()
    return await engine.add_sponsor(sponsor)

@broadcast_control_api.get("/broadcast/sponsors/active")
async def get_active_sponsors(during_round: bool = False):
    """
    Get sponsors that should be displayed
    
    Args:
        during_round: True if during a round, False if between rounds
    """
    engine = get_broadcast_engine()
    sponsors = await engine.get_active_sponsors(during_round)
    
    return {
        "during_round": during_round,
        "sponsors": sponsors,
        "count": len(sponsors)
    }

# ============================================================================
# Broadcast Configuration
# ============================================================================

@broadcast_control_api.get("/broadcast/config/{bout_id}", response_model=BroadcastConfig)
async def get_broadcast_config(bout_id: str):
    """Get broadcast configuration for a bout"""
    engine = get_broadcast_engine()
    config = await engine.get_broadcast_config(bout_id)
    
    if not config:
        # Return default config
        return BroadcastConfig(bout_id=bout_id)
    
    return config

@broadcast_control_api.post("/broadcast/config", response_model=BroadcastConfig)
async def update_broadcast_config(config: BroadcastConfig):
    """Update broadcast configuration"""
    engine = get_broadcast_engine()
    return await engine.update_broadcast_config(config)

# ============================================================================
# Quick Actions
# ============================================================================

@broadcast_control_api.post("/broadcast/quick/show_fighter_intro")
async def show_fighter_intro(
    fighter_name: str,
    nickname: Optional[str] = None,
    record: str = "0-0-0",
    weight_class: str = "Unknown",
    country: Optional[str] = None
):
    """
    Quick action: Show fighter introduction lower third
    """
    engine = get_broadcast_engine()
    
    lower_third = LowerThird(
        fighter_name=fighter_name,
        nickname=nickname,
        record=record,
        weight_class=weight_class,
        country=country
    )
    
    overlay = await engine.create_lower_third(lower_third)
    await engine.show_overlay(overlay.id)
    
    return {
        "success": True,
        "overlay_id": overlay.id,
        "message": f"Showing intro for {fighter_name}"
    }

@broadcast_control_api.post("/broadcast/quick/update_scoreboard")
async def update_scoreboard(
    fighter_1_name: str,
    fighter_1_score: int,
    fighter_2_name: str,
    fighter_2_score: int,
    current_round: int,
    total_rounds: int,
    time_remaining: str
):
    """
    Quick action: Update scoreboard
    """
    engine = get_broadcast_engine()
    
    scoreboard = Scoreboard(
        fighter_1_name=fighter_1_name,
        fighter_1_score=fighter_1_score,
        fighter_2_name=fighter_2_name,
        fighter_2_score=fighter_2_score,
        current_round=current_round,
        total_rounds=total_rounds,
        time_remaining=time_remaining
    )
    
    overlay = await engine.create_scoreboard(scoreboard)
    await engine.show_overlay(overlay.id)
    
    return {
        "success": True,
        "overlay_id": overlay.id,
        "message": "Scoreboard updated"
    }

@broadcast_control_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Broadcast Control", "version": "1.0.0"}
