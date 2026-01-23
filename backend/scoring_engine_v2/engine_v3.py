"""
FightJudge.AI Scoring Engine v3.0 - Impact-First Implementation
Implements all regularization rules and impact lock logic.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .config_v3 import (
    SCORING_CONFIG,
    REGULARIZATION_RULES,
    IMPACT_LOCK_RULES,
    ROUND_SCORING,
    LEGACY_EVENT_MAP,
    get_all_event_configs,
    get_event_points,
    get_control_config,
    is_ss_event,
    is_protected_event,
    get_impact_lock,
)

logger = logging.getLogger(__name__)


@dataclass
class ScoredEvent:
    """A single scored event with all metadata"""
    event_id: str
    fighter: str  # "RED" or "BLUE"
    event_key: str
    base_points: int
    technique_multiplier: float = 1.0
    ss_multiplier: float = 1.0
    control_multiplier: float = 1.0
    td_stuffed_multiplier: float = 1.0
    final_points: float = 0.0
    timestamp: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_final(self):
        """Calculate final points with all multipliers"""
        self.final_points = (
            self.base_points 
            * self.technique_multiplier 
            * self.ss_multiplier 
            * self.control_multiplier
            * self.td_stuffed_multiplier
        )
        return self.final_points


@dataclass
class FighterRoundState:
    """Tracks per-fighter, per-round scoring state"""
    fighter: str
    
    # Event counts for regularization
    technique_counts: Dict[str, int] = field(default_factory=dict)
    ss_total_count: int = 0
    takedown_stuffed_count: int = 0
    
    # Control tracking
    control_continuous_seconds: Dict[str, float] = field(default_factory=dict)
    control_last_timestamp: Dict[str, float] = field(default_factory=dict)
    
    # Point totals
    raw_points: float = 0.0
    strike_points: float = 0.0  # All strikes (stand-up + ground)
    control_points: float = 0.0
    gnp_hard_points: float = 0.0
    
    # Impact flags
    impact_flags: Dict[str, bool] = field(default_factory=lambda: {
        "rocked": False,
        "kd_flash": False,
        "kd_hard": False,
        "kd_nf": False,
        "sub_nf": False,
    })
    has_submission: bool = False
    
    # Scored events list
    events: List[ScoredEvent] = field(default_factory=list)
    
    def get_technique_count(self, event_key: str) -> int:
        return self.technique_counts.get(event_key, 0)
    
    def increment_technique(self, event_key: str) -> int:
        self.technique_counts[event_key] = self.technique_counts.get(event_key, 0) + 1
        return self.technique_counts[event_key]


@dataclass
class RoundResult:
    """Complete round scoring result"""
    round_number: int
    
    # Per-fighter totals
    red_raw_points: float = 0.0
    blue_raw_points: float = 0.0
    red_final_points: float = 0.0
    blue_final_points: float = 0.0
    
    # Delta and share
    delta: float = 0.0
    red_share_percent: float = 50.0
    blue_share_percent: float = 50.0
    
    # Impact flags
    red_impact_flags: Dict[str, bool] = field(default_factory=dict)
    blue_impact_flags: Dict[str, bool] = field(default_factory=dict)
    
    # Winner determination
    winner: str = "DRAW"  # "RED", "BLUE", "DRAW"
    winner_reason: str = "points"  # "points", "impact_lock_kd_flash", etc.
    red_round_score: int = 10
    blue_round_score: int = 10
    
    # Control discount applied
    red_control_discount_applied: bool = False
    blue_control_discount_applied: bool = False
    
    # Debug info
    red_state: Optional[FighterRoundState] = None
    blue_state: Optional[FighterRoundState] = None


class ScoringEngineV3:
    """
    Impact-First Scoring Engine v3.0
    
    Features:
    - Config-driven weights
    - 5 regularization rules (anti-spam)
    - Impact lock system
    - Full auditability
    """
    
    def __init__(self):
        self.config = SCORING_CONFIG
        self.rules = REGULARIZATION_RULES
        self.impact_locks = IMPACT_LOCK_RULES
    
    def normalize_event_key(self, event: Dict[str, Any]) -> str:
        """Convert legacy event type to normalized event key"""
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {}) or {}
        
        # Check for SS prefix in event type
        if event_type.startswith("SS "):
            base_type = event_type[3:]  # Remove "SS " prefix
            ss_key = f"ss_{base_type.lower()}"
            if ss_key in LEGACY_EVENT_MAP.values():
                return ss_key
        
        # Check legacy map
        if event_type in LEGACY_EVENT_MAP:
            base_key = LEGACY_EVENT_MAP[event_type]
            
            # Handle KD tiers
            if event_type == "KD":
                tier = metadata.get("tier", "Flash")
                if tier in ["Near-Finish", "NF"]:
                    return "kd_nf"
                elif tier == "Hard":
                    return "kd_hard"
                else:
                    return "kd_flash"
            
            # Handle Ground Strike quality
            if event_type == "Ground Strike":
                quality = metadata.get("quality", "LIGHT")
                if quality == "SOLID" or quality == "HARD":
                    return "gnp_hard"
                else:
                    return "gnp_light"
            
            # Handle Submission depth
            if event_type == "Submission Attempt":
                tier = metadata.get("tier", metadata.get("depth", "Light"))
                if tier in ["Near-Finish", "NF", "NEAR_FINISH"]:
                    return "sub_nf"
                elif tier in ["Deep", "DEEP"]:
                    return "sub_deep"
                else:
                    return "sub_light"
            
            return base_key
        
        # Try lowercase match
        lower_type = event_type.lower().replace(" ", "_").replace("-", "_")
        all_events = get_all_event_configs()
        if lower_type in all_events:
            return lower_type
        
        # Control events
        if "control" in lower_type.lower():
            if "back" in lower_type.lower():
                return "back_control"
            elif "cage" in lower_type.lower():
                return "cage_control"
            else:
                return "top_control"
        
        logger.warning(f"Unknown event type: {event_type}")
        return event_type.lower().replace(" ", "_")
    
    def get_technique_multiplier(self, event_key: str, count: int) -> float:
        """RULE 1: Get technique diminishing returns multiplier"""
        if not self.rules["technique_diminishing_returns"]["enabled"]:
            return 1.0
        
        if event_key not in self.rules["technique_diminishing_returns"]["applies_to"]:
            return 1.0
        
        for threshold in self.rules["technique_diminishing_returns"]["thresholds"]:
            if threshold["min"] <= count <= threshold["max"]:
                return threshold["multiplier"]
        
        return 1.0
    
    def get_ss_abuse_multiplier(self, ss_count: int) -> float:
        """RULE 2: Get SS abuse guardrail multiplier"""
        if not self.rules["ss_abuse_guardrail"]["enabled"]:
            return 1.0
        
        for threshold in self.rules["ss_abuse_guardrail"]["thresholds"]:
            if threshold["min"] <= ss_count <= threshold["max"]:
                return threshold["multiplier"]
        
        return 1.0
    
    def get_control_multiplier(self, control_type: str, continuous_seconds: float) -> float:
        """RULE 3: Get control time diminishing returns multiplier"""
        if not self.rules["control_diminishing_returns"]["enabled"]:
            return 1.0
        
        threshold = self.rules["control_diminishing_returns"]["continuous_threshold_seconds"]
        if continuous_seconds > threshold:
            return self.rules["control_diminishing_returns"]["multiplier_after_threshold"]
        
        return 1.0
    
    def get_td_stuffed_multiplier(self, count: int) -> float:
        """RULE 5: Get takedown stuffed cap multiplier"""
        if not self.rules["takedown_stuffed_cap"]["enabled"]:
            return 1.0
        
        if count > self.rules["takedown_stuffed_cap"]["full_value_count"]:
            return self.rules["takedown_stuffed_cap"]["multiplier_after_cap"]
        
        return 1.0
    
    def apply_control_without_work_discount(self, state: FighterRoundState) -> float:
        """RULE 4: Apply control without work discount"""
        if not self.rules["control_without_work"]["enabled"]:
            return 1.0
        
        threshold = self.rules["control_without_work"]["control_points_threshold"]
        if state.control_points < threshold:
            return 1.0
        
        # Check work requirements
        req = self.rules["control_without_work"]["required_work"]
        
        has_strikes = state.strike_points >= req["min_strike_points"]
        has_submission = state.has_submission if req["any_submission"] else False
        has_gnp_hard = state.gnp_hard_points >= req["min_gnp_hard_points"]
        
        if has_strikes or has_submission or has_gnp_hard:
            return 1.0
        
        # No work requirement met, apply discount
        return self.rules["control_without_work"]["discount_multiplier"]
    
    def score_event(
        self, 
        event: Dict[str, Any], 
        state: FighterRoundState,
        timestamp: Optional[float] = None
    ) -> ScoredEvent:
        """Score a single event with all regularization rules applied"""
        
        event_key = self.normalize_event_key(event)
        base_points = get_event_points(event_key)
        
        # Create scored event
        scored = ScoredEvent(
            event_id=event.get("event_id", str(id(event))),
            fighter=state.fighter,
            event_key=event_key,
            base_points=base_points,
            timestamp=timestamp,
            metadata=event.get("metadata", {}) or {}
        )
        
        # Handle control events specially
        if event_key in ["top_control", "back_control", "cage_control"]:
            return self.score_control_event(event, state, scored)
        
        # RULE 1: Technique diminishing returns
        count = state.increment_technique(event_key)
        scored.technique_multiplier = self.get_technique_multiplier(event_key, count)
        
        # RULE 2: SS abuse guardrail (stacks with Rule 1)
        if is_ss_event(event_key):
            state.ss_total_count += 1
            scored.ss_multiplier = self.get_ss_abuse_multiplier(state.ss_total_count)
        
        # RULE 5: Takedown stuffed cap
        if event_key == "takedown_stuffed":
            state.takedown_stuffed_count += 1
            scored.td_stuffed_multiplier = self.get_td_stuffed_multiplier(state.takedown_stuffed_count)
        
        # Calculate final points
        scored.calculate_final()
        
        # Update state totals
        state.raw_points += scored.final_points
        
        # Track strike points (for Rule 4)
        if event_key in self.config.get("striking", {}) or event_key in ["gnp_light", "gnp_hard"]:
            state.strike_points += scored.final_points
        
        # Track GnP hard points (for Rule 4)
        if event_key == "gnp_hard":
            state.gnp_hard_points += scored.final_points
        
        # Track submissions (for Rule 4)
        if event_key in ["sub_light", "sub_deep", "sub_nf"]:
            state.has_submission = True
        
        # Track impact flags
        if event_key in state.impact_flags:
            state.impact_flags[event_key] = True
        
        state.events.append(scored)
        return scored
    
    def score_control_event(
        self,
        event: Dict[str, Any],
        state: FighterRoundState,
        scored: ScoredEvent
    ) -> ScoredEvent:
        """Score a control event with time-based regularization"""
        
        event_key = scored.event_key
        metadata = event.get("metadata", {}) or {}
        
        # Get duration from metadata (in seconds)
        duration = metadata.get("duration", 10)  # Default to 1 bucket (10s)
        
        # Get control config
        ctrl_config = get_control_config(event_key)
        bucket_seconds = ctrl_config.get("bucket_seconds", 10)
        points_per_bucket = ctrl_config.get("points_per_bucket", 1)
        
        # Calculate number of buckets
        num_buckets = max(1, int(duration / bucket_seconds))
        
        # Update continuous control tracking
        gap_threshold = self.rules["control_diminishing_returns"]["bucket_gap_reset_seconds"]
        last_time = state.control_last_timestamp.get(event_key, 0)
        current_time = scored.timestamp or 0
        
        if current_time - last_time > gap_threshold:
            # Reset continuous streak
            state.control_continuous_seconds[event_key] = 0
        
        # RULE 3: Apply diminishing returns for continuous control
        continuous = state.control_continuous_seconds.get(event_key, 0)
        scored.control_multiplier = self.get_control_multiplier(event_key, continuous)
        
        # Update continuous tracking
        state.control_continuous_seconds[event_key] = continuous + duration
        state.control_last_timestamp[event_key] = current_time
        
        # Calculate points
        scored.base_points = points_per_bucket * num_buckets
        scored.calculate_final()
        
        # Update state
        state.raw_points += scored.final_points
        state.control_points += scored.final_points
        
        state.events.append(scored)
        return scored
    
    def determine_winner(
        self,
        red_state: FighterRoundState,
        blue_state: FighterRoundState
    ) -> Tuple[str, str, float]:
        """
        Determine round winner with Impact Lock logic.
        
        Returns: (winner, reason, delta)
        """
        red_points = red_state.raw_points
        blue_points = blue_state.raw_points
        delta = abs(red_points - blue_points)
        
        # Determine points leader
        if red_points > blue_points:
            points_leader = "RED"
        elif blue_points > red_points:
            points_leader = "BLUE"
        else:
            points_leader = "DRAW"
        
        # Check for impact locks
        red_lock = self.get_strongest_lock(red_state.impact_flags)
        blue_lock = self.get_strongest_lock(blue_state.impact_flags)
        
        # If both have locks, highest priority wins (or points decide if same)
        if red_lock and blue_lock:
            red_priority = IMPACT_LOCK_RULES["priority_order"].index(red_lock) if red_lock in IMPACT_LOCK_RULES["priority_order"] else 999
            blue_priority = IMPACT_LOCK_RULES["priority_order"].index(blue_lock) if blue_lock in IMPACT_LOCK_RULES["priority_order"] else 999
            
            if red_priority < blue_priority:
                # Red has stronger lock
                return self.apply_impact_lock("RED", red_lock, points_leader, delta)
            elif blue_priority < red_priority:
                # Blue has stronger lock
                return self.apply_impact_lock("BLUE", blue_lock, points_leader, delta)
            else:
                # Same priority, points decide
                return points_leader, "points", delta
        
        # Only one side has a lock
        if red_lock:
            return self.apply_impact_lock("RED", red_lock, points_leader, delta)
        if blue_lock:
            return self.apply_impact_lock("BLUE", blue_lock, points_leader, delta)
        
        # No locks, points decide
        return points_leader, "points", delta
    
    def get_strongest_lock(self, impact_flags: Dict[str, bool]) -> Optional[str]:
        """Get the strongest impact lock from flags"""
        for lock_key in IMPACT_LOCK_RULES["priority_order"]:
            if impact_flags.get(lock_key, False):
                return lock_key
        return None
    
    def apply_impact_lock(
        self,
        lock_holder: str,
        lock_key: str,
        points_leader: str,
        delta: float
    ) -> Tuple[str, str, float]:
        """Apply impact lock logic"""
        lock_config = IMPACT_LOCK_RULES["locks"].get(lock_key, {})
        threshold = lock_config.get("delta_threshold", 0)
        reason_code = lock_config.get("reason_code", "impact_lock")
        
        # Lock holder wins unless opponent leads by >= threshold
        if points_leader == lock_holder:
            # Lock holder already winning on points
            return lock_holder, "points", delta
        elif points_leader == "DRAW":
            # Draw goes to lock holder
            return lock_holder, reason_code, delta
        else:
            # Opponent leading - check if they overcome the lock
            if delta >= threshold:
                # Opponent overcame the lock with volume
                return points_leader, "points", delta
            else:
                # Lock holds - impact side wins
                return lock_holder, reason_code, delta
    
    def determine_round_score(
        self,
        winner: str,
        delta: float,
        red_state: FighterRoundState,
        blue_state: FighterRoundState
    ) -> Tuple[int, int]:
        """Determine 10-point must score"""
        
        if winner == "DRAW" and delta < ROUND_SCORING["draw_threshold"]:
            return 10, 10
        
        # Count protected events for winner
        winner_state = red_state if winner == "RED" else blue_state
        loser_state = blue_state if winner == "RED" else red_state
        
        protected_count = sum([
            winner_state.impact_flags.get("rocked", False),
            winner_state.impact_flags.get("kd_flash", False),
            winner_state.impact_flags.get("kd_hard", False),
            winner_state.impact_flags.get("kd_nf", False),
            winner_state.has_submission and any([
                winner_state.impact_flags.get("sub_nf", False)
            ])
        ])
        
        # Check for 10-7
        if (protected_count >= ROUND_SCORING["score_10_7"]["min_impact_events"] or 
            delta >= ROUND_SCORING["score_10_7"]["min_delta"]):
            if winner == "RED":
                return 10, 7
            else:
                return 7, 10
        
        # Check for 10-8
        if (protected_count >= ROUND_SCORING["score_10_8"]["min_impact_events"] or 
            delta >= ROUND_SCORING["score_10_8"]["min_delta"]):
            if winner == "RED":
                return 10, 8
            else:
                return 8, 10
        
        # Default 10-9
        if winner == "RED":
            return 10, 9
        elif winner == "BLUE":
            return 9, 10
        else:
            return 10, 10
    
    def score_round(
        self,
        round_number: int,
        events: List[Dict[str, Any]]
    ) -> RoundResult:
        """
        Score a complete round.
        
        This is the main entry point for the v3 scoring engine.
        """
        # Initialize fighter states
        red_state = FighterRoundState(fighter="RED")
        blue_state = FighterRoundState(fighter="BLUE")
        
        # Score each event
        for event in events:
            corner = event.get("corner", "").upper()
            if corner not in ["RED", "BLUE"]:
                # Try legacy fighter field
                fighter = event.get("fighter", "")
                corner = "RED" if fighter == "fighter1" else "BLUE" if fighter == "fighter2" else ""
            
            if not corner:
                continue
            
            state = red_state if corner == "RED" else blue_state
            timestamp = event.get("timestamp", 0)
            
            self.score_event(event, state, timestamp)
        
        # RULE 4: Apply control without work discount
        red_control_discount = self.apply_control_without_work_discount(red_state)
        blue_control_discount = self.apply_control_without_work_discount(blue_state)
        
        if red_control_discount < 1.0:
            red_state.raw_points -= red_state.control_points * (1 - red_control_discount)
            red_state.control_points *= red_control_discount
        
        if blue_control_discount < 1.0:
            blue_state.raw_points -= blue_state.control_points * (1 - blue_control_discount)
            blue_state.control_points *= blue_control_discount
        
        # Determine winner with Impact Lock logic
        winner, winner_reason, delta = self.determine_winner(red_state, blue_state)
        
        # Determine 10-point must score
        red_score, blue_score = self.determine_round_score(
            winner, delta, red_state, blue_state
        )
        
        # Calculate share percentages
        total = red_state.raw_points + blue_state.raw_points
        if total > 0:
            red_share = (red_state.raw_points / total) * 100
            blue_share = (blue_state.raw_points / total) * 100
        else:
            red_share = blue_share = 50.0
        
        # Build result
        result = RoundResult(
            round_number=round_number,
            red_raw_points=red_state.raw_points,
            blue_raw_points=blue_state.raw_points,
            red_final_points=red_state.raw_points,
            blue_final_points=blue_state.raw_points,
            delta=delta,
            red_share_percent=round(red_share, 1),
            blue_share_percent=round(blue_share, 1),
            red_impact_flags=red_state.impact_flags.copy(),
            blue_impact_flags=blue_state.impact_flags.copy(),
            winner=winner,
            winner_reason=winner_reason,
            red_round_score=red_score,
            blue_round_score=blue_score,
            red_control_discount_applied=red_control_discount < 1.0,
            blue_control_discount_applied=blue_control_discount < 1.0,
            red_state=red_state,
            blue_state=blue_state,
        )
        
        return result
    
    def to_dict(self, result: RoundResult) -> Dict[str, Any]:
        """Convert RoundResult to dictionary for API response"""
        # Build breakdown from scored events
        red_breakdown = {}
        blue_breakdown = {}
        
        if result.red_state:
            for event in result.red_state.events:
                key = event.event_key
                red_breakdown[key] = red_breakdown.get(key, 0) + event.final_points
        
        if result.blue_state:
            for event in result.blue_state.events:
                key = event.event_key
                blue_breakdown[key] = blue_breakdown.get(key, 0) + event.final_points
        
        return {
            "round_number": result.round_number,
            "red_points": result.red_round_score,
            "blue_points": result.blue_round_score,
            "red_raw_points": round(result.red_raw_points, 2),
            "blue_raw_points": round(result.blue_raw_points, 2),
            "delta": round(result.delta, 2),
            "red_share_percent": result.red_share_percent,
            "blue_share_percent": result.blue_share_percent,
            "winner": result.winner,
            "winner_reason": result.winner_reason,
            "red_impact_flags": result.red_impact_flags,
            "blue_impact_flags": result.blue_impact_flags,
            "red_control_discount_applied": result.red_control_discount_applied,
            "blue_control_discount_applied": result.blue_control_discount_applied,
            
            # Legacy compatibility fields (required by server.py)
            "red_total": round(result.red_raw_points, 2),
            "blue_total": round(result.blue_raw_points, 2),
            "red_breakdown": {k: round(v, 2) for k, v in red_breakdown.items()},
            "blue_breakdown": {k: round(v, 2) for k, v in blue_breakdown.items()},
            "total_events": len(result.red_state.events) + len(result.blue_state.events) if result.red_state and result.blue_state else 0,
            "red_kd": sum([
                result.red_impact_flags.get("kd_flash", False),
                result.red_impact_flags.get("kd_hard", False),
                result.red_impact_flags.get("kd_nf", False),
            ]),
            "blue_kd": sum([
                result.blue_impact_flags.get("kd_flash", False),
                result.blue_impact_flags.get("kd_hard", False),
                result.blue_impact_flags.get("kd_nf", False),
            ]),
            
            # V3 receipt fields
            "receipt": {
                "round_number": result.round_number,
                "winner": result.winner,
                "score": f"{result.red_round_score}-{result.blue_round_score}",
                "red_raw": round(result.red_raw_points, 2),
                "blue_raw": round(result.blue_raw_points, 2),
                "winner_reason": result.winner_reason,
                "impact_lock_applied": result.winner_reason != "points",
                "red_control_discounted": result.red_control_discount_applied,
                "blue_control_discounted": result.blue_control_discount_applied,
            },
            "deltas": {
                "round": round(result.delta, 2),
            },
            "verdict": {
                "winner": result.winner,
                "score_string": f"{result.red_round_score}-{result.blue_round_score}",
                "red_points": result.red_round_score,
                "blue_points": result.blue_round_score,
            },
            "red_categories": {
                "striking": round(result.red_state.strike_points, 2) if result.red_state else 0,
                "grappling": 0,  # Not tracked separately in v3
                "control": round(result.red_state.control_points, 2) if result.red_state else 0,
                "impact": sum([60 if result.red_impact_flags.get("rocked") else 0,
                              100 if result.red_impact_flags.get("kd_flash") else 0,
                              150 if result.red_impact_flags.get("kd_hard") else 0,
                              210 if result.red_impact_flags.get("kd_nf") else 0]),
            },
            "blue_categories": {
                "striking": round(result.blue_state.strike_points, 2) if result.blue_state else 0,
                "grappling": 0,
                "control": round(result.blue_state.control_points, 2) if result.blue_state else 0,
                "impact": sum([60 if result.blue_impact_flags.get("rocked") else 0,
                              100 if result.blue_impact_flags.get("kd_flash") else 0,
                              150 if result.blue_impact_flags.get("kd_hard") else 0,
                              210 if result.blue_impact_flags.get("kd_nf") else 0]),
            },
            
            # Debug info (v3 specific)
            "debug": self.get_debug_info(result) if result.red_state and result.blue_state else {},
        }
    
    def get_debug_info(self, result: RoundResult) -> Dict[str, Any]:
        """Get detailed debug information for the round"""
        return {
            "red": {
                "technique_counts": result.red_state.technique_counts,
                "ss_total_count": result.red_state.ss_total_count,
                "takedown_stuffed_count": result.red_state.takedown_stuffed_count,
                "strike_points": round(result.red_state.strike_points, 2),
                "control_points": round(result.red_state.control_points, 2),
                "gnp_hard_points": round(result.red_state.gnp_hard_points, 2),
                "has_submission": result.red_state.has_submission,
                "events": [
                    {
                        "event_key": e.event_key,
                        "base_points": e.base_points,
                        "technique_mult": e.technique_multiplier,
                        "ss_mult": e.ss_multiplier,
                        "control_mult": e.control_multiplier,
                        "td_stuffed_mult": e.td_stuffed_multiplier,
                        "final_points": round(e.final_points, 2),
                    }
                    for e in result.red_state.events
                ]
            },
            "blue": {
                "technique_counts": result.blue_state.technique_counts,
                "ss_total_count": result.blue_state.ss_total_count,
                "takedown_stuffed_count": result.blue_state.takedown_stuffed_count,
                "strike_points": round(result.blue_state.strike_points, 2),
                "control_points": round(result.blue_state.control_points, 2),
                "gnp_hard_points": round(result.blue_state.gnp_hard_points, 2),
                "has_submission": result.blue_state.has_submission,
                "events": [
                    {
                        "event_key": e.event_key,
                        "base_points": e.base_points,
                        "technique_mult": e.technique_multiplier,
                        "ss_mult": e.ss_multiplier,
                        "control_mult": e.control_multiplier,
                        "td_stuffed_mult": e.td_stuffed_multiplier,
                        "final_points": round(e.final_points, 2),
                    }
                    for e in result.blue_state.events
                ]
            },
            "impact_lock_applied": result.winner_reason != "points",
        }


# Global engine instance
_engine = None

def get_engine() -> ScoringEngineV3:
    """Get or create the global engine instance"""
    global _engine
    if _engine is None:
        _engine = ScoringEngineV3()
    return _engine


def score_round_v3(round_number: int, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main entry point for v3 scoring.
    
    Args:
        round_number: The round number
        events: List of raw events
        
    Returns:
        Dictionary with scoring results
    """
    engine = get_engine()
    result = engine.score_round(round_number, events)
    return engine.to_dict(result)
