"""
Blockchain Audit - Blockchain Engine
"""

import logging
import hashlib
import hmac
import secrets
from typing import List, Optional, Dict
from datetime import datetime, timezone
from .models import (
    ScoreRecord,
    BlockchainRecord,
    VerificationResult,
    AuditTrail,
    DigitalSignature
)

logger = logging.getLogger(__name__)

# Secret key for signatures (in production, use proper key management)
SECRET_KEY = secrets.token_hex(32)


class BlockchainEngine:
    """Engine for creating immutable blockchain records"""
    
    def __init__(self, db=None):
        self.db = db
        self.chain_cache: Dict[str, List[BlockchainRecord]] = {}
    
    def hash_data(self, data: dict) -> str:
        """
        Create SHA-256 hash of data
        
        Args:
            data: Dictionary to hash
        
        Returns:
            Hex string of hash
        """
        # Sort keys for consistent hashing
        sorted_data = str(sorted(data.items()))
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def create_signature(self, data_hash: str, signed_by: str) -> str:
        """
        Create HMAC signature for data hash
        
        Args:
            data_hash: Hash of the data
            signed_by: Identity of signer
        
        Returns:
            Hex string of signature
        """
        message = f"{data_hash}:{signed_by}".encode()
        signature = hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()
        return signature
    
    def verify_signature(self, data_hash: str, signature: str, signed_by: str) -> bool:
        """
        Verify HMAC signature
        
        Args:
            data_hash: Original hash
            signature: Signature to verify
            signed_by: Claimed signer
        
        Returns:
            True if valid, False otherwise
        """
        expected_signature = self.create_signature(data_hash, signed_by)
        return hmac.compare_digest(signature, expected_signature)
    
    async def record_score(self, score: ScoreRecord, signed_by: str) -> BlockchainRecord:
        """
        Record a score on the blockchain
        
        Args:
            score: Score record
            signed_by: Identity of person locking the score
        
        Returns:
            BlockchainRecord
        """
        # Create hash of score data
        score_dict = score.model_dump()
        score_dict['timestamp'] = score_dict['timestamp'].isoformat()
        data_hash = self.hash_data(score_dict)
        
        # Create digital signature
        signature = self.create_signature(data_hash, signed_by)
        
        # Get previous block
        previous_hash = "0" * 64  # Genesis block
        block_number = 1
        
        if self.db:
            try:
                # Get last block for this bout
                last_block = await self.db.blockchain_records.find_one(
                    {"bout_id": score.bout_id},
                    {"_id": 0},
                    sort=[("block_number", -1)]
                )
                
                if last_block:
                    previous_hash = last_block['data_hash']
                    block_number = last_block['block_number'] + 1
            
            except Exception as e:
                logger.error(f"Error getting previous block: {e}")
        
        # Create blockchain record
        record = BlockchainRecord(
            record_id=score.record_id,
            record_type="score",
            data_hash=data_hash,
            signature=signature,
            signed_by=signed_by,
            previous_hash=previous_hash,
            block_number=block_number,
            bout_id=score.bout_id,
            round_num=score.round_num
        )
        
        # Store in database
        if self.db:
            try:
                record_dict = record.model_dump()
                record_dict['created_at'] = record_dict['created_at'].isoformat()
                
                await self.db.blockchain_records.insert_one(record_dict)
                logger.info(f"Score recorded on blockchain: Block #{block_number}")
            
            except Exception as e:
                logger.error(f"Error storing blockchain record: {e}")
        
        return record
    
    async def verify_record(self, record_id: str) -> VerificationResult:
        """
        Verify integrity of a blockchain record
        
        Args:
            record_id: ID of record to verify
        
        Returns:
            VerificationResult
        """
        if not self.db:
            return VerificationResult(
                record_id=record_id,
                is_valid=False,
                data_hash_match=False,
                signature_valid=False,
                chain_integrity=False,
                message="Database not available"
            )
        
        try:
            # Get record
            record_dict = await self.db.blockchain_records.find_one(
                {"record_id": record_id},
                {"_id": 0}
            )
            
            if not record_dict:
                return VerificationResult(
                    record_id=record_id,
                    is_valid=False,
                    data_hash_match=False,
                    signature_valid=False,
                    chain_integrity=False,
                    message="Record not found"
                )
            
            record = BlockchainRecord(**{**record_dict, 'created_at': datetime.fromisoformat(record_dict['created_at'])})
            
            # Verify signature
            signature_valid = self.verify_signature(
                record.data_hash,
                record.signature,
                record.signed_by
            )
            
            # Verify chain integrity (check previous hash)
            chain_valid = True
            if record.block_number > 1:
                # Get previous block
                prev_block = await self.db.blockchain_records.find_one(
                    {
                        "bout_id": record.bout_id,
                        "block_number": record.block_number - 1
                    },
                    {"_id": 0}
                )
                
                if prev_block:
                    chain_valid = record.previous_hash == prev_block['data_hash']
                else:
                    chain_valid = False
            
            is_valid = signature_valid and chain_valid
            
            return VerificationResult(
                record_id=record_id,
                is_valid=is_valid,
                data_hash_match=True,
                signature_valid=signature_valid,
                chain_integrity=chain_valid,
                message="Valid" if is_valid else "Invalid: signature or chain integrity failed"
            )
        
        except Exception as e:
            logger.error(f"Error verifying record: {e}")
            return VerificationResult(
                record_id=record_id,
                is_valid=False,
                data_hash_match=False,
                signature_valid=False,
                chain_integrity=False,
                message=f"Error: {str(e)}"
            )
    
    async def get_audit_trail(self, bout_id: str) -> Optional[AuditTrail]:
        """
        Get complete audit trail for a bout
        
        Args:
            bout_id: Bout ID
        
        Returns:
            AuditTrail
        """
        if not self.db:
            return None
        
        try:
            # Get all blocks for bout
            cursor = self.db.blockchain_records.find(
                {"bout_id": bout_id},
                {"_id": 0}
            ).sort("block_number", 1)
            
            blocks_dict = await cursor.to_list(length=1000)
            
            if not blocks_dict:
                return AuditTrail(
                    bout_id=bout_id,
                    total_records=0,
                    score_records=0,
                    event_records=0,
                    blocks=[],
                    chain_valid=True
                )
            
            # Convert to BlockchainRecord objects
            blocks = [
                BlockchainRecord(**{**b, 'created_at': datetime.fromisoformat(b['created_at'])})
                for b in blocks_dict
            ]
            
            # Verify chain integrity
            chain_valid = True
            for i in range(1, len(blocks)):
                if blocks[i].previous_hash != blocks[i-1].data_hash:
                    chain_valid = False
                    break
            
            # Count by type
            score_records = sum(1 for b in blocks if b.record_type == "score")
            event_records = sum(1 for b in blocks if b.record_type == "event")
            
            return AuditTrail(
                bout_id=bout_id,
                total_records=len(blocks),
                score_records=score_records,
                event_records=event_records,
                blocks=blocks,
                chain_valid=chain_valid,
                first_block=blocks[0].block_id if blocks else None,
                last_block=blocks[-1].block_id if blocks else None
            )
        
        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return None
    
    async def verify_bout_integrity(self, bout_id: str) -> dict:
        """
        Verify complete integrity of all records for a bout
        
        Args:
            bout_id: Bout ID
        
        Returns:
            Verification summary
        """
        audit_trail = await self.get_audit_trail(bout_id)
        
        if not audit_trail:
            return {
                "bout_id": bout_id,
                "verified": False,
                "message": "No audit trail found"
            }
        
        # Verify each record
        total = len(audit_trail.blocks)
        verified = 0
        
        for block in audit_trail.blocks:
            result = await self.verify_record(block.record_id)
            if result.is_valid:
                verified += 1
        
        return {
            "bout_id": bout_id,
            "total_records": total,
            "verified_records": verified,
            "failed_records": total - verified,
            "chain_valid": audit_trail.chain_valid,
            "verified": verified == total and audit_trail.chain_valid,
            "integrity_percentage": (verified / total * 100) if total > 0 else 0
        }
