"""
Advanced Audit Logger - Blockchain-Style Audit Engine
"""

import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .models import AuditEntry, ChainTip, VerificationResult

logger = logging.getLogger(__name__)


class AdvancedAuditEngine:
    """Blockchain-style tamper-proof audit logging"""
    
    GENESIS_HASH = "0" * 64  # Genesis block hash
    
    def __init__(self):
        # In-memory chain storage (use database in production)
        self.chains: Dict[str, List[AuditEntry]] = {}
        self.chain_tips: Dict[str, ChainTip] = {}
    
    def log_event(
        self,
        bout_id: str,
        event_type: str,
        payload: Dict[str, Any],
        actor: str = "system",
        cv_version: Optional[str] = None,
        judge_device_id: Optional[str] = None,
        scoring_engine_version: Optional[str] = None
    ) -> AuditEntry:
        """
        Log event to audit chain
        
        Args:
            bout_id: Bout identifier
            event_type: Type of event (e.g., 'scoring_output', 'event_logged')
            payload: Event data
            actor: Who triggered the event
            cv_version: CV model version
            judge_device_id: Judge device ID
            scoring_engine_version: Scoring engine version
        
        Returns:
            AuditEntry with chain hash
        """
        # Initialize chain if new bout
        if bout_id not in self.chains:
            self.chains[bout_id] = []
            self.chain_tips[bout_id] = ChainTip(
                bout_id=bout_id,
                current_hash=self.GENESIS_HASH,
                sequence_num=0
            )
        
        # Get previous hash
        previous_hash = self.chain_tips[bout_id].current_hash
        sequence_num = self.chain_tips[bout_id].sequence_num + 1
        
        # Create entry
        entry = AuditEntry(
            bout_id=bout_id,
            sequence_num=sequence_num,
            previous_hash=previous_hash,
            current_hash="",  # Will be calculated
            event_type=event_type,
            payload=payload,
            actor=actor,
            cv_version=cv_version,
            judge_device_id=judge_device_id,
            scoring_engine_version=scoring_engine_version
        )
        
        # Calculate hash: SHA256(previous_hash + payload)
        entry.current_hash = self._calculate_hash(entry)
        
        # Add to chain
        self.chains[bout_id].append(entry)
        
        # Update chain tip
        self.chain_tips[bout_id].current_hash = entry.current_hash
        self.chain_tips[bout_id].sequence_num = sequence_num
        self.chain_tips[bout_id].last_updated = datetime.now(timezone.utc)
        
        logger.info(f"Audit entry {sequence_num} logged for {bout_id}: {event_type}")
        return entry
    
    def _calculate_hash(self, entry: AuditEntry) -> str:
        """
        Calculate SHA256 hash for entry
        
        Hash = SHA256(previous_hash + entry_data)
        """
        # Create deterministic string representation
        data = {
            "sequence_num": entry.sequence_num,
            "previous_hash": entry.previous_hash,
            "event_type": entry.event_type,
            "payload": entry.payload,
            "timestamp": entry.timestamp.isoformat(),
            "actor": entry.actor
        }
        
        data_string = json.dumps(data, sort_keys=True)
        hash_input = entry.previous_hash + data_string
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def verify_chain(self, bout_id: str) -> VerificationResult:
        """
        Verify integrity of audit chain
        
        Returns:
            VerificationResult with tamper detection
        """
        if bout_id not in self.chains:
            return VerificationResult(
                bout_id=bout_id,
                valid=False,
                total_entries=0,
                verified_entries=0,
                tampered=False,
                tamper_details="Chain not found"
            )
        
        chain = self.chains[bout_id]
        total_entries = len(chain)
        verified_entries = 0
        tampered = False
        tamper_at = None
        tamper_details = None
        
        # Verify each entry
        for i, entry in enumerate(chain):
            # Recalculate hash
            expected_hash = self._calculate_hash(entry)
            
            if expected_hash != entry.current_hash:
                # Hash mismatch - tampered!
                tampered = True
                tamper_at = i
                tamper_details = f"Hash mismatch at entry {i}: expected {expected_hash}, got {entry.current_hash}"
                break
            
            # Check previous hash linkage
            if i > 0:
                prev_entry = chain[i-1]
                if entry.previous_hash != prev_entry.current_hash:
                    tampered = True
                    tamper_at = i
                    tamper_details = f"Chain broken at entry {i}: previous_hash mismatch"
                    break
            else:
                # First entry should point to genesis
                if entry.previous_hash != self.GENESIS_HASH:
                    tampered = True
                    tamper_at = i
                    tamper_details = f"Genesis hash mismatch at entry {i}"
                    break
            
            verified_entries += 1
        
        result = VerificationResult(
            bout_id=bout_id,
            valid=not tampered,
            total_entries=total_entries,
            verified_entries=verified_entries,
            tampered=tampered,
            tamper_detected_at=tamper_at,
            tamper_details=tamper_details
        )
        
        if tampered:
            logger.error(f"TAMPER DETECTED in {bout_id}: {tamper_details}")
        else:
            logger.info(f"Chain verified for {bout_id}: {verified_entries}/{total_entries} entries")
        
        return result
    
    def get_chain(self, bout_id: str) -> List[AuditEntry]:
        """Get complete audit chain for bout"""
        return self.chains.get(bout_id, [])
    
    def get_chain_tip(self, bout_id: str) -> Optional[ChainTip]:
        """Get current chain tip"""
        return self.chain_tips.get(bout_id)
