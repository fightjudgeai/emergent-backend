"""
Fighter Analytics - FastAPI Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from .analytics_engine import FighterAnalyticsEngine
from .models import (
    FighterProfile,
    BoutResult,
    PerformanceStats,
    LeaderboardEntry
)

logger = logging.getLogger(__name__)

fighter_analytics_api = APIRouter(tags=["Fighter Analytics"])
analytics_engine: Optional[FighterAnalyticsEngine] = None

def get_analytics_engine():
    if analytics_engine is None:
        raise HTTPException(status_code=500, detail="Fighter Analytics not initialized")
    return analytics_engine

# ============================================================================
# Fighter CRUD Operations
# ============================================================================

@fighter_analytics_api.post("/fighters", response_model=FighterProfile, status_code=201)
async def create_fighter(fighter: FighterProfile):
    """Create a new fighter profile"""
    engine = get_analytics_engine()
    return await engine.create_fighter(fighter)

@fighter_analytics_api.get("/fighters", response_model=List[FighterProfile])
async def list_fighters(limit: int = 100, skip: int = 0, weight_class: Optional[str] = None):
    """List all fighters"""
    engine = get_analytics_engine()
    fighters = await engine.list_fighters(limit=limit, skip=skip)
    
    if weight_class:
        fighters = [f for f in fighters if f.weight_class == weight_class]
    
    return fighters

@fighter_analytics_api.get("/fighters/{fighter_id}", response_model=FighterProfile)
async def get_fighter(fighter_id: str):
    """Get fighter by ID"""
    engine = get_analytics_engine()
    fighter = await engine.get_fighter(fighter_id)
    
    if not fighter:
        raise HTTPException(status_code=404, detail=f"Fighter not found: {fighter_id}")
    
    return fighter

@fighter_analytics_api.put("/fighters/{fighter_id}", response_model=FighterProfile)
async def update_fighter(fighter_id: str, updates: dict):
    """Update fighter profile"""
    engine = get_analytics_engine()
    
    # Don't allow updating id, created_at
    updates.pop('id', None)
    updates.pop('created_at', None)
    
    fighter = await engine.update_fighter(fighter_id, updates)
    
    if not fighter:
        raise HTTPException(status_code=404, detail=f"Fighter not found: {fighter_id}")
    
    return fighter

@fighter_analytics_api.delete("/fighters/{fighter_id}")
async def delete_fighter(fighter_id: str):
    """Delete fighter profile"""
    engine = get_analytics_engine()
    success = await engine.delete_fighter(fighter_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Fighter not found: {fighter_id}")
    
    return {"success": True, "fighter_id": fighter_id}

# ============================================================================
# Fighter Stats & History
# ============================================================================

@fighter_analytics_api.get("/fighters/{fighter_id}/stats", response_model=PerformanceStats)
async def get_fighter_stats(fighter_id: str):
    """Get fighter performance statistics"""
    engine = get_analytics_engine()
    stats = await engine.calculate_stats(fighter_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"Fighter not found: {fighter_id}")
    
    return stats

@fighter_analytics_api.get("/fighters/{fighter_id}/history", response_model=List[BoutResult])
async def get_fighter_history(fighter_id: str):
    """Get fighter bout history"""
    engine = get_analytics_engine()
    history = await engine.get_fighter_history(fighter_id)
    
    return history

@fighter_analytics_api.post("/fighters/{fighter_id}/bout")
async def add_bout_result(fighter_id: str, bout: BoutResult):
    """Add bout result to fighter history"""
    engine = get_analytics_engine()
    
    # Verify fighter exists
    fighter = await engine.get_fighter(fighter_id)
    if not fighter:
        raise HTTPException(status_code=404, detail=f"Fighter not found: {fighter_id}")
    
    success = await engine.add_bout_result(fighter_id, bout)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add bout result")
    
    return {"success": True, "bout_id": bout.bout_id}

# ============================================================================
# Leaderboard & Rankings
# ============================================================================

@fighter_analytics_api.get("/stats/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(weight_class: Optional[str] = None, limit: int = 20):
    """
    Get fighter leaderboard/rankings
    
    Sorted by win rate, then finish rate
    """
    engine = get_analytics_engine()
    return await engine.get_leaderboard(weight_class=weight_class, limit=limit)

@fighter_analytics_api.get("/stats/weight_classes")
async def get_weight_classes():
    """Get list of all weight classes"""
    engine = get_analytics_engine()
    fighters = await engine.list_fighters(limit=1000)
    
    weight_classes = list(set(f.weight_class for f in fighters))
    weight_classes.sort()
    
    return {"weight_classes": weight_classes, "count": len(weight_classes)}

# ============================================================================
# Search & Filter
# ============================================================================

@fighter_analytics_api.get("/fighters/search/{query}")
async def search_fighters(query: str, limit: int = 20):
    """Search fighters by name"""
    engine = get_analytics_engine()
    fighters = await engine.list_fighters(limit=1000)
    
    # Filter by name (case-insensitive)
    query_lower = query.lower()
    results = [
        f for f in fighters
        if query_lower in f.name.lower() or (f.nickname and query_lower in f.nickname.lower())
    ]
    
    return results[:limit]

@fighter_analytics_api.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Fighter Analytics", "version": "1.0.0"}
