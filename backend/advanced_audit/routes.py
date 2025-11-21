"""
Advanced Audit Logger - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
import logging
from .audit_engine import AdvancedAuditEngine
from .models import AuditEntry, VerificationResult, ChainTip

logger = logging.getLogger(__name__)

advanced_audit_api = APIRouter(tags=["Advanced Audit"])
audit_engine: Optional[AdvancedAuditEngine] = None

def get_audit_engine():
    if audit_engine is None:
        raise HTTPException(status_code=500, detail="Advanced Audit not initialized")
    return audit_engine

@advanced_audit_api.post("/log", response_model=AuditEntry)
async def log_event(
    bout_id: str,
    event_type: str,
    payload: Dict[str, Any],
    actor: str = "system",
    cv_version: Optional[str] = None,
    judge_device_id: Optional[str] = None,
    scoring_engine_version: Optional[str] = None
):
    """Log event to audit chain"""
    engine = get_audit_engine()
    return engine.log_event(bout_id, event_type, payload, actor, cv_version, judge_device_id, scoring_engine_version)

@advanced_audit_api.get("/verify/{bout_id}", response_model=VerificationResult)
async def verify_chain(bout_id: str):
    """Verify audit chain integrity"""
    engine = get_audit_engine()
    return engine.verify_chain(bout_id)

@advanced_audit_api.get("/chain/{bout_id}", response_model=List[AuditEntry])
async def get_chain(bout_id: str):
    """Get complete audit chain"""
    engine = get_audit_engine()
    return engine.get_chain(bout_id)

@advanced_audit_api.get("/tip/{bout_id}", response_model=ChainTip)
async def get_chain_tip(bout_id: str):
    """Get current chain tip"""
    engine = get_audit_engine()
    tip = engine.get_chain_tip(bout_id)
    if not tip:
        raise HTTPException(status_code=404, detail="Chain not found")
    return tip

@advanced_audit_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Advanced Audit", "version": "1.0.0"}
