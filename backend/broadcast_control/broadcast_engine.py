"""
Broadcast Control - Broadcast Engine
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone
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


class BroadcastEngine:
    """Engine for managing broadcast production"""
    
    def __init__(self, db=None):
        self.db = db
        
        # In-memory state
        self.cameras: Dict[str, Camera] = {}
        self.layouts: Dict[str, CameraLayout] = {}
        self.overlays: Dict[str, GraphicsOverlay] = {}
        self.sponsors: Dict[str, SponsorLogo] = {}
        
        self.current_bout_config: Optional[BroadcastConfig] = None
    
    async def register_camera(self, camera: Camera) -> Camera:
        """Register a camera feed"""
        self.cameras[camera.id] = camera
        
        if self.db:
            try:
                camera_dict = camera.model_dump()
                camera_dict['created_at'] = camera_dict['created_at'].isoformat()
                await self.db.cameras.insert_one(camera_dict)
                logger.info(f"Camera registered: {camera.name} [{camera.position}]")
            except Exception as e:
                logger.error(f"Error storing camera: {e}")
        
        return camera
    
    async def get_camera(self, camera_id: str) -> Optional[Camera]:
        """Get camera by ID"""
        if camera_id in self.cameras:
            return self.cameras[camera_id]
        
        if self.db:
            try:
                camera_dict = await self.db.cameras.find_one({"id": camera_id}, {"_id": 0})
                if camera_dict:
                    camera_dict['created_at'] = datetime.fromisoformat(camera_dict['created_at'])
                    camera = Camera(**camera_dict)
                    self.cameras[camera_id] = camera
                    return camera
            except Exception as e:
                logger.error(f"Error fetching camera: {e}")
        
        return None
    
    async def list_cameras(self) -> List[Camera]:
        """List all cameras"""
        if self.db:
            try:
                cursor = self.db.cameras.find({}, {"_id": 0})
                cameras_dict = await cursor.to_list(length=100)
                
                return [
                    Camera(**{**c, 'created_at': datetime.fromisoformat(c['created_at'])})
                    for c in cameras_dict
                ]
            except Exception as e:
                logger.error(f"Error listing cameras: {e}")
        
        return list(self.cameras.values())
    
    async def switch_active_camera(self, camera_id: str) -> bool:
        """Switch the active camera"""
        camera = await self.get_camera(camera_id)
        if not camera:
            return False
        
        # Deactivate all cameras
        for cam in self.cameras.values():
            cam.is_active = False
        
        # Activate selected camera
        camera.is_active = True
        self.cameras[camera_id] = camera
        
        logger.info(f"Switched to camera: {camera.name}")
        return True
    
    async def create_layout(self, layout: CameraLayout) -> CameraLayout:
        """Create a camera layout"""
        self.layouts[layout.id] = layout
        
        if self.db:
            try:
                await self.db.camera_layouts.insert_one(layout.model_dump())
            except Exception as e:
                logger.error(f"Error storing layout: {e}")
        
        return layout
    
    async def activate_layout(self, layout_id: str) -> bool:
        """Activate a camera layout"""
        if layout_id not in self.layouts:
            return False
        
        # Deactivate all layouts
        for layout in self.layouts.values():
            layout.is_active = False
        
        # Activate selected layout
        self.layouts[layout_id].is_active = True
        
        logger.info(f"Activated layout: {self.layouts[layout_id].name}")
        return True
    
    async def create_overlay(self, overlay: GraphicsOverlay) -> GraphicsOverlay:
        """Create a graphics overlay"""
        self.overlays[overlay.id] = overlay
        
        if self.db:
            try:
                overlay_dict = overlay.model_dump()
                overlay_dict['created_at'] = overlay_dict['created_at'].isoformat()
                await self.db.graphics_overlays.insert_one(overlay_dict)
                logger.info(f"Overlay created: {overlay.overlay_type}")
            except Exception as e:
                logger.error(f"Error storing overlay: {e}")
        
        return overlay
    
    async def show_overlay(self, overlay_id: str) -> bool:
        """Show an overlay"""
        if overlay_id not in self.overlays:
            return False
        
        self.overlays[overlay_id].is_visible = True
        logger.info(f"Showing overlay: {overlay_id}")
        return True
    
    async def hide_overlay(self, overlay_id: str) -> bool:
        """Hide an overlay"""
        if overlay_id not in self.overlays:
            return False
        
        self.overlays[overlay_id].is_visible = False
        logger.info(f"Hiding overlay: {overlay_id}")
        return True
    
    async def create_lower_third(self, data: LowerThird) -> GraphicsOverlay:
        """Create a lower third overlay"""
        overlay = GraphicsOverlay(
            overlay_type="lower_third",
            template_data=data.model_dump(),
            position_x=50,
            position_y=900,
            width=800,
            height=120,
            auto_hide_after_ms=data.duration_ms
        )
        
        return await self.create_overlay(overlay)
    
    async def create_scoreboard(self, data: Scoreboard) -> GraphicsOverlay:
        """Create a scoreboard overlay"""
        overlay = GraphicsOverlay(
            overlay_type="scoreboard",
            template_data=data.model_dump(),
            position_x=660,
            position_y=50,
            width=600,
            height=150
        )
        
        return await self.create_overlay(overlay)
    
    async def add_sponsor(self, sponsor: SponsorLogo) -> SponsorLogo:
        """Add a sponsor logo"""
        self.sponsors[sponsor.id] = sponsor
        
        if self.db:
            try:
                await self.db.sponsor_logos.insert_one(sponsor.model_dump())
                logger.info(f"Sponsor added: {sponsor.sponsor_name}")
            except Exception as e:
                logger.error(f"Error storing sponsor: {e}")
        
        return sponsor
    
    async def get_active_sponsors(self, during_round: bool = False) -> List[SponsorLogo]:
        """Get sponsors that should be displayed"""
        active = []
        
        for sponsor in self.sponsors.values():
            if not sponsor.is_active:
                continue
            
            if during_round and sponsor.show_during_rounds:
                active.append(sponsor)
            elif not during_round and sponsor.show_between_rounds:
                active.append(sponsor)
        
        # Sort by rotation order
        active.sort(key=lambda s: s.rotation_order)
        return active
    
    async def get_broadcast_config(self, bout_id: str) -> Optional[BroadcastConfig]:
        """Get broadcast configuration for a bout"""
        if self.current_bout_config and self.current_bout_config.bout_id == bout_id:
            return self.current_bout_config
        
        if self.db:
            try:
                config_dict = await self.db.broadcast_configs.find_one(
                    {"bout_id": bout_id},
                    {"_id": 0}
                )
                
                if config_dict:
                    config_dict['updated_at'] = datetime.fromisoformat(config_dict['updated_at'])
                    self.current_bout_config = BroadcastConfig(**config_dict)
                    return self.current_bout_config
            except Exception as e:
                logger.error(f"Error fetching config: {e}")
        
        return None
    
    async def update_broadcast_config(self, config: BroadcastConfig) -> BroadcastConfig:
        """Update broadcast configuration"""
        self.current_bout_config = config
        config.updated_at = datetime.now(timezone.utc)
        
        if self.db:
            try:
                config_dict = config.model_dump()
                config_dict['updated_at'] = config_dict['updated_at'].isoformat()
                
                await self.db.broadcast_configs.update_one(
                    {"bout_id": config.bout_id},
                    {"$set": config_dict},
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Error updating config: {e}")
        
        return config
