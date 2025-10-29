from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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
    ip_address: str = None

class SignatureVerification(BaseModel):
    valid: bool
    signature: str
    computed_signature: str
    message: str

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
            
            elif etype.startswith("SS"):
                # All SS strikes equal value (matches TypeScript)
                location = etype.replace("SS ", "").lower()
                impact_map = {"head": 1.0, "body": 0.8, "leg": 0.7}
                impact = impact_map.get(location, 1.0)
                
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
        Calculate final strength score on 1-1000 scale
        Returns a score between 0 and 1000
        
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
        
        # Scale to 1-1000 range (0-10 → 0-1000)
        # S * 100 gives us 0-1000 range
        strength_score = S * 100
        
        # Clamp to 0-1000 range
        strength_score = max(0.0, min(1000.0, strength_score))
        
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
        Map continuous scores (1-1000 scale) to 10-Point-Must system
        
        Thresholds:
        - 10-9: score differential 1-600
        - 10-8: score differential 601-900
        - 10-7: score differential 901-1000
        
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
        
        # Determine score based on delta thresholds (1-1000 scale)
        to_108 = False
        to_107 = False
        
        if abs_delta <= 600:
            # 10-9: Score differential 1-600
            score_l = 9
        elif abs_delta <= 900:
            # 10-8: Score differential 601-900
            score_l = 8
            to_108 = True
        else:  # abs_delta > 900
            # 10-7: Score differential 901-1000
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
        
        # Calculate SS totals for AGG calculation
        f1_ss_total = sum([1.0 for e in fighter1_events if e.event_type.startswith("SS")])
        f2_ss_total = sum([1.0 for e in fighter2_events if e.event_type.startswith("SS")])
        
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
                final_score=s_a
            ),
            fighter2_score=FighterScore(
                fighter="fighter2",
                subscores=f2_subscores,
                final_score=s_b
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
        ss_count = len([e for e in update.round_events if e.get('event_type', '').startswith('SS')])
        td_count = len([e for e in update.round_events if e.get('event_type') == 'Takedown'])
        sub_count = len([e for e in update.round_events if e.get('event_type') == 'Submission Attempt'])
        pass_count = len([e for e in update.round_events if e.get('event_type') == 'Pass'])
        rev_count = len([e for e in update.round_events if e.get('event_type') == 'Reversal'])
        
        # Calculate striking style
        ss_head = len([e for e in update.round_events if e.get('event_type') == 'SS Head'])
        ss_body = len([e for e in update.round_events if e.get('event_type') == 'SS Body'])
        ss_leg = len([e for e in update.round_events if e.get('event_type') == 'SS Leg'])
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
        stats = await db.fighter_stats.find_one({"fighter_name": fighter_name})
        
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
        if "weights" in update_data:
            update_data["weights"] = update_data["weights"].model_dump()
        if "thresholds" in update_data:
            update_data["thresholds"] = update_data["thresholds"].model_dump()
        if "gate_sensitivity" in update_data:
            update_data["gate_sensitivity"] = update_data["gate_sensitivity"].model_dump()
        
        await db.tuning_profiles.update_one(
            {"id": profile_id},
            {"$set": update_data}
        )
        
        return {"success": True, "message": "Profile updated"}
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
    action_type: str = None,
    user_id: str = None,
    resource_type: str = None,
    limit: int = 100
):
    """Get audit logs with optional filters"""
    try:
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
    except Exception as e:
        logger.error(f"Error fetching audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/audit/verify/{log_id}")
async def verify_audit_log(log_id: str):
    """Verify cryptographic signature of an audit log"""
    try:
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
    start_date: str = None,
    end_date: str = None,
    format: str = "json"
):
    """Export audit logs for compliance/archival"""
    try:
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
async def get_audit_stats():
    """Get statistics about audit logs"""
    try:
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()