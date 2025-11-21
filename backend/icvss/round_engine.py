"""
ICVSS Live Round Engine
/round/open, /round/event, /round/score, /round/lock
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging
import json
from .models import ICVSSRound, CVEvent, ScoreResponse
from .event_processor import EventProcessor
from .scoring_engine import HybridScoringEngine
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)


def serialize_for_mongo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert datetime objects to ISO strings for MongoDB storage"""
    serialized = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, dict):
            serialized[key] = serialize_for_mongo(value)
        elif isinstance(value, list):
            serialized[key] = [serialize_for_mongo(item) if isinstance(item, dict) else item for item in value]
        else:
            serialized[key] = value
    return serialized


class RoundEngine:
    """Manage ICVSS round lifecycle"""
    
    def __init__(self, db):
        self.db = db
        self.event_processor = EventProcessor()
        self.scoring_engine = HybridScoringEngine()
        self.audit_logger = AuditLogger(db)
        self.active_rounds: Dict[str, ICVSSRound] = {}
    
    async def open_round(self, bout_id: str, round_num: int) -> ICVSSRound:
        """Open a new ICVSS round"""
        round_data = ICVSSRound(
            bout_id=bout_id,
            round_num=round_num,
            status="open"
        )
        
        # Save to database
        await self.db.icvss_rounds.insert_one(round_data.model_dump())
        
        # Add to active rounds
        self.active_rounds[round_data.round_id] = round_data
        
        # Audit log
        await self.audit_logger.log_action(
            bout_id=bout_id,
            round_id=round_data.round_id,
            action="round_opened",
            actor="system",
            data={"round_num": round_num}
        )
        
        logger.info(f"Round opened: {round_data.round_id} (bout: {bout_id}, round: {round_num})")
        return round_data
    
    async def add_event(self, round_id: str, event: CVEvent) -> bool:
        """Add event to round"""
        round_data = self.active_rounds.get(round_id)
        if not round_data:
            # Try loading from database
            round_doc = await self.db.icvss_rounds.find_one({"round_id": round_id})
            if not round_doc:
                logger.error(f"Round not found: {round_id}")
                return False
            round_data = ICVSSRound(**round_doc)
            self.active_rounds[round_id] = round_data
        
        if round_data.status == "locked":
            logger.warning(f"Cannot add event to locked round: {round_id}")
            return False
        
        # Process event
        accepted, reason = self.event_processor.process_event(event)
        
        if accepted:
            # Add to round
            if event.source.value == "cv_system":
                round_data.cv_events.append(event)
            else:
                round_data.judge_events.append(event.model_dump())
            
            # Update database with proper datetime serialization
            event_dict = serialize_for_mongo(event.model_dump())
            
            await self.db.icvss_rounds.update_one(
                {"round_id": round_id},
                {"$push": {"cv_events" if event.source.value == "cv_system" else "judge_events": event_dict}}
            )
            
            # Audit log with proper datetime serialization
            audit_data = serialize_for_mongo(event.model_dump())
            
            await self.audit_logger.log_action(
                bout_id=round_data.bout_id,
                round_id=round_id,
                action="event_added",
                actor=event.source.value,
                data=audit_data
            )
            
            logger.info(f"Event added to round {round_id}: {event.event_type}")
            return True
        else:
            logger.warning(f"Event rejected: {reason}")
            return False
    
    async def calculate_score(self, round_id: str) -> Optional[ScoreResponse]:
        """Calculate current score for round"""
        round_data = self.active_rounds.get(round_id)
        if not round_data:
            round_doc = await self.db.icvss_rounds.find_one({"round_id": round_id})
            if not round_doc:
                return None
            round_data = ICVSSRound(**round_doc)
        
        # Calculate hybrid score
        score_result = self.scoring_engine.calculate_hybrid_score(
            cv_events=round_data.cv_events,
            judge_events=round_data.judge_events
        )
        
        # Create response
        response = ScoreResponse(
            bout_id=round_data.bout_id,
            round_id=round_id,
            round_num=round_data.round_num,
            fighter1_score=int(score_result["score_card"].split("-")[0]),
            fighter2_score=int(score_result["score_card"].split("-")[1]),
            score_card=score_result["score_card"],
            winner=score_result["winner"],
            fighter1_breakdown=score_result["fighter1_breakdown"],
            fighter2_breakdown=score_result["fighter2_breakdown"],
            confidence=0.85,
            cv_event_count=score_result["cv_event_count"],
            judge_event_count=score_result["judge_event_count"],
            total_events=score_result["cv_event_count"] + score_result["judge_event_count"],
            cv_contribution=score_result["cv_contribution"],
            judge_contribution=score_result["judge_contribution"]
        )
        
        # Update round data
        round_data.fighter1_score = response.fighter1_score
        round_data.fighter2_score = response.fighter2_score
        round_data.score_card = response.score_card
        round_data.winner = response.winner
        round_data.score_breakdown = score_result
        
        # Save to database
        await self.db.icvss_rounds.update_one(
            {"round_id": round_id},
            {"$set": {
                "fighter1_score": response.fighter1_score,
                "fighter2_score": response.fighter2_score,
                "score_card": response.score_card,
                "winner": response.winner,
                "score_breakdown": score_result
            }}
        )
        
        logger.info(f"Score calculated for round {round_id}: {response.score_card}")
        return response
    
    async def lock_round(self, round_id: str) -> bool:
        """Lock round (finalize score)"""
        round_data = self.active_rounds.get(round_id)
        if not round_data:
            return False
        
        # Calculate final score
        final_score = await self.calculate_score(round_id)
        
        # Generate event hash
        event_hash = self.audit_logger.generate_event_hash(
            round_data.cv_events + round_data.judge_events
        )
        
        # Update status
        round_data.status = "locked"
        round_data.locked_at = datetime.now(timezone.utc)
        round_data.event_hash = event_hash
        
        # Save to database
        await self.db.icvss_rounds.update_one(
            {"round_id": round_id},
            {"$set": {
                "status": "locked",
                "locked_at": round_data.locked_at.isoformat(),
                "event_hash": event_hash
            }}
        )
        
        # Audit log
        await self.audit_logger.log_action(
            bout_id=round_data.bout_id,
            round_id=round_id,
            action="round_locked",
            actor="system",
            data={"event_hash": event_hash, "final_score": final_score.model_dump() if final_score else None}
        )
        
        logger.info(f"Round locked: {round_id} with hash {event_hash}")
        return True
    
    async def get_round(self, round_id: str) -> Optional[ICVSSRound]:
        """Get round data"""
        if round_id in self.active_rounds:
            return self.active_rounds[round_id]
        
        round_doc = await self.db.icvss_rounds.find_one({"round_id": round_id})
        if round_doc:
            return ICVSSRound(**round_doc)
        return None

    async def get_active_rounds_count(self) -> int:
        """Get count of currently active rounds"""
        return len([r for r in self.active_rounds.values() if r.status == "open"])
    
    async def get_event_processing_stats(self) -> Dict:
        """Get event processing statistics from last 5 minutes"""
        from datetime import timedelta
        
        # Calculate time window (last 5 minutes)
        time_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        # Get recent events from all active rounds
        total_events = 0
        total_latency = 0
        error_count = 0
        dedup_count = 0
        
        for round_data in self.active_rounds.values():
            # Count CV and judge events
            cv_events = len(round_data.cv_events)
            judge_events = len(round_data.judge_events)
            total_events += cv_events + judge_events
            
            # Get dedup stats from event processor
            dedup_count += self.event_processor.dedup_count
        
        # Calculate metrics
        avg_latency = total_latency / total_events if total_events > 0 else 0
        error_rate = error_count / total_events if total_events > 0 else 0
        dedup_rate = dedup_count / total_events if total_events > 0 else 0
        
        return {
            "total_processed": total_events,
            "recent_count": total_events,
            "processing_latency_ms": round(avg_latency, 2),
            "error_rate": round(error_rate, 4),
            "dedup_rate": round(dedup_rate, 4)
        }

