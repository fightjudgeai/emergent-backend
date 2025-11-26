"""
WebSocket Handler

Real-time stats updates for overlay clients.
"""

import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class OverlayWebSocketManager:
    """Manages WebSocket connections for live overlay updates"""
    
    def __init__(self):
        # fight_id -> set of websockets
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.update_interval = 1.0  # 1 second updates
    
    async def connect(self, websocket: WebSocket, fight_id: str):
        """Register new WebSocket connection"""
        await websocket.accept()
        
        if fight_id not in self.connections:
            self.connections[fight_id] = set()
        
        self.connections[fight_id].add(websocket)
        logger.info(f"WebSocket connected for fight {fight_id}. Total connections: {len(self.connections[fight_id])}")
    
    def disconnect(self, websocket: WebSocket, fight_id: str):
        """Unregister WebSocket connection"""
        if fight_id in self.connections:
            self.connections[fight_id].discard(websocket)
            
            if len(self.connections[fight_id]) == 0:
                del self.connections[fight_id]
            
            logger.info(f"WebSocket disconnected for fight {fight_id}")
    
    async def broadcast_to_fight(self, fight_id: str, data: dict):
        """
        Broadcast data to all connections for a specific fight
        
        Args:
            fight_id: Fight identifier
            data: Data to broadcast
        """
        if fight_id not in self.connections:
            return
        
        # Create copy to avoid modification during iteration
        connections = self.connections[fight_id].copy()
        
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(data)
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws, fight_id)
    
    def get_connection_count(self, fight_id: str = None) -> int:
        """Get number of active connections"""
        if fight_id:
            return len(self.connections.get(fight_id, set()))
        
        return sum(len(conns) for conns in self.connections.values())
    
    def get_active_fights(self) -> list:
        """Get list of fight IDs with active connections"""
        return list(self.connections.keys())


# Global WebSocket manager
overlay_ws_manager = OverlayWebSocketManager()
