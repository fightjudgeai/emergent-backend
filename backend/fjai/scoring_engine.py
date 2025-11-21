"""
Fight Judge AI - Weighted Scoring Engine
Combines manual + CV events with damage primacy rule
"""

from typing import List, Dict, Tuple
import logging
from .models import (
    CombatEvent, EventType, RoundScore, ScoreBreakdown,
    ScoringWeights
)

logger = logging.getLogger(__name__)


class WeightedScoringEngine:
    """Weighted scoring with damage primacy"""
    
    # Event base values
    EVENT_VALUES = {
        # Knockdowns
        EventType.KD_FLASH: 15.0,
        EventType.KD_HARD: 25.0,
        EventType.KD_NF: 35.0,
        
        # Damage
        EventType.ROCKED: 12.0,
        EventType.STRIKE_HIGHIMPACT: 5.0,
        EventType.STRIKE_SIG: 2.0,
        
        # Grappling
        EventType.TD_LAND: 4.0,
        EventType.TD_ATTEMPT: 0.5,
        EventType.SUB_ATTEMPT: 6.0,
        
        # Control (per second)
        EventType.CONTROL_START: 0.0,
        EventType.CONTROL_END: 0.0,  # Calculated from duration
        
        # Momentum
        EventType.MOMENTUM_SWING: 8.0
    }
    
    def __init__(self, weights: ScoringWeights = None):
        self.weights = weights or ScoringWeights()
    
    def calculate_round_score(
        self,
        events: List[CombatEvent],
        bout_id: str,
        round_id: str,
        round_num: int
    ) -> RoundScore:
        """
        Calculate complete round score from events
        """
        # Separate events by fighter
        fighter_a_events = [e for e in events if e.fighter_id == "fighter_a"]
        fighter_b_events = [e for e in events if e.fighter_id == "fighter_b"]
        
        # Calculate breakdowns
        fighter_a_breakdown = self._calculate_breakdown(fighter_a_events)
        fighter_b_breakdown = self._calculate_breakdown(fighter_b_events)
        
        # Apply weighted scoring
        fighter_a_score = self._apply_weights(fighter_a_breakdown)
        fighter_b_score = self._apply_weights(fighter_b_breakdown)
        
        # Check damage primacy
        damage_override = self._check_damage_primacy(
            fighter_a_breakdown.damage,
            fighter_b_breakdown.damage,
            fighter_a_score,
            fighter_b_score
        )
        
        if damage_override:
            # Damage override - winner determined solely by damage
            if fighter_a_breakdown.damage > fighter_b_breakdown.damage:
                fighter_a_score = max(fighter_a_score, fighter_b_score + 20.0)
            else:
                fighter_b_score = max(fighter_b_score, fighter_a_score + 20.0)
        
        # Map to 10-point-must
        score_card, winner = self._map_to_10_point_must(fighter_a_score, fighter_b_score)
        
        # Calculate confidence
        confidence = self._calculate_confidence(events, fighter_a_score, fighter_b_score)
        
        # Event counts
        manual_count = len([e for e in events if e.source.value == "manual"])
        cv_count = len([e for e in events if e.source.value == "cv_system"])
        
        return RoundScore(
            round_id=round_id,
            bout_id=bout_id,
            round_num=round_num,
            fighter_a_score=fighter_a_score,
            fighter_b_score=fighter_b_score,
            score_card=score_card,
            winner=winner,
            confidence=confidence,
            fighter_a_breakdown=fighter_a_breakdown,
            fighter_b_breakdown=fighter_b_breakdown,
            total_events=len(events),
            manual_events=manual_count,
            cv_events=cv_count,
            damage_override=damage_override
        )
    
    def _calculate_breakdown(self, events: List[CombatEvent]) -> ScoreBreakdown:
        """
        Calculate score breakdown by category
        """
        damage = 0.0
        control = 0.0
        aggression = 0.0
        defense = 0.0
        
        # Track control time
        control_start_time = None
        
        for event in events:
            # Get base value
            base_value = self.EVENT_VALUES.get(event.event_type, 0.0)
            
            # Apply severity multiplier
            value = base_value * event.severity
            
            # Categorize event
            if event.event_type in [
                EventType.KD_FLASH, EventType.KD_HARD, EventType.KD_NF,
                EventType.ROCKED, EventType.STRIKE_HIGHIMPACT
            ]:
                damage += value
            
            elif event.event_type == EventType.STRIKE_SIG:
                # Significant strikes contribute to both damage and aggression
                damage += value * 0.5
                aggression += value * 0.5
            
            elif event.event_type in [EventType.TD_LAND, EventType.SUB_ATTEMPT]:
                # Grappling contributes to control
                control += value
            
            elif event.event_type == EventType.CONTROL_START:
                control_start_time = event.timestamp_ms
            
            elif event.event_type == EventType.CONTROL_END:
                if control_start_time:
                    # Calculate control duration
                    duration_ms = event.timestamp_ms - control_start_time
                    duration_sec = duration_ms / 1000.0
                    control += duration_sec * 0.3  # 0.3 points per second
                    control_start_time = None
            
            elif event.event_type == EventType.MOMENTUM_SWING:
                # Momentum contributes to aggression
                aggression += value
            
            elif event.event_type == EventType.TD_ATTEMPT:
                # Failed takedowns are defensive wins for opponent
                # This is tracked separately in opponent's defense
                pass
        
        # Calculate defense (inverse of opponent's successful offense)
        # This is a simplified version - full implementation would track stuffed TDs, etc.
        defense = 0.0  # Placeholder
        
        total = damage + control + aggression + defense
        
        return ScoreBreakdown(
            damage=damage,
            control=control,
            aggression=aggression,
            defense=defense,
            total=total
        )
    
    def _apply_weights(self, breakdown: ScoreBreakdown) -> float:
        """
        Apply category weights to get final score
        """
        return (
            breakdown.damage * self.weights.damage +
            breakdown.control * self.weights.control +
            breakdown.aggression * self.weights.aggression +
            breakdown.defense * self.weights.defense
        )
    
    def _check_damage_primacy(
        self,
        damage_a: float,
        damage_b: float,
        score_a: float,
        score_b: float
    ) -> bool:
        """
        Check if damage primacy rule should apply
        Returns True if one fighter has significant damage advantage
        """
        if damage_a == 0 and damage_b == 0:
            return False
        
        total_damage = damage_a + damage_b
        if total_damage == 0:
            return False
        
        # Check if one fighter has >30% of total damage
        damage_ratio = max(damage_a, damage_b) / total_damage
        
        return damage_ratio >= (0.5 + self.weights.damage_primacy_threshold)
    
    def _map_to_10_point_must(self, score_a: float, score_b: float) -> Tuple[str, str]:
        """
        Map raw scores to 10-point-must system
        
        Returns:
            (score_card: str, winner: str)
        """
        diff = abs(score_a - score_b)
        
        if diff < 3.0:
            # Very close - 10-10 draw
            return "10-10", "draw"
        elif diff < 15.0:
            # Clear winner - 10-9
            winner = "fighter_a" if score_a > score_b else "fighter_b"
            if winner == "fighter_a":
                return "10-9", "fighter_a"
            else:
                return "9-10", "fighter_b"
        elif diff < 30.0:
            # Dominant round - 10-8
            winner = "fighter_a" if score_a > score_b else "fighter_b"
            if winner == "fighter_a":
                return "10-8", "fighter_a"
            else:
                return "8-10", "fighter_b"
        else:
            # Overwhelming dominance - 10-7
            winner = "fighter_a" if score_a > score_b else "fighter_b"
            if winner == "fighter_a":
                return "10-7", "fighter_a"
            else:
                return "7-10", "fighter_b"
    
    def _calculate_confidence(self, events: List[CombatEvent], score_a: float, score_b: float) -> float:
        """
        Calculate confidence in score
        Based on:
        - Number of events
        - Average event confidence
        - Score margin
        """
        if not events:
            return 0.5
        
        # Event count confidence (more events = higher confidence)
        event_count_confidence = min(len(events) / 20.0, 1.0)
        
        # Average event confidence
        avg_confidence = sum(e.confidence for e in events) / len(events)
        
        # Score margin confidence (larger margin = higher confidence)
        diff = abs(score_a - score_b)
        margin_confidence = min(diff / 30.0, 1.0)
        
        # Weighted combination
        total_confidence = (
            event_count_confidence * 0.3 +
            avg_confidence * 0.5 +
            margin_confidence * 0.2
        )
        
        return round(total_confidence, 3)
