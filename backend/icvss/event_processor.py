"""
ICVSS Event Processing Pipeline
- Deduplication (80-150ms window)
- Confidence filtering
- Normalization
"""

from typing import List, Dict, Tuple
from datetime import datetime, timezone
import logging
from .models import CVEvent, EventSource

logger = logging.getLogger(__name__)


class EventProcessor:
    """Process and deduplicate CV events"""
    
    def __init__(self, 
                 dedup_window_ms: int = 100,
                 confidence_threshold: float = 0.6):
        """
        Args:
            dedup_window_ms: Deduplication window in milliseconds (80-150)
            confidence_threshold: Minimum confidence to accept events
        """
        self.dedup_window_ms = dedup_window_ms
        self.confidence_threshold = confidence_threshold
        self.processed_events: List[CVEvent] = []
    
    def process_event(self, event: CVEvent) -> Tuple[bool, str]:
        """
        Process a single event through the pipeline
        
        Returns:
            (accepted: bool, reason: str)
        """
        # Step 1: Confidence check
        if event.confidence < self.confidence_threshold:
            logger.info(f"Event {event.event_id} rejected: confidence {event.confidence:.2f} < threshold {self.confidence_threshold}")
            return False, f"Low confidence: {event.confidence:.2f}"
        
        # Step 2: Deduplication check
        if self._is_duplicate(event):
            logger.info(f"Event {event.event_id} rejected: duplicate within {self.dedup_window_ms}ms window")
            return False, "Duplicate event"
        
        # Step 3: Normalize event
        normalized_event = self._normalize_event(event)
        
        # Step 4: Mark as processed
        normalized_event.deduplicated = True
        normalized_event.processed_at = datetime.now(timezone.utc)
        
        # Step 5: Add to processed events
        self.processed_events.append(normalized_event)
        
        logger.info(f"Event {event.event_id} accepted: {event.event_type} for {event.fighter_id} at {event.timestamp_ms}ms")
        return True, "Accepted"
    
    def process_batch(self, events: List[CVEvent]) -> Tuple[List[CVEvent], List[Dict]]:
        """
        Process a batch of events
        
        Returns:
            (accepted_events, rejected_events)
        """
        accepted = []
        rejected = []
        
        for event in events:
            is_accepted, reason = self.process_event(event)
            
            if is_accepted:
                accepted.append(event)
            else:
                rejected.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "reason": reason,
                    "timestamp_ms": event.timestamp_ms
                })
        
        logger.info(f"Batch processed: {len(accepted)} accepted, {len(rejected)} rejected")
        return accepted, rejected
    
    def _is_duplicate(self, new_event: CVEvent) -> bool:
        """
        Check if event is a duplicate within the deduplication window
        
        Duplicate criteria:
        - Same fighter_id
        - Same event_type
        - Within dedup_window_ms milliseconds
        """
        for existing_event in reversed(self.processed_events[-50:]):  # Check last 50 events
            # Check time window
            time_diff = abs(new_event.timestamp_ms - existing_event.timestamp_ms)
            if time_diff > self.dedup_window_ms:
                continue  # Outside window
            
            # Check if same fighter and event type
            if (existing_event.fighter_id == new_event.fighter_id and
                existing_event.event_type == new_event.event_type):
                logger.debug(f"Duplicate found: {new_event.event_type} within {time_diff}ms")
                return True
        
        return False
    
    def _normalize_event(self, event: CVEvent) -> CVEvent:
        """
        Normalize event into canonical schema
        
        Handles:
        - Vendor-specific field mappings
        - Severity normalization
        - Position standardization
        """
        # Normalize severity to 0-1 range if needed
        if event.severity > 1.0:
            event.severity = event.severity / 100.0  # Convert percentage
        
        # Ensure metadata exists
        if event.metadata is None:
            event.metadata = {}
        
        # Add normalized flag
        event.metadata["normalized"] = True
        event.metadata["processor_version"] = "1.0.0"
        
        return event
    
    def get_events_for_round(self, bout_id: str, round_id: str) -> List[CVEvent]:
        """
        Get all processed events for a specific round
        """
        return [
            event for event in self.processed_events
            if event.bout_id == bout_id and event.round_id == round_id
        ]
    
    def clear_old_events(self, keep_last_n: int = 1000):
        """
        Clear old events to prevent memory buildup
        Keeps only the last N events
        """
        if len(self.processed_events) > keep_last_n:
            removed = len(self.processed_events) - keep_last_n
            self.processed_events = self.processed_events[-keep_last_n:]
            logger.info(f"Cleared {removed} old events from memory")
    
    def get_stats(self) -> Dict:
        """
        Get processor statistics
        """
        return {
            "total_processed": len(self.processed_events),
            "dedup_window_ms": self.dedup_window_ms,
            "confidence_threshold": self.confidence_threshold
        }


class EventNormalizer:
    """Normalize events from different CV vendors"""
    
    # Vendor-specific event type mappings
    VENDOR_MAPPINGS = {
        "vendor_a": {
            "punch_jab": "strike_jab",
            "punch_straight": "strike_cross",
            "knockdown": "KD_hard"
        },
        "vendor_b": {
            "jab_detected": "strike_jab",
            "cross_detected": "strike_cross",
            "kd_event": "KD_hard"
        }
    }
    
    @classmethod
    def normalize_from_vendor(cls, vendor_id: str, raw_data: Dict) -> CVEvent:
        """
        Convert vendor-specific format to CVEvent
        
        Args:
            vendor_id: CV vendor identifier
            raw_data: Raw event data from vendor
        
        Returns:
            Normalized CVEvent
        """
        # Get vendor mapping
        mapping = cls.VENDOR_MAPPINGS.get(vendor_id, {})
        
        # Map event type
        raw_event_type = raw_data.get("event_type", raw_data.get("type"))
        event_type = mapping.get(raw_event_type, raw_event_type)
        
        # Create normalized event
        return CVEvent(
            bout_id=raw_data["bout_id"],
            round_id=raw_data["round_id"],
            fighter_id=raw_data["fighter_id"],
            event_type=event_type,
            severity=raw_data.get("severity", raw_data.get("impact", 0.5)),
            confidence=raw_data.get("confidence", raw_data.get("certainty", 0.7)),
            position=raw_data.get("position", "distance"),
            timestamp_ms=raw_data["timestamp_ms"],
            source=EventSource.CV_SYSTEM,
            vendor_id=vendor_id,
            metadata=raw_data.get("metadata", {})
        )
