"""
Real-Time CV - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
import uuid

class VideoFrame(BaseModel):
    """Single video frame for analysis"""
    frame_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    camera_id: str
    timestamp_ms: int
    frame_number: int
    
    # Frame data (base64 encoded or URL)
    frame_data: Optional[str] = None
    frame_url: Optional[str] = None
    
    # Resolution
    width: int = 1920
    height: int = 1080
    
class PoseKeypoints(BaseModel):
    """Pose estimation keypoints"""
    frame_id: str
    fighter_id: str
    
    # MediaPipe/OpenPose keypoints (33 points)
    keypoints: List[Dict[str, float]]  # [{x, y, z, visibility}]
    
    # Confidence
    detection_confidence: float
    
    # Derived metrics
    stance: Optional[Literal["orthodox", "southpaw", "neutral"]] = None
    guard_up: bool = False
    body_rotation: Optional[float] = None
    
class ActionDetection(BaseModel):
    """Detected action from video"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    frame_id: str
    bout_id: str
    timestamp_ms: int
    
    # Action classification
    action_type: Literal[
        "punch_thrown", "kick_thrown", "knee_thrown", "elbow_thrown",
        "takedown_attempt", "clinch_engaged", "ground_position",
        "submission_attempt", "strike_landed", "block", "slip"
    ]
    
    # Fighter info
    fighter_id: str
    
    # Confidence (0-1)
    confidence: float
    
    # Pose data
    pose_before: Optional[PoseKeypoints] = None
    pose_during: Optional[PoseKeypoints] = None
    
    # Analysis
    velocity_estimate: Optional[float] = None
    power_estimate: Optional[float] = None
    
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StreamConfig(BaseModel):
    """Video stream configuration"""
    stream_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    camera_id: str
    
    # Stream source
    stream_url: str
    stream_type: Literal["rtsp", "rtmp", "http", "webcam"]
    
    # Processing config
    fps_target: int = 30
    analysis_fps: int = 10  # Analyze every 3rd frame
    
    # CV models to use
    enable_pose_estimation: bool = True
    enable_action_detection: bool = True
    enable_object_tracking: bool = True
    
    # Output
    save_frames: bool = False
    save_detections: bool = True
    
    is_active: bool = False

class CVModelInfo(BaseModel):
    """CV model information"""
    model_id: str
    model_name: str
    model_type: Literal["pose_estimation", "action_recognition", "object_detection"]
    
    # Model details
    framework: Literal["mediapipe", "openpose", "yolo", "custom"]
    version: str
    
    # Performance
    inference_time_ms: float
    accuracy: Optional[float] = None
    
    # Status
    is_loaded: bool = False
    last_used: Optional[datetime] = None
