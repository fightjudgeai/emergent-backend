"""
CV Router Microservice
Manage multiple RTMP/SRT streams and distribute to CV workers
"""

from .router_engine import CVRouterEngine
from .worker_manager import WorkerManager
from .stream_ingestor import StreamIngestor
from .routes import cv_router_api

__version__ = "1.0.0"
