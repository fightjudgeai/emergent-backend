"""
Event Harmonizer - Main Engine
Process CV and judge event streams in real-time
"""

import asyncio
from typing import List, Optional, Dict
import logging
from collections import deque
from datetime import datetime, timezone
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent, EventSource
from .conflict_resolver import ConflictResolver
from .models import HarmonizedEvent, HarmonizerStats

logger = logging.getLogger(__name__)


class EventHarmonizerEngine:
    """Main event harmonization engine"""
    
    def __init__(self, buffer_size: int = 100):
        self.conflict_resolver = ConflictResolver()
        
        # Event buffers
        self.judge_events = deque(maxlen=buffer_size)
        self.cv_events = deque(maxlen=buffer_size)
        self.harmonized_events = []
        
        # Stats
        self.stats = {
            "total_processed": 0,
            "conflicts_detected": 0,
            "judge_overrides": 0,
            "cv_priorities": 0,
            "hybrid_merges": 0,
            "conflicts_by_type": {},
            "resolutions_by_strategy": {}
        }
        
        # Output callback
        self.output_callback = None
    
    def set_output_callback(self, callback):
        """Set callback for harmonized events"""
        self.output_callback = callback
    
    async def process_judge_event(self, event: CombatEvent):
        """
        Process incoming judge event
        
        Args:
            event: Judge event
        """
        self.judge_events.append(event)
        await self._harmonize_event(event, EventSource.MANUAL)
    
    async def process_cv_event(self, event: CombatEvent):
        """
        Process incoming CV event
        
        Args:
            event: CV event
        """
        self.cv_events.append(event)
        await self._harmonize_event(event, EventSource.CV_SYSTEM)
    
    async def _harmonize_event(self, new_event: CombatEvent, source: EventSource):
        """
        Harmonize new event with existing events
        
        Args:
            new_event: Incoming event
            source: Event source
        """
        self.stats["total_processed"] += 1
        
        # Find potential conflicts
        if source == EventSource.MANUAL:
            # Judge event - check against recent CV events
            conflicts = self._find_conflicts(new_event, list(self.cv_events))
        else:
            # CV event - check against recent judge events
            conflicts = self._find_conflicts(new_event, list(self.judge_events))
        
        if conflicts:
            # Resolve conflicts
            for conflicting_event in conflicts:
                await self._resolve_and_emit(new_event, conflicting_event, source)
        else:
            # No conflict - emit as is
            harmonized = HarmonizedEvent(
                harmonized_event=new_event,
                source_events=[new_event.event_id],
                conflict_resolved=False
            )
            await self._emit_harmonized_event(harmonized)
    
    def _find_conflicts(
        self,
        new_event: CombatEvent,
        event_buffer: List[CombatEvent]
    ) -> List[CombatEvent]:
        """
        Find conflicting events in buffer
        
        Returns:
            List of conflicting events
        """
        conflicts = []
        
        for existing_event in event_buffer:
            # Check proximity
            time_diff = abs(new_event.timestamp_ms - existing_event.timestamp_ms)
            
            if time_diff <= self.conflict_resolver.proximity_window_ms:
                # Same fighter?
                if new_event.fighter_id == existing_event.fighter_id:
                    conflicts.append(existing_event)
        
        return conflicts
    
    async def _resolve_and_emit(
        self,
        event1: CombatEvent,
        event2: CombatEvent,
        source: EventSource
    ):
        """
        Resolve conflict and emit harmonized event
        
        Args:
            event1: New event
            event2: Conflicting event
            source: Source of new event
        """
        # Determine which is judge vs CV
        if source == EventSource.MANUAL:
            judge_event = event1
            cv_event = event2
        else:
            judge_event = event2
            cv_event = event1
        
        # Detect and analyze conflict
        conflict_type, analysis = self.conflict_resolver.detect_conflict(
            judge_event, cv_event
        )
        
        if conflict_type.value != "no_conflict":
            self.stats["conflicts_detected"] += 1
            
            # Track conflict type
            self.stats["conflicts_by_type"][conflict_type.value] = \
                self.stats["conflicts_by_type"].get(conflict_type.value, 0) + 1
            
            # Resolve conflict
            harmonized = self.conflict_resolver.resolve_conflict(analysis)
            
            # Track resolution strategy
            strategy = harmonized.resolution_strategy.value
            self.stats["resolutions_by_strategy"][strategy] = \
                self.stats["resolutions_by_strategy"].get(strategy, 0) + 1
            
            # Update specific stats
            if strategy == "judge_override":
                self.stats["judge_overrides"] += 1
            elif strategy == "cv_priority":
                self.stats["cv_priorities"] += 1
            elif strategy == "hybrid":
                self.stats["hybrid_merges"] += 1
            
            await self._emit_harmonized_event(harmonized)
            
            logger.info(f"Conflict resolved: {conflict_type.value} using {strategy}")
    
    async def _emit_harmonized_event(self, harmonized: HarmonizedEvent):
        """
        Emit harmonized event to output
        
        Args:
            harmonized: Harmonized event
        """
        self.harmonized_events.append(harmonized)
        
        # Keep only recent events
        if len(self.harmonized_events) > 1000:
            self.harmonized_events = self.harmonized_events[-1000:]
        
        # Send to callback
        if self.output_callback:
            await self.output_callback(harmonized)
    
    def get_stats(self) -> HarmonizerStats:
        """Get harmonizer statistics"""
        return HarmonizerStats(
            total_events_processed=self.stats["total_processed"],
            conflicts_detected=self.stats["conflicts_detected"],
            conflicts_by_type=self.stats["conflicts_by_type"],
            resolutions_by_strategy=self.stats["resolutions_by_strategy"],
            judge_overrides=self.stats["judge_overrides"],
            cv_priorities=self.stats["cv_priorities"],
            hybrid_merges=self.stats["hybrid_merges"],
            avg_confidence_adjustment=0.0  # TODO: Calculate
        )
