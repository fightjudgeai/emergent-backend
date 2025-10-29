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
                
                card = "10-9 (Damage TB)" if winner == "fighter1" else "9-10 (Damage TB)"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False
                ))
            
            # Priority 2: CONTROL (grappling/positional)
            control_a = (subscores_a.GCQ * 2.0) + subscores_a.TDQ
            control_b = (subscores_b.GCQ * 2.0) + subscores_b.TDQ
            
            if control_a != control_b:
                winner = "fighter1" if control_a > control_b else "fighter2"
                gates_w = gates_a if control_a > control_b else gates_b
                gates_l = gates_b if control_a > control_b else gates_a
                delta = 1.0 if control_a > control_b else -1.0
                
                card = "10-9 (Control TB)" if winner == "fighter1" else "9-10 (Control TB)"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False
                ))
            
            # Priority 3: AGGRESSION & ACTIVITY
            aggression_a = (subscores_a.AGG * 1.5) + subscores_a.TSR + subscores_a.OC
            aggression_b = (subscores_b.AGG * 1.5) + subscores_b.TSR + subscores_b.OC
            
            if aggression_a != aggression_b:
                winner = "fighter1" if aggression_a > aggression_b else "fighter2"
                gates_w = gates_a if aggression_a > aggression_b else gates_b
                gates_l = gates_b if aggression_a > aggression_b else gates_a
                delta = 1.0 if aggression_a > aggression_b else -1.0
                
                card = "10-9 (Aggression TB)" if winner == "fighter1" else "9-10 (Aggression TB)"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False
                ))
            
            # Priority 4: TECHNICAL SUPERIORITY (reversals/passes)
            technical_a = subscores_a.RP
            technical_b = subscores_b.RP
            
            if technical_a != technical_b:
                winner = "fighter1" if technical_a > technical_b else "fighter2"
                gates_w = gates_a if technical_a > technical_b else gates_b
                gates_l = gates_b if technical_a > technical_b else gates_a
                delta = 1.0 if technical_a > technical_b else -1.0
                
                card = "10-9 (Technical TB)" if winner == "fighter1" else "9-10 (Technical TB)"
                return (card, winner, RoundReasons(
                    delta=delta,
                    gates_winner=gates_w,
                    gates_loser=gates_l,
                    to_108=False,
                    to_107=False,
                    draw=False
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
                    
                    card = f"10-9 ({metric} TB)" if winner == "fighter1" else f"9-10 ({metric} TB)"
                    return (card, winner, RoundReasons(
                        delta=delta,
                        gates_winner=gates_w,
                        gates_loser=gates_l,
                        to_108=False,
                        to_107=False,
                        draw=False
                    ))
            
            # ONLY if EVERY single metric is EXACTLY equal - TRUE 10-10 DRAW
            return ("10-10", "DRAW", RoundReasons(
                delta=0,
                gates_winner=gates_a,
                gates_loser=gates_b,
                to_108=False,
                to_107=False,
                draw=True
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