"""
MODULE 4: Career Stats Aggregator

Aggregates all fight_stats per fighter_id into career statistics.
Computes advanced lifetime metrics.

Typically run as nightly job.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from .models import CareerStats, FightStats

logger = logging.getLogger(__name__)


class CareerStatsAggregator:
    """Aggregates fight stats into career-level statistics"""
    
    def __init__(self, db):
        self.db = db
        logger.info("Career Stats Aggregator initialized")
    
    async def aggregate_career(self, fighter_id: str) -> CareerStats:
        """
        Aggregate all fight stats for a fighter's career
        
        Args:
            fighter_id: Fighter ID
        
        Returns:
            CareerStats object with lifetime statistics
        """
        
        logger.info(f"Aggregating career stats for fighter={fighter_id}")
        
        # Get all fight stats for this fighter
        fight_stats = await self._get_fight_stats(fighter_id)
        
        if not fight_stats:
            logger.warning(f"No fight stats found for fighter={fighter_id}")
            return CareerStats(
                fighter_id=fighter_id,
                total_fights=0,
                total_rounds=0
            )
        
        # Initialize career stats
        stats = CareerStats(
            fighter_id=fighter_id,
            total_fights=len(fight_stats),
            fights_aggregated=len(fight_stats)
        )
        
        # Sum all fight stats
        for fight_stat in fight_stats:
            stats.total_rounds += fight_stat.total_rounds
            
            stats.total_strikes_attempted += fight_stat.total_strikes_attempted
            stats.total_strikes_landed += fight_stat.total_strikes_landed
            stats.sig_strikes_attempted += fight_stat.sig_strikes_attempted
            stats.sig_strikes_landed += fight_stat.sig_strikes_landed
            
            stats.sig_head_landed += fight_stat.sig_head_landed
            stats.sig_body_landed += fight_stat.sig_body_landed
            stats.sig_leg_landed += fight_stat.sig_leg_landed
            
            stats.knockdowns += fight_stat.knockdowns
            stats.rocked_events += fight_stat.rocked_events
            
            stats.td_attempts += fight_stat.td_attempts
            stats.td_landed += fight_stat.td_landed
            stats.td_stuffed += fight_stat.td_stuffed
            
            stats.sub_attempts += fight_stat.sub_attempts
            
            stats.ground_control_secs += fight_stat.ground_control_secs
            stats.clinch_control_secs += fight_stat.clinch_control_secs
            stats.cage_control_secs += fight_stat.cage_control_secs
            stats.back_control_secs += fight_stat.back_control_secs
            stats.mount_secs += fight_stat.mount_secs
            stats.total_control_secs += fight_stat.total_control_secs
        
        # Compute advanced career metrics
        
        # Average strikes per minute (across all rounds)
        total_career_minutes = stats.total_rounds * 5
        if total_career_minutes > 0:
            stats.avg_sig_strikes_per_min = stats.sig_strikes_landed / total_career_minutes
        
        # Average significant strike accuracy
        total_sig_strikes = stats.sig_strikes_attempted + stats.sig_strikes_landed
        if total_sig_strikes > 0:
            stats.avg_sig_strike_accuracy = (stats.sig_strikes_landed / total_sig_strikes) * 100
        
        # Average takedown accuracy
        if stats.td_attempts > 0:
            stats.avg_td_accuracy = (stats.td_landed / stats.td_attempts) * 100
        
        # Average control time per fight
        if stats.total_fights > 0:
            stats.avg_control_time_per_fight = stats.total_control_secs / stats.total_fights
        
        # Knockdowns per 15 minutes
        total_career_15min_periods = total_career_minutes / 15
        if total_career_15min_periods > 0:
            stats.knockdowns_per_15min = stats.knockdowns / total_career_15min_periods
        
        # Takedown defense percentage (stuffed / attempts against)
        # Note: This requires tracking opponent's TD attempts, using available data
        if stats.td_stuffed > 0:
            stats.td_defense_percentage = (stats.td_stuffed / (stats.td_stuffed + stats.td_landed)) * 100
        
        stats.last_updated = datetime.now(timezone.utc)
        
        logger.info(
            f"Career stats computed: {stats.total_fights} fights, "
            f"{stats.sig_strikes_landed} sig strikes, {stats.avg_sig_strike_accuracy:.1f}% accuracy"
        )
        
        return stats
    
    async def _get_fight_stats(self, fighter_id: str) -> List[FightStats]:
        """Get all fight stats for a fighter"""
        
        if not self.db:
            return []
        
        try:
            cursor = self.db.fight_stats.find({
                "fighter_id": fighter_id
            })
            
            docs = await cursor.to_list(length=None)
            
            # Convert to FightStats objects
            fight_stats = []
            for doc in docs:
                # Remove MongoDB _id
                doc.pop('_id', None)
                fight_stats.append(FightStats(**doc))
            
            return fight_stats
        
        except Exception as e:
            logger.error(f"Error getting fight stats: {e}")
            return []
    
    async def save_career_stats(self, stats: CareerStats) -> bool:
        """
        Save career stats to database (UPSERT)
        
        Args:
            stats: CareerStats object
        
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
            
            # UPSERT by fighter_id
            query = {"fighter_id": stats.fighter_id}
            
            result = await self.db.career_stats.update_one(
                query,
                {"$set": doc},
                upsert=True
            )
            
            logger.info(
                f"Saved career stats: fighter={stats.fighter_id}, "
                f"upserted={result.upserted_id is not None}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving career stats: {e}")
            return False
    
    async def aggregate_and_save(self, fighter_id: str) -> CareerStats:
        """
        Aggregate career stats and save to database
        
        Convenience method that combines aggregate_career and save_career_stats
        """
        
        stats = await self.aggregate_career(fighter_id)
        await self.save_career_stats(stats)
        return stats
    
    async def aggregate_all_fighters(self) -> List[CareerStats]:
        """
        Aggregate career stats for all fighters (nightly job)
        
        Returns:
            List of CareerStats for all fighters
        """
        
        if not self.db:
            return []
        
        try:
            # Get all unique fighter IDs from fight_stats
            fighters = await self.db.fight_stats.distinct("fighter_id")
            
            logger.info(f"Aggregating career stats for {len(fighters)} fighters (nightly job)")
            
            all_stats = []
            for fighter_id in fighters:
                try:
                    stats = await self.aggregate_and_save(fighter_id)
                    all_stats.append(stats)
                except Exception as e:
                    logger.error(f"Error aggregating fighter {fighter_id}: {e}")
                    continue
            
            logger.info(f"Successfully aggregated career stats for {len(all_stats)} fighters")
            return all_stats
        
        except Exception as e:
            logger.error(f"Error in nightly aggregation: {e}")
            return []
