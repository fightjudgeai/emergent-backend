"""
CV Analytics Engine - Data Models
Raw CV input and processed output schemas
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ActionType(str, Enum):
    """Raw CV action classifications"""
    PUNCH = "punch"
    KICK = "kick"
    KNEE = "knee"
    ELBOW = "elbow"
    TAKEDOWN = "takedown"
    SUBMISSION = "submission"
    CLINCH = "clinch"
    GROUND_CONTROL = "ground_control"
    KNOCKDOWN = "knockdown"
    STANDUP = "standup"


class ImpactLevel(str, Enum):
    """Impact severity from CV model"""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    CRITICAL = "critical"


class RawCVInput(BaseModel):
    """Raw computer vision model output"""
    # Identifiers
    frame_id: int
    timestamp_ms: int
    camera_id: str
    
    # Detection data
    fighter_id: str  # "fighter_a" or "fighter_b"
    action_type: ActionType
    action_logits: Dict[str, float] = Field(description="Confidence scores for each action class")
    
    # Bounding boxes [x, y, w, h]
    fighter_bbox: List[float]
    impact_point: Optional[Tuple[float, float]] = None
    
    # Keypoints (17 COCO keypoints format)
    keypoints: List[Tuple[float, float, float]] = Field(
        description="[(x, y, confidence), ...] for 17 keypoints"
    )
    
    # Impact detection
    impact_detected: bool = False
    impact_level: Optional[ImpactLevel] = None
    
    # Motion vectors
    motion_vectors: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optical flow vectors {vx, vy, magnitude}"
    )
    
    # Camera metadata
    camera_angle: float = Field(description="Camera angle in degrees")
    camera_distance: float = Field(description="Distance from action in meters")


class AnalyticsOutput(BaseModel):
    """Processed analytics output"""
    # Control metrics
    control_time_estimate: float = Field(description="Estimated control time in seconds")
    
    # Pace/tempo
    pace_score: float = Field(ge=0.0, le=1.0, description="Fight pace (0=slow, 1=fast)")
    tempo_pattern: str = Field(description="high/medium/low/variable")
    
    # Style classification
    fighter_style: str = Field(description="striker/grappler/wrestler/balanced")
    
    # Flurry detection
    flurry_detected: bool = False
    strikes_in_flurry: int = 0
    
    # Damage indicators
    cumulative_damage: float = Field(ge=0.0, le=1.0)
    rocked_probability: float = Field(ge=0.0, le=1.0)
