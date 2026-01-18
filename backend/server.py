from fastapi import FastAPI, APIRouter, HTTPException, Form, WebSocket, WebSocketDisconnect
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
import json
from event_dedup import EventDedupEngine, verify_event_chain
from replay_engine import reconstruct_round_timeline
from fight_completion import save_completed_fight, calculate_fighter_stats, determine_winner

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
        # Striking - percentage values (0.14 = 14%)
        "KD": {"category": "striking", "Near-Finish": 1.00, "Hard": 0.70, "Flash": 0.40},
        "Rocked/Stunned": {"category": "striking", "value": 0.30},
        "Cross": {"category": "striking", "value": 0.14},
        "Hook": {"category": "striking", "value": 0.14},
        "Uppercut": {"category": "striking", "value": 0.14},
        "Elbow": {"category": "striking", "value": 0.14},
        "Kick": {"category": "striking", "value": 0.14},
        "Jab": {"category": "striking", "value": 0.10},
        "Knee": {"category": "striking", "value": 0.10},
        "Ground Strike": {"category": "striking", "value": 0.08},
        # Grappling - percentage values
        "Submission Attempt": {"category": "grappling", "Near-Finish": 1.00, "Deep": 0.60, "Light": 0.25, "Standard": 0.25},
        "Takedown Landed": {"category": "grappling", "value": 0.25},
        "Sweep/Reversal": {"category": "grappling", "value": 0.05},
        "Guard Passing": {"category": "grappling", "value": 0.05},
        "Back Control": {"category": "grappling", "value_per_sec": 0.012},
        "Mount Control": {"category": "grappling", "value_per_sec": 0.010},
        "Side Control": {"category": "grappling", "value_per_sec": 0.010},
        "Ground Back Control": {"category": "grappling", "value_per_sec": 0.012},
        "Ground Top Control": {"category": "grappling", "value_per_sec": 0.010},
        # Other - percentage values
        "Cage Control Time": {"category": "other", "value_per_sec": 0.006},
        "Takedown Stuffed": {"category": "other", "value": 0.04},
        "Takedown Defended": {"category": "other", "value": 0.04}
    },
    "round_thresholds": {
        "draw_max": 5.0,        # ≤5% = 10-10
        "standard_max": 80.0,   # 5-80% = 10-9
        "dominant_max": 95.0,   # 80-95% = 10-8
        # >95% = 10-7 (near impossible)
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

# =============================================================================
# WEBSOCKET CONNECTION MANAGER FOR REAL-TIME UNIFIED SCORING
# =============================================================================

class UnifiedScoringConnectionManager:
    """
    Manages WebSocket connections for real-time unified scoring updates.
    All connected operator laptops receive the same data from the server.
    """
    def __init__(self):
        # bout_id -> list of connected WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, bout_id: str):
        """Connect a client to a bout's real-time updates"""
        await websocket.accept()
        async with self.lock:
            if bout_id not in self.active_connections:
                self.active_connections[bout_id] = []
            self.active_connections[bout_id].append(websocket)
            logging.info(f"[WS] Client connected to bout {bout_id}. Total: {len(self.active_connections[bout_id])}")
    
    async def disconnect(self, websocket: WebSocket, bout_id: str):
        """Disconnect a client"""
        async with self.lock:
            if bout_id in self.active_connections:
                if websocket in self.active_connections[bout_id]:
                    self.active_connections[bout_id].remove(websocket)
                    logging.info(f"[WS] Client disconnected from bout {bout_id}. Remaining: {len(self.active_connections[bout_id])}")
                if not self.active_connections[bout_id]:
                    del self.active_connections[bout_id]
    
    async def broadcast_to_bout(self, bout_id: str, message: dict):
        """Broadcast a message to ALL clients watching a bout"""
        async with self.lock:
            if bout_id in self.active_connections:
                disconnected = []
                for connection in self.active_connections[bout_id]:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logging.warning(f"[WS] Failed to send to client: {e}")
                        disconnected.append(connection)
                
                # Clean up disconnected clients
                for conn in disconnected:
                    if conn in self.active_connections[bout_id]:
                        self.active_connections[bout_id].remove(conn)
    
    def get_connection_count(self, bout_id: str) -> int:
        """Get number of connected clients for a bout"""
        return len(self.active_connections.get(bout_id, []))

# Global WebSocket manager for unified scoring
ws_manager = UnifiedScoringConnectionManager()

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
# III. BOUTS MANAGEMENT API
# ============================================================================

class BoutCreate(BaseModel):
    """Model for creating a new bout"""
    bout_id: Optional[str] = None
    fighter1: str
    fighter2: str
    fighter1_photo: Optional[str] = ""
    fighter2_photo: Optional[str] = ""
    total_rounds: int = 3
    event_name: Optional[str] = "PFC 50"
    division: Optional[str] = ""

@api_router.get("/bouts")
async def list_bouts():
    """List all bouts in MongoDB"""
    try:
        bouts = await db.bouts.find({}, {"_id": 0}).to_list(100)
        return bouts
    except Exception as e:
        logging.error(f"Error listing bouts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/bouts/active")
async def list_active_bouts():
    """List only active/in-progress bouts"""
    try:
        bouts = await db.bouts.find(
            {"status": {"$in": ["in_progress", "pending", "active"]}},
            {"_id": 0}
        ).to_list(100)
        return bouts
    except Exception as e:
        logging.error(f"Error listing active bouts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/bouts")
async def create_bout(bout: BoutCreate):
    """Create a new bout for the broadcast system"""
    try:
        bout_id = bout.bout_id or f"bout-{str(uuid.uuid4())[:8]}"
        
        bout_doc = {
            "bout_id": bout_id,
            "boutId": bout_id,  # Also store as boutId for compatibility
            "fighter1": bout.fighter1,
            "fighter2": bout.fighter2,
            "fighter1Photo": bout.fighter1_photo,
            "fighter2Photo": bout.fighter2_photo,
            "totalRounds": bout.total_rounds,
            "currentRound": 1,
            "status": "in_progress",
            "eventName": bout.event_name,
            "division": bout.division,
            "roundScores": [],
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.bouts.insert_one(bout_doc)
        
        # Return without _id
        bout_doc.pop("_id", None)
        
        logging.info(f"Created bout: {bout_id} - {bout.fighter1} vs {bout.fighter2}")
        return bout_doc
    except Exception as e:
        logging.error(f"Error creating bout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/bouts/{bout_id}")
async def get_bout(bout_id: str):
    """Get a specific bout by ID"""
    try:
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0}
        )
        if not bout:
            raise HTTPException(status_code=404, detail=f"Bout {bout_id} not found")
        return bout
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting bout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.patch("/bouts/{bout_id}")
async def update_bout(bout_id: str, data: dict):
    """Update bout settings (totalRounds, fighter names, etc.)"""
    try:
        # Only allow certain fields to be updated
        allowed_fields = ["totalRounds", "fighter1", "fighter2", "currentRound", "status"]
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        result = await db.bouts.update_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Bout {bout_id} not found")
        
        logging.info(f"[BOUT] Updated {bout_id}: {update_data}")
        return {"success": True, "updated": update_data}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating bout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/bouts/{bout_id}/round-score")
async def update_bout_round_score(bout_id: str, round_num: int, red_score: int, blue_score: int):
    """Update round score for a bout"""
    try:
        bout = await db.bouts.find_one({"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]})
        if not bout:
            raise HTTPException(status_code=404, detail=f"Bout {bout_id} not found")
        
        round_scores = bout.get("roundScores", [])
        
        # Update or append round score
        round_data = {
            "round": round_num,
            "red_score": red_score,
            "blue_score": blue_score,
            "unified_red": red_score,
            "unified_blue": blue_score
        }
        
        # Find existing round or append
        found = False
        for i, r in enumerate(round_scores):
            if r.get("round") == round_num:
                round_scores[i] = round_data
                found = True
                break
        
        if not found:
            round_scores.append(round_data)
        
        # Calculate totals
        total_red = sum(r.get("red_score", 0) for r in round_scores)
        total_blue = sum(r.get("blue_score", 0) for r in round_scores)
        
        await db.bouts.update_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"$set": {
                "roundScores": round_scores,
                "fighter1_total": total_red,
                "fighter2_total": total_blue
            }}
        )
        
        return {"success": True, "round_scores": round_scores}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating round score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/bouts/{bout_id}/status")
