"""
Time Sync Service
Unified timestamp source with NTP-like synchronization
"""

from .sync_engine import TimeSyncEngine
from .routes import time_sync_api

__version__ = "1.0.0"
