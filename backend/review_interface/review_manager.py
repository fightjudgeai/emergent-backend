"""
Review Manager

Handles event editing, versioning, merging, and deletion with audit logging.
"""

import logging
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
import uuid
import copy

logger = logging.getLogger(__name__)


class ReviewManager:
    """Post-fight event review and editing"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
    
    async def get_fight_timeline(self, fight_id: str) -> Dict[str, Any]:
        """
        Get complete timeline of all events for a fight
        
        Args:
            fight_id: Fight identifier
            
        Returns:
            Chronological timeline with all events
        """
        try:
            events = await self.db.events.find(
                {'bout_id': fight_id}
            ).sort('timestamp', 1).to_list(length=10000)
            
            # Group by round
            rounds = {}
            for event in events:
                round_num = event.get('round', 1)
                if round_num not in rounds:
                    rounds[round_num] = []
                rounds[round_num].append(event)
            
            return {
                'fight_id': fight_id,
                'total_events': len(events),
                'rounds': rounds,
                'timeline': events
            }
        
        except Exception as e:
            logger.error(f"Error getting fight timeline: {e}")
            return {'error': str(e)}
    
    async def edit_event(
        self,
        event_id: str,
        updates: Dict[str, Any],
        supervisor_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Edit an event with versioning
        
        All edits are:
        - Versioned (original kept in event_versions)
        - Logged by supervisor_id
        - Tracked in audit log
        
        Args:
            event_id: Event ID to edit
            updates: Fields to update
            supervisor_id: Supervisor making the edit
            reason: Reason for edit
            
        Returns:
            Updated event and version info
        """
        try:
            # Get original event
            original_event = await self.db.events.find_one({'id': event_id})
            
            if not original_event:
                return {'error': 'Event not found'}
            
            # Create version record
            version_doc = {
                'version_id': str(uuid.uuid4()),
                'event_id': event_id,
                'original_data': copy.deepcopy(original_event),
                'changes': updates,
                'supervisor_id': supervisor_id,
                'reason': reason,
                'created_at': datetime.now(timezone.utc)
            }
            
            await self.db.event_versions.insert_one(version_doc)
            
            # Update event
            updates['updated_at'] = datetime.now(timezone.utc)
            updates['last_edited_by'] = supervisor_id
            
            await self.db.events.update_one(
                {'id': event_id},
                {'$set': updates}
            )
            
            # Log audit trail
            await self._log_audit(
                action='edit_event',
                event_id=event_id,
                supervisor_id=supervisor_id,
                details={'updates': updates, 'reason': reason}
            )
            
            logger.info(f"Event {event_id} edited by {supervisor_id}")
            
            return {
                'status': 'success',
                'event_id': event_id,
                'version_id': version_doc['version_id']
            }
        
        except Exception as e:
            logger.error(f"Error editing event: {e}")
            return {'error': str(e)}
    
    async def delete_event(
        self,
        event_id: str,
        supervisor_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Delete incorrect event (soft delete with versioning)
        
        Args:
            event_id: Event ID to delete
            supervisor_id: Supervisor performing deletion
            reason: Reason for deletion
            
        Returns:
            Deletion status
        """
        try:
            # Get event
            event = await self.db.events.find_one({'id': event_id})
            
            if not event:
                return {'error': 'Event not found'}
            
            # Create version record before deletion
            version_doc = {
                'version_id': str(uuid.uuid4()),
                'event_id': event_id,
                'original_data': copy.deepcopy(event),
                'action': 'delete',
                'supervisor_id': supervisor_id,
                'reason': reason,
                'created_at': datetime.now(timezone.utc)
            }
            
            await self.db.event_versions.insert_one(version_doc)
            
            # Soft delete (mark as deleted)
            await self.db.events.update_one(
                {'id': event_id},
                {
                    '$set': {
                        'deleted': True,
                        'deleted_by': supervisor_id,
                        'deleted_at': datetime.now(timezone.utc),
                        'deletion_reason': reason
                    }
                }
            )
            
            # Log audit trail
            await self._log_audit(
                action='delete_event',
                event_id=event_id,
                supervisor_id=supervisor_id,
                details={'reason': reason}
            )
            
            logger.info(f"Event {event_id} deleted by {supervisor_id}")
            
            return {
                'status': 'success',
                'event_id': event_id,
                'version_id': version_doc['version_id']
            }
        
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return {'error': str(e)}
    
    async def merge_duplicate_events(
        self,
        event_ids: List[str],
        supervisor_id: str,
        merged_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge duplicate events into single event
        
        Args:
            event_ids: List of event IDs to merge
            supervisor_id: Supervisor performing merge
            merged_data: Data for merged event
            
        Returns:
            Merged event info
        """
        try:
            if len(event_ids) < 2:
                return {'error': 'Need at least 2 events to merge'}
            
            # Get all events
            events = await self.db.events.find(
                {'id': {'$in': event_ids}}
            ).to_list(length=100)
            
            if len(events) != len(event_ids):
                return {'error': 'Some events not found'}
            
            # Create merged event
            merged_event_id = str(uuid.uuid4())
            merged_event = {
                'id': merged_event_id,
                **merged_data,
                'merged_from': event_ids,
                'merged_by': supervisor_id,
                'merged_at': datetime.now(timezone.utc),
                'created_at': datetime.now(timezone.utc)
            }
            
            await self.db.events.insert_one(merged_event)
            
            # Version all original events
            for event in events:
                version_doc = {
                    'version_id': str(uuid.uuid4()),
                    'event_id': event['id'],
                    'original_data': copy.deepcopy(event),
                    'action': 'merge',
                    'merged_into': merged_event_id,
                    'supervisor_id': supervisor_id,
                    'created_at': datetime.now(timezone.utc)
                }
                await self.db.event_versions.insert_one(version_doc)
            
            # Soft delete originals
            await self.db.events.update_many(
                {'id': {'$in': event_ids}},
                {
                    '$set': {
                        'deleted': True,
                        'merged_into': merged_event_id,
                        'deleted_by': supervisor_id,
                        'deleted_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            # Log audit trail
            await self._log_audit(
                action='merge_events',
                event_id=merged_event_id,
                supervisor_id=supervisor_id,
                details={'merged_from': event_ids}
            )
            
            logger.info(f"Merged {len(event_ids)} events into {merged_event_id}")
            
            return {
                'status': 'success',
                'merged_event_id': merged_event_id,
                'merged_count': len(event_ids)
            }
        
        except Exception as e:
            logger.error(f"Error merging events: {e}")
            return {'error': str(e)}
    
    async def approve_and_rerun_stats(
        self,
        fight_id: str,
        supervisor_id: str
    ) -> Dict[str, Any]:
        """
        Approve all edits and trigger stat engine re-run
        
        Args:
            fight_id: Fight ID
            supervisor_id: Supervisor approving
            
        Returns:
            Approval and recalculation status
        """
        try:
            # Mark fight as reviewed
            await self.db.fight_reviews.insert_one({
                'review_id': str(uuid.uuid4()),
                'fight_id': fight_id,
                'supervisor_id': supervisor_id,
                'status': 'approved',
                'approved_at': datetime.now(timezone.utc)
            })
            
            # Trigger stat recalculation
            job_doc = {
                'job_id': str(uuid.uuid4()),
                'fight_id': fight_id,
                'job_type': 'manual_review_approval',
                'status': 'pending',
                'created_by': supervisor_id,
                'created_at': datetime.now(timezone.utc)
            }
            
            await self.db.stat_recalculation_jobs.insert_one(job_doc)
            
            # Log audit trail
            await self._log_audit(
                action='approve_review',
                fight_id=fight_id,
                supervisor_id=supervisor_id,
                details={'job_id': job_doc['job_id']}
            )
            
            logger.info(f"Fight {fight_id} approved by {supervisor_id}, stats recalculation triggered")
            
            return {
                'status': 'success',
                'fight_id': fight_id,
                'job_id': job_doc['job_id']
            }
        
        except Exception as e:
            logger.error(f"Error approving review: {e}")
            return {'error': str(e)}
    
    async def get_event_history(
        self,
        event_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get version history for an event
        
        Args:
            event_id: Event ID
            
        Returns:
            List of versions
        """
        try:
            versions = await self.db.event_versions.find(
                {'event_id': event_id}
            ).sort('created_at', -1).to_list(length=100)
            
            return versions
        
        except Exception as e:
            logger.error(f"Error getting event history: {e}")
            return []
    
    async def _log_audit(
        self,
        action: str,
        supervisor_id: str,
        details: Dict[str, Any],
        event_id: str = None,
        fight_id: str = None
    ):
        """Log action to audit trail"""
        try:
            audit_doc = {
                'audit_id': str(uuid.uuid4()),
                'action': action,
                'supervisor_id': supervisor_id,
                'event_id': event_id,
                'fight_id': fight_id,
                'details': details,
                'timestamp': datetime.now(timezone.utc)
            }
            
            await self.db.review_audit_log.insert_one(audit_doc)
        
        except Exception as e:
            logger.error(f"Error logging audit: {e}")