async def update_bout_status(bout_id: str, status: str, winner: Optional[str] = None):
    """Update bout status (in_progress, completed, etc.)"""
    try:
        update_data = {"status": status}
        if winner:
            update_data["winner"] = winner
        
        result = await db.bouts.update_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Bout {bout_id} not found")
        
        return {"success": True, "status": status}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating bout status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# IV. MULTI-JUDGE REAL-TIME SYNC SYSTEM
# ============================================================================

class JudgeEventLog(BaseModel):
    """Event logged by a specific judge"""
    bout_id: str
    round_num: int
    judge_id: str
    judge_name: str
    fighter: str  # "fighter1" or "fighter2"
    event_type: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = {}

class JudgeRoundScore(BaseModel):
    """Round score from a specific judge"""
    bout_id: str
    round_num: int
    judge_id: str
    judge_name: str
    fighter1_score: int
    fighter2_score: int
    card: str  # "10-9", "10-8", etc.
    notes: Optional[str] = ""

class DeviceRegistration(BaseModel):
    """Register a device for multi-device sync"""
    bout_id: str
    device_id: str
    account_id: str  # Same account on all devices (e.g., "ericgann")
    device_name: str  # e.g., "Laptop 1", "Laptop 2"

class NextRoundRequest(BaseModel):
    """Signal that a device is ready for next round"""
    bout_id: str
    device_id: str
    account_id: str
    current_round: int

# ============================================================================
# MULTI-DEVICE SYNC (Same Account on Multiple Laptops)
# ============================================================================

@api_router.post("/sync/register-device")
async def register_device(reg: DeviceRegistration):
    """
    Register a device/laptop for syncing. All devices on same account combine events.
    """
    try:
        # Auto-create bout in MongoDB if it doesn't exist
        existing_bout = await db.bouts.find_one(
            {"$or": [{"bout_id": reg.bout_id}, {"boutId": reg.bout_id}]}
        )
        if not existing_bout:
            new_bout = {
                "bout_id": reg.bout_id,
                "boutId": reg.bout_id,
                "fighter1": "Fighter 1",
                "fighter2": "Fighter 2",
                "totalRounds": 3,
                "currentRound": 1,
                "status": "in_progress",
                "roundScores": [],
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "auto_created": True
            }
            await db.bouts.insert_one(new_bout)
            logging.info(f"[DEVICE] Auto-created bout in MongoDB: {reg.bout_id}")
        
        await db.registered_devices.update_one(
            {"bout_id": reg.bout_id, "device_id": reg.device_id},
            {"$set": {
                "bout_id": reg.bout_id,
                "device_id": reg.device_id,
                "account_id": reg.account_id,
                "device_name": reg.device_name,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "active": True,
                "ready_for_next_round": False,
                "current_round": 1
            }},
            upsert=True
        )
        
        # Get all registered devices for this bout
        devices = await db.registered_devices.find(
            {"bout_id": reg.bout_id, "active": True},
            {"_id": 0}
        ).to_list(100)
        
        logging.info(f"[DEVICE] Registered {reg.device_name} ({reg.device_id}) for bout {reg.bout_id}")
        
        return {
            "success": True,
            "device_id": reg.device_id,
            "total_devices": len(devices),
            "devices": [{"device_id": d["device_id"], "device_name": d["device_name"]} for d in devices]
        }
    except Exception as e:
        logging.error(f"Error registering device: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/sync/next-round")
