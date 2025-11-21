"""
Fight Judge AI - Integrated Scoring Engine
Combines manual judge events + CV events into unified 10-Point-Must scoring
"""

from .models import *
from .event_pipeline import EventPipeline
from .scoring_engine import WeightedScoringEngine
from .round_manager import RoundManager
from .audit_layer import AuditLayer
from .routes import fjai_router

__version__ = "1.0.0"
