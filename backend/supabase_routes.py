"""
Supabase-based API routes for fights and judgments
Add these routes to your FastAPI app
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from supabase_client import (
    create_fight,
    get_fight,
    list_fights,
    update_fight,
    create_judgment,
    get_judgment,
    get_fight_judgments,
    list_judgments,
    update_judgment,
)

logger = logging.getLogger(__name__)

# Create router
supabase_router = APIRouter(prefix="/api/supabase", tags=["supabase"])

# ==============================================================================
# DATA MODELS
# ==============================================================================

class FightCreate(BaseModel):
    description: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FightUpdate(BaseModel):
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class JudgmentCreate(BaseModel):
    fight_id: str
    winner: Optional[str] = None
    scores: Dict[str, Any]
    reasoning: str
    ai_model: Optional[str] = None
    user_id: Optional[str] = None

class JudgmentUpdate(BaseModel):
    winner: Optional[str] = None
    scores: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None

# ==============================================================================
# FIGHTS ENDPOINTS
# ==============================================================================

@supabase_router.post("/fights", summary="Create a new fight")
async def create_new_fight(fight: FightCreate):
    """
    Create a new fight record in Supabase
    
    - **description**: Description of the fight
    - **user_id**: Optional user identifier
    - **metadata**: Optional JSON metadata (fighters, event info, etc.)
    """
    try:
        result = await create_fight(
            description=fight.description,
            user_id=fight.user_id,
            metadata=fight.metadata
        )
        if result:
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=400, detail="Failed to create fight")
    except Exception as e:
        logger.error(f"Error creating fight: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.get("/fights/{fight_id}", summary="Get a fight by ID")
async def get_fight_details(fight_id: str):
    """Get fight details by ID"""
    try:
        fight = await get_fight(fight_id)
        if fight:
            return {"status": "success", "data": fight}
        else:
            raise HTTPException(status_code=404, detail="Fight not found")
    except Exception as e:
        logger.error(f"Error getting fight: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.get("/fights", summary="List all fights")
async def list_all_fights(
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """
    List fights with optional filtering
    
    - **user_id**: Optional filter by user
    - **limit**: Maximum number of results (max 100)
    """
    try:
        fights = await list_fights(user_id=user_id, limit=limit)
        return {
            "status": "success",
            "count": len(fights),
            "data": fights
        }
    except Exception as e:
        logger.error(f"Error listing fights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.put("/fights/{fight_id}", summary="Update a fight")
async def update_fight_details(fight_id: str, updates: FightUpdate):
    """Update fight details"""
    try:
        update_dict = updates.dict(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = await update_fight(fight_id, update_dict)
        if result:
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=404, detail="Fight not found")
    except Exception as e:
        logger.error(f"Error updating fight: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# JUDGMENTS ENDPOINTS
# ==============================================================================

@supabase_router.post("/judgments", summary="Submit a judgment")
async def submit_new_judgment(judgment: JudgmentCreate):
    """
    Create a new judgment record
    
    - **fight_id**: ID of the fight being judged
    - **winner**: Winner of the fight (optional)
    - **scores**: Scoring breakdown (required)
    - **reasoning**: Text explanation of the judgment
    - **ai_model**: Name of AI model used (optional)
    - **user_id**: Judge user ID (optional)
    """
    try:
        result = await create_judgment(
            fight_id=judgment.fight_id,
            winner=judgment.winner,
            scores=judgment.scores,
            reasoning=judgment.reasoning,
            ai_model=judgment.ai_model,
            user_id=judgment.user_id
        )
        if result:
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=400, detail="Failed to create judgment")
    except Exception as e:
        logger.error(f"Error creating judgment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.get("/judgments/{judgment_id}", summary="Get a judgment by ID")
async def get_judgment_details(judgment_id: str):
    """Get judgment details by ID"""
    try:
        judgment = await get_judgment(judgment_id)
        if judgment:
            return {"status": "success", "data": judgment}
        else:
            raise HTTPException(status_code=404, detail="Judgment not found")
    except Exception as e:
        logger.error(f"Error getting judgment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.get("/fights/{fight_id}/judgments", summary="Get judgments for a fight")
async def get_fight_judgments_list(fight_id: str):
    """Get all judgments for a specific fight"""
    try:
        judgments = await get_fight_judgments(fight_id)
        return {
            "status": "success",
            "fight_id": fight_id,
            "count": len(judgments),
            "data": judgments
        }
    except Exception as e:
        logger.error(f"Error getting fight judgments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.get("/judgments", summary="List all judgments")
async def list_all_judgments(
    user_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """
    List judgments with optional filtering
    
    - **user_id**: Optional filter by judge
    - **limit**: Maximum number of results (max 500)
    """
    try:
        judgments = await list_judgments(user_id=user_id, limit=limit)
        return {
            "status": "success",
            "count": len(judgments),
            "data": judgments
        }
    except Exception as e:
        logger.error(f"Error listing judgments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.put("/judgments/{judgment_id}", summary="Update a judgment")
async def update_judgment_details(judgment_id: str, updates: JudgmentUpdate):
    """Update judgment details"""
    try:
        update_dict = updates.dict(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = await update_judgment(judgment_id, update_dict)
        if result:
            return {"status": "success", "data": result}
        else:
            raise HTTPException(status_code=404, detail="Judgment not found")
    except Exception as e:
        logger.error(f"Error updating judgment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# ANALYTICS ENDPOINTS
# ==============================================================================

@supabase_router.get("/stats/fights", summary="Fight statistics")
async def get_fight_stats(user_id: Optional[str] = None):
    """Get statistics about fights"""
    try:
        fights = await list_fights(user_id=user_id, limit=1000)
        return {
            "status": "success",
            "total_fights": len(fights),
            "latest_fight": fights[0] if fights else None,
            "filtered_by_user": user_id is not None
        }
    except Exception as e:
        logger.error(f"Error getting fight stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@supabase_router.get("/stats/judgments", summary="Judgment statistics")
async def get_judgment_stats(user_id: Optional[str] = None):
    """Get statistics about judgments"""
    try:
        judgments = await list_judgments(user_id=user_id, limit=1000)
        
        # Calculate basic stats
        total = len(judgments)
        with_winners = sum(1 for j in judgments if j.get("winner"))
        
        return {
            "status": "success",
            "total_judgments": total,
            "judgments_with_winner": with_winners,
            "latest_judgment": judgments[0] if judgments else None,
            "filtered_by_judge": user_id is not None
        }
    except Exception as e:
        logger.error(f"Error getting judgment stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# EXPORT ROUTER
# ==============================================================================

def get_supabase_router():
    """Return the Supabase router to be included in FastAPI app"""
    return supabase_router

# ==============================================================================
# INTEGRATION INSTRUCTIONS
# ==============================================================================
"""
To integrate these routes into your FastAPI app (server.py):

1. Import at the top:
   from supabase_routes import get_supabase_router

2. In your app setup section, add:
   supabase_router = get_supabase_router()
   app.include_router(supabase_router)

3. Make sure you've initialized Supabase in startup:
   from supabase_client import init_supabase
   
   @app.on_event("startup")
   async def startup_supabase():
       init_supabase()

4. Your endpoints will be available at:
   - POST   /api/supabase/fights
   - GET    /api/supabase/fights
   - GET    /api/supabase/fights/{fight_id}
   - PUT    /api/supabase/fights/{fight_id}
   - POST   /api/supabase/judgments
   - GET    /api/supabase/judgments
   - GET    /api/supabase/judgments/{judgment_id}
   - GET    /api/supabase/fights/{fight_id}/judgments
   - PUT    /api/supabase/judgments/{judgment_id}
   - GET    /api/supabase/stats/fights
   - GET    /api/supabase/stats/judgments
"""
