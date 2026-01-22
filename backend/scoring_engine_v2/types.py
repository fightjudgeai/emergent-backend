"""
Type definitions for Scoring Engine V2
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class QualityTag(str, Enum):
    """Strike quality modifier"""
    LIGHT = "LIGHT"
    SOLID = "SOLID"


class KnockdownTier(str, Enum):
    """Knockdown severity"""
    KD_FLASH = "KD_FLASH"
    KD_HARD = "KD_HARD"
    KD_NF = "KD_NF"  # Near-finish


class SubmissionDepth(str, Enum):
    """Submission attempt depth"""
    LIGHT = "LIGHT"
    DEEP = "DEEP"
    NEAR_FINISH = "NEAR_FINISH"


class ControlType(str, Enum):
    """Control position type"""
    TOP = "TOP"
    BACK = "BACK"
    CAGE = "CAGE"


class Corner(str, Enum):
    """Fighter corner"""
    RED = "RED"
    BLUE = "BLUE"


class Technique(str, Enum):
    """Strike technique types"""
    JAB = "jab"
    CROSS = "cross"
    HOOK = "hook"
    UPPERCUT = "uppercut"
    OVERHAND = "overhand"
    HEAD_KICK = "head_kick"
    BODY_KICK = "body_kick"
    LEG_KICK = "leg_kick"
    ELBOW = "elbow"
    KNEE = "knee"
    GROUND_STRIKE = "ground_strike"
    GROUND_STRIKE_BOTTOM = "ground_strike_bottom"


@dataclass
class StrikeEvent:
    """A single strike event"""
    fighter: Corner
    technique: str
    quality: QualityTag = QualityTag.SOLID
    timestamp: Optional[float] = None
    event_id: Optional[str] = None


@dataclass
class GrapplingEvent:
    """A grappling event (takedown, submission, etc.)"""
    fighter: Corner
    event_type: str  # "takedown", "takedown_stuffed", "submission_attempt"
    depth: Optional[SubmissionDepth] = None  # For submissions
    timestamp: Optional[float] = None
    event_id: Optional[str] = None


@dataclass
class ImpactEvent:
    """A damage/impact event (knockdown, rocked)"""
    fighter: Corner  # Fighter who SCORED the impact
    impact_type: str  # "KD_FLASH", "KD_HARD", "KD_NF", "ROCKED"
    timestamp: Optional[float] = None
    event_id: Optional[str] = None


@dataclass
class ControlWindow:
    """A control time window"""
    fighter: Corner
    control_type: ControlType
    start_time: float
    end_time: float
    duration_seconds: float
    has_offense: bool = False  # Did controlling fighter land SOLID strike or sub attempt?
    offense_events: List[str] = field(default_factory=list)  # Event IDs of offense during window


@dataclass
class ContributionItem:
    """A single scoring contribution for receipts"""
    id: str
    fighter: Corner
    label: str
    points: float
    category: str  # "striking", "grappling", "control", "impact"


@dataclass
class PlanBreakdown:
    """Breakdown of Plan A/B/C scores for one fighter"""
    striking_score: float = 0.0
    grappling_score: float = 0.0
    control_score: float = 0.0
    impact_score: float = 0.0
    plan_a_total: float = 0.0
    plan_b_value: float = 0.0
    plan_c_value: float = 0.0
    
    # Detailed breakdowns
    strike_breakdown: Dict[str, Any] = field(default_factory=dict)
    grappling_breakdown: Dict[str, Any] = field(default_factory=dict)
    control_breakdown: Dict[str, Any] = field(default_factory=dict)
    impact_breakdown: Dict[str, Any] = field(default_factory=dict)
    
    # Counts for gates
    kd_flash_count: int = 0
    kd_hard_count: int = 0
    kd_nf_count: int = 0
    rocked_count: int = 0
    total_kd_count: int = 0
    heavy_strike_count: int = 0  # SOLID heavy strikes
    solid_strike_count: int = 0  # All SOLID strikes
    sub_nf_count: int = 0  # Near-finish submissions


@dataclass
class Verdict:
    """Final round verdict"""
    winner: str  # "RED", "BLUE", "DRAW"
    score_string: str  # "10-9 RED", "10-8 BLUE", "10-10"
    red_points: int
    blue_points: int


@dataclass
class RoundReceipt:
    """Full explainability receipt for a round"""
    round_number: int
    winner: str
    score: str
    
    # Plan breakdowns
    red_plan_a: float
    blue_plan_a: float
    delta_plan_a: float
    
    plan_b_applied: float
    plan_c_applied: float
    plan_b_allowed: bool
    plan_c_allowed: bool
    
    # Impact advantage
    red_has_impact_advantage: bool
    blue_has_impact_advantage: bool
    impact_advantage_reason: str
    
    # Top drivers
    top_drivers: List[ContributionItem]
    
    # Gate messages
    gate_messages: List[str]
    
    # Detailed breakdowns
    red_breakdown: PlanBreakdown
    blue_breakdown: PlanBreakdown


@dataclass
class RoundScoreResult:
    """Complete round scoring result"""
    # Per-fighter totals
    red: PlanBreakdown
    blue: PlanBreakdown
    
    # Deltas
    delta_plan_a: float
    delta_plan_b: float
    delta_plan_c: float
    delta_round: float
    
    # Verdict
    verdict: Verdict
    
    # Receipt
    receipt: RoundReceipt
    
    # Raw counts for backwards compatibility
    total_events: int
    red_kd: int
    blue_kd: int


# Mapping from legacy event types to new types
LEGACY_EVENT_TYPE_MAP = {
    # Strikes
    "Jab": "jab",
    "Cross": "cross", 
    "Hook": "hook",
    "Uppercut": "uppercut",
    "Overhand": "overhand",
    "Head Kick": "head_kick",
    "Body Kick": "body_kick",
    "Leg Kick": "leg_kick",
    "Low Kick": "leg_kick",
    "Kick": "head_kick",  # Default kick to head
    "Elbow": "elbow",
    "Knee": "knee",
    "Ground Strike": "ground_strike",
    
    # Impact
    "KD": "KD",  # Will be mapped based on tier metadata
    "Rocked/Stunned": "ROCKED",
    "Rocked": "ROCKED",
    
    # Grappling
    "TD": "takedown",
    "Takedown": "takedown",
    "Takedown Landed": "takedown",
    "Takedown Stuffed": "takedown_stuffed",
    "Takedown Defended": "takedown_stuffed",
    "Submission Attempt": "submission_attempt",
    
    # Control
    "Top Control": "TOP",
    "Back Control": "BACK",
    "Cage Control": "CAGE",
    "Ground Top Control": "TOP",
    "Ground Back Control": "BACK",
    "Cage Control Time": "CAGE",
    "CTRL_START": "CTRL_START",
    "CTRL_END": "CTRL_END",
}

# Map KD tiers from legacy
LEGACY_KD_TIER_MAP = {
    "Flash": KnockdownTier.KD_FLASH,
    "Hard": KnockdownTier.KD_HARD,
    "Near-Finish": KnockdownTier.KD_NF,
    "NF": KnockdownTier.KD_NF,
}

# Map submission depths from legacy
LEGACY_SUB_DEPTH_MAP = {
    "Light": SubmissionDepth.LIGHT,
    "Standard": SubmissionDepth.LIGHT,
    "Deep": SubmissionDepth.DEEP,
    "Near-Finish": SubmissionDepth.NEAR_FINISH,
    "NF": SubmissionDepth.NEAR_FINISH,
}
