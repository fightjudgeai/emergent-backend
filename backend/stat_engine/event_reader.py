"""
MODULE 1: Event Reader

Reads fight events from the existing events table.
CRITICAL: This module ONLY reads. It NEVER writes to events table.

Supports filtering by:
- fight_id (bout_id)
- round
- fighter_id
- event_type
- source
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class EventReader:
    """Reads events from existing judge logging system"""
    
    def __init__(self, db):
        self.db = db
        logger.info("Event Reader initialized (READ-ONLY mode)")
    
    async def get_fight_events(
        self,
        fight_id: str,
        round_num: Optional[int] = None,
        fighter_id: Optional[str] = None,
        event_type: Optional[str] = None,
        source: Optional[str] = None
    ) -> List[Dict]:
        """
        Read events from database with filters
        
        Args:
            fight_id: Bout ID (required)
            round_num: Filter by round number
            fighter_id: Filter by fighter
            event_type: Filter by event type
            source: Filter by source (judge, cv, hybrid)
        
        Returns:
            List of event documents
        """
        
        if not self.db:
            logger.warning("Database not available")
            return []
        
        try:
            # Build query
            query = {"boutId": fight_id}
            
            if round_num is not None:
                query["round"] = round_num
            
            if fighter_id:
                query["fighterId"] = fighter_id
            
            if event_type:
                query["eventType"] = event_type
            
            if source:
                query["source"] = source
            
            # Execute query (sorted by timestamp)
            cursor = self.db.events.find(query).sort("timestamp", 1)
            events = await cursor.to_list(length=None)
            
            logger.info(
                f"Read {len(events)} events for fight={fight_id}, "
                f"round={round_num}, fighter={fighter_id}"
            )
            
            return events
        
        except Exception as e:
            logger.error(f"Error reading events: {e}")
            return []
    
    async def get_round_events(self, fight_id: str, round_num: int) -> List[Dict]:
        """Get all events for a specific round"""
        return await self.get_fight_events(fight_id=fight_id, round_num=round_num)
    
    async def get_fighter_events(
        self,
        fight_id: str,
        fighter_id: str,
        round_num: Optional[int] = None
    ) -> List[Dict]:
        """Get all events for a specific fighter"""
        return await self.get_fight_events(
            fight_id=fight_id,
            fighter_id=fighter_id,
            round_num=round_num
        )
    
    async def get_control_events(
        self,
        fight_id: str,
        round_num: int,
        fighter_id: str
    ) -> List[Dict]:
        """
        Get control start/stop events for calculating control time
        
        Returns events where:
        - eventType contains 'CTRL', 'Control', 'control'
        - Has metadata.type = 'start' or 'stop'
        """
        
        all_events = await self.get_fighter_events(
            fight_id=fight_id,
            fighter_id=fighter_id,
            round_num=round_num
        )
        
        # Filter for control events
        control_events = []
        for event in all_events:
            event_type = event.get("eventType", "")
            metadata = event.get("metadata", {})
            
            # Check if it's a control event
            is_control = any(keyword in event_type.lower() for keyword in [
                "control", "ctrl", "back control", "top control", "cage control",
                "ground back control", "ground top control"
            ])
            
            if is_control:
                control_events.append(event)
        
        logger.debug(f"Found {len(control_events)} control events")
        return control_events
    
    async def get_event_count(
        self,
        fight_id: str,
        round_num: Optional[int] = None,
        fighter_id: Optional[str] = None
    ) -> int:
        """Get count of events matching criteria"""
        
        if not self.db:
            return 0
        
        try:
            query = {"boutId": fight_id}
            
            if round_num is not None:
                query["round"] = round_num
            
            if fighter_id:
                query["fighterId"] = fighter_id
            
            count = await self.db.events.count_documents(query)
            return count
        
        except Exception as e:
            logger.error(f"Error counting events: {e}")
            return 0
    
    async def get_fight_rounds(self, fight_id: str) -> List[int]:
        """Get list of unique round numbers for a fight"""
        
        if not self.db:
            return []
        
        try:
            rounds = await self.db.events.distinct("round", {"boutId": fight_id})
            return sorted([r for r in rounds if r is not None])
        
        except Exception as e:
            logger.error(f"Error getting rounds: {e}")
            return []
    
    async def get_fight_fighters(self, fight_id: str) -> List[str]:
        """Get list of unique fighter IDs for a fight"""
        
        if not self.db:
            return []
        
        try:
            fighters = await self.db.events.distinct("fighterId", {"boutId": fight_id})
            return [f for f in fighters if f is not None]
        
        except Exception as e:
            logger.error(f"Error getting fighters: {e}")
            return []
    
    def classify_strike(self, event_type: str, metadata: Dict) -> Dict:
        """
        Classify a strike event
        
        Returns:
            {
                'is_strike': bool,
                'is_significant': bool,
                'target': 'head' | 'body' | 'leg' | None,
                'landed': bool
            }
        """
        
        event_lower = event_type.lower()
        
        # Check if it's a strike
        strike_keywords = ['strike', 'punch', 'kick', 'knee', 'elbow', 'hook', 'cross', 
                          'jab', 'uppercut', 'head kick', 'body kick', 'low kick']
        is_strike = any(keyword in event_lower for keyword in strike_keywords)
        
        if not is_strike:
            return {
                'is_strike': False,
                'is_significant': False,
                'target': None,
                'landed': False
            }
        
        # Check if significant
        is_significant = metadata.get('significant', True)  # Default to True
        
        # Check if landed (vs attempted/thrown)
        landed = 'landed' in event_lower or metadata.get('landed', True)
        
        # Determine target
        target = None
        if any(keyword in event_lower for keyword in ['head', 'face', 'chin']):
            target = 'head'
        elif any(keyword in event_lower for keyword in ['body', 'liver', 'ribs']):
            target = 'body'
        elif any(keyword in event_lower for keyword in ['leg', 'calf', 'thigh', 'low kick']):
            target = 'leg'
        
        return {
            'is_strike': True,
            'is_significant': is_significant,
            'target': target,
            'landed': landed
        }
    
    def is_knockdown(self, event_type: str) -> bool:
        """Check if event is a knockdown"""
        return 'kd' in event_type.lower() or 'knockdown' in event_type.lower()
    
    def is_rocked(self, event_type: str) -> bool:
        """Check if event is rocked/stunned"""
        return 'rocked' in event_type.lower() or 'stunned' in event_type.lower()
    
    def is_takedown(self, event_type: str, metadata: Dict) -> Dict:
        """
        Check if event is a takedown
        
        Returns:
            {
                'is_takedown': bool,
                'landed': bool,
                'stuffed': bool
            }
        """
        
        event_lower = event_type.lower()
        is_td = 'takedown' in event_lower or 'td' in event_lower
        
        if not is_td:
            return {'is_takedown': False, 'landed': False, 'stuffed': False}
        
        landed = 'landed' in event_lower or metadata.get('landed', False)
        stuffed = 'stuffed' in event_lower or 'defended' in event_lower
        
        return {
            'is_takedown': True,
            'landed': landed,
            'stuffed': stuffed
        }
    
    def is_submission_attempt(self, event_type: str) -> bool:
        """Check if event is a submission attempt"""
        event_lower = event_type.lower()
        return 'submission' in event_lower or 'sub attempt' in event_lower
