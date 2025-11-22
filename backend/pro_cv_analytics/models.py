"""
Professional CV Analytics - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from datetime import datetime, timezone
import uuid

# ============================================================================
# Strike Classification
# ============================================================================

StrikeType = Literal[
    # Punches
    "jab", "cross", "hook", "uppercut", "overhand",
    # Elbows
    "elbow_horizontal", "elbow_vertical", "elbow_spinning",
    # Knees
    "knee_straight", "knee_flying", "knee_clinch",
    # Kicks
    "front_kick", "roundhouse", "side_kick", "back_kick",
    "leg_kick", "body_kick", "head_kick", "spinning_kick"
]

Zone = Literal["head", "body", "legs"]

TargetArea = Literal[
    # Head
    "jaw", "temple", "nose", "eye", "forehead", "ear",
    # Body
    "solar_plexus", "ribs", "liver", "kidney", "sternum",
    # Legs
    "thigh", "calf", "knee", "foot"
]

DefenseType = Literal[
    "block", "parry", "slip", "duck", "roll", "catch", "check"
]


class StrikeEvent(BaseModel):
    """Professional-grade strike event"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    # Fighter info
    attacker_id: str
    defender_id: str
    
    # Strike classification
    strike_type: StrikeType
    hand_foot: Literal["left", "right"] = "right"
    
    # Impact analysis
    zone: Zone
    target_area: TargetArea
    landed: bool  # True if landed, False if missed/blocked
    
    # Power analysis (0-10 scale)
    power_rating: float  # 0.0-10.0
    estimated_force_lbs: Optional[float] = None
    
    # Precision
    accuracy_score: float  # 0.0-1.0 (how clean the landing was)
    
    # Context
    was_counter: bool = False
    in_combination: bool = False
    combo_position: Optional[int] = None  # 1st, 2nd, 3rd strike in combo
    
    # Damage assessment
    caused_visible_damage: bool = False
    caused_knockdown: bool = False
    caused_wobble: bool = False
    
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DefenseEvent(BaseModel):
    """Defense technique detected"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    fighter_id: str
    defense_type: DefenseType
    
    # What was defended
    against_strike_type: Optional[StrikeType] = None
    
    # Effectiveness
    success: bool  # True if defense worked
    effectiveness_score: float  # 0.0-1.0
    
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Ground Game Analysis
# ============================================================================

GroundPosition = Literal[
    # Top positions
    "mount", "side_control", "north_south", "back_control", "half_guard_top",
    # Bottom positions
    "guard_closed", "guard_open", "half_guard_bottom", "turtle",
    # Neutral
    "scramble", "standing"
]

SubmissionType = Literal[
    # Chokes
    "rear_naked_choke", "guillotine", "triangle", "anaconda", "darce", "arm_triangle",
    # Joint locks
    "armbar", "kimura", "americana", "omoplata", "heel_hook", "knee_bar", "ankle_lock"
]


class TakedownEvent(BaseModel):
    """Takedown detected"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    attacker_id: str
    defender_id: str
    
    takedown_type: Literal[
        "single_leg", "double_leg", "body_lock", "hip_throw",
        "suplex", "slam", "trip", "foot_sweep"
    ]
    
    successful: bool
    
    # Result
    resulting_position: Optional[GroundPosition] = None
    
    # Defense
    defense_attempted: bool = False
    sprawl_quality: Optional[float] = None  # 0.0-1.0
    
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GroundPositionTransition(BaseModel):
    """Ground position change"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    fighter_id: str
    
    from_position: GroundPosition
    to_position: GroundPosition
    
    # Who initiated
    initiated_by: Literal["top", "bottom"]
    
    # Transition quality
    transition_speed: Literal["slow", "medium", "explosive"]
    control_maintained: bool
    
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubmissionAttemptPro(BaseModel):
    """Professional submission attempt analysis"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    attacker_id: str
    defender_id: str
    
    submission_type: SubmissionType
    
    # Progression
    setup_position: GroundPosition
    danger_level: float  # 0.0-1.0 (how close to finishing)
    
    # Duration
    start_time_ms: int
    end_time_ms: int
    duration_ms: int
    
    # Result
    result: Literal["success", "escaped", "transitioned", "stalled"]
    escape_method: Optional[str] = None
    
    # Details
    arm_depth: Optional[float] = None  # For chokes (0.0-1.0)
    extension_angle: Optional[float] = None  # For armbars (degrees)
    
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GroundControl(BaseModel):
    """Ground control time analysis"""
    bout_id: str
    round_num: int
    
    fighter_id: str
    total_control_time_ms: int
    
    # Position breakdown
    mount_time_ms: int = 0
    back_control_time_ms: int = 0
    side_control_time_ms: int = 0
    guard_top_time_ms: int = 0
    
    # Activity
    ground_strikes_landed: int = 0
    submission_attempts: int = 0
    position_improvements: int = 0
    

