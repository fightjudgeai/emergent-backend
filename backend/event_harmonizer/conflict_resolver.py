"""
Event Harmonizer - Conflict Resolution Logic
"""

from typing import Optional, Tuple, List
import logging
import uuid
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent, EventType, EventSource
from .models import (
    ConflictType, ResolutionStrategy, ConflictAnalysis, HarmonizedEvent
)

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Resolve conflicts between judge and CV events"""
    
    def __init__(
        self,
        proximity_window_ms: int = 200,
        judge_override_threshold: float = 0.8,
        cv_confidence_threshold: float = 0.9
    ):
        self.proximity_window_ms = proximity_window_ms
        self.judge_override_threshold = judge_override_threshold
        self.cv_confidence_threshold = cv_confidence_threshold
    
    def detect_conflict(
        self,
        judge_event: Optional[CombatEvent],
        cv_event: Optional[CombatEvent]
    ) -> Tuple[ConflictType, ConflictAnalysis]:
        """
        Detect and analyze conflict between events
        
        Returns:
            (conflict_type, analysis)
        """
        if not judge_event or not cv_event:
            return ConflictType.NO_CONFLICT, None
        
        # Check timestamp proximity
        time_diff = abs(judge_event.timestamp_ms - cv_event.timestamp_ms)
        
        if time_diff > self.proximity_window_ms:
            return ConflictType.NO_CONFLICT, None
        
        # Events are within proximity - analyze conflict
        severity_diff = abs(judge_event.severity - cv_event.severity)
        confidence_diff = abs(judge_event.confidence - cv_event.confidence)
        
        # Determine conflict type
        conflict_type = self._classify_conflict(judge_event, cv_event)
        
        # Create analysis
        analysis = ConflictAnalysis(
            conflict_id=str(uuid.uuid4()),
            conflict_type=conflict_type,
            judge_event=judge_event,
            cv_event=cv_event,
            time_diff_ms=time_diff,
            severity_diff=severity_diff,
            confidence_diff=confidence_diff,
            resolution_strategy=self._select_resolution_strategy(
                conflict_type, judge_event, cv_event
            ),
            confidence_score=min(judge_event.confidence, cv_event.confidence)
        )
        
        return conflict_type, analysis
    
    def _classify_conflict(
        self,
        judge_event: CombatEvent,
        cv_event: CombatEvent
    ) -> ConflictType:
        """Classify type of conflict"""
        # Same fighter?
        if judge_event.fighter_id != cv_event.fighter_id:
            return ConflictType.NO_CONFLICT
        
        # Duplicate detection
        if judge_event.event_type == cv_event.event_type:
            return ConflictType.DUPLICATE
        
        # Type contradiction (e.g., KD_flash vs KD_hard)
        if self._are_contradicting_types(judge_event.event_type, cv_event.event_type):
            return ConflictType.TYPE_CONTRADICTION
        
        # Severity mismatch
        severity_diff = abs(judge_event.severity - cv_event.severity)
        if severity_diff > 0.3:
            return ConflictType.SEVERITY_MISMATCH
        
        # Close proximity
        return ConflictType.TIMESTAMP_PROXIMITY
    
    def _are_contradicting_types(self, type1: EventType, type2: EventType) -> bool:
        """Check if event types contradict each other"""
        # KD tiers contradict each other
        kd_types = {EventType.KD_FLASH, EventType.KD_HARD, EventType.KD_NF}
        if type1 in kd_types and type2 in kd_types:
            return type1 != type2
        
        # Strike types can coexist
        return False
    
    def _select_resolution_strategy(
        self,
        conflict_type: ConflictType,
        judge_event: CombatEvent,
        cv_event: CombatEvent
    ) -> ResolutionStrategy:
        """Select appropriate resolution strategy"""
        # Judge override rules
        if judge_event.confidence >= self.judge_override_threshold:
            return ResolutionStrategy.JUDGE_OVERRIDE
        
        # CV priority for high confidence
        if cv_event.confidence >= self.cv_confidence_threshold:
            return ResolutionStrategy.CV_PRIORITY
        
        # Type contradiction - use severity priority
        if conflict_type == ConflictType.TYPE_CONTRADICTION:
            return ResolutionStrategy.SEVERITY_PRIORITY
        
        # Duplicates - use weighted confidence
        if conflict_type == ConflictType.DUPLICATE:
            return ResolutionStrategy.WEIGHTED_CONFIDENCE
        
        # Default: hybrid merge
        return ResolutionStrategy.HYBRID
    
    def resolve_conflict(
        self,
        analysis: ConflictAnalysis
    ) -> HarmonizedEvent:
        """
        Resolve conflict and create harmonized event
        
        Returns:
            HarmonizedEvent
        """
        judge_event = analysis.judge_event
        cv_event = analysis.cv_event
        strategy = analysis.resolution_strategy
        
        # Apply resolution strategy
        if strategy == ResolutionStrategy.JUDGE_OVERRIDE:
            harmonized = self._judge_override(judge_event, cv_event)
        
        elif strategy == ResolutionStrategy.CV_PRIORITY:
            harmonized = self._cv_priority(judge_event, cv_event)
        
        elif strategy == ResolutionStrategy.SEVERITY_PRIORITY:
            harmonized = self._severity_priority(judge_event, cv_event)
        
        elif strategy == ResolutionStrategy.WEIGHTED_CONFIDENCE:
            harmonized = self._weighted_confidence(judge_event, cv_event)
        
        elif strategy == ResolutionStrategy.HYBRID:
            harmonized = self._hybrid_merge(judge_event, cv_event)
        
        else:
            harmonized = judge_event  # Fallback
        
        # Calculate confidence adjustment
        original_conf = (judge_event.confidence + cv_event.confidence) / 2
        confidence_adjustment = harmonized.confidence - original_conf
        
        return HarmonizedEvent(
            harmonized_event=harmonized,
            source_events=[judge_event.event_id, cv_event.event_id],
            conflict_resolved=True,
            resolution_strategy=strategy,
            confidence_adjustment=confidence_adjustment
        )
    
    def _judge_override(self, judge_event: CombatEvent, cv_event: CombatEvent) -> CombatEvent:
        """Judge overrides CV"""
        event = judge_event.model_copy(deep=True)
        event.metadata["resolution"] = "judge_override"
        event.metadata["cv_event_id"] = cv_event.event_id
        return event
    
    def _cv_priority(self, judge_event: CombatEvent, cv_event: CombatEvent) -> CombatEvent:
        """CV takes priority"""
        event = cv_event.model_copy(deep=True)
        event.metadata["resolution"] = "cv_priority"
        event.metadata["judge_event_id"] = judge_event.event_id
        return event
    
    def _severity_priority(self, judge_event: CombatEvent, cv_event: CombatEvent) -> CombatEvent:
        """Higher severity wins"""
        winner = judge_event if judge_event.severity > cv_event.severity else cv_event
        event = winner.model_copy(deep=True)
        event.metadata["resolution"] = "severity_priority"
        return event
    
    def _weighted_confidence(self, judge_event: CombatEvent, cv_event: CombatEvent) -> CombatEvent:
        """Weighted average based on confidence"""
        total_conf = judge_event.confidence + cv_event.confidence
        judge_weight = judge_event.confidence / total_conf
        cv_weight = cv_event.confidence / total_conf
        
        # Average severity
        avg_severity = (
            judge_event.severity * judge_weight +
            cv_event.severity * cv_weight
        )
        
        # Use higher confidence event as base
        base_event = judge_event if judge_event.confidence > cv_event.confidence else cv_event
        event = base_event.model_copy(deep=True)
        event.severity = avg_severity
        event.confidence = (judge_event.confidence + cv_event.confidence) / 2
        event.metadata["resolution"] = "weighted_confidence"
        
        return event
    
    def _hybrid_merge(self, judge_event: CombatEvent, cv_event: CombatEvent) -> CombatEvent:
        """Hybrid merge of both events"""
        # Use judge event as base
        event = judge_event.model_copy(deep=True)
        
        # Adjust severity (weighted average)
        event.severity = (
            judge_event.severity * 0.6 +  # Judge gets 60% weight
            cv_event.severity * 0.4
        )
        
        # Boost confidence (both sources agree)
        event.confidence = min(
            (judge_event.confidence + cv_event.confidence) / 2 * 1.1,
            1.0
        )
        
        event.metadata["resolution"] = "hybrid_merge"
        event.metadata["cv_severity"] = cv_event.severity
        event.metadata["cv_confidence"] = cv_event.confidence
        
        return event
