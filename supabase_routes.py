"""
Supabase-based API routes for fights and judgments (v1)
Add these routes to your FastAPI app
Features:
- Input validation with Pydantic
- Retry logic for transient failures
- Standardized response format
- API versioning
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import logging
import json
from datetime import datetime, timezone

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

# Create router with versioning
supabase_router = APIRouter(prefix="/v1/supabase", tags=["supabase"])

# ==============================================================================
# DATA MODELS
# ==============================================================================

class FightCreate(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=255, description="External fight identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Fight metadata (fighters, event, location, etc.)")
    
    @validator('external_id')
    def validate_external_id(cls, v):
        """Validate external_id is not just whitespace"""
        if not v.strip():
            raise ValueError("external_id cannot be empty or whitespace")
        return v.strip()
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Ensure metadata is valid JSON-serializable"""
        if v is None:
            return {}
        try:
            json.dumps(v)  # Ensure it's JSON serializable
        except (TypeError, ValueError) as e:
            raise ValueError(f"metadata must be JSON-serializable: {e}")
        return v

class FightUpdate(BaseModel):
    external_id: Optional[str] = Field(None, min_length=1, max_length=255)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Ensure metadata is valid JSON-serializable"""
        if v is None:
            return None
        try:
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"metadata must be JSON-serializable: {e}")
        return v

class JudgmentCreate(BaseModel):
    fight_id: str = Field(..., description="UUID of the fight")
    judge: Optional[str] = Field(None, max_length=255, description="Judge identifier")
    scores: Dict[str, Any] = Field(..., description="Scoring data (rounds, criteria, etc.)")
    
    @validator('scores')
    def validate_scores(cls, v):
        """Ensure scores is valid and not empty"""
        if not v:
            raise ValueError("scores cannot be empty")
        try:
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"scores must be JSON-serializable: {e}")
        return v

class JudgmentUpdate(BaseModel):
    judge: Optional[str] = Field(None, max_length=255)
    scores: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    
    @validator('scores')
    def validate_scores(cls, v):
        """Ensure scores is valid"""
        if v is None:
            return None
        try:
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"scores must be JSON-serializable: {e}")
        return v

# ==============================================================================
# FIGHTS ENDPOINTS
# ==============================================================================

@supabase_router.post("/fights", summary="Create a new fight")
async def create_new_fight(fight: FightCreate):
    """
    Create a new fight record in Supabase
    
    - **external_id**: External fight identifier
    - **metadata**: Optional JSON metadata (fighters, event info, etc.)
    """
    try:
        result = await create_fight(
            external_id=fight.external_id,
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
    - **judge**: Judge identifier (optional)
    - **scores**: Scoring breakdown (required)
    """
    try:
        result = await create_judgment(
            fight_id=judgment.fight_id,
            judge=judgment.judge,
            scores=judgment.scores
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
# HEALTH CHECK ENDPOINT
# ==============================================================================

@supabase_router.get("/health", summary="Health check with database status")
async def health_check():
    """
    Comprehensive health check endpoint
    Returns status of Supabase connectivity and basic statistics
    """
    try:
        from supabase_client import check_supabase_health, http_client
        
        # Check Supabase connectivity
        supabase_ok = await check_supabase_health() if http_client else False
        
        # Get basic counts
        fights_count = len(await list_fights(limit=1)) if supabase_ok else 0
        judgments_count = len(await list_judgments(limit=1)) if supabase_ok else 0
        
        return {
            "status": "ok" if supabase_ok else "degraded",
            "service": "supabase",
            "database_connected": supabase_ok,
            "statistics": {
                "total_fights_stored": len(await list_fights(limit=10000)) if supabase_ok else 0,
                "total_judgments_stored": len(await list_judgments(limit=10000)) if supabase_ok else 0,
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "service": "supabase",
            "database_connected": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
# ==============================================================================
# EXPORT ROUTER
# ==============================================================================

def get_supabase_router():
    """Return the Supabase router to be included in FastAPI app"""
    return supabase_router

# ==============================================================================
# INTEGRATION INSTRUCTIONS & API DOCUMENTATION
# ==============================================================================
"""
API Versioning: v1.0
Path Prefix: /api/v1/supabase

Features:
- RESTful CRUD operations for fights and judgments
- Input validation with Pydantic models
- Automatic retry logic for transient network failures (up to 3 attempts)
- JSON schema validation for metadata and scores fields
- Health check with database connectivity status
- Statistics endpoints for monitoring

Endpoints Overview:

FIGHTS:
  - POST   /api/v1/supabase/fights              - Create a new fight
  - GET    /api/v1/supabase/fights              - List all fights (paginated)
  - GET    /api/v1/supabase/fights/{fight_id}   - Get specific fight
  - PUT    /api/v1/supabase/fights/{fight_id}   - Update a fight

JUDGMENTS:
  - POST   /api/v1/supabase/judgments                    - Submit a judgment
  - GET    /api/v1/supabase/judgments                    - List all judgments
  - GET    /api/v1/supabase/judgments/{judgment_id}      - Get specific judgment
  - PUT    /api/v1/supabase/judgments/{judgment_id}      - Update a judgment
  - GET    /api/v1/supabase/fights/{fight_id}/judgments  - Get judgments for fight

ANALYTICS:
  - GET    /api/v1/supabase/stats/fights      - Fight statistics
  - GET    /api/v1/supabase/stats/judgments   - Judgment statistics

MONITORING:
  - GET    /api/v1/supabase/health  - Health check with database status

Example Requests:

1. Create a fight:
   POST /api/v1/supabase/fights
   {
     "external_id": "fight_001",
     "metadata": {
       "event": "UFC 300",
       "fighters": ["Fighter A", "Fighter B"],
       "location": "Las Vegas",
       "date": "2026-02-07"
     }
   }

2. Create a judgment:
   POST /api/v1/supabase/judgments
   {
     "fight_id": "550e8400-e29b-41d4-a716-446655440000",
     "judge": "Judge1",
     "scores": {
       "round_1": 10,
       "round_2": 9,
       "round_3": 10,
       "winner": "fighter1"
     }
   }

3. Get health status:
   GET /api/v1/supabase/health
   Response: { "status": "ok", "database_connected": true, ... }

Error Handling:
- 400 Bad Request: Validation errors on input fields
- 404 Not Found: Resource doesn't exist
- 500 Internal Server Error: Database or server error
  
All 5xx errors include automatic retry logic (up to 3 attempts with exponential backoff)
for transient failures (timeouts, connection errors).
"""