# ============================================================================
# Multi-Camera Strike Correlation
# ============================================================================

class CameraView(BaseModel):
    """Individual camera view data"""
    camera_id: str
    camera_position: Literal["main", "corner_red", "corner_blue", "overhead"]
    
    # 2D coordinates in camera frame
    impact_point_x: float
    impact_point_y: float
    
    # Confidence
    detection_confidence: float  # 0.0-1.0
    
    # Angle data
    camera_angle_degrees: float
    distance_to_fighters_meters: float


class TriangulatedStrike(BaseModel):
    """Strike with multi-camera triangulation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    timestamp_ms: int
    
    # Base strike data
    strike_event: StrikeEvent
    
    # Multi-camera data
    camera_views: List[CameraView]
    
    # 3D triangulation
    impact_point_3d: Optional[Dict[str, float]] = None  # {x, y, z}
    trajectory_angle: Optional[float] = None
    
    # Force estimation from multiple angles
    estimated_velocity_mps: Optional[float] = None  # meters per second
    estimated_force_newtons: Optional[float] = None
    
    triangulation_accuracy: float  # 0.0-1.0


# ============================================================================
# Advanced Metrics & Analytics
# ============================================================================

class DamageHeatmap(BaseModel):
    """Damage accumulation heatmap"""
    bout_id: str
    fighter_id: str  # Fighter receiving damage
    
    # Zone damage scores (0-100)
    head_damage: float = 0.0
    body_damage: float = 0.0
    leg_damage: float = 0.0
    
    # Specific target damage
    target_damage: Dict[str, float] = Field(default_factory=dict)
    
    # Cumulative
    total_damage_score: float = 0.0
    
    # Visual representation data
    heatmap_data: Dict[str, int] = Field(default_factory=dict)  # coordinate -> intensity


class EngagementMetrics(BaseModel):
    """Fight engagement analysis"""
    bout_id: str
    round_num: int
    
    # Activity levels
    total_exchanges: int
    avg_exchange_duration_ms: float
    
    # Distances
    time_at_range_ms: int = 0  # Striking distance
    time_in_clinch_ms: int = 0
    time_on_ground_ms: int = 0
    
    # Pace
    pace_rating: Literal["slow", "moderate", "fast", "frenetic"]
    strikes_per_minute: float
    
    # Momentum
    momentum_shifts: List[int] = Field(default_factory=list)  # Timestamps of shifts


class MomentumAnalysis(BaseModel):
    """Round momentum tracking"""
    bout_id: str
    round_num: int
    
    # Momentum timeline (every 10 seconds)
    timeline: List[Dict] = Field(default_factory=list)  # [{time, fighter_1_momentum, fighter_2_momentum}]
    
    # Momentum shifts
    major_shifts: List[Dict] = Field(default_factory=list)  # [{time, from_fighter, to_fighter, cause}]
    
    # Overall
    dominant_fighter: Optional[str] = None
    dominance_percentage: float = 50.0


class FIEMetrics(BaseModel):
    """Fight Impact Engine metrics (Jabbr/DeepStrike standard)"""
    bout_id: str
    round_num: Optional[int] = None
    fighter_id: str
    
    # Striking metrics
    total_strikes_thrown: int = 0
    total_strikes_landed: int = 0
    strike_accuracy: float = 0.0
    
    # Power metrics
    significant_strikes: int = 0
    power_strikes_landed: int = 0
    avg_strike_power: float = 0.0
    max_strike_power: float = 0.0
    
    # Zone breakdown
    head_strikes_landed: int = 0
    body_strikes_landed: int = 0
    leg_strikes_landed: int = 0
    
    # Strike types
    jabs_landed: int = 0
    power_punches_landed: int = 0
    kicks_landed: int = 0
    knees_landed: int = 0
    elbows_landed: int = 0
    
    # Defense
    strikes_absorbed: int = 0
    strikes_defended: int = 0
    defense_rate: float = 0.0
    
    # Ground game
    takedowns_landed: int = 0
    takedowns_attempted: int = 0
    takedown_accuracy: float = 0.0
    submission_attempts: int = 0
    ground_control_time_sec: float = 0.0
    
    # Damage
    damage_dealt: float = 0.0
    damage_absorbed: float = 0.0
    damage_differential: float = 0.0
    
    # Overall
    dominance_score: float = 0.0  # 0-100
    aggression_rating: float = 0.0  # 0-10
    
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
