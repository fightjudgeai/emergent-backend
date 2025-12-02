"""
REST API Routes
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from datetime import datetime
import asyncpg

from models.schemas import Event, Fight, RoundState, FightResult
from auth.middleware import AuthMiddleware

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to get database pool and auth middleware (injected from main.py)
db_pool: Optional[asyncpg.Pool] = None
auth_middleware: Optional[AuthMiddleware] = None


def set_dependencies(pool: asyncpg.Pool, auth: AuthMiddleware):
    """Set global dependencies"""
    global db_pool, auth_middleware
    db_pool = pool
    auth_middleware = auth


async def verify_authorization(authorization: str = Header(...)) -> dict:
    """Verify API key from Authorization header"""
    if not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <API_KEY>'"
        )
    
    api_key = authorization.replace('Bearer ', '')
    
    is_valid, scope, client_info = await auth_middleware.validate_api_key(api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    return client_info


# ========================================
# EVENT ENDPOINTS
# ========================================

@router.get("/events/{event_code}", response_model=dict)
async def get_event(
    event_code: str,
    client_info: dict = Depends(verify_authorization)
):
    """
    Get event details by event code
    
    Returns event metadata including all fights on the card
    """
    try:
        async with db_pool.acquire() as conn:
            # Get event
            event_row = await conn.fetchrow(
                """
                SELECT id, code, name, venue, promotion, start_time_utc, created_at, updated_at
                FROM events
                WHERE code = $1
                """,
                event_code
            )
            
            if not event_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Event {event_code} not found"
                )
            
            # Get fights for this event
            fight_rows = await conn.fetch(
                """
                SELECT 
                    f.id, f.event_id, f.bout_order, f.code, 
                    f.red_fighter_id, f.blue_fighter_id, 
                    f.scheduled_rounds, f.weight_class, f.rule_set,
                    rf.first_name as red_first_name, rf.last_name as red_last_name,
                    rf.nickname as red_nickname, rf.country as red_country,
                    bf.first_name as blue_first_name, bf.last_name as blue_last_name,
                    bf.nickname as blue_nickname, bf.country as blue_country
                FROM fights f
                JOIN fighters rf ON f.red_fighter_id = rf.id
                JOIN fighters bf ON f.blue_fighter_id = bf.id
                WHERE f.event_id = $1
                ORDER BY f.bout_order
                """,
                event_row['id']
            )
            
            fights = []
            for fight_row in fight_rows:
                fights.append({
                    "code": fight_row['code'],
                    "bout_order": fight_row['bout_order'],
                    "red_corner": {
                        "first_name": fight_row['red_first_name'],
                        "last_name": fight_row['red_last_name'],
                        "nickname": fight_row['red_nickname'],
                        "country": fight_row['red_country']
                    },
                    "blue_corner": {
                        "first_name": fight_row['blue_first_name'],
                        "last_name": fight_row['blue_last_name'],
                        "nickname": fight_row['blue_nickname'],
                        "country": fight_row['blue_country']
                    },
                    "scheduled_rounds": fight_row['scheduled_rounds'],
                    "weight_class": fight_row['weight_class'],
                    "rule_set": fight_row['rule_set']
                })
            
            return {
                "event": {
                    "code": event_row['code'],
                    "name": event_row['name'],
                    "venue": event_row['venue'],
                    "promotion": event_row['promotion'],
                    "start_time_utc": event_row['start_time_utc'].isoformat()
                },
                "fights": fights,
                "total_fights": len(fights)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event {event_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ========================================
# FIGHT ENDPOINTS
# ========================================

@router.get("/fights/{fight_code}/live", response_model=dict)
async def get_fight_live_state(
    fight_code: str,
    client_info: dict = Depends(verify_authorization)
):
    """
    Get current live state of a fight (latest round_state)
    
    Returns the most recent round state with scope-based field filtering
    """
    try:
        async with db_pool.acquire() as conn:
            # Get fight details
            fight_row = await conn.fetchrow(
                """
                SELECT 
                    f.id, f.code, f.event_id, f.bout_order,
                    f.scheduled_rounds, f.weight_class,
                    e.code as event_code, e.name as event_name,
                    rf.first_name as red_first_name, rf.last_name as red_last_name,
                    rf.nickname as red_nickname,
                    bf.first_name as blue_first_name, bf.last_name as blue_last_name,
                    bf.nickname as blue_nickname
                FROM fights f
                JOIN events e ON f.event_id = e.id
                JOIN fighters rf ON f.red_fighter_id = rf.id
                JOIN fighters bf ON f.blue_fighter_id = bf.id
                WHERE f.code = $1
                """,
                fight_code
            )
            
            if not fight_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fight {fight_code} not found"
                )
            
            # Get latest round state
            state_row = await conn.fetchrow(
                """
                SELECT *
                FROM round_state
                WHERE fight_id = $1
                ORDER BY seq DESC
                LIMIT 1
                """,
                fight_row['id']
            )
            
            # Get fight result if available
            result_row = await conn.fetchrow(
                """
                SELECT winner_side, method, round, time
                FROM fight_results
                WHERE fight_id = $1
                """,
                fight_row['id']
            )
            
            response = {
                "fight": {
                    "code": fight_row['code'],
                    "event_code": fight_row['event_code'],
                    "event_name": fight_row['event_name'],
                    "bout_order": fight_row['bout_order'],
                    "red_corner": {
                        "name": f"{fight_row['red_first_name']} {fight_row['red_last_name']}",
                        "nickname": fight_row['red_nickname']
                    },
                    "blue_corner": {
                        "name": f"{fight_row['blue_first_name']} {fight_row['blue_last_name']}",
                        "nickname": fight_row['blue_nickname']
                    },
                    "scheduled_rounds": fight_row['scheduled_rounds'],
                    "weight_class": fight_row['weight_class']
                },
                "current_state": None,
                "result": None
            }
            
            # Add current state if available
            if state_row:
                state_payload = {
                    "round": state_row['round'],
                    "seq": state_row['seq'],
                    "ts_ms": state_row['ts_ms'],
                    "state": {
                        "red": {
                            "strikes": state_row['red_strikes'],
                            "sig_strikes": state_row['red_sig_strikes'],
                            "knockdowns": state_row['red_knockdowns'],
                            "control_sec": state_row['red_control_sec']
                        },
                        "blue": {
                            "strikes": state_row['blue_strikes'],
                            "sig_strikes": state_row['blue_sig_strikes'],
                            "knockdowns": state_row['blue_knockdowns'],
                            "control_sec": state_row['blue_control_sec']
                        }
                    },
                    "round_locked": state_row['round_locked']
                }
                
                # Add AI fields for advanced/pro scopes
                scope = client_info['scope']
                if scope in ['fantasy.advanced', 'sportsbook.pro']:
                    state_payload['state']['red']['ai_damage'] = float(state_row['red_ai_damage'])
                    state_payload['state']['red']['ai_win_prob'] = float(state_row['red_ai_win_prob'])
                    state_payload['state']['blue']['ai_damage'] = float(state_row['blue_ai_damage'])
                    state_payload['state']['blue']['ai_win_prob'] = float(state_row['blue_ai_win_prob'])
                
                response['current_state'] = state_payload
            
            # Add result if available
            if result_row:
                response['result'] = {
                    "winner": result_row['winner_side'],
                    "method": result_row['method'],
                    "round": result_row['round'],
                    "time": result_row['time']
                }
            
            return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching live state for {fight_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/fights/{fight_code}/timeline", response_model=dict)
async def get_fight_timeline(
    fight_code: str,
    round: Optional[int] = None,
    client_info: dict = Depends(verify_authorization)
):
    """
    Get historical timeline of fight state updates
    
    Query params:
    - round: Optional filter for specific round
    
    Returns all round_state records with scope-based filtering
    """
    # Only sportsbook.pro has access to full timeline
    if client_info['scope'] != 'sportsbook.pro':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Timeline access requires sportsbook.pro scope"
        )
    
    try:
        async with db_pool.acquire() as conn:
            # Get fight
            fight_row = await conn.fetchrow(
                "SELECT id, code FROM fights WHERE code = $1",
                fight_code
            )
            
            if not fight_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fight {fight_code} not found"
                )
            
            # Build query
            if round:
                query = """
                    SELECT *
                    FROM round_state
                    WHERE fight_id = $1 AND round = $2
                    ORDER BY seq ASC
                """
                rows = await conn.fetch(query, fight_row['id'], round)
            else:
                query = """
                    SELECT *
                    FROM round_state
                    WHERE fight_id = $1
                    ORDER BY seq ASC
                """
                rows = await conn.fetch(query, fight_row['id'])
            
            timeline = []
            for row in rows:
                timeline.append({
                    "seq": row['seq'],
                    "round": row['round'],
                    "ts_ms": row['ts_ms'],
                    "red": {
                        "strikes": row['red_strikes'],
                        "sig_strikes": row['red_sig_strikes'],
                        "knockdowns": row['red_knockdowns'],
                        "control_sec": row['red_control_sec'],
                        "ai_damage": float(row['red_ai_damage']),
                        "ai_win_prob": float(row['red_ai_win_prob'])
                    },
                    "blue": {
                        "strikes": row['blue_strikes'],
                        "sig_strikes": row['blue_sig_strikes'],
                        "knockdowns": row['blue_knockdowns'],
                        "control_sec": row['blue_control_sec'],
                        "ai_damage": float(row['blue_ai_damage']),
                        "ai_win_prob": float(row['blue_ai_win_prob'])
                    },
                    "round_locked": row['round_locked'],
                    "source": row['source']
                })
            
            return {
                "fight_code": fight_code,
                "round_filter": round,
                "total_updates": len(timeline),
                "timeline": timeline
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timeline for {fight_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ========================================
# ADMIN ENDPOINTS (Internal use)
# ========================================

@router.get("/admin/clients")
async def list_api_clients():
    """List all API clients (for internal admin use)"""
    # TODO: Add admin authentication
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, scope, active, rate_limit_per_min, created_at, last_used_at
                FROM api_clients
                ORDER BY created_at DESC
                """
            )
            
            clients = []
            for row in rows:
                clients.append({
                    "id": str(row['id']),
                    "name": row['name'],
                    "scope": row['scope'],
                    "active": row['active'],
                    "rate_limit_per_min": row['rate_limit_per_min'],
                    "created_at": row['created_at'].isoformat(),
                    "last_used_at": row['last_used_at'].isoformat() if row['last_used_at'] else None
                })
            
            return {"clients": clients, "total": len(clients)}
    
    except Exception as e:
        logger.error(f"Error listing API clients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
