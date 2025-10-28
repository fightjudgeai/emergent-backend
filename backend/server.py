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

class RoundScore(BaseModel):
    bout_id: str
    round_num: int
    fighter1_score: FighterScore
    fighter2_score: FighterScore
    score_gap: float
    card: str  # e.g., "10-9", "10-8", "10-7", "10-10"
    winner: str  # "fighter1", "fighter2", or "DRAW"
    reasons: RoundReasons

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
        Calculate final strength score on 7-10 scale
        Matches TypeScript implementation exactly
        
        Original weights from provided code:
        0.28*KD + 0.24*ISS + 0.12*GCQ + 0.10*TDQ + 0.10*SUBQ +
        0.06*OC + 0.05*AGG + 0.03*RP + 0.02*TSR
        """
        weights = {
            "KD": 0.28,
            "ISS": 0.24,
            "GCQ": 0.12,
            "TDQ": 0.10,
            "SUBQ": 0.10,
            "OC": 0.06,
            "AGG": 0.05,
            "RP": 0.03,
            "TSR": 0.02
        }
        
        # Calculate weighted score (matches TypeScript compositeScore)
        S = (
            weights["KD"] * subscores.KD +
            weights["ISS"] * subscores.ISS +
            weights["GCQ"] * subscores.GCQ +
            weights["TDQ"] * subscores.TDQ +
            weights["SUBQ"] * subscores.SUBQ +
            weights["OC"] * subscores.OC +
            weights["AGG"] * subscores.AGG +
            weights["RP"] * subscores.RP +
            weights["TSR"] * subscores.TSR
        )
        
        # Scale to 0-100 range (matches TypeScript S*10)
        composite = S * 10
        
        # Map to 7-10 scale for display
        # 0-100 composite → 7.0-10.0 final
        # Linear mapping: final = 7 + (composite * 0.03)
        final_score = 7.0 + (composite * 0.03)
        
        # Clamp to 7-10 range
        final_score = max(7.0, min(10.0, final_score))
        
        return round(final_score, 2)
    
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
                              fouls_a: int = 0, fouls_b: int = 0) -> tuple[str, str, RoundReasons]:
        """
        Map continuous scores to 10-Point-Must system
        Returns: (card, winner, reasons)
        
        Thresholds adjusted for 7-10 scale:
        - Exact match (Δ = 0): 10-10
        - Δ ≤ 1.5: 10-9
        - Δ > 1.5 and ≤ 2.5: 10-8
        - Δ > 2.5: 10-7
        """
        delta = s_a - s_b
        abs_delta = abs(delta)
        
        # Check for 10-10 draw (exact match only)
        if abs_delta == 0:
            return ("10-10", "DRAW", RoundReasons(
                delta=delta,
                gates_winner=gates_a,
                gates_loser=gates_b,
                to_108=False,
                to_107=False,
                draw=True
            ))
        
        # Determine winner and loser
        if delta > 0:
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
        
        # Determine score based on delta thresholds (7-10 scale)
        to_108 = False
        to_107 = False
        
        if abs_delta <= 1.5:
            # 10-9: Close round
            score_l = 9
        elif abs_delta <= 2.5:
            # 10-8: Clear dominance
            score_l = 8
            to_108 = True
        else:  # abs_delta > 2.5
            # 10-7: Overwhelming dominance
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
        
        # Map to 10-Point-Must
        card, winner, reasons = engine.map_to_ten_point_must(s_a, s_b, gates_a, gates_b)
        
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
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating score: {str(e)}")
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