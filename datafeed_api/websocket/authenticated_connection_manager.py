"""
Authenticated WebSocket Connection Manager
Handles JWT-authenticated WebSocket connections for real-time data
"""

import json
import logging
import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class AuthenticatedWebSocketConnection:
    """Represents an authenticated WebSocket connection"""
    
    def __init__(
        self,
        websocket: WebSocket,
        client_id: str,
        tier: str,
        session_id: str
    ):
        self.websocket = websocket
        self.client_id = client_id
        self.tier = tier
        self.session_id = session_id
        self.subscriptions: Set[str] = set()
        self.connected_at = datetime.utcnow()


class AuthenticatedConnectionManager:
    """
    Manages authenticated WebSocket connections
    
    Requires JWT token for connection
    Tracks usage for billing
    """
    
    def __init__(self, db_client, jwt_service):
        """
        Initialize connection manager
        
        Args:
            db_client: Database client
            jwt_service: JWT service for token validation
        """
        self.db = db_client
        self.jwt_service = jwt_service
        self.active_connections: Dict[str, AuthenticatedWebSocketConnection] = {}
        self.event_subscribers: Dict[str, Set[str]] = {}  # event_slug -> set of session_ids
        self._lock = asyncio.Lock()
    
    async def authenticate_and_connect(
        self,
        websocket: WebSocket,
        event_slug: str,
        token: str
    ) -> Optional[str]:
        """
        Authenticate WebSocket connection with JWT token
        
        Args:
            websocket: WebSocket instance
            event_slug: Event slug to subscribe to
            token: JWT token
        
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            # Validate token
            is_valid, payload = self.jwt_service.validate_token(token)
            
            if not is_valid or not payload:
                logger.warning("WebSocket authentication failed: invalid token")
                await websocket.close(code=1008, reason="Unauthorized: Invalid token")
                return None
            
            client_id = payload.get('client_id')
            tier = payload.get('tier')
            
            if not client_id or not tier:
                logger.warning("WebSocket authentication failed: missing client info in token")
                await websocket.close(code=1008, reason="Unauthorized: Invalid token payload")
                return None
            
            # Accept connection
            await websocket.accept()
            
            # Create session in database
            session_response = self.db.client.table('websocket_sessions').insert({
                'client_id': client_id,
                'session_token': token[:50],  # Store truncated token for reference
                'event_slug': event_slug,
                'ip_address': websocket.client.host if websocket.client else None,
                'user_agent': websocket.headers.get('user-agent')
            }).execute()
            
            if not session_response.data:
                logger.error("Failed to create WebSocket session in database")
                await websocket.close(code=1011, reason="Internal error")
                return None
            
            session_id = session_response.data[0]['id']
            
            # Create connection object
            connection = AuthenticatedWebSocketConnection(
                websocket=websocket,
                client_id=client_id,
                tier=tier,
                session_id=session_id
            )
            
            async with self._lock:
                self.active_connections[session_id] = connection
                
                # Subscribe to event
                if event_slug not in self.event_subscribers:
                    self.event_subscribers[event_slug] = set()
                self.event_subscribers[event_slug].add(session_id)
            
            logger.info(f"WebSocket connected: session={session_id}, client={client_id}, tier={tier}, event={event_slug}")
            
            # Send welcome message
            await self.send_personal_message(session_id, {
                'type': 'connected',
                'session_id': session_id,
                'tier': tier,
                'event': event_slug,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return session_id
        
        except Exception as e:
            logger.error(f"Error authenticating WebSocket: {e}")
            try:
                await websocket.close(code=1011, reason="Internal error")
            except:
                pass
            return None
    
    async def disconnect(self, session_id: str):
        """
        Disconnect WebSocket and update billing
        
        Args:
            session_id: Session ID
        """
        async with self._lock:
            if session_id not in self.active_connections:
                return
            
            connection = self.active_connections[session_id]
            
            try:
                # Close WebSocket
                await connection.websocket.close()
            except:
                pass
            
            # Update session in database (triggers billing update)
            self.db.client.table('websocket_sessions')\
                .update({'disconnected_at': datetime.utcnow().isoformat()})\
                .eq('id', session_id)\
                .execute()
            
            # Remove from subscriptions
            for event_slug, subscribers in self.event_subscribers.items():
                subscribers.discard(session_id)
            
            # Remove connection
            del self.active_connections[session_id]
            
            logger.info(f"WebSocket disconnected: session={session_id}")
    
    async def send_personal_message(self, session_id: str, message: dict):
        """
        Send message to specific connection
        
        Args:
            session_id: Session ID
            message: Message dict
        """
        if session_id not in self.active_connections:
            return
        
        connection = self.active_connections[session_id]
        
        try:
            await connection.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to {session_id}: {e}")
            await self.disconnect(session_id)
    
    async def broadcast_to_event(self, event_slug: str, message: dict):
        """
        Broadcast message to all connections subscribed to an event
        
        Args:
            event_slug: Event slug
            message: Message dict
        """
        if event_slug not in self.event_subscribers:
            return
        
        subscribers = list(self.event_subscribers[event_slug])
        
        for session_id in subscribers:
            await self.send_personal_message(session_id, message)
    
    async def broadcast_fight_update(
        self,
        event_slug: str,
        fight_data: dict
    ):
        """
        Broadcast fight update with tier-appropriate data
        
        Args:
            event_slug: Event slug
            fight_data: Fight data dict
        """
        if event_slug not in self.event_subscribers:
            return
        
        subscribers = list(self.event_subscribers[event_slug])
        
        for session_id in subscribers:
            if session_id not in self.active_connections:
                continue
            
            connection = self.active_connections[session_id]
            tier = connection.tier
            
            # Filter data based on tier
            filtered_data = self._filter_data_by_tier(fight_data, tier)
            
            message = {
                'type': 'fight_update',
                'event': event_slug,
                'data': filtered_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await self.send_personal_message(session_id, message)
    
    def _filter_data_by_tier(self, data: dict, tier: str) -> dict:
        """
        Filter data based on client tier
        
        Args:
            data: Full data dict
            tier: Client tier
        
        Returns:
            Filtered data dict
        """
        # Basic tiers get limited data
        if tier in ['public', 'dev']:
            return {
                'fight_id': data.get('fight_id'),
                'status': data.get('status'),
                'current_round': data.get('current_round')
            }
        
        # Fantasy tiers get full fight data
        if tier in ['fantasy.basic', 'fantasy.advanced']:
            filtered = dict(data)
            # Remove market data for fantasy-only tiers
            filtered.pop('markets', None)
            filtered.pop('settlement', None)
            return filtered
        
        # Sportsbook and enterprise get everything
        return data
    
    def get_active_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_event_subscriber_count(self, event_slug: str) -> int:
        """Get number of subscribers for an event"""
        return len(self.event_subscribers.get(event_slug, set()))
    
    async def handle_client_message(self, session_id: str, message: dict):
        """
        Handle message received from client
        
        Args:
            session_id: Session ID
            message: Message dict from client
        """
        if session_id not in self.active_connections:
            return
        
        message_type = message.get('type')
        
        if message_type == 'subscribe':
            # Subscribe to additional event
            event_slug = message.get('event')
            if event_slug:
                async with self._lock:
                    if event_slug not in self.event_subscribers:
                        self.event_subscribers[event_slug] = set()
                    self.event_subscribers[event_slug].add(session_id)
                
                await self.send_personal_message(session_id, {
                    'type': 'subscribed',
                    'event': event_slug,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        elif message_type == 'unsubscribe':
            # Unsubscribe from event
            event_slug = message.get('event')
            if event_slug and event_slug in self.event_subscribers:
                self.event_subscribers[event_slug].discard(session_id)
                
                await self.send_personal_message(session_id, {
                    'type': 'unsubscribed',
                    'event': event_slug,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        elif message_type == 'ping':
            # Respond to ping
            await self.send_personal_message(session_id, {
                'type': 'pong',
                'timestamp': datetime.utcnow().isoformat()
            })
