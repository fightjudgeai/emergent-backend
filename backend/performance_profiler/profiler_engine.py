"""
Performance Profiler - Main Engine
"""

import time
import asyncio
import logging
from typing import Dict, List, Deque
from collections import deque
from datetime import datetime, timezone
from .models import PerformanceMetric, PerformanceSummary, LiveMetric

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """Monitor system performance metrics"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        
        # Metric storage (rolling window)
        self.cv_inference: Deque[float] = deque(maxlen=window_size)
        self.event_ingestion: Deque[float] = deque(maxlen=window_size)
        self.scoring_calc: Deque[float] = deque(maxlen=window_size)
        self.websocket_roundtrip: Deque[float] = deque(maxlen=window_size)
        
        # Start time
        self.start_time = time.time()
        
        # WebSocket connections for live streaming
        self.live_connections: List = []
    
    def record_cv_inference(self, duration_ms: float):
        """Record CV inference time"""
        self.cv_inference.append(duration_ms)
        self._broadcast_live_metric("cv_inference", duration_ms)
    
    def record_event_ingestion(self, duration_ms: float):
        """Record event ingestion time"""
        self.event_ingestion.append(duration_ms)
        self._broadcast_live_metric("event_ingestion", duration_ms)
    
    def record_scoring_calc(self, duration_ms: float):
        """Record scoring calculation time"""
        self.scoring_calc.append(duration_ms)
        self._broadcast_live_metric("scoring", duration_ms)
    
    def record_websocket_roundtrip(self, duration_ms: float):
        """Record WebSocket roundtrip time"""
        self.websocket_roundtrip.append(duration_ms)
        self._broadcast_live_metric("websocket", duration_ms)
    
    def get_summary(self) -> PerformanceSummary:
        """
        Get performance summary statistics
        
        Returns:
            PerformanceSummary with percentiles
        """
        total_measurements = (
            len(self.cv_inference) +
            len(self.event_ingestion) +
            len(self.scoring_calc) +
            len(self.websocket_roundtrip)
        )
        
        measurement_period = time.time() - self.start_time
        
        return PerformanceSummary(
            cv_inference_avg_ms=self._calculate_avg(self.cv_inference),
            cv_inference_p95_ms=self._calculate_percentile(self.cv_inference, 95),
            cv_inference_p99_ms=self._calculate_percentile(self.cv_inference, 99),
            
            event_ingestion_avg_ms=self._calculate_avg(self.event_ingestion),
            event_ingestion_p95_ms=self._calculate_percentile(self.event_ingestion, 95),
            event_ingestion_p99_ms=self._calculate_percentile(self.event_ingestion, 99),
            
            scoring_calc_avg_ms=self._calculate_avg(self.scoring_calc),
            scoring_calc_p95_ms=self._calculate_percentile(self.scoring_calc, 95),
            scoring_calc_p99_ms=self._calculate_percentile(self.scoring_calc, 99),
            
            websocket_roundtrip_avg_ms=self._calculate_avg(self.websocket_roundtrip),
            websocket_roundtrip_p95_ms=self._calculate_percentile(self.websocket_roundtrip, 95),
            websocket_roundtrip_p99_ms=self._calculate_percentile(self.websocket_roundtrip, 99),
            
            total_measurements=total_measurements,
            measurement_period_sec=measurement_period
        )
    
    def _calculate_avg(self, data: Deque[float]) -> float:
        """Calculate average"""
        if not data:
            return 0.0
        return sum(data) / len(data)
    
    def _calculate_percentile(self, data: Deque[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100.0))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]
    
    def _broadcast_live_metric(self, metric_type: str, value_ms: float):
        """Broadcast live metric to connected WebSocket clients"""
        if not self.live_connections:
            return
        
        metric = LiveMetric(
            metric_type=metric_type,
            value_ms=value_ms,
            timestamp_ms=int(time.time() * 1000)
        )
        
        # In production: send to WebSocket connections
        # for conn in self.live_connections:
        #     await conn.send_json(metric.model_dump())
        pass
    
    async def generate_mock_data(self):
        """
        Generate mock performance data for testing
        """
        import random
        
        while True:
            # Mock CV inference (30-100ms)
            self.record_cv_inference(random.uniform(30, 100))
            
            # Mock event ingestion (5-20ms)
            self.record_event_ingestion(random.uniform(5, 20))
            
            # Mock scoring calc (10-50ms)
            self.record_scoring_calc(random.uniform(10, 50))
            
            # Mock WebSocket roundtrip (10-30ms)
            self.record_websocket_roundtrip(random.uniform(10, 30))
            
            await asyncio.sleep(0.1)  # Generate every 100ms
