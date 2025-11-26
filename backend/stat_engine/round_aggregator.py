"""
MODULE 2: Round Stats Aggregator

Computes per-round statistics for each fighter.
Uses event_reader to get events, then aggregates into RoundStats.

Handles:
- Strike counting (total, significant, by target)
- Knockdowns and rocked events
- Takedown statistics
- Submission attempts
- Control time calculation (using CONTROL_START/STOP deltas)
"""

import logging
from typing import Dict, List
from datetime import datetime, timezone

from .models import RoundStats
from .event_reader import EventReader

logger = logging.getLogger(__name__)


class RoundStatsAggregator:
    """Aggregates events into per-round statistics"""
    
    def __init__(self, db, event_reader: EventReader):
        self.db = db
        self.event_reader = event_reader
        logger.info("Round Stats Aggregator initialized")
    
    async def aggregate_round(
        self,
        fight_id: str,
        round_num: int,
        fighter_id: str
    ) -> RoundStats:
        """
        Aggregate all events for a fighter in a specific round
        
        Args:
            fight_id: Bout ID
            round_num: Round number
            fighter_id: Fighter ID
        
        Returns:
            RoundStats object with computed statistics
        """
        
        logger.info(f"Aggregating round stats: fight={fight_id}, round={round_num}, fighter={fighter_id}")
        
        # Get all events for this fighter in this round
        events = await self.event_reader.get_fighter_events(
            fight_id=fight_id,
            fighter_id=fighter_id,
            round_num=round_num
        )
        
        # Initialize stats
        stats = RoundStats(
            fight_id=fight_id,
            round_num=round_num,
            fighter_id=fighter_id,
            source_event_count=len(events)
        )
        
        # Process each event
        for event in events:
            event_type = event.get("eventType", "")
            metadata = event.get("metadata", {})
            
            # Classify strike
            strike_info = self.event_reader.classify_strike(event_type, metadata)
            
            if strike_info['is_strike']:
                # Count total strikes
                if strike_info['landed']:
                    stats.total_strikes_landed += 1
                else:
                    stats.total_strikes_attempted += 1
                
                # Count significant strikes
                if strike_info['is_significant']:
                    if strike_info['landed']:
                        stats.sig_strikes_landed += 1
                        
                        # Count by target
                        if strike_info['target'] == 'head':
                            stats.sig_head_landed += 1
                        elif strike_info['target'] == 'body':
                            stats.sig_body_landed += 1
                        elif strike_info['target'] == 'leg':
                            stats.sig_leg_landed += 1
                    else:
                        stats.sig_strikes_attempted += 1
            
            # Check knockdowns
            if self.event_reader.is_knockdown(event_type):
                stats.knockdowns += 1
            
            # Check rocked
            if self.event_reader.is_rocked(event_type):
                stats.rocked_events += 1
            
            # Check takedowns
            td_info = self.event_reader.is_takedown(event_type, metadata)
            if td_info['is_takedown']:
                stats.td_attempts += 1
                if td_info['landed']:
                    stats.td_landed += 1
                if td_info['stuffed']:
                    stats.td_stuffed += 1
            
            # Check submissions
            if self.event_reader.is_submission_attempt(event_type):
                stats.sub_attempts += 1
        
        # Calculate control time
        control_time = await self._calculate_control_time(fight_id, round_num, fighter_id)
        
        stats.ground_control_secs = control_time.get('ground_control', 0)
        stats.clinch_control_secs = control_time.get('clinch_control', 0)
        stats.cage_control_secs = control_time.get('cage_control', 0)
        stats.back_control_secs = control_time.get('back_control', 0)
        stats.mount_secs = control_time.get('mount', 0)
        
        stats.total_control_secs = (
            stats.ground_control_secs +
            stats.clinch_control_secs +
            stats.cage_control_secs +
            stats.back_control_secs +
            stats.mount_secs
        )
        
        stats.last_updated = datetime.now(timezone.utc)
        
        logger.info(
            f"Round stats computed: {stats.sig_strikes_landed} sig strikes, "
            f"{stats.knockdowns} KDs, {stats.total_control_secs}s control"
        )
        
        return stats
    
    async def _calculate_control_time(
        self,
        fight_id: str,
        round_num: int,
        fighter_id: str
    ) -> Dict[str, int]:
        """
        Calculate control time from CONTROL_START/STOP events
        
        Returns:
            Dictionary with control time by type (in seconds)
        """
        
        control_events = await self.event_reader.get_control_events(
            fight_id=fight_id,
            round_num=round_num,
            fighter_id=fighter_id
        )
        
        control_time = {
            'ground_control': 0,
            'clinch_control': 0,
            'cage_control': 0,
            'back_control': 0,
            'mount': 0
        }
        
        # Track active control periods
        active_controls = {}
        
        for event in control_events:
            event_type = event.get("eventType", "")
            metadata = event.get("metadata", {})
            timestamp = event.get("timestamp")
            
            control_type_lower = event_type.lower()
            event_action = metadata.get("type", "")  # 'start' or 'stop'
            
            # Determine control category
            control_category = None
            if "ground top control" in control_type_lower or "top control" in control_type_lower:
                control_category = "ground_control"
            elif "ground back control" in control_type_lower or "back control" in control_type_lower:
                control_category = "back_control"
            elif "cage control" in control_type_lower:
                control_category = "cage_control"
            elif "mount" in control_type_lower:
                control_category = "mount"
            elif "clinch" in control_type_lower:
                control_category = "clinch_control"
            
            if not control_category:
                continue
            
            # Handle start/stop
            if event_action == "start":
                # Store start time
                if metadata.get("startTime"):
                    active_controls[control_category] = metadata["startTime"]
            
            elif event_action == "stop":
                # Calculate duration
                duration = metadata.get("duration", 0)  # Already in seconds
                if duration > 0:
                    control_time[control_category] += duration
                
                # Clear active control
                if control_category in active_controls:
                    del active_controls[control_category]
        
        logger.debug(f"Control time calculated: {control_time}")
        return control_time
    
    async def save_round_stats(self, stats: RoundStats) -> bool:
        """
        Save round stats to database (UPSERT)
        
        Args:
            stats: RoundStats object
        
        Returns:
            True if successful
        """
        
        if not self.db:
            logger.error("Database not available")
            return False
        
        try:
            # Prepare document
            doc = stats.model_dump()
            doc['computed_at'] = doc['computed_at'].isoformat() if isinstance(doc['computed_at'], datetime) else doc['computed_at']
            doc['last_updated'] = doc['last_updated'].isoformat() if isinstance(doc['last_updated'], datetime) else doc['last_updated']
            
            # UPSERT by fight_id + round_num + fighter_id
            query = {
                "fight_id": stats.fight_id,
                "round_num": stats.round_num,
                "fighter_id": stats.fighter_id
            }
            
            result = await self.db.round_stats.update_one(
                query,
                {"$set": doc},
                upsert=True
            )
            
            logger.info(
                f"Saved round stats: fight={stats.fight_id}, round={stats.round_num}, "
                f"fighter={stats.fighter_id}, upserted={result.upserted_id is not None}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving round stats: {e}")
            return False
    
    async def aggregate_and_save(
        self,
        fight_id: str,
        round_num: int,
        fighter_id: str
    ) -> RoundStats:
        """
        Aggregate round stats and save to database
        
        Convenience method that combines aggregate_round and save_round_stats
        """
        
        stats = await self.aggregate_round(fight_id, round_num, fighter_id)
        await self.save_round_stats(stats)
        return stats
    
    async def aggregate_all_fighters_in_round(
        self,
        fight_id: str,
        round_num: int
    ) -> List[RoundStats]:
        """
        Aggregate stats for all fighters in a round
        
        Returns:
            List of RoundStats for each fighter
        """
        
        # Get all fighters in this fight
        fighters = await self.event_reader.get_fight_fighters(fight_id)
        
        logger.info(f"Aggregating round {round_num} for {len(fighters)} fighters")
        
        all_stats = []
        for fighter_id in fighters:
            stats = await self.aggregate_and_save(fight_id, round_num, fighter_id)
            all_stats.append(stats)
        
        return all_stats
