from fastapi import FastAPI, APIRouter, HTTPException, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
import asyncio
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import math
import time
from event_dedup import EventDedupEngine, verify_event_chain
from replay_engine import reconstruct_round_timeline

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# New Scoring Model Configuration
SCORING_CONFIG = {
    "categories": {
        "striking": 50.0,
        "grappling": 40.0,
        "other": 10.0
    },
    "base_values": {
        # Striking - base values per occurrence (before normalization)
        "KD": {"category": "striking", "Near-Finish": 1.00, "Hard": 0.70, "Flash": 0.40},
        "Rocked/Stunned": {"category": "striking", "value": 0.30},
        # Significant strikes (0.10-0.14 range)
        "Cross": {"category": "striking", "sig": 0.14, "non_sig": 0.07},
        "Hook": {"category": "striking", "sig": 0.14, "non_sig": 0.07},
        "Uppercut": {"category": "striking", "sig": 0.14, "non_sig": 0.07},
        "Elbow": {"category": "striking", "sig": 0.14, "non_sig": 0.07},
        "Jab": {"category": "striking", "sig": 0.10, "non_sig": 0.05},
        "Knee": {"category": "striking", "sig": 0.10, "non_sig": 0.05},
        # Grappling - base values per occurrence or per second
        "Submission Attempt": {"category": "grappling", "Near-Finish": 1.00, "Deep": 0.60, "Light": 0.25},
        "Takedown Landed": {"category": "grappling", "value": 0.25},
        "Sweep/Reversal": {"category": "grappling", "value": 0.05},
        "Ground Back Control": {"category": "grappling", "value_per_sec": 0.012},
        "Ground Top Control": {"category": "grappling", "value_per_sec": 0.010},
        # Other - base values
        "Cage Control Time": {"category": "other", "value_per_sec": 0.006},
        "Takedown Stuffed": {"category": "other", "value": 0.04}
    },
    "volume_dampening": {
        "non_sig_strike_threshold": 20,  # Beyond +20 advantage
        "dampening_factor": 0.70  # Excess scores at 70%
    }
}

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize Event Deduplication Engine
dedup_engine = EventDedupEngine(db)

# Initialize Postgres and Redis
from db_utils import init_db, SessionLocal
from redis_utils import init_redis, calibration_pubsub

# Will be initialized on startup
postgres_available = False
redis_available = False

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class EventData(BaseModel):
    bout_id: str
    round_num: int
    fighter: str  # "fighter1" or "fighter2"
    event_type: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

class JudgeScore(BaseModel):
    model_config = ConfigDict(extra="ignore")
    judge_id: str
    judge_name: str
    bout_id: str
    round_num: int
    fighter1_score: int
    fighter2_score: int
    card: str  # "10-9", "10-8", etc.
    locked: bool = False
    locked_at: Optional[datetime] = None

class JudgeScoreLock(BaseModel):
    bout_id: str
    round_num: int
    judge_id: str
    judge_name: str
    fighter1_score: int
    fighter2_score: int
    card: str

class JudgeScoreUnlock(BaseModel):
    bout_id: str
    round_num: int
    judge_id: str
    supervisor_code: str

class ForceCloseRound(BaseModel):
    bout_id: str
    round_num: int
    supervisor_code: str
    closed_by: str

class EventV2(BaseModel):
    """Enhanced event model with deduplication support"""
    bout_id: str
    round_id: int
    judge_id: str
    fighter_id: str  # "fighter1" or "fighter2"
    event_type: str
    timestamp_ms: int
    device_id: str
    metadata: Optional[Dict[str, Any]] = {}

class JudgeSession(BaseModel):
    """Judge session for hot-swap capability"""
    judge_session_id: str
    judge_id: str
    bout_id: str
    round_id: int
    last_event_sequence: int = 0
    session_state: str = "OPEN"  # OPEN, LOCKED, SYNCED
    unsent_event_queue: List[Dict[str, Any]] = []

class DeviceTelemetry(BaseModel):
    """Real-time device health telemetry"""
    device_id: str
    judge_id: str
    bout_id: str
    battery_percent: Optional[int] = None
    network_strength_percent: Optional[int] = None
    latency_ms: Optional[int] = None
    fps: Optional[int] = None
    dropped_event_count: int = 0
    event_rate_per_second: float = 0.0

class ScoreRequest(BaseModel):
    bout_id: str
    round_num: int
    events: List[EventData]
    round_duration: int  # in seconds, typically 300 (5 min)

class Subscores(BaseModel):
    KD: float
    ISS: float
    GCQ: float
    TDQ: float
    SUBQ: float
    OC: float
    AGG: float
    RP: float
    TSR: float

class FighterScore(BaseModel):
    fighter: str
    subscores: Subscores
    final_score: float
    event_counts: Optional[dict] = {}  # Count of events per category

class GateChecks(BaseModel):
    finish_threat: bool
    control_dom: bool
    multi_cat_dom: bool

class RoundReasons(BaseModel):
    delta: float
    gates_winner: GateChecks
    gates_loser: GateChecks
    to_108: bool
    to_107: bool
    draw: bool = False
    tie_breaker: Optional[str] = None  # "damage", "control", "aggression", "technical", "metric_name", or None

class RoundScore(BaseModel):
    bout_id: str
    round_num: int
    fighter1_score: FighterScore
    fighter2_score: FighterScore
    score_gap: float
    card: str  # e.g., "10-9", "10-8", "10-7", "10-10"
    winner: str  # "fighter1", "fighter2", or "DRAW"
    reasons: RoundReasons
    uncertainty: str = "medium_confidence"  # "high_confidence", "medium_confidence", "low_confidence"
    uncertainty_factors: List[str] = []  # Reasons for uncertainty level

# Shadow Judging Models
class TrainingRound(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event: str
    fighters: str
    roundNumber: int
    summary: List[str]
    officialCard: str  # "10-9", "10-8", etc.
    type: str = "historical"
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TrainingRoundCreate(BaseModel):
    event: str
    fighters: str
    roundNumber: int
    summary: List[str]
    officialCard: str

class JudgePerformance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    judgeId: str
    judgeName: str
    roundId: str
    myScore: str
    officialScore: str
    mae: float
    sensitivity108: bool
    accuracy: float
    match: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class JudgePerformanceCreate(BaseModel):
    judgeId: str
    judgeName: str
    roundId: str
    myScore: str
    officialScore: str
    mae: float
    sensitivity108: bool
    accuracy: float
    match: bool

class JudgeStats(BaseModel):
    judgeId: str
    judgeName: str
    totalAttempts: int
    averageAccuracy: float
    averageMAE: float
    sensitivity108Rate: float
    perfectMatches: int

# Fighter Memory Log Models
class FighterTendencies(BaseModel):
    striking_style: dict  # {"head": 0.6, "body": 0.3, "leg": 0.1}
    grappling_rate: float  # 0-1 (0 = pure striker, 1 = pure grappler)
    finish_threat_rate: float  # Rate of rounds with finish threats
    control_preference: float  # 0-1 (preference for control vs striking)
    aggression_level: float  # 0-10 scale

class FighterStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fighter_name: str
    total_rounds: int = 0
    total_fights: int = 0
    # Offensive stats (per round averages)
    avg_kd_per_round: float = 0.0
    avg_ss_per_round: float = 0.0
    avg_td_per_round: float = 0.0
    avg_sub_attempts: float = 0.0
    avg_passes: float = 0.0
    avg_reversals: float = 0.0
    avg_control_time: float = 0.0  # seconds
    # Performance stats
    avg_round_score: float = 0.0
    rounds_won: int = 0
    rounds_lost: int = 0
    rounds_drawn: int = 0
    rate_10_8: float = 0.0  # Rate of 10-8 rounds achieved
    rate_10_7: float = 0.0  # Rate of 10-7 rounds achieved
    # Tendencies
    tendencies: FighterTendencies = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FighterStatsUpdate(BaseModel):
    fighter_name: str
    round_events: List[dict]  # List of events from the round
    round_score: float
    round_result: str  # "won", "lost", "draw"
    control_time: float
    round_card: str  # "10-9", "10-8", etc.

# Discrepancy Flags Models
class DiscrepancyFlag(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    flag_type: str  # "boundary_case", "tie_breaker", "low_activity", "statistical_anomaly"
    severity: str  # "low", "medium", "high"
    description: str
    context: dict  # Additional context data
    status: str = "pending"  # "pending", "under_review", "resolved", "dismissed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime = None
    resolved_by: str = None
    resolution_notes: str = None

class DiscrepancyFlagCreate(BaseModel):
    bout_id: str
    round_num: int
    flag_type: str
    severity: str
    description: str
    context: dict = {}

class FlagResolution(BaseModel):
    resolved_by: str
    resolution_notes: str
    status: str  # "resolved" or "dismissed"

# Tuning Profile Models
class MetricWeights(BaseModel):
    KD: float = 0.30
    ISS: float = 0.20
    TSR: float = 0.15
    GCQ: float = 0.10
    TDQ: float = 0.08
    OC: float = 0.06
    SUBQ: float = 0.05
    AGG: float = 0.05
    RP: float = 0.01

class ScoreThresholds(BaseModel):
    threshold_10_9: int = 600  # 1-600 = 10-9
    threshold_10_8: int = 900  # 601-900 = 10-8
    # 901-1000 = 10-7

class GateSensitivity(BaseModel):
    finish_threat_kd_threshold: float = 1.0
    finish_threat_subq_threshold: float = 8.0
    finish_threat_iss_threshold: float = 9.0
    control_dom_gcq_threshold: float = 7.5
    control_dom_time_share: float = 0.5
    multi_cat_dom_count: int = 3
    multi_cat_dom_score_threshold: float = 7.5

class TuningProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    promotion: str  # "UFC", "Bellator", "ONE Championship", etc.
    description: str = ""
    weights: MetricWeights = Field(default_factory=MetricWeights)
    thresholds: ScoreThresholds = Field(default_factory=ScoreThresholds)
    gate_sensitivity: GateSensitivity = Field(default_factory=GateSensitivity)
    is_default: bool = False
    created_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TuningProfileCreate(BaseModel):
    name: str
    promotion: str
    description: str = ""
    weights: MetricWeights = Field(default_factory=MetricWeights)
    thresholds: ScoreThresholds = Field(default_factory=ScoreThresholds)
    gate_sensitivity: GateSensitivity = Field(default_factory=GateSensitivity)
    created_by: str = ""

class TuningProfileUpdate(BaseModel):
    name: str = None
    description: str = None
    weights: MetricWeights = None
    thresholds: ScoreThresholds = None
    gate_sensitivity: GateSensitivity = None

# Security & Audit Models
class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action_type: str  # "score_calculation", "flag_created", "profile_changed", "judge_action"
    user_id: str
    user_name: str
    resource_type: str  # "round_score", "flag", "profile", "bout"
    resource_id: str
    action_data: dict = {}
    signature: str = ""  # Cryptographic hash for verification
    ip_address: Optional[str] = None
    immutable: bool = True  # WORM - cannot be modified once created

class AuditLogCreate(BaseModel):
    action_type: str
    user_id: str
    user_name: str
    resource_type: str
    resource_id: str
    action_data: dict = {}
    ip_address: Optional[str] = None

class SignatureVerification(BaseModel):
    valid: bool
    signature: str
    computed_signature: str
    message: str

# Helper function to verify owner access
def verify_owner_access(judge_id: str):
    """Verify if the judge is the owner"""
    owner_id = os.environ.get('OWNER_JUDGE_ID', 'owner-001')
    if judge_id != owner_id:
        raise HTTPException(status_code=403, detail="Access denied. Only owner can access audit logs.")
    return True

# Judge Profile Models
class JudgeProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    judgeId: str
    judgeName: str
    organization: str
    email: Optional[str] = None
    certifications: List[str] = []
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    totalRoundsJudged: int = 0
    averageAccuracy: float = 0.0

class JudgeProfileCreate(BaseModel):
    judgeId: str
    judgeName: str
    organization: str
    email: Optional[str] = None
    certifications: List[str] = []

class JudgeProfileUpdate(BaseModel):
    judgeName: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    certifications: Optional[List[str]] = None

# Scoring Engine
class ScoringEngine:
    @staticmethod
    def calculate_subscores(events: List[EventData], fighter: str, round_duration: int, opponent_iss_total: float = 0) -> Subscores:
        # Filter events for this fighter
        fighter_events = [e for e in events if e.fighter == fighter]
        
        # Initialize accumulators
        kd_severities = []
        iss_impacts = []
        ground_iss_impacts = []
        ctrl_segments = []
        td_qualities = []
        sub_attempts = []
        passes = 0
        reversals = 0
        scramble_wins = 0
        total_strikes = 0
        significant_strikes = 0
        
        # Control timer tracking
        ctrl_start_time = None
        ctrl_dom_seconds = 0
        ctrl_eff_seconds = 0
        
        # Process events
        for event in sorted(fighter_events, key=lambda x: x.timestamp):
            etype = event.event_type
            meta = event.metadata or {}
            
            if etype == "KD":
                # KD severity matches TypeScript implementation
                severity_map = {"flash": 1.0, "hard": 1.4, "near-finish": 1.8}
                kd_severities.append(severity_map.get(meta.get("severity", "flash"), 1.0))
            
            elif etype == "Rocked":
                # Rocked/Stunned moment - rated between KD and strikes
                # Score as 0.6 KD equivalent (lower than flash KD which is 1.0)
                kd_severities.append(0.6)
            
            elif etype in ["HS", "BS", "LS"]:
                # Head, Body, and Leg Strikes
                impact_map = {"HS": 1.0, "BS": 0.8, "LS": 0.7}
                impact = impact_map.get(etype, 1.0)
                
                # Check for power strikes
                if meta.get("power_strike"):
                    impact *= 1.2
                if meta.get("rocked"):
                    impact += 0.5
                
                iss_impacts.append(impact)
                significant_strikes += 1
                
                # Track ground strikes for GCQ
                if meta.get("on_ground"):
                    ground_iss_impacts.append(impact)
            
            elif etype == "POSITION_START":
                ctrl_start_time = event.timestamp
                # Store position info for later scoring
                current_position = meta.get("position", "mount")
            
            elif etype == "POSITION_CHANGE":
                # Position change - continue timer, update position
                current_position = meta.get("to", "mount")
            
            elif etype == "POSITION_STOP":
                if ctrl_start_time is not None:
                    duration = meta.get("duration", 0)
                    position = meta.get("position", current_position if 'current_position' in locals() else "mount")
                    
                    # Position-based scoring weights
                    position_weights = {
                        "mount": 1.5,           # Highest - full control, strike capability
                        "back-control": 1.5,    # Highest - finish threat
                        "side-control": 1.2,    # Strong control
                        "half-guard": 0.8,      # Moderate control
                        "closed-guard": 0.6,    # Limited control
                        "open-guard": 0.5,      # Minimal control
                        "standing": 0.7         # Clinch control
                    }
                    
                    weight = position_weights.get(position, 1.0)
                    weighted_duration = duration * weight
                    
                    # Dominant positions get full credit
                    if position in ["mount", "back-control", "side-control"]:
                        ctrl_dom_seconds += weighted_duration
                    else:
                        # Other positions get partial credit
                        ctrl_dom_seconds += weighted_duration * 0.6
                    
                    ctrl_start_time = None
            
            # Legacy CTRL_START/CTRL_STOP support (for backwards compatibility)
            elif etype == "CTRL_START":
                ctrl_start_time = event.timestamp
            
            elif etype == "CTRL_STOP":
                if ctrl_start_time is not None:
                    duration = event.timestamp - ctrl_start_time
                    position = meta.get("position", "top")
                    
                    # Dominant positions
                    if position in ["mount", "back", "top_half", "side_control"]:
                        ctrl_dom_seconds += duration
                    
                    # Effective control (cage/center)
                    if meta.get("effective_control"):
                        ctrl_eff_seconds += duration
                    
                    ctrl_start_time = None
            
            elif etype == "Takedown":
                td_quality = 1.0
                
                # Check for immediate pass within 10s
                if meta.get("immediate_pass"):
                    td_quality += 0.4
                
                # Check for strikes within 10s
                if meta.get("followed_by_strikes"):
                    td_quality += 0.4
                
                # Mat return
                if meta.get("mat_return"):
                    td_quality = 0.5
                
                td_qualities.append(td_quality)
            
            elif etype == "Submission Attempt":
                # Sub attempt depth: fight-ending (2.2) > tight (1.6) > light (1.0)
                depth_map = {"light": 1.0, "tight": 1.6, "fight-ending": 2.2}
                depth = depth_map.get(meta.get("depth", "light"), 1.0)
                duration = min(meta.get("duration", 0) / 10, 2)
                sub_attempts.append(depth + duration)
            
            elif etype == "Pass":
                passes += 1
            
            elif etype == "Reversal":
                reversals += 1
            
            elif etype == "SCRAMBLE_WIN":
                scramble_wins += 1
            
            elif etype == "STRIKE":
                total_strikes += 1
        
        # Handle unclosed control timer at round end
        if ctrl_start_time is not None:
            duration = round_duration - ctrl_start_time
            ctrl_dom_seconds += duration
        
        # Calculate subscores with exponents
        T = max(round_duration, 1)  # Avoid division by zero
        
        # KD Score
        kd_score = 10 * (sum(kd_severities) ** 0.8) if kd_severities else 0
        
        # ISS Score
        iss_score = 10 * (sum(iss_impacts) ** 0.6) if iss_impacts else 0
        
        # GCQ Score
        gcq_raw = (ctrl_dom_seconds / T) ** 0.8 + 0.08 * passes + 0.04 * sum(ground_iss_impacts)
        gcq_score = 10 * gcq_raw
        
        # TDQ Score
        tdq_score = 10 * (sum(td_qualities) ** 0.7) if td_qualities else 0
        
        # SUBQ Score
        subq_score = 10 * (sum(sub_attempts) ** 0.8) if sub_attempts else 0
        
        # OC Score
        oc_score = 10 * ((ctrl_eff_seconds / T) ** 0.7) if ctrl_eff_seconds > 0 else 0
        
        # AGG Score
        f_eng = ctrl_eff_seconds + sum(iss_impacts) * 2  # Engagement proxy
        attempts_over_base = 0  # Would need weight class baseline
        iss_diff_negative = 1 if opponent_iss_total > sum(iss_impacts) else 0
        agg_raw = max((f_eng / T) + 0.06 * attempts_over_base - 0.04 * iss_diff_negative, 0)
        agg_score = 10 * (agg_raw ** 0.7)
        
        # RP Score
        rp_raw = 2 * reversals + 0.5 * passes + 0.8 * scramble_wins
        rp_score = 10 * (rp_raw ** 0.7) if rp_raw > 0 else 0
        
        # TSR Score
        tsr_raw = max(total_strikes - significant_strikes, 0)
        tsr_score = 10 * (math.log1p(tsr_raw) / math.log(41)) if tsr_raw > 0 else 0
        
        return Subscores(
            KD=round(kd_score, 2),
            ISS=round(iss_score, 2),
            GCQ=round(gcq_score, 2),
            TDQ=round(tdq_score, 2),
            SUBQ=round(subq_score, 2),
            OC=round(oc_score, 2),
            AGG=round(agg_score, 2),
            RP=round(rp_score, 2),
            TSR=round(tsr_score, 2)
        )
    
    @staticmethod
    def calculate_final_score(subscores: Subscores) -> float:
        """
        Calculate final strength score on 1-10000 scale
        Returns a score between 0 and 10000 (realistically 0-9000)
        
        Perfect round (all 10s) = 9000 points
        10000 is reserved for beyond-perfect performance
        
        Weights:
        KD: 30%, ISS: 20%, TSR: 15%, GCQ: 10%, TDQ: 8%,
        OC: 6%, SUBQ: 5%, AGG: 5%, RP: 1%
        """
        weights = {
            "KD": 0.30,    # Knockdowns - 30%
            "ISS": 0.20,   # Significant Strikes - 20%
            "TSR": 0.15,   # Total Strike Ratio - 15%
            "GCQ": 0.10,   # Control Time - 10%
            "TDQ": 0.08,   # Takedowns - 8%
            "OC": 0.06,    # Octagon Control - 6%
            "SUBQ": 0.05,  # Submission Attempts - 5%
            "AGG": 0.05,   # Aggression - 5%
            "RP": 0.01     # Passes/Reversals - 1%
        }
        
        # Calculate weighted score (0-10 scale for each subscore)
        S = (
            weights["KD"] * subscores.KD +
            weights["ISS"] * subscores.ISS +
            weights["TSR"] * subscores.TSR +
            weights["GCQ"] * subscores.GCQ +
            weights["TDQ"] * subscores.TDQ +
            weights["OC"] * subscores.OC +
            weights["SUBQ"] * subscores.SUBQ +
            weights["AGG"] * subscores.AGG +
            weights["RP"] * subscores.RP
        )
        
        # Scale to 1-9000 range (0-10 → 0-9000)
        # S * 900 gives us 0-9000 for perfect rounds
        # 10000 is reserved for exceptional beyond-perfect performance
        strength_score = S * 900
        
        # Clamp to 0-10000 range
        strength_score = max(0.0, min(10000.0, strength_score))
        
        return round(strength_score, 2)
    
    @staticmethod
    def calculate_gate_checks(subscores: Subscores, gcq_time_share: float = 0) -> GateChecks:
        """Calculate boolean gate checks for finish threats and dominance"""
        finish_threat = (subscores.KD >= 1) or (subscores.SUBQ >= 8.0) or (subscores.ISS >= 9.0)
        control_dom = (subscores.GCQ >= 7.5) and (gcq_time_share >= 0.5)
        
        # Count subscores >= 7.5
        high_scores = sum([
            1 for score in [subscores.KD, subscores.ISS, subscores.GCQ, subscores.TDQ, subscores.SUBQ]
            if score >= 7.5
        ])
        multi_cat_dom = high_scores >= 3
        
        return GateChecks(
            finish_threat=finish_threat,
            control_dom=control_dom,
            multi_cat_dom=multi_cat_dom
        )
    
    @staticmethod
    def map_to_ten_point_must(s_a: float, s_b: float, gates_a: GateChecks, gates_b: GateChecks, 
                              subscores_a: Subscores, subscores_b: Subscores,
                              fouls_a: int = 0, fouls_b: int = 0) -> tuple[str, str, RoundReasons]:
        """
        Map continuous scores (1-10000 scale) to 10-Point-Must system
        
        Thresholds:
        - 10-9: score differential 1-4999
        - 10-8: score differential 5000-9000
        - 10-7: score differential 9001-10000
        
        Tie-breakers applied when scores are equal:
        1. Damage (KD > ISS > SUBQ)
        2. Control (GCQ > TDQ)
        3. Aggression/Activity (AGG > TSR)
        4. Technical superiority (OC > RP)
        """
        delta = s_a - s_b
        abs_delta = abs(delta)
        
        # EXTREME TIE-BREAKING SYSTEM - Avoid 10-10 unless absolutely identical
        if abs_delta == 0:
            # Priority 1: DAMAGE (highest priority)
            damage_a = (subscores_a.KD * 3.0) + (subscores_a.ISS * 2.0) + (subscores_a.SUBQ * 1.5)
            damage_b = (subscores_b.KD * 3.0) + (subscores_b.ISS * 2.0) + (subscores_b.SUBQ * 1.5)
            
            if damage_a != damage_b:
                winner = "fighter1" if damage_a > damage_b else "fighter2"
                gates_w = gates_a if damage_a > damage_b else gates_b
                gates_l = gates_b if damage_a > damage_b else gates_a
                delta = 1.0 if damage_a > damage_b else -1.0
                
                card = "10-9" if winner == "fighter1" else "9-10"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False,
                    tie_breaker="damage"
                ))
            
            # Priority 2: CONTROL (grappling/positional)
            control_a = (subscores_a.GCQ * 2.0) + subscores_a.TDQ
            control_b = (subscores_b.GCQ * 2.0) + subscores_b.TDQ
            
            if control_a != control_b:
                winner = "fighter1" if control_a > control_b else "fighter2"
                gates_w = gates_a if control_a > control_b else gates_b
                gates_l = gates_b if control_a > control_b else gates_a
                delta = 1.0 if control_a > control_b else -1.0
                
                card = "10-9" if winner == "fighter1" else "9-10"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False,
                    tie_breaker="control"
                ))
            
            # Priority 3: AGGRESSION & ACTIVITY
            aggression_a = (subscores_a.AGG * 1.5) + subscores_a.TSR + subscores_a.OC
            aggression_b = (subscores_b.AGG * 1.5) + subscores_b.TSR + subscores_b.OC
            
            if aggression_a != aggression_b:
                winner = "fighter1" if aggression_a > aggression_b else "fighter2"
                gates_w = gates_a if aggression_a > aggression_b else gates_b
                gates_l = gates_b if aggression_a > aggression_b else gates_a
                delta = 1.0 if aggression_a > aggression_b else -1.0
                
                card = "10-9" if winner == "fighter1" else "9-10"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False,
                    tie_breaker="aggression"
                ))
            
            # Priority 4: TECHNICAL SUPERIORITY (reversals/passes)
            technical_a = subscores_a.RP
            technical_b = subscores_b.RP
            
            if technical_a != technical_b:
                winner = "fighter1" if technical_a > technical_b else "fighter2"
                gates_w = gates_a if technical_a > technical_b else gates_b
                gates_l = gates_b if technical_a > technical_b else gates_a
                delta = 1.0 if technical_a > technical_b else -1.0
                
                card = "10-9" if winner == "fighter1" else "9-10"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False,
                    tie_breaker="technical"
                ))
            
            # Priority 5: INDIVIDUAL SUBSCORE COMPARISON (most granular)
            # Compare each subscore individually in order of importance
            comparison_order = ['KD', 'ISS', 'SUBQ', 'GCQ', 'TDQ', 'AGG', 'OC', 'TSR', 'RP']
            
            for metric in comparison_order:
                val_a = getattr(subscores_a, metric)
                val_b = getattr(subscores_b, metric)
                
                if val_a != val_b:
                    winner = "fighter1" if val_a > val_b else "fighter2"
                    gates_w = gates_a if val_a > val_b else gates_b
                    gates_l = gates_b if val_a > val_b else gates_a
                    delta = 1.0 if val_a > val_b else -1.0
                    
                    card = "10-9" if winner == "fighter1" else "9-10"
                    return (card, winner, RoundReasons(
                        delta=delta,
                        gates_winner=gates_w,
                        gates_loser=gates_l,
                        to_108=False,
                        to_107=False,
                        draw=False,
                        tie_breaker=metric
                    ))
            
            # ONLY if EVERY single metric is EXACTLY equal - TRUE 10-10 DRAW
            return ("10-10", "DRAW", RoundReasons(
                delta=0,
                gates_winner=gates_a,
                gates_loser=gates_b,
                to_108=False,
                to_107=False,
                draw=True,
                tie_breaker=None
            ))
        
        # Determine winner and loser
        if delta >= 0:
            winner = "fighter1"
            gates_w = gates_a
            gates_l = gates_b
        else:
            winner = "fighter2"
            gates_w = gates_b
            gates_l = gates_a
        
        # Base scores: 10-9 is the default
        score_w = 10
        score_l = 9
        
        # Determine score based on delta thresholds (1-10000 scale)
        to_108 = False
        to_107 = False
        
        if abs_delta < 5000:
            # 10-9: Score differential 1-4999
            score_l = 9
        elif abs_delta <= 9000:
            # 10-8: Score differential 5000-9000
            score_l = 8
            to_108 = True
        else:  # abs_delta > 9000
            # 10-7: Score differential 9001-10000
            score_l = 7
            to_107 = True
        
        # Apply foul deductions
        if winner == "fighter1":
            score_w -= fouls_a
            score_l -= fouls_b
        else:
            score_w -= fouls_b
            score_l -= fouls_a
        
        # Never go below 7
        score_w = max(score_w, 7)
        score_l = max(score_l, 7)
        
        # Format card
        if winner == "fighter1":
            card = f"{score_w}-{score_l}"
        else:
            card = f"{score_l}-{score_w}"
        
        reasons = RoundReasons(
            delta=delta,
            gates_winner=gates_w,
            gates_loser=gates_l,
            to_108=to_108,
            to_107=to_107,
            draw=False
        )
        
        return (card, winner, reasons)

