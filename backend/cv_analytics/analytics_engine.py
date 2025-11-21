"""
CV Analytics Engine - Main Processing Engine
Converts raw CV data into standardized combat events
"""

from typing import List, Optional
import logging
from datetime import datetime, timezone
import sys
sys.path.append('/app/backend')

from fjai.models import CombatEvent, EventType, EventSource
from .models import RawCVInput, ImpactLevel, ActionType, AnalyticsOutput
from .temporal_smoothing import TemporalSmoother
from .multicam_fusion import MultiCameraFusion

logger = logging.getLogger(__name__)


class CVAnalyticsEngine:
    """Convert raw CV outputs to standardized combat events"""
    
    def __init__(self):
        self.temporal_smoother = TemporalSmoother()
        self.multicam_fusion = MultiCameraFusion()
        
        # Analytics state
        self.recent_strikes = []  # Track for flurry detection
        self.control_start_time = None
        self.cumulative_damage = {"fighter_a": 0.0, "fighter_b": 0.0}
    
    def process_raw_input(self, raw_input: RawCVInput, bout_id: str, round_id: str) -> List[CombatEvent]:
        """
        Process single raw CV input frame
        
        Returns:
            List of standardized CombatEvent objects
        """
        events = []
        
        # Apply temporal smoothing
        smoothed = self.temporal_smoother.smooth(raw_input)
        if not smoothed:
            return events  # Too noisy, skip
        
        # Classify event type
        event_type = self._classify_event(smoothed)
        if not event_type:
            return events  # No significant event detected
        
        # Calculate severity
        severity = self._calculate_severity(smoothed)
        
        # Get confidence
        confidence = max(smoothed.action_logits.values())
        
        # Create combat event
        event = CombatEvent(
            bout_id=bout_id,
            round_id=round_id,
            fighter_id=smoothed.fighter_id,
            event_type=event_type,
            severity=severity,
            confidence=confidence,
            timestamp_ms=smoothed.timestamp_ms,
            source=EventSource.CV_SYSTEM,
            camera_id=smoothed.camera_id,
            position=self._estimate_octagon_position(smoothed),
            angle=smoothed.camera_angle,
            metadata={
                "frame_id": smoothed.frame_id,
                "impact_level": smoothed.impact_level.value if smoothed.impact_level else None,
                "motion_magnitude": smoothed.motion_vectors.get("magnitude") if smoothed.motion_vectors else None
            }
        )
        
        events.append(event)
        
        # Check for secondary events (e.g., momentum swings)
        if event_type in [EventType.STRIKE_SIG, EventType.STRIKE_HIGHIMPACT]:
            self.recent_strikes.append((smoothed.timestamp_ms, smoothed.fighter_id))
            momentum_event = self._check_momentum_swing(smoothed, bout_id, round_id)
            if momentum_event:
                events.append(momentum_event)
        
        # Track cumulative damage for rocked detection
        if event_type in [EventType.STRIKE_HIGHIMPACT, EventType.KD_FLASH, EventType.KD_HARD, EventType.KD_NF]:
            opponent = "fighter_b" if smoothed.fighter_id == "fighter_a" else "fighter_a"
            self.cumulative_damage[opponent] += severity
            
            # Check if opponent is rocked
            if self.cumulative_damage[opponent] > 0.7:
                rocked_event = CombatEvent(
                    bout_id=bout_id,
                    round_id=round_id,
                    fighter_id=opponent,
                    event_type=EventType.ROCKED,
                    severity=0.8,
                    confidence=0.85,
                    timestamp_ms=smoothed.timestamp_ms + 100,
                    source=EventSource.ANALYTICS,
                    metadata={"trigger": "cumulative_damage"}
                )
                events.append(rocked_event)
                self.cumulative_damage[opponent] = 0.0  # Reset
        
        return events
    
    def process_multicamera_batch(
        self,
        raw_inputs: List[RawCVInput],
        bout_id: str,
        round_id: str
    ) -> List[CombatEvent]:
        """
        Process batch of multi-camera inputs and fuse
        
        Returns:
            Fused list of CombatEvent objects
        """
        # Process each camera input
        all_events = []
        for raw_input in raw_inputs:
            events = self.process_raw_input(raw_input, bout_id, round_id)
            all_events.extend(events)
        
        # Apply multi-camera fusion
        fused_events = self.multicam_fusion.fuse_events(all_events)
        
        return fused_events
    
    def generate_analytics(self, events: List[CombatEvent], window_seconds: int = 60) -> AnalyticsOutput:
        """
        Generate analytics from event stream
        
        Args:
            events: List of recent combat events
            window_seconds: Time window for analysis
        
        Returns:
            AnalyticsOutput with pace, style, control metrics
        """
        if not events:
            return AnalyticsOutput(
                control_time_estimate=0.0,
                pace_score=0.5,
                tempo_pattern="low",
                fighter_style="unknown",
                cumulative_damage=0.0,
                rocked_probability=0.0
            )
        
        # Calculate control time
        control_events = [e for e in events if e.event_type in [EventType.CONTROL_START, EventType.CONTROL_END]]
        control_time = self._calculate_control_time(control_events)
        
        # Calculate pace
        strike_events = [e for e in events if "strike" in e.event_type.value.lower()]
        pace_score = min(len(strike_events) / 20.0, 1.0)  # Normalize to 0-1
        
        # Determine tempo pattern
        tempo_pattern = self._analyze_tempo(events)
        
        # Classify fighter style
        fighter_style = self._classify_fighter_style(events)
        
        # Damage indicators
        damage_events = [e for e in events if e.event_type in [
            EventType.KD_FLASH, EventType.KD_HARD, EventType.KD_NF,
            EventType.ROCKED, EventType.STRIKE_HIGHIMPACT
        ]]
        cumulative_damage = sum(e.severity for e in damage_events) / len(events) if events else 0.0
        
        # Rocked probability
        recent_damage = sum(e.severity for e in damage_events[-5:]) if len(damage_events) >= 5 else 0.0
        rocked_probability = min(recent_damage, 1.0)
        
        return AnalyticsOutput(
            control_time_estimate=control_time,
            pace_score=pace_score,
            tempo_pattern=tempo_pattern,
            fighter_style=fighter_style,
            cumulative_damage=cumulative_damage,
            rocked_probability=rocked_probability
        )
    
    def _classify_event(self, raw_input: RawCVInput) -> Optional[EventType]:
        """Classify raw CV input into standardized event type"""
        action = raw_input.action_type
        impact = raw_input.impact_level
        
        # Knockdown detection
        if action == ActionType.KNOCKDOWN:
            if impact == ImpactLevel.CRITICAL:
                return EventType.KD_NF
            elif impact == ImpactLevel.HEAVY:
                return EventType.KD_HARD
            else:
                return EventType.KD_FLASH
        
        # Strike classification
        if action in [ActionType.PUNCH, ActionType.KICK, ActionType.KNEE, ActionType.ELBOW]:
            if impact in [ImpactLevel.HEAVY, ImpactLevel.CRITICAL]:
                return EventType.STRIKE_HIGHIMPACT
            elif impact == ImpactLevel.MEDIUM:
                return EventType.STRIKE_SIG
            else:
                return None  # Light strikes not tracked
        
        # Grappling
        if action == ActionType.TAKEDOWN:
            return EventType.TD_LAND if raw_input.impact_detected else EventType.TD_ATTEMPT
        
        if action == ActionType.SUBMISSION:
            return EventType.SUB_ATTEMPT
        
        if action == ActionType.GROUND_CONTROL:
            return EventType.CONTROL_START
        
        if action == ActionType.STANDUP:
            return EventType.CONTROL_END
        
        return None
    
    def _calculate_severity(self, raw_input: RawCVInput) -> float:
        """Calculate event severity from raw input"""
        # Base severity from impact level
        impact_map = {
            ImpactLevel.LIGHT: 0.3,
            ImpactLevel.MEDIUM: 0.6,
            ImpactLevel.HEAVY: 0.8,
            ImpactLevel.CRITICAL: 1.0
        }
        
        base_severity = impact_map.get(raw_input.impact_level, 0.5)
        
        # Adjust based on motion vectors
        if raw_input.motion_vectors:
            magnitude = raw_input.motion_vectors.get("magnitude", 0.0)
            motion_boost = min(magnitude / 10.0, 0.2)  # Up to +0.2
            base_severity += motion_boost
        
        return min(base_severity, 1.0)
    
    def _estimate_octagon_position(self, raw_input: RawCVInput) -> str:
        """Estimate position in octagon from bbox"""
        # Simplified - use center of bbox
        if len(raw_input.fighter_bbox) >= 2:
            x, y = raw_input.fighter_bbox[0], raw_input.fighter_bbox[1]
            
            if x < 0.33:
                return "cage_left"
            elif x > 0.67:
                return "cage_right"
            else:
                return "center"
        return "unknown"
    
    def _check_momentum_swing(self, raw_input: RawCVInput, bout_id: str, round_id: str) -> Optional[CombatEvent]:
        """Check if recent strikes constitute a momentum swing"""
        # Clean old strikes (>1.5s ago)
        current_time = raw_input.timestamp_ms
        self.recent_strikes = [
            (ts, fid) for ts, fid in self.recent_strikes
            if current_time - ts < 1500
        ]
        
        # Count strikes by this fighter in window
        fighter_strikes = [fid for ts, fid in self.recent_strikes if fid == raw_input.fighter_id]
        
        # Momentum swing if ≥4 strikes in <1.5s
        if len(fighter_strikes) >= 4:
            return CombatEvent(
                bout_id=bout_id,
                round_id=round_id,
                fighter_id=raw_input.fighter_id,
                event_type=EventType.MOMENTUM_SWING,
                severity=0.7,
                confidence=0.88,
                timestamp_ms=current_time,
                source=EventSource.ANALYTICS,
                metadata={
                    "trigger": "flurry",
                    "strikes_in_window": len(fighter_strikes)
                }
            )
        
        return None
    
    def _calculate_control_time(self, control_events: List[CombatEvent]) -> float:
        """Calculate total control time from events"""
        total_time = 0.0
        control_start = None
        
        for event in sorted(control_events, key=lambda e: e.timestamp_ms):
            if event.event_type == EventType.CONTROL_START:
                control_start = event.timestamp_ms
            elif event.event_type == EventType.CONTROL_END and control_start:
                duration = (event.timestamp_ms - control_start) / 1000.0
                total_time += duration
                control_start = None
        
        return total_time
    
    def _analyze_tempo(self, events: List[CombatEvent]) -> str:
        """Analyze fight tempo pattern"""
        if len(events) < 5:
            return "low"
        
        # Calculate variance in event timing
        timestamps = sorted([e.timestamp_ms for e in events])
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        
        if not intervals:
            return "low"
        
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((x - avg_interval)**2 for x in intervals) / len(intervals)
        
        # Classify based on average pace and variance
        if avg_interval < 2000:  # <2s between events
            return "high" if variance < 1000000 else "variable"
        elif avg_interval < 5000:  # 2-5s
            return "medium"
        else:
            return "low"
    
    def _classify_fighter_style(self, events: List[CombatEvent]) -> str:
        """Classify fighter style based on event distribution"""
        if not events:
            return "unknown"
        
        strike_count = len([e for e in events if "strike" in e.event_type.value.lower()])
        grapple_count = len([e for e in events if e.event_type in [
            EventType.TD_LAND, EventType.TD_ATTEMPT, EventType.SUB_ATTEMPT, EventType.CONTROL_START
        ]])
        
        total = strike_count + grapple_count
        if total == 0:
            return "unknown"
        
        strike_ratio = strike_count / total
        
        if strike_ratio > 0.75:
            return "striker"
        elif strike_ratio < 0.25:
            return "grappler"
        elif grapple_count > strike_count * 0.5:
            return "wrestler"
        else:
            return "balanced"
