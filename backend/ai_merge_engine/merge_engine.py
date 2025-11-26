"""
Merge Engine

Intelligent merging of AI events with human events using tolerance-based rules.
"""

import logging
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta
import uuid

logger = logging.getLogger(__name__)


class MergeEngine:
    """AI event merge engine with conflict detection"""
    
    # Tolerance thresholds for auto-approval
    TIME_TOLERANCE_MS = 2000  # 2 seconds
    POSITION_TOLERANCE = 1  # Adjacent positions acceptable
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
    
    async def merge_ai_batch(
        self,
        ai_events: List[Dict[str, Any]],
        fight_id: str,
        submitted_by: str = "colab_ai"
    ) -> Dict[str, Any]:
        """
        Merge batch of AI events with existing human events
        
        Args:
            ai_events: List of AI-generated events
            fight_id: Fight identifier
            submitted_by: Source identifier (e.g., "colab_ai", "roboflow_cv")
            
        Returns:
            Merge result with auto-approved, conflicted, and rejected counts
        """
        try:
            results = {
                'auto_approved': 0,
                'marked_for_review': 0,
                'rejected': 0,
                'total_submitted': len(ai_events),
                'approved_events': [],
                'review_required': [],
                'errors': []
            }
            
            # Get existing human events for this fight
            human_events = await self.db.events.find({
                'bout_id': fight_id,
                'source': {'$in': ['judge_software', 'stat_operator']}
            }).to_list(length=10000)
            
            # Process each AI event
            for ai_event in ai_events:
                try:
                    merge_result = await self._process_ai_event(
                        ai_event,
                        human_events,
                        fight_id,
                        submitted_by
                    )
                    
                    if merge_result['action'] == 'auto_approve':
                        results['auto_approved'] += 1
                        results['approved_events'].append(merge_result['event'])
                    
                    elif merge_result['action'] == 'review':
                        results['marked_for_review'] += 1
                        results['review_required'].append(merge_result)
                    
                    elif merge_result['action'] == 'reject':
                        results['rejected'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing AI event: {e}")
                    results['errors'].append(str(e))
            
            # Store auto-approved events
            if results['approved_events']:
                await self.db.events.insert_many(results['approved_events'])
                logger.info(f"Auto-approved {len(results['approved_events'])} AI events")
                
                # Trigger stat recalculation
                await self._trigger_stat_recalculation(fight_id)
            
            # Store review items
            if results['review_required']:
                await self._store_review_items(results['review_required'], fight_id)
            
            return results
            
        except Exception as e:
            logger.error(f"Error merging AI batch: {e}")
            return {
                'error': str(e),
                'total_submitted': len(ai_events)
            }
    
    async def _process_ai_event(
        self,
        ai_event: Dict[str, Any],
        human_events: List[Dict[str, Any]],
        fight_id: str,
        submitted_by: str
    ) -> Dict[str, Any]:
        """Process single AI event and determine merge action"""
        
        # Find matching human events (within tolerance)
        matching_events = self._find_matching_events(ai_event, human_events)
        
        if not matching_events:
            # No human event found - auto-approve if confidence high
            confidence = ai_event.get('confidence', 0)
            
            if confidence >= 0.85:
                # Auto-approve high-confidence AI event
                approved_event = self._prepare_event_for_storage(
                    ai_event, fight_id, submitted_by, approved=True
                )
                return {
                    'action': 'auto_approve',
                    'event': approved_event,
                    'reason': 'High confidence, no conflicting human event'
                }
            else:
                # Low confidence, mark for review
                return {
                    'action': 'review',
                    'ai_event': ai_event,
                    'reason': 'Low confidence, requires human verification',
                    'confidence': confidence
                }
        
        # Found matching human event(s)
        best_match = matching_events[0]
        
        # Check agreement
        if self._events_agree(ai_event, best_match):
            # Agreement - auto-approve to reinforce human data
            approved_event = self._prepare_event_for_storage(
                ai_event, fight_id, submitted_by, approved=True
            )
            return {
                'action': 'auto_approve',
                'event': approved_event,
                'reason': 'Agrees with human event within tolerance',
                'matched_human_event_id': best_match.get('id')
            }
        
        else:
            # Conflict detected - mark for review
            return {
                'action': 'review',
                'ai_event': ai_event,
                'conflicting_human_event': best_match,
                'reason': 'Conflict with human event',
                'differences': self._get_differences(ai_event, best_match)
            }
    
    def _find_matching_events(
        self,
        ai_event: Dict[str, Any],
        human_events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find human events that match AI event within tolerance"""
        
        matches = []
        
        ai_timestamp = ai_event.get('timestamp')
        ai_round = ai_event.get('round', 1)
        ai_fighter = ai_event.get('fighter_id')
        
        # Parse AI timestamp if it's a string
        if isinstance(ai_timestamp, str):
            try:
                ai_timestamp = datetime.fromisoformat(ai_timestamp.replace('Z', '+00:00'))
            except:
                ai_timestamp = None
        
        for human_event in human_events:
            # Check round
            if human_event.get('round') != ai_round:
                continue
            
            # Check fighter
            if human_event.get('fighter_id') != ai_fighter:
                continue
            
            # Check timestamp (within tolerance)
            human_timestamp = human_event.get('timestamp')
            
            if ai_timestamp and human_timestamp:
                # Ensure human_timestamp is datetime
                if isinstance(human_timestamp, str):
                    try:
                        human_timestamp = datetime.fromisoformat(human_timestamp.replace('Z', '+00:00'))
                    except:
                        continue
                
                # Calculate time difference
                time_diff = abs((ai_timestamp - human_timestamp).total_seconds() * 1000)
                
                if time_diff <= self.TIME_TOLERANCE_MS:
                    matches.append(human_event)
        
        return matches
    
    def _events_agree(
        self,
        ai_event: Dict[str, Any],
        human_event: Dict[str, Any]
    ) -> bool:
        """Check if AI and human events agree within tolerance"""
        
        # Check event type
        ai_type = ai_event.get('event_type', '').lower()
        human_type = human_event.get('event_type', '').lower()
        
        # Normalize types for comparison
        if ai_type != human_type:
            # Check for similar types (e.g., "jab" vs "punch")
            if not self._types_similar(ai_type, human_type):
                return False
        
        # Check target area if available
        ai_target = ai_event.get('target', '').lower()
        human_target = human_event.get('target', '').lower()
        
        if ai_target and human_target and ai_target != human_target:
            return False
        
        # Events agree
        return True
    
    def _types_similar(self, type1: str, type2: str) -> bool:
        """Check if event types are similar"""
        
        # Strike type groups
        punch_types = ['jab', 'cross', 'hook', 'uppercut', 'punch']
        kick_types = ['head kick', 'body kick', 'low kick', 'kick', 'front kick']
        
        if type1 in punch_types and type2 in punch_types:
            return True
        
        if type1 in kick_types and type2 in kick_types:
            return True
        
        return type1 == type2
    
    def _get_differences(
        self,
        ai_event: Dict[str, Any],
        human_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get differences between AI and human events"""
        
        differences = {}
        
        fields_to_compare = ['event_type', 'target', 'position', 'landed', 'power']
        
        for field in fields_to_compare:
            ai_value = ai_event.get(field)
            human_value = human_event.get(field)
            
            if ai_value != human_value:
                differences[field] = {
                    'ai': ai_value,
                    'human': human_value
                }
        
        return differences
    
    def _prepare_event_for_storage(
        self,
        ai_event: Dict[str, Any],
        fight_id: str,
        submitted_by: str,
        approved: bool
    ) -> Dict[str, Any]:
        """Prepare AI event for storage in events collection"""
        
        event_doc = {
            'id': str(uuid.uuid4()),
            'bout_id': fight_id,
            'fighter_id': ai_event.get('fighter_id'),
            'round': ai_event.get('round', 1),
            'timestamp': ai_event.get('timestamp', datetime.now(timezone.utc)),
            'event_type': ai_event.get('event_type'),
            'source': 'ai_cv',  # Mark as AI source
            'ai_confidence': ai_event.get('confidence', 0),
            'submitted_by': submitted_by,
            'auto_approved': approved,
            'created_at': datetime.now(timezone.utc)
        }
        
        # Optional fields
        optional_fields = ['target', 'position', 'landed', 'power', 'judge_id', 'notes']
        for field in optional_fields:
            if field in ai_event:
                event_doc[field] = ai_event[field]
        
        return event_doc
    
    async def _store_review_items(
        self,
        review_items: List[Dict[str, Any]],
        fight_id: str
    ):
        """Store items that require human review"""
        
        try:
            review_docs = []
            
            for item in review_items:
                review_doc = {
                    'review_id': str(uuid.uuid4()),
                    'fight_id': fight_id,
                    'ai_event': item.get('ai_event'),
                    'conflicting_human_event': item.get('conflicting_human_event'),
                    'reason': item.get('reason'),
                    'differences': item.get('differences', {}),
                    'status': 'pending',
                    'created_at': datetime.now(timezone.utc)
                }
                review_docs.append(review_doc)
            
            if review_docs:
                await self.db.ai_event_reviews.insert_many(review_docs)
                logger.info(f"Stored {len(review_docs)} items for review")
        
        except Exception as e:
            logger.error(f"Error storing review items: {e}")
    
    async def _trigger_stat_recalculation(self, fight_id: str):
        """Trigger automatic stat recalculation after AI event approval"""
        
        try:
            # Create recalculation job
            job_doc = {
                'job_id': str(uuid.uuid4()),
                'fight_id': fight_id,
                'job_type': 'ai_event_merge',
                'status': 'pending',
                'created_at': datetime.now(timezone.utc)
            }
            
            await self.db.stat_recalculation_jobs.insert_one(job_doc)
            logger.info(f"Triggered stat recalculation for fight {fight_id}")
        
        except Exception as e:
            logger.error(f"Error triggering stat recalculation: {e}")
    
    async def approve_review_item(
        self,
        review_id: str,
        approved_version: str,
        approved_by: str
    ) -> bool:
        """
        Approve a review item
        
        Args:
            review_id: Review item ID
            approved_version: 'ai' or 'human' or 'merged'
            approved_by: Supervisor ID
            
        Returns:
            Success status
        """
        try:
            # Get review item
            review_item = await self.db.ai_event_reviews.find_one({'review_id': review_id})
            
            if not review_item:
                return False
            
            # Insert approved event
            if approved_version == 'ai':
                ai_event = review_item['ai_event']
                event_doc = self._prepare_event_for_storage(
                    ai_event,
                    review_item['fight_id'],
                    'manual_approval',
                    approved=True
                )
                await self.db.events.insert_one(event_doc)
            
            # Update review status
            await self.db.ai_event_reviews.update_one(
                {'review_id': review_id},
                {
                    '$set': {
                        'status': 'approved',
                        'approved_version': approved_version,
                        'approved_by': approved_by,
                        'approved_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            # Trigger stat recalculation
            await self._trigger_stat_recalculation(review_item['fight_id'])
            
            return True
        
        except Exception as e:
            logger.error(f"Error approving review item: {e}")
            return False
    
    async def get_review_items(
        self,
        fight_id: Optional[str] = None,
        status: str = 'pending',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get AI event review items"""
        
        try:
            query = {'status': status}
            
            if fight_id:
                query['fight_id'] = fight_id
            
            items = await self.db.ai_event_reviews.find(query, {"_id": 0}).limit(limit).to_list(length=limit)
            return items
        
        except Exception as e:
            logger.error(f"Error getting review items: {e}")
            return []
