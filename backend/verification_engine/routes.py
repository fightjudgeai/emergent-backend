"""
Verification Engine API Routes

Endpoints for multi-operator verification and discrepancy management.
"""

from fastapi import APIRouter, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging

from .verifier import VerificationEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verification", tags=["Verification Engine"])

# Global instances
db: Optional[AsyncIOMotorDatabase] = None
verifier: Optional[VerificationEngine] = None


def init_verification_engine(database: AsyncIOMotorDatabase):
    """Initialize verification engine with database"""
    global db, verifier
    db = database
    verifier = VerificationEngine(database)
    logger.info("✅ Verification Engine initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Verification Engine",
        "version": "1.0.0",
        "status": "operational",
        "verifier_active": verifier is not None
    }


@router.post("/verify/round/{fight_id}/{round_num}")
async def verify_round(fight_id: str, round_num: int):
    """
    Verify round stats across all sources
    
    Compares:
    - judge_software vs stat_operator vs ai_cv
    
    Flags:
    - Sig strikes differ > 10%
    - Takedowns differ > 1
    
    Args:
        fight_id: Fight identifier
        round_num: Round number
        
    Returns:
        Verification result with discrepancies
    """
    
    if not verifier:
        raise HTTPException(status_code=500, detail="Verifier not initialized")
    
    try:
        result = await verifier.verify_round(fight_id, round_num)
        return result
    
    except Exception as e:
        logger.error(f"Error verifying round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/fight/{fight_id}")
async def verify_fight(fight_id: str):
    """
    Verify all rounds in a fight
    
    Args:
        fight_id: Fight identifier
        
    Returns:
        Verification results for all rounds
    """
    
    if not verifier:
        raise HTTPException(status_code=500, detail="Verifier not initialized")
    
    try:
        # Get all rounds for this fight
        round_stats = await db.round_stats.find({'fight_id': fight_id}).to_list(length=100)
        
        if not round_stats:
            raise HTTPException(status_code=404, detail=f"No rounds found for fight {fight_id}")
        
        # Get unique rounds
        rounds = sorted(set(stat.get('round', 1) for stat in round_stats))
        
        # Verify each round
        results = []
        total_discrepancies = 0
        
        for round_num in rounds:
            result = await verifier.verify_round(fight_id, round_num)
            results.append(result)
            total_discrepancies += result.get('discrepancies_found', 0)
        
        return {
            'fight_id': fight_id,
            'total_rounds': len(rounds),
            'rounds_verified': len(results),
            'total_discrepancies': total_discrepancies,
            'requires_review': total_discrepancies > 0,
            'results': results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying fight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discrepancies")
async def get_discrepancies(
    fight_id: Optional[str] = Query(None, description="Filter by fight ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending_review, reviewed, resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity (high, medium, low)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
):
    """
    Get discrepancies with filters
    
    Returns list of flagged discrepancies
    """
    
    if not verifier:
        raise HTTPException(status_code=500, detail="Verifier not initialized")
    
    try:
        discrepancies = await verifier.get_discrepancies(
            fight_id=fight_id,
            status=status,
            severity=severity,
            limit=limit
        )
        
        return {
            'count': len(discrepancies),
            'discrepancies': discrepancies
        }
    
    except Exception as e:
        logger.error(f"Error getting discrepancies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discrepancies/{discrepancy_id}/resolve")
async def resolve_discrepancy(
    discrepancy_id: str,
    resolution: str,
    resolved_by: str
):
    """
    Resolve a discrepancy
    
    Args:
        discrepancy_id: Discrepancy ID
        resolution: Resolution notes
        resolved_by: User who resolved it
        
    Returns:
        Success status
    """
    
    if not verifier:
        raise HTTPException(status_code=500, detail="Verifier not initialized")
    
    try:
        success = await verifier.resolve_discrepancy(
            discrepancy_id=discrepancy_id,
            resolution=resolution,
            resolved_by=resolved_by
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Discrepancy not found")
        
        return {
            'status': 'success',
            'discrepancy_id': discrepancy_id,
            'message': 'Discrepancy resolved'
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving discrepancy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_verification_summary():
    """
    Get verification statistics summary
    
    Returns counts by status and severity
    """
    
    if not verifier or not db:
        raise HTTPException(status_code=500, detail="Verifier not initialized")
    
    try:
        # Count by status
        pending = await db.stat_discrepancies.count_documents({'status': 'pending_review'})
        reviewed = await db.stat_discrepancies.count_documents({'status': 'reviewed'})
        resolved = await db.stat_discrepancies.count_documents({'status': 'resolved'})
        
        # Count by severity
        high = await db.stat_discrepancies.count_documents({'severity': 'high'})
        medium = await db.stat_discrepancies.count_documents({'severity': 'medium'})
        
        # Total
        total = await db.stat_discrepancies.count_documents({})
        
        return {
            'total_discrepancies': total,
            'by_status': {
                'pending_review': pending,
                'reviewed': reviewed,
                'resolved': resolved
            },
            'by_severity': {
                'high': high,
                'medium': medium
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting verification summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
