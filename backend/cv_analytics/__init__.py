"""
CV Analytics Engine (E2) - FJAI Edition
Converts raw CV model outputs into standardized combat events
"""

from .analytics_engine import CVAnalyticsEngine
from .temporal_smoothing import TemporalSmoother
from .multicam_fusion import MultiCameraFusion
from .mock_generator import MockCVDataGenerator
from .routes import cv_analytics_router

__version__ = "1.0.0"
