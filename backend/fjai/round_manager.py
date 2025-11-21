"""
Fight Judge AI - Round Lifecycle Manager
Handles round creation, event ingestion, scoring, and locking
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
import logging
import hashlib
import json
from .models import RoundState, CombatEvent, RoundScore
from .event_pipeline import EventPipeline
from .scoring_engine import WeightedScoringEngine
from .audit_layer import AuditLayer

logger = logging.getLogger(__name__)


class RoundManager:
    """Manage round lifecycle"""
    
    def __init__(self, db, event_pipeline: EventPipeline = None, scoring_engine: WeightedScoringEngine = None):
        self.db = db
        self.event_pipeline = event_pipeline or EventPipeline()
        self.scoring_engine = scoring_engine or WeightedScoringEngine()
        self.audit_layer = AuditLayer(db)
        
        # Active rounds cache
        self.active_rounds: Dict[str, RoundState] = {}
    
    async def open_round(self, bout_id: str, round_num: int) -> RoundState:
        """
        Open new round
        """
        round_state = RoundState(
            bout_id=bout_id,
            round_num=round_num,
            status="open"
        )
        
        # Save to database
        await self.db.fjai_rounds.insert_one(self._serialize_for_mongo(round_state.model_dump()))
        
        # Add to active rounds
        self.active_rounds[round_state.round_id] = round_state
        
        # Audit log
        await self.audit_layer.log_action(
            bout_id=bout_id,
            round_id=round_state.round_id,
            action="round_opened",
            actor="system",
            data={"round_num": round_num}
        )
        
        logger.info(f"Round opened: {round_state.round_id} (bout: {bout_id}, round: {round_num})")
        return round_state
    
    async def add_event(self, round_id: str, event: CombatEvent) -> bool:
        """
        Add event to round
        
        Returns:
            True if event accepted, False if rejected
        """
        # Get round
        round_state = await self._get_round(round_id)
        if not round_state:
            logger.error(f"Round not found: {round_id}")
            return False
        
        if round_state.status == "locked":
            logger.warning(f"Cannot add event to locked round: {round_id}")
            return False
        
        # Process event through pipeline
        accepted, reason = self.event_pipeline.process_event(event)
        
        if not accepted:
            logger.info(f"Event rejected: {reason}")
            return False
        
        # Add to round
        round_state.events.append(event)
        
        # Update database
        await self.db.fjai_rounds.update_one(
            {"round_id": round_id},
            {"$push": {"events": self._serialize_for_mongo(event.model_dump())}}
        )
        
        # Audit log
        await self.audit_layer.log_action(
            bout_id=round_state.bout_id,
            round_id=round_id,
            action="event_added",
            actor=event.source.value,
            data=self._serialize_for_mongo(event.model_dump())
        )
        
        logger.info(f"Event added to round {round_id}: {event.event_type}")
        return True
    
    async def calculate_score(self, round_id: str) -> Optional[RoundScore]:
        """
        Calculate live round score
        """
        # Get round
        round_state = await self._get_round(round_id)
        if not round_state:
            return None
        
        # Calculate score
        score = self.scoring_engine.calculate_round_score(
            events=round_state.events,
            bout_id=round_state.bout_id,
            round_id=round_id,
            round_num=round_state.round_num
        )
        
        # Update round state
        round_state.fighter_a_score = score.fighter_a_score
        round_state.fighter_b_score = score.fighter_b_score
        round_state.score_card = score.score_card
        round_state.winner = score.winner
        round_state.status = "scoring"
        
        # Update database
        await self.db.fjai_rounds.update_one(
            {"round_id": round_id},
            {"$set": {
                "fighter_a_score": score.fighter_a_score,
                "fighter_b_score": score.fighter_b_score,
                "score_card": score.score_card,
                "winner": score.winner,
                "status": "scoring"
            }}
        )
        
        return score
    
    async def lock_round(self, round_id: str) -> bool:
        """
        Lock round (finalize score)
        """
        # Get round
        round_state = await self._get_round(round_id)
        if not round_state:
            return False
        
        if round_state.status == "locked":
            logger.warning(f"Round already locked: {round_id}")
            return False
        
        # Calculate final score if not already done
        if not round_state.score_card:
            await self.calculate_score(round_id)
            round_state = await self._get_round(round_id)  # Reload
        
        # Generate event hash
        event_hash = self._generate_event_hash(round_state.events)
        
        # Lock round
        round_state.status = "locked"
        round_state.locked_at = datetime.now(timezone.utc)
        round_state.event_hash = event_hash
        
        # Update database
        await self.db.fjai_rounds.update_one(
            {"round_id": round_id},
            {"$set": {
                "status": "locked",
                "locked_at": round_state.locked_at.isoformat(),
                "event_hash": event_hash
            }}
        )
        
        # Audit log
        await self.audit_layer.log_action(
            bout_id=round_state.bout_id,
            round_id=round_id,
            action="round_locked",
            actor="system",
            data={"event_hash": event_hash, "final_score": round_state.score_card}
        )
        
        logger.info(f"Round locked: {round_id} with hash {event_hash}")
        return True
    
    async def _get_round(self, round_id: str) -> Optional[RoundState]:
        """Get round from cache or database"""
        if round_id in self.active_rounds:
            return self.active_rounds[round_id]
        
        round_doc = await self.db.fjai_rounds.find_one({"round_id": round_id})
        if round_doc:
            round_state = RoundState(**round_doc)
            self.active_rounds[round_id] = round_state
            return round_state
        
        return None
    
    def _generate_event_hash(self, events: List[CombatEvent]) -> str:
        """Generate SHA256 hash of all events (CombatIQ style)"""
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp_ms)
        
        # Create deterministic string representation
        event_data = json.dumps(
            [self._serialize_for_mongo(e.model_dump()) for e in sorted_events],
            sort_keys=True
        )
        
        # Generate SHA256 hash
        return hashlib.sha256(event_data.encode()).hexdigest()
    
    def _serialize_for_mongo(self, data: Dict) -> Dict:
        """Convert datetime objects to ISO strings for MongoDB"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_for_mongo(value)
            elif isinstance(value, list):
                serialized[key] = [
                    self._serialize_for_mongo(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                serialized[key] = value
        return serialized