# Helper function to prepare data for MongoDB
def prepare_for_mongo(data):
    if isinstance(data.get('createdAt'), datetime):
        data['createdAt'] = data['createdAt'].isoformat()
    if isinstance(data.get('timestamp'), datetime):
        data['timestamp'] = data['timestamp'].isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item.get('createdAt'), str):
        item['createdAt'] = datetime.fromisoformat(item['createdAt'])
    if isinstance(item.get('timestamp'), str):
        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
    return item

# New Scoring Engine Function
def calculate_new_score(events: List[EventData], fighter: str) -> tuple[float, dict, dict]:
    """
    Calculate score using normalized base values with volume dampening and unified rules
    Returns: (total_score, category_scores, event_counts)
    """
    fighter_events = [e for e in events if e.fighter == fighter]
    
    # Raw score accumulators (before normalization)
    striking_raw = 0.0
    grappling_raw = 0.0
    other_raw = 0.0
    
    # Event counts and tracking
    event_counts = {}
    has_near_finish_striking = False
    has_near_finish_grappling = False
    
    # Strike counting for volume dampening
    non_sig_strike_count = 0
    
    for event in fighter_events:
        event_type = event.event_type
        meta = event.metadata or {}
        
        # Get base value config
        base_config = SCORING_CONFIG["base_values"].get(event_type)
        if not base_config:
            continue
        
        # Track event count
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        category = base_config["category"]
        base_value = 0.0
        
        # Calculate base value based on event type
        if event_type == "KD":
            tier = meta.get("tier", "Flash")
            base_value = base_config.get(tier, base_config["Flash"])
            if tier == "Near-Finish":
                has_near_finish_striking = True
                
        elif event_type == "Submission Attempt":
            tier = meta.get("tier", meta.get("depth", "Light"))
            base_value = base_config.get(tier, base_config["Light"])
            if tier == "Near-Finish":
                has_near_finish_grappling = True
                
        elif event_type in ["Ground Back Control", "Ground Top Control", "Cage Control Time"]:
            duration = meta.get("duration", 0)
            base_value = base_config["value_per_sec"] * duration
            
        elif event_type in ["Cross", "Hook", "Uppercut", "Elbow", "Jab", "Knee"]:
            is_significant = meta.get("significant", True)
            if is_significant:
                base_value = base_config["sig"]
            else:
                base_value = base_config["non_sig"]
                non_sig_strike_count += 1
                
        else:
            # Simple value events (Rocked, TD Landed, TD Stuffed, Sweep/Reversal)
            base_value = base_config["value"]
        
        # Add to category raw score
        if category == "striking":
            striking_raw += base_value
        elif category == "grappling":
            grappling_raw += base_value
        elif category == "other":
            other_raw += base_value
    
    # Normalize within each category (to 0-100 scale) then apply category weight
    # Note: Normalization factor can be adjusted based on typical round values
    # Using simple linear scaling for now
    
    striking_normalized = striking_raw * 100  # Scale raw scores to 0-100
    grappling_normalized = grappling_raw * 100
    other_normalized = other_raw * 100
    
    # Apply category weights (Striking 50%, Grappling 40%, Other 10%)
    weighted_striking = striking_normalized * 0.50
    weighted_grappling = grappling_normalized * 0.40
    weighted_other = other_normalized * 0.10
    
    total_score = weighted_striking + weighted_grappling + weighted_other
    
    category_scores = {
        "striking": weighted_striking,
        "grappling": weighted_grappling,
        "other": weighted_other,
        "striking_raw": striking_raw,
        "grappling_raw": grappling_raw,
        "other_raw": other_raw,
        "has_near_finish_striking": has_near_finish_striking,
        "has_near_finish_grappling": has_near_finish_grappling
    }
    
    return total_score, category_scores, event_counts

