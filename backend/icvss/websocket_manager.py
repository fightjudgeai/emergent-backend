"""
ICVSS WebSocket Manager
Real-time feeds for CV events, judge events, scores, and broadcast
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import logging
from datetime import datetime, timezone
from .models import WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for ICVSS"""
    
    def __init__(self):
        # Active connections by feed type
        self.cv_feed_connections: Dict[str, Set[WebSocket]] = {}  # bout_id -> {websockets}
        self.judge_feed_connections: Dict[str, Set[WebSocket]] = {}
        self.score_feed_connections: Dict[str, Set[WebSocket]] = {}
        self.broadcast_feed_connections: Dict[str, Set[WebSocket]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}  # websocket -> {auth, bout_id, etc}
    
    async def connect(self, websocket: WebSocket, feed_type: str, bout_id: str, auth_token: str = None):
        """
        Connect a WebSocket client to a feed
        
        Args:
            websocket: WebSocket connection
            feed_type: "cv_event", "judge_event", "score_update", "broadcast"
            bout_id: Bout identifier
            auth_token: Authentication token (optional for broadcast)
        """
        await websocket.accept()
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "feed_type": feed_type,
            "bout_id": bout_id,
            "auth_token": auth_token,
            "connected_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add to appropriate feed
        if feed_type == "cv_event":
            if bout_id not in self.cv_feed_connections:
                self.cv_feed_connections[bout_id] = set()
            self.cv_feed_connections[bout_id].add(websocket)
        
        elif feed_type == "judge_event":
            if bout_id not in self.judge_feed_connections:
                self.judge_feed_connections[bout_id] = set()
            self.judge_feed_connections[bout_id].add(websocket)
        
        elif feed_type == "score_update":
            if bout_id not in self.score_feed_connections:
                self.score_feed_connections[bout_id] = set()
            self.score_feed_connections[bout_id].add(websocket)
        
        elif feed_type == "broadcast":
            if bout_id not in self.broadcast_feed_connections:
                self.broadcast_feed_connections[bout_id] = set()
            self.broadcast_feed_connections[bout_id].add(websocket)
        
        logger.info(f"WebSocket connected: {feed_type} for bout {bout_id}")
        
        # Send welcome message
        await self.send_personal_message(websocket, {
            "type": "connection_established",
            "feed_type": feed_type,
            "bout_id": bout_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        if websocket not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[websocket]
        feed_type = metadata["feed_type"]
        bout_id = metadata["bout_id"]
        
        # Remove from appropriate feed
        if feed_type == "cv_event" and bout_id in self.cv_feed_connections:
            self.cv_feed_connections[bout_id].discard(websocket)
        elif feed_type == "judge_event" and bout_id in self.judge_feed_connections:
            self.judge_feed_connections[bout_id].discard(websocket)
        elif feed_type == "score_update" and bout_id in self.score_feed_connections:
            self.score_feed_connections[bout_id].discard(websocket)
        elif feed_type == "broadcast" and bout_id in self.broadcast_feed_connections:
            self.broadcast_feed_connections[bout_id].discard(websocket)
        
        # Remove metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket disconnected: {feed_type} for bout {bout_id}")
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to a specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def broadcast_cv_event(self, bout_id: str, round_id: str, event_data: dict):
        """Broadcast CV event to all CV feed subscribers"""
        message = WebSocketMessage(
            type="cv_event",
            bout_id=bout_id,
            round_id=round_id,
            data=event_data
        )
        
        await self._broadcast_to_feed(self.cv_feed_connections, bout_id, message.model_dump())
    
    async def broadcast_judge_event(self, bout_id: str, round_id: str, event_data: dict):
        """Broadcast judge event to all judge feed subscribers"""
        message = WebSocketMessage(
            type="judge_event",
            bout_id=bout_id,
            round_id=round_id,
            data=event_data
        )
        
        await self._broadcast_to_feed(self.judge_feed_connections, bout_id, message.model_dump())
    
    async def broadcast_score_update(self, bout_id: str, round_id: str, score_data: dict):
        """Broadcast score update to all score feed subscribers"""
        message = WebSocketMessage(
            type="score_update",
            bout_id=bout_id,
            round_id=round_id,
            data=score_data
        )
        
        await self._broadcast_to_feed(self.score_feed_connections, bout_id, message.model_dump())
    
    async def broadcast_to_display(self, bout_id: str, broadcast_data: dict):
        """Broadcast to all broadcast feed subscribers (arena displays, overlays)"""
        message = WebSocketMessage(
            type="broadcast",
            bout_id=bout_id,
            data=broadcast_data
        )
        
        await self._broadcast_to_feed(self.broadcast_feed_connections, bout_id, message.model_dump())
    
    async def _broadcast_to_feed(self, feed_dict: Dict[str, Set[WebSocket]], bout_id: str, message: dict):
        """Broadcast message to all connections in a feed"""
        if bout_id not in feed_dict:
            return
        
        dead_connections = set()
        
        for connection in feed_dict[bout_id]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                dead_connections.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)
    
    def get_connection_count(self, bout_id: str = None) -> Dict[str, int]:
        """Get connection count by feed type"""
        if bout_id:
            return {
                "cv_feed": len(self.cv_feed_connections.get(bout_id, set())),
                "judge_feed": len(self.judge_feed_connections.get(bout_id, set())),
                "score_feed": len(self.score_feed_connections.get(bout_id, set())),
                "broadcast_feed": len(self.broadcast_feed_connections.get(bout_id, set()))
            }
        else:
            return {
                "total_cv_feed": sum(len(connections) for connections in self.cv_feed_connections.values()),
                "total_judge_feed": sum(len(connections) for connections in self.judge_feed_connections.values()),
                "total_score_feed": sum(len(connections) for connections in self.score_feed_connections.values()),
                "total_broadcast_feed": sum(len(connections) for connections in self.broadcast_feed_connections.values())
            }


# Global connection manager instance
ws_manager = ConnectionManager()
