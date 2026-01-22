"""
Scoring Engine V2 - UWID Rules Implementation
Complete replacement for unified_scoring.py

Implements:
- Plan A/B/C hierarchy (Unified Rules)
- Impact-based scoring with gates
- Strict 10-8 and 10-7 requirements
- Control-with-offense rules
- Leg damage escalation
- Full receipt/explainability output
"""

from .engine import score_round_delta_v2
from .types import (
    RoundScoreResult,
    RoundReceipt,
    PlanBreakdown,
    Verdict,
    ContributionItem,
    ControlWindow,
    StrikeEvent,
    GrapplingEvent,
    ImpactEvent,
    QualityTag,
    KnockdownTier,
    SubmissionDepth,
    ControlType
)

__all__ = [
    'score_round_delta_v2',
    'RoundScoreResult',
    'RoundReceipt',
    'PlanBreakdown',
    'Verdict',
    'ContributionItem',
    'ControlWindow',
    'StrikeEvent',
    'GrapplingEvent',
    'ImpactEvent',
    'QualityTag',
    'KnockdownTier',
    'SubmissionDepth',
    'ControlType'
]
