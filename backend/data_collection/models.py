"""
Data Collection - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime, timezone
import uuid

class TrainingVideo(BaseModel):
    """Video for training dataset"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    video_url: str
    
    # Metadata
    bout_id: Optional[str] = None
    event_name: Optional[str] = None
    fighters: List[str] = Field(default_factory=list)
    
    # Video specs
    duration_sec: float
    fps: int = 30
    resolution: str = "1920x1080"
    
    # Annotation status
    is_annotated: bool = False
    annotation_progress: float = 0.0  # 0-100%
    
    # Quality
    quality_score: Optional[float] = None
    usable_for_training: bool = True
    
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Annotation(BaseModel):
    """Manual annotation for training"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    video_id: str
    frame_number: int
    timestamp_ms: int
    
    # Annotation type
    annotation_type: Literal[
        "strike", "takedown", "submission", "position", "defense", "other"
    ]
    
    # Specific label
    label: str  # e.g., "jab", "cross", "double_leg", "armbar"
    
    # Bounding box (if applicable)
    bbox: Optional[Dict[str, int]] = None  # {x, y, w, h}
    
    # Keypoints (if applicable)
    keypoints: Optional[List[Dict]] = None
    
    # Metadata
    fighter_id: str
    confidence: Literal["low", "medium", "high"] = "high"
    notes: Optional[str] = None
    
    # Annotator info
    annotator_id: str
    annotated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DatasetSplit(BaseModel):
    """Dataset train/val/test split"""
    dataset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str = "1.0.0"
    
    # Videos
    train_videos: List[str] = Field(default_factory=list)
    val_videos: List[str] = Field(default_factory=list)
    test_videos: List[str] = Field(default_factory=list)
    
    # Statistics
    total_videos: int = 0
    total_annotations: int = 0
    total_frames: int = 0
    
    # Class distribution
    class_distribution: Dict[str, int] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ModelTrainingJob(BaseModel):
    """Training job for custom model"""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str
    model_type: Literal["pose_estimation", "action_recognition", "object_detection"]
    
    # Training config
    dataset_id: str
    architecture: str  # e.g., "YOLOv8", "ResNet50", "Transformer"
    hyperparameters: Dict = Field(default_factory=dict)
    
    # Status
    status: Literal["queued", "training", "completed", "failed"] = "queued"
    progress: float = 0.0  # 0-100%
    
    # Results
    accuracy: Optional[float] = None
    loss: Optional[float] = None
    
    # Artifacts
    model_checkpoint_url: Optional[str] = None
    logs_url: Optional[str] = None
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
