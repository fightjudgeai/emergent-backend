"""
Database Index Management

Creates and manages all database indexes for optimal query performance.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT
from typing import Dict, List

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages database indexes"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        logger.info("Index Manager initialized")
    
    async def create_all_indexes(self) -> Dict[str, List[str]]:
        """
        Create all indexes for production tables
        
        Returns:
            Dictionary of collection names to list of created indexes
        """
        
        results = {}
        
        logger.info("Creating all database indexes...")
        
        # Fighters indexes
        results['fighters'] = await self._create_fighters_indexes()
        
        # Events indexes
        results['events'] = await self._create_events_indexes()
        
        # Round stats indexes
        results['round_stats'] = await self._create_round_stats_indexes()
        
        # Fight stats indexes
        results['fight_stats'] = await self._create_fight_stats_indexes()
        
        # Career stats indexes
        results['career_stats'] = await self._create_career_stats_indexes()
        
        logger.info(f"✅ All indexes created successfully")
        return results
    
    async def _create_fighters_indexes(self) -> List[str]:
        """Create indexes for fighters table"""
        
        indexes = []
        
        try:
            # Unique index on id
            await self.db.fighters.create_index(
                [("id", ASCENDING)],
                unique=True,
                name="idx_fighters_id"
            )
            indexes.append("idx_fighters_id")
            
            # Text search on name
            await self.db.fighters.create_index(
                [("name", TEXT)],
                name="idx_fighters_name_text"
            )
            indexes.append("idx_fighters_name_text")
            
            # Index on division for filtering
            await self.db.fighters.create_index(
                [("division", ASCENDING)],
                name="idx_fighters_division"
            )
            indexes.append("idx_fighters_division")
            
            # Index on gym for filtering
            await self.db.fighters.create_index(
                [("gym", ASCENDING)],
                name="idx_fighters_gym"
            )
            indexes.append("idx_fighters_gym")
            
            # Index on created_at for sorting
            await self.db.fighters.create_index(
                [("created_at", DESCENDING)],
                name="idx_fighters_created_at"
            )
            indexes.append("idx_fighters_created_at")
            
            logger.info(f"✅ Created {len(indexes)} indexes for fighters")
        
        except Exception as e:
            logger.error(f"Error creating fighters indexes: {e}")
        
        return indexes
    
    async def _create_events_indexes(self) -> List[str]:
        """Create indexes for events table"""
        
        indexes = []
        
        try:
            # Compound index on (fight_id, round, timestamp_in_round)
            # Used for querying events in a specific round chronologically
            await self.db.events.create_index(
                [("fight_id", ASCENDING), ("round", ASCENDING), ("timestamp_in_round", ASCENDING)],
                name="idx_events_fight_round_timestamp"
            )
            indexes.append("idx_events_fight_round_timestamp")
            
            # Index on fighter_id for querying fighter-specific events
            await self.db.events.create_index(
                [("fighter_id", ASCENDING)],
                name="idx_events_fighter_id"
            )
            indexes.append("idx_events_fighter_id")
            
            # Compound index on (fight_id, fighter_id) for fighter events in a fight
            await self.db.events.create_index(
                [("fight_id", ASCENDING), ("fighter_id", ASCENDING)],
                name="idx_events_fight_fighter"
            )
            indexes.append("idx_events_fight_fighter")
            
            # Index on event_type for filtering by type
            await self.db.events.create_index(
                [("event_type", ASCENDING)],
                name="idx_events_event_type"
            )
            indexes.append("idx_events_event_type")
            
            # Index on source for filtering by source
            await self.db.events.create_index(
                [("source", ASCENDING)],
                name="idx_events_source"
            )
            indexes.append("idx_events_source")
            
            # Index on created_at for time-based queries
            await self.db.events.create_index(
                [("created_at", DESCENDING)],
                name="idx_events_created_at"
            )
            indexes.append("idx_events_created_at")
            
            # Compound index for stat aggregation queries
            await self.db.events.create_index(
                [("fight_id", ASCENDING), ("round", ASCENDING), ("fighter_id", ASCENDING), ("event_type", ASCENDING)],
                name="idx_events_aggregation"
            )
            indexes.append("idx_events_aggregation")
            
            logger.info(f"✅ Created {len(indexes)} indexes for events")
        
        except Exception as e:
            logger.error(f"Error creating events indexes: {e}")
        
        return indexes
    
    async def _create_round_stats_indexes(self) -> List[str]:
        """Create indexes for round_stats table"""
        
        indexes = []
        
        try:
            # UNIQUE compound index on (fight_id, round, fighter_id)
            # Ensures only one stat record per fighter per round
            await self.db.round_stats.create_index(
                [("fight_id", ASCENDING), ("round", ASCENDING), ("fighter_id", ASCENDING)],
                unique=True,
                name="idx_round_stats_unique"
            )
            indexes.append("idx_round_stats_unique")
            
            # Index on fighter_id for fighter-specific queries
            await self.db.round_stats.create_index(
                [("fighter_id", ASCENDING)],
                name="idx_round_stats_fighter_id"
            )
            indexes.append("idx_round_stats_fighter_id")
            
            # Index on fight_id for fight-specific queries
            await self.db.round_stats.create_index(
                [("fight_id", ASCENDING)],
                name="idx_round_stats_fight_id"
            )
            indexes.append("idx_round_stats_fight_id")
            
            # Compound index on (fight_id, round) for round queries
            await self.db.round_stats.create_index(
                [("fight_id", ASCENDING), ("round", ASCENDING)],
                name="idx_round_stats_fight_round"
            )
            indexes.append("idx_round_stats_fight_round")
            
            # Index on updated_at for recently updated stats
            await self.db.round_stats.create_index(
                [("updated_at", DESCENDING)],
                name="idx_round_stats_updated_at"
            )
            indexes.append("idx_round_stats_updated_at")
            
            logger.info(f"✅ Created {len(indexes)} indexes for round_stats")
        
        except Exception as e:
            logger.error(f"Error creating round_stats indexes: {e}")
        
        return indexes
    
    async def _create_fight_stats_indexes(self) -> List[str]:
        """Create indexes for fight_stats table"""
        
        indexes = []
        
        try:
            # UNIQUE compound index on (fight_id, fighter_id)
            # Ensures only one stat record per fighter per fight
            await self.db.fight_stats.create_index(
                [("fight_id", ASCENDING), ("fighter_id", ASCENDING)],
                unique=True,
                name="idx_fight_stats_unique"
            )
            indexes.append("idx_fight_stats_unique")
            
            # Index on fighter_id for fighter-specific queries
            await self.db.fight_stats.create_index(
                [("fighter_id", ASCENDING)],
                name="idx_fight_stats_fighter_id"
            )
            indexes.append("idx_fight_stats_fighter_id")
            
            # Index on fight_id for fight-specific queries
            await self.db.fight_stats.create_index(
                [("fight_id", ASCENDING)],
                name="idx_fight_stats_fight_id"
            )
            indexes.append("idx_fight_stats_fight_id")
            
            # Index on updated_at for recently updated stats
            await self.db.fight_stats.create_index(
                [("updated_at", DESCENDING)],
                name="idx_fight_stats_updated_at"
            )
            indexes.append("idx_fight_stats_updated_at")
            
            # Compound index for sorting by performance
            await self.db.fight_stats.create_index(
                [("sig_strikes_landed", DESCENDING), ("knockdowns", DESCENDING)],
                name="idx_fight_stats_performance"
            )
            indexes.append("idx_fight_stats_performance")
            
            logger.info(f"✅ Created {len(indexes)} indexes for fight_stats")
        
        except Exception as e:
            logger.error(f"Error creating fight_stats indexes: {e}")
        
        return indexes
    
    async def _create_career_stats_indexes(self) -> List[str]:
        """Create indexes for career_stats table"""
        
        indexes = []
        
        try:
            # UNIQUE index on fighter_id
            # Ensures only one career stat record per fighter
            await self.db.career_stats.create_index(
                [("fighter_id", ASCENDING)],
                unique=True,
                name="idx_career_stats_unique"
            )
            indexes.append("idx_career_stats_unique")
            
            # Index on updated_at for recently updated stats
            await self.db.career_stats.create_index(
                [("updated_at", DESCENDING)],
                name="idx_career_stats_updated_at"
            )
            indexes.append("idx_career_stats_updated_at")
            
            # Index on total_fights for sorting
            await self.db.career_stats.create_index(
                [("total_fights", DESCENDING)],
                name="idx_career_stats_total_fights"
            )
            indexes.append("idx_career_stats_total_fights")
            
            # Compound index for leaderboards (by sig strikes per min)
            await self.db.career_stats.create_index(
                [("avg_sig_strikes_per_min", DESCENDING)],
                name="idx_career_stats_sig_strikes_leader"
            )
            indexes.append("idx_career_stats_sig_strikes_leader")
            
            # Compound index for leaderboards (by knockdowns per 15min)
            await self.db.career_stats.create_index(
                [("knockdowns_per_15min", DESCENDING)],
                name="idx_career_stats_kd_leader"
            )
            indexes.append("idx_career_stats_kd_leader")
            
            # Compound index for leaderboards (by accuracy)
            await self.db.career_stats.create_index(
                [("avg_sig_strike_accuracy", DESCENDING)],
                name="idx_career_stats_accuracy_leader"
            )
            indexes.append("idx_career_stats_accuracy_leader")
            
            logger.info(f"✅ Created {len(indexes)} indexes for career_stats")
        
        except Exception as e:
            logger.error(f"Error creating career_stats indexes: {e}")
        
        return indexes
    
    async def verify_indexes(self) -> Dict[str, List[str]]:
        """
        Verify all indexes exist
        
        Returns:
            Dictionary of collection names to list of existing index names
        """
        
        results = {}
        
        collections = ['fighters', 'events', 'round_stats', 'fight_stats', 'career_stats']
        
        for collection_name in collections:
            try:
                collection = self.db[collection_name]
                indexes = await collection.index_information()
                results[collection_name] = list(indexes.keys())
                logger.info(f"Collection '{collection_name}': {len(indexes)} indexes")
            except Exception as e:
                logger.error(f"Error verifying {collection_name} indexes: {e}")
                results[collection_name] = []
        
        return results
    
    async def drop_all_indexes(self, confirm: bool = False):
        """
        Drop all indexes (except _id)
        
        WARNING: Only use for development/testing
        
        Args:
            confirm: Must be True to actually drop indexes
        """
        
        if not confirm:
            logger.warning("drop_all_indexes called without confirmation - skipping")
            return
        
        logger.warning("⚠️ Dropping all indexes...")
        
        collections = ['fighters', 'events', 'round_stats', 'fight_stats', 'career_stats']
        
        for collection_name in collections:
            try:
                collection = self.db[collection_name]
                await collection.drop_indexes()
                logger.info(f"Dropped indexes for {collection_name}")
            except Exception as e:
                logger.error(f"Error dropping {collection_name} indexes: {e}")
