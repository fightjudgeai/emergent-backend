"""
CV Analytics Engine - Multi-Camera Fusion
Consensus detection and angle weighting
"""

from typing import List, Dict
import logging
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent

logger = logging.getLogger(__name__)


class MultiCameraFusion:
    """Fuse events from multiple cameras"""
    
    def __init__(self, fusion_window_ms: int = 150):
        self.fusion_window_ms = fusion_window_ms
    
    def fuse_events(self, events: List[CombatEvent]) -> List[CombatEvent]:
        """
        Fuse multi-camera events using consensus
        
        Args:
            events: List of events from all cameras
        
        Returns:
            Fused canonical events
        """
        if not events:
            return []
        
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp_ms)
        
        # Group events by time window
        groups = self._group_by_time_window(sorted_events)
        
        # Apply fusion to each group
        fused_events = []
        for group in groups:
            if len(group) == 1:
                fused_events.append(group[0])
            else:
                # Multi-camera group - apply fusion
                canonical = self._apply_consensus_fusion(group)
                fused_events.append(canonical)
        
        return fused_events
    
    def _group_by_time_window(self, events: List[CombatEvent]) -> List[List[CombatEvent]]:
        """Group events by time window"""
        groups = []
        current_group = [events[0]]
        
        for event in events[1:]:
            time_diff = event.timestamp_ms - current_group[0].timestamp_ms
            
            # Check if similar event in same window
            if time_diff < self.fusion_window_ms and self._events_similar(event, current_group[0]):
                current_group.append(event)
            else:
                groups.append(current_group)
                current_group = [event]
        
        groups.append(current_group)
        return groups
    
    def _events_similar(self, e1: CombatEvent, e2: CombatEvent) -> bool:
        """Check if events are similar (same fighter, same type)"""
        return (
            e1.fighter_id == e2.fighter_id and
            e1.event_type == e2.event_type
        )
    
    def _apply_consensus_fusion(self, events: List[CombatEvent]) -> CombatEvent:
        """
        Apply consensus fusion with angle weighting
        
        Selects event with best angle + confidence score
        """
        # Angle weighting function
        def angle_weight(angle: float) -> float:
            """Front angles (45-135°, 225-315°) preferred"""
            if angle is None:
                return 0.8
            angle = angle % 360
            if (45 <= angle <= 135) or (225 <= angle <= 315):
                return 1.0
            return 0.7
        
        # Score each event: confidence * severity * angle_weight
        scored_events = [
            (
                event,
                event.confidence * event.severity * angle_weight(event.angle)
            )
            for event in events
        ]
        
        # Select highest scored event
        canonical_event, _ = max(scored_events, key=lambda x: x[1])
        
        # Mark as canonical and aggregate confidence
        canonical_event.canonical = True
        canonical_event.confidence = sum(e.confidence for e in events) / len(events)
        canonical_event.metadata["camera_count"] = len(events)
        
        logger.info(f"Fused {len(events)} camera views for {canonical_event.event_type}")
        
        return canonical_event
