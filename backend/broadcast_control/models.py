"""
Broadcast Control - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from datetime import datetime, timezone
import uuid


class Camera(BaseModel):
    """Camera feed configuration"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    feed_url: str
    position: Literal["main", "corner_red", "corner_blue", "overhead", "crowd", "judges"]
    resolution: str = "1920x1080"
    fps: int = 30
    is_active: bool = False
    is_recording: bool = False
    latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CameraLayout(BaseModel):
    """Camera layout configuration"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    layout_type: Literal["single", "pip", "split_screen", "quad", "custom"]
    
    # Camera assignments
    main_camera_id: str
    pip_camera_ids: List[str] = Field(default_factory=list)
    
    # PIP positioning
    pip_position: Literal["top_left", "top_right", "bottom_left", "bottom_right"] = "top_right"
    pip_size: Literal["small", "medium", "large"] = "small"
    
    is_active: bool = False


class GraphicsOverlay(BaseModel):
    """Graphics overlay template"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    overlay_type: Literal[
        "lower_third",
        "scoreboard",
        "round_timer",
        "fighter_stats",
        "sponsor_logo",
        "custom"
    ]
    
    # Content
    template_data: Dict
    
    # Position on screen
    position_x: int = 0  # Pixels from left
    position_y: int = 0  # Pixels from top
    width: int = 400
    height: int = 100
    
    # Styling
    background_color: Optional[str] = None
    text_color: Optional[str] = "#FFFFFF"
    font_family: Optional[str] = "Arial"
    font_size: int = 24
    
    # Behavior
    is_visible: bool = True
    auto_hide_after_ms: Optional[int] = None
    z_index: int = 100
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LowerThird(BaseModel):
    """Lower third overlay"""
    fighter_name: str
    nickname: Optional[str] = None
    record: str  # e.g., "15-3-0"
    weight_class: str
    country: Optional[str] = None
    
    # Styling
    primary_color: str = "#FF0000"
    secondary_color: str = "#000000"
    
    duration_ms: int = 5000


class Scoreboard(BaseModel):
    """Scoreboard overlay"""
    fighter_1_name: str
    fighter_1_score: int
    fighter_2_name: str
    fighter_2_score: int
    
    current_round: int
    total_rounds: int
    time_remaining: str  # "2:45"
    
    is_locked: bool = False


class SponsorLogo(BaseModel):
    """Sponsor logo configuration"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sponsor_name: str
    logo_url: str
    
    # Display settings
    display_duration_ms: int = 10000
    rotation_order: int = 1
    
    # Position
    position: Literal["top_center", "bottom_left", "bottom_right", "corner"] = "bottom_right"
    size: Literal["small", "medium", "large"] = "medium"
    
    # Schedule
    show_between_rounds: bool = True
    show_during_rounds: bool = False
    
    is_active: bool = True


class BroadcastConfig(BaseModel):
    """Complete broadcast configuration"""
    bout_id: str
    active_layout: Optional[str] = None
    active_overlays: List[str] = Field(default_factory=list)
    active_sponsors: List[str] = Field(default_factory=list)
    
    # Settings
    output_resolution: str = "1920x1080"
    output_fps: int = 30
    bitrate_kbps: int = 5000
    
    # Streaming
    is_streaming: bool = False
    stream_url: Optional[str] = None
    stream_key: Optional[str] = None
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BroadcastCommand(BaseModel):
    """Command for broadcast control"""
    command: Literal[
        "start_stream",
        "stop_stream",
        "switch_camera",
        "show_overlay",
        "hide_overlay",
        "show_sponsor",
        "change_layout"
    ]
    parameters: Dict = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
