"""
Scoring Engine v3.0 - Impact-First Implementation
Complete replacement for scoring engine v2.

Implements:
- Config-driven event weights
- 5 Regularization rules (anti-spam)
- Impact Lock system (KD overrides volume)
- Full auditability and round receipts
"""

from .engine_v3 import score_round_v3, ScoringEngineV3, get_engine
from .config_v3 import (
    SCORING_CONFIG,
    REGULARIZATION_RULES,
    IMPACT_LOCK_RULES,
    ROUND_SCORING,
    UI_TOOLTIPS,
    get_all_event_configs,
    get_event_points,
    is_ss_event,
    is_protected_event,
)

# Legacy compatibility - point to v3 engine
score_round_delta_v2 = score_round_v3

__all__ = [
    'score_round_v3',
    'score_round_delta_v2',  # Legacy alias
    'ScoringEngineV3',
    'get_engine',
    'SCORING_CONFIG',
    'REGULARIZATION_RULES',
    'IMPACT_LOCK_RULES',
    'ROUND_SCORING',
    'UI_TOOLTIPS',
    'get_all_event_configs',
    'get_event_points',
    'is_ss_event',
    'is_protected_event',
]
