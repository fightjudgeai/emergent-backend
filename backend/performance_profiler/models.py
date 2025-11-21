"""
Performance Profiler - Data Models
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class PerformanceMetric(BaseModel):
    """Single performance metric"""
    name: str
    value_ms: float
    timestamp: datetime = Field(default_factory=datetime.now)


class PerformanceSummary(BaseModel):
    """Performance summary statistics"""
    
    # CV inference
    cv_inference_avg_ms: float
    cv_inference_p95_ms: float
    cv_inference_p99_ms: float
    
    # Event ingestion
    event_ingestion_avg_ms: float
    event_ingestion_p95_ms: float
    event_ingestion_p99_ms: float
    
    # Scoring calculation
    scoring_calc_avg_ms: float
    scoring_calc_p95_ms: float
    scoring_calc_p99_ms: float
    
    # WebSocket roundtrip
    websocket_roundtrip_avg_ms: float
    websocket_roundtrip_p95_ms: float
    websocket_roundtrip_p99_ms: float
    
    # Overall system health
    total_measurements: int
    measurement_period_sec: float


class LiveMetric(BaseModel):
    """Live performance metric for WebSocket streaming"""
    metric_type: str  # cv_inference, event_ingestion, scoring, websocket
    value_ms: float
    timestamp_ms: int
