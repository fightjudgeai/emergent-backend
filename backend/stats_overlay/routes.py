"""
Stats Overlay API Routes

Low-latency endpoints for broadcast overlays with caching.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging
import time

from .cache_manager import overlay_cache
from .aggregator import StatsAggregator
from .websocket_handler import overlay_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/overlay", tags=["Stats Overlay"])

# Global instances
db: Optional[AsyncIOMotorDatabase] = None
aggregator: Optional[StatsAggregator] = None


def init_stats_overlay(database: AsyncIOMotorDatabase):
    """Initialize stats overlay with database"""
    global db, aggregator
    db = database
    aggregator = StatsAggregator(database)
    logger.info("✅ Stats Overlay API initialized")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Stats Overlay API",
        "version": "1.0.0",
        "status": "operational",
        "cache_stats": overlay_cache.get_stats(),
        "websocket_connections": overlay_ws_manager.get_connection_count()
    }


@router.get("/live/{fight_id}")
async def get_live_overlay(fight_id: str):
    """
    Get live stats overlay data
    
    Performance: Sub-200ms with 1-second cache
    
    Returns:
    - Current round stats
    - Last 60 seconds event totals
    - KD / Rock indicators
    """
    
    if not aggregator:
        raise HTTPException(status_code=500, detail="Aggregator not initialized")
    
    start_time = time.time()
    
    # Check cache first
    cache_key = f"live:{fight_id}"
    cached_data = overlay_cache.get(cache_key)
    
    if cached_data:
        cached_data['_cached'] = True
        cached_data['_latency_ms'] = round((time.time() - start_time) * 1000, 2)
        return cached_data
    
    # Fetch fresh data
    live_stats = await aggregator.get_live_stats(fight_id)
    
    if not live_stats:
        raise HTTPException(status_code=404, detail=f"No live data for fight {fight_id}")
    
    # Cache for 1 second
    overlay_cache.set(cache_key, live_stats)
    
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    live_stats['_cached'] = False
    live_stats['_latency_ms'] = latency_ms
    
    # Log if over 200ms
    if latency_ms > 200:
        logger.warning(f"Overlay latency exceeded 200ms: {latency_ms}ms for fight {fight_id}")
    
    return live_stats


@router.get("/comparison/{fight_id}")
async def get_comparison_overlay(fight_id: str):
    """
    Get red vs blue stat comparison with deltas
    
    Performance: Sub-200ms with 1-second cache
    
    Returns:
    - Red corner stats
    - Blue corner stats
    - Stat deltas
    - Leaders per category
    """
    
    if not aggregator:
        raise HTTPException(status_code=500, detail="Aggregator not initialized")
    
    start_time = time.time()
    
    # Check cache
    cache_key = f"comparison:{fight_id}"
    cached_data = overlay_cache.get(cache_key)
    
    if cached_data:
        cached_data['_cached'] = True
        cached_data['_latency_ms'] = round((time.time() - start_time) * 1000, 2)
        return cached_data
    
    # Fetch fresh data
    comparison = await aggregator.get_comparison_stats(fight_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail=f"No comparison data for fight {fight_id}")
    
    # Cache for 1 second
    overlay_cache.set(cache_key, comparison)
    
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    comparison['_cached'] = False
    comparison['_latency_ms'] = latency_ms
    
    if latency_ms > 200:
        logger.warning(f"Comparison latency exceeded 200ms: {latency_ms}ms for fight {fight_id}")
    
    return comparison


@router.post("/cache/invalidate/{fight_id}")
async def invalidate_cache(fight_id: str):
    """
    Manually invalidate cache for a fight
    
    Use when new events are logged to force refresh
    """
    
    overlay_cache.invalidate(f"live:{fight_id}")
    overlay_cache.invalidate(f"comparison:{fight_id}")
    
    return {
        "status": "success",
        "fight_id": fight_id,
        "message": "Cache invalidated"
    }


@router.websocket("/ws/live/{fight_id}")
async def websocket_live_overlay(websocket: WebSocket, fight_id: str):
    """
    WebSocket endpoint for real-time overlay updates
    
    Pushes updates every 1 second
    """
    
    if not aggregator:
        await websocket.close(code=1011, reason="Aggregator not initialized")
        return
    
    await overlay_ws_manager.connect(websocket, fight_id)
    
    try:
        while True:
            # Get live stats
            live_stats = await aggregator.get_live_stats(fight_id)
            
            if live_stats:
                await websocket.send_json({
                    "type": "live_stats",
                    "data": live_stats
                })
            
            # Wait 1 second before next update
            await asyncio.sleep(1.0)
    
    except WebSocketDisconnect:
        overlay_ws_manager.disconnect(websocket, fight_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        overlay_ws_manager.disconnect(websocket, fight_id)


@router.get("/stats/cache")
async def get_cache_stats():
    """Get cache statistics"""
    return overlay_cache.get_stats()


@router.get("/stats/websockets")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "total_connections": overlay_ws_manager.get_connection_count(),
        "active_fights": overlay_ws_manager.get_active_fights(),
        "fights_with_connections": len(overlay_ws_manager.get_active_fights())
    }
