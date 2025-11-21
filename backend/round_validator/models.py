"""
Round Validator - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone
from enum import Enum


class ValidationIssueType(str, Enum):
    MISSING_JUDGE_EVENTS = "missing_judge_events"
    CV_FEED_INACTIVE = "cv_feed_inactive"
    TIMECODE_MISMATCH = "timecode_mismatch"
    JUDGE_INACTIVITY = "judge_inactivity"
    INSUFFICIENT_EVENTS = "insufficient_events"
    TIMING_ANOMALY = "timing_anomaly"


class ValidationSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Single validation issue"""
    issue_type: ValidationIssueType
    severity: ValidationSeverity
    message: str
    details: Dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RoundValidationResult(BaseModel):
    """Complete round validation result"""
    round_id: str
    bout_id: str
    round_num: int
    
    # Overall status
    valid: bool
    requires_supervisor_review: bool
    can_lock: bool
    
    # Issues found
    issues: List[ValidationIssue] = Field(default_factory=list)
    warnings: int = 0
    errors: int = 0
    critical_issues: int = 0
    
    # Statistics
    total_events: int = 0
    judge_events: int = 0
    cv_events: int = 0
    
    # Checks performed
    checks_passed: int = 0
    checks_failed: int = 0
    
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValidationConfig(BaseModel):
    """Validation configuration"""
    # Minimum events required
    min_total_events: int = 5
    min_judge_events: int = 2
    
    # Inactivity thresholds (seconds)
    max_judge_inactivity_sec: int = 60
    max_cv_inactivity_sec: int = 30
    
    # Timecode tolerance (ms)
    timecode_tolerance_ms: int = 5000
    
    # Round duration (seconds)
    expected_round_duration_sec: int = 300  # 5 minutes
    duration_tolerance_sec: int = 30
