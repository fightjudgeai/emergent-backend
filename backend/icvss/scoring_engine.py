"""
ICVSS Hybrid Scoring Engine
Fuses CV events + Judge manual events using FightJudge AI percentages
"""

from typing import List, Dict, Tuple
import logging
from .models import CVEvent, EventType, EventSource

logger = logging.getLogger(__name__)


class HybridScoringEngine:
    """
    Hybrid scoring that combines CV-detected events with judge manual events
    Uses current FightJudge AI percentages: Striking 50%, Grappling 40%, Control 10%
    """
    
    # Current FightJudge AI weights (from existing system)
    CATEGORY_WEIGHTS = {
        "striking": 0.50,  # 50%
        "grappling": 0.40,  # 40%
        "control": 0.10    # 10%
    }
    
    # Event scoring values (aligned with existing system)
    EVENT_VALUES = {
        # Strikes (Striking category)
        EventType.STRIKE_JAB: {"category": "striking", "base_value": 1.0},
        EventType.STRIKE_CROSS: {"category": "striking", "base_value": 2.0},
        EventType.STRIKE_HOOK: {"category": "striking", "base_value": 2.5},
        EventType.STRIKE_UPPERCUT: {"category": "striking", "base_value": 2.5},
        EventType.STRIKE_ELBOW: {"category": "striking", "base_value": 3.0},
        EventType.STRIKE_KNEE: {"category": "striking", "base_value": 4.0},
        
        # Kicks (Striking category)
        EventType.KICK_HEAD: {"category": "striking", "base_value": 5.0},
        EventType.KICK_BODY: {"category": "striking", "base_value": 3.0},
        EventType.KICK_LOW: {"category": "striking", "base_value": 1.5},
        EventType.KICK_FRONT: {"category": "striking", "base_value": 2.0},
        
        # Damage (Striking category with multipliers)
        EventType.ROCK: {"category": "striking", "base_value": 20.0},
        EventType.KD_FLASH: {"category": "striking", "base_value": 30.0},
        EventType.KD_HARD: {"category": "striking", "base_value": 50.0},
        EventType.KD_NEARFINISH: {"category": "striking", "base_value": 80.0},
        
        # Grappling (Grappling category)
        EventType.TD_LANDED: {"category": "grappling", "base_value": 15.0},
        EventType.TD_STUFFED: {"category": "grappling", "base_value": 5.0},
        EventType.SUB_ATTEMPT_LIGHT: {"category": "grappling", "base_value": 10.0},
        EventType.SUB_ATTEMPT_DEEP: {"category": "grappling", "base_value": 25.0},
        EventType.SUB_ATTEMPT_NEARFINISH: {"category": "grappling", "base_value": 60.0},
        EventType.SWEEP: {"category": "grappling", "base_value": 8.0},
        
        # Control (Control category - calculated from duration)
        EventType.CONTROL_TOP: {"category": "control", "base_value": 0.5},  # per second
        EventType.CONTROL_BACK: {"category": "control", "base_value": 0.7},  # per second
        EventType.CONTROL_CAGE: {"category": "control", "base_value": 0.3},  # per second
    }
    
    def __init__(self, cv_weight: float = 0.7, judge_weight: float = 0.3):
        """
        Args:
            cv_weight: Weight for CV events (0-1)
            judge_weight: Weight for judge manual events (0-1)
        """
        self.cv_weight = cv_weight
        self.judge_weight = judge_weight
    
    def calculate_hybrid_score(self,
                               cv_events: List[CVEvent],
                               judge_events: List[Dict],
                               round_duration: int = 300) -> Dict:
        """
        Calculate hybrid score combining CV and judge events
        
        Args:
            cv_events: List of processed CV events
            judge_events: List of judge manual events
            round_duration: Round duration in seconds (default 5 min = 300s)
        
        Returns:
            Score breakdown with fighter1 and fighter2 scores
        """
        logger.info(f"Calculating hybrid score: {len(cv_events)} CV events, {len(judge_events)} judge events")
        
        # Calculate CV scores
        f1_cv_score, f1_cv_breakdown = self._score_events(cv_events, "fighter1")
        f2_cv_score, f2_cv_breakdown = self._score_events(cv_events, "fighter2")
        
        # Calculate judge scores (using existing scoring logic)
        f1_judge_score, f1_judge_breakdown = self._score_judge_events(judge_events, "fighter1")
        f2_judge_score, f2_judge_breakdown = self._score_judge_events(judge_events, "fighter2")
        
        # Fuse scores with weights
        f1_total = (f1_cv_score * self.cv_weight) + (f1_judge_score * self.judge_weight)
        f2_total = (f2_cv_score * self.cv_weight) + (f2_judge_score * self.judge_weight)
        
        logger.info(f"  Fighter1: CV={f1_cv_score:.2f}, Judge={f1_judge_score:.2f}, Total={f1_total:.2f}")
        logger.info(f"  Fighter2: CV={f2_cv_score:.2f}, Judge={f2_judge_score:.2f}, Total={f2_total:.2f}")
        
        # Apply damage primacy rule
        f1_total, f2_total = self._apply_damage_primacy(
            f1_total, f2_total,
            f1_cv_breakdown, f2_cv_breakdown,
            f1_judge_breakdown, f2_judge_breakdown
        )
        
        # Determine winner and score card
        score_diff = f1_total - f2_total
        card, winner = self._determine_score_card(score_diff, f1_cv_breakdown, f2_cv_breakdown)
        
        return {
            "fighter1_total": f1_total,
            "fighter2_total": f2_total,
            "fighter1_breakdown": {
                "cv_score": f1_cv_score,
                "judge_score": f1_judge_score,
                "striking": f1_cv_breakdown["striking"] + f1_judge_breakdown.get("striking", 0),
                "grappling": f1_cv_breakdown["grappling"] + f1_judge_breakdown.get("grappling", 0),
                "control": f1_cv_breakdown["control"] + f1_judge_breakdown.get("control", 0)
            },
            "fighter2_breakdown": {
                "cv_score": f2_cv_score,
                "judge_score": f2_judge_score,
                "striking": f2_cv_breakdown["striking"] + f2_judge_breakdown.get("striking", 0),
                "grappling": f2_cv_breakdown["grappling"] + f2_judge_breakdown.get("grappling", 0),
                "control": f2_cv_breakdown["control"] + f2_judge_breakdown.get("control", 0)
            },
            "score_card": card,
            "winner": winner,
            "cv_contribution": self.cv_weight,
            "judge_contribution": self.judge_weight,
            "cv_event_count": len(cv_events),
            "judge_event_count": len(judge_events)
        }
    
    def _score_events(self, events: List[CVEvent], fighter_id: str) -> Tuple[float, Dict]:
        """Score CV events for a specific fighter"""
        fighter_events = [e for e in events if e.fighter_id == fighter_id]
        
        categories = {
            "striking": 0.0,
            "grappling": 0.0,
            "control": 0.0
        }
        
        for event in fighter_events:
            event_config = self.EVENT_VALUES.get(event.event_type)
            if not event_config:
                continue
            
            category = event_config["category"]
            base_value = event_config["base_value"]
            
            # Apply severity multiplier (CV confidence affects impact)
            value = base_value * event.severity * event.confidence
            
            categories[category] += value
        
        # Apply category weights
        total = (
            categories["striking"] * self.CATEGORY_WEIGHTS["striking"] +
            categories["grappling"] * self.CATEGORY_WEIGHTS["grappling"] +
            categories["control"] * self.CATEGORY_WEIGHTS["control"]
        )
        
        return total, categories
    
    def _score_judge_events(self, events: List[Dict], fighter_id: str) -> Tuple[float, Dict]:
        """Score judge manual events (using existing scoring logic)"""
        fighter_events = [e for e in events if e.get("fighter") == fighter_id]
        
        categories = {
            "striking": 0.0,
            "grappling": 0.0,
            "control": 0.0
        }
        
        # Map existing event types to categories
        for event in fighter_events:
            event_type = event.get("event_type", "")
            
            # Striking events
            if any(x in event_type.lower() for x in ["jab", "cross", "hook", "kick", "knee", "elbow"]):
                categories["striking"] += 2.0
            
            # Damage events
            if "rock" in event_type.lower():
                categories["striking"] += 20.0
            elif "kd" in event_type.lower():
                categories["striking"] += 40.0
            
            # Grappling events
            if "takedown" in event_type.lower():
                categories["grappling"] += 15.0
            elif "submission" in event_type.lower():
                categories["grappling"] += 20.0
            
            # Control events (from metadata duration)
            if "control" in event_type.lower():
                duration = event.get("metadata", {}).get("duration", 0)
                categories["control"] += duration * 0.5
        
        # Apply category weights
        total = (
            categories["striking"] * self.CATEGORY_WEIGHTS["striking"] +
            categories["grappling"] * self.CATEGORY_WEIGHTS["grappling"] +
            categories["control"] * self.CATEGORY_WEIGHTS["control"]
        )
        
        return total, categories
    
    def _apply_damage_primacy(self, f1_total, f2_total, f1_cv, f2_cv, f1_judge, f2_judge) -> Tuple[float, float]:
        """
        Apply damage primacy rule
        If one fighter has significant damage advantage (KD, rock), they win regardless
        """
        # Check for knockdowns in CV events
        f1_damage = f1_cv.get("striking", 0) + f1_judge.get("striking", 0)
        f2_damage = f2_cv.get("striking", 0) + f2_judge.get("striking", 0)
        
        damage_diff = f1_damage - f2_damage
        
        # If damage difference is significant (>30 points), ensure winner
        if damage_diff > 30 and f1_total < f2_total:
            logger.info("  [DAMAGE PRIMACY] Fighter1 damage overrides score")
            return f1_total + 50, f2_total
        elif damage_diff < -30 and f2_total < f1_total:
            logger.info("  [DAMAGE PRIMACY] Fighter2 damage overrides score")
            return f1_total, f2_total + 50
        
        return f1_total, f2_total
    
    def _determine_score_card(self, score_diff: float, f1_cv: Dict, f2_cv: Dict) -> Tuple[str, str]:
        """Determine 10-point must score card"""
        
        # Check for near-finish events (KD, deep sub)
        f1_has_nearfinish = "KD_hard" in str(f1_cv) or "KD_nearfinish" in str(f1_cv)
        f2_has_nearfinish = "KD_hard" in str(f2_cv) or "KD_nearfinish" in str(f2_cv)
        
        # 10-10 draw (extremely rare)
        if abs(score_diff) <= 3.0:
            return "10-10", "DRAW"
        
        # 10-9 (standard win)
        elif abs(score_diff) < 100.0:
            if score_diff > 0:
                return "10-9", "fighter1"
            else:
                return "9-10", "fighter2"
        
        # 10-8 (dominant win)
        elif abs(score_diff) < 200.0:
            if score_diff > 0:
                card = "10-8" if f1_has_nearfinish else "10-9"
                return card, "fighter1"
            else:
                card = "8-10" if f2_has_nearfinish else "9-10"
                return card, "fighter2"
        
        # 10-7 (complete domination)
        else:
            if score_diff > 0:
                return "10-7", "fighter1"
            else:
                return "7-10", "fighter2"