# Routes
@api_router.get("/")
async def root():
    return {"message": "Combat Sports Judging API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks

@api_router.post("/calculate-score-v2")
async def calculate_score_v2(request: ScoreRequest):
    """
    NEW SCORING ENGINE - Uses weighted category system
    Calculate round scores based on new scoring model with:
    - Striking (50%), Grappling (40%), Control/Aggression (10%)
    - Event-specific weights
    - Tier multipliers for KD and Sub Attempts
    - Stacking rules
    """
    try:
        # Calculate scores using new model
        f1_total, f1_categories, f1_counts = calculate_new_score(request.events, "fighter1")
        f2_total, f2_categories, f2_counts = calculate_new_score(request.events, "fighter2")
        
        # Handle Point Deductions
        f1_deductions = 0
        f2_deductions = 0
        
        for event in request.events:
            if event.event_type == "Point Deduction":
                fighter_deducted = event.metadata.get("fighter", event.fighter)
                points = event.metadata.get("points", 1)
                
                if fighter_deducted == "fighter1":
                    f1_deductions += points
                elif fighter_deducted == "fighter2":
                    f2_deductions += points
                
                print(f"[DEDUCTION] {fighter_deducted} deducted {points} point(s)")
        
        # Log the score differential for debugging
        print(f"[SCORING] Round {request.round_num} - Fighter1: {f1_total:.2f} (-{f1_deductions}), Fighter2: {f2_total:.2f} (-{f2_deductions})")
        print(f"  F1 Categories - Striking: {f1_categories['striking_raw']:.2f}, Grappling: {f1_categories['grappling_raw']:.2f}, Other: {f1_categories['other_raw']:.2f}")
        print(f"  F2 Categories - Striking: {f2_categories['striking_raw']:.2f}, Grappling: {f2_categories['grappling_raw']:.2f}, Other: {f2_categories['other_raw']:.2f}")
        
        # UNIFIED RULES GUARDRAILS
        
        # Guardrail 1: Near-finish domination
        f1_has_near_finish = f1_categories.get("has_near_finish_striking") or f1_categories.get("has_near_finish_grappling")
        f2_has_near_finish = f2_categories.get("has_near_finish_striking") or f2_categories.get("has_near_finish_grappling")
        
        if f1_has_near_finish and not f2_has_near_finish:
            # Fighter 1 wins with near-finish advantage
            score_diff = max(f1_total - f2_total, 10.0)  # Ensure at least 10-9 win
            print(f"  [GUARDRAIL] F1 has near-finish, F2 does not - F1 wins")
        elif f2_has_near_finish and not f1_has_near_finish:
            # Fighter 2 wins with near-finish advantage
            score_diff = min(f1_total - f2_total, -10.0)  # Ensure at least 10-9 win
            print(f"  [GUARDRAIL] F2 has near-finish, F1 does not - F2 wins")
        else:
            # Guardrail 2: Striking dominance override
            striking_margin = f1_categories['striking'] - f2_categories['striking']
            if abs(striking_margin) >= 20.0:
                # Striking margin ≥ 20 points overrides unless opponent has near-finish grappling
                if striking_margin > 0 and not f2_categories.get("has_near_finish_grappling"):
                    score_diff = max(f1_total - f2_total, 10.0)
                    print(f"  [GUARDRAIL] F1 striking dominance (margin: {striking_margin:.1f}) overrides")
                elif striking_margin < 0 and not f1_categories.get("has_near_finish_grappling"):
                    score_diff = min(f1_total - f2_total, -10.0)
                    print(f"  [GUARDRAIL] F2 striking dominance (margin: {abs(striking_margin):.1f}) overrides")
                else:
                    score_diff = f1_total - f2_total
            else:
                score_diff = f1_total - f2_total
        
        print(f"  Final Diff: {score_diff:.2f}")
        
        # ADDITIONAL GUARDRAILS FOR 10-8 AND 10-7 ROUNDS
        # Count total knockdowns for each fighter
        f1_kd_count = f1_counts.get("KD", 0)
        f2_kd_count = f2_counts.get("KD", 0)
        kd_differential = abs(f1_kd_count - f2_kd_count)
        
        # Calculate total strikes differential (all strike types)
        f1_total_strikes = sum([
            f1_counts.get("Jab", 0),
            f1_counts.get("Cross", 0),
            f1_counts.get("Hook", 0),
            f1_counts.get("Uppercut", 0),
            f1_counts.get("Elbow", 0),
            f1_counts.get("Knee", 0),
            f1_counts.get("Head Kick", 0),
            f1_counts.get("Body Kick", 0),
            f1_counts.get("Low Kick", 0),
            f1_counts.get("Front Kick/Teep", 0)
        ])
        f2_total_strikes = sum([
            f2_counts.get("Jab", 0),
            f2_counts.get("Cross", 0),
            f2_counts.get("Hook", 0),
            f2_counts.get("Uppercut", 0),
            f2_counts.get("Elbow", 0),
            f2_counts.get("Knee", 0),
            f2_counts.get("Head Kick", 0),
            f2_counts.get("Body Kick", 0),
            f2_counts.get("Low Kick", 0),
            f2_counts.get("Front Kick/Teep", 0)
        ])
        strike_differential = abs(f1_total_strikes - f2_total_strikes)
        
        print(f"  [GUARDRAILS] KD Diff: {kd_differential}, Strike Diff: {strike_differential}")
        
        # Determine if 10-8 or 10-7 is allowed based on guardrails
        # For 10-8/10-7: Need EITHER 2+ KD advantage OR 100+ strike differential
        allow_extreme_score = (kd_differential >= 2) or (strike_differential >= 100)
        
        # 10-Point Must System mapping - EXTREMELY STRICT UFC THRESHOLDS
        # 10-8 rounds extremely rare - requires complete one-sided dominance
        # 10-7 should basically never happen
        if abs(score_diff) <= 3.0:  # Extremely rare draw - virtually identical
            card = "10-10"
            winner = "DRAW"
        elif abs(score_diff) < 140.0:  # Clear winner (99.5% of rounds)
            winner = "fighter1" if score_diff > 0 else "fighter2"
            card = "10-9" if score_diff > 0 else "9-10"
        elif abs(score_diff) < 200.0:  # Potential 10-8 territory
            winner = "fighter1" if score_diff > 0 else "fighter2"
            # Only award 10-8 if guardrails are met
            if allow_extreme_score:
                card = "10-8" if score_diff > 0 else "8-10"
                print(f"  [10-8 AWARDED] Guardrails met: {kd_differential} KD diff, {strike_differential} strike diff")
            else:
                card = "10-9" if score_diff > 0 else "9-10"
                print(f"  [10-8 DENIED] Guardrails not met: Only {kd_differential} KD diff, {strike_differential} strike diff (need 2+ KD or 100+ strikes)")
        else:  # Potential 10-7 territory (should almost never happen)
            winner = "fighter1" if score_diff > 0 else "fighter2"
            # Only award 10-7 if guardrails are met AND difference is massive
            if allow_extreme_score and abs(score_diff) >= 250.0:
                card = "10-7" if score_diff > 0 else "7-10"
                print(f"  [10-7 AWARDED] Extreme guardrails met: {kd_differential} KD diff, {strike_differential} strike diff")
            elif allow_extreme_score:
                card = "10-8" if score_diff > 0 else "8-10"
                print(f"  [10-8 AWARDED] Guardrails met but not extreme enough for 10-7")
            else:
                card = "10-9" if score_diff > 0 else "9-10"
                print(f"  [10-7/10-8 DENIED] Guardrails not met: Only {kd_differential} KD diff, {strike_differential} strike diff")
        
        # Apply Point Deductions to the card
        if f1_deductions > 0 or f2_deductions > 0:
            # Parse the current card
            scores = card.split("-")
            f1_card_score = int(scores[0])
            f2_card_score = int(scores[1])
            
            # Apply deductions
            f1_card_score -= f1_deductions
            f2_card_score -= f2_deductions
            
            # Update card
            card = f"{f1_card_score}-{f2_card_score}"
            
            # Determine winner after deductions
            if f1_card_score > f2_card_score:
                winner = "fighter1"
            elif f2_card_score > f1_card_score:
                winner = "fighter2"
            else:
                winner = "DRAW"
            
            print(f"  [DEDUCTIONS APPLIED] Final card after deductions: {card} (Winner: {winner})")
        
        # Create legacy-compatible subscores for compatibility
        def create_legacy_subscores(categories):
            return Subscores(
                KD=categories["striking_raw"] * 0.3,  # Approximate mapping
                ISS=categories["striking_raw"] * 0.5,
                GCQ=categories["grappling_raw"] * 0.5,
                TDQ=categories["grappling_raw"] * 0.3,
                SUBQ=categories["grappling_raw"] * 0.2,
                OC=categories["other_raw"],
                AGG=categories["other_raw"] * 0.5,
                RP=0.0,
                TSR=categories["striking_raw"] * 0.2
            )
        
        result = RoundScore(
            bout_id=request.bout_id,
            round_num=request.round_num,
            fighter1_score=FighterScore(
                fighter="fighter1",
                subscores=create_legacy_subscores(f1_categories),
                final_score=f1_total,
                event_counts=f1_counts
            ),
            fighter2_score=FighterScore(
                fighter="fighter2",
                subscores=create_legacy_subscores(f2_categories),
                final_score=f2_total,
                event_counts=f2_counts
            ),
            score_gap=abs(score_diff),
            card=card,
            winner=winner,
            reasons=RoundReasons(
                delta=score_diff,
                gates_winner=GateChecks(finish_threat=False, control_dom=False, multi_cat_dom=False),
                gates_loser=GateChecks(finish_threat=False, control_dom=False, multi_cat_dom=False),
                to_108=(card == "10-8"),
                to_107=(card == "10-7"),
                draw=(card == "10-10"),
                tie_breaker=None
            ),
            uncertainty="medium_confidence",
            uncertainty_factors=[]
        )
        
        return result
        
    except Exception as e:
        logging.error(f"Error in calculate_score_v2: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scoring calculation failed: {str(e)}")

@api_router.post("/calculate-score", response_model=RoundScore)
async def calculate_score(request: ScoreRequest):
    """
    Calculate round scores for both fighters based on logged events
    Uses 10-Point-Must system with gate checks
    """
    try:
        engine = ScoringEngine()
        
        # Get all events for the round
        fighter1_events = [e for e in request.events if e.fighter == "fighter1"]
        fighter2_events = [e for e in request.events if e.fighter == "fighter2"]
        
        # Count events by category for both fighters
        def count_events_by_category(events):
            """Count events grouped by scoring categories"""
            counts = {
                "Significant Strikes": 0,
                "Grappling Control": 0,
                "Aggression": 0,
                "Damage": 0,
                "Takedowns": 0
            }
            
            for e in events:
                event_type = e.event_type
                # Significant Strikes: HS (Head Strikes), BS (Body Strikes), LS (Leg Strikes), KD, Rocked
                if event_type in ["HS", "BS", "LS", "KD", "Rocked"]:
                    counts["Significant Strikes"] += 1
                # Grappling Control: CTRL, Pass, Reversal
                if event_type in ["CTRL_START", "CTRL_STOP", "Pass", "Reversal"]:
                    counts["Grappling Control"] += 1
                # Aggression: Strike counts
                if event_type in ["HS", "BS", "LS"]:
                    counts["Aggression"] += 1
                # Damage: KD, Rocked, Submission Attempt
                if event_type in ["KD", "Rocked", "Submission Attempt"]:
                    counts["Damage"] += 1
                # Takedowns
                if event_type == "Takedown":
                    counts["Takedowns"] += 1
            
            return counts
        
        f1_event_counts = count_events_by_category(fighter1_events)
        f2_event_counts = count_events_by_category(fighter2_events)
        
        # Calculate strike totals for AGG calculation (HS, BS, LS)
        f1_ss_total = sum([1.0 for e in fighter1_events if e.event_type in ["HS", "BS", "LS"]])
        f2_ss_total = sum([1.0 for e in fighter2_events if e.event_type in ["HS", "BS", "LS"]])
        
        # Calculate subscores for both fighters
        f1_subscores = engine.calculate_subscores(request.events, "fighter1", request.round_duration, f2_ss_total)
        f2_subscores = engine.calculate_subscores(request.events, "fighter2", request.round_duration, f1_ss_total)
        
        # Calculate final strength scores
        s_a = engine.calculate_final_score(f1_subscores)
        s_b = engine.calculate_final_score(f2_subscores)
        
        # Calculate GCQ time share (simplified - can be enhanced)
        f1_ctrl_time = sum([e.metadata.get('duration', 0) for e in fighter1_events if e.event_type == 'CTRL_STOP'])
        f2_ctrl_time = sum([e.metadata.get('duration', 0) for e in fighter2_events if e.event_type == 'CTRL_STOP'])
        total_ctrl = f1_ctrl_time + f2_ctrl_time
        f1_gcq_share = f1_ctrl_time / total_ctrl if total_ctrl > 0 else 0
        f2_gcq_share = f2_ctrl_time / total_ctrl if total_ctrl > 0 else 0
        
        # Calculate gate checks
        gates_a = engine.calculate_gate_checks(f1_subscores, f1_gcq_share)
        gates_b = engine.calculate_gate_checks(f2_subscores, f2_gcq_share)
        
        # Map to 10-Point-Must with tie-breaking system
        card, winner, reasons = engine.map_to_ten_point_must(s_a, s_b, gates_a, gates_b, f1_subscores, f2_subscores)
        
        # Calculate gap
        gap = abs(s_a - s_b)
        
        result = RoundScore(
            bout_id=request.bout_id,
            round_num=request.round_num,
            fighter1_score=FighterScore(
                fighter="fighter1",
                subscores=f1_subscores,
                final_score=s_a,
                event_counts=f1_event_counts
            ),
            fighter2_score=FighterScore(
                fighter="fighter2",
                subscores=f2_subscores,
                final_score=s_b,
                event_counts=f2_event_counts
            ),
            score_gap=gap,
            card=card,
            winner=winner,
            reasons=reasons
        )
        
        # Calculate uncertainty bands
        uncertainty_level, uncertainty_factors = calculate_uncertainty(
            gap, 
            reasons.tie_breaker, 
            len(request.events)
        )
        result.uncertainty = uncertainty_level
        result.uncertainty_factors = uncertainty_factors
        
        # Create audit log for score calculation
        await create_audit_log(
            action_type="score_calculation",
            user_id="system",
            user_name="Scoring System",
            resource_type="round_score",
            resource_id=f"{request.bout_id}_round_{request.round_num}",
            action_data={
                "bout_id": request.bout_id,
                "round_num": request.round_num,
                "card": card,
                "winner": winner,
                "score_gap": gap,
                "uncertainty": uncertainty_level
            }
        )
        
        # Automatically detect and flag discrepancies
        await detect_and_flag_discrepancies(request.bout_id, request.round_num, result, request.events)
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Shadow Judging Endpoints
@api_router.post("/training-library/seed")
async def seed_training_library():
    """Seed the training library with sample historical rounds"""
    try:
        # Clear existing training rounds
        await db.training_library.delete_many({})
        
        # Sample historical rounds
        sample_rounds = [
            {
                "event": "UFC 299: O'Malley vs. Vera 2",
                "fighters": "Dustin Poirier vs. Benoit Saint Denis",
                "roundNumber": 2,
                "summary": [
                    "Poirier lands multiple hard combinations to the head",
                    "Saint Denis attempts guillotine but Poirier escapes",
                    "Poirier drops Saint Denis with a straight right",
                    "Dominant striking throughout the round"
                ],
                "officialCard": "10-9"
            },
            {
                "event": "UFC 300: Pereira vs. Hill",
                "fighters": "Max Holloway vs. Justin Gaethje",
                "roundNumber": 5,
                "summary": [
                    "Both fighters exchange in the pocket",
                    "Holloway lands the final 10 seconds standing knockout",
                    "Legendary finish at the buzzer",
                    "Extreme violence with knockdown"
                ],
                "officialCard": "10-8"
            },
            {
                "event": "UFC 296: Edwards vs. Covington",
                "fighters": "Alexandre Pantoja vs. Brandon Royval",
                "roundNumber": 1,
                "summary": [
                    "Pantoja secures takedown early",
                    "Controls back for 3+ minutes",
                    "Multiple submission attempts including RNC",
                    "Royval survives but takes heavy damage"
                ],
                "officialCard": "10-8"
            },
            {
                "event": "UFC 298: Volkanovski vs. Topuria",
                "fighters": "Ian Garry vs. Geoff Neal",
                "roundNumber": 3,
                "summary": [
                    "Even striking exchanges",
                    "Both fighters land equal significant strikes",
                    "No clear control or damage advantage",
                    "Competitive round throughout"
                ],
                "officialCard": "10-10"
            },
            {
                "event": "UFC 297: Strickland vs. Du Plessis",
                "fighters": "Sean Strickland vs. Dricus Du Plessis",
                "roundNumber": 2,
                "summary": [
                    "Du Plessis lands heavy shots early",
                    "Strickland hurt badly in the first minute",
                    "Du Plessis controls cage center",
                    "Strickland recovers but loses round clearly"
                ],
                "officialCard": "10-9"
            },
            {
                "event": "UFC 295: Prochazka vs. Pereira",
                "fighters": "Jiri Prochazka vs. Alex Pereira",
                "roundNumber": 1,
                "summary": [
                    "Early knockdown by Pereira",
                    "Brutal ground and pound",
                    "Prochazka survives but takes heavy damage",
                    "Clear dominance by Pereira"
                ],
                "officialCard": "10-8"
            },
            {
                "event": "UFC 294: Makhachev vs. Volkanovski 2",
                "fighters": "Islam Makhachev vs. Alexander Volkanovski",
                "roundNumber": 1,
                "summary": [
                    "Makhachev lands devastating head kick knockout",
                    "Volkanovski unconscious",
                    "Fight stopped in first round",
                    "Near-finish level dominance"
                ],
                "officialCard": "10-7"
            },
            {
                "event": "UFC 293: Adesanya vs. Strickland",
                "fighters": "Israel Adesanya vs. Sean Strickland",
                "roundNumber": 3,
                "summary": [
                    "Strickland pressures forward constantly",
                    "Adesanya circling and countering",
                    "Close striking numbers",
                    "Could go either way"
                ],
                "officialCard": "10-9"
            },
            {
                "event": "UFC 292: Sterling vs. O'Malley",
                "fighters": "Aljamain Sterling vs. Sean O'Malley",
                "roundNumber": 1,
                "summary": [
                    "O'Malley lands multiple hard right hands",
                    "Sterling shoots for takedown unsuccessfully",
                    "O'Malley controls distance and pace",
                    "Clear striking advantage"
                ],
                "officialCard": "10-9"
            },
            {
                "event": "UFC 291: Poirier vs. Gaethje 2",
                "fighters": "Dustin Poirier vs. Justin Gaethje",
                "roundNumber": 2,
                "summary": [
                    "Poirier drops Gaethje twice",
                    "Heavy leg kicks throughout",
                    "Gaethje survives but wobbled",
                    "Dominant performance"
                ],
                "officialCard": "10-8"
            },
            {
                "event": "UFC 290: Volkanovski vs. Rodriguez",
                "fighters": "Brandon Moreno vs. Alexandre Pantoja",
                "roundNumber": 4,
                "summary": [
                    "Pantoja secures rear naked choke",
                    "Moreno defends for entire round",
                    "Pantoja maintains back control 4+ minutes",
                    "Extreme control dominance"
                ],
                "officialCard": "10-8"
            },
            {
                "event": "UFC 289: Nunes vs. Aldana",
                "fighters": "Charles Oliveira vs. Beneil Dariush",
                "roundNumber": 1,
                "summary": [
                    "Oliveira drops Dariush early",
                    "Ground and pound finishes fight",
                    "Dariush unconscious from strikes",
                    "Complete dominance"
                ],
                "officialCard": "10-7"
            },
            {
                "event": "UFC 288: Sterling vs. Cejudo",
                "fighters": "Aljamain Sterling vs. Henry Cejudo",
                "roundNumber": 2,
                "summary": [
                    "Sterling controls pace with jab",
                    "Cejudo struggles to close distance",
                    "Even round with slight Sterling edge",
                    "Close but clear winner"
                ],
                "officialCard": "10-9"
            },
            {
                "event": "UFC 287: Pereira vs. Adesanya 2",
                "fighters": "Alex Pereira vs. Israel Adesanya",
                "roundNumber": 2,
                "summary": [
                    "Adesanya lands huge right hand",
                    "Pereira dropped and hurt badly",
                    "Ground and pound to finish",
                    "Referee stops fight"
                ],
                "officialCard": "10-7"
            },
            {
                "event": "UFC 286: Edwards vs. Usman 3",
                "fighters": "Leon Edwards vs. Kamaru Usman",
                "roundNumber": 1,
                "summary": [
                    "Usman pressures with wrestling",
                    "Edwards defends takedowns well",
                    "Even striking exchanges",
                    "Competitive round"
                ],
                "officialCard": "10-10"
            },
            {
                "event": "UFC 285: Jones vs. Gane",
                "fighters": "Jon Jones vs. Ciryl Gane",
                "roundNumber": 1,
                "summary": [
                    "Jones secures guillotine submission",
                    "Gane taps quickly",
                    "Dominant grappling",
                    "Fight-ending submission"
                ],
                "officialCard": "10-8"
            }
        ]
        
        # Insert all sample rounds
        training_rounds = []
        for round_data in sample_rounds:
            round_obj = TrainingRound(**round_data)
            doc = round_obj.model_dump()
            doc = prepare_for_mongo(doc)
            training_rounds.append(doc)
        
        if training_rounds:
            await db.training_library.insert_many(training_rounds)
        
        return {
            "success": True,
            "message": f"Seeded {len(training_rounds)} training rounds",
            "count": len(training_rounds)
        }
    except Exception as e:
        logger.error(f"Error seeding training library: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/training-library/rounds", response_model=List[TrainingRound])
async def get_training_rounds():
    """Get all available training rounds"""
    try:
        rounds = await db.training_library.find({}, {"_id": 0}).to_list(1000)
        rounds = [parse_from_mongo(r) for r in rounds]
        return rounds
    except Exception as e:
        logger.error(f"Error fetching training rounds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/training-library/rounds", response_model=TrainingRound)
async def create_training_round(round_data: TrainingRoundCreate):
    """Create a new training round"""
    try:
        round_obj = TrainingRound(**round_data.model_dump())
        doc = round_obj.model_dump()
        doc = prepare_for_mongo(doc)
        await db.training_library.insert_one(doc)
        return round_obj
    except Exception as e:
        logger.error(f"Error creating training round: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/training-library/submit-score", response_model=JudgePerformance)
async def submit_judge_score(performance: JudgePerformanceCreate):
    """Submit a judge's score and track performance"""
    try:
        perf_obj = JudgePerformance(**performance.model_dump())
        doc = perf_obj.model_dump()
        doc = prepare_for_mongo(doc)
        await db.judge_performance.insert_one(doc)
        return perf_obj
    except Exception as e:
        logger.error(f"Error submitting judge score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/training-library/judge-stats/{judgeId}", response_model=JudgeStats)
async def get_judge_stats(judgeId: str):
    """Get calibration statistics for a specific judge"""
    try:
        performances = await db.judge_performance.find(
            {"judgeId": judgeId},
            {"_id": 0}
        ).to_list(1000)
        
        if not performances:
            raise HTTPException(status_code=404, detail="No performance data found for this judge")
        
        # Calculate statistics
        total_attempts = len(performances)
        avg_accuracy = sum(p['accuracy'] for p in performances) / total_attempts
        avg_mae = sum(p['mae'] for p in performances) / total_attempts
        sensitivity108_count = sum(1 for p in performances if p['sensitivity108'])
        sensitivity108_rate = sensitivity108_count / total_attempts
        perfect_matches = sum(1 for p in performances if p['match'])
        
        judge_name = performances[0]['judgeName'] if performances else "Unknown"
        
        return JudgeStats(
            judgeId=judgeId,
            judgeName=judge_name,
            totalAttempts=total_attempts,
            averageAccuracy=round(avg_accuracy, 2),
            averageMAE=round(avg_mae, 2),
            sensitivity108Rate=round(sensitivity108_rate * 100, 2),
            perfectMatches=perfect_matches
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching judge stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/training-library/leaderboard")
async def get_leaderboard():
    """Get top judges by accuracy"""
    try:
        # Aggregate judge performances
        pipeline = [
            {
                "$group": {
                    "_id": "$judgeId",
                    "judgeName": {"$first": "$judgeName"},
                    "totalAttempts": {"$sum": 1},
                    "avgAccuracy": {"$avg": "$accuracy"},
                    "avgMAE": {"$avg": "$mae"},
                    "perfectMatches": {
                        "$sum": {"$cond": [{"$eq": ["$match", True]}, 1, 0]}
                    }
                }
            },
            {"$sort": {"avgAccuracy": -1}},
            {"$limit": 10}
        ]
        
        leaderboard = await db.judge_performance.aggregate(pipeline).to_list(10)
        
        # Format results
        formatted_leaderboard = [
            {
                "judgeId": entry["_id"],
                "judgeName": entry["judgeName"],
                "totalAttempts": entry["totalAttempts"],
                "averageAccuracy": round(entry["avgAccuracy"], 2),
                "averageMAE": round(entry["avgMAE"], 2),
                "perfectMatches": entry["perfectMatches"]
            }
            for entry in leaderboard
        ]
        
        return {"leaderboard": formatted_leaderboard}
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Fighter Memory Log Endpoints
@api_router.post("/fighters/update-stats")
async def update_fighter_stats(update: FighterStatsUpdate):
    """Update fighter statistics after a round"""
    try:
        fighter_name = update.fighter_name
        
        # Get existing stats or create new
        existing = await db.fighter_stats.find_one({"fighter_name": fighter_name})
        
        if existing:
            stats = FighterStats(**existing)
        else:
            stats = FighterStats(fighter_name=fighter_name)
        
        # Count events
        kd_count = len([e for e in update.round_events if e.get('event_type') == 'KD'])
        ss_count = len([e for e in update.round_events if e.get('event_type') in ['HS', 'BS', 'LS']])
        td_count = len([e for e in update.round_events if e.get('event_type') == 'Takedown'])
        sub_count = len([e for e in update.round_events if e.get('event_type') == 'Submission Attempt'])
        pass_count = len([e for e in update.round_events if e.get('event_type') == 'Pass'])
        rev_count = len([e for e in update.round_events if e.get('event_type') == 'Reversal'])
        
        # Calculate striking style
        ss_head = len([e for e in update.round_events if e.get('event_type') == 'HS'])
        ss_body = len([e for e in update.round_events if e.get('event_type') == 'BS'])
        ss_leg = len([e for e in update.round_events if e.get('event_type') == 'LS'])
        ss_total = ss_head + ss_body + ss_leg
        
        # Update cumulative stats
        total_rounds = stats.total_rounds + 1
        
        # Running averages
        stats.avg_kd_per_round = ((stats.avg_kd_per_round * stats.total_rounds) + kd_count) / total_rounds
        stats.avg_ss_per_round = ((stats.avg_ss_per_round * stats.total_rounds) + ss_count) / total_rounds
        stats.avg_td_per_round = ((stats.avg_td_per_round * stats.total_rounds) + td_count) / total_rounds
        stats.avg_sub_attempts = ((stats.avg_sub_attempts * stats.total_rounds) + sub_count) / total_rounds
        stats.avg_passes = ((stats.avg_passes * stats.total_rounds) + pass_count) / total_rounds
        stats.avg_reversals = ((stats.avg_reversals * stats.total_rounds) + rev_count) / total_rounds
        stats.avg_control_time = ((stats.avg_control_time * stats.total_rounds) + update.control_time) / total_rounds
        stats.avg_round_score = ((stats.avg_round_score * stats.total_rounds) + update.round_score) / total_rounds
        
        # Update round results
        if update.round_result == "won":
            stats.rounds_won += 1
        elif update.round_result == "lost":
            stats.rounds_lost += 1
        else:
            stats.rounds_drawn += 1
        
        # Update 10-8/10-7 rates
        if "10-8" in update.round_card or "8-10" in update.round_card:
            stats.rate_10_8 = ((stats.rate_10_8 * stats.total_rounds) + 1) / total_rounds
        if "10-7" in update.round_card or "7-10" in update.round_card:
            stats.rate_10_7 = ((stats.rate_10_7 * stats.total_rounds) + 1) / total_rounds
        
        stats.total_rounds = total_rounds
        
        # Calculate tendencies
        grappling_events = td_count + sub_count + pass_count + rev_count
        striking_events = ss_count + kd_count
        total_events = grappling_events + striking_events
        
        grappling_rate = grappling_events / total_events if total_events > 0 else 0
        
        striking_style = {
            "head": ss_head / ss_total if ss_total > 0 else 0.33,
            "body": ss_body / ss_total if ss_total > 0 else 0.33,
            "leg": ss_leg / ss_total if ss_total > 0 else 0.34
        }
        
        finish_threat = 1.0 if (kd_count > 0 or sub_count > 1) else 0.0
        control_pref = update.control_time / 300.0 if update.control_time > 0 else 0.0  # 300s = 5min round
        
        stats.tendencies = FighterTendencies(
            striking_style=striking_style,
            grappling_rate=round(grappling_rate, 2),
            finish_threat_rate=round(finish_threat, 2),
            control_preference=round(control_pref, 2),
            aggression_level=round(min(10.0, (striking_events + grappling_events) / 2.0), 2)
        )
        
        stats.last_updated = datetime.now(timezone.utc)
        
        # Save to database
        doc = stats.model_dump()
        doc = prepare_for_mongo(doc)
        
        await db.fighter_stats.update_one(
            {"fighter_name": fighter_name},
            {"$set": doc},
            upsert=True
        )
        
        return {"success": True, "message": f"Updated stats for {fighter_name}"}
    except Exception as e:
        logger.error(f"Error updating fighter stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/fighters/{fighter_name}/stats")
async def get_fighter_stats(fighter_name: str):
    """Get historical statistics for a fighter"""
    try:
        stats = await db.fighter_stats.find_one({"fighter_name": fighter_name}, {"_id": 0})
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"No stats found for {fighter_name}")
        
        stats = parse_from_mongo(stats)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fighter stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/fighters/compare")
async def compare_fighters(fighter1: str, fighter2: str):
    """Compare statistics between two fighters"""
    try:
        stats1 = await db.fighter_stats.find_one({"fighter_name": fighter1})
        stats2 = await db.fighter_stats.find_one({"fighter_name": fighter2})
        
        if not stats1:
            raise HTTPException(status_code=404, detail=f"No stats found for {fighter1}")
        if not stats2:
            raise HTTPException(status_code=404, detail=f"No stats found for {fighter2}")
        
        stats1 = parse_from_mongo(stats1)
        stats2 = parse_from_mongo(stats2)
        
        # Calculate comparative advantages
        comparison = {
            "fighter1": stats1,
            "fighter2": stats2,
            "advantages": {
                "fighter1": [],
                "fighter2": []
            }
        }
        
        # Compare key metrics
        if stats1['avg_kd_per_round'] > stats2['avg_kd_per_round']:
            comparison["advantages"]["fighter1"].append("More knockdowns per round")
        elif stats2['avg_kd_per_round'] > stats1['avg_kd_per_round']:
            comparison["advantages"]["fighter2"].append("More knockdowns per round")
        
        if stats1['avg_td_per_round'] > stats2['avg_td_per_round']:
            comparison["advantages"]["fighter1"].append("More takedowns per round")
        elif stats2['avg_td_per_round'] > stats1['avg_td_per_round']:
            comparison["advantages"]["fighter2"].append("More takedowns per round")
        
        if stats1['tendencies']['grappling_rate'] > stats2['tendencies']['grappling_rate']:
            comparison["advantages"]["fighter1"].append("More grappling-focused")
        elif stats2['tendencies']['grappling_rate'] > stats1['tendencies']['grappling_rate']:
            comparison["advantages"]["fighter2"].append("More grappling-focused")
        
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing fighters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Discrepancy Detection Helper
# Discrepancy Detection Helper
def calculate_uncertainty(score_gap: float, tie_breaker: str, event_count: int, thresholds: dict = None) -> tuple[str, List[str]]:
    """Calculate uncertainty level for a scoring decision"""
    if thresholds is None:
        thresholds = {"10_9": 600, "10_8": 900}
    
    factors = []
    
    # Base confidence from threshold proximity
    distance_to_10_9 = abs(score_gap - thresholds["10_9"])
    distance_to_10_8 = abs(score_gap - thresholds["10_8"])
    min_distance = min(distance_to_10_9, distance_to_10_8)
    
    # Determine base confidence
    if min_distance > 150:
        confidence = "high_confidence"
    elif min_distance > 50:
        confidence = "medium_confidence"
    else:
        confidence = "low_confidence"
        factors.append(f"Score within {min_distance:.0f} points of threshold")
    
    # Tie-breaker reduces confidence
    if tie_breaker:
        if confidence == "high_confidence":
            confidence = "medium_confidence"
        else:
            confidence = "low_confidence"
        factors.append(f"Decided by tie-breaker: {tie_breaker}")
    
    # Low activity reduces confidence
    if event_count < 5:
        if confidence == "high_confidence":
            confidence = "medium_confidence"
        else:
            confidence = "low_confidence"
        factors.append(f"Low activity: only {event_count} events logged")
    
    # Very close scores
    if score_gap < 50 and score_gap > 0:
        confidence = "low_confidence"
        factors.append(f"Extremely close: {score_gap:.0f} point difference")
    
    return confidence, factors

async def detect_and_flag_discrepancies(bout_id: str, round_num: int, round_score: RoundScore, events: list):
    """Automatically detect and create flags for controversial decisions"""
    flags_created = []
    
    try:
        delta = round_score.score_gap
        
        # Flag 1: Boundary cases (close to threshold)
        if abs(delta - 600) < 50:
            flag = DiscrepancyFlag(
                bout_id=bout_id,
                round_num=round_num,
                flag_type="boundary_10_9_vs_10_8",
                severity="medium",
                description=f"Score is {delta:.0f} points, very close to 10-8 threshold (600)",
                context={
                    "delta": delta,
                    "threshold": 600,
                    "difference_from_threshold": abs(delta - 600),
                    "card": round_score.card
                }
            )
            doc = flag.model_dump()
            doc = prepare_for_mongo(doc)
            await db.discrepancy_flags.insert_one(doc)
            flags_created.append("boundary_10_9_vs_10_8")
        
        if abs(delta - 900) < 50:
            flag = DiscrepancyFlag(
                bout_id=bout_id,
                round_num=round_num,
                flag_type="boundary_10_8_vs_10_7",
                severity="high",
                description=f"Score is {delta:.0f} points, very close to 10-7 threshold (900)",
                context={
                    "delta": delta,
                    "threshold": 900,
                    "difference_from_threshold": abs(delta - 900),
                    "card": round_score.card
                }
            )
            doc = flag.model_dump()
            doc = prepare_for_mongo(doc)
            await db.discrepancy_flags.insert_one(doc)
            flags_created.append("boundary_10_8_vs_10_7")
        
        # Flag 2: Tie-breaker used
        if round_score.reasons.tie_breaker:
            flag = DiscrepancyFlag(
                bout_id=bout_id,
                round_num=round_num,
                flag_type="tie_breaker_used",
                severity="medium",
                description=f"Round decided by tie-breaker: {round_score.reasons.tie_breaker}",
                context={
                    "tie_breaker": round_score.reasons.tie_breaker,
                    "delta": delta,
                    "card": round_score.card
                }
            )
            doc = flag.model_dump()
            doc = prepare_for_mongo(doc)
            await db.discrepancy_flags.insert_one(doc)
            flags_created.append("tie_breaker_used")
        
        # Flag 3: Very close decision
        if delta < 100 and not round_score.reasons.draw:
            flag = DiscrepancyFlag(
                bout_id=bout_id,
                round_num=round_num,
                flag_type="very_close_decision",
                severity="low",
                description=f"Extremely close round with only {delta:.0f} point difference",
                context={
                    "delta": delta,
                    "card": round_score.card,
                    "winner": round_score.winner
                }
            )
            doc = flag.model_dump()
            doc = prepare_for_mongo(doc)
            await db.discrepancy_flags.insert_one(doc)
            flags_created.append("very_close_decision")
        
        # Flag 4: 10-8 without standard gates
        if round_score.reasons.to_108:
            gates = round_score.reasons.gates_winner
            if not gates.finish_threat and not gates.control_dom and not gates.multi_cat_dom:
                flag = DiscrepancyFlag(
                    bout_id=bout_id,
                    round_num=round_num,
                    flag_type="10_8_without_gate",
                    severity="high",
                    description="10-8 score given without any standard dominance gates triggered",
                    context={
                        "delta": delta,
                        "card": round_score.card,
                        "gates": {
                            "finish_threat": gates.finish_threat,
                            "control_dom": gates.control_dom,
                            "multi_cat_dom": gates.multi_cat_dom
                        }
                    }
                )
                doc = flag.model_dump()
                doc = prepare_for_mongo(doc)
                await db.discrepancy_flags.insert_one(doc)
                flags_created.append("10_8_without_gate")
        
        # Flag 5: Low activity round
        event_count = len(events)
        if event_count < 5:
            flag = DiscrepancyFlag(
                bout_id=bout_id,
                round_num=round_num,
                flag_type="low_activity",
                severity="low",
                description=f"Very low activity round with only {event_count} logged events",
                context={
                    "event_count": event_count,
                    "card": round_score.card
                }
            )
            doc = flag.model_dump()
            doc = prepare_for_mongo(doc)
            await db.discrepancy_flags.insert_one(doc)
            flags_created.append("low_activity")
        
        return flags_created
        
    except Exception as e:
        logger.error(f"Error detecting discrepancies: {str(e)}")
        return []

# Discrepancy Flags Endpoints
@api_router.post("/review/create-flag")
async def create_review_flag(flag: DiscrepancyFlagCreate):
    """Manually create a review flag"""
    try:
        flag_obj = DiscrepancyFlag(**flag.model_dump())
        doc = flag_obj.model_dump()
        doc = prepare_for_mongo(doc)
        await db.discrepancy_flags.insert_one(doc)
        return {"success": True, "flag_id": flag_obj.id}
    except Exception as e:
        logger.error(f"Error creating flag: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/review/flags")
async def get_review_flags(status: str = None, severity: str = None, flag_type: str = None):
    """Get all review flags with optional filters"""
    try:
        query = {}
        if status:
            query["status"] = status
        if severity:
            query["severity"] = severity
        if flag_type:
            query["flag_type"] = flag_type
        
        flags = await db.discrepancy_flags.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
        flags = [parse_from_mongo(f) for f in flags]
        return {"flags": flags, "count": len(flags)}
    except Exception as e:
        logger.error(f"Error fetching flags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/review/flags/{bout_id}")
async def get_bout_flags(bout_id: str):
    """Get all flags for a specific bout"""
    try:
        flags = await db.discrepancy_flags.find(
            {"bout_id": bout_id},
            {"_id": 0}
        ).sort("round_num", 1).to_list(100)
        
        flags = [parse_from_mongo(f) for f in flags]
        return {"flags": flags, "count": len(flags)}
    except Exception as e:
        logger.error(f"Error fetching bout flags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/review/resolve/{flag_id}")
async def resolve_flag(flag_id: str, resolution: FlagResolution):
    """Resolve or dismiss a review flag"""
    try:
        flag = await db.discrepancy_flags.find_one({"id": flag_id})
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        update_data = {
            "status": resolution.status,
            "resolved_by": resolution.resolved_by,
            "resolution_notes": resolution.resolution_notes,
            "resolved_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.discrepancy_flags.update_one(
            {"id": flag_id},
            {"$set": update_data}
        )
        
        return {"success": True, "message": f"Flag {resolution.status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving flag: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/review/stats")
async def get_review_stats():
    """Get statistics about review flags"""
    try:
        # Count by status
        pending = await db.discrepancy_flags.count_documents({"status": "pending"})
        under_review = await db.discrepancy_flags.count_documents({"status": "under_review"})
        resolved = await db.discrepancy_flags.count_documents({"status": "resolved"})
        dismissed = await db.discrepancy_flags.count_documents({"status": "dismissed"})
        
        # Count by severity
        high = await db.discrepancy_flags.count_documents({"severity": "high"})
        medium = await db.discrepancy_flags.count_documents({"severity": "medium"})
        low = await db.discrepancy_flags.count_documents({"severity": "low"})
        
        # Count by type
        pipeline = [
            {"$group": {"_id": "$flag_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        by_type = await db.discrepancy_flags.aggregate(pipeline).to_list(20)
        
        return {
            "by_status": {
                "pending": pending,
                "under_review": under_review,
                "resolved": resolved,
                "dismissed": dismissed,
                "total": pending + under_review + resolved + dismissed
            },
            "by_severity": {
                "high": high,
                "medium": medium,
                "low": low
            },
            "by_type": [{"type": item["_id"], "count": item["count"]} for item in by_type]
        }
    except Exception as e:
        logger.error(f"Error fetching review stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Tuning Profile Endpoints
@api_router.post("/tuning-profiles/create")
async def create_tuning_profile(profile: TuningProfileCreate):
    """Create a new tuning profile"""
    try:
        profile_obj = TuningProfile(**profile.model_dump())
        doc = profile_obj.model_dump()
        doc = prepare_for_mongo(doc)
        await db.tuning_profiles.insert_one(doc)
        return {"success": True, "profile_id": profile_obj.id, "profile": profile_obj}
    except Exception as e:
        logger.error(f"Error creating tuning profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/tuning-profiles")
async def get_tuning_profiles():
    """Get all tuning profiles"""
    try:
        profiles = await db.tuning_profiles.find({}, {"_id": 0}).to_list(100)
        profiles = [parse_from_mongo(p) for p in profiles]
        return {"profiles": profiles, "count": len(profiles)}
    except Exception as e:
        logger.error(f"Error fetching tuning profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/tuning-profiles/default")
async def get_default_profile():
    """Get the default UFC profile"""
    try:
        profile = await db.tuning_profiles.find_one({"is_default": True}, {"_id": 0})
        
        if not profile:
            # Create default UFC profile if it doesn't exist
            default_profile = TuningProfile(
                name="UFC Standard",
                promotion="UFC",
                description="Official UFC judging criteria with standard weights",
                is_default=True,
                created_by="system"
            )
            doc = default_profile.model_dump()
            doc = prepare_for_mongo(doc)
            await db.tuning_profiles.insert_one(doc)
            return default_profile
        
        profile = parse_from_mongo(profile)
        return profile
    except Exception as e:
        logger.error(f"Error fetching default profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/tuning-profiles/{profile_id}")
async def get_tuning_profile(profile_id: str):
    """Get a specific tuning profile"""
    try:
        profile = await db.tuning_profiles.find_one({"id": profile_id}, {"_id": 0})
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = parse_from_mongo(profile)
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tuning profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/tuning-profiles/{profile_id}")
async def update_tuning_profile(profile_id: str, update: TuningProfileUpdate):
    """Update a tuning profile"""
    try:
        profile = await db.tuning_profiles.find_one({"id": profile_id})
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Build update document
        update_data = {k: v for k, v in update.model_dump().items() if v is not None}
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Convert nested models to dicts
        if "weights" in update_data and hasattr(update_data["weights"], 'model_dump'):
            update_data["weights"] = update_data["weights"].model_dump()
        if "thresholds" in update_data and hasattr(update_data["thresholds"], 'model_dump'):
            update_data["thresholds"] = update_data["thresholds"].model_dump()
        if "gate_sensitivity" in update_data and hasattr(update_data["gate_sensitivity"], 'model_dump'):
            update_data["gate_sensitivity"] = update_data["gate_sensitivity"].model_dump()
        
        await db.tuning_profiles.update_one(
            {"id": profile_id},
            {"$set": update_data}
        )
        
        # Return updated profile
        updated_profile = await db.tuning_profiles.find_one({"id": profile_id}, {"_id": 0})
        updated_profile = parse_from_mongo(updated_profile)
        
        return updated_profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tuning profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/tuning-profiles/{profile_id}")
async def delete_tuning_profile(profile_id: str):
    """Delete a tuning profile"""
    try:
        profile = await db.tuning_profiles.find_one({"id": profile_id})
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        if profile.get("is_default"):
            raise HTTPException(status_code=400, detail="Cannot delete default profile")
        
        await db.tuning_profiles.delete_one({"id": profile_id})
        
        return {"success": True, "message": "Profile deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tuning profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Security & Audit Functions
import hashlib
import json

def generate_signature(data: dict) -> str:
    """Generate cryptographic signature for data integrity"""
    # Sort keys to ensure consistent hashing
    sorted_data = json.dumps(data, sort_keys=True)
    signature = hashlib.sha256(sorted_data.encode()).hexdigest()
    return signature

def verify_signature(data: dict, signature: str) -> bool:
    """Verify cryptographic signature"""
    computed_signature = generate_signature(data)
    return computed_signature == signature

async def create_audit_log(action_type: str, user_id: str, user_name: str, 
                          resource_type: str, resource_id: str, action_data: dict = {}, 
                          ip_address: str = None):
    """Create immutable audit log entry"""
    try:
        # Create audit entry
        entry = AuditLogEntry(
            action_type=action_type,
            user_id=user_id,
            user_name=user_name,
            resource_type=resource_type,
            resource_id=resource_id,
            action_data=action_data,
            ip_address=ip_address
        )
        
        # Generate signature for integrity verification
        signature_data = {
            "timestamp": entry.timestamp.isoformat(),
            "action_type": action_type,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action_data": action_data
        }
        entry.signature = generate_signature(signature_data)
        
        # Save to database (WORM - Write Once Read Many)
        doc = entry.model_dump()
        doc = prepare_for_mongo(doc)
        await db.audit_logs.insert_one(doc)
        
        logger.info(f"Audit log created: {action_type} by {user_name}")
        return entry
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}")
        # Don't fail the main operation if audit logging fails
        return None

# Audit Log Endpoints
@api_router.post("/audit/log")
async def create_audit_log_entry(log: AuditLogCreate):
    """Manually create audit log entry"""
    try:
        entry = await create_audit_log(
            log.action_type,
            log.user_id,
            log.user_name,
            log.resource_type,
            log.resource_id,
            log.action_data,
            log.ip_address
        )
        
        if entry:
            return {"success": True, "log_id": entry.id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create audit log")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in audit log endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/audit/logs")
async def get_audit_logs(
    judge_id: str,  # Required: Judge ID for owner verification
    action_type: str = None,
    user_id: str = None,
    resource_type: str = None,
    limit: int = 100
):
    """Get audit logs with optional filters (Owner access only)"""
    try:
        # Verify owner access
        verify_owner_access(judge_id)
        
        query = {}
        if action_type:
            query["action_type"] = action_type
        if user_id:
            query["user_id"] = user_id
        if resource_type:
            query["resource_type"] = resource_type
        
        logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
        logs = [parse_from_mongo(log) for log in logs]
        
        return {
            "logs": logs,
            "count": len(logs),
            "immutable": True,
            "message": "These logs are WORM (Write Once Read Many) and cannot be modified"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/audit/verify/{log_id}")
async def verify_audit_log(log_id: str, judge_id: str):
    """Verify cryptographic signature of an audit log (Owner access only)"""
    try:
        # Verify owner access
        verify_owner_access(judge_id)
        
        log = await db.audit_logs.find_one({"id": log_id}, {"_id": 0})
        
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")
        
        log = parse_from_mongo(log)
        
        # Reconstruct signature data
        signature_data = {
            "timestamp": log["timestamp"].isoformat() if isinstance(log["timestamp"], datetime) else log["timestamp"],
            "action_type": log["action_type"],
            "user_id": log["user_id"],
            "resource_type": log["resource_type"],
            "resource_id": log["resource_id"],
            "action_data": log["action_data"]
        }
        
        computed_signature = generate_signature(signature_data)
        is_valid = computed_signature == log["signature"]
        
        return SignatureVerification(
            valid=is_valid,
            signature=log["signature"],
            computed_signature=computed_signature,
            message="Signature is valid - log has not been tampered with" if is_valid else "WARNING: Signature mismatch - log may have been tampered with"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/audit/export")
async def export_audit_logs(
    judge_id: str,  # Required: Judge ID for owner verification
    start_date: str = None,
    end_date: str = None,
    format: str = "json"
):
    """Export audit logs for compliance/archival (Owner access only)"""
    try:
        # Verify owner access
        verify_owner_access(judge_id)
        
        query = {}
        
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        if end_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_date
            else:
                query["timestamp"] = {"$lte": end_date}
        
        logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", 1).to_list(10000)
        logs = [parse_from_mongo(log) for log in logs]
        
        # Convert datetime to string for JSON serialization
        for log in logs:
            if isinstance(log.get("timestamp"), datetime):
                log["timestamp"] = log["timestamp"].isoformat()
        
        return {
            "export_format": format,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": len(logs),
            "logs": logs,
            "immutable": True,
            "note": "This is a certified export of WORM audit logs"
        }
    except Exception as e:
        logger.error(f"Error exporting audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/audit/stats")
async def get_audit_stats(judge_id: str):
    """Get statistics about audit logs (Owner access only)"""
    try:
        # Verify owner access
        verify_owner_access(judge_id)
        
        total = await db.audit_logs.count_documents({})
        
        # Count by action type
        pipeline = [
            {"$group": {"_id": "$action_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        by_type = await db.audit_logs.aggregate(pipeline).to_list(50)
        
        # Count by user
        user_pipeline = [
            {"$group": {"_id": "$user_id", "user_name": {"$first": "$user_name"}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        by_user = await db.audit_logs.aggregate(user_pipeline).to_list(10)
        
        return {
            "total_logs": total,
            "by_action_type": [{"type": item["_id"], "count": item["count"]} for item in by_type],
            "top_users": [
                {"user_id": item["_id"], "user_name": item["user_name"], "count": item["count"]} 
                for item in by_user
            ],
            "immutable": True,
            "worm_compliant": True
        }
    except Exception as e:
        logger.error(f"Error fetching audit stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Judge Profile Management APIs
@api_router.post("/judges")
async def create_or_update_judge(profile: JudgeProfileCreate):
    """Create or update judge profile"""
    try:
        existing = await db.judges.find_one({"judgeId": profile.judgeId})
        
        profile_dict = profile.dict()
        
        if existing:
            # Update existing profile
            profile_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
            await db.judges.update_one(
                {"judgeId": profile.judgeId},
                {"$set": prepare_for_mongo(profile_dict)}
            )
            message = "Profile updated successfully"
        else:
            # Create new profile
            profile_dict["createdAt"] = datetime.now(timezone.utc).isoformat()
            profile_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
            profile_dict["totalRoundsJudged"] = 0
            profile_dict["averageAccuracy"] = 0.0
            await db.judges.insert_one(prepare_for_mongo(profile_dict))
            message = "Profile created successfully"
        
        return {"success": True, "message": message, "judgeId": profile.judgeId}
    except Exception as e:
        logger.error(f"Error creating/updating judge profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/judges/{judge_id}")
async def get_judge_profile(judge_id: str):
    """Get judge profile by ID"""
    try:
        profile = await db.judges.find_one({"judgeId": judge_id}, {"_id": 0})
        
        if not profile:
            raise HTTPException(status_code=404, detail="Judge profile not found")
        
        profile = parse_from_mongo(profile)
        
        # Get latest stats from shadow judging
        submissions = await db.judge_performance.find({"judgeId": judge_id}, {"_id": 0}).to_list(1000)
        
        if submissions:
            total_attempts = len(submissions)
            avg_accuracy = sum(s["accuracy"] for s in submissions) / total_attempts
            perfect_matches = sum(1 for s in submissions if s["match"])
            
            profile["totalRoundsJudged"] = total_attempts
            profile["averageAccuracy"] = round(avg_accuracy, 2)
            profile["perfectMatches"] = perfect_matches
        
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching judge profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/judges/{judge_id}")
async def update_judge_profile(judge_id: str, updates: JudgeProfileUpdate):
    """Update judge profile"""
    try:
        existing = await db.judges.find_one({"judgeId": judge_id})
        
        if not existing:
            raise HTTPException(status_code=404, detail="Judge profile not found")
        
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        update_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()
        
        await db.judges.update_one(
            {"judgeId": judge_id},
            {"$set": prepare_for_mongo(update_dict)}
        )
        
        return {"success": True, "message": "Profile updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating judge profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/judges/{judge_id}/history")
async def get_judge_history(judge_id: str, limit: int = 50):
    """Get judge's scoring history"""
    try:
        # Get shadow judging submissions
        submissions = await db.judge_performance.find(
            {"judgeId": judge_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        submissions = [parse_from_mongo(sub) for sub in submissions]
        
        # Calculate summary stats
        if submissions:
            total = len(submissions)
            avg_accuracy = sum(s["accuracy"] for s in submissions) / total
            avg_mae = sum(s["mae"] for s in submissions) / total
            perfect_matches = sum(1 for s in submissions if s["match"])
            
            stats = {
                "totalAttempts": total,
                "averageAccuracy": round(avg_accuracy, 2),
                "averageMAE": round(avg_mae, 2),
                "perfectMatches": perfect_matches
            }
        else:
            stats = {
                "totalAttempts": 0,
                "averageAccuracy": 0,
                "averageMAE": 0,
                "perfectMatches": 0
            }
        
        return {
            "judgeId": judge_id,
            "stats": stats,
            "history": submissions
        }
    except Exception as e:
        logger.error(f"Error fetching judge history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# I. EVENT DEDUPLICATION + IDEMPOTENT UPSERT ENGINE
# ============================================================================

@api_router.post("/events/v2/log")
async def log_event_v2(event: EventV2):
    """
    Enhanced event logging with deduplication and hash chain
    Prevents duplicate events from double-taps, resends, or reconnections
    """
    try:
        result = await dedup_engine.upsert_event(
            bout_id=event.bout_id,
            round_id=event.round_id,
            judge_id=event.judge_id,
            fighter_id=event.fighter_id,
            event_type=event.event_type,
            timestamp_ms=event.timestamp_ms,
            device_id=event.device_id,
            metadata=event.metadata
        )
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logging.error(f"Error logging event v2: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/events/v2/verify/{bout_id}/{round_id}")
async def verify_event_chain_integrity(bout_id: str, round_id: int):
    """
    Verify tamper-proof hash chain integrity for a round
    """
    try:
        events = await db.events_v2.find({
            "bout_id": bout_id,
            "round_id": round_id
        }).to_list(10000)
        
        is_valid = verify_event_chain(events)
        
        return {
            "bout_id": bout_id,
            "round_id": round_id,
            "total_events": len(events),
            "chain_valid": is_valid,
            "message": "Hash chain intact" if is_valid else "TAMPERING DETECTED"
        }
    except Exception as e:
        logging.error(f"Error verifying chain: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/events/v2/{bout_id}/{round_id}")
async def get_events_v2(bout_id: str, round_id: int):
    """
    Get all events for a bout/round in correct sequence order
    """
    try:
        events = await db.events_v2.find({
            "bout_id": bout_id,
            "round_id": round_id
        }).sort("sequence_index", 1).to_list(10000)
        
        # Remove MongoDB _id for JSON serialization
        for event in events:
            event.pop('_id', None)
        
        return {
            "bout_id": bout_id,
            "round_id": round_id,
            "count": len(events),
            "total_events": len(events),
            "events": events
        }
    except Exception as e:
        logging.error(f"Error fetching events v2: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Judge Score Synchronization Endpoints
SUPERVISOR_CODE = os.environ.get('SUPERVISOR_CODE', '199215')

@api_router.post("/judge-scores/lock")
async def lock_judge_score(score: JudgeScoreLock):
    """Lock a judge's score for a specific round"""
    try:
        score_data = {
            "judge_id": score.judge_id,
            "judge_name": score.judge_name,
            "bout_id": score.bout_id,
            "round_num": score.round_num,
            "fighter1_score": score.fighter1_score,
            "fighter2_score": score.fighter2_score,
            "card": score.card,
            "locked": True,
            "locked_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Update or insert judge score
        await db.judge_scores.update_one(
            {
                "bout_id": score.bout_id,
                "round_num": score.round_num,
                "judge_id": score.judge_id
            },
            {"$set": score_data},
            upsert=True
        )
        
        # Check if all judges have locked for this round
        all_scores = await db.judge_scores.find({
            "bout_id": score.bout_id,
            "round_num": score.round_num
        }).to_list(100)
        
        all_locked = all([s.get("locked", False) for s in all_scores])
        
        return {
            "success": True,
            "message": "Score locked successfully",
            "all_judges_locked": all_locked,
            "total_judges": len(all_scores),
            "locked_judges": len([s for s in all_scores if s.get("locked", False)])
        }
    except Exception as e:
        logging.error(f"Error locking judge score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/judge-scores/unlock")
async def unlock_judge_score(unlock_request: JudgeScoreUnlock):
    """Unlock a judge's score (supervisor only)"""
    try:
        # Verify supervisor code
        if unlock_request.supervisor_code != SUPERVISOR_CODE:
            raise HTTPException(status_code=403, detail="Invalid supervisor code")
        
        # Unlock the score
        result = await db.judge_scores.update_one(
            {
                "bout_id": unlock_request.bout_id,
                "round_num": unlock_request.round_num,
                "judge_id": unlock_request.judge_id
            },
            {"$set": {"locked": False, "locked_at": None}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Judge score not found")
        
        return {"success": True, "message": "Score unlocked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error unlocking judge score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/judge-scores/{bout_id}/{round_num}")
async def get_judge_scores(bout_id: str, round_num: int):
    """Get all judge scores for a specific bout and round"""
    try:
        scores = await db.judge_scores.find({
            "bout_id": bout_id,
            "round_num": round_num
        }).to_list(100)
        
        # Parse timestamps
        for score in scores:
            if isinstance(score.get('locked_at'), str):
                score['locked_at'] = datetime.fromisoformat(score['locked_at'])
            score.pop('_id', None)
        
        all_locked = all([s.get("locked", False) for s in scores])
        
        return {
            "scores": scores,
            "total_judges": len(scores),
            "locked_judges": len([s for s in scores if s.get("locked", False)]),
            "all_judges_locked": all_locked
        }
    except Exception as e:
        logging.error(f"Error fetching judge scores: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/judge-scores/{bout_id}")
async def get_all_judge_scores_for_bout(bout_id: str):
    """Get all judge scores for all rounds of a bout"""
    try:
        scores = await db.judge_scores.find({
            "bout_id": bout_id
        }).to_list(1000)
        
        # Parse timestamps and organize by round
        for score in scores:
            if isinstance(score.get('locked_at'), str):
                score['locked_at'] = datetime.fromisoformat(score['locked_at'])
            score.pop('_id', None)
        
        # Group by round
        by_round = {}
        for score in scores:
            round_num = score["round_num"]
            if round_num not in by_round:
                by_round[round_num] = []
            by_round[round_num].append(score)
        
        return {
            "bout_id": bout_id,
            "rounds": by_round,
            "total_scores": len(scores)
        }
    except Exception as e:
        logging.error(f"Error fetching all judge scores: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/rounds/force-close")
async def force_close_round(request: ForceCloseRound):
    """Force close a round (supervisor override)"""
    try:
        # Verify supervisor code
        if request.supervisor_code != SUPERVISOR_CODE:
            raise HTTPException(status_code=403, detail="Invalid supervisor code")
        
        # Mark round as force-closed in database
        await db.force_closed_rounds.insert_one({
            "bout_id": request.bout_id,
            "round_num": request.round_num,
            "closed_by": request.closed_by,
            "closed_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": f"Round {request.round_num} force-closed successfully",
            "closed_by": request.closed_by
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error force-closing round: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# II. ROUND REPLAY ENGINE
# ============================================================================

@api_router.get("/replay/{bout_id}/{round_id}")
async def get_round_replay(bout_id: str, round_id: int, round_length: int = 300):
    """
    Reconstruct round second-by-second timeline with accumulated scores
    Performance target: <150ms
    """
    try:
        start_time = time.time()
        
        replay_data = await reconstruct_round_timeline(db, bout_id, round_id, round_length)
        
        elapsed = (time.time() - start_time) * 1000
        logging.info(f"Replay generated in {elapsed:.2f}ms")
        
        return {
            "success": True,
            "performance_ms": round(elapsed, 2),
            **replay_data
        }
    except Exception as e:
        logging.error(f"Error generating replay: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# III. BROADCAST API LAYER
# ============================================================================

@api_router.get("/live/{bout_id}")
async def get_live_broadcast_data(bout_id: str):
    """
    Real-time broadcast endpoint for jumbotrons, TV graphics, commentary
    Performance target: <100ms
    Refresh rate: 250-500ms
    """
    try:
        start_time = time.time()
        
        # Get bout info - try both _id and boutId fields for compatibility
        bout = await db.bouts.find_one({"$or": [{"_id": bout_id}, {"boutId": bout_id}]})
        if not bout:
            # Try without filter to see if any bouts exist
            any_bout = await db.bouts.find_one({})
            if any_bout:
                logging.warning(f"Bout {bout_id} not found, but other bouts exist")
            raise HTTPException(status_code=404, detail=f"Bout {bout_id} not found")
        
        round_id = bout.get('currentRound', 1)
        
        # Get latest events (last 5 seconds)
        five_sec_ago = int((time.time() - 5) * 1000)
        recent_events = await db.events_v2.find({
            "bout_id": bout_id,
            "round_id": round_id,
            "server_timestamp_ms": {"$gte": five_sec_ago}
        }).sort("sequence_index", -1).limit(20).to_list(20)
        
        # Calculate live totals using replay engine (cached)
        replay_data = await reconstruct_round_timeline(db, bout_id, round_id)
        summary = replay_data.get('round_summary', {})
        
        # Identify redline moments (major damage events)
        redline_moments = []
        for event in recent_events:
            if event.get('event_type') in ['KD', 'Rocked/Stunned']:
                redline_moments.append({
                    "timestamp": event.get('server_timestamp_ms', 0),
                    "fighter_id": event.get('fighter_id'),
                    "event_type": event.get('event_type'),
                    "severity": event.get('metadata', {}).get('tier', 'Unknown')
                })
        
        elapsed = (time.time() - start_time) * 1000
        
        return {
            "bout_id": bout_id,
            "round_id": round_id,
            "round_status": bout.get('status', 'IN_PROGRESS'),
            "red_totals": {
                "damage": summary.get('damage_score', {}).get('red', 0),
                "grappling": summary.get('grappling_score', {}).get('red', 0),
                "control": summary.get('control_score', {}).get('red', 0),
                "weighted_score": summary.get('total_score', {}).get('red', 0)
            },
            "blue_totals": {
                "damage": summary.get('damage_score', {}).get('blue', 0),
                "grappling": summary.get('grappling_score', {}).get('blue', 0),
                "control": summary.get('control_score', {}).get('blue', 0),
                "weighted_score": summary.get('total_score', {}).get('blue', 0)
            },
            "time_remaining": bout.get('timeRemaining', '5:00'),
            "events_last_5_sec": len(recent_events),
            "redline_moments": redline_moments,
            "performance_ms": round(elapsed, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in live broadcast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/final/{bout_id}")
async def get_final_broadcast_data(bout_id: str):
    """
    Final bout results for post-fight broadcast
    """
    try:
        # Get bout info - try both _id and boutId fields for compatibility
        bout = await db.bouts.find_one({"$or": [{"_id": bout_id}, {"boutId": bout_id}]})
        if not bout:
            # Try without filter to see if any bouts exist
            any_bout = await db.bouts.find_one({})
            if any_bout:
                logging.warning(f"Bout {bout_id} not found, but other bouts exist")
            raise HTTPException(status_code=404, detail=f"Bout {bout_id} not found")
        
        # Get all judge scorecards
        judge_scores = await db.judge_scores.find({"bout_id": bout_id}).to_list(100)
        
        # Get all rounds and verify chain
        all_valid = True
        for round_id in range(1, bout.get('totalRounds', 3) + 1):
            events = await db.events_v2.find({
                "bout_id": bout_id,
                "round_id": round_id
            }).to_list(10000)
            if not verify_event_chain(events):
                all_valid = False
                break
        
        # Format scorecards
        scorecards = []
        for score in judge_scores:
            score.pop('_id', None)
            scorecards.append(score)
        
        return {
            "bout_id": bout_id,
            "fighter1": bout.get('fighter1'),
            "fighter2": bout.get('fighter2'),
            "final_scores": scorecards,
            "winner": bout.get('winner', 'TBD'),
            "full_event_log_hash_chain_valid": all_valid,
            "total_rounds": bout.get('totalRounds', 3)
        }
    except Exception as e:
        logging.error(f"Error in final broadcast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# VI. TELEMETRY & DEVICE HEALTH ENGINE
# ============================================================================

@api_router.post("/telemetry/report")
async def report_device_telemetry(telemetry: DeviceTelemetry):
    """
    Ingest device health telemetry
    Performance target: <20ms
    """
    try:
        start_time = time.time()
        
        telemetry_doc = {
            "device_id": telemetry.device_id,
            "judge_id": telemetry.judge_id,
            "bout_id": telemetry.bout_id,
            "battery_percent": telemetry.battery_percent,
            "network_strength_percent": telemetry.network_strength_percent,
            "latency_ms": telemetry.latency_ms,
            "fps": telemetry.fps,
            "dropped_event_count": telemetry.dropped_event_count,
            "event_rate_per_second": telemetry.event_rate_per_second,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.telemetry.insert_one(telemetry_doc)
        
        # Generate alerts
        alerts = []
        if telemetry.battery_percent and telemetry.battery_percent < 20:
            alerts.append({"type": "battery_low", "value": telemetry.battery_percent})
        if telemetry.latency_ms and telemetry.latency_ms > 350:
            alerts.append({"type": "high_latency", "value": telemetry.latency_ms})
        if telemetry.network_strength_percent and telemetry.network_strength_percent < 30:
            alerts.append({"type": "poor_network", "value": telemetry.network_strength_percent})
        if telemetry.dropped_event_count > 0:
            alerts.append({"type": "dropped_events", "value": telemetry.dropped_event_count})
        
        elapsed = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "alerts": alerts,
            "performance_ms": round(elapsed, 2)
        }
    except Exception as e:
        logging.error(f"Error reporting telemetry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/telemetry/{bout_id}")
async def get_bout_telemetry(bout_id: str):
    """
    Get real-time telemetry for all devices in a bout
    """
    try:
        # Get recent telemetry (last 30 seconds)
        thirty_sec_ago = datetime.now(timezone.utc).timestamp() - 30
        
        telemetry_data = await db.telemetry.find({
            "bout_id": bout_id
        }).sort("timestamp", -1).limit(100).to_list(100)
        
        # Group by device and remove MongoDB _id
        devices = {}
        for t in telemetry_data:
            t.pop('_id', None)  # Remove ObjectId for JSON serialization
            device_id = t.get('device_id')
            if device_id not in devices:
                devices[device_id] = t
        
        return {
            "bout_id": bout_id,
            "devices": list(devices.values()),
            "total_devices": len(devices)
        }
    except Exception as e:
        logging.error(f"Error fetching telemetry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# V. JUDGE SESSION & HOT-SWAP ENGINE
# ============================================================================

@api_router.post("/judge-session/create")
async def create_judge_session(session: JudgeSession):
    """
    Create or restore judge session for hot-swap capability
    """
    try:
        session_doc = {
            "judge_session_id": session.judge_session_id,
            "judge_id": session.judge_id,
            "bout_id": session.bout_id,
            "round_id": session.round_id,
            "last_event_sequence": session.last_event_sequence,
            "session_state": session.session_state,
            "unsent_event_queue": session.unsent_event_queue,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert session
        await db.judge_sessions.update_one(
            {"judge_session_id": session.judge_session_id},
            {"$set": session_doc},
            upsert=True
        )
        
        return {
            "success": True,
            "session_id": session.judge_session_id,
            "judge_session_id": session.judge_session_id,
            "message": "Session saved"
        }
    except Exception as e:
        logging.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/judge-session/{judge_session_id}")
async def restore_judge_session(judge_session_id: str):
    """
    Restore judge session for hot-swap (device change mid-fight)
    Performance target: <200ms
    """
    try:
        start_time = time.time()
        
        session = await db.judge_sessions.find_one({"judge_session_id": judge_session_id})
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.pop('_id', None)
        
        elapsed = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "session": session,
            "performance_ms": round(elapsed, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error restoring session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SYSTEM 2: ROUND NOTES ENGINE
# ============================================================================

class RoundNote(BaseModel):
    """Model for round notes"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    judge_id: str
    judge_name: str
    note_text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[Dict[str, Any]] = None

class RoundNoteCreate(BaseModel):
    """Model for creating a round note"""
    bout_id: str
    round_num: int
    judge_id: str
    judge_name: str
    note_text: str
    metadata: Optional[Dict[str, Any]] = None

@api_router.post("/round-notes", response_model=RoundNote, status_code=201)
async def create_round_note(note: RoundNoteCreate):
    """Create a new round note"""
    try:
        note_data = RoundNote(
            bout_id=note.bout_id,
            round_num=note.round_num,
            judge_id=note.judge_id,
            judge_name=note.judge_name,
            note_text=note.note_text,
            metadata=note.metadata or {}
        )
        
        result = await db.round_notes.insert_one(note_data.model_dump())
        logger.info(f"Round note created: {note_data.id} for bout {note.bout_id} round {note.round_num}")
        
        return note_data
    except Exception as e:
        logger.error(f"Error creating round note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/round-notes/{bout_id}/{round_num}")
async def get_round_notes(bout_id: str, round_num: int, judge_id: Optional[str] = None):
    """Get all notes for a specific bout and round"""
    try:
        query = {"bout_id": bout_id, "round_num": round_num}
        if judge_id:
            query["judge_id"] = judge_id
        
        notes_cursor = db.round_notes.find(query, {"_id": 0}).sort("timestamp", 1)
        notes = await notes_cursor.to_list(length=None)
        
        return {"notes": notes, "count": len(notes)}
    except Exception as e:
        logger.error(f"Error fetching round notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/round-notes/{bout_id}")
async def get_bout_notes(bout_id: str, judge_id: Optional[str] = None):
    """Get all notes for a bout"""
    try:
        query = {"bout_id": bout_id}
        if judge_id:
            query["judge_id"] = judge_id
        
        notes_cursor = db.round_notes.find(query, {"_id": 0}).sort("round_num", 1).sort("timestamp", 1)
        notes = await notes_cursor.to_list(length=None)
        
        # Group by round
        notes_by_round = {}
        for note in notes:
            round_num = note.get("round_num")
            if round_num not in notes_by_round:
                notes_by_round[round_num] = []
            notes_by_round[round_num].append(note)
        
        return {
            "notes": notes,
            "notes_by_round": notes_by_round,
            "total_count": len(notes)
        }
    except Exception as e:
        logger.error(f"Error fetching bout notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/round-notes/{note_id}")
async def update_round_note(note_id: str, note_text: str = Form(...)):
    """Update an existing round note"""
    try:
        result = await db.round_notes.update_one(
            {"id": note_id},
            {"$set": {
                "note_text": note_text,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Note not found")
        
        return {"success": True, "message": "Note updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating round note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/round-notes/{note_id}")
async def delete_round_note(note_id: str):
    """Delete a round note"""
    try:
        result = await db.round_notes.delete_one({"id": note_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Note not found")
        
        return {"success": True, "message": "Note deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting round note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SYSTEM 3: SUPERVISOR DASHBOARD DATA FEEDS
# ============================================================================

@api_router.get("/supervisor/dashboard/{bout_id}")
async def get_supervisor_dashboard(bout_id: str):
    """Get comprehensive dashboard data for supervisor"""
    try:
        # Get all judge scores
        judge_scores_cursor = db.judge_scores.find({"bout_id": bout_id}, {"_id": 0})
        judge_scores = await judge_scores_cursor.to_list(length=None)
        
        # Get all events
        events_cursor = db.events.find({"boutId": bout_id}, {"_id": 0})
        events = await events_cursor.to_list(length=None)
        
        # Get round notes
        notes_cursor = db.round_notes.find({"bout_id": bout_id}, {"_id": 0})
        notes = await notes_cursor.to_list(length=None)
        
        # Calculate stats per round
        rounds_data = {}
        for score in judge_scores:
            round_num = score.get("round_num")
            if round_num not in rounds_data:
                rounds_data[round_num] = {
                    "scores": [],
                    "locked_count": 0,
                    "total_judges": 0
                }
            rounds_data[round_num]["scores"].append(score)
            rounds_data[round_num]["total_judges"] += 1
            if score.get("locked"):
                rounds_data[round_num]["locked_count"] += 1
        
        # Detect anomalies
        anomalies = []
        for round_num, data in rounds_data.items():
            if data["total_judges"] >= 2:
                scores = [s.get("fighter1_score", 10) for s in data["scores"]]
                max_variance = max(scores) - min(scores)
                if max_variance > 2:  # More than 2 point variance
                    anomalies.append({
                        "round": round_num,
                        "type": "variance",
                        "severity": "high" if max_variance > 3 else "medium",
                        "message": f"High score variance ({max_variance} points) in Round {round_num}"
                    })
        
        return {
            "bout_id": bout_id,
            "judge_scores": judge_scores,
            "rounds_data": rounds_data,
            "total_events": len(events),
            "total_notes": len(notes),
            "anomalies": anomalies,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting supervisor dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SYSTEM 4: AI JUDGE VARIANCE DETECTION (Rule-Based)
# ============================================================================

@api_router.get("/variance/detect/{bout_id}/{round_num}")
async def detect_judge_variance(bout_id: str, round_num: int):
    """Detect variance between judge scores using rule-based algorithm"""
    try:
        # Get all judge scores for this round
        judge_scores_cursor = db.judge_scores.find({
            "bout_id": bout_id,
            "round_num": round_num
        }, {"_id": 0})
        judge_scores = await judge_scores_cursor.to_list(length=None)
        
        if len(judge_scores) < 2:
            return {
                "bout_id": bout_id,
                "round_num": round_num,
                "variance_detected": False,
                "message": "Insufficient judges for variance detection",
                "judge_count": len(judge_scores)
            }
        
        # Extract scores
        fighter1_scores = [s.get("fighter1_score", 10) for s in judge_scores]
        fighter2_scores = [s.get("fighter2_score", 10) for s in judge_scores]
        
        # Calculate variance metrics
        f1_variance = max(fighter1_scores) - min(fighter1_scores)
        f2_variance = max(fighter2_scores) - min(fighter2_scores)
        max_variance = max(f1_variance, f2_variance)
        
        # Detect outliers
        outliers = []
        for i, score in enumerate(judge_scores):
            f1_score = score.get("fighter1_score", 10)
            f2_score = score.get("fighter2_score", 10)
            
            # Check if this judge's score is outlier (>2 points from any other judge)
            is_outlier = False
            for j, other_score in enumerate(judge_scores):
                if i != j:
                    other_f1 = other_score.get("fighter1_score", 10)
                    other_f2 = other_score.get("fighter2_score", 10)
                    
                    if abs(f1_score - other_f1) > 2 or abs(f2_score - other_f2) > 2:
                        is_outlier = True
                        break
            
            if is_outlier:
                outliers.append({
                    "judge_id": score.get("judge_id"),
                    "judge_name": score.get("judge_name"),
                    "card": score.get("card"),
                    "fighter1_score": f1_score,
                    "fighter2_score": f2_score
                })
        
        # Determine severity
        severity = "low"
        if max_variance > 3:
            severity = "critical"
        elif max_variance > 2:
            severity = "high"
        elif max_variance > 1:
            severity = "medium"
        
        variance_detected = max_variance > 2  # Threshold: 2+ points
        
        return {
            "bout_id": bout_id,
            "round_num": round_num,
            "variance_detected": variance_detected,
            "max_variance": max_variance,
            "fighter1_variance": f1_variance,
            "fighter2_variance": f2_variance,
            "severity": severity,
            "outliers": outliers,
            "judge_count": len(judge_scores),
            "all_scores": judge_scores,
            "message": f"{'Variance detected' if variance_detected else 'No significant variance'} ({max_variance} points max)"
        }
    except Exception as e:
        logger.error(f"Error detecting variance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SYSTEM 6: PROMOTION BRANDING ENGINE
# ============================================================================

class PromotionBranding(BaseModel):
    """Model for promotion branding"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    promotion_name: str
    logo_url: Optional[str] = None
    primary_color: str = "#FF6B35"  # Default orange
    secondary_color: str = "#004E89"  # Default blue
    accent_color: str = "#F7931E"  # Default amber
    font_family: Optional[str] = "Inter"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

@api_router.post("/branding/promotion", response_model=PromotionBranding)
async def create_promotion_branding(branding: PromotionBranding):
    """Create or update promotion branding"""
    try:
        branding_data = branding.model_dump()
        
        # Check if branding already exists for this promotion
        existing = await db.promotion_branding.find_one({"promotion_name": branding.promotion_name})
        
        if existing:
            # Update existing
            branding_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db.promotion_branding.update_one(
                {"promotion_name": branding.promotion_name},
                {"$set": branding_data}
            )
            logger.info(f"Updated branding for {branding.promotion_name}")
        else:
            # Create new
            await db.promotion_branding.insert_one(branding_data)
            logger.info(f"Created branding for {branding.promotion_name}")
        
        return branding
    except Exception as e:
        logger.error(f"Error creating/updating branding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/branding/promotion/{promotion_name}")
async def get_promotion_branding(promotion_name: str):
    """Get branding for a promotion"""
    try:
        branding = await db.promotion_branding.find_one(
            {"promotion_name": promotion_name},
            {"_id": 0}
        )
        
        if not branding:
            # Return default branding
            return {
                "promotion_name": promotion_name,
                "logo_url": None,
                "primary_color": "#FF6B35",
                "secondary_color": "#004E89",
                "accent_color": "#F7931E",
                "font_family": "Inter",
                "is_default": True
            }
        
        branding["is_default"] = False
        return branding
    except Exception as e:
        logger.error(f"Error getting branding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SYSTEM 7: PRODUCTION OUTPUT BUFFERS
# ============================================================================

class BroadcastBuffer(BaseModel):
    """Model for broadcast buffer configuration"""
    bout_id: str
    delay_seconds: int = 5  # Default 5 second delay
    enabled: bool = True

@api_router.post("/broadcast/buffer/config")
async def configure_broadcast_buffer(config: BroadcastBuffer):
    """Configure broadcast delay buffer"""
    try:
        config_data = config.model_dump()
        config_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.broadcast_buffers.update_one(
            {"bout_id": config.bout_id},
            {"$set": config_data},
            upsert=True
        )
        
        logger.info(f"Configured broadcast buffer for {config.bout_id}: {config.delay_seconds}s delay")
        return {"success": True, "config": config_data}
    except Exception as e:
        logger.error(f"Error configuring broadcast buffer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/broadcast/buffer/{bout_id}")
async def get_buffered_data(bout_id: str, timestamp: Optional[float] = None):
    """Get buffered broadcast data with configured delay"""
    try:
        # Get buffer configuration
        buffer_config = await db.broadcast_buffers.find_one({"bout_id": bout_id})
        delay_seconds = buffer_config.get("delay_seconds", 5) if buffer_config else 5
        enabled = buffer_config.get("enabled", True) if buffer_config else True
        
        if not enabled:
            delay_seconds = 0  # No delay if disabled
        
        # Calculate cutoff time
        cutoff_time = time.time() - delay_seconds
        
        # Get bout data
        bout_data = await db.bouts.find_one({"_id": bout_id}, {"_id": 0})
        
        # Get events up to cutoff time
        if timestamp:
            cutoff_timestamp = timestamp - delay_seconds
        else:
            cutoff_timestamp = cutoff_time
        
        # This is a simplified version - in production you'd want more sophisticated buffering
        return {
            "bout_id": bout_id,
            "delay_seconds": delay_seconds,
            "enabled": enabled,
            "cutoff_time": cutoff_time,
            "message": f"Data delayed by {delay_seconds} seconds for broadcast"
        }
    except Exception as e:
        logger.error(f"Error getting buffered data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# ICVSS INTEGRATION
# ============================================================================

try:
    from icvss.routes import icvss_router
    from icvss.round_engine import RoundEngine
    import icvss.routes as icvss_routes_module
    
    # Initialize ICVSS Round Engine with database
    icvss_round_engine = RoundEngine(db)
    icvss_routes_module.round_engine = icvss_round_engine
    
    # Mount ICVSS router under API prefix
    api_router.include_router(icvss_router, prefix="/icvss")
    
    logger.info("✓ ICVSS (Intelligent Combat Vision Scoring System) loaded")
    logger.info("  - Event processing with 80-150ms deduplication")
    logger.info("  - Hybrid CV + Judge scoring (70/30 split)")
    logger.info("  - Real-time WebSocket feeds")
    logger.info("  - SHA256 audit logging")
    
except Exception as e:
    logger.warning(f"ICVSS module not loaded: {e}")
    logger.info("  System will run in legacy mode only")


# ============================================================================
# FIGHT JUDGE AI - Integrated Scoring Engine (E1)
# ============================================================================
try:
    import fjai.routes as fjai_routes_module
    from fjai.routes import fjai_router
    from fjai.round_manager import RoundManager as FJAIRoundManager
    
    # Initialize FJAI round manager
    fjai_round_manager = FJAIRoundManager(db)
    fjai_routes_module.round_manager = fjai_round_manager
    
    # Mount FJAI router
    api_router.include_router(fjai_router, prefix="/fjai")
    
    logger.info("✓ Fight Judge AI (E1) - Integrated Scoring Engine loaded")
    logger.info("  - Damage primacy rule with weighted scoring")
    logger.info("  - 10-Point-Must system")
    logger.info("  - SHA256 audit trails")
    logger.info("  - Multi-camera event fusion")
    
except Exception as e:
    logger.warning(f"Fight Judge AI module not loaded: {e}")

# ============================================================================
# CV ANALYTICS ENGINE (E2)
# ============================================================================
try:
    from cv_analytics.routes import cv_analytics_router
    
    # Mount CV Analytics router
    api_router.include_router(cv_analytics_router, prefix="/cv-analytics")
    
    logger.info("✓ CV Analytics Engine (E2) loaded")
    logger.info("  - Raw CV → Standardized events")
    logger.info("  - Temporal smoothing & optical flow validation")
    logger.info("  - Multi-camera consensus fusion")
    logger.info("  - Momentum swing detection")
    logger.info("  - Fighter style classification")
    
except Exception as e:
    logger.warning(f"CV Analytics Engine not loaded: {e}")

# ============================================================================
# CV ROUTER
# ============================================================================
try:
    from cv_router.routes import cv_router_api
    from cv_router.router_engine import CVRouterEngine
    import cv_router.routes as cv_router_routes_module
    
    # Initialize CV Router
    cv_router_engine = CVRouterEngine()
    cv_router_routes_module.router_engine = cv_router_engine
    
    # Mount router
    api_router.include_router(cv_router_api, prefix="/cv-router")
    
    logger.info("✓ CV Router loaded")
    logger.info("  - Multi-camera stream ingestion")
    logger.info("  - Worker load balancing")
    logger.info("  - Failover & health monitoring")
    
except Exception as e:
    logger.warning(f"CV Router not loaded: {e}")

# ============================================================================
# EVENT HARMONIZER
# ============================================================================
try:
    from event_harmonizer.routes import event_harmonizer_api
    from event_harmonizer.harmonizer_engine import EventHarmonizerEngine
    import event_harmonizer.routes as harmonizer_routes_module
    
    # Initialize Event Harmonizer
    event_harmonizer = EventHarmonizerEngine()
    harmonizer_routes_module.harmonizer_engine = event_harmonizer
    
    # Mount router
    api_router.include_router(event_harmonizer_api, prefix="/harmonizer")
    
    logger.info("✓ Event Harmonizer loaded")
    logger.info("  - Judge vs CV conflict resolution")
    logger.info("  - Weighted confidence logic")
    logger.info("  - Hybrid event merging")
    
except Exception as e:
    logger.warning(f"Event Harmonizer not loaded: {e}")

# ============================================================================
# NORMALIZATION ENGINE
# ============================================================================
try:
    from normalization_engine.routes import normalization_api
    from normalization_engine.normalization_engine import NormalizationEngine
    import normalization_engine.routes as norm_routes_module
    
    # Initialize Normalization Engine
    normalization_engine = NormalizationEngine()
    norm_routes_module.norm_engine = normalization_engine
    
    # Mount router
    api_router.include_router(normalization_api, prefix="/normalization")
    
    logger.info("✓ Normalization Engine loaded")
    logger.info("  - Event weight normalization (0-1 scale)")
    logger.info("  - Global caps & metric drift prevention")
    logger.info("  - Transparent weight breakdown")
    
except Exception as e:
    logger.warning(f"Normalization Engine not loaded: {e}")

# ============================================================================
# ROUND VALIDATOR (Enhanced with Postgres storage)
# ============================================================================
try:
    from round_validator.routes import round_validator_api
    from round_validator.validator_engine import RoundValidatorEngine
    import round_validator.routes as validator_routes_module
    
    # Pass Postgres session if available
    validator_engine = RoundValidatorEngine(
        postgres_session=SessionLocal if postgres_available else None
    )
    validator_routes_module.validator_engine = validator_engine
    
    api_router.include_router(round_validator_api, prefix="/validator")
    logger.info(f"✓ Round Validator loaded [{'Postgres storage' if postgres_available else 'In-memory cache'}]")
    
except Exception as e:
    logger.warning(f"Round Validator not loaded: {e}")

# ============================================================================
# REPORT GENERATOR
# ============================================================================
try:
    from report_generator.routes import report_generator_api
    from report_generator.generator_engine import ReportGeneratorEngine
    import report_generator.routes as report_routes_module
    
    report_engine = ReportGeneratorEngine()
    report_routes_module.report_engine = report_engine
    
    api_router.include_router(report_generator_api, prefix="/report")
    logger.info("✓ Report Generator loaded")
    
except Exception as e:
    logger.warning(f"Report Generator not loaded: {e}")

# ============================================================================
# HIGHLIGHT WORKER
# ============================================================================
try:
    from highlight_worker.routes import highlight_worker_api
    from highlight_worker.worker_engine import HighlightWorkerEngine
    import highlight_worker.routes as highlight_routes_module
    
    highlight_engine = HighlightWorkerEngine()
    highlight_routes_module.highlight_engine = highlight_engine
    
    api_router.include_router(highlight_worker_api, prefix="/highlights")
    logger.info("✓ Highlight Worker loaded")
    
except Exception as e:
    logger.warning(f"Highlight Worker not loaded: {e}")

# ============================================================================
# REPLAY SERVICE
# ============================================================================
try:
    from replay_service.routes import replay_service_api
    from replay_service.replay_engine import ReplayEngine
    import replay_service.routes as replay_routes_module
    
    replay_engine = ReplayEngine()
    replay_routes_module.replay_engine = replay_engine
    
    api_router.include_router(replay_service_api, prefix="/replay")
    logger.info("✓ Replay Service loaded")
    
except Exception as e:
    logger.warning(f"Replay Service not loaded: {e}")

# ============================================================================
# STORAGE MANAGER
# ============================================================================
try:
    from storage_manager.routes import storage_manager_api
    from storage_manager.manager_engine import StorageManagerEngine
    import storage_manager.routes as storage_routes_module
    
    storage_engine = StorageManagerEngine()
    storage_routes_module.storage_engine = storage_engine
    
    api_router.include_router(storage_manager_api, prefix="/storage")
    logger.info("✓ Storage Manager loaded")
    
except Exception as e:
    logger.warning(f"Storage Manager not loaded: {e}")

# ============================================================================
# ADVANCED AUDIT LOGGER
# ============================================================================
try:
    from advanced_audit.routes import advanced_audit_api
    from advanced_audit.audit_engine import AdvancedAuditEngine
    import advanced_audit.routes as audit_routes_module
    
    audit_logger = AdvancedAuditEngine()
    audit_routes_module.audit_engine = audit_logger
    
    api_router.include_router(advanced_audit_api, prefix="/audit")
    logger.info("✓ Advanced Audit Logger loaded - Blockchain-style tamper-proof logging")
    
except Exception as e:
    logger.warning(f"Advanced Audit not loaded: {e}")

# ============================================================================
# SCORING SIMULATOR
# ============================================================================
try:
    from scoring_simulator.routes import scoring_simulator_api
    from scoring_simulator.simulator_engine import ScoringSimulatorEngine
    import scoring_simulator.routes as simulator_routes_module
    
    simulator = ScoringSimulatorEngine()
    simulator_routes_module.simulator_engine = simulator
    
    api_router.include_router(scoring_simulator_api, prefix="/simulator")
    logger.info("✓ Scoring Simulator loaded - Event replay & validation")
    
except Exception as e:
    logger.warning(f"Scoring Simulator not loaded: {e}")

# ============================================================================
# FAILOVER ENGINE
# ============================================================================
try:
    from failover_engine.routes import failover_engine_api
    from failover_engine.failover_manager import FailoverManager
    import failover_engine.routes as failover_routes_module
    
    failover = FailoverManager()
    failover_routes_module.failover_manager = failover
    
    api_router.include_router(failover_engine_api, prefix="/failover")
    logger.info("✓ Failover Engine loaded - Cloud/Local/Manual auto-failover")
    
except Exception as e:
    logger.warning(f"Failover Engine not loaded: {e}")

# ============================================================================
# TIME SYNC SERVICE
# ============================================================================
try:
    from time_sync.routes import time_sync_api
    from time_sync.sync_engine import TimeSyncEngine
    import time_sync.routes as time_sync_routes_module
    
    time_sync = TimeSyncEngine()
    time_sync_routes_module.sync_engine = time_sync
    
    api_router.include_router(time_sync_api, prefix="/timesync")
    logger.info("✓ Time Sync Service loaded - NTP-like unified timestamps")
    
except Exception as e:
    logger.warning(f"Time Sync not loaded: {e}")

# ============================================================================
# CALIBRATION API (Enhanced with Postgres + Redis)
# ============================================================================
try:
    from calibration_api.routes import calibration_api
    from calibration_api.calibration_manager import CalibrationManager
    import calibration_api.routes as calibration_routes_module
    
    # Pass Postgres session and Redis pub/sub if available
    calibration_mgr = CalibrationManager(
        db=db,
        postgres_session=SessionLocal if postgres_available else None,
        redis_pubsub=calibration_pubsub if redis_available else None
    )
    calibration_routes_module.calibration_manager = calibration_mgr
    
    api_router.include_router(calibration_api, prefix="/calibration")
    
    features = []
    if postgres_available:
        features.append("Postgres")
    if redis_available:
        features.append("Redis pub/sub")
    
    logger.info(f"✓ Calibration API loaded - AI model threshold tuning [{', '.join(features) if features else 'In-memory'}]")
    
except Exception as e:
    logger.warning(f"Calibration API not loaded: {e}")

# ============================================================================
# PERFORMANCE PROFILER
# ============================================================================
try:
    from performance_profiler.routes import performance_profiler_api
    from performance_profiler.profiler_engine import PerformanceProfiler
    import performance_profiler.routes as profiler_routes_module
    import asyncio
    
    profiler_engine = PerformanceProfiler(window_size=1000)
    profiler_routes_module.profiler = profiler_engine
    
    # Start background task for mock data generation (for testing)
    async def start_profiler_mock_data():
        asyncio.create_task(profiler_engine.generate_mock_data())
    
    # Schedule mock data generation
    @app.on_event("startup")
    async def startup_profiler():
        asyncio.create_task(profiler_engine.generate_mock_data())
    
    api_router.include_router(performance_profiler_api, prefix="/perf")
    logger.info("✓ Performance Profiler loaded - Real-time metrics & WebSocket streaming")
    
except Exception as e:
    logger.warning(f"Performance Profiler not loaded: {e}")

# ============================================================================
# HEARTBEAT MONITOR
# ============================================================================
try:
    from heartbeat_monitor.routes import heartbeat_api
    from heartbeat_monitor.monitor_engine import HeartbeatMonitor
    import heartbeat_monitor.routes as heartbeat_routes_module
    
    heartbeat_mon = HeartbeatMonitor(db=db)
    heartbeat_routes_module.monitor = heartbeat_mon
    
    api_router.include_router(heartbeat_api, prefix="")
    logger.info("✓ Heartbeat Monitor loaded - Service health tracking for FJAIPOS modules")
    
except Exception as e:
    logger.warning(f"Heartbeat Monitor not loaded: {e}")

# ============================================================================
# FIGHTER ANALYTICS (Phase 1)
# ============================================================================
try:
    from fighter_analytics.routes import fighter_analytics_api
    from fighter_analytics.analytics_engine import FighterAnalyticsEngine
    import fighter_analytics.routes as fighter_analytics_routes_module
    
    fighter_analytics_eng = FighterAnalyticsEngine(db=db)
    fighter_analytics_routes_module.analytics_engine = fighter_analytics_eng
    
    api_router.include_router(fighter_analytics_api, prefix="")
    logger.info("✓ Fighter Analytics loaded - Historical stats, performance trends, leaderboards")
    
except Exception as e:
    logger.warning(f"Fighter Analytics not loaded: {e}")

# ============================================================================
# CV MOMENTS - AI DETECTION (Phase 2)
# ============================================================================
try:
    from cv_moments.routes import cv_moments_api
    from cv_moments.detection_engine import MomentDetectionEngine
    import cv_moments.routes as cv_moments_routes_module
    
    cv_moments_eng = MomentDetectionEngine(db=db)
    cv_moments_routes_module.detection_engine = cv_moments_eng
    
    api_router.include_router(cv_moments_api, prefix="")
    logger.info("✓ CV Moments AI loaded - Knockdown/Strike/Submission detection, Auto-highlights")
    
except Exception as e:
    logger.warning(f"CV Moments AI not loaded: {e}")

# ============================================================================
# BLOCKCHAIN AUDIT (Phase 3)
# ============================================================================
try:
    from blockchain_audit.routes import blockchain_audit_api
    from blockchain_audit.blockchain_engine import BlockchainEngine
    import blockchain_audit.routes as blockchain_routes_module
    
    blockchain_eng = BlockchainEngine(db=db)
    blockchain_routes_module.blockchain_engine = blockchain_eng
    
    api_router.include_router(blockchain_audit_api, prefix="")
    logger.info("✓ Blockchain Audit loaded - Immutable records, Digital signatures, Tamper-proof trail")
    
except Exception as e:
    logger.warning(f"Blockchain Audit not loaded: {e}")

# ============================================================================
# BROADCAST CONTROL (Phase 4)
# ============================================================================
try:
    from broadcast_control.routes import broadcast_control_api
    from broadcast_control.broadcast_engine import BroadcastEngine
    import broadcast_routes_module
    
    broadcast_eng = BroadcastEngine(db=db)
    broadcast_routes_module.broadcast_engine = broadcast_eng
    
    api_router.include_router(broadcast_control_api, prefix="")
    logger.info("✓ Broadcast Control loaded - Multi-camera, Graphics overlays, Sponsor management")
    
except Exception as e:
    logger.warning(f"Broadcast Control not loaded: {e}")

# ============================================================================
# PROFESSIONAL CV ANALYTICS (Elite System)
# ============================================================================
try:
    from pro_cv_analytics.routes import pro_cv_api
    from pro_cv_analytics.analytics_engine import ProfessionalCVEngine
    import pro_cv_analytics.routes as pro_cv_routes_module
    
    pro_cv_eng = ProfessionalCVEngine(db=db)
    pro_cv_routes_module.cv_engine = pro_cv_eng
    
    api_router.include_router(pro_cv_api, prefix="")
    logger.info("✓ Professional CV Analytics loaded - Elite strike/ground/defense analysis (Jabbr/DeepStrike grade)")
    
except Exception as e:
    logger.warning(f"Professional CV Analytics not loaded: {e}")

# ============================================================================
# SOCIAL MEDIA INTEGRATION (Phase 5)
# ============================================================================
try:
    from social_media.routes import social_media_api
    from social_media.social_engine import SocialMediaEngine
    import social_media.routes as social_routes_module
    
    social_eng = SocialMediaEngine(db=db)
    social_routes_module.social_engine = social_eng
    
    api_router.include_router(social_media_api, prefix="")
    logger.info("✓ Social Media Integration loaded - Auto-post to Twitter/Instagram")
    
except Exception as e:
    logger.warning(f"Social Media Integration not loaded: {e}")

# ============================================================================
# BRANDING & THEMES (Phase 7)
# ============================================================================
try:
    from branding_themes.routes import branding_api
    from branding_themes.theme_engine import ThemeEngine
    import branding_themes.routes as branding_routes_module
    
    theme_eng = ThemeEngine(db=db)
    branding_routes_module.theme_engine = theme_eng
    
    api_router.include_router(branding_api, prefix="")
    logger.info("✓ Branding & Themes loaded - Custom themes, logo management, CSS generation")
    
except Exception as e:
    logger.warning(f"Branding & Themes not loaded: {e}")

# ============================================================================
# REAL-TIME CV SYSTEM (Professional Computer Vision)
# ============================================================================
try:
    from realtime_cv.routes import router as realtime_cv_api
    from realtime_cv.data_routes import router as cv_data_api
    import realtime_cv.routes as cv_routes_module
    import realtime_cv.data_routes as cv_data_routes_module
    
    # Initialize CV engine
    cv_routes_module.init_cv_engine(db=db)
    
    # Initialize data collector
    cv_data_routes_module.init_data_collector(db=db)
    
    # Include both routers
    app.include_router(realtime_cv_api)
    app.include_router(cv_data_api)
    
    logger.info("✓ Real-Time CV System loaded - MediaPipe + YOLO for live video analysis")
    logger.info("✓ CV Data Collection loaded - Training dataset management (GitHub/Kaggle)")
    
except Exception as e:
    logger.warning(f"Real-Time CV System not loaded: {e}")

# ============================================================================
# STAT ENGINE (Production-Grade Statistics Aggregation)
# ============================================================================
try:
    from stat_engine.routes import router as stat_engine_api
    import stat_engine.routes as stat_routes_module
    
    # Initialize stat engine
    stat_routes_module.init_stat_engine(db=db)
    
    # Include router
    app.include_router(stat_engine_api)
    
    logger.info("✓ Stat Engine loaded - Round/Fight/Career statistics aggregation")
    logger.info("  - Event Reader (READ-ONLY from events table)")
    logger.info("  - Round Stats Aggregator (per-round metrics)")
    logger.info("  - Fight Stats Aggregator (per-fight totals)")
    logger.info("  - Career Stats Aggregator (lifetime metrics)")
    logger.info("  - Scheduler (manual/round-locked/post-fight/nightly triggers)")
    
except Exception as e:
    logger.warning(f"Stat Engine not loaded: {e}")

# ============================================================================
# PUBLIC STATS ROUTES (Public-facing statistics pages)
# ============================================================================
try:
    from public_stats_routes import router as public_stats_api
    import public_stats_routes as public_stats_module
    
    # Initialize public stats routes
    public_stats_module.init_public_stats_routes(database=db)
    
    # Include router
    app.include_router(public_stats_api)
    
    logger.info("✓ Public Stats Routes loaded - Public-facing event/fight/fighter pages")
    logger.info("  - GET /api/events (list all events with fight counts)")
    logger.info("  - GET /api/fights/:fight_id/stats (fight detail page data)")
    logger.info("  - GET /api/fighters/:fighter_id/stats (fighter profile data)")
    
except Exception as e:
    logger.warning(f"Public Stats Routes not loaded: {e}")

# ============================================================================
# TAPOLOGY SCRAPER (Web scraping for MMA data)
# ============================================================================
try:
    from tapology_scraper.routes import router as scraper_api
    import tapology_scraper.routes as scraper_module
    
    # Initialize scraper with database
    scraper_module.init_tapology_scraper(database=db)
    
    # Include router
    app.include_router(scraper_api)
    
    logger.info("✓ Tapology Scraper loaded - Web scraping for MMA data")
    logger.info("  - POST /api/scraper/events/recent (scrape recent events)")
    logger.info("  - POST /api/scraper/fighter/{id} (scrape fighter profile)")
    logger.info("  - POST /api/scraper/event/{id} (scrape event details)")
    logger.info("  - GET /api/scraper/status (scraping statistics)")
    logger.info("  - GET /api/scraper/fighters/search (search scraped fighters)")
    
except Exception as e:
    logger.warning(f"Tapology Scraper not loaded: {e}")

# ============================================================================
# STATS OVERLAY API (Low-latency broadcast overlays)
# ============================================================================
try:
    from stats_overlay.routes import router as overlay_api
    import stats_overlay.routes as overlay_module
    
    # Initialize stats overlay with database
    overlay_module.init_stats_overlay(database=db)
    
    # Include router
    app.include_router(overlay_api)
    
    logger.info("✓ Stats Overlay API loaded - Low-latency broadcast overlays")
    logger.info("  - GET /api/overlay/live/{fight_id} (live stats with 60s window)")
    logger.info("  - GET /api/overlay/comparison/{fight_id} (red vs blue deltas)")
    logger.info("  - WS /api/overlay/ws/live/{fight_id} (WebSocket real-time)")
    logger.info("  - Performance: Sub-200ms latency, 1-second cache")
    
except Exception as e:
    logger.warning(f"Stats Overlay API not loaded: {e}")

# ============================================================================
# VERIFICATION ENGINE (Multi-operator verification)
# ============================================================================
try:
    from verification_engine.routes import router as verification_api
    import verification_engine.routes as verification_module
    
    # Initialize verification engine with database
    verification_module.init_verification_engine(database=db)
    
    # Include router
    app.include_router(verification_api)
    
    logger.info("✓ Verification Engine loaded - Multi-operator data verification")
    logger.info("  - POST /api/verification/verify/round/{fight_id}/{round} (verify round)")
    logger.info("  - POST /api/verification/verify/fight/{fight_id} (verify all rounds)")
    logger.info("  - GET /api/verification/discrepancies (get flagged issues)")
    logger.info("  - Thresholds: Sig strikes >10%, Takedowns >1")
    
except Exception as e:
    logger.warning(f"Verification Engine not loaded: {e}")

# ============================================================================
# AI MERGE ENGINE (Colab/Kaggle AI event integration)
# ============================================================================
try:
    from ai_merge_engine.routes import router as ai_merge_api
    import ai_merge_engine.routes as ai_merge_module
    
    # Initialize AI merge engine with database
    ai_merge_module.init_ai_merge_engine(database=db)
    
    # Include router
    app.include_router(ai_merge_api)
    
    logger.info("✓ AI Merge Engine loaded - Colab/Kaggle AI event integration")
    logger.info("  - POST /api/ai-merge/submit-batch (receive AI events from Colab)")
    logger.info("  - GET /api/ai-merge/review-items (get conflicts for review)")
    logger.info("  - POST /api/ai-merge/review-items/{id}/approve (approve resolution)")
    logger.info("  - Merge rules: tolerance-based auto-approval, conflict detection")
    
except Exception as e:
    logger.warning(f"AI Merge Engine not loaded: {e}")

# ============================================================================
# POST-FIGHT REVIEW INTERFACE (Event editing and versioning)
# ============================================================================
try:
    from review_interface.routes import router as review_api
    import review_interface.routes as review_module
    
    # Initialize review interface with database
    review_module.init_review_interface(database=db)
    
    # Include router
    app.include_router(review_api)
    
    logger.info("✓ Post-Fight Review Interface loaded - Event editing and versioning")
    logger.info("  - GET /api/review/timeline/{fight_id} (get event timeline)")
    logger.info("  - PUT /api/review/events/{id} (edit event with versioning)")
    logger.info("  - DELETE /api/review/events/{id} (delete event)")
    logger.info("  - POST /api/review/events/merge (merge duplicate events)")
    logger.info("  - POST /api/review/fights/{id}/approve (approve and rerun stats)")
    logger.info("  - POST /api/review/videos/upload (upload fight video)")
    
except Exception as e:
    logger.warning(f"Post-Fight Review Interface not loaded: {e}")

# ============================================================================
# DATABASE MANAGEMENT (Production Models & Indexes)
# ============================================================================
try:
    from database.routes import router as database_api
    import database.routes as db_routes_module
    from database.init_db import initialize_database
    
    # Initialize database routes
    db_routes_module.init_database_routes(db=db)
    
    # Include router
    app.include_router(database_api)
    
    logger.info("✓ Database Management loaded - Production schemas and indexes")
    logger.info("  - Fighters table with biographical data")
    logger.info("  - Events table with proper relations")
    logger.info("  - Round/Fight/Career stats tables")
    logger.info("  - 30+ optimized indexes for query performance")
    
except Exception as e:
    logger.warning(f"Database Management not loaded: {e}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_databases():
    """Initialize Postgres and Redis on startup"""
    global postgres_available, redis_available
    
    # Initialize MongoDB with production schemas and indexes
    try:
        from database.init_db import initialize_database
        logger.info("🚀 Initializing MongoDB with production schemas...")
        
        init_results = await initialize_database(db, force_recreate_indexes=False)
        
        if init_results["status"] == "success":
            logger.info("✓ MongoDB initialized with production schemas")
            logger.info(f"  Collections: {len(init_results.get('collections_created', []))}")
            logger.info(f"  Total indexes: {sum(len(v) for v in init_results.get('indexes_created', {}).values())}")
            
            # Log collection counts
            counts = init_results.get('collection_counts', {})
            for collection, count in counts.items():
                logger.info(f"  - {collection}: {count} documents")
        else:
            logger.warning(f"MongoDB initialization had issues: {init_results.get('errors')}")
    
    except Exception as e:
        logger.warning(f"MongoDB initialization skipped: {e}")
    
    # Initialize Postgres
    try:
        await init_db()
        postgres_available = True
        logger.info("✓ Postgres initialized successfully")
    except Exception as e:
        logger.warning(f"Postgres initialization skipped: {e}")
        postgres_available = False
    
    # Initialize Redis
    try:
        redis_client = await init_redis()
        redis_available = redis_client is not None
        if redis_available:
            logger.info("✓ Redis initialized successfully")
    except Exception as e:
        logger.warning(f"Redis initialization skipped: {e}")
        redis_available = False

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    
    # Close Redis
    if redis_available:
        from redis_utils import close_redis
        await close_redis()