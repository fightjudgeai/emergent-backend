"""
Event Harmonizer Microservice
Resolve conflicts between manual judge events and CV events
"""

from .harmonizer_engine import EventHarmonizerEngine
from .conflict_resolver import ConflictResolver
from .routes import event_harmonizer_api

__version__ = "1.0.0"
