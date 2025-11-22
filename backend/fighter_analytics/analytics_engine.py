"""
Fighter Analytics - Analytics Engine
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone
from .models import (
    FighterProfile,
    BoutResult,
    PerformanceStats,
    LeaderboardEntry,
    FighterComparison
)

logger = logging.getLogger(__name__)


class FighterAnalyticsEngine:
    """Analytics engine for fighter statistics"""
    
    def __init__(self, db=None):
        self.db = db
    
    async def create_fighter(self, fighter: FighterProfile) -> FighterProfile:
        """Create a new fighter profile"""
        if not self.db:
            logger.warning("Database not available")
            return fighter
        
        try:
            fighter_dict = fighter.model_dump()
            fighter_dict['created_at'] = fighter_dict['created_at'].isoformat()
            fighter_dict['updated_at'] = fighter_dict['updated_at'].isoformat()
            
            await self.db.fighters.insert_one(fighter_dict)
            logger.info(f"Fighter created: {fighter.name} [{fighter.id}]")
            return fighter
        
        except Exception as e:
            logger.error(f"Error creating fighter: {e}")
            raise
    
    async def get_fighter(self, fighter_id: str) -> Optional[FighterProfile]:
        """Get fighter by ID"""
        if not self.db:
            return None
        
        try:
            fighter_dict = await self.db.fighters.find_one({"id": fighter_id}, {"_id": 0})
            
            if fighter_dict:
                fighter_dict['created_at'] = datetime.fromisoformat(fighter_dict['created_at'])
                fighter_dict['updated_at'] = datetime.fromisoformat(fighter_dict['updated_at'])
                return FighterProfile(**fighter_dict)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting fighter: {e}")
            return None
    
    async def list_fighters(self, limit: int = 100, skip: int = 0) -> List[FighterProfile]:
        """List all fighters"""
        if not self.db:
            return []
        
        try:
            cursor = self.db.fighters.find({}, {"_id": 0}).skip(skip).limit(limit)
            fighters = await cursor.to_list(length=limit)
            
            return [
                FighterProfile(
                    **{**f, 'created_at': datetime.fromisoformat(f['created_at']),
                       'updated_at': datetime.fromisoformat(f['updated_at'])}
                )
                for f in fighters
            ]
        
        except Exception as e:
            logger.error(f"Error listing fighters: {e}")
            return []
    
    async def update_fighter(self, fighter_id: str, updates: dict) -> Optional[FighterProfile]:
        """Update fighter profile"""
        if not self.db:
            return None
        
        try:
            updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            result = await self.db.fighters.update_one(
                {"id": fighter_id},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                return await self.get_fighter(fighter_id)
            
            return None
        
        except Exception as e:
            logger.error(f"Error updating fighter: {e}")
            return None
    
    async def delete_fighter(self, fighter_id: str) -> bool:
        """Delete fighter profile"""
        if not self.db:
            return False
        
        try:
            result = await self.db.fighters.delete_one({"id": fighter_id})
            
            if result.deleted_count > 0:
                # Also delete bout history
                await self.db.bout_results.delete_many({"$or": [
                    {"fighter_id": fighter_id},
                    {"opponent_id": fighter_id}
                ]})
                logger.info(f"Fighter deleted: {fighter_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error deleting fighter: {e}")
            return False
    
    async def add_bout_result(self, fighter_id: str, bout: BoutResult) -> bool:
        """Add bout result to fighter history"""
        if not self.db:
            return False
        
        try:
            # Store bout result
            bout_dict = bout.model_dump()
            bout_dict['fighter_id'] = fighter_id
            bout_dict['date'] = bout_dict['date'].isoformat()
            
            await self.db.bout_results.insert_one(bout_dict)
            
            # Update fighter record
            fighter = await self.get_fighter(fighter_id)
            if not fighter:
                return False
            
            updates = {
                'total_fights': fighter.total_fights + 1
            }
            
            if bout.result == "win":
                updates['record_wins'] = fighter.record_wins + 1
            elif bout.result == "loss":
                updates['record_losses'] = fighter.record_losses + 1
            elif bout.result == "draw":
                updates['record_draws'] = fighter.record_draws + 1
            
            await self.update_fighter(fighter_id, updates)
            
            logger.info(f"Bout result added for fighter {fighter_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding bout result: {e}")
            return False
    
    async def get_fighter_history(self, fighter_id: str) -> List[BoutResult]:
        """Get fighter's bout history"""
        if not self.db:
            return []
        
        try:
            cursor = self.db.bout_results.find(
                {"fighter_id": fighter_id},
                {"_id": 0}
            ).sort("date", -1)
            
            bouts = await cursor.to_list(length=1000)
            
            return [
                BoutResult(**{**b, 'date': datetime.fromisoformat(b['date'])})
                for b in bouts
            ]
        
        except Exception as e:
            logger.error(f"Error getting fighter history: {e}")
            return []
    
    async def calculate_stats(self, fighter_id: str) -> Optional[PerformanceStats]:
        """Calculate performance statistics for a fighter"""
        fighter = await self.get_fighter(fighter_id)
        if not fighter:
            return None
        
        history = await self.get_fighter_history(fighter_id)
        
        if not history:
            # Return empty stats
            return PerformanceStats(
                fighter_id=fighter.id,
                fighter_name=fighter.name,
                total_fights=0,
                wins=0,
                losses=0,
                draws=0,
                win_rate=0.0,
                total_strikes_landed=0,
                total_strikes_attempted=0,
                strike_accuracy=0.0,
                avg_strikes_per_fight=0.0,
                knockdowns_total=0,
                total_takedowns_landed=0,
                total_takedowns_attempted=0,
                takedown_success_rate=0.0,
                avg_control_time_seconds=0.0,
                submission_attempts_total=0,
                ko_tko_wins=0,
                submission_wins=0,
                decision_wins=0,
                finish_rate=0.0,
                last_5_results=[],
                current_streak="0"
            )
        
        # Aggregate statistics
        total_fights = len(history)
        wins = sum(1 for b in history if b.result == "win")
        losses = sum(1 for b in history if b.result == "loss")
        draws = sum(1 for b in history if b.result == "draw")
        
        # Striking stats
        total_strikes_landed = sum(b.strikes_landed for b in history)
        total_strikes_attempted = sum(b.strikes_attempted for b in history)
        strike_accuracy = (total_strikes_landed / total_strikes_attempted * 100) if total_strikes_attempted > 0 else 0.0
        avg_strikes_per_fight = total_strikes_landed / total_fights if total_fights > 0 else 0.0
        knockdowns_total = sum(b.knockdowns_scored for b in history)
        
        # Grappling stats
        total_takedowns_landed = sum(b.takedowns_landed for b in history)
        total_takedowns_attempted = sum(b.takedowns_attempted for b in history)
        takedown_success_rate = (total_takedowns_landed / total_takedowns_attempted * 100) if total_takedowns_attempted > 0 else 0.0
        avg_control_time_seconds = sum(b.control_time_seconds for b in history) / total_fights if total_fights > 0 else 0.0
        submission_attempts_total = sum(b.submission_attempts for b in history)
        
        # Finish stats
        ko_tko_wins = sum(1 for b in history if b.result == "win" and b.method in ["KO", "TKO"])
        submission_wins = sum(1 for b in history if b.result == "win" and b.method == "Submission")
        decision_wins = sum(1 for b in history if b.result == "win" and b.method == "Decision")
        finish_rate = ((ko_tko_wins + submission_wins) / wins * 100) if wins > 0 else 0.0
        
        # Last 5 results
        last_5 = [b.result[0].upper() for b in history[:5]]
        
        # Current streak
        if history:
            streak_type = history[0].result[0].upper()
            streak_count = 1
            for bout in history[1:]:
                if bout.result[0].upper() == streak_type:
                    streak_count += 1
                else:
                    break
            current_streak = f"{streak_count}{streak_type}"
        else:
            current_streak = "0"
        
        return PerformanceStats(
            fighter_id=fighter.id,
            fighter_name=fighter.name,
            total_fights=total_fights,
            wins=wins,
            losses=losses,
            draws=draws,
            win_rate=(wins / total_fights * 100) if total_fights > 0 else 0.0,
            total_strikes_landed=total_strikes_landed,
            total_strikes_attempted=total_strikes_attempted,
            strike_accuracy=round(strike_accuracy, 2),
            avg_strikes_per_fight=round(avg_strikes_per_fight, 2),
            knockdowns_total=knockdowns_total,
            total_takedowns_landed=total_takedowns_landed,
            total_takedowns_attempted=total_takedowns_attempted,
            takedown_success_rate=round(takedown_success_rate, 2),
            avg_control_time_seconds=round(avg_control_time_seconds, 2),
            submission_attempts_total=submission_attempts_total,
            ko_tko_wins=ko_tko_wins,
            submission_wins=submission_wins,
            decision_wins=decision_wins,
            finish_rate=round(finish_rate, 2),
            last_5_results=last_5,
            current_streak=current_streak
        )
    
    async def get_leaderboard(self, weight_class: Optional[str] = None, limit: int = 20) -> List[LeaderboardEntry]:
        """Get fighter leaderboard/rankings"""
        fighters = await self.list_fighters(limit=1000)
        
        # Filter by weight class if specified
        if weight_class:
            fighters = [f for f in fighters if f.weight_class == weight_class]
        
        # Calculate stats for each fighter and sort
        leaderboard = []
        
        for fighter in fighters:
            if fighter.total_fights == 0:
                continue
            
            stats = await self.calculate_stats(fighter.id)
            if not stats:
                continue
            
            leaderboard.append(LeaderboardEntry(
                rank=0,  # Will be set after sorting
                fighter_id=fighter.id,
                fighter_name=fighter.name,
                weight_class=fighter.weight_class,
                record=f"{fighter.record_wins}-{fighter.record_losses}-{fighter.record_draws}",
                win_rate=stats.win_rate,
                strike_accuracy=stats.strike_accuracy,
                takedown_success_rate=stats.takedown_success_rate,
                finish_rate=stats.finish_rate,
                total_fights=fighter.total_fights
            ))
        
        # Sort by win rate, then by finish rate
        leaderboard.sort(key=lambda x: (x.win_rate, x.finish_rate), reverse=True)
        
        # Assign ranks
        for i, entry in enumerate(leaderboard[:limit]):
            entry.rank = i + 1
        
        return leaderboard[:limit]
