"""
Round Validator - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
import sys
sys.path.append('/app/backend')
from fjai.models import CombatEvent
from .validator_engine import RoundValidatorEngine
from .models import RoundValidationResult, ValidationConfig

logger = logging.getLogger(__name__)

round_validator_api = APIRouter(tags=["Round Validator"])
validator_engine: Optional[RoundValidatorEngine] = None

def get_validator_engine():
    if validator_engine is None:
        raise HTTPException(status_code=500, detail="Round Validator not initialized")
    return validator_engine

@round_validator_api.post("/validate", response_model=RoundValidationResult)
async def validate_round(
    round_id: str,
    bout_id: str,
    round_num: int,
    events: List[CombatEvent],
    round_start_time: Optional[int] = None,
    round_end_time: Optional[int] = None
):
    """Validate round before scoring"""
    engine = get_validator_engine()
    return engine.validate_round(round_id, bout_id, round_num, events, round_start_time, round_end_time)

@round_validator_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Round Validator", "version": "1.0.0"}
