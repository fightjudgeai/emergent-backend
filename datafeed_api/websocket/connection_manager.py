"""
WebSocket Connection Manager
Handles WebSocket lifecycle, authentication, and message broadcasting
with real-time fantasy points and market data
"""

import json
import logging
import asyncio
from typing import Dict, Set, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from uuid import UUID

from auth.middleware import AuthMiddleware
from models.schemas import WebSocketMessage, AuthMessage, SubscribeMessage

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Represents a single WebSocket connection with auth state"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.authenticated = False
        self.client_info: Optional[dict] = None
        self.subscriptions: Set[str] = set()
    
    @property
    def scope(self) -> Optional[str]:
        return self.client_info.get('scope') if self.client_info else None


class ConnectionManager:
    """Manages all WebSocket connections and message broadcasting"""
    
    def __init__(self, db_pool: asyncpg.Pool, auth_middleware: AuthMiddleware):
        self.db_pool = db_pool
        self.auth_middleware = auth_middleware
        self.active_connections: Dict[str, WebSocketConnection] = {}  # connection_id -> WebSocketConnection
        self.subscriptions: Dict[str, Set[str]] = {}  # channel -> set of connection_ids
        self._connection_counter = 0
        self._lock = asyncio.Lock()
    
    def _generate_connection_id(self) -> str:
        """Generate unique connection ID"""
        self._connection_counter += 1
        return f"conn_{self._connection_counter}"
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle WebSocket connection lifecycle"""
        connection_id = self._generate_connection_id()
        ws_conn = WebSocketConnection(websocket)
        
        await websocket.accept()
        logger.info(f"[{connection_id}] WebSocket connected")
        
        async with self._lock:
            self.active_connections[connection_id] = ws_conn
        
        try:
            # Wait for authentication (timeout 10 seconds)
            auth_task = asyncio.create_task(self._wait_for_auth(connection_id, ws_conn))
            timeout_task = asyncio.create_task(asyncio.sleep(10))
            
            done, pending = await asyncio.wait(
                [auth_task, timeout_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            if timeout_task in done:
                await self._send_error(websocket, "Authentication timeout")
                await websocket.close(code=1008)
                return
            
            if not ws_conn.authenticated:
                await websocket.close(code=1008)
                return
            
            # Authentication successful - handle messages
            await self._handle_messages(connection_id, ws_conn)
            
        except WebSocketDisconnect:
            logger.info(f"[{connection_id}] Client disconnected")
        except Exception as e:
            logger.error(f"[{connection_id}] Error: {e}")
        finally:
            await self._cleanup_connection(connection_id)
    
    async def _wait_for_auth(self, connection_id: str, ws_conn: WebSocketConnection):
        """Wait for authentication message"""
        try:
            data = await ws_conn.websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') != 'auth':
                await self._send_error(ws_conn.websocket, "First message must be authentication")
                return
            
            api_key = message.get('api_key')
            if not api_key:
                await self._send_error(ws_conn.websocket, "Missing api_key")
                return
            
            # Validate API key
            is_valid, scope, client_info = await self.auth_middleware.validate_api_key(api_key)
            
            if not is_valid:
                await self._send_error(ws_conn.websocket, "Invalid or inactive API key")
                return
            
            # Authentication successful
            ws_conn.authenticated = True
            ws_conn.client_info = client_info
            
            await self._send_message(ws_conn.websocket, {
                "type": "auth_ok",
                "payload": {
                    "client_name": client_info['name'],
                    "scope": scope
                }
            })
            
            logger.info(f"[{connection_id}] Authenticated as {client_info['name']} (scope: {scope})")
            
        except json.JSONDecodeError:
            await self._send_error(ws_conn.websocket, "Invalid JSON")
        except Exception as e:
            logger.error(f"[{connection_id}] Auth error: {e}")
            await self._send_error(ws_conn.websocket, "Authentication failed")
    
    async def _handle_messages(self, connection_id: str, ws_conn: WebSocketConnection):
        """Handle incoming WebSocket messages after authentication"""
        while True:
            data = await ws_conn.websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get('type')
            
            if message_type == 'subscribe':
                await self._handle_subscribe(connection_id, ws_conn, message)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscribe(connection_id, ws_conn, message)
            elif message_type == 'ping':
                await self._send_message(ws_conn.websocket, {"type": "pong"})
            else:
                await self._send_error(ws_conn.websocket, f"Unknown message type: {message_type}")
    
    async def _handle_subscribe(self, connection_id: str, ws_conn: WebSocketConnection, message: dict):
        """Handle subscription request"""
        channel = message.get('channel')
        filters = message.get('filters', {})
        
        if not channel:
            await self._send_error(ws_conn.websocket, "Missing channel")
            return
        
        # Build subscription key (e.g., "fight:PFC50-F3" or "event:PFC50")
        if channel == 'fight':
            fight_code = filters.get('fight_code')
            if not fight_code:
                await self._send_error(ws_conn.websocket, "Missing fight_code filter")
                return
            subscription_key = f"fight:{fight_code}"
        elif channel == 'event':
            event_code = filters.get('event_code')
            if not event_code:
                await self._send_error(ws_conn.websocket, "Missing event_code filter")
                return
            subscription_key = f"event:{event_code}"
        else:
            await self._send_error(ws_conn.websocket, f"Unknown channel: {channel}")
            return
        
        # Add subscription
        async with self._lock:
            if subscription_key not in self.subscriptions:
                self.subscriptions[subscription_key] = set()
            self.subscriptions[subscription_key].add(connection_id)
            ws_conn.subscriptions.add(subscription_key)
        
        await self._send_message(ws_conn.websocket, {
            "type": "subscribe_ok",
            "payload": {
                "channel": channel,
                "subscription_key": subscription_key
            }
        })
        
        logger.info(f"[{connection_id}] Subscribed to {subscription_key}")
    
    async def _handle_unsubscribe(self, connection_id: str, ws_conn: WebSocketConnection, message: dict):
        """Handle unsubscription request"""
        subscription_key = message.get('subscription_key')
        
        if not subscription_key:
            await self._send_error(ws_conn.websocket, "Missing subscription_key")
            return
        
        async with self._lock:
            if subscription_key in self.subscriptions:
                self.subscriptions[subscription_key].discard(connection_id)
                if not self.subscriptions[subscription_key]:
                    del self.subscriptions[subscription_key]
            ws_conn.subscriptions.discard(subscription_key)
        
        await self._send_message(ws_conn.websocket, {
            "type": "unsubscribe_ok",
            "payload": {"subscription_key": subscription_key}
        })
        
        logger.info(f"[{connection_id}] Unsubscribed from {subscription_key}")
    
    async def broadcast_to_subscription(self, subscription_key: str, message: dict):
        """Broadcast message to all subscribers of a channel"""
        async with self._lock:
            connection_ids = self.subscriptions.get(subscription_key, set()).copy()
        
        if not connection_ids:
            return
        
        logger.info(f"Broadcasting to {len(connection_ids)} connections on {subscription_key}")
        
        # Send to each connection with scope-based filtering
        for connection_id in connection_ids:
            ws_conn = self.active_connections.get(connection_id)
            if ws_conn and ws_conn.authenticated:
                try:
                    # Filter payload based on client scope
                    filtered_message = message.copy()
                    if 'payload' in filtered_message:
                        filtered_message['payload'] = self.auth_middleware.filter_payload_by_scope(
                            filtered_message['payload'],
                            ws_conn.scope
                        )
                    
                    await self._send_message(ws_conn.websocket, filtered_message)
                except Exception as e:
                    logger.error(f"[{connection_id}] Broadcast error: {e}")
    
    async def _send_message(self, websocket: WebSocket, message: dict):
        """Send JSON message to WebSocket"""
        await websocket.send_text(json.dumps(message))
    
    async def _send_error(self, websocket: WebSocket, error: str):
        """Send error message to WebSocket"""
        await self._send_message(websocket, {
            "type": "error",
            "error": error
        })
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection and subscriptions"""
        async with self._lock:
            ws_conn = self.active_connections.pop(connection_id, None)
            
            if ws_conn:
                # Remove from all subscriptions
                for subscription_key in ws_conn.subscriptions:
                    if subscription_key in self.subscriptions:
                        self.subscriptions[subscription_key].discard(connection_id)
                        if not self.subscriptions[subscription_key]:
                            del self.subscriptions[subscription_key]
        
        logger.info(f"[{connection_id}] Connection cleaned up")
    
    def get_active_connection_count(self) -> int:
        """Get number of active WebSocket connections"""
        return len(self.active_connections)
    
    async def shutdown(self):
        """Gracefully shutdown all connections"""
        logger.info("Shutting down connection manager...")
        
        for connection_id, ws_conn in self.active_connections.items():
            try:
                await ws_conn.websocket.close(code=1001, reason="Server shutdown")
            except Exception as e:
                logger.error(f"Error closing connection {connection_id}: {e}")
        
        self.active_connections.clear()
        self.subscriptions.clear()
        
        logger.info("All connections closed")
