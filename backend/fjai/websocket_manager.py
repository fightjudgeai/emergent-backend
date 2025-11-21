"""
Fight Judge AI - WebSocket Manager
Real-time feeds for CV, judge, score, and broadcast
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FJAIWebSocketManager:
    """Manage WebSocket connections for Fight Judge AI"""
    
    def __init__(self):
        # Connections by feed type
        self.cv_connections: Dict[str, Set[WebSocket]] = {}
        self.judge_connections: Dict[str, Set[WebSocket]] = {}
        self.score_connections: Dict[str, Set[WebSocket]] = {}
        self.broadcast_connections: Dict[str, Set[WebSocket]] = {}
        
        # Stats
        self.stats = {
            "messages_sent": 0,
            "connection_errors": 0
        }
    
    async def connect(self, websocket: WebSocket, feed_type: str, bout_id: str):
        """Connect client to feed"""
        await websocket.accept()
        
        if feed_type == "cv":
            if bout_id not in self.cv_connections:
                self.cv_connections[bout_id] = set()
            self.cv_connections[bout_id].add(websocket)
        elif feed_type == "judge":
            if bout_id not in self.judge_connections:
                self.judge_connections[bout_id] = set()
            self.judge_connections[bout_id].add(websocket)
        elif feed_type == "score":
            if bout_id not in self.score_connections:
                self.score_connections[bout_id] = set()
            self.score_connections[bout_id].add(websocket)
        elif feed_type == "broadcast":
            if bout_id not in self.broadcast_connections:
                self.broadcast_connections[bout_id] = set()
            self.broadcast_connections[bout_id].add(websocket)
        
        logger.info(f"WebSocket connected: {feed_type} for bout {bout_id}")
        
        # Send welcome message
        await self._send_message(websocket, {
            "type": "connection_established",
            "feed_type": feed_type,
            "bout_id": bout_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def disconnect(self, websocket: WebSocket, feed_type: str, bout_id: str):
        """Disconnect client"""
        if feed_type == "cv" and bout_id in self.cv_connections:
            self.cv_connections[bout_id].discard(websocket)
        elif feed_type == "judge" and bout_id in self.judge_connections:
            self.judge_connections[bout_id].discard(websocket)
        elif feed_type == "score" and bout_id in self.score_connections:
            self.score_connections[bout_id].discard(websocket)
        elif feed_type == "broadcast" and bout_id in self.broadcast_connections:
            self.broadcast_connections[bout_id].discard(websocket)
        
        logger.info(f"WebSocket disconnected: {feed_type} for bout {bout_id}")
    
    async def broadcast_cv_event(self, bout_id: str, event_data: Dict):
        """Broadcast CV event to subscribers"""
        await self._broadcast_to_feed(self.cv_connections, bout_id, {
            "type": "cv_event",
            "data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_judge_event(self, bout_id: str, event_data: Dict):
        """Broadcast judge event to subscribers"""
        await self._broadcast_to_feed(self.judge_connections, bout_id, {
            "type": "judge_event",
            "data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_score_update(self, bout_id: str, score_data: Dict):
        """Broadcast score update to subscribers"""
        await self._broadcast_to_feed(self.score_connections, bout_id, {
            "type": "score_update",
            "data": score_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_to_displays(self, bout_id: str, broadcast_data: Dict):
        """Broadcast to arena displays"""
        await self._broadcast_to_feed(self.broadcast_connections, bout_id, {
            "type": "broadcast",
            "data": broadcast_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def _broadcast_to_feed(self, feed_dict: Dict[str, Set[WebSocket]], bout_id: str, message: Dict):
        """Broadcast to all connections in feed"""
        if bout_id not in feed_dict:
            return
        
        dead_connections = set()
        
        for connection in feed_dict[bout_id]:
            try:
                await self._send_message(connection, message)
                self.stats["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                dead_connections.add(connection)
                self.stats["connection_errors"] += 1
        
        # Clean up dead connections
        for connection in dead_connections:
            feed_dict[bout_id].discard(connection)
    
    async def _send_message(self, websocket: WebSocket, message: Dict):
        """Send message to specific connection"""
        await websocket.send_json(message)
    
    def get_stats(self) -> Dict:
        """Get WebSocket statistics"""
        return {
            "total_cv_connections": sum(len(conns) for conns in self.cv_connections.values()),
            "total_judge_connections": sum(len(conns) for conns in self.judge_connections.values()),
            "total_score_connections": sum(len(conns) for conns in self.score_connections.values()),
            "total_broadcast_connections": sum(len(conns) for conns in self.broadcast_connections.values()),
            "messages_sent": self.stats["messages_sent"],
            "connection_errors": self.stats["connection_errors"]
        }


# Global instance
fjai_ws_manager = FJAIWebSocketManager()
