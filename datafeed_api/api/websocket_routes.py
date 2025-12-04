"""
WebSocket API Routes
Endpoints for WebSocket token generation and connection
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status, Depends
from typing import Optional

from auth.dependencies import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

# Global services (set during startup)
jwt_service = None
ws_manager = None


def set_services(jwt_svc, ws_mgr):
    """Set global services"""
    global jwt_service, ws_manager
    jwt_service = jwt_svc
    ws_manager = ws_mgr


@router.post("/websocket/token")
async def generate_websocket_token(
    event_slug: str,
    client_info: dict = Depends(require_api_key)
):
    """
    Generate JWT token for WebSocket connection
    
    **Requires API key authentication**
    
    Query params:
    - event_slug: Event to subscribe to
    
    Returns:
        WebSocket URL with token and expiration info
        
    Example:
    ```
    POST /websocket/token?event_slug=UFC309
    X-API-Key: FJAI_FANTASY_BASIC_001
    
    Response:
    {
        "websocket_url": "wss://fightjudge.ai/live/UFC309?token=eyJ...",
        "token": "eyJ...",
        "expires_at": "2024-01-04T13:00:00Z",
        "tier": "fantasy.basic"
    }
    ```
    """
    try:
        client_id = client_info['id']
        tier = client_info['tier']
        
        # Generate token
        token, expires_at = jwt_service.generate_token(client_id, tier)
        
        # Generate WebSocket URL
        ws_url = f"ws://localhost:8002/ws/live/{event_slug}?token={token}"
        
        return {
            "websocket_url": ws_url,
            "token": token,
            "expires_at": expires_at.isoformat(),
            "tier": tier,
            "event": event_slug,
            "instructions": "Connect to websocket_url to receive real-time updates"
        }
    
    except Exception as e:
        logger.error(f"Error generating WebSocket token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating token: {str(e)}"
        )


@router.websocket("/ws/live/{event_slug}")
async def websocket_endpoint(
    websocket: WebSocket,
    event_slug: str,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time fight data
    
    **Requires JWT token** (obtained from POST /websocket/token)
    
    Connection URL:
    ```
    ws://localhost:8002/ws/live/{event_slug}?token={jwt_token}
    ```
    
    Message Types:
    
    **From Server:**
    - `connected` - Connection established
    - `fight_update` - Real-time fight data
    - `pong` - Response to ping
    
    **From Client:**
    - `subscribe` - Subscribe to additional event
    - `unsubscribe` - Unsubscribe from event
    - `ping` - Keepalive ping
    
    Example Messages:
    ```json
    // Server -> Client (fight update)
    {
        "type": "fight_update",
        "event": "UFC309",
        "data": {
            "fight_id": "uuid",
            "current_round": 2,
            "red_score": 45.5,
            "blue_score": 32.0
        },
        "timestamp": "2024-01-04T12:30:00Z"
    }
    
    // Client -> Server (ping)
    {
        "type": "ping"
    }
    ```
    """
    session_id = None
    
    try:
        # Authenticate and connect
        session_id = await ws_manager.authenticate_and_connect(
            websocket,
            event_slug,
            token
        )
        
        if not session_id:
            # Authentication failed (connection already closed)
            return
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                # Handle client message
                await ws_manager.handle_client_message(session_id, data)
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        if session_id:
            await ws_manager.disconnect(session_id)


@router.get("/websocket/active")
async def get_active_connections(client_info: dict = Depends(require_api_key)):
    """
    Get active WebSocket connections
    
    **Admin/monitoring endpoint**
    
    Returns:
        Statistics about active WebSocket connections
    """
    try:
        total_connections = ws_manager.get_active_connection_count()
        
        # Get event-specific counts
        event_counts = {}
        for event_slug in ws_manager.event_subscribers.keys():
            event_counts[event_slug] = ws_manager.get_event_subscriber_count(event_slug)
        
        return {
            "total_active_connections": total_connections,
            "event_subscribers": event_counts,
            "timestamp": "2024-01-04T12:00:00Z"
        }
    
    except Exception as e:
        logger.error(f"Error fetching active connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching connection stats"
        )
