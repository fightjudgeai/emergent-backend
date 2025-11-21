"""
Round Validator - Validation Engine
"""

import sys
sys.path.append('/app/backend')
from typing import List, Optional, Tuple
import logging
from datetime import datetime, timezone
from fjai.models import CombatEvent, EventSource
from .models import (
    RoundValidationResult, ValidationIssue, ValidationIssueType,
    ValidationSeverity, ValidationConfig
)

logger = logging.getLogger(__name__)


class RoundValidatorEngine:
    """Validate rounds before scoring"""
    
    def __init__(self, config: ValidationConfig = None, postgres_session=None):
        self.config = config or ValidationConfig()
        self.postgres_session = postgres_session
        
        # In-memory cache for quick lookups
        self.validation_cache = {}
    
    def validate_round(
        self,
        round_id: str,
        bout_id: str,
        round_num: int,
        events: List[CombatEvent],
        round_start_time: Optional[int] = None,
        round_end_time: Optional[int] = None
    ) -> RoundValidationResult:
        """
        Perform complete round validation
        
        Args:
            round_id: Round identifier
            bout_id: Bout identifier
            round_num: Round number
            events: All round events
            round_start_time: Expected start timestamp (ms)
            round_end_time: Expected end timestamp (ms)
        
        Returns:
            RoundValidationResult
        """
        issues: List[ValidationIssue] = []
        
        # Separate events by source
        judge_events = [e for e in events if e.source == EventSource.MANUAL]
        cv_events = [e for e in events if e.source == EventSource.CV_SYSTEM]
        
        # Check 1: Minimum events
        issues.extend(self._check_minimum_events(events, judge_events))
        
        # Check 2: Judge inactivity
        issues.extend(self._check_judge_inactivity(judge_events))
        
        # Check 3: CV feed activity
        issues.extend(self._check_cv_feed_activity(cv_events))
        
        # Check 4: Timecode matching
        if round_start_time and round_end_time:
            issues.extend(self._check_timecodes(events, round_start_time, round_end_time))
        
        # Check 5: Round duration
        if round_start_time and round_end_time:
            issues.extend(self._check_round_duration(round_start_time, round_end_time))
        
        # Count severity levels
        warnings = len([i for i in issues if i.severity == ValidationSeverity.WARNING])
        errors = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        critical = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL])
        
        # Determine status
        valid = len(issues) == 0
        requires_review = errors > 0 or critical > 0
        can_lock = critical == 0  # Can lock if no critical issues
        
        checks_total = 5
        checks_failed = len(set(i.issue_type for i in issues))
        checks_passed = checks_total - checks_failed
        
        result = RoundValidationResult(
            round_id=round_id,
            bout_id=bout_id,
            round_num=round_num,
            valid=valid,
            requires_supervisor_review=requires_review,
            can_lock=can_lock,
            issues=issues,
            warnings=warnings,
            errors=errors,
            critical_issues=critical,
            total_events=len(events),
            judge_events=len(judge_events),
            cv_events=len(cv_events),
            checks_passed=checks_passed,
            checks_failed=checks_failed
        )
        
        logger.info(f"Round {round_id} validation: valid={valid}, can_lock={can_lock}, issues={len(issues)}")
        return result
    
    def _check_minimum_events(
        self,
        all_events: List[CombatEvent],
        judge_events: List[CombatEvent]
    ) -> List[ValidationIssue]:
        """Check minimum event requirements"""
        issues = []
        
        if len(all_events) < self.config.min_total_events:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.INSUFFICIENT_EVENTS,
                severity=ValidationSeverity.ERROR,
                message=f"Insufficient total events: {len(all_events)} < {self.config.min_total_events}",
                details={"total_events": len(all_events), "required": self.config.min_total_events}
            ))
        
        if len(judge_events) < self.config.min_judge_events:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.MISSING_JUDGE_EVENTS,
                severity=ValidationSeverity.CRITICAL,
                message=f"Insufficient judge events: {len(judge_events)} < {self.config.min_judge_events}",
                details={"judge_events": len(judge_events), "required": self.config.min_judge_events}
            ))
        
        return issues
    
    def _check_judge_inactivity(self, judge_events: List[CombatEvent]) -> List[ValidationIssue]:
        """Check for judge inactivity periods"""
        issues = []
        
        if len(judge_events) < 2:
            return issues
        
        # Sort by timestamp
        sorted_events = sorted(judge_events, key=lambda e: e.timestamp_ms)
        
        # Check gaps between events
        max_gap = 0
        for i in range(len(sorted_events) - 1):
            gap = (sorted_events[i+1].timestamp_ms - sorted_events[i].timestamp_ms) / 1000.0
            if gap > max_gap:
                max_gap = gap
        
        if max_gap > self.config.max_judge_inactivity_sec:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.JUDGE_INACTIVITY,
                severity=ValidationSeverity.WARNING,
                message=f"Judge inactivity detected: {max_gap:.0f}s gap",
                details={"max_gap_seconds": max_gap, "threshold": self.config.max_judge_inactivity_sec}
            ))
        
        return issues
    
    def _check_cv_feed_activity(self, cv_events: List[CombatEvent]) -> List[ValidationIssue]:
        """Check CV feed was active"""
        issues = []
        
        if len(cv_events) == 0:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.CV_FEED_INACTIVE,
                severity=ValidationSeverity.WARNING,
                message="No CV events detected - CV feed may be inactive",
                details={"cv_events": 0}
            ))
            return issues
        
        # Check CV event spacing
        sorted_events = sorted(cv_events, key=lambda e: e.timestamp_ms)
        
        max_gap = 0
        for i in range(len(sorted_events) - 1):
            gap = (sorted_events[i+1].timestamp_ms - sorted_events[i].timestamp_ms) / 1000.0
            if gap > max_gap:
                max_gap = gap
        
        if max_gap > self.config.max_cv_inactivity_sec:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.CV_FEED_INACTIVE,
                severity=ValidationSeverity.WARNING,
                message=f"CV feed gap detected: {max_gap:.0f}s",
                details={"max_gap_seconds": max_gap, "threshold": self.config.max_cv_inactivity_sec}
            ))
        
        return issues
    
    def _check_timecodes(
        self,
        events: List[CombatEvent],
        round_start: int,
        round_end: int
    ) -> List[ValidationIssue]:
        """Check event timecodes match round window"""
        issues = []
        
        out_of_window = []
        for event in events:
            if event.timestamp_ms < (round_start - self.config.timecode_tolerance_ms):
                out_of_window.append(event)
            elif event.timestamp_ms > (round_end + self.config.timecode_tolerance_ms):
                out_of_window.append(event)
        
        if out_of_window:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.TIMECODE_MISMATCH,
                severity=ValidationSeverity.ERROR,
                message=f"{len(out_of_window)} events outside round window",
                details={
                    "out_of_window_count": len(out_of_window),
                    "round_start": round_start,
                    "round_end": round_end,
                    "tolerance_ms": self.config.timecode_tolerance_ms
                }
            ))
        
        return issues
    
    def _check_round_duration(
        self,
        round_start: int,
        round_end: int
    ) -> List[ValidationIssue]:
        """Check round duration is reasonable"""
        issues = []
        
        duration_sec = (round_end - round_start) / 1000.0
        expected = self.config.expected_round_duration_sec
        tolerance = self.config.duration_tolerance_sec
        
        if abs(duration_sec - expected) > tolerance:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.TIMING_ANOMALY,
                severity=ValidationSeverity.WARNING,
                message=f"Round duration anomaly: {duration_sec:.0f}s (expected {expected}s)",
                details={
                    "duration_seconds": duration_sec,
                    "expected_seconds": expected,
                    "tolerance_seconds": tolerance
                }
            ))
        
        return issues
