"""
Failover Engine
Auto-failover between cloud/local CV engines
"""

from .failover_manager import FailoverManager
from .routes import failover_engine_api

__version__ = "1.0.0"
