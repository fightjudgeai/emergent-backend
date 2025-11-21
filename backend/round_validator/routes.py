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
    """Validate round before scoring (POST)"""
    engine = get_validator_engine()
    result = engine.validate_round(round_id, bout_id, round_num, events, round_start_time, round_end_time)
    
    # Store result for later retrieval
    await engine.store_validation_result(result)
    
    return result

@round_validator_api.get("/rounds/{round_id}/validate", response_model=RoundValidationResult)
async def get_round_validation(round_id: str):
    """
    Get validation result for a round (GET endpoint)
    
    Returns cached validation result if available.
    Supervisor dashboard can call this endpoint to retrieve results.
    """
    engine = get_validator_engine()
    result = await engine.get_validation_result(round_id)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No validation result found for round_id: {round_id}"
        )
    
    return result

@round_validator_api.get("/bouts/{bout_id}/validate")
async def get_bout_validations(bout_id: str):
    """Get all validation results for a bout"""
    engine = get_validator_engine()
    results = await engine.get_bout_validations(bout_id)
    
    return {
        "bout_id": bout_id,
        "total_rounds": len(results),
        "validations": results
    }

@round_validator_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Round Validator", "version": "1.0.0"}