async def signal_next_round(req: NextRoundRequest):
    """
    Signal that this device is ready to move to next round.
    When ALL devices click next round, the round score is computed and locked.
    """
    try:
        # Mark this device as ready
        await db.registered_devices.update_one(
            {"bout_id": req.bout_id, "device_id": req.device_id},
            {"$set": {
                "ready_for_next_round": True,
                "current_round": req.current_round,
                "ready_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Check if ALL devices are ready
        all_devices = await db.registered_devices.find(
            {"bout_id": req.bout_id, "active": True},
            {"_id": 0}
        ).to_list(100)
        
        ready_devices = [d for d in all_devices if d.get("ready_for_next_round") and d.get("current_round") == req.current_round]
        
        all_ready = len(ready_devices) == len(all_devices) and len(all_devices) > 0
        
        result = {
            "success": True,
            "device_id": req.device_id,
            "current_round": req.current_round,
            "devices_ready": len(ready_devices),
            "devices_total": len(all_devices),
            "all_ready": all_ready,
            "waiting_for": [d["device_name"] for d in all_devices if not d.get("ready_for_next_round") or d.get("current_round") != req.current_round]
        }
        
        if all_ready:
            # Compute and lock the round score
            score_result = await compute_unified_round_score(req.bout_id, req.current_round)
            
            # Reset ready status for all devices and move to next round
            next_round = req.current_round + 1
            await db.registered_devices.update_many(
                {"bout_id": req.bout_id, "active": True},
                {"$set": {"ready_for_next_round": False, "current_round": next_round}}
            )
            
            # Update bout's current round
            await db.bouts.update_one(
                {"$or": [{"bout_id": req.bout_id}, {"boutId": req.bout_id}]},
                {"$set": {"currentRound": next_round}}
            )
            
            result["round_computed"] = True
            result["score"] = score_result
            result["next_round"] = next_round
            
            logging.info(f"[SYNC] All {len(all_devices)} devices ready - Round {req.current_round} computed: {score_result.get('card')}")
        
        return result
    except Exception as e:
        logging.error(f"Error in next round: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/sync/round-status/{bout_id}/{round_num}")
async def get_round_status(bout_id: str, round_num: int):
    """
    Get real-time status of current round - combined events from all devices.
    """
    try:
        # Get all events for this round
        events = await db.synced_events.find(
            {"bout_id": bout_id, "round_num": round_num},
            {"_id": 0}
        ).to_list(10000)
        
        # Get registered devices
        devices = await db.registered_devices.find(
            {"bout_id": bout_id, "active": True},
            {"_id": 0}
        ).to_list(100)
        
        # Count events by fighter
        f1_events = [e for e in events if e.get("fighter") == "fighter1"]
        f2_events = [e for e in events if e.get("fighter") == "fighter2"]
        
        # Count event types
        f1_types = {}
        f2_types = {}
        for e in f1_events:
            t = e.get("event_type", "")
            f1_types[t] = f1_types.get(t, 0) + 1
        for e in f2_events:
            t = e.get("event_type", "")
            f2_types[t] = f2_types.get(t, 0) + 1
        
        # Get current computed score if any
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0, "roundScores": 1, "fighter1": 1, "fighter2": 1}
        )
        
        current_score = None
        if bout:
            for r in bout.get("roundScores", []):
                if r.get("round") == round_num:
                    current_score = r
                    break
        
        return {
            "bout_id": bout_id,
            "round_num": round_num,
            "fighter1": bout.get("fighter1", "Fighter 1") if bout else "Fighter 1",
            "fighter2": bout.get("fighter2", "Fighter 2") if bout else "Fighter 2",
            "total_events": len(events),
            "fighter1_events": len(f1_events),
            "fighter2_events": len(f2_events),
            "fighter1_types": f1_types,
            "fighter2_types": f2_types,
            "devices": [{"device_id": d["device_id"], "device_name": d["device_name"], "ready": d.get("ready_for_next_round", False)} for d in devices],
            "devices_ready": len([d for d in devices if d.get("ready_for_next_round")]),
            "devices_total": len(devices),
            "current_score": current_score
        }
    except Exception as e:
        logging.error(f"Error getting round status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/sync/end-fight")
async def end_fight_sync(bout_id: str):
    """
    End the fight and compute final totals from all combined rounds.
    """
    try:
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0}
        )
        
        if not bout:
            raise HTTPException(status_code=404, detail="Bout not found")
        
        round_scores = bout.get("roundScores", [])
        
        # Calculate final totals
        total_red = sum(r.get("red_score", 0) for r in round_scores)
        total_blue = sum(r.get("blue_score", 0) for r in round_scores)
        
        # Determine winner
        if total_red > total_blue:
            winner = "fighter1"
            winner_name = bout.get("fighter1", "Fighter 1")
        elif total_blue > total_red:
            winner = "fighter2"
            winner_name = bout.get("fighter2", "Fighter 2")
        else:
            winner = "draw"
            winner_name = "Draw"
        
        # Update bout status
        await db.bouts.update_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"$set": {
                "status": "completed",
                "fighter1_total": total_red,
                "fighter2_total": total_blue,
                "winner": winner,
                "winner_name": winner_name,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Deactivate devices
        await db.registered_devices.update_many(
            {"bout_id": bout_id},
            {"$set": {"active": False}}
        )
        
        logging.info(f"[FIGHT END] {bout_id}: {bout.get('fighter1')} {total_red} - {total_blue} {bout.get('fighter2')} | Winner: {winner_name}")
        
        return {
            "success": True,
            "bout_id": bout_id,
            "fighter1": bout.get("fighter1"),
            "fighter2": bout.get("fighter2"),
            "fighter1_total": total_red,
            "fighter2_total": total_blue,
            "winner": winner,
            "winner_name": winner_name,
            "rounds": round_scores
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error ending fight: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/sync/event")
async def sync_judge_event(event: JudgeEventLog):
    """
    Sync an event from any device. All events combine together as ONE unified log.
    Score auto-computes after each event - treats all devices as one scorer.
    Auto-creates bout in MongoDB if it doesn't exist (for Firebase integration).
    """
    try:
        # Auto-create bout in MongoDB if it doesn't exist
        existing_bout = await db.bouts.find_one(
            {"$or": [{"bout_id": event.bout_id}, {"boutId": event.bout_id}]}
        )
        if not existing_bout:
            # Create a placeholder bout - will be updated with real names later
            new_bout = {
                "bout_id": event.bout_id,
                "boutId": event.bout_id,
                "fighter1": "Fighter 1",
                "fighter2": "Fighter 2",
                "totalRounds": 3,
                "currentRound": event.round_num,
                "status": "in_progress",
                "roundScores": [],
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "auto_created": True
            }
            await db.bouts.insert_one(new_bout)
            logging.info(f"[SYNC] Auto-created bout in MongoDB: {event.bout_id}")
        
        event_doc = {
            "bout_id": event.bout_id,
            "round_num": event.round_num,
            "judge_id": event.judge_id,
            "judge_name": event.judge_name,
            "fighter": event.fighter,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "metadata": event.metadata,
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
            "synced": True
        }
        
        await db.synced_events.insert_one(event_doc)
        
        logging.info(f"[SYNC] Event: {event.event_type} for {event.fighter} (from {event.judge_name})")
        
        # Auto-compute the unified score from ALL combined events
        score_result = await compute_unified_round_score(event.bout_id, event.round_num)
        
        return {
            "success": True, 
            "synced_at": event_doc["server_timestamp"],
            "current_score": score_result.get("card", ""),
            "score_diff": score_result.get("score_diff", 0),
            "total_events": score_result.get("total_events", 0)
        }
    except Exception as e:
        logging.error(f"Error syncing event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/sync/compute-round")
async def compute_round_from_all_events(bout_id: str, round_num: int):
    """
    Compute round score from ALL events logged by ALL devices.
    Events from all 4 laptops combine into ONE unified score using the delta scoring system.
    """
    try:
        # Compute the unified score from all synced events
        result = await compute_unified_round_score(bout_id, round_num)
        return result
    except Exception as e:
        logging.error(f"Error computing round: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def compute_unified_round_score(bout_id: str, round_num: int):
    """
    Combine ALL events from ALL devices and compute ONE unified score
    using the existing delta-based scoring system.
    """
    try:
        # Get ALL events for this round from ALL devices
        all_events_raw = await db.synced_events.find({
            "bout_id": bout_id,
            "round_num": round_num
        }).sort("timestamp", 1).to_list(10000)
        
        if not all_events_raw:
            return {"bout_id": bout_id, "round_num": round_num, "status": "no_events"}
        
        # Track which devices contributed
        devices = set()
        for e in all_events_raw:
            devices.add(e.get("judge_id", "unknown"))
        
        # Convert to EventData format for the scoring engine
        events_for_scoring = []
        for e in all_events_raw:
            events_for_scoring.append(EventData(
                bout_id=bout_id,
                round_num=round_num,
                fighter=e.get("fighter", "fighter1"),
                event_type=e.get("event_type", ""),
                timestamp=e.get("timestamp", 0),
                metadata=e.get("metadata", {})
            ))
        
        # Use the existing scoring engine
        f1_total, f1_categories, f1_counts = calculate_new_score(events_for_scoring, "fighter1")
        f2_total, f2_categories, f2_counts = calculate_new_score(events_for_scoring, "fighter2")
        
        # Calculate score differential
        score_diff = f1_total - f2_total
        
        # GUARDRAILS - same as calculate_score_v2
        f1_has_near_finish = f1_categories.get("has_near_finish_striking") or f1_categories.get("has_near_finish_grappling")
        f2_has_near_finish = f2_categories.get("has_near_finish_striking") or f2_categories.get("has_near_finish_grappling")
        
        if f1_has_near_finish and not f2_has_near_finish:
            score_diff = max(f1_total - f2_total, 10.0)
        elif f2_has_near_finish and not f1_has_near_finish:
            score_diff = min(f1_total - f2_total, -10.0)
        else:
            striking_margin = f1_categories['striking'] - f2_categories['striking']
            if abs(striking_margin) >= 20.0:
                if striking_margin > 0 and not f2_categories.get("has_near_finish_grappling"):
                    score_diff = max(f1_total - f2_total, 10.0)
                elif striking_margin < 0 and not f1_categories.get("has_near_finish_grappling"):
                    score_diff = min(f1_total - f2_total, -10.0)
        
        # KD and strike differential for 10-8 guardrails
        f1_kd_count = f1_counts.get("KD", 0)
        f2_kd_count = f2_counts.get("KD", 0)
        kd_differential = abs(f1_kd_count - f2_kd_count)
        
        f1_total_strikes = sum([f1_counts.get(t, 0) for t in ["Jab", "Cross", "Hook", "Uppercut", "Elbow", "Knee", "Head Kick", "Body Kick", "Low Kick"]])
        f2_total_strikes = sum([f2_counts.get(t, 0) for t in ["Jab", "Cross", "Hook", "Uppercut", "Elbow", "Knee", "Head Kick", "Body Kick", "Low Kick"]])
        strike_differential = abs(f1_total_strikes - f2_total_strikes)
        
        allow_extreme_score = (kd_differential >= 2) or (strike_differential >= 100)
        
        # Determine card using the same thresholds as calculate_score_v2
        if abs(score_diff) <= 3.0:
            card = "10-10"
            winner = "DRAW"
        elif abs(score_diff) < 140.0:
            winner = "fighter1" if score_diff > 0 else "fighter2"
            card = "10-9" if score_diff > 0 else "9-10"
        elif abs(score_diff) < 200.0:
            winner = "fighter1" if score_diff > 0 else "fighter2"
            if allow_extreme_score:
                card = "10-8" if score_diff > 0 else "8-10"
            else:
                card = "10-9" if score_diff > 0 else "9-10"
        else:
            winner = "fighter1" if score_diff > 0 else "fighter2"
            if allow_extreme_score and abs(score_diff) >= 250.0:
                card = "10-7" if score_diff > 0 else "7-10"
            elif allow_extreme_score:
                card = "10-8" if score_diff > 0 else "8-10"
            else:
                card = "10-9" if score_diff > 0 else "9-10"
        
        # Parse card to get scores
        if "-" in card:
            parts = card.split("-")
            red_score = int(parts[0])
            blue_score = int(parts[1])
        else:
            red_score, blue_score = 10, 9
        
        # Update the bout with computed score
        bout = await db.bouts.find_one({"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]})
        if bout:
            round_scores = bout.get("roundScores", [])
            
            round_data = {
                "round": round_num,
                "red_score": red_score,
                "blue_score": blue_score,
                "unified_red": red_score,
                "unified_blue": blue_score,
                "computed_from_events": True,
                "total_events": len(all_events_raw),
                "devices_contributed": list(devices),
                "num_devices": len(devices),
                "score_diff": round(score_diff, 2),
                "f1_total": round(f1_total, 2),
                "f2_total": round(f2_total, 2),
                "f1_counts": f1_counts,
                "f2_counts": f2_counts
            }
            
            # Update or append
            found = False
            for i, r in enumerate(round_scores):
                if r.get("round") == round_num:
                    round_scores[i] = round_data
                    found = True
                    break
            if not found:
                round_scores.append(round_data)
            
            round_scores.sort(key=lambda x: x.get("round", 0))
            
            # Calculate totals
            total_red = sum(r.get("red_score", 0) for r in round_scores)
            total_blue = sum(r.get("blue_score", 0) for r in round_scores)
            
            await db.bouts.update_one(
                {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
                {"$set": {
                    "roundScores": round_scores,
                    "fighter1_total": total_red,
                    "fighter2_total": total_blue,
                    "active_devices": len(devices),
                    "last_computed": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        logging.info(f"[UNIFIED] Bout {bout_id} Round {round_num}: {card} (diff: {score_diff:.2f}) from {len(all_events_raw)} events ({len(devices)} devices)")
        
        return {
            "bout_id": bout_id,
            "round_num": round_num,
            "card": card,
            "red_score": red_score,
            "blue_score": blue_score,
            "winner": winner,
            "score_diff": round(score_diff, 2),
            "total_events": len(all_events_raw),
            "devices": list(devices),
            "f1_total": round(f1_total, 2),
            "f2_total": round(f2_total, 2),
            "f1_counts": f1_counts,
            "f2_counts": f2_counts,
            "kd_differential": kd_differential,
            "strike_differential": strike_differential
        }
    except Exception as e:
        logging.error(f"Error computing unified score: {str(e)}")
        return {"error": str(e)}

@api_router.get("/sync/status/{bout_id}")
async def get_sync_status(bout_id: str):
    """
    Get real-time sync status - ALL events combined as ONE unified scorer.
    """
    try:
        # Get bout info
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0}
        )
        if not bout:
            raise HTTPException(status_code=404, detail=f"Bout {bout_id} not found")
        
        # Get ALL synced events for this bout (combined from all devices)
        all_events = await db.synced_events.find({"bout_id": bout_id}, {"_id": 0}).to_list(10000)
        
        # Count combined events by round and fighter
        events_by_round = {}
        total_f1_events = 0
        total_f2_events = 0
        device_count = len(set(e.get("judge_id", "") for e in all_events))
        
        for event in all_events:
            round_num = event.get("round_num", 1)
            fighter = event.get("fighter", "fighter1")
            event_type = event.get("event_type", "")
            
            if round_num not in events_by_round:
                events_by_round[round_num] = {
                    "round": round_num,
                    "fighter1_events": 0,
                    "fighter2_events": 0,
                    "event_types": {"fighter1": {}, "fighter2": {}}
                }
            
            if fighter == "fighter1":
                events_by_round[round_num]["fighter1_events"] += 1
                total_f1_events += 1
            else:
                events_by_round[round_num]["fighter2_events"] += 1
                total_f2_events += 1
            
            # Track event types
            types_dict = events_by_round[round_num]["event_types"][fighter]
            types_dict[event_type] = types_dict.get(event_type, 0) + 1
        
        return {
            "bout_id": bout_id,
            "fighter1": bout.get("fighter1", "Fighter 1"),
            "fighter2": bout.get("fighter2", "Fighter 2"),
            "current_round": bout.get("currentRound", 1),
            "total_rounds": bout.get("totalRounds", 3),
            "status": bout.get("status", "pending"),
            "total_events": len(all_events),
            "total_f1_events": total_f1_events,
            "total_f2_events": total_f2_events,
            "connected_devices": device_count,
            "events_by_round": list(events_by_round.values()),
            "unified_scores": bout.get("roundScores", []),
            "unified_total_red": bout.get("fighter1_total", 0),
            "unified_total_blue": bout.get("fighter2_total", 0),
            "last_computed": bout.get("last_computed", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/sync/events/{bout_id}/{round_num}")
async def get_synced_events(bout_id: str, round_num: int, judge_id: Optional[str] = None):
    """
    Get all synced events for a round, optionally filtered by judge.
    """
    try:
        query = {"bout_id": bout_id, "round_num": round_num}
        if judge_id:
            query["judge_id"] = judge_id
        
        events = await db.synced_events.find(query, {"_id": 0}).sort("timestamp", 1).to_list(1000)
        
        # Group by judge for display
        by_judge = {}
        for event in events:
            jid = event["judge_id"]
            if jid not in by_judge:
                by_judge[jid] = {
                    "judge_id": jid,
                    "judge_name": event["judge_name"],
                    "events": []
                }
            by_judge[jid]["events"].append(event)
        
        return {
            "bout_id": bout_id,
            "round_num": round_num,
            "total_events": len(events),
            "judges": list(by_judge.values())
        }
    except Exception as e:
        logging.error(f"Error getting synced events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/sync/heartbeat")
async def judge_heartbeat(judge_id: str, judge_name: str, bout_id: str):
    """
    Heartbeat from a judge's device to track active connections.
    """
    try:
        await db.judge_heartbeats.update_one(
            {"judge_id": judge_id, "bout_id": bout_id},
            {"$set": {
                "judge_id": judge_id,
                "judge_name": judge_name,
                "bout_id": bout_id,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "active": True
            }},
            upsert=True
        )
        
        # Get all active judges for this bout (seen in last 30 seconds)
        thirty_sec_ago = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        active_judges = await db.judge_heartbeats.find({
            "bout_id": bout_id,
            "last_seen": {"$gte": thirty_sec_ago}
        }, {"_id": 0}).to_list(100)
        
        return {
            "success": True,
            "active_judges": len(active_judges),
            "judges": [{"judge_id": j["judge_id"], "judge_name": j["judge_name"]} for j in active_judges]
        }
    except Exception as e:
        logging.error(f"Error processing heartbeat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Need timedelta import for sync features
from datetime import timedelta

# Import unified scoring system
from unified_scoring import compute_round_from_events, compute_fight_totals, get_event_value

# ============================================================================
# VI. UNIFIED SCORING API (SERVER-AUTHORITATIVE)
# ============================================================================
# ALL scoring computations happen HERE on the server.
# Operators NEVER compute scores locally - they only display server results.
# This ensures all 4 laptops see the SAME combined score.

class UnifiedEventCreate(BaseModel):
    """Event creation for unified scoring"""
    bout_id: str
    round_number: int
    corner: str  # RED or BLUE
    aspect: str  # STRIKING or GRAPPLING
    event_type: str
    device_role: str  # RED_STRIKING, RED_GRAPPLING, BLUE_STRIKING, BLUE_GRAPPLING
    metadata: Optional[Dict[str, Any]] = {}

class RoundComputeRequest(BaseModel):
    """Request to compute a round score"""
    bout_id: str
    round_number: int

class FightFinalizeRequest(BaseModel):
    """Request to finalize a fight"""
    bout_id: str

@api_router.get("/events")
async def get_all_events(bout_id: str, round_number: Optional[int] = None):
    """
    Get ALL events for a bout (and optionally a specific round).
    CRITICAL: This returns ALL events from ALL devices - NO filtering by device/user.
    """
    try:
        query = {"bout_id": bout_id}
        if round_number is not None:
            query["round_number"] = round_number
        
        # Also check the synced_events collection with round_num field
        events = await db.unified_events.find(query, {"_id": 0}).sort("created_at", 1).to_list(10000)
        
        # Also get from synced_events (legacy/bridge)
        legacy_query = {"bout_id": bout_id}
        if round_number is not None:
            legacy_query["round_num"] = round_number
        legacy_events = await db.synced_events.find(legacy_query, {"_id": 0}).sort("server_timestamp", 1).to_list(10000)
        
        # Convert legacy events to unified format
        for evt in legacy_events:
            # Map fighter to corner
            corner = "RED" if evt.get("fighter") == "fighter1" else "BLUE"
            events.append({
                "bout_id": evt.get("bout_id"),
                "round_number": evt.get("round_num"),
                "corner": corner,
                "aspect": "STRIKING",  # Default, could be improved
                "event_type": evt.get("event_type"),
                "device_role": evt.get("judge_name", "UNKNOWN"),
                "metadata": evt.get("metadata", {}),
                "created_at": evt.get("server_timestamp"),
                "created_by": evt.get("judge_id"),
                "fighter": evt.get("fighter")  # Keep for backwards compat
            })
        
        # Sort by created_at
        events.sort(key=lambda x: x.get("created_at", ""))
        
        logging.info(f"[UNIFIED] GET /events bout={bout_id} round={round_number}: {len(events)} events (NO DEVICE FILTER)")
        
        return {
            "bout_id": bout_id,
            "round_number": round_number,
            "total_events": len(events),
            "events": events
        }
    except Exception as e:
        logging.error(f"Error getting events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# OPERATOR DEVICE MANAGEMENT - For Central Assignment
# =============================================================================

class OperatorRegister(BaseModel):
    bout_id: str
    device_id: str
    device_name: str

class OperatorAssign(BaseModel):
    bout_id: str
    device_id: str
    role: str

@api_router.post("/operators/register")
async def register_operator(data: OperatorRegister):
    """Register an operator device for a bout. Supervisor will assign role."""
    try:
        operator_doc = {
            "bout_id": data.bout_id,
            "device_id": data.device_id,
            "device_name": data.device_name,
            "assigned_role": None,
            "status": "waiting",
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert - update if exists, insert if not
        await db.operators.update_one(
            {"bout_id": data.bout_id, "device_id": data.device_id},
            {"$set": operator_doc},
            upsert=True
        )
        
        logging.info(f"[OPERATORS] Registered: {data.device_name} ({data.device_id}) for bout {data.bout_id}")
        
        return {"success": True, "device_id": data.device_id, "status": "waiting"}
    except Exception as e:
        logging.error(f"Error registering operator: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/operators/status")
async def get_operator_status(bout_id: str, device_id: str):
    """Check if operator has been assigned a role."""
    try:
        operator = await db.operators.find_one(
            {"bout_id": bout_id, "device_id": device_id},
            {"_id": 0}
        )
        
        if not operator:
            return {"status": "not_registered", "assigned_role": None}
        
        return {
            "status": operator.get("status", "waiting"),
            "assigned_role": operator.get("assigned_role"),
            "device_name": operator.get("device_name")
        }
    except Exception as e:
        logging.error(f"Error getting operator status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/operators/heartbeat")
async def operator_heartbeat(data: dict):
    """Update operator heartbeat to show they're still connected."""
    try:
        bout_id = data.get("bout_id")
        device_id = data.get("device_id")
        
        await db.operators.update_one(
            {"bout_id": bout_id, "device_id": device_id},
            {"$set": {"last_heartbeat": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"success": True}
    except Exception as e:
        return {"success": False}

# =============================================================================
# SUPERVISOR CONTROL ENDPOINTS
# =============================================================================

@api_router.post("/events/create")
async def create_event(data: dict):
    """Create a new event (e.g., PFC 50)"""
    try:
        event_doc = {
            "event_id": data.get("event_id"),
            "event_name": data.get("event_name"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        }
        await db.events.update_one(
            {"event_id": event_doc["event_id"]},
            {"$set": event_doc},
            upsert=True
        )
        logging.info(f"[EVENT] Created: {event_doc['event_name']}")
        return {"success": True, "event_id": event_doc["event_id"]}
    except Exception as e:
        logging.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/supervisor/fights")
async def get_supervisor_fights(event_id: str):
    """Get all fights for an event (for supervisor control panel)"""
    try:
        fights = await db.bouts.find(
            {"event_id": event_id},
            {"_id": 0}
        ).sort("created_at", 1).to_list(100)
        
        # Also get fights without event_id that match pattern
        if not fights:
            fights = await db.bouts.find(
                {"bout_id": {"$regex": f"^{event_id}"}},
                {"_id": 0}
            ).sort("createdAt", 1).to_list(100)
        
        return {"event_id": event_id, "fights": fights}
    except Exception as e:
        logging.error(f"Error getting fights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/supervisor/activate-fight")
async def activate_fight(data: dict):
    """Activate a fight for scoring (sets others to pending)"""
    try:
        event_id = data.get("event_id")
        bout_id = data.get("bout_id")
        
        # Set all fights in event to pending
        await db.bouts.update_many(
            {"event_id": event_id},
            {"$set": {"status": "pending"}}
        )
        
        # Set the selected fight to active
        await db.bouts.update_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"$set": {"status": "active", "currentRound": 1}}
        )
        
        logging.info(f"[SUPERVISOR] Activated fight: {bout_id}")
        return {"success": True, "active_bout_id": bout_id}
    except Exception as e:
        logging.error(f"Error activating fight: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/bouts/{bout_id}")
async def delete_bout(bout_id: str):
    """Delete a bout"""
    try:
        await db.bouts.delete_one({"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]})
        await db.unified_events.delete_many({"bout_id": bout_id})
        await db.round_results.delete_many({"bout_id": bout_id})
        await db.operators.delete_many({"bout_id": bout_id})
        logging.info(f"[BOUT] Deleted: {bout_id}")
        return {"success": True}
    except Exception as e:
        logging.error(f"Error deleting bout: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/operators/list")
async def list_operators(bout_id: str):
    """List all registered operators for a bout (for supervisor)."""
    try:
        operators = await db.operators.find(
            {"bout_id": bout_id},
            {"_id": 0}
        ).sort("registered_at", 1).to_list(100)
        
        # Check which operators are still active (heartbeat within last 30 seconds)
        cutoff = datetime.now(timezone.utc).timestamp() - 30
        for op in operators:
            heartbeat = op.get("last_heartbeat", "")
            if heartbeat:
                try:
                    heartbeat_time = datetime.fromisoformat(heartbeat.replace("Z", "+00:00")).timestamp()
                    op["is_active"] = heartbeat_time > cutoff
                except:
                    op["is_active"] = False
            else:
                op["is_active"] = False
        
        return {"bout_id": bout_id, "operators": operators}
    except Exception as e:
        logging.error(f"Error listing operators: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/operators/assign")
async def assign_operator_role(data: OperatorAssign):
    """Supervisor assigns a role to an operator device."""
    try:
        result = await db.operators.update_one(
            {"bout_id": data.bout_id, "device_id": data.device_id},
            {"$set": {
                "assigned_role": data.role,
                "status": "assigned",
                "assigned_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.modified_count > 0:
            logging.info(f"[OPERATORS] Assigned {data.role} to device {data.device_id}")
            return {"success": True, "role": data.role}
        else:
            raise HTTPException(status_code=404, detail="Operator not found")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error assigning operator: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/operators/unassign")
async def unassign_operator_role(data: dict):
    """Remove role assignment from an operator."""
    try:
        bout_id = data.get("bout_id")
        device_id = data.get("device_id")
        
        await db.operators.update_one(
            {"bout_id": bout_id, "device_id": device_id},
            {"$set": {"assigned_role": None, "status": "waiting"}}
        )
        
        return {"success": True}
    except Exception as e:
        logging.error(f"Error unassigning operator: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/operators/remove")
async def remove_operator(bout_id: str, device_id: str):
    """Remove an operator from the bout."""
    try:
        await db.operators.delete_one({"bout_id": bout_id, "device_id": device_id})
        return {"success": True}
    except Exception as e:
        logging.error(f"Error removing operator: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/bouts/{bout_id}/advance-round")
async def advance_round(bout_id: str, data: dict = None):
    """
    Advance to next round after supervisor ends current round.
    Updates bout's currentRound and notifies all operators.
    """
    try:
        # Get current bout
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]}
        )
        
        if not bout:
            raise HTTPException(status_code=404, detail="Bout not found")
        
        current = bout.get("currentRound", 1)
        total = bout.get("totalRounds", 5)
        next_round = current + 1
        
        if next_round > total:
            return {
                "success": False,
                "message": "Already at final round",
                "current_round": current,
                "is_final": True
            }
        
        # Update bout's current round
        await db.bouts.update_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"$set": {"currentRound": next_round}}
        )
        
        # Update all operators to new round
        await db.operators.update_many(
            {"bout_id": bout_id},
            {"$set": {"current_round": next_round, "round_locked": False}}
        )
        
        logging.info(f"[BOUT] Advanced {bout_id} to round {next_round}")
        
        return {
            "success": True,
            "previous_round": current,
            "current_round": next_round,
            "total_rounds": total,
            "is_final": next_round >= total
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error advancing round: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/bouts/{bout_id}/current-round")
async def get_current_round(bout_id: str):
    """Get current round for a bout - used by operators to sync."""
    try:
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0, "currentRound": 1, "totalRounds": 1, "status": 1, "fighter1": 1, "fighter2": 1}
        )
        
        if not bout:
            return {"current_round": 1, "total_rounds": 5, "status": "unknown"}
        
        return {
            "current_round": bout.get("currentRound", 1),
            "total_rounds": bout.get("totalRounds", 5),
            "status": bout.get("status", "in_progress"),
            "fighter1": bout.get("fighter1", "Red Corner"),
            "fighter2": bout.get("fighter2", "Blue Corner")
        }
    except Exception as e:
        logging.error(f"Error getting current round: {e}")
        return {"current_round": 1, "total_rounds": 5, "status": "error"}

@api_router.post("/events")
async def create_event(event: UnifiedEventCreate):
    """
    Create a new event for unified scoring.
    Event is stored with device_role for auditing, but NEVER filtered by it.
    Broadcasts to all connected WebSocket clients for real-time sync.
    """
    try:
        # Auto-create bout if it doesn't exist
        existing_bout = await db.bouts.find_one(
            {"$or": [{"bout_id": event.bout_id}, {"boutId": event.bout_id}]}
        )
        if not existing_bout:
            new_bout = {
                "bout_id": event.bout_id,
                "boutId": event.bout_id,
                "fighter1": "Red Corner",
                "fighter2": "Blue Corner",
                "totalRounds": 5,
                "currentRound": event.round_number,
                "status": "in_progress",
                "roundScores": [],
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "auto_created": True
            }
            await db.bouts.insert_one(new_bout)
            logging.info(f"[UNIFIED] Auto-created bout: {event.bout_id}")
        
        # Calculate event value
        value = get_event_value(event.event_type, event.metadata)
        
        event_doc = {
            "bout_id": event.bout_id,
            "round_number": event.round_number,
            "corner": event.corner.upper(),
            "aspect": event.aspect.upper(),
            "event_type": event.event_type,
            "value": value,
            "device_role": event.device_role,
            "metadata": event.metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": event.device_role  # For audit only
        }
        
        await db.unified_events.insert_one(event_doc)
        event_doc.pop("_id", None)
        
        logging.info(f"[UNIFIED] Event created: {event.event_type} for {event.corner} (from {event.device_role})")
        
        # BROADCAST to all connected WebSocket clients
        await broadcast_event_added(event.bout_id, event_doc)
        
        return {
            "success": True,
            "event": event_doc,
            "connected_clients": ws_manager.get_connection_count(event.bout_id)
        }
    except Exception as e:
        logging.error(f"Error creating event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/rounds/compute")
async def compute_round(request: RoundComputeRequest):
    """
    SERVER-AUTHORITATIVE round computation.
    Loads ALL events for bout_id + round_number from ALL devices,
    computes the unified score, and persists the RoundResult.
    
    This is IDEMPOTENT - calling multiple times produces the same result.
    """
    try:
        bout_id = request.bout_id
        round_number = request.round_number
        
        # Get ALL events for this round from ALL sources (NO DEVICE FILTER)
        unified_events = await db.unified_events.find(
            {"bout_id": bout_id, "round_number": round_number},
            {"_id": 0}
        ).to_list(10000)
        
        # Also get from synced_events (bridge/legacy)
        synced_events = await db.synced_events.find(
            {"bout_id": bout_id, "round_num": round_number},
            {"_id": 0}
        ).to_list(10000)
        
        # Convert synced_events to unified format
        all_events = list(unified_events)
        for evt in synced_events:
            corner = "RED" if evt.get("fighter") == "fighter1" else "BLUE"
            all_events.append({
                "corner": corner,
                "event_type": evt.get("event_type"),
                "metadata": evt.get("metadata", {}),
                "fighter": evt.get("fighter")
            })
        
        logging.info(f"[UNIFIED] Computing round {round_number} for bout {bout_id}: {len(all_events)} events from ALL devices")
        
        # Compute the round score using unified scoring logic
        result = compute_round_from_events(all_events)
        
        # Get bout info for fighter names
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0}
        )
        
        # Create RoundResult document
        round_result = {
            "bout_id": bout_id,
            "round_number": round_number,
            "red_points": result["red_points"],
            "blue_points": result["blue_points"],
            "delta": result["delta"],
            "red_total": result["red_total"],
            "blue_total": result["blue_total"],
            "red_breakdown": result["red_breakdown"],
            "blue_breakdown": result["blue_breakdown"],
            "total_events": result["total_events"],
            "winner": result["winner"],
            "red_kd": result.get("red_kd", 0),
            "blue_kd": result.get("blue_kd", 0),
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "fighter1_name": bout.get("fighter1", "Red Corner") if bout else "Red Corner",
            "fighter2_name": bout.get("fighter2", "Blue Corner") if bout else "Blue Corner"
        }
        
        # UPSERT - idempotent storage
        await db.round_results.update_one(
            {"bout_id": bout_id, "round_number": round_number},
            {"$set": round_result},
            upsert=True
        )
        
        # Also update bout's roundScores for backwards compatibility
        if bout:
            round_scores = bout.get("roundScores", [])
            round_data = {
                "round": round_number,
                "red_score": result["red_points"],
                "blue_score": result["blue_points"],
                "unified_red": result["red_points"],
                "unified_blue": result["blue_points"],
                "delta": result["delta"],
                "total_events": result["total_events"],
                "computed_at": round_result["computed_at"]
            }
            
            # Update or append
            found = False
            for i, r in enumerate(round_scores):
                if r.get("round") == round_number:
                    round_scores[i] = round_data
                    found = True
                    break
            if not found:
                round_scores.append(round_data)
            
            round_scores.sort(key=lambda x: x.get("round", 0))
            
            # Calculate totals
            total_red = sum(r.get("red_score", 0) for r in round_scores)
            total_blue = sum(r.get("blue_score", 0) for r in round_scores)
            
            await db.bouts.update_one(
                {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
                {"$set": {
                    "roundScores": round_scores,
                    "fighter1_total": total_red,
                    "fighter2_total": total_blue,
                    "last_computed": round_result["computed_at"]
                }}
            )
        
        logging.info(f"[UNIFIED] Round {round_number} computed: {result['red_points']}-{result['blue_points']} (delta: {result['delta']}) from {result['total_events']} events")
        
        # BROADCAST to all connected WebSocket clients
        await broadcast_round_computed(bout_id, round_result)
        
        return round_result
    except Exception as e:
        logging.error(f"Error computing round: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/rounds")
async def get_all_rounds(bout_id: str):
    """
    Get all computed RoundResults for a bout.
    Returns the server-authoritative scores for all rounds.
    """
    try:
        round_results = await db.round_results.find(
            {"bout_id": bout_id},
            {"_id": 0}
        ).sort("round_number", 1).to_list(100)
        
        # Also get from bout's roundScores if round_results is empty (backwards compat)
        if not round_results:
            bout = await db.bouts.find_one(
                {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
                {"_id": 0}
            )
            if bout and bout.get("roundScores"):
                for r in bout["roundScores"]:
                    round_results.append({
                        "bout_id": bout_id,
                        "round_number": r.get("round"),
                        "red_points": r.get("red_score", r.get("unified_red", 0)),
                        "blue_points": r.get("blue_score", r.get("unified_blue", 0)),
                        "delta": r.get("delta", 0),
                        "total_events": r.get("total_events", 0)
                    })
        
        # Calculate running totals
        running_red = 0
        running_blue = 0
        for r in round_results:
            running_red += r.get("red_points", 0)
            running_blue += r.get("blue_points", 0)
        
        # Get bout info
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0}
        )
        
        return {
            "bout_id": bout_id,
            "fighter1": bout.get("fighter1", "Red Corner") if bout else "Red Corner",
            "fighter2": bout.get("fighter2", "Blue Corner") if bout else "Blue Corner",
            "rounds": round_results,
            "total_rounds": len(round_results),
            "running_red": running_red,
            "running_blue": running_blue
        }
    except Exception as e:
        logging.error(f"Error getting rounds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/fights/finalize")
async def finalize_fight(request: FightFinalizeRequest):
    """
    Finalize a fight - compute final totals and determine winner.
    This is the authoritative final result.
    """
    try:
        bout_id = request.bout_id
        
        # Get all round results
        round_results = await db.round_results.find(
            {"bout_id": bout_id},
            {"_id": 0}
        ).sort("round_number", 1).to_list(100)
        
        # If no round_results, try to get from bout
        if not round_results:
            bout = await db.bouts.find_one(
                {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
                {"_id": 0}
            )
            if bout and bout.get("roundScores"):
                for r in bout["roundScores"]:
                    round_results.append({
                        "round_number": r.get("round"),
                        "red_points": r.get("red_score", r.get("unified_red", 0)),
                        "blue_points": r.get("blue_score", r.get("unified_blue", 0)),
                        "delta": r.get("delta", 0)
                    })
        
        # Compute final totals
        fight_totals = compute_fight_totals(round_results)
        
        # Get bout info for fighter names
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0}
        )
        
        fighter1_name = bout.get("fighter1", "Red Corner") if bout else "Red Corner"
        fighter2_name = bout.get("fighter2", "Blue Corner") if bout else "Blue Corner"
        
        if fight_totals["winner"] == "RED":
            winner_name = fighter1_name
        elif fight_totals["winner"] == "BLUE":
            winner_name = fighter2_name
        else:
            winner_name = "DRAW"
        
        # Create FightResult document
        fight_result = {
            "bout_id": bout_id,
            "final_red": fight_totals["final_red"],
            "final_blue": fight_totals["final_blue"],
            "winner": fight_totals["winner"],
            "winner_name": winner_name,
            "fighter1_name": fighter1_name,
            "fighter2_name": fighter2_name,
            "total_rounds": fight_totals["total_rounds"],
            "rounds": [
                {
                    "round": r.get("round_number"),
                    "red": r.get("red_points"),
                    "blue": r.get("blue_points"),
                    "delta": r.get("delta", 0)
                }
                for r in round_results
            ],
            "finalized_at": datetime.now(timezone.utc).isoformat()
        }
        
        # UPSERT - idempotent storage
        await db.fight_results.update_one(
            {"bout_id": bout_id},
            {"$set": fight_result},
            upsert=True
        )
        
        # Update bout status
        await db.bouts.update_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"$set": {
                "status": "completed",
                "fighter1_total": fight_totals["final_red"],
                "fighter2_total": fight_totals["final_blue"],
                "winner": fight_totals["winner"],
                "winner_name": winner_name,
                "finalized_at": fight_result["finalized_at"]
            }}
        )
        
        logging.info(f"[UNIFIED] Fight finalized: {bout_id} - {fighter1_name} {fight_totals['final_red']} vs {fight_totals['final_blue']} {fighter2_name} | Winner: {winner_name}")
        
        # BROADCAST to all connected WebSocket clients
        await broadcast_fight_finalized(bout_id, fight_result)
        
        return fight_result
    except Exception as e:
        logging.error(f"Error finalizing fight: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/fights/{bout_id}/result")
async def get_fight_result(bout_id: str):
    """
    Get the final fight result (if finalized).
    """
    try:
        result = await db.fight_results.find_one(
            {"bout_id": bout_id},
            {"_id": 0}
        )
        
        if not result:
            # Try to compute from rounds
            rounds_response = await get_all_rounds(bout_id)
            return {
                "bout_id": bout_id,
                "status": "in_progress",
                "running_red": rounds_response["running_red"],
                "running_blue": rounds_response["running_blue"],
                "rounds": rounds_response["rounds"],
                "finalized": False
            }
        
        result["finalized"] = True
        return result
    except Exception as e:
        logging.error(f"Error getting fight result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# WEBSOCKET ENDPOINT FOR REAL-TIME UNIFIED SCORING
# =============================================================================

@app.websocket("/api/ws/unified/{bout_id}")
async def unified_scoring_websocket(websocket: WebSocket, bout_id: str):
    """
    WebSocket endpoint for real-time unified scoring updates.
    
    All connected operator laptops receive the SAME data from the server.
    This ensures all 4 operators see identical event counts and scores.
    
    Message types sent to clients:
    - event_added: New event was logged (from any device)
    - round_computed: Round score was computed
    - fight_finalized: Fight was finalized
    - state_sync: Full state synchronization
    - connection_count: Number of connected operators
    """
    await ws_manager.connect(websocket, bout_id)
    
    try:
        # Send initial state on connect
        initial_state = await get_unified_state(bout_id)
        await websocket.send_json({
            "type": "state_sync",
            "data": initial_state,
            "connection_count": ws_manager.get_connection_count(bout_id)
        })
        
        # Broadcast new connection to all clients
        await ws_manager.broadcast_to_bout(bout_id, {
            "type": "connection_count",
            "count": ws_manager.get_connection_count(bout_id)
        })
        
        while True:
            # Wait for messages from client (heartbeat, round change, etc.)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
                
                elif data.get("type") == "request_sync":
                    # Client requesting full state sync
                    state = await get_unified_state(bout_id, data.get("round_number"))
                    await websocket.send_json({
                        "type": "state_sync",
                        "data": state
                    })
                
                elif data.get("type") == "set_round":
                    # Client changed round - send state for new round
                    round_num = data.get("round_number", 1)
                    state = await get_unified_state(bout_id, round_num)
                    await websocket.send_json({
                        "type": "state_sync",
                        "data": state
                    })
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logging.info(f"[WS] Client disconnected from bout {bout_id}")
    except Exception as e:
        logging.error(f"[WS] Error in websocket: {e}")
    finally:
        await ws_manager.disconnect(websocket, bout_id)
        # Broadcast updated connection count
        await ws_manager.broadcast_to_bout(bout_id, {
            "type": "connection_count",
            "count": ws_manager.get_connection_count(bout_id)
        })

async def get_unified_state(bout_id: str, round_number: int = None) -> dict:
    """
    Get the complete unified state for a bout (and optionally a specific round).
    This is the authoritative state that all clients should display.
    """
    try:
        # Get bout info
        bout = await db.bouts.find_one(
            {"$or": [{"bout_id": bout_id}, {"boutId": bout_id}]},
            {"_id": 0}
        )
        
        if not bout:
            return {"error": "Bout not found", "bout_id": bout_id}
        
        current_round = round_number or bout.get("currentRound", 1)
        
        # Get ALL events for current round (NO DEVICE FILTER)
        events_query = {"bout_id": bout_id, "round_number": current_round}
        unified_events = await db.unified_events.find(events_query, {"_id": 0}).sort("created_at", 1).to_list(10000)
        
        # Also get from synced_events (legacy)
        legacy_events = await db.synced_events.find(
            {"bout_id": bout_id, "round_num": current_round},
            {"_id": 0}
        ).sort("server_timestamp", 1).to_list(10000)
        
        # Merge and aggregate events
        all_events = list(unified_events)
        for evt in legacy_events:
            corner = "RED" if evt.get("fighter") == "fighter1" else "BLUE"
            all_events.append({
                "bout_id": evt.get("bout_id"),
                "round_number": evt.get("round_num"),
                "corner": corner,
                "event_type": evt.get("event_type"),
                "device_role": evt.get("judge_name", "UNKNOWN"),
                "metadata": evt.get("metadata", {}),
                "created_at": evt.get("server_timestamp"),
                "fighter": evt.get("fighter")
            })
        
        # Aggregate by corner
        red_events = {}
        blue_events = {}
        for evt in all_events:
            corner = evt.get("corner", "").upper()
            if not corner:
                corner = "RED" if evt.get("fighter") == "fighter1" else "BLUE"
            event_type = evt.get("event_type", "")
            
            if corner == "RED":
                red_events[event_type] = red_events.get(event_type, 0) + 1
            else:
                blue_events[event_type] = blue_events.get(event_type, 0) + 1
        
        # Get all computed round results
        round_results = await db.round_results.find(
            {"bout_id": bout_id},
            {"_id": 0}
        ).sort("round_number", 1).to_list(100)
        
        # Calculate running totals
        running_red = sum(r.get("red_points", 0) for r in round_results)
        running_blue = sum(r.get("blue_points", 0) for r in round_results)
        
        return {
            "bout_id": bout_id,
            "fighter1": bout.get("fighter1", "Red Corner"),
            "fighter2": bout.get("fighter2", "Blue Corner"),
            "current_round": current_round,
            "total_rounds": bout.get("totalRounds", 5),
            "status": bout.get("status", "in_progress"),
            "events": {
                "round_number": current_round,
                "red": red_events,
                "blue": blue_events,
                "red_total": sum(red_events.values()),
                "blue_total": sum(blue_events.values()),
                "all_events": len(all_events)
            },
            "round_results": round_results,
            "running_totals": {
                "red": running_red,
                "blue": running_blue
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logging.error(f"Error getting unified state: {e}")
        return {"error": str(e), "bout_id": bout_id}

async def broadcast_event_added(bout_id: str, event: dict):
    """Broadcast a new event to all connected clients"""
    await ws_manager.broadcast_to_bout(bout_id, {
        "type": "event_added",
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def broadcast_round_computed(bout_id: str, result: dict):
    """Broadcast round computation result to all connected clients"""
    await ws_manager.broadcast_to_bout(bout_id, {
        "type": "round_computed",
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def broadcast_fight_finalized(bout_id: str, result: dict):
    """Broadcast fight finalization to all connected clients"""
    await ws_manager.broadcast_to_bout(bout_id, {
        "type": "fight_finalized",
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

# ============================================================================
# VII. BROADCAST API LAYER
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
            "fighter1_name": bout.get('fighter1', 'Fighter 1'),
            "fighter2_name": bout.get('fighter2', 'Fighter 2'),
            "fighter1_photo": bout.get('fighter1Photo', ''),
            "fighter2_photo": bout.get('fighter2Photo', ''),
            "round_id": round_id,
            "current_round": round_id,
            "total_rounds": bout.get('totalRounds', 3),
            "status": bout.get('status', 'in_progress'),
            "round_status": bout.get('status', 'IN_PROGRESS'),
            "fighter1_total": summary.get('total_score', {}).get('red', 0),
            "fighter2_total": summary.get('total_score', {}).get('blue', 0),
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
            "rounds": bout.get('roundScores', []),
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
# FIGHT COMPLETION & ARCHIVAL
# ============================================================================

@api_router.post("/fight/complete/{bout_id}")
async def complete_fight(bout_id: str):
    """
    Complete and archive a fight with all stats saved to database.
    This endpoint should be called when the fight is officially over.
    """
    try:
        # Save the completed fight
        completed_fight = await save_completed_fight(db, bout_id)
        
        # Remove _id for JSON response
        completed_fight.pop('_id', None)
        
        logging.info(f"Fight {bout_id} completed and archived successfully")
        
        return {
            "success": True,
            "message": f"Fight {completed_fight['fighter1']['name']} vs {completed_fight['fighter2']['name']} completed and archived",
            "bout_id": bout_id,
            "winner": completed_fight['fight_details']['winner'],
            "total_events": completed_fight['metadata']['total_events'],
            "fighter1_stats": completed_fight['fighter1']['stats']['summary'],
            "fighter2_stats": completed_fight['fighter2']['stats']['summary']
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error completing fight {bout_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete fight: {str(e)}")

@api_router.get("/fight/completed/{bout_id}")
async def get_completed_fight(bout_id: str):
    """
    Get a completed fight's archived data
    """
    try:
        fight = await db.completed_fights.find_one({"bout_id": bout_id}, {"_id": 0})
        if not fight:
            raise HTTPException(status_code=404, detail=f"Completed fight {bout_id} not found")
        return fight
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching completed fight {bout_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/fights/completed")
async def list_completed_fights(limit: int = 50, skip: int = 0):
    """
    List all completed fights (paginated)
    """
    try:
        fights = await db.completed_fights.find(
            {}, 
            {
                "_id": 0,
                "bout_id": 1,
                "fighter1.name": 1,
                "fighter2.name": 1,
                "event.event_name": 1,
                "fight_details": 1,
                "completed_at": 1
            }
        ).sort("completed_at", -1).skip(skip).limit(limit).to_list(limit)
        
        total = await db.completed_fights.count_documents({})
        
        return {
            "fights": fights,
            "total": total,
            "limit": limit,
            "skip": skip
        }
    except Exception as e:
        logging.error(f"Error listing completed fights: {str(e)}")
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
# ORGANIZATION STATS (Multi-org filtering)
# ============================================================================
try:
    from organization_stats.routes import router as org_stats_api
    import organization_stats.routes as org_stats_module
    
    # Initialize organization stats with database
    org_stats_module.init_organization_stats(database=db)
    
    # Include router
    app.include_router(org_stats_api)
    
    logger.info("✓ Organization Stats loaded - Multi-org stat filtering")
    logger.info("  - GET /api/organizations/list (list all organizations)")
    logger.info("  - GET /api/organizations/{id}/summary (org summary)")
    logger.info("  - GET /api/organizations/{id}/events (org events)")
    logger.info("  - GET /api/organizations/{id}/fighters (org fighters)")
    logger.info("  - All stats APIs support ?organization_id= query parameter")
    
except Exception as e:
    logger.warning(f"Organization Stats not loaded: {e}")

# ============================================================================
# COMBAT SPORTS (Sport types and organizations)
# ============================================================================
try:
    from combat_sports.routes import router as combat_sports_api
    import combat_sports.routes as combat_sports_module
    
    # Initialize combat sports with database
    combat_sports_module.init_combat_sports(database=db)
    
    # Include router
    app.include_router(combat_sports_api)
    
    logger.info("✓ Combat Sports loaded - Multi-sport support")
    logger.info("  - GET /api/sports/types (list sport types: MMA, Boxing, BKFC, etc.)")
    logger.info("  - GET /api/sports/types/{type}/organizations (orgs per sport)")
    logger.info("  - GET /api/sports/stats/summary (sport-filtered stats)")
    logger.info("  - Sports: MMA, Boxing, Dirty Boxing, BKFC, Karate Combat, Other")
    logger.info("  - All stats APIs support ?sport_type= and ?organization_id= parameters")
    
except Exception as e:
    logger.warning(f"Combat Sports not loaded: {e}")

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
    
    # Create indexes for unified scoring collections
    try:
        logger.info("🔧 Creating unified scoring indexes...")
        
        # unified_events: { bout_id: 1, round_number: 1, created_at: 1 }
        await db.unified_events.create_index([
            ("bout_id", 1),
            ("round_number", 1),
            ("created_at", 1)
        ], name="unified_events_bout_round_created")
        
        # round_results: { bout_id: 1, round_number: 1 } UNIQUE
        await db.round_results.create_index([
            ("bout_id", 1),
            ("round_number", 1)
        ], unique=True, name="round_results_bout_round_unique")
        
        # fight_results: { bout_id: 1 } UNIQUE
        await db.fight_results.create_index([
            ("bout_id", 1)
        ], unique=True, name="fight_results_bout_unique")
        
        # synced_events: { bout_id: 1, round_num: 1, server_timestamp: 1 }
        await db.synced_events.create_index([
            ("bout_id", 1),
            ("round_num", 1),
            ("server_timestamp", 1)
        ], name="synced_events_bout_round_ts")
        
        logger.info("✓ Unified scoring indexes created")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")
    
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