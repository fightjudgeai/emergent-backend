"""
Event Deduplication & Idempotent Upsert Engine
Ensures no duplicate events from double-taps, resends, or reconnections
"""
import hashlib
import time
from typing import Dict, Any, Optional

def generate_event_fingerprint(
    bout_id: str,
    round_id: int,
    judge_id: str,
    fighter_id: str,
    event_type: str,
    timestamp_ms: int,
    device_id: str
) -> str:
    """
    Generate a universal event fingerprint for deduplication
    
    Args:
        bout_id: Unique bout identifier
        round_id: Round number
        judge_id: Judge/operator identifier
        fighter_id: fighter1 or fighter2
        event_type: Type of event (Jab, Cross, KD, etc.)
        timestamp_ms: Client timestamp in milliseconds (rounded to 10ms)
        device_id: Unique device identifier
    
    Returns:
        Fingerprint string used for hashing
    """
    # Round timestamp to nearest 10ms to handle slight timing variations
    rounded_ts = (timestamp_ms // 10) * 10
    
    # Concatenate all components
    fingerprint = f"{bout_id}|{round_id}|{judge_id}|{fighter_id}|{event_type}|{rounded_ts}|{device_id}"
    return fingerprint


def generate_event_hash(fingerprint: str) -> str:
    """
    Generate SHA256 hash from event fingerprint
    
    Args:
        fingerprint: Event fingerprint string
    
    Returns:
        SHA256 hash as hex string
    """
    return hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()


def create_event_chain_hash(
    current_event_hash: str,
    previous_event_hash: Optional[str] = None
) -> str:
    """
    Create a tamper-proof event chain by linking current hash with previous
    
    Args:
        current_event_hash: Hash of current event
        previous_event_hash: Hash of previous event (None for first event)
    
    Returns:
        Chain hash linking current to previous
    """
    if previous_event_hash:
        chain_data = f"{previous_event_hash}:{current_event_hash}"
    else:
        chain_data = f"GENESIS:{current_event_hash}"
    
    return hashlib.sha256(chain_data.encode('utf-8')).hexdigest()


def verify_event_chain(events: list) -> bool:
    """
    Verify integrity of event hash chain
    
    Args:
        events: List of events with event_hash and previous_event_hash
    
    Returns:
        True if chain is valid, False if tampered
    """
    if not events:
        return True
    
    # Sort by sequence_index
    sorted_events = sorted(events, key=lambda e: e.get('sequence_index', 0))
    
    for i, event in enumerate(sorted_events):
        if i == 0:
            # First event should have no previous or GENESIS
            if event.get('previous_event_hash') and event['previous_event_hash'] != 'GENESIS':
                return False
        else:
            # Verify this event's previous_event_hash matches actual previous
            expected_prev = sorted_events[i-1]['event_hash']
            if event.get('previous_event_hash') != expected_prev:
                return False
    
    return True


class EventDedupEngine:
    """
    Engine for handling event deduplication and idempotent upserts
    """
    
    def __init__(self, db):
        self.db = db
        self.sequence_counter = {}  # bout_id -> current sequence
    
    async def get_next_sequence(self, bout_id: str, round_id: int) -> int:
        """Get next sequence index for bout+round"""
        key = f"{bout_id}_{round_id}"
        
        if key not in self.sequence_counter:
            # Get max sequence from database
            result = await self.db.events_v2.find_one(
                {"bout_id": bout_id, "round_id": round_id},
                sort=[("sequence_index", -1)]
            )
            self.sequence_counter[key] = result['sequence_index'] + 1 if result else 0
        else:
            self.sequence_counter[key] += 1
        
        return self.sequence_counter[key]
    
    async def get_previous_event_hash(self, bout_id: str, round_id: int) -> Optional[str]:
        """Get hash of previous event in chain"""
        result = await self.db.events_v2.find_one(
            {"bout_id": bout_id, "round_id": round_id},
            sort=[("sequence_index", -1)]
        )
        return result['event_hash'] if result else None
    
    async def check_duplicate(self, bout_id: str, round_id: int, event_hash: str) -> bool:
        """
        Check if event with this hash already exists
        
        Returns:
            True if duplicate exists, False if new
        """
        result = await self.db.events_v2.find_one({
            "bout_id": bout_id,
            "round_id": round_id,
            "event_hash": event_hash
        })
        return result is not None
    
    async def upsert_event(
        self,
        bout_id: str,
        round_id: int,
        judge_id: str,
        fighter_id: str,
        event_type: str,
        timestamp_ms: int,
        device_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Idempotent event upsert with deduplication
        
        Returns:
            {
                "success": bool,
                "event_id": str,
                "is_duplicate": bool,
                "sequence_index": int
            }
        """
        # Generate fingerprint and hash
        fingerprint = generate_event_fingerprint(
            bout_id, round_id, judge_id, fighter_id, 
            event_type, timestamp_ms, device_id
        )
        event_hash = generate_event_hash(fingerprint)
        
        # Check for duplicate
        is_duplicate = await self.check_duplicate(bout_id, round_id, event_hash)
        
        if is_duplicate:
            # Return existing event info
            existing = await self.db.events_v2.find_one({
                "bout_id": bout_id,
                "round_id": round_id,
                "event_hash": event_hash
            })
            return {
                "success": True,
                "event_id": str(existing['_id']),
                "is_duplicate": True,
                "sequence_index": existing['sequence_index'],
                "message": "Duplicate event ignored (idempotent)"
            }
        
        # Get sequence and previous hash
        sequence_index = await self.get_next_sequence(bout_id, round_id)
        previous_hash = await self.get_previous_event_hash(bout_id, round_id)
        
        # Create chain hash
        chain_hash = create_event_chain_hash(event_hash, previous_hash)
        
        # Create event document
        event_doc = {
            "bout_id": bout_id,
            "round_id": round_id,
            "judge_id": judge_id,
            "fighter_id": fighter_id,
            "event_type": event_type,
            "event_hash": event_hash,
            "event_fingerprint": fingerprint,
            "previous_event_hash": previous_hash or "GENESIS",
            "chain_hash": chain_hash,
            "sequence_index": sequence_index,
            "device_id": device_id,
            "client_timestamp_ms": timestamp_ms,
            "server_timestamp_ms": int(time.time() * 1000),
            "metadata": metadata or {}
        }
        
        # Insert event
        result = await self.db.events_v2.insert_one(event_doc)
        
        return {
            "success": True,
            "event_id": str(result.inserted_id),
            "is_duplicate": False,
            "sequence_index": sequence_index,
            "event_hash": event_hash,
            "message": "Event logged successfully"
        }
