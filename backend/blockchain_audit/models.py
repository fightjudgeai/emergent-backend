"""
Blockchain Audit - Data Models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid


class ScoreRecord(BaseModel):
    """Score record to be hashed and stored"""
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    round_num: int
    judge_id: str
    judge_name: str
    fighter_1_score: int
    fighter_2_score: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BlockchainRecord(BaseModel):
    """Blockchain record with hash and signature"""
    block_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    record_id: str
    record_type: Literal["score", "event", "bout_result"]
    
    # Original data hash
    data_hash: str
    
    # Digital signature
    signature: str
    signed_by: str
    
    # Blockchain linkage
    previous_hash: str
    block_number: int
    
    # Metadata
    bout_id: str
    round_num: Optional[int] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_verified: bool = True


class VerificationResult(BaseModel):
    """Result of blockchain verification"""
    record_id: str
    is_valid: bool
    data_hash_match: bool
    signature_valid: bool
    chain_integrity: bool
    
    message: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditTrail(BaseModel):
    """Complete audit trail for a bout"""
    bout_id: str
    total_records: int
    score_records: int
    event_records: int
    
    blocks: List[BlockchainRecord]
    
    chain_valid: bool
    first_block: Optional[str] = None
    last_block: Optional[str] = None
    
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DigitalSignature(BaseModel):
    """Digital signature details"""
    signature_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_hash: str
    signature: str
    public_key: str
    algorithm: str = "SHA256-RSA"
    signed_by: str
    signed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
