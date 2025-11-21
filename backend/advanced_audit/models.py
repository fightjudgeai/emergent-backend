"""
Advanced Audit Logger - Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid


class AuditEntry(BaseModel):
    """Single audit entry in chain"""
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bout_id: str
    
    # Chain information
    sequence_num: int
    previous_hash: str
    current_hash: str
    
    # Event data
    event_type: str
    payload: Dict[str, Any]
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "system"
    
    # Source tracking
    cv_version: Optional[str] = None
    judge_device_id: Optional[str] = None
    scoring_engine_version: Optional[str] = None


class ChainTip(BaseModel):
    """Current tip of audit chain for bout"""
    bout_id: str
    current_hash: str
    sequence_num: int
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationResult(BaseModel):
    """Chain verification result"""
    bout_id: str
    valid: bool
    total_entries: int
    verified_entries: int
    
    # Tamper detection
    tampered: bool
    tamper_detected_at: Optional[int] = None
    tamper_details: Optional[str] = None
    
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
