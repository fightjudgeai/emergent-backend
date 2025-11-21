"""
Report Generator - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException, Response
from typing import Optional
import logging
from .generator_engine import ReportGeneratorEngine
from .models import FightReport, ReportFormat

logger = logging.getLogger(__name__)

report_generator_api = APIRouter(tags=["Report Generator"])
report_engine: Optional[ReportGeneratorEngine] = None

def get_report_engine():
    if report_engine is None:
        raise HTTPException(status_code=500, detail="Report Generator not initialized")
    return report_engine

@report_generator_api.get("/generate")
async def generate_report(bout_id: str, format: ReportFormat = ReportFormat.HTML):
    """Generate fight report"""
    engine = get_report_engine()
    
    # In production: fetch data from database
    # For now: return mock report
    from datetime import datetime
    mock_report = FightReport(
        bout_id=bout_id,
        event_name="PFC 50",
        fighters={"fighter_a": "Fighter A", "fighter_b": "Fighter B"},
        date=datetime.now(),
        round_scores=[],
        final_result="10-9, 10-9, 10-9",
        major_events=[],
        kd_timeline=[],
        rocked_timeline=[],
        momentum_swings=[],
        total_events=50,
        strike_counts={"fighter_a": 25, "fighter_b": 25},
        control_time={"fighter_a": 60.0, "fighter_b": 30.0},
        model_versions={"cv_analytics": "1.0.0", "scoring_engine": "1.0.0"},
        audit_log_reference=f"audit_{bout_id}"
    )
    
    content = engine.generate_report(mock_report, format)
    
    if format == ReportFormat.HTML:
        return Response(content=content, media_type="text/html")
    elif format == ReportFormat.JSON:
        return Response(content=content, media_type="application/json")
    else:
        return Response(content=content, media_type="application/pdf")

@report_generator_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Report Generator", "version": "1.0.0"}
