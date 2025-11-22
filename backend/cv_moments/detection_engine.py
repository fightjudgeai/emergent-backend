"""
CV Moments - Moment Detection Engine
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone
from .models import (
    SignificantMoment,
    Knockdown,
    BigStrike,
    SubmissionAttempt,
    ControversyMoment,
    HighlightReel,
    MomentAnalysis
)
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent

logger = logging.getLogger(__name__)

# Detection thresholds
KNOCKDOWN_THRESHOLD = 0.85
BIG_STRIKE_THRESHOLD = 0.75
SUBMISSION_DANGER_THRESHOLD = 0.70
CONTROVERSY_VARIANCE_THRESHOLD = 2.0


class MomentDetectionEngine:
    """AI engine for detecting significant fight moments"""
    
    def __init__(self, db=None):
        self.db = db
        self.moments_cache: Dict[str, List[SignificantMoment]] = {}
    
    def detect_knockdown(self, events: List[CombatEvent]) -> List[Knockdown]:
        """
        Detect knockdowns from events
        
        Criteria:
        - High severity strike (>0.85)
        - Followed by "fighter_down" or "rocked" event
        - Short time window (within 2 seconds)
        """
        knockdowns = []
        
        for i, event in enumerate(events):
            # Look for high impact strikes
            if event.event_type in ["strike", "significant_strike"] and event.severity and event.severity >= KNOCKDOWN_THRESHOLD:
                # Look ahead for knockdown confirmation
                for j in range(i + 1, min(i + 10, len(events))):
                    next_event = events[j]
                    
                    # Check if within 2 seconds
                    if next_event.timestamp_ms - event.timestamp_ms > 2000:
                        break
                    
                    # Check for knockdown indicators
                    if next_event.event_type in ["knockdown", "fighter_down", "rocked"]:
                        knockdown = Knockdown(
                            moment_id=f"kd_{event.event_id}",
                            bout_id=event.bout_id,
                            round_num=event.round_num,
                            timestamp_ms=event.timestamp_ms,
                            aggressor_id=event.fighter_id,
                            victim_id=next_event.fighter_id if next_event.fighter_id != event.fighter_id else "unknown",
                            strike_type=event.metadata.get("strike_type") if event.metadata else None,
                            impact_severity=event.severity,
                            recovery_time_ms=next_event.timestamp_ms - event.timestamp_ms,
                            was_flash_knockdown=next_event.timestamp_ms - event.timestamp_ms < 1000
                        )
                        knockdowns.append(knockdown)
                        break
        
        logger.info(f"Detected {len(knockdowns)} knockdowns")
        return knockdowns
    
    def detect_big_strikes(self, events: List[CombatEvent]) -> List[BigStrike]:
        """
        Detect significant strikes
        
        Criteria:
        - High severity (>0.75)
        - High confidence (>0.7)
        - Significant event type
        """
        big_strikes = []
        
        for event in events:
            if event.event_type in ["significant_strike", "strike"] and event.severity and event.severity >= BIG_STRIKE_THRESHOLD:
                if event.confidence and event.confidence >= 0.7:
                    # Check for combo (multiple strikes in quick succession)
                    combo_count = 1
                    
                    strike = BigStrike(
                        moment_id=f"strike_{event.event_id}",
                        bout_id=event.bout_id,
                        round_num=event.round_num,
                        timestamp_ms=event.timestamp_ms,
                        striker_id=event.fighter_id,
                        target_id="opponent",
                        strike_type=event.metadata.get("strike_type", "unknown") if event.metadata else "unknown",
                        target_area=event.metadata.get("target_area", "unknown") if event.metadata else "unknown",
                        impact_score=event.severity,
                        combo_strikes=combo_count,
                        momentum_shift=event.severity >= 0.90
                    )
                    big_strikes.append(strike)
        
        logger.info(f"Detected {len(big_strikes)} big strikes")
        return big_strikes
    
    def detect_submissions(self, events: List[CombatEvent]) -> List[SubmissionAttempt]:
        """
        Detect submission attempts
        
        Criteria:
        - Submission or grappling event
        - High danger level
        - Sufficient duration
        """
        submissions = []
        
        for i, event in enumerate(events):
            if event.event_type in ["submission_attempt", "grappling"] and event.severity and event.severity >= SUBMISSION_DANGER_THRESHOLD:
                # Try to find when submission ended
                duration = 3000  # Default 3 seconds
                was_successful = False
                
                for j in range(i + 1, min(i + 20, len(events))):
                    next_event = events[j]
                    if next_event.event_type in ["submission_success", "tap_out"]:
                        duration = next_event.timestamp_ms - event.timestamp_ms
                        was_successful = True
                        break
                    elif next_event.event_type in ["escape", "position_change"]:
                        duration = next_event.timestamp_ms - event.timestamp_ms
                        break
                
                submission = SubmissionAttempt(
                    moment_id=f"sub_{event.event_id}",
                    bout_id=event.bout_id,
                    round_num=event.round_num,
                    timestamp_ms=event.timestamp_ms,
                    attacker_id=event.fighter_id,
                    defender_id="opponent",
                    submission_type=event.metadata.get("submission_type", "unknown") if event.metadata else "unknown",
                    danger_level=event.severity,
                    duration_ms=duration,
                    was_successful=was_successful
                )
                submissions.append(submission)
        
        logger.info(f"Detected {len(submissions)} submission attempts")
        return submissions
    
    def detect_controversies(self, bout_id: str, judge_scores: List[Dict]) -> List[ControversyMoment]:
        """
        Detect controversial moments
        
        Criteria:
        - Large score variance between judges
        - Split decisions
        - Unusual scoring patterns
        """
        controversies = []
        
        # Check for score variance
        if judge_scores:
            for round_scores in judge_scores:
                scores = round_scores.get('scores', [])
                if len(scores) >= 3:
                    variance = max(scores) - min(scores)
                    
                    if variance >= CONTROVERSY_VARIANCE_THRESHOLD:
                        controversy = ControversyMoment(
                            moment_id=f"controversy_{bout_id}_{round_scores.get('round_num')}",
                            bout_id=bout_id,
                            round_num=round_scores.get('round_num'),
                            controversy_type="score_variance",
                            description=f"Large score variance: {variance} points",
                            severity=min(variance / 5.0, 1.0),
                            judge_scores=scores,
                            score_variance=variance
                        )
                        controversies.append(controversy)
        
        logger.info(f"Detected {len(controversies)} controversies")
        return controversies
    
    async def analyze_bout(self, bout_id: str, events: List[CombatEvent], judge_scores: Optional[List[Dict]] = None) -> MomentAnalysis:
        """
        Complete analysis of a bout for all significant moments
        """
        # Detect all moment types
        knockdowns = self.detect_knockdown(events)
        big_strikes = self.detect_big_strikes(events)
        submissions = self.detect_submissions(events)
        controversies = self.detect_controversies(bout_id, judge_scores or [])
        
        # Create SignificantMoment objects for all
        all_moments = []
        
        # Add knockdowns
        for kd in knockdowns:
            moment = SignificantMoment(
                bout_id=kd.bout_id,
                round_num=kd.round_num,
                timestamp_ms=kd.timestamp_ms,
                moment_type="knockdown",
                severity=kd.impact_severity,
                confidence=0.95,
                fighter_1_id=kd.aggressor_id,
                fighter_2_id=kd.victim_id,
                description=f"Knockdown by {kd.strike_type or 'strike'}",
                clip_start_ms=max(0, kd.timestamp_ms - 5000),
                clip_end_ms=kd.timestamp_ms + 5000
            )
            all_moments.append(moment)
        
        # Add big strikes
        for strike in big_strikes:
            moment = SignificantMoment(
                bout_id=strike.bout_id,
                round_num=strike.round_num,
                timestamp_ms=strike.timestamp_ms,
                moment_type="big_strike",
                severity=strike.impact_score,
                confidence=0.85,
                fighter_1_id=strike.striker_id,
                description=f"Significant {strike.strike_type} to {strike.target_area}",
                clip_start_ms=max(0, strike.timestamp_ms - 3000),
                clip_end_ms=strike.timestamp_ms + 3000
            )
            all_moments.append(moment)
        
        # Add submissions
        for sub in submissions:
            moment = SignificantMoment(
                bout_id=sub.bout_id,
                round_num=sub.round_num,
                timestamp_ms=sub.timestamp_ms,
                moment_type="submission_attempt",
                severity=sub.danger_level,
                confidence=0.90,
                fighter_1_id=sub.attacker_id,
                fighter_2_id=sub.defender_id,
                description=f"{sub.submission_type} attempt",
                clip_start_ms=max(0, sub.timestamp_ms - 2000),
                clip_end_ms=sub.timestamp_ms + sub.duration_ms + 2000
            )
            all_moments.append(moment)
        
        # Sort by severity
        all_moments.sort(key=lambda x: x.severity, reverse=True)
        
        # Calculate excitement score (0-100)
        excitement_score = min(100, (
            len(knockdowns) * 30 +
            len(big_strikes) * 5 +
            len(submissions) * 15
        ))
        
        # Calculate competitiveness (based on score variance)
        competitiveness = 75.0  # Default
        if controversies:
            avg_variance = sum(c.score_variance or 0 for c in controversies) / len(controversies)
            competitiveness = min(100, 50 + (avg_variance * 10))
        
        # Store in cache
        self.moments_cache[bout_id] = all_moments
        
        # Store in database
        if self.db:
            try:
                for moment in all_moments:
                    moment_dict = moment.model_dump()
                    moment_dict['detected_at'] = moment_dict['detected_at'].isoformat()
                    await self.db.significant_moments.insert_one(moment_dict)
            except Exception as e:
                logger.error(f"Error storing moments: {e}")
        
        analysis = MomentAnalysis(
            bout_id=bout_id,
            total_rounds=max([e.round_num for e in events]) if events else 0,
            moments_detected=len(all_moments),
            knockdowns_count=len(knockdowns),
            big_strikes_count=len(big_strikes),
            submission_attempts_count=len(submissions),
            controversies_count=len(controversies),
            excitement_score=excitement_score,
            competitiveness_score=competitiveness,
            top_moments=all_moments[:10]  # Top 10 moments
        )
        
        logger.info(f"Bout analysis complete: {len(all_moments)} moments detected")
        return analysis
    
    async def get_highlight_reel(self, bout_id: str) -> Optional[HighlightReel]:
        """Get complete highlight reel for a bout"""
        if not self.db:
            return None
        
        try:
            # Get all moments from database
            cursor = self.db.significant_moments.find({"bout_id": bout_id}, {"_id": 0})
            moments = await cursor.to_list(length=1000)
            
            # Separate by type
            knockdowns = []
            big_strikes = []
            submissions = []
            controversies = []
            
            for m in moments:
                if m['moment_type'] == 'knockdown':
                    knockdowns.append(Knockdown(
                        moment_id=m['id'],
                        bout_id=m['bout_id'],
                        round_num=m['round_num'],
                        timestamp_ms=m['timestamp_ms'],
                        aggressor_id=m.get('fighter_1_id', 'unknown'),
                        victim_id=m.get('fighter_2_id', 'unknown'),
                        impact_severity=m['severity']
                    ))
                elif m['moment_type'] == 'big_strike':
                    big_strikes.append(BigStrike(
                        moment_id=m['id'],
                        bout_id=m['bout_id'],
                        round_num=m['round_num'],
                        timestamp_ms=m['timestamp_ms'],
                        striker_id=m.get('fighter_1_id', 'unknown'),
                        target_id=m.get('fighter_2_id', 'unknown'),
                        strike_type='unknown',
                        target_area='unknown',
                        impact_score=m['severity']
                    ))
                elif m['moment_type'] == 'submission_attempt':
                    submissions.append(SubmissionAttempt(
                        moment_id=m['id'],
                        bout_id=m['bout_id'],
                        round_num=m['round_num'],
                        timestamp_ms=m['timestamp_ms'],
                        attacker_id=m.get('fighter_1_id', 'unknown'),
                        defender_id=m.get('fighter_2_id', 'unknown'),
                        submission_type='unknown',
                        danger_level=m['severity'],
                        duration_ms=3000
                    ))
            
            # Find most exciting round
            round_excitement = {}
            for m in moments:
                r = m['round_num']
                round_excitement[r] = round_excitement.get(r, 0) + m['severity']
            
            most_exciting = max(round_excitement.keys(), key=lambda k: round_excitement[k]) if round_excitement else None
            
            return HighlightReel(
                bout_id=bout_id,
                total_moments=len(moments),
                knockdowns=knockdowns,
                big_strikes=big_strikes,
                submission_attempts=submissions,
                controversies=controversies,
                most_exciting_round=most_exciting,
                momentum_shifts=sum(1 for m in moments if m.get('metadata', {}).get('momentum_shift'))
            )
        
        except Exception as e:
            logger.error(f"Error getting highlight reel: {e}")
            return None
