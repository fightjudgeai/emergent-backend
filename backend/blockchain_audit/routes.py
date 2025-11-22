"""
Blockchain Audit - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from .blockchain_engine import BlockchainEngine
from .models import (
    ScoreRecord,
    BlockchainRecord,
    VerificationResult,
    AuditTrail
)

logger = logging.getLogger(__name__)

blockchain_audit_api = APIRouter(tags=["Blockchain Audit"])
blockchain_engine: Optional[BlockchainEngine] = None

def get_blockchain_engine():
    if blockchain_engine is None:
        raise HTTPException(status_code=500, detail="Blockchain engine not initialized")
    return blockchain_engine

# ============================================================================
# Record Management
# ============================================================================

@blockchain_audit_api.post("/blockchain/record/score", response_model=BlockchainRecord, status_code=201)
async def record_score_on_blockchain(score: ScoreRecord, signed_by: str):
    """
    Record a score on the blockchain with digital signature
    
    Creates immutable record that cannot be tampered with
    """
    engine = get_blockchain_engine()
    
    try:
        record = await engine.record_score(score, signed_by)
        return record
    
    except Exception as e:
        logger.error(f"Error recording score: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record score: {str(e)}")

# ============================================================================
# Verification
# ============================================================================

@blockchain_audit_api.get("/blockchain/verify/{record_id}", response_model=VerificationResult)
async def verify_blockchain_record(record_id: str):
    """
    Verify integrity of a blockchain record
    
    Checks:
    - Digital signature validity
    - Chain integrity (previous hash linkage)
    - Data hash match
    """
    engine = get_blockchain_engine()
    
    result = await engine.verify_record(record_id)
    return result

@blockchain_audit_api.get("/blockchain/verify/bout/{bout_id}")
async def verify_bout_integrity(bout_id: str):
    """
    Verify complete integrity of all records for a bout
    
    Returns summary of verification status
    """
    engine = get_blockchain_engine()
    
    summary = await engine.verify_bout_integrity(bout_id)
    return summary

# ============================================================================
# Audit Trail
# ============================================================================

@blockchain_audit_api.get("/blockchain/audit/{bout_id}", response_model=AuditTrail)
async def get_audit_trail(bout_id: str):
    """
    Get complete audit trail for a bout
    
    Returns all blockchain records in chronological order
    """
    engine = get_blockchain_engine()
    
    audit_trail = await engine.get_audit_trail(bout_id)
    
    if not audit_trail:
        raise HTTPException(status_code=404, detail=f"No audit trail found for bout: {bout_id}")
    
    return audit_trail

@blockchain_audit_api.get("/blockchain/blocks/{bout_id}")
async def get_blockchain_blocks(bout_id: str):
    """Get all blockchain blocks for a bout"""
    engine = get_blockchain_engine()
    
    audit_trail = await engine.get_audit_trail(bout_id)
    
    if not audit_trail:
        return {"bout_id": bout_id, "blocks": []}
    
    return {
        "bout_id": bout_id,
        "total_blocks": len(audit_trail.blocks),
        "chain_valid": audit_trail.chain_valid,
        "blocks": [
            {
                "block_number": b.block_number,
                "record_id": b.record_id,
                "record_type": b.record_type,
                "data_hash": b.data_hash,
                "signature": b.signature[:16] + "...",  # Truncated for display
                "signed_by": b.signed_by,
                "created_at": b.created_at.isoformat()
            }
            for b in audit_trail.blocks
        ]
    }

# ============================================================================
# Statistics
# ============================================================================

@blockchain_audit_api.get("/blockchain/stats")
async def get_blockchain_stats():
    """Get blockchain statistics"""
    engine = get_blockchain_engine()
    
    if not engine.db:
        return {"message": "Database not available"}
    
    try:
        # Count total records
        total_records = await engine.db.blockchain_records.count_documents({})
        
        # Count by type
        score_records = await engine.db.blockchain_records.count_documents({"record_type": "score"})
        event_records = await engine.db.blockchain_records.count_documents({"record_type": "event"})
        
        # Get unique bouts
        bouts = await engine.db.blockchain_records.distinct("bout_id")
        
        return {
            "total_records": total_records,
            "score_records": score_records,
            "event_records": event_records,
            "total_bouts": len(bouts),
            "average_records_per_bout": total_records / len(bouts) if bouts else 0
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

@blockchain_audit_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Blockchain Audit", "version": "1.0.0"}
