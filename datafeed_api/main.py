"""
Fight Judge AI - Financial-Grade Real-Time Data Feed
WebSocket + REST API for sports data syndication
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncpg
from dotenv import load_dotenv

from auth.middleware import AuthMiddleware, verify_api_key
from websocket.connection_manager import ConnectionManager
from api.routes import router as api_router
from models.schemas import WebSocketMessage, AuthMessage

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
db_pool: Optional[asyncpg.Pool] = None
auth_middleware: Optional[AuthMiddleware] = None
connection_manager: Optional[ConnectionManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    global db_pool, auth_middleware, connection_manager
    
    # Startup
    logger.info("Starting Fight Judge AI Data Feed API...")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    try:
        # Create database connection pool
        db_pool = await asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("✓ Database connection pool created")
        
        # Initialize authentication middleware
        auth_middleware = AuthMiddleware(db_pool)
        logger.info("✓ Authentication middleware initialized")
        
        # Initialize WebSocket connection manager
        connection_manager = ConnectionManager(db_pool, auth_middleware)
        
        # Set services for fantasy/market data injection
        from services.fantasy_scoring_service import FantasyScoringService
        from services.market_settler import MarketSettler
        fantasy_svc = FantasyScoringService(db_pool)
        market_svc = MarketSettler(db_pool)
        connection_manager.set_services(fantasy_svc, market_svc)
        
        logger.info("✓ WebSocket connection manager initialized with fantasy/market injection")
        
        logger.info("=" * 60)
        logger.info("🚀 Fight Judge AI Data Feed API is LIVE")
        logger.info("=" * 60)
        logger.info(f"WebSocket: ws://localhost:{os.getenv('API_PORT', 8002)}/v1/realtime")
        logger.info(f"REST API: http://localhost:{os.getenv('API_PORT', 8002)}/v1")
        logger.info("=" * 60)
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Fight Judge AI Data Feed API...")
        
        if connection_manager:
            await connection_manager.shutdown()
        
        if db_pool:
            await db_pool.close()
            logger.info("✓ Database connection pool closed")


# Create FastAPI application
app = FastAPI(
    title="Fight Judge AI Data Feed",
    description="Financial-grade real-time sports data syndication API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include REST API routes
app.include_router(api_router, prefix="/v1")


# Inject dependencies into API routes after lifespan initialization
@app.on_event("startup")
async def inject_api_dependencies():
    """Inject database pool and auth middleware into API routes"""
    from api.routes import set_dependencies
    set_dependencies(db_pool, auth_middleware)


# ========================================
# WEBSOCKET ENDPOINT
# ========================================

@app.websocket("/v1/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time data feed WebSocket endpoint
    
    Protocol:
    1. Client connects
    2. Client sends auth message: {"type": "auth", "api_key": "..."}
    3. Server responds: {"type": "auth_ok"} or {"type": "auth_error"}
    4. Client subscribes: {"type": "subscribe", "channel": "fight", "filters": {"fight_code": "PFC50-F3"}}
    5. Server streams data: {"type": "round_state", "payload": {...}}
    """
    await connection_manager.handle_connection(websocket)


# ========================================
# HEALTH CHECK
# ========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        
        return {
            "status": "healthy",
            "database": "connected",
            "websocket_connections": connection_manager.get_active_connection_count(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Fight Judge AI Data Feed",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/v1/realtime",
            "rest_api": "/v1",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('API_PORT', 8002))
    host = os.getenv('API_HOST', '0.0.0.0')
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
