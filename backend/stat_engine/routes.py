"""
Stat Engine API Routes

Endpoints for triggering aggregations and retrieving statistics.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from .models import (
    RoundStats, FightStats, CareerStats,
    AggregationJob, StatEngineHealth
)
from .event_reader import EventReader
from .round_aggregator import RoundStatsAggregator
from .fight_aggregator import FightStatsAggregator
from .career_aggregator import CareerStatsAggregator
from .scheduler import StatEngineScheduler
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["Stat Engine"])

# Global instances (initialized in server.py)
event_reader: Optional[EventReader] = None
round_aggregator: Optional[RoundStatsAggregator] = None
fight_aggregator: Optional[FightStatsAggregator] = None
career_aggregator: Optional[CareerStatsAggregator] = None
scheduler: Optional[StatEngineScheduler] = None
audit_logger: Optional[AuditLogger] = None


def init_stat_engine(db):
    """Initialize all stat engine components"""
    global event_reader, round_aggregator, fight_aggregator, career_aggregator, scheduler, audit_logger
    
    event_reader = EventReader(db)
    round_aggregator = RoundStatsAggregator(db, event_reader)
    fight_aggregator = FightStatsAggregator(db)
    career_aggregator = CareerStatsAggregator(db)
    scheduler = StatEngineScheduler(
        db=db,
        event_reader=event_reader,
        round_aggregator=round_aggregator,
        fight_aggregator=fight_aggregator,
        career_aggregator=career_aggregator
    )
    audit_logger = AuditLogger(db)
    
    logger.info("✅ Stat Engine fully initialized (with audit logging)")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return StatEngineHealth(
        service="Stat Engine",
        version="1.0.0",
        status="operational",
        event_reader_active=event_reader is not None,
        aggregation_active=scheduler is not None,
        scheduler_active=scheduler.is_running if scheduler else False
    )


# ============================================================================
# AGGREGATION TRIGGERS
# ============================================================================

@router.post("/aggregate/round")
async def aggregate_round(
    fight_id: str,
    round_num: int,
    trigger: str = "manual"
):
    """
    Trigger aggregation for a specific round
    
    Query Params:
    - fight_id: Bout ID
    - round_num: Round number
    - trigger: manual | round_locked
    
    Returns:
    - AggregationJob with results (audit logged)
    """
    
    if not scheduler:
        raise HTTPException(status_code=500, detail="Stat Engine not initialized")
    
    try:
        job = await scheduler.trigger_round_aggregation(
            fight_id=fight_id,
            round_num=round_num,
            trigger=trigger
        )
        
        result = {
            "job_id": job.id,
            "status": job.status,
            "rows_updated": job.rows_updated,
            "message": f"Round {round_num} aggregation completed"
        }
        
        # Audit log the action
        if audit_logger:
            await audit_logger.log_action(
                action_type="round_aggregation",
                trigger=trigger,
                fight_id=fight_id,
                round_num=round_num,
                result=result
            )
        
        return result
    
    except Exception as e:
        logger.error(f"Error aggregating round: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aggregate/fight")
async def aggregate_fight(
    fight_id: str,
    trigger: str = "manual"
):
    """
    Trigger aggregation for an entire fight
    
    Query Params:
    - fight_id: Bout ID
    - trigger: manual | post_fight
    
    Returns:
    - AggregationJob with results (audit logged)
    """
    
    if not scheduler:
        raise HTTPException(status_code=500, detail="Stat Engine not initialized")
    
    try:
        job = await scheduler.trigger_fight_aggregation(
            fight_id=fight_id,
            trigger=trigger
        )
        
        result = {
            "job_id": job.id,
            "status": job.status,
            "rows_updated": job.rows_updated,
            "message": f"Fight aggregation completed"
        }
        
        # Audit log the action
        if audit_logger:
            await audit_logger.log_action(
                action_type="fight_aggregation",
                trigger=trigger,
                fight_id=fight_id,
                result=result
            )
        
        return result
    
    except Exception as e:
        logger.error(f"Error aggregating fight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aggregate/career")
async def aggregate_career(
    fighter_id: Optional[str] = None,
    trigger: str = "manual"
):
    """
    Trigger career aggregation (single fighter or all)
    
    Query Params:
    - fighter_id: Fighter ID (optional - None = all fighters)
    - trigger: manual | nightly
    
    Returns:
    - AggregationJob with results
    """
    
    if not scheduler:
        raise HTTPException(status_code=500, detail="Stat Engine not initialized")
    
    try:
        job = await scheduler.trigger_career_aggregation(
            fighter_id=fighter_id,
            trigger=trigger
        )
        
        scope = f"fighter {fighter_id}" if fighter_id else "all fighters"
        
        return {
            "job_id": job.id,
            "status": job.status,
            "rows_updated": job.rows_updated,
            "message": f"Career aggregation completed for {scope}"
        }
    
    except Exception as e:
        logger.error(f"Error aggregating career: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aggregate/full/{fight_id}")
async def full_recalculation(fight_id: str):
    """
    Trigger full recalculation for a fight
    
    Aggregates:
    - All rounds
    - Fight stats
    - Career stats for all fighters in fight
    
    Use for fixing data issues or after major changes.
    """
    
    if not scheduler:
        raise HTTPException(status_code=500, detail="Stat Engine not initialized")
    
    try:
        jobs = await scheduler.trigger_full_recalculation(fight_id)
        
        return {
            "fight_id": fight_id,
            "jobs_executed": len(jobs),
            "successful": len([j for j in jobs if j.status == "completed"]),
            "failed": len([j for j in jobs if j.status == "failed"]),
            "message": f"Full recalculation completed: {len(jobs)} jobs"
        }
    
    except Exception as e:
        logger.error(f"Error in full recalculation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS RETRIEVAL
# ============================================================================

@router.get("/round/{fight_id}/{round_num}/{fighter_id}")
async def get_round_stats(
    fight_id: str,
    round_num: int,
    fighter_id: str
):
    """
    Get statistics for a specific round and fighter
    
    Returns:
    - RoundStats object with all statistics
    """
    
    if not round_aggregator or not round_aggregator.db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        doc = await round_aggregator.db.round_stats.find_one({
            "fight_id": fight_id,
            "round_num": round_num,
            "fighter_id": fighter_id
        })
        
        if not doc:
            raise HTTPException(status_code=404, detail="Round stats not found")
        
        doc.pop('_id', None)
        return RoundStats(**doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting round stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fight/{fight_id}/{fighter_id}")
async def get_fight_stats(
    fight_id: str,
    fighter_id: str
):
    """
    Get statistics for an entire fight and fighter
    
    Returns:
    - FightStats object with all statistics
    """
    
    if not fight_aggregator or not fight_aggregator.db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        doc = await fight_aggregator.db.fight_stats.find_one({
            "fight_id": fight_id,
            "fighter_id": fighter_id
        })
        
        if not doc:
            raise HTTPException(status_code=404, detail="Fight stats not found")
        
        doc.pop('_id', None)
        return FightStats(**doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fight stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/career/{fighter_id}")
async def get_career_stats(fighter_id: str):
    """
    Get career statistics for a fighter
    
    Returns:
    - CareerStats object with lifetime statistics
    """
    
    if not career_aggregator or not career_aggregator.db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        doc = await career_aggregator.db.career_stats.find_one({
            "fighter_id": fighter_id
        })
        
        if not doc:
            raise HTTPException(status_code=404, detail="Career stats not found")
        
        doc.pop('_id', None)
        return CareerStats(**doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting career stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fight/{fight_id}/all")
async def get_all_fight_stats(fight_id: str):
    """
    Get fight statistics for all fighters in a fight
    
    Returns:
    - List of FightStats for all fighters
    """
    
    if not fight_aggregator or not fight_aggregator.db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    try:
        cursor = fight_aggregator.db.fight_stats.find({"fight_id": fight_id})
        docs = await cursor.to_list(length=None)
        
        stats = []
        for doc in docs:
            doc.pop('_id', None)
            stats.append(FightStats(**doc))
        
        return {"fight_id": fight_id, "fighters": stats, "count": len(stats)}
    
    except Exception as e:
        logger.error(f"Error getting all fight stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# JOB MANAGEMENT
# ============================================================================

@router.get("/jobs")
async def get_recent_jobs(limit: int = Query(20, ge=1, le=100)):
    """
    Get recent aggregation jobs
    
    Query Params:
    - limit: Maximum number of jobs to return (default 20)
    
    Returns:
    - List of recent AggregationJob records
    """
    
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    try:
        jobs = await scheduler.get_recent_jobs(limit=limit)
        return {"jobs": jobs, "count": len(jobs)}
    
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
