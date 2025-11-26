"""
WebSocket Handler for Live Stats

Provides real-time stat updates via WebSocket connections.
"""

import logging
import asyncio
import json
from typing import Dict, Set
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StatsWebSocketManager:
    """Manages WebSocket connections for live stats updates"""
    
    def __init__(self, db):
        self.db = db
        self.active_connections: Dict[str, Set] = {}  # fight_id -> set of websockets
        self.update_interval = 2  # seconds
        logger.info("Stats WebSocket Manager initialized")
    
    async def connect(self, websocket, fight_id: str):
        """Register a new WebSocket connection"""
        if fight_id not in self.active_connections:
            self.active_connections[fight_id] = set()
        
        self.active_connections[fight_id].add(websocket)
        logger.info(f"WebSocket connected for fight: {fight_id}, total connections: {len(self.active_connections[fight_id])}")
    
    def disconnect(self, websocket, fight_id: str):
        """Remove a WebSocket connection"""
        if fight_id in self.active_connections:
            self.active_connections[fight_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[fight_id]:
                del self.active_connections[fight_id]
            
            logger.info(f"WebSocket disconnected for fight: {fight_id}")
    
    async def broadcast_stats(self, fight_id: str, stats_data: dict):
        """Broadcast stats to all connected clients for a fight"""
        if fight_id not in self.active_connections:
            return
        
        message = json.dumps({
            "type": "stats_update",
            "fight_id": fight_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": stats_data
        })
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.active_connections[fight_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket, fight_id)
    
    async def get_live_stats(self, fight_id: str) -> dict:
        """Get current stats for a fight"""
        if not self.db:
            return {"error": "Database not available"}
        
        try:
            stats_data = {
                "round_stats": {},
                "fight_stats": {},
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Get all round stats for this fight
            round_cursor = self.db.round_stats.find({"fight_id": fight_id})
            round_docs = await round_cursor.to_list(length=None)
            
            for doc in round_docs:
                doc.pop('_id', None)
                fighter_id = doc['fighter_id']
                round_num = doc['round']
                
                if fighter_id not in stats_data['round_stats']:
                    stats_data['round_stats'][fighter_id] = {}
                
                stats_data['round_stats'][fighter_id][round_num] = doc
            
            # Get fight stats for this fight
            fight_cursor = self.db.fight_stats.find({"fight_id": fight_id})
            fight_docs = await fight_cursor.to_list(length=None)
            
            for doc in fight_docs:
                doc.pop('_id', None)
                fighter_id = doc['fighter_id']
                stats_data['fight_stats'][fighter_id] = doc
            
            return stats_data
        
        except Exception as e:
            logger.error(f"Error getting live stats: {e}")
            return {"error": str(e)}


# Global instance
stats_ws_manager = None


def init_stats_websocket_manager(db):
    """Initialize the WebSocket manager"""
    global stats_ws_manager
    stats_ws_manager = StatsWebSocketManager(db)
    return stats_ws_manager
