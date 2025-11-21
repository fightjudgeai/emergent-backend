"""
CV Analytics Engine - Temporal Smoothing
Rolling window smoothing and optical flow validation
"""

from typing import Optional, List
from collections import deque
import logging
from .models import RawCVInput

logger = logging.getLogger(__name__)


class TemporalSmoother:
    """Smooth CV detections over time"""
    
    def __init__(self, window_size: int = 5, confidence_threshold: float = 0.6):
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold
        self.frame_buffer: deque = deque(maxlen=window_size)
    
    def smooth(self, raw_input: RawCVInput) -> Optional[RawCVInput]:
        """
        Apply temporal smoothing
        
        Returns:
            Smoothed input or None if too noisy
        """
        # Add to buffer
        self.frame_buffer.append(raw_input)
        
        if len(self.frame_buffer) < self.window_size:
            return None  # Need full window
        
        # Check consistency across window
        action_counts = {}
        for frame in self.frame_buffer:
            action = frame.action_type.value
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Get most common action
        most_common_action = max(action_counts, key=action_counts.get)
        consistency = action_counts[most_common_action] / self.window_size
        
        # Require at least 60% consistency
        if consistency < 0.6:
            logger.debug(f"Low consistency: {consistency:.2f}")
            return None
        
        # Validate optical flow
        if not self._validate_optical_flow(raw_input):
            logger.debug("Optical flow validation failed")
            return None
        
        # Average confidence across window
        avg_confidence = sum(
            max(frame.action_logits.values()) for frame in self.frame_buffer
        ) / len(self.frame_buffer)
        
        if avg_confidence < self.confidence_threshold:
            logger.debug(f"Low confidence: {avg_confidence:.2f}")
            return None
        
        # Return smoothed input (use most recent frame with averaged confidence)
        smoothed = raw_input.model_copy(deep=True)
        for action, logit in smoothed.action_logits.items():
            smoothed.action_logits[action] = avg_confidence
        
        return smoothed
    
    def _validate_optical_flow(self, raw_input: RawCVInput) -> bool:
        """
        Validate motion vectors are consistent with action
        """
        if not raw_input.motion_vectors:
            return True  # No flow data, skip validation
        
        magnitude = raw_input.motion_vectors.get("magnitude", 0.0)
        
        # High-impact actions should have significant motion
        if raw_input.impact_detected and raw_input.impact_level:
            if raw_input.impact_level.value in ["heavy", "critical"]:
                return magnitude > 3.0  # Threshold for significant motion
        
        return True
