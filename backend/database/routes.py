"""
Database Management API Routes

Endpoints for database health checks and management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from .init_db import DatabaseInitializer
from .models import DatabaseHealth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/database", tags=["Database Management"])

# Global instance
db_initializer: Optional[DatabaseInitializer] = None


def init_database_routes(db):
    """Initialize database routes"""
    global db_initializer
    db_initializer = DatabaseInitializer(db)
    logger.info("✅ Database Management routes initialized")


@router.get("/health")
async def health_check():
    """
    Database health check
    
    Returns:
    - Database status
    - Collection counts
    - Index counts
    - Total documents
    """
    
    if not db_initializer:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        health = await db_initializer.health_check()
        return health
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize")
async def initialize_database(
    force_recreate_indexes: bool = Query(False, description="Force recreate all indexes")
):
    """
    Initialize database with collections and indexes
    
    Query Params:
    - force_recreate_indexes: Drop and recreate all indexes (default: false)
    
    Returns:
    - Initialization results
    - Collections created
    - Indexes created
    
    WARNING: Use force_recreate_indexes=true with caution in production
    """
    
    if not db_initializer:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        results = await db_initializer.initialize(force_recreate_indexes=force_recreate_indexes)
        return results
    
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indexes")
async def get_indexes():
    """
    Get all database indexes
    
    Returns:
    - Dictionary of collections to index names
    """
    
    if not db_initializer:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        indexes = await db_initializer.index_manager.verify_indexes()
        return {
            "collections": indexes,
            "total_indexes": sum(len(v) for v in indexes.values())
        }
    
    except Exception as e:
        logger.error(f"Error getting indexes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indexes/recreate")
async def recreate_indexes():
    """
    Drop and recreate all database indexes
    
    WARNING: Use with caution in production
    This will temporarily impact query performance
    
    Returns:
    - Indexes created
    """
    
    if not db_initializer:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Drop existing indexes
        await db_initializer.index_manager.drop_all_indexes(confirm=True)
        
        # Create new indexes
        indexes = await db_initializer.index_manager.create_all_indexes()
        
        return {
            "status": "success",
            "indexes_created": indexes,
            "total_indexes": sum(len(v) for v in indexes.values())
        }
    
    except Exception as e:
        logger.error(f"Error recreating indexes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections")
async def get_collections():
    """
    Get all collections with document counts
    
    Returns:
    - Collection names and counts
    """
    
    if not db_initializer or not db_initializer.db:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        counts = await db_initializer._get_collection_counts()
        
        return {
            "collections": counts,
            "total_documents": sum(c for c in counts.values() if c >= 0)
        }
    
    except Exception as e:
        logger.error(f"Error getting collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))
