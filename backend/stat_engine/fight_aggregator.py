"""
MODULE 3: Fight Stats Aggregator

Sums all round_stats by fight_id + fighter_id.
Produces fight-level statistics with computed metrics.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from .models import FightStats, RoundStats

logger = logging.getLogger(__name__)


class FightStatsAggregator:
    """Aggregates round stats into fight-level statistics"""
    
    def __init__(self, db):
        self.db = db
        logger.info("Fight Stats Aggregator initialized")
    
    async def aggregate_fight(self, fight_id: str, fighter_id: str) -> FightStats:
        """
        Aggregate all round stats for a fighter in a fight
        
        Args:
            fight_id: Bout ID
            fighter_id: Fighter ID
        
        Returns:
            FightStats object with summed statistics
        """
        
        logger.info(f"Aggregating fight stats: fight={fight_id}, fighter={fighter_id}")
        
        # Get all round stats for this fighter in this fight
        round_stats = await self._get_round_stats(fight_id, fighter_id)
        
        if not round_stats:
            logger.warning(f"No round stats found for fight={fight_id}, fighter={fighter_id}")
            return FightStats(
                fight_id=fight_id,
                fighter_id=fighter_id,
                total_rounds=0
            )
        
        # Initialize fight stats
        stats = FightStats(
            fight_id=fight_id,
            fighter_id=fighter_id,
            total_rounds=len(round_stats),
            rounds_aggregated=len(round_stats)
        )
        
        # Sum all round stats
        for round_stat in round_stats:
            stats.total_strikes_attempted += round_stat.total_strikes_attempted
            stats.total_strikes_landed += round_stat.total_strikes_landed
            stats.sig_strikes_attempted += round_stat.sig_strikes_attempted
            stats.sig_strikes_landed += round_stat.sig_strikes_landed
            
            stats.sig_head_landed += round_stat.sig_head_landed
            stats.sig_body_landed += round_stat.sig_body_landed
            stats.sig_leg_landed += round_stat.sig_leg_landed
            
            stats.knockdowns += round_stat.knockdowns
            stats.rocked_events += round_stat.rocked_events
            
            stats.td_attempts += round_stat.td_attempts
            stats.td_landed += round_stat.td_landed
            stats.td_stuffed += round_stat.td_stuffed
            
            stats.sub_attempts += round_stat.sub_attempts
            
            stats.ground_control_secs += round_stat.ground_control_secs
            stats.clinch_control_secs += round_stat.clinch_control_secs
            stats.cage_control_secs += round_stat.cage_control_secs
            stats.back_control_secs += round_stat.back_control_secs
            stats.mount_secs += round_stat.mount_secs
            stats.total_control_secs += round_stat.total_control_secs
        
        # Compute derived metrics
        stats.sig_strike_accuracy = self._calculate_accuracy(
            stats.sig_strikes_landed,
            stats.sig_strikes_attempted + stats.sig_strikes_landed
        )
        
        stats.td_accuracy = self._calculate_accuracy(
            stats.td_landed,
            stats.td_attempts
        )
        
        # Strikes per minute (assuming 5 minutes per round)
        total_fight_minutes = stats.total_rounds * 5
        if total_fight_minutes > 0:
            stats.strikes_per_minute = stats.total_strikes_landed / total_fight_minutes
        
        # Control time percentage (of total fight time)
        total_fight_seconds = stats.total_rounds * 5 * 60
        if total_fight_seconds > 0:
            stats.control_time_percentage = (stats.total_control_secs / total_fight_seconds) * 100
        
        stats.last_updated = datetime.now(timezone.utc)
        
        logger.info(
            f"Fight stats computed: {stats.sig_strikes_landed} sig strikes, "
            f"{stats.knockdowns} KDs, {stats.sig_strike_accuracy:.1f}% accuracy"
        )
        
        return stats
    
    async def _get_round_stats(self, fight_id: str, fighter_id: str) -> List[RoundStats]:
        """Get all round stats for a fighter in a fight"""
        
        if not self.db:
            return []
        
        try:
            cursor = self.db.round_stats.find({
                "fight_id": fight_id,
                "fighter_id": fighter_id
            }).sort("round_num", 1)
            
            docs = await cursor.to_list(length=None)
            
            # Convert to RoundStats objects
            round_stats = []
            for doc in docs:
                # Remove MongoDB _id
                doc.pop('_id', None)
                round_stats.append(RoundStats(**doc))
            
            return round_stats
        
        except Exception as e:
            logger.error(f"Error getting round stats: {e}")
            return []
    
    def _calculate_accuracy(self, landed: int, total: int) -> float:
        """Calculate accuracy percentage"""
        if total == 0:
            return 0.0
        return (landed / total) * 100
    
    async def save_fight_stats(self, stats: FightStats) -> bool:
        """
        Save fight stats to database (UPSERT)
        
        Args:
            stats: FightStats object
        
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
            
            # UPSERT by fight_id + fighter_id
            query = {
                "fight_id": stats.fight_id,
                "fighter_id": stats.fighter_id
            }
            
            result = await self.db.fight_stats.update_one(
                query,
                {"$set": doc},
                upsert=True
            )
            
            logger.info(
                f"Saved fight stats: fight={stats.fight_id}, fighter={stats.fighter_id}, "
                f"upserted={result.upserted_id is not None}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving fight stats: {e}")
            return False
    
    async def aggregate_and_save(self, fight_id: str, fighter_id: str) -> FightStats:
        """
        Aggregate fight stats and save to database
        
        Convenience method that combines aggregate_fight and save_fight_stats
        """
        
        stats = await self.aggregate_fight(fight_id, fighter_id)
        await self.save_fight_stats(stats)
        return stats
    
    async def aggregate_all_fighters_in_fight(self, fight_id: str) -> List[FightStats]:
        """
        Aggregate stats for all fighters in a fight
        
        Returns:
            List of FightStats for each fighter
        """
        
        if not self.db:
            return []
        
        try:
            # Get unique fighters from round_stats
            fighters = await self.db.round_stats.distinct("fighter_id", {"fight_id": fight_id})
            
            logger.info(f"Aggregating fight stats for {len(fighters)} fighters")
            
            all_stats = []
            for fighter_id in fighters:
                stats = await self.aggregate_and_save(fight_id, fighter_id)
                all_stats.append(stats)
            
            return all_stats
        
        except Exception as e:
            logger.error(f"Error aggregating all fighters: {e}")
            return []
