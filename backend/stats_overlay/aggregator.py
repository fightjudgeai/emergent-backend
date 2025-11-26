"""
Stats Aggregator

Fast aggregation for live stats and comparison data.
"""

import logging
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class StatsAggregator:
    """High-performance stats aggregation for overlays"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
    
    async def get_live_stats(self, fight_id: str) -> Optional[Dict[str, Any]]:
        """
        Get live stats for current round + last 60 seconds
        
        Args:
            fight_id: Fight identifier
            
        Returns:
            Live stats with current round, recent events, KD/Rock indicators
        """
        try:
            # Get current fight state (determine current round)
            # For now, we'll get the latest round with events
            latest_event = await self.db.events.find_one(
                {'bout_id': fight_id},
                sort=[('timestamp', -1)]
            )
            
            if not latest_event:
                return None
            
            current_round = latest_event.get('round', 1)
            
            # Get events from last 60 seconds
            sixty_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
            
            recent_events = await self.db.events.find({
                'bout_id': fight_id,
                'timestamp': {'$gte': sixty_seconds_ago}
            }).to_list(length=1000)
            
            # Get current round stats
            round_stats = await self.db.round_stats.find({
                'fight_id': fight_id,
                'round': current_round
            }).to_list(length=2)
            
            # Aggregate by fighter
            fighter_stats = {}
            
            for stat_doc in round_stats:
                fighter_id = stat_doc.get('fighter_id')
                fighter_stats[fighter_id] = {
                    'fighter_id': fighter_id,
                    'fighter_name': stat_doc.get('fighter_name', fighter_id),
                    'significant_strikes': stat_doc.get('significant_strikes', 0),
                    'total_strikes': stat_doc.get('total_strikes', 0),
                    'takedowns': stat_doc.get('takedowns', 0),
                    'knockdowns': stat_doc.get('knockdowns', 0),
                    'control_time': stat_doc.get('control_time', 0)
                }
            
            # Aggregate last 60 seconds
            last_60s_totals = self._aggregate_recent_events(recent_events)
            
            # Detect KD and Rock indicators
            kd_rock_indicators = self._detect_kd_rock(recent_events)
            
            return {
                'fight_id': fight_id,
                'current_round': current_round,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_round_stats': list(fighter_stats.values()),
                'last_60s_totals': last_60s_totals,
                'indicators': kd_rock_indicators
            }
            
        except Exception as e:
            logger.error(f"Error getting live stats: {e}")
            return None
    
    def _aggregate_recent_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate events from last 60 seconds"""
        totals_by_fighter = {}
        
        for event in events:
            fighter_id = event.get('fighter_id')
            
            if fighter_id not in totals_by_fighter:
                totals_by_fighter[fighter_id] = {
                    'fighter_id': fighter_id,
                    'sig_strikes': 0,
                    'total_strikes': 0,
                    'takedowns': 0,
                    'knockdowns': 0,
                    'event_count': 0
                }
            
            event_type = event.get('event_type', '').lower()
            
            # Count strikes
            strike_types = ['hook', 'cross', 'jab', 'uppercut', 'elbow', 'head kick', 'body kick', 'low kick', 'knee']
            if any(st in event_type for st in strike_types):
                totals_by_fighter[fighter_id]['total_strikes'] += 1
                
                # Significant strikes (head and body strikes)
                if 'head' in event_type or 'body' in event_type or 'kick' in event_type:
                    totals_by_fighter[fighter_id]['sig_strikes'] += 1
            
            # Count takedowns
            if 'takedown' in event_type:
                totals_by_fighter[fighter_id]['takedowns'] += 1
            
            # Count knockdowns
            if 'knockdown' in event_type or event_type == 'kd':
                totals_by_fighter[fighter_id]['knockdowns'] += 1
            
            totals_by_fighter[fighter_id]['event_count'] += 1
        
        return list(totals_by_fighter.values())
    
    def _detect_kd_rock(self, recent_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect knockdown and rocked indicators"""
        kd_events = []
        rock_events = []
        
        for event in recent_events:
            event_type = event.get('event_type', '').lower()
            
            if 'knockdown' in event_type or event_type == 'kd':
                kd_events.append({
                    'fighter_id': event.get('fighter_id'),
                    'timestamp': event.get('timestamp'),
                    'round': event.get('round')
                })
            
            if 'rocked' in event_type:
                rock_events.append({
                    'fighter_id': event.get('fighter_id'),
                    'timestamp': event.get('timestamp'),
                    'round': event.get('round')
                })
        
        return {
            'knockdowns': kd_events,
            'rocked': rock_events,
            'has_kd': len(kd_events) > 0,
            'has_rock': len(rock_events) > 0
        }
    
    async def get_comparison_stats(self, fight_id: str) -> Optional[Dict[str, Any]]:
        """
        Get red vs blue comparison with stat deltas
        
        Args:
            fight_id: Fight identifier
            
        Returns:
            Comparison data with deltas
        """
        try:
            # Get fight stats for both fighters
            fight_stats = await self.db.fight_stats.find({
                'fight_id': fight_id
            }).to_list(length=2)
            
            if len(fight_stats) < 2:
                return None
            
            # Assume first is red corner, second is blue corner
            red = fight_stats[0]
            blue = fight_stats[1]
            
            # Calculate deltas
            deltas = {
                'significant_strikes': {
                    'red': red.get('total_significant_strikes', 0),
                    'blue': blue.get('total_significant_strikes', 0),
                    'delta': red.get('total_significant_strikes', 0) - blue.get('total_significant_strikes', 0),
                    'leader': 'red' if red.get('total_significant_strikes', 0) > blue.get('total_significant_strikes', 0) else 'blue'
                },
                'total_strikes': {
                    'red': red.get('total_strikes', 0),
                    'blue': blue.get('total_strikes', 0),
                    'delta': red.get('total_strikes', 0) - blue.get('total_strikes', 0),
                    'leader': 'red' if red.get('total_strikes', 0) > blue.get('total_strikes', 0) else 'blue'
                },
                'takedowns': {
                    'red': red.get('total_takedowns', 0),
                    'blue': blue.get('total_takedowns', 0),
                    'delta': red.get('total_takedowns', 0) - blue.get('total_takedowns', 0),
                    'leader': 'red' if red.get('total_takedowns', 0) > blue.get('total_takedowns', 0) else 'blue'
                },
                'control_time': {
                    'red': red.get('total_control_time', 0),
                    'blue': blue.get('total_control_time', 0),
                    'delta': red.get('total_control_time', 0) - blue.get('total_control_time', 0),
                    'leader': 'red' if red.get('total_control_time', 0) > blue.get('total_control_time', 0) else 'blue'
                },
                'knockdowns': {
                    'red': red.get('total_knockdowns', 0),
                    'blue': blue.get('total_knockdowns', 0),
                    'delta': red.get('total_knockdowns', 0) - blue.get('total_knockdowns', 0),
                    'leader': 'red' if red.get('total_knockdowns', 0) > blue.get('total_knockdowns', 0) else 'blue'
                }
            }
            
            return {
                'fight_id': fight_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'red_corner': {
                    'fighter_id': red.get('fighter_id'),
                    'fighter_name': red.get('fighter_name', 'Red Corner')
                },
                'blue_corner': {
                    'fighter_id': blue.get('fighter_id'),
                    'fighter_name': blue.get('fighter_name', 'Blue Corner')
                },
                'deltas': deltas
            }
            
        except Exception as e:
            logger.error(f"Error getting comparison stats: {e}")
            return None
