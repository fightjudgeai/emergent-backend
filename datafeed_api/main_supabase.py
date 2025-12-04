"""
Fight Judge AI - Financial-Grade Real-Time Data Feed (Supabase Version)
WebSocket + REST API for sports data syndication
"""

import os
import logging
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from database.supabase_client import SupabaseDB
from services.fantasy_scoring_service import FantasyScoringService
from services.market_settler import MarketSettler
from api import fantasy_routes, market_routes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global database client and services
db: Optional[SupabaseDB] = None
fantasy_service: Optional[FantasyScoringService] = None
market_service: Optional[MarketSettler] = None

# Create FastAPI application
app = FastAPI(
    title="Fight Judge AI Data Feed",
    description="Financial-grade real-time sports data syndication API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    global db, fantasy_service, market_service
    logger.info("Starting Fight Judge AI Data Feed API...")
    
    try:
        db = SupabaseDB()
        logger.info("✓ Supabase client initialized")
        
        # Test connection
        if db.health_check():
            logger.info("✓ Database connection verified")
        else:
            logger.warning("⚠ Database health check failed")
        
        # Initialize fantasy scoring service
        fantasy_service = FantasyScoringService(db)
        fantasy_routes.set_fantasy_service(fantasy_service)
        logger.info("✓ Fantasy scoring service initialized")
        
        # Initialize market settler service
        market_service = MarketSettler(db)
        market_routes.set_market_settler(market_service)
        logger.info("✓ Market settler service initialized")
        
        logger.info("="*60)
        logger.info("🚀 Fight Judge AI Data Feed API is LIVE")
        logger.info("="*60)
        logger.info(f"REST API: http://localhost:{os.getenv('API_PORT', 8002)}/v1")
        logger.info(f"Fantasy API: http://localhost:{os.getenv('API_PORT', 8002)}/v1/fantasy")
        logger.info(f"Markets API: http://localhost:{os.getenv('API_PORT', 8002)}/v1/markets")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down Fight Judge AI Data Feed API...")


# Dependency for API key verification
async def verify_api_key(authorization: str = Header(...)) -> dict:
    """Verify API key from Authorization header"""
    if not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <API_KEY>'"
        )
    
    api_key = authorization.replace('Bearer ', '')
    
    is_valid, scope, client_info = await db.validate_api_key(api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    return client_info


# ========================================
# REST API ENDPOINTS
# ========================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Fight Judge AI Data Feed",
        "version": "1.0.0",
        "endpoints": {
            "rest_api": "/v1",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if db and db.health_check():
            return {
                "status": "healthy",
                "database": "connected",
                "version": "1.0.0"
            }
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "database": "disconnected"
                }
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/v1/events/{event_code}")
async def get_event(event_code: str, authorization: str = Header(None)):
    """Get event details by event code"""
    # Simple auth check
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        event = db.get_event(event_code)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_code} not found"
            )
        
        # Get fights for this event
        fights = db.get_event_fights(event['id'])
        
        fight_list = []
        for fight in fights:
            fight_list.append({
                "code": fight['code'],
                "bout_order": fight['bout_order'],
                "red_corner": {
                    "first_name": fight['red_fighter']['first_name'],
                    "last_name": fight['red_fighter']['last_name'],
                    "nickname": fight['red_fighter']['nickname'],
                    "country": fight['red_fighter']['country']
                },
                "blue_corner": {
                    "first_name": fight['blue_fighter']['first_name'],
                    "last_name": fight['blue_fighter']['last_name'],
                    "nickname": fight['blue_fighter']['nickname'],
                    "country": fight['blue_fighter']['country']
                },
                "scheduled_rounds": fight['scheduled_rounds'],
                "weight_class": fight['weight_class'],
                "rule_set": fight['rule_set']
            })
        
        return {
            "event": {
                "code": event['code'],
                "name": event['name'],
                "venue": event['venue'],
                "promotion": event['promotion'],
                "start_time_utc": event['start_time_utc']
            },
            "fights": fight_list,
            "total_fights": len(fight_list)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event {event_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/v1/fights/{fight_code}/live")
async def get_fight_live(fight_code: str, authorization: str = Header(None)):
    """Get live fight state"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        fight = db.get_fight_by_code(fight_code)
        
        if not fight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fight {fight_code} not found"
            )
        
        # Get latest round state
        state = db.get_latest_round_state(fight['id'])
        
        # Get result
        result = db.get_fight_result(fight['id'])
        
        response = {
            "fight": {
                "code": fight['code'],
                "event_code": fight['event']['code'],
                "event_name": fight['event']['name'],
                "bout_order": fight['bout_order'],
                "red_corner": {
                    "name": f"{fight['red_fighter']['first_name']} {fight['red_fighter']['last_name']}",
                    "nickname": fight['red_fighter']['nickname']
                },
                "blue_corner": {
                    "name": f"{fight['blue_fighter']['first_name']} {fight['blue_fighter']['last_name']}",
                    "nickname": fight['blue_fighter']['nickname']
                },
                "scheduled_rounds": fight['scheduled_rounds'],
                "weight_class": fight['weight_class']
            },
            "current_state": None,
            "result": None
        }
        
        if state:
            response['current_state'] = {
                "round": state['round'],
                "seq": state['seq'],
                "ts_ms": state['ts_ms'],
                "state": {
                    "red": {
                        "strikes": state['red_strikes'],
                        "sig_strikes": state['red_sig_strikes'],
                        "knockdowns": state['red_knockdowns'],
                        "control_sec": state['red_control_sec'],
                        "ai_damage": float(state['red_ai_damage']),
                        "ai_win_prob": float(state['red_ai_win_prob'])
                    },
                    "blue": {
                        "strikes": state['blue_strikes'],
                        "sig_strikes": state['blue_sig_strikes'],
                        "knockdowns": state['blue_knockdowns'],
                        "control_sec": state['blue_control_sec'],
                        "ai_damage": float(state['blue_ai_damage']),
                        "ai_win_prob": float(state['blue_ai_win_prob'])
                    }
                },
                "round_locked": state['round_locked']
            }
        
        if result:
            response['result'] = {
                "winner": result['winner_side'],
                "method": result['method'],
                "round": result['round'],
                "time": result['time']
            }
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fight {fight_code}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/v1/admin/clients")
async def list_clients():
    """List all API clients"""
    try:
        clients = db.get_api_clients()
        return {"clients": clients, "total": len(clients)}
    except Exception as e:
        logger.error(f"Error listing clients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Include fantasy scoring routes
app.include_router(fantasy_routes.router, prefix="/v1")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('API_PORT', 8002))
    host = os.getenv('API_HOST', '0.0.0.0')
    
    uvicorn.run(
        "main_supabase:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
