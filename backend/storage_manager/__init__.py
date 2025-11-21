"""
Storage Manager Service
Manage recording disk usage, cleanup, and archival
"""

from .manager_engine import StorageManagerEngine
from .routes import storage_manager_api

__version__ = "1.0.0"
