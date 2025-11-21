"""
Fight Judge AI - Event Processing Pipeline
Deduplication, confidence filtering, multi-camera fusion, momentum detection
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
import logging
import hashlib
from collections import defaultdict
from .models import CombatEvent, EventType, EventSource

logger = logging.getLogger(__name__)


class EventPipeline:
    """Process and validate combat events"""
    
    def __init__(
        self,
        dedup_window_ms: int = 100,
        confidence_threshold: float = 0.5,
        momentum_window_ms: int = 1200,
        momentum_strike_threshold: int = 3
    ):
        self.dedup_window_ms = dedup_window_ms
        self.confidence_threshold = confidence_threshold
        self.momentum_window_ms = momentum_window_ms
        self.momentum_strike_threshold = momentum_strike_threshold
        
        self.processed_events: List[CombatEvent] = []
        self.stats = {
            "total_processed": 0,
            "rejected_low_confidence": 0,
            "rejected_duplicates": 0,
            "momentum_swings_detected": 0,
            "multicam_fusions": 0
        }
    
    def process_event(self, event: CombatEvent) -> Tuple[bool, str]:
        """
        Process single event through pipeline
        
        Returns:
            (accepted: bool, reason: str)
        """
        # Step 1: Confidence filtering
        if event.confidence < self.confidence_threshold:
            self.stats["rejected_low_confidence"] += 1
            return False, f"Low confidence: {event.confidence:.2f}"
        
        # Step 2: Deduplication
        if self._is_duplicate(event):
            self.stats["rejected_duplicates"] += 1
            return False, "Duplicate event"
        
        # Step 3: Mark as processed
        event.deduplicated = True
        event.processed_at = datetime.now(timezone.utc)
        
        # Step 4: Add to processed events
        self.processed_events.append(event)
        self.stats["total_processed"] += 1
        
        return True, "Event accepted"
    
    def _is_duplicate(self, event: CombatEvent) -> bool:
        """Check if event is duplicate within time window"""
        for processed in reversed(self.processed_events[-50:]):  # Check last 50 events
            # Same fighter, same event type
            if (
                processed.fighter_id == event.fighter_id and
                processed.event_type == event.event_type
            ):
                # Check time window
                time_diff = abs(event.timestamp_ms - processed.timestamp_ms)
                if time_diff < self.dedup_window_ms:
                    return True
        return False
    
    def fuse_multicamera_events(
        self,
        events: List[CombatEvent],
        fusion_window_ms: int = 150
    ) -> List[CombatEvent]:
        """
        Fuse multi-camera events into canonical events
        Groups events by time window and selects highest confidence
        """
        if not events:
            return []
        
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp_ms)
        
        # Group events by time window
        groups: List[List[CombatEvent]] = []
        current_group = [sorted_events[0]]
        
        for event in sorted_events[1:]:
            time_diff = event.timestamp_ms - current_group[0].timestamp_ms
            
            if time_diff < fusion_window_ms:
                # Same window - check if similar event
                if self._events_similar(event, current_group[0]):
                    current_group.append(event)
                else:
                    # Different event - start new group
                    groups.append(current_group)
                    current_group = [event]
            else:
                # New window - start new group
                groups.append(current_group)
                current_group = [event]
        
        groups.append(current_group)
        
        # Select canonical event from each group
        canonical_events = []
        for group in groups:
            if len(group) == 1:
                canonical_events.append(group[0])
            else:
                # Multi-camera - select highest confidence with angle weighting
                canonical = self._select_canonical(group)
                canonical.canonical = True
                canonical_events.append(canonical)
                self.stats["multicam_fusions"] += 1
        
        return canonical_events
    
    def _events_similar(self, e1: CombatEvent, e2: CombatEvent) -> bool:
        """Check if two events are similar (same fighter, same type)"""
        return (
            e1.fighter_id == e2.fighter_id and
            e1.event_type == e2.event_type
        )
    
    def _select_canonical(self, events: List[CombatEvent]) -> CombatEvent:
        """
        Select canonical event from multi-camera group
        Uses confidence + angle weighting
        """
        # Angle weighting: front angles (45-135°, 225-315°) preferred
        def angle_weight(angle: Optional[float]) -> float:
            if angle is None:
                return 0.8
            # Normalize angle to 0-360
            angle = angle % 360
            # Front angles get higher weight
            if (45 <= angle <= 135) or (225 <= angle <= 315):
                return 1.0
            return 0.7
        
        # Score each event: confidence * angle_weight
        scored_events = [
            (event, event.confidence * angle_weight(event.angle))
            for event in events
        ]
        
        # Return highest scored event
        return max(scored_events, key=lambda x: x[1])[0]
    
    def detect_momentum_swings(
        self,
        events: List[CombatEvent],
        fighter_id: str
    ) -> List[CombatEvent]:
        """
        Detect momentum swing events
        Criteria: ≥3 significant strikes in <1.2s OR heavy damage cluster
        """
        momentum_events = []
        
        # Filter to striking events for this fighter
        striking_events = [
            e for e in events
            if e.fighter_id == fighter_id and
            e.event_type in [EventType.STRIKE_SIG, EventType.STRIKE_HIGHIMPACT]
        ]
        
        if len(striking_events) < self.momentum_strike_threshold:
            return momentum_events
        
        # Sort by timestamp
        striking_events.sort(key=lambda e: e.timestamp_ms)
        
        # Sliding window to detect flurries
        for i in range(len(striking_events) - self.momentum_strike_threshold + 1):
            window = striking_events[i:i + self.momentum_strike_threshold]
            
            # Check if all strikes within time window
            time_span = window[-1].timestamp_ms - window[0].timestamp_ms
            
            if time_span < self.momentum_window_ms:
                # Flurry detected - create momentum event
                avg_severity = sum(e.severity for e in window) / len(window)
                avg_confidence = sum(e.confidence for e in window) / len(window)
                
                momentum_event = CombatEvent(
                    bout_id=window[0].bout_id,
                    round_id=window[0].round_id,
                    fighter_id=fighter_id,
                    event_type=EventType.MOMENTUM_SWING,
                    severity=min(avg_severity * 1.2, 1.0),  # Boost severity
                    confidence=avg_confidence,
                    timestamp_ms=window[-1].timestamp_ms,
                    source=EventSource.ANALYTICS,
                    metadata={
                        "strikes_in_flurry": len(window),
                        "time_span_ms": time_span,
                        "trigger": "flurry"
                    }
                )
                
                momentum_events.append(momentum_event)
                self.stats["momentum_swings_detected"] += 1
                
                # Skip ahead to avoid overlapping momentum events
                i += self.momentum_strike_threshold
        
        return momentum_events
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics"""
        return self.stats.copy()
