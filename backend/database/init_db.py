"""
Database Initialization

Initializes production database with proper schemas and indexes.
Run on application startup.
"""

import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any

from .indexes import IndexManager

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.index_manager = IndexManager(db)
        logger.info("Database Initializer created")
    
    async def initialize(self, force_recreate_indexes: bool = False) -> Dict[str, Any]:
        """
        Initialize database with all required collections and indexes
        
        Args:
            force_recreate_indexes: If True, drop and recreate all indexes
        
        Returns:
            Dictionary with initialization results
        """
        
        logger.info("🚀 Initializing production database...")
        
        results = {
            "status": "success",
            "collections_created": [],
            "indexes_created": {},
            "errors": []
        }
        
        try:
            # 1. Create collections if they don't exist
            await self._ensure_collections(results)
            
            # 2. Drop existing indexes if force recreate
            if force_recreate_indexes:
                logger.warning("⚠️ Force recreating indexes...")
                await self.index_manager.drop_all_indexes(confirm=True)
            
            # 3. Create all indexes
            results["indexes_created"] = await self.index_manager.create_all_indexes()
            
            # 4. Verify indexes
            existing_indexes = await self.index_manager.verify_indexes()
            results["indexes_verified"] = existing_indexes
            
            # 5. Get collection counts
            results["collection_counts"] = await self._get_collection_counts()
            
            logger.info("✅ Database initialization complete")
            logger.info(f"   Collections: {len(results['collections_created'])}")
            logger.info(f"   Total indexes: {sum(len(v) for v in results['indexes_created'].values())}")
        
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            results["status"] = "failed"
            results["errors"].append(str(e))
        
        return results
    
    async def _ensure_collections(self, results: Dict) -> None:
        """
        Ensure all required collections exist
        
        In MongoDB, collections are created automatically on first insert,
        but we explicitly create them here for clarity.
        """
        
        required_collections = [
            'fighters',
            'events',
            'round_stats',
            'fight_stats',
            'career_stats'
        ]
        
        existing_collections = await self.db.list_collection_names()
        
        for collection_name in required_collections:
            if collection_name not in existing_collections:
                await self.db.create_collection(collection_name)
                results["collections_created"].append(collection_name)
                logger.info(f"✅ Created collection: {collection_name}")
            else:
                logger.debug(f"Collection already exists: {collection_name}")
    
    async def _get_collection_counts(self) -> Dict[str, int]:
        """Get document counts for all collections"""
        
        counts = {}
        
        collections = ['fighters', 'events', 'round_stats', 'fight_stats', 'career_stats']
        
        for collection_name in collections:
            try:
                count = await self.db[collection_name].count_documents({})
                counts[collection_name] = count
            except Exception as e:
                logger.error(f"Error counting {collection_name}: {e}")
                counts[collection_name] = -1
        
        return counts
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check
        
        Returns:
            Health status with collection counts and index info
        """
        
        health = {
            "status": "healthy",
            "database_name": self.db.name,
            "collections": {},
            "indexes": {},
            "total_documents": 0
        }
        
        try:
            # Get collection counts
            counts = await self._get_collection_counts()
            health["collections"] = counts
            health["total_documents"] = sum(c for c in counts.values() if c >= 0)
            
            # Verify indexes
            indexes = await self.index_manager.verify_indexes()
            health["indexes"] = {k: len(v) for k, v in indexes.items()}
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health["status"] = "unhealthy"
            health["error"] = str(e)
        
        return health


async def initialize_database(db: AsyncIOMotorDatabase, force_recreate_indexes: bool = False) -> Dict[str, Any]:
    """
    Convenience function to initialize database
    
    Args:
        db: MongoDB database instance
        force_recreate_indexes: Whether to drop and recreate indexes
    
    Returns:
        Initialization results
    """
    
    initializer = DatabaseInitializer(db)
    return await initializer.initialize(force_recreate_indexes=force_recreate_indexes)
