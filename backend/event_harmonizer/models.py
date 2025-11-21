"""
Event Harmonizer - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent, EventType, EventSource


class ConflictType(str, Enum):
    """Type of event conflict"""
    SEVERITY_MISMATCH = "severity_mismatch"
    TYPE_CONTRADICTION = "type_contradiction"
    TIMESTAMP_PROXIMITY = "timestamp_proximity"
    DUPLICATE = "duplicate"
    NO_CONFLICT = "no_conflict"


class ResolutionStrategy(str, Enum):
    """Conflict resolution strategy"""
    JUDGE_OVERRIDE = "judge_override"  # Judge always wins
    CV_PRIORITY = "cv_priority"  # CV wins (high confidence)
    WEIGHTED_CONFIDENCE = "weighted_confidence"  # Confidence-based
    HYBRID = "hybrid"  # Merge both
    SEVERITY_PRIORITY = "severity_priority"  # Higher severity wins


class ConflictAnalysis(BaseModel):
    """Analysis of event conflict"""
    conflict_id: str
    conflict_type: ConflictType
    
    # Conflicting events
    judge_event: Optional[CombatEvent] = None
    cv_event: Optional[CombatEvent] = None
    
    # Analysis
    time_diff_ms: float
    severity_diff: float
    confidence_diff: float
    
    # Resolution
    resolution_strategy: ResolutionStrategy
    confidence_score: float
    
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HarmonizedEvent(BaseModel):
    """Harmonized event output"""
    harmonized_event: CombatEvent
    
    # Metadata
    source_events: List[str] = Field(description="IDs of source events")
    conflict_resolved: bool
    resolution_strategy: Optional[ResolutionStrategy] = None
    confidence_adjustment: float = 0.0
    
    harmonized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HarmonizerStats(BaseModel):
    """Harmonizer statistics"""
    total_events_processed: int
    conflicts_detected: int
    conflicts_by_type: dict
    resolutions_by_strategy: dict
    
    judge_overrides: int
    cv_priorities: int
    hybrid_merges: int
    
    avg_confidence_adjustment: float
