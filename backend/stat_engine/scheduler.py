"""
MODULE 5: Scheduler

Supports multiple trigger types:
- Manual trigger (on-demand via API)
- Round-locked trigger (when round is locked)
- Post-fight trigger (when fight completes)
- Nightly career aggregation (scheduled job)

Fault-tolerant with job tracking and retry logic.
"""

import logging
import asyncio
from typing import Optional, List
from datetime import datetime, timezone

from .models import AggregationJob
from .event_reader import EventReader
from .round_aggregator import RoundStatsAggregator
from .fight_aggregator import FightStatsAggregator
from .career_aggregator import CareerStatsAggregator

logger = logging.getLogger(__name__)


class StatEngineScheduler:
    """Schedules and executes stat aggregation jobs"""
    
    def __init__(
        self,
        db,
        event_reader: EventReader,
        round_aggregator: RoundStatsAggregator,
        fight_aggregator: FightStatsAggregator,
        career_aggregator: CareerStatsAggregator
    ):
        self.db = db
        self.event_reader = event_reader
        self.round_aggregator = round_aggregator
        self.fight_aggregator = fight_aggregator
        self.career_aggregator = career_aggregator
        
        self.is_running = False
        self.nightly_task = None
        
        logger.info("Stat Engine Scheduler initialized")
    
    async def trigger_round_aggregation(
        self,
        fight_id: str,
        round_num: int,
        trigger: str = "manual"
    ) -> AggregationJob:
        """
        Trigger aggregation for a specific round
        
        Args:
            fight_id: Bout ID
            round_num: Round number
            trigger: Trigger type (manual, round_locked)
        
        Returns:
            AggregationJob with results
        """
        
        logger.info(f"Triggering round aggregation: fight={fight_id}, round={round_num}, trigger={trigger}")
        
        # Create job record
        job = AggregationJob(
            job_type="round",
            trigger=trigger,
            fight_id=fight_id,
            round_num=round_num,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # Aggregate all fighters in this round
            round_stats = await self.round_aggregator.aggregate_all_fighters_in_round(
                fight_id=fight_id,
                round_num=round_num
            )
            
            job.rows_processed = len(round_stats)
            job.rows_updated = len(round_stats)
            job.status = "completed"
            
            logger.info(f"Round aggregation completed: {job.rows_updated} fighters aggregated")
        
        except Exception as e:
            logger.error(f"Round aggregation failed: {e}")
            job.status = "failed"
            job.errors.append(str(e))
        
        finally:
            job.completed_at = datetime.now(timezone.utc)
            await self._save_job(job)
        
        return job
    
    async def trigger_fight_aggregation(
        self,
        fight_id: str,
        trigger: str = "manual"
    ) -> AggregationJob:
        """
        Trigger aggregation for an entire fight
        
        Args:
            fight_id: Bout ID
            trigger: Trigger type (manual, post_fight)
        
        Returns:
            AggregationJob with results
        """
        
        logger.info(f"Triggering fight aggregation: fight={fight_id}, trigger={trigger}")
        
        job = AggregationJob(
            job_type="fight",
            trigger=trigger,
            fight_id=fight_id,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # First, ensure all rounds are aggregated
            rounds = await self.event_reader.get_fight_rounds(fight_id)
            
            for round_num in rounds:
                await self.round_aggregator.aggregate_all_fighters_in_round(
                    fight_id=fight_id,
                    round_num=round_num
                )
            
            # Now aggregate fight stats
            fight_stats = await self.fight_aggregator.aggregate_all_fighters_in_fight(fight_id)
            
            job.rows_processed = len(fight_stats)
            job.rows_updated = len(fight_stats)
            job.status = "completed"
            
            logger.info(f"Fight aggregation completed: {job.rows_updated} fighters aggregated")
        
        except Exception as e:
            logger.error(f"Fight aggregation failed: {e}")
            job.status = "failed"
            job.errors.append(str(e))
        
        finally:
            job.completed_at = datetime.now(timezone.utc)
            await self._save_job(job)
        
        return job
    
    async def trigger_career_aggregation(
        self,
        fighter_id: Optional[str] = None,
        trigger: str = "manual"
    ) -> AggregationJob:
        """
        Trigger career aggregation (single fighter or all)
        
        Args:
            fighter_id: Fighter ID (None = all fighters)
            trigger: Trigger type (manual, nightly)
        
        Returns:
            AggregationJob with results
        """
        
        scope = f"fighter={fighter_id}" if fighter_id else "all fighters"
        logger.info(f"Triggering career aggregation: {scope}, trigger={trigger}")
        
        job = AggregationJob(
            job_type="career",
            trigger=trigger,
            fighter_id=fighter_id,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            if fighter_id:
                # Single fighter
                stats = await self.career_aggregator.aggregate_and_save(fighter_id)
                job.rows_processed = 1
                job.rows_updated = 1
            else:
                # All fighters (nightly job)
                all_stats = await self.career_aggregator.aggregate_all_fighters()
                job.rows_processed = len(all_stats)
                job.rows_updated = len(all_stats)
            
            job.status = "completed"
            logger.info(f"Career aggregation completed: {job.rows_updated} fighters aggregated")
        
        except Exception as e:
            logger.error(f"Career aggregation failed: {e}")
            job.status = "failed"
            job.errors.append(str(e))
        
        finally:
            job.completed_at = datetime.now(timezone.utc)
            await self._save_job(job)
        
        return job
    
    async def trigger_full_recalculation(self, fight_id: str) -> List[AggregationJob]:
        """
        Trigger full recalculation for a fight (all rounds + fight + career)
        
        Useful for fixing data issues or after major event changes.
        
        Returns:
            List of all jobs executed
        """
        
        logger.info(f"Triggering FULL recalculation for fight={fight_id}")
        
        jobs = []
        
        # 1. Aggregate all rounds
        rounds = await self.event_reader.get_fight_rounds(fight_id)
        for round_num in rounds:
            job = await self.trigger_round_aggregation(
                fight_id=fight_id,
                round_num=round_num,
                trigger="manual"
            )
            jobs.append(job)
        
        # 2. Aggregate fight
        fight_job = await self.trigger_fight_aggregation(
            fight_id=fight_id,
            trigger="manual"
        )
        jobs.append(fight_job)
        
        # 3. Aggregate career for all fighters in this fight
        fighters = await self.event_reader.get_fight_fighters(fight_id)
        for fighter_id in fighters:
            career_job = await self.trigger_career_aggregation(
                fighter_id=fighter_id,
                trigger="manual"
            )
            jobs.append(career_job)
        
        logger.info(f"Full recalculation completed: {len(jobs)} jobs executed")
        return jobs
    
    async def start_nightly_aggregation(self, hour: int = 3):
        """
        Start nightly career aggregation background task
        
        Args:
            hour: Hour of day to run (default 3am UTC)
        """
        
        if self.nightly_task and not self.nightly_task.done():
            logger.warning("Nightly aggregation already running")
            return
        
        logger.info(f"Starting nightly aggregation scheduler (runs at {hour}:00 UTC)")
        self.is_running = True
        self.nightly_task = asyncio.create_task(self._nightly_loop(hour))
    
    async def stop_nightly_aggregation(self):
        """Stop nightly aggregation background task"""
        
        logger.info("Stopping nightly aggregation scheduler")
        self.is_running = False
        
        if self.nightly_task:
            self.nightly_task.cancel()
            try:
                await self.nightly_task
            except asyncio.CancelledError:
                pass
    
    async def _nightly_loop(self, target_hour: int):
        """
        Background loop that runs nightly career aggregation
        """
        
        while self.is_running:
            try:
                # Calculate seconds until next run
                now = datetime.now(timezone.utc)
                next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                
                # If target hour already passed today, run tomorrow
                if next_run <= now:
                    next_run = next_run.replace(day=next_run.day + 1)
                
                wait_seconds = (next_run - now).total_seconds()
                
                logger.info(f"Nightly aggregation scheduled for {next_run} (in {wait_seconds/3600:.1f} hours)")
                
                # Wait until target time
                await asyncio.sleep(wait_seconds)
                
                # Run career aggregation for all fighters
                logger.info("Starting nightly career aggregation...")
                await self.trigger_career_aggregation(trigger="nightly")
                logger.info("Nightly career aggregation completed")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in nightly aggregation loop: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)
    
    async def _save_job(self, job: AggregationJob) -> bool:
        """Save job record to database"""
        
        if not self.db:
            return False
        
        try:
            doc = job.model_dump()
            
            # Convert datetimes
            if doc.get('started_at'):
                doc['started_at'] = doc['started_at'].isoformat() if isinstance(doc['started_at'], datetime) else doc['started_at']
            if doc.get('completed_at'):
                doc['completed_at'] = doc['completed_at'].isoformat() if isinstance(doc['completed_at'], datetime) else doc['completed_at']
            doc['created_at'] = doc['created_at'].isoformat() if isinstance(doc['created_at'], datetime) else doc['created_at']
            
            await self.db.aggregation_jobs.insert_one(doc)
            return True
        
        except Exception as e:
            logger.error(f"Error saving job: {e}")
            return False
    
    async def get_recent_jobs(self, limit: int = 20) -> List[AggregationJob]:
        """Get recent aggregation jobs"""
        
        if not self.db:
            return []
        
        try:
            cursor = self.db.aggregation_jobs.find().sort("created_at", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            
            jobs = []
            for doc in docs:
                doc.pop('_id', None)
                jobs.append(AggregationJob(**doc))
            
            return jobs
        
        except Exception as e:
            logger.error(f"Error getting jobs: {e}")
            return []
