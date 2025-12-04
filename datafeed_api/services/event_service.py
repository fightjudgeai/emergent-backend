"""
Event Service
Handles granular fight event tracking with UFCstats parity
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standardized event types (UFCstats vocabulary)"""
    STR_ATT = "STR_ATT"          # Strike attempt
    STR_LAND = "STR_LAND"        # Strike landed
    KD = "KD"                    # Knockdown
    TD_ATT = "TD_ATT"            # Takedown attempt
    TD_LAND = "TD_LAND"          # Takedown landed
    CTRL_START = "CTRL_START"    # Control begins
    CTRL_END = "CTRL_END"        # Control ends
    SUB_ATT = "SUB_ATT"          # Submission attempt
    REVERSAL = "REVERSAL"        # Position reversal
    ROUND_START = "ROUND_START"  # Round begins
    ROUND_END = "ROUND_END"      # Round ends
    FIGHT_END = "FIGHT_END"      # Fight ends


class Corner(str, Enum):
    """Fighter corner"""
    RED = "RED"
    BLUE = "BLUE"
    NEUTRAL = "NEUTRAL"


class EventService:
    """Service for managing fight events"""
    
    def __init__(self, db_client):
        self.db = db_client
    
    def normalize_event_type(self, input_type: str) -> EventType:
        """
        Normalize event type with legacy alias mapping
        
        Args:
            input_type: Raw event type (may be alias)
        
        Returns:
            Normalized EventType
        """
        try:
            # Call SQL normalization function
            result = self.db.client.rpc(
                'normalize_event_type',
                {'p_input_type': input_type}
            ).execute()
            
            if result.data:
                normalized = result.data[0] if isinstance(result.data, list) else result.data
                return EventType(normalized)
            else:
                # Fallback to Python normalization
                return self._normalize_event_type_fallback(input_type)
        
        except Exception as e:
            logger.warning(f"SQL normalization failed, using fallback: {e}")
            return self._normalize_event_type_fallback(input_type)
    
    def _normalize_event_type_fallback(self, input_type: str) -> EventType:
        """Fallback Python normalization"""
        input_upper = input_type.upper().strip()
        
        # Legacy alias mapping
        alias_map = {
            'STRIKE': EventType.STR_LAND,
            'STRIKE_LAND': EventType.STR_LAND,
            'STRIKE_LANDED': EventType.STR_LAND,
            'STRIKE_ATT': EventType.STR_ATT,
            'STRIKE_ATTEMPT': EventType.STR_ATT,
            'KNOCKDOWN': EventType.KD,
            'TAKEDOWN': EventType.TD_LAND,
            'TAKEDOWN_LAND': EventType.TD_LAND,
            'TAKEDOWN_LANDED': EventType.TD_LAND,
            'TAKEDOWN_ATT': EventType.TD_ATT,
            'TAKEDOWN_ATTEMPT': EventType.TD_ATT,
            'CONTROL_START': EventType.CTRL_START,
            'CONTROL_END': EventType.CTRL_END,
            'SUBMISSION': EventType.SUB_ATT,
            'SUBMISSION_ATT': EventType.SUB_ATT,
            'SUBMISSION_ATTEMPT': EventType.SUB_ATT,
        }
        
        if input_upper in alias_map:
            return alias_map[input_upper]
        
        # Try direct match
        try:
            return EventType(input_upper)
        except ValueError:
            raise ValueError(f"Invalid event type: {input_type}. Must be one of: {[e.value for e in EventType]}")
    
    def insert_event(
        self,
        fight_id: UUID,
        round_num: int,
        second_in_round: int,
        event_type: str,
        corner: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Insert a fight event with normalization
        
        Args:
            fight_id: Fight UUID
            round_num: Round number (1-based)
            second_in_round: Timestamp within round (0-300)
            event_type: Event type (will be normalized)
            corner: RED, BLUE, or NEUTRAL
            metadata: Optional event-specific data
        
        Returns:
            Created event record
        """
        try:
            # Normalize event type
            normalized_type = self.normalize_event_type(event_type)
            
            # Validate corner
            corner_enum = Corner(corner.upper())
            
            # Get next sequence number
            seq_response = self.db.client.table('fight_events')\
                .select('seq')\
                .eq('fight_id', str(fight_id))\
                .order('seq', desc=True)\
                .limit(1)\
                .execute()
            
            next_seq = 1
            if seq_response.data:
                next_seq = seq_response.data[0]['seq'] + 1
            
            # Insert event
            response = self.db.client.table('fight_events')\
                .insert({
                    'fight_id': str(fight_id),
                    'round': round_num,
                    'second_in_round': second_in_round,
                    'event_type': normalized_type.value,
                    'corner': corner_enum.value,
                    'metadata': metadata or {},
                    'seq': next_seq
                })\
                .execute()
            
            if response.data:
                logger.info(f"Inserted event: {normalized_type.value} for {corner_enum.value} at R{round_num}:{second_in_round}s")
                return response.data[0]
            else:
                raise Exception("No data returned from insert")
        
        except Exception as e:
            logger.error(f"Error inserting event: {e}")
            raise
    
    def get_fight_events(
        self,
        fight_id: UUID,
        round_num: Optional[int] = None,
        event_type: Optional[EventType] = None
    ) -> List[Dict]:
        """Get events for a fight with optional filters"""
        query = self.db.client.table('fight_events')\
            .select('*')\
            .eq('fight_id', str(fight_id))\
            .order('seq')
        
        if round_num:
            query = query.eq('round', round_num)
        
        if event_type:
            query = query.eq('event_type', event_type.value)
        
        response = query.execute()
        return response.data if response.data else []
    
    def calculate_control_time(
        self,
        fight_id: UUID,
        round_num: int,
        corner: Corner
    ) -> int:
        """
        Calculate deterministic control time from events
        
        Uses SQL function to pair CTRL_START with next CTRL_END
        """
        try:
            result = self.db.client.rpc(
                'calculate_control_time_from_events',
                {
                    'p_fight_id': str(fight_id),
                    'p_round': round_num,
                    'p_corner': corner.value
                }
            ).execute()
            
            if result.data is not None:
                control_seconds = result.data[0] if isinstance(result.data, list) else result.data
                return int(control_seconds)
            else:
                return 0
        
        except Exception as e:
            logger.error(f"Error calculating control time: {e}")
            return 0
    
    def validate_control_overlap(
        self,
        fight_id: UUID,
        round_num: int
    ) -> Dict[str, Any]:
        """
        Validate no overlapping control periods
        
        Returns validation result with details
        """
        try:
            result = self.db.client.rpc(
                'validate_no_control_overlap',
                {
                    'p_fight_id': str(fight_id),
                    'p_round': round_num
                }
            ).execute()
            
            if result.data:
                return result.data[0]
            else:
                return {'has_overlap': False, 'overlap_details': {}}
        
        except Exception as e:
            logger.error(f"Error validating control overlap: {e}")
            return {'has_overlap': None, 'error': str(e)}
    
    def aggregate_stats_from_events(
        self,
        fight_id: UUID,
        round_num: int
    ) -> Dict[str, Any]:
        """
        Aggregate cumulative stats from events
        
        Returns round stats calculated from event stream
        """
        try:
            result = self.db.client.rpc(
                'aggregate_round_stats_from_events',
                {
                    'p_fight_id': str(fight_id),
                    'p_round': round_num
                }
            ).execute()
            
            if result.data:
                stats = result.data[0]
                return {
                    'red': {
                        'strikes': stats.get('red_strikes', 0),
                        'sig_strikes': stats.get('red_sig_strikes', 0),
                        'knockdowns': stats.get('red_knockdowns', 0),
                        'control_sec': stats.get('red_control_sec', 0),
                        'takedowns': stats.get('red_takedowns', 0),
                        'sub_attempts': stats.get('red_sub_attempts', 0)
                    },
                    'blue': {
                        'strikes': stats.get('blue_strikes', 0),
                        'sig_strikes': stats.get('blue_sig_strikes', 0),
                        'knockdowns': stats.get('blue_knockdowns', 0),
                        'control_sec': stats.get('blue_control_sec', 0),
                        'takedowns': stats.get('blue_takedowns', 0),
                        'sub_attempts': stats.get('blue_sub_attempts', 0)
                    }
                }
            else:
                return {'red': {}, 'blue': {}}
        
        except Exception as e:
            logger.error(f"Error aggregating stats from events: {e}")
            return {'red': {}, 'blue': {}, 'error': str(e)}
    
    def get_event_stream_summary(self, fight_id: UUID) -> Dict[str, Any]:
        """Get event stream summary for a fight"""
        events = self.get_fight_events(fight_id)
        
        # Count events by type
        event_counts = {}
        for event in events:
            event_type = event['event_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Get rounds covered
        rounds = set(e['round'] for e in events)
        
        return {
            'fight_id': str(fight_id),
            'total_events': len(events),
            'event_counts': event_counts,
            'rounds': sorted(list(rounds)),
            'first_event_seq': events[0]['seq'] if events else None,
            'last_event_seq': events[-1]['seq'] if events else None
        }
