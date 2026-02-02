"""
Fight Judge AI - Core Scoring Service
=====================================

This module contains the core scoring logic for MMA fights.
It provides clean, testable functions for scoring rounds and fights.

Key Functions:
- score_round(): Takes round stats, returns scores + flags
- score_fight(): Aggregates rounds into final outcome
- calculate_delta(): Computes point differential from events
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


# ============== Enums ==============

class RoundResult(Enum):
    """Possible round outcomes"""
    RED_WIN_10_9 = "10-9 RED"
    RED_WIN_10_8 = "10-8 RED"
    RED_WIN_10_7 = "10-7 RED"
    BLUE_WIN_10_9 = "10-9 BLUE"
    BLUE_WIN_10_8 = "10-8 BLUE"
    BLUE_WIN_10_7 = "10-7 BLUE"
    DRAW = "10-10 DRAW"


class FightResult(Enum):
    """Possible fight outcomes"""
    RED_DECISION = "RED_DECISION"
    BLUE_DECISION = "BLUE_DECISION"
    RED_KO_TKO = "RED_KO_TKO"
    BLUE_KO_TKO = "BLUE_KO_TKO"
    RED_SUBMISSION = "RED_SUBMISSION"
    BLUE_SUBMISSION = "BLUE_SUBMISSION"
    DRAW = "DRAW"
    MAJORITY_DRAW = "MAJORITY_DRAW"
    NO_CONTEST = "NO_CONTEST"


class FinishMethod(Enum):
    """Methods of finishing a fight"""
    DECISION = "DEC"
    UNANIMOUS_DECISION = "UD"
    SPLIT_DECISION = "SD"
    MAJORITY_DECISION = "MD"
    KO = "KO"
    TKO = "TKO"
    SUBMISSION = "SUB"
    DQ = "DQ"
    NO_CONTEST = "NC"


# ============== Data Classes ==============

@dataclass
class RoundStats:
    """Statistics for a single round"""
    round_number: int
    
    # Strikes
    red_significant_strikes: int = 0
    blue_significant_strikes: int = 0
    red_total_strikes: int = 0
    blue_total_strikes: int = 0
    red_knockdowns: int = 0
    blue_knockdowns: int = 0
    
    # Grappling
    red_takedowns: int = 0
    blue_takedowns: int = 0
    red_takedowns_attempted: int = 0
    blue_takedowns_attempted: int = 0
    red_submission_attempts: int = 0
    blue_submission_attempts: int = 0
    
    # Control
    red_control_time_seconds: int = 0
    blue_control_time_seconds: int = 0
    
    # Impact events (high-value moments)
    red_near_finishes: int = 0  # Hurt opponent badly
    blue_near_finishes: int = 0
    
    # Fouls and deductions
    red_fouls: int = 0
    blue_fouls: int = 0
    red_point_deductions: int = 0
    blue_point_deductions: int = 0
    
    # Raw events (for delta calculation)
    events: List[Dict] = field(default_factory=list)
    
    # Metadata
    finish_in_round: bool = False
    finish_method: Optional[str] = None
    finish_winner: Optional[str] = None


@dataclass
class RoundScore:
    """Calculated score for a single round"""
    round_number: int
    red_score: int
    blue_score: int
    winner: str  # "RED", "BLUE", or "DRAW"
    result: RoundResult
    delta: float
    
    # Flags
    is_10_8: bool = False
    is_10_7: bool = False
    requires_approval: bool = False  # For 10-8 supervisor approval
    
    # Point deductions applied
    red_deductions: int = 0
    blue_deductions: int = 0
    
    # Breakdown for explainability
    breakdown: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "round_number": self.round_number,
            "red_score": self.red_score,
            "blue_score": self.blue_score,
            "red_points": self.red_score,  # Alias for compatibility
            "blue_points": self.blue_score,
            "winner": self.winner,
            "result": self.result.value,
            "delta": self.delta,
            "is_10_8": self.is_10_8,
            "is_10_7": self.is_10_7,
            "requires_approval": self.requires_approval,
            "red_deductions": self.red_deductions,
            "blue_deductions": self.blue_deductions,
            "breakdown": self.breakdown
        }


@dataclass
class FightScore:
    """Final fight score and outcome"""
    red_total: int
    blue_total: int
    winner: str  # "RED", "BLUE", or "DRAW"
    result: FightResult
    finish_method: FinishMethod
    rounds: List[RoundScore]
    
    # Details
    rounds_completed: int = 0
    finish_round: Optional[int] = None
    finish_time: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "red_total": self.red_total,
            "blue_total": self.blue_total,
            "final_red": self.red_total,  # Alias
            "final_blue": self.blue_total,
            "winner": self.winner,
            "result": self.result.value,
            "finish_method": self.finish_method.value,
            "rounds": [r.to_dict() for r in self.rounds],
            "rounds_completed": self.rounds_completed,
            "finish_round": self.finish_round,
            "finish_time": self.finish_time
        }


# ============== Scoring Configuration ==============

SCORING_CONFIG = {
    # Delta thresholds for 10-point must system
    "draw_threshold": 5,      # |delta| < 5 = 10-10
    "threshold_10_8": 500,    # |delta| >= 500 = 10-8
    "threshold_10_7": 750,    # |delta| >= 750 = 10-7
    
    # Event point values
    "event_points": {
        # Strikes
        "Jab": 10,
        "Cross": 14,
        "Hook": 14,
        "Uppercut": 14,
        "Overhand": 16,
        "Spinning Back Fist": 18,
        "Body Punch": 10,
        "Kick": 3,
        "Body Kick": 12,
        "Head Kick": 25,
        "Leg Kick": 6,
        "Calf Kick": 8,
        "Knee": 15,
        "Flying Knee": 25,
        "Elbow": 18,
        "Spinning Elbow": 22,
        
        # Grappling
        "Takedown": 6,
        "Takedown Stuffed": 2,
        "Sweep/Reversal": 20,
        "Submission Attempt": 15,
        
        # Control
        "Control": 1,  # Per second
        
        # High Impact
        "Knockdown": {"Flash": 50, "Hard": 75, "Near-Finish": 100},
        "KD": {"Flash": 50, "Hard": 75, "Near-Finish": 100},
    },
    
    # Impact lock thresholds (protects leading fighter)
    "impact_locks": {
        "knockdown_near_finish": 100,  # Delta protection after NF knockdown
        "knockdown_hard": 50,
    },
    
    # Fouls
    "foul_warning_threshold": 2,  # Warnings before deduction
    "foul_point_deduction": 1,
}


# ============== Core Scoring Functions ==============

def calculate_delta(events: List[Dict], config: Dict = None) -> Tuple[float, float, Dict]:
    """
    Calculate point differential from a list of events.
    
    Args:
        events: List of event dictionaries with corner, event_type, metadata
        config: Optional custom scoring configuration
    
    Returns:
        Tuple of (red_delta, blue_delta, breakdown)
    """
    if config is None:
        config = SCORING_CONFIG
    
    event_points = config["event_points"]
    
    red_delta = 0.0
    blue_delta = 0.0
    breakdown = {
        "red": {"strikes": 0, "grappling": 0, "control": 0, "impact": 0},
        "blue": {"strikes": 0, "grappling": 0, "control": 0, "impact": 0},
        "event_counts": {"red": {}, "blue": {}}
    }
    
    for event in events:
        corner = event.get("corner", "").upper()
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {})
        tier = metadata.get("tier", "")
        
        # Get base points for event type
        points = 0
        category = "strikes"
        
        if event_type in event_points:
            point_value = event_points[event_type]
            
            # Handle tiered events (knockdowns)
            if isinstance(point_value, dict):
                points = point_value.get(tier, list(point_value.values())[0])
                category = "impact"
            else:
                points = point_value
                
                # Categorize
                if event_type in ["Takedown", "Takedown Stuffed", "Sweep/Reversal", "Submission Attempt"]:
                    category = "grappling"
                elif event_type == "Control":
                    category = "control"
                    # Control time in seconds
                    duration = metadata.get("duration", 1)
                    points = points * duration
        
        # Apply points to correct corner
        if corner == "RED":
            red_delta += points
            breakdown["red"][category] += points
            breakdown["event_counts"]["red"][event_type] = breakdown["event_counts"]["red"].get(event_type, 0) + 1
        elif corner == "BLUE":
            blue_delta += points
            breakdown["blue"][category] += points
            breakdown["event_counts"]["blue"][event_type] = breakdown["event_counts"]["blue"].get(event_type, 0) + 1
    
    return red_delta, blue_delta, breakdown


def score_round(stats: RoundStats, config: Dict = None, require_10_8_approval: bool = True) -> RoundScore:
    """
    Score a single round based on provided statistics.
    
    This is the core scoring function that implements the 10-point must system.
    
    Args:
        stats: RoundStats object with all round statistics
        config: Optional custom scoring configuration
        require_10_8_approval: If True, flags 10-8 rounds for supervisor approval
    
    Returns:
        RoundScore object with calculated scores and flags
    """
    if config is None:
        config = SCORING_CONFIG
    
    # Calculate delta from events if provided
    if stats.events:
        red_delta, blue_delta, breakdown = calculate_delta(stats.events, config)
        delta = red_delta - blue_delta
    else:
        # Calculate from stats if no events
        delta = _calculate_delta_from_stats(stats, config)
        breakdown = {"calculated_from_stats": True}
    
    # Determine base scores using 10-point must system
    abs_delta = abs(delta)
    
    # Default scores
    red_score = 10
    blue_score = 10
    is_10_8 = False
    is_10_7 = False
    
    if abs_delta <= config["draw_threshold"]:
        # Draw round
        winner = "DRAW"
        result = RoundResult.DRAW
    elif delta > 0:
        # Red wins
        winner = "RED"
        if abs_delta >= config["threshold_10_7"]:
            blue_score = 7
            is_10_7 = True
            is_10_8 = True
            result = RoundResult.RED_WIN_10_7
        elif abs_delta >= config["threshold_10_8"]:
            blue_score = 8
            is_10_8 = True
            result = RoundResult.RED_WIN_10_8
        else:
            blue_score = 9
            result = RoundResult.RED_WIN_10_9
    else:
        # Blue wins
        winner = "BLUE"
        if abs_delta >= config["threshold_10_7"]:
            red_score = 7
            is_10_7 = True
            is_10_8 = True
            result = RoundResult.BLUE_WIN_10_7
        elif abs_delta >= config["threshold_10_8"]:
            red_score = 8
            is_10_8 = True
            result = RoundResult.BLUE_WIN_10_8
        else:
            red_score = 9
            result = RoundResult.BLUE_WIN_10_9
    
    # Apply point deductions from fouls
    red_score -= stats.red_point_deductions
    blue_score -= stats.blue_point_deductions
    
    # Ensure scores don't go below 7
    red_score = max(7, red_score)
    blue_score = max(7, blue_score)
    
    # Check if 10-8 requires approval
    requires_approval = is_10_8 and require_10_8_approval
    
    return RoundScore(
        round_number=stats.round_number,
        red_score=red_score,
        blue_score=blue_score,
        winner=winner,
        result=result,
        delta=delta,
        is_10_8=is_10_8,
        is_10_7=is_10_7,
        requires_approval=requires_approval,
        red_deductions=stats.red_point_deductions,
        blue_deductions=stats.blue_point_deductions,
        breakdown=breakdown
    )


def _calculate_delta_from_stats(stats: RoundStats, config: Dict) -> float:
    """
    Calculate delta from aggregated stats when individual events aren't available.
    """
    red_points = 0.0
    blue_points = 0.0
    
    # Strikes (weighted by significant vs total)
    red_points += stats.red_significant_strikes * 15
    blue_points += stats.blue_significant_strikes * 15
    red_points += (stats.red_total_strikes - stats.red_significant_strikes) * 5
    blue_points += (stats.blue_total_strikes - stats.blue_significant_strikes) * 5
    
    # Knockdowns (major impact)
    red_points += stats.red_knockdowns * 75
    blue_points += stats.blue_knockdowns * 75
    
    # Near finishes
    red_points += stats.red_near_finishes * 100
    blue_points += stats.blue_near_finishes * 100
    
    # Takedowns
    red_points += stats.red_takedowns * 20
    blue_points += stats.blue_takedowns * 20
    
    # Submission attempts
    red_points += stats.red_submission_attempts * 15
    blue_points += stats.blue_submission_attempts * 15
    
    # Control time (1 point per 3 seconds)
    red_points += stats.red_control_time_seconds / 3
    blue_points += stats.blue_control_time_seconds / 3
    
    return red_points - blue_points


def score_fight(
    rounds: List[RoundScore],
    finish_method: Optional[str] = None,
    finish_winner: Optional[str] = None,
    finish_round: Optional[int] = None,
    finish_time: Optional[str] = None
) -> FightScore:
    """
    Aggregate round scores into a final fight score.
    
    Args:
        rounds: List of RoundScore objects
        finish_method: If fight ended early, the method (KO, TKO, SUB, etc.)
        finish_winner: If fight ended early, the winner (RED or BLUE)
        finish_round: Round in which finish occurred
        finish_time: Time of finish in the round
    
    Returns:
        FightScore object with final outcome
    """
    if not rounds:
        raise ValueError("Cannot score fight with no rounds")
    
    # Check for early finish
    if finish_method and finish_winner:
        # Fight ended by finish
        red_total = sum(r.red_score for r in rounds)
        blue_total = sum(r.blue_score for r in rounds)
        
        # Determine result
        if finish_winner == "RED":
            if finish_method in ["KO", "TKO"]:
                result = FightResult.RED_KO_TKO
                method = FinishMethod.TKO if finish_method == "TKO" else FinishMethod.KO
            elif finish_method in ["SUB", "SUBMISSION"]:
                result = FightResult.RED_SUBMISSION
                method = FinishMethod.SUBMISSION
            elif finish_method == "DQ":
                result = FightResult.RED_DECISION  # DQ counts as win
                method = FinishMethod.DQ
            else:
                result = FightResult.RED_DECISION
                method = FinishMethod.DECISION
            winner = "RED"
        else:
            if finish_method in ["KO", "TKO"]:
                result = FightResult.BLUE_KO_TKO
                method = FinishMethod.TKO if finish_method == "TKO" else FinishMethod.KO
            elif finish_method in ["SUB", "SUBMISSION"]:
                result = FightResult.BLUE_SUBMISSION
                method = FinishMethod.SUBMISSION
            elif finish_method == "DQ":
                result = FightResult.BLUE_DECISION
                method = FinishMethod.DQ
            else:
                result = FightResult.BLUE_DECISION
                method = FinishMethod.DECISION
            winner = "BLUE"
        
        return FightScore(
            red_total=red_total,
            blue_total=blue_total,
            winner=winner,
            result=result,
            finish_method=method,
            rounds=rounds,
            rounds_completed=len(rounds),
            finish_round=finish_round,
            finish_time=finish_time
        )
    
    # Fight went to decision
    red_total = sum(r.red_score for r in rounds)
    blue_total = sum(r.blue_score for r in rounds)
    
    # Determine winner
    if red_total > blue_total:
        winner = "RED"
        result = FightResult.RED_DECISION
    elif blue_total > red_total:
        winner = "BLUE"
        result = FightResult.BLUE_DECISION
    else:
        winner = "DRAW"
        result = FightResult.DRAW
    
    # Determine decision type based on round winners
    red_rounds_won = sum(1 for r in rounds if r.winner == "RED")
    blue_rounds_won = sum(1 for r in rounds if r.winner == "BLUE")
    
    if winner != "DRAW":
        if red_rounds_won == len(rounds) or blue_rounds_won == len(rounds):
            method = FinishMethod.UNANIMOUS_DECISION
        elif abs(red_rounds_won - blue_rounds_won) == 1:
            method = FinishMethod.SPLIT_DECISION
        else:
            method = FinishMethod.DECISION
    else:
        method = FinishMethod.DECISION
    
    return FightScore(
        red_total=red_total,
        blue_total=blue_total,
        winner=winner,
        result=result,
        finish_method=method,
        rounds=rounds,
        rounds_completed=len(rounds)
    )


# ============== Utility Functions ==============

def validate_round_stats(stats: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate round statistics input.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["round_number"]
    
    for field in required_fields:
        if field not in stats:
            return False, f"Missing required field: {field}"
    
    # Validate round number
    if not isinstance(stats["round_number"], int) or stats["round_number"] < 1:
        return False, "round_number must be a positive integer"
    
    # Validate numeric fields
    numeric_fields = [
        "red_significant_strikes", "blue_significant_strikes",
        "red_total_strikes", "blue_total_strikes",
        "red_knockdowns", "blue_knockdowns",
        "red_takedowns", "blue_takedowns",
        "red_control_time_seconds", "blue_control_time_seconds"
    ]
    
    for field in numeric_fields:
        if field in stats:
            if not isinstance(stats[field], (int, float)) or stats[field] < 0:
                return False, f"{field} must be a non-negative number"
    
    return True, None


def round_stats_from_dict(data: Dict) -> RoundStats:
    """Convert a dictionary to RoundStats object."""
    return RoundStats(
        round_number=data.get("round_number", 1),
        red_significant_strikes=data.get("red_significant_strikes", 0),
        blue_significant_strikes=data.get("blue_significant_strikes", 0),
        red_total_strikes=data.get("red_total_strikes", 0),
        blue_total_strikes=data.get("blue_total_strikes", 0),
        red_knockdowns=data.get("red_knockdowns", 0),
        blue_knockdowns=data.get("blue_knockdowns", 0),
        red_takedowns=data.get("red_takedowns", 0),
        blue_takedowns=data.get("blue_takedowns", 0),
        red_takedowns_attempted=data.get("red_takedowns_attempted", 0),
        blue_takedowns_attempted=data.get("blue_takedowns_attempted", 0),
        red_submission_attempts=data.get("red_submission_attempts", 0),
        blue_submission_attempts=data.get("blue_submission_attempts", 0),
        red_control_time_seconds=data.get("red_control_time_seconds", 0),
        blue_control_time_seconds=data.get("blue_control_time_seconds", 0),
        red_near_finishes=data.get("red_near_finishes", 0),
        blue_near_finishes=data.get("blue_near_finishes", 0),
        red_fouls=data.get("red_fouls", 0),
        blue_fouls=data.get("blue_fouls", 0),
        red_point_deductions=data.get("red_point_deductions", 0),
        blue_point_deductions=data.get("blue_point_deductions", 0),
        events=data.get("events", []),
        finish_in_round=data.get("finish_in_round", False),
        finish_method=data.get("finish_method"),
        finish_winner=data.get("finish_winner")
    )
