"""
Data Transformer

Transforms scraped Tapology data into our database schema format.
"""

import uuid
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms Tapology data to FJAIPOS database format"""
    
    @staticmethod
    def transform_fighter(tapology_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Tapology fighter data to our database schema
        
        Args:
            tapology_data: Raw scraped fighter data
            
        Returns:
            Fighter document for MongoDB
        """
        try:
            fighter_id = str(uuid.uuid4())
            
            fighter_doc = {
                'id': fighter_id,
                'name': tapology_data.get('name', 'Unknown Fighter'),
                'record': tapology_data.get('record', '0-0-0'),
                'tapology_id': tapology_data.get('tapology_id'),
                'tapology_url': tapology_data.get('tapology_url'),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'source': 'tapology'
            }
            
            # Optional fields
            if tapology_data.get('nickname'):
                fighter_doc['nickname'] = tapology_data['nickname']
            
            if tapology_data.get('weight_class'):
                fighter_doc['weight_class'] = tapology_data['weight_class']
            
            if tapology_data.get('age'):
                fighter_doc['age'] = tapology_data['age']
            
            if tapology_data.get('height'):
                fighter_doc['height'] = tapology_data['height']
            
            if tapology_data.get('reach'):
                fighter_doc['reach'] = tapology_data['reach']
            
            if tapology_data.get('stance'):
                fighter_doc['stance'] = tapology_data['stance']
            
            # Parse record into wins, losses, draws
            record_parsed = DataTransformer._parse_record(tapology_data.get('record', '0-0-0'))
            fighter_doc.update(record_parsed)
            
            return fighter_doc
            
        except Exception as e:
            logger.error(f"Error transforming fighter data: {e}")
            return None
    
    @staticmethod
    def _parse_record(record_str: str) -> Dict[str, int]:
        """Parse W-L-D record string"""
        try:
            parts = record_str.split('-')
            return {
                'wins': int(parts[0]) if len(parts) > 0 else 0,
                'losses': int(parts[1]) if len(parts) > 1 else 0,
                'draws': int(parts[2]) if len(parts) > 2 else 0
            }
        except Exception:
            return {'wins': 0, 'losses': 0, 'draws': 0}
    
    @staticmethod
    def transform_event(tapology_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Tapology event data to our database schema
        
        Args:
            tapology_data: Raw scraped event data
            
        Returns:
            Event document for aggregation
        """
        try:
            return {
                'event_name': tapology_data.get('event_name', 'Unknown Event'),
                'event_date': tapology_data.get('event_date'),
                'promotion': tapology_data.get('promotion', 'Unknown'),
                'location': tapology_data.get('location', 'Unknown'),
                'tapology_id': tapology_data.get('tapology_id'),
                'tapology_url': tapology_data.get('tapology_url'),
                'fight_count': len(tapology_data.get('fights', [])),
                'scraped_at': tapology_data.get('scraped_at'),
                'source': 'tapology'
            }
            
        except Exception as e:
            logger.error(f"Error transforming event data: {e}")
            return None
    
    @staticmethod
    def transform_fight_result(bout_data: Dict[str, Any], event_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Transform bout result into fight_stats format
        
        Args:
            bout_data: Raw scraped bout data
            event_name: Optional event name
            
        Returns:
            Fight stats document
        """
        try:
            fight_id = str(uuid.uuid4())
            result_data = bout_data.get('result', {})
            
            # Determine winner and loser
            fighter1 = bout_data.get('fighter1', {})
            fighter2 = bout_data.get('fighter2', {})
            
            winner_name = result_data.get('winner', '').strip()
            
            # Basic fight stats document
            fight_doc = {
                'fight_id': fight_id,
                'tapology_bout_id': bout_data.get('tapology_id'),
                'event_name': event_name or 'Unknown Event',
                'method': result_data.get('method', 'Decision'),
                'round': result_data.get('round', 3),
                'created_at': datetime.now(timezone.utc),
                'source': 'tapology',
                'fighters': [
                    {
                        'tapology_id': fighter1.get('tapology_id'),
                        'name': fighter1.get('name'),
                        'result': 'win' if winner_name.lower() in fighter1.get('name', '').lower() else 'loss'
                    },
                    {
                        'tapology_id': fighter2.get('tapology_id'),
                        'name': fighter2.get('name'),
                        'result': 'win' if winner_name.lower() in fighter2.get('name', '').lower() else 'loss'
                    }
                ]
            }
            
            return fight_doc
            
        except Exception as e:
            logger.error(f"Error transforming fight result: {e}")
            return None
    
    @staticmethod
    def create_mock_fight_stats(fight_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create basic fight_stats documents for both fighters
        (Since Tapology doesn't provide detailed stats, we create placeholder entries)
        
        Args:
            fight_doc: Transformed fight document
            
        Returns:
            List of fight_stats documents (one per fighter)
        """
        try:
            fight_stats = []
            
            for fighter in fight_doc.get('fighters', []):
                stat_doc = {
                    'fight_id': fight_doc['fight_id'],
                    'fighter_id': fighter.get('tapology_id') or str(uuid.uuid4()),
                    'fighter_name': fighter.get('name'),
                    'event_name': fight_doc.get('event_name'),
                    'opponent_name': next((f['name'] for f in fight_doc['fighters'] if f != fighter), 'Unknown'),
                    'result': fighter.get('result'),
                    
                    # Basic stats (set to 0 as Tapology doesn't provide detailed stats)
                    'total_significant_strikes': 0,
                    'total_strikes': 0,
                    'total_takedowns': 0,
                    'total_takedown_attempts': 0,
                    'total_control_time': 0,
                    'total_knockdowns': 0,
                    'total_submission_attempts': 0,
                    
                    'method': fight_doc.get('method'),
                    'round': fight_doc.get('round'),
                    
                    'created_at': datetime.now(timezone.utc),
                    'source': 'tapology',
                    'has_detailed_stats': False  # Flag to indicate this is from Tapology (no detailed stats)
                }
                
                fight_stats.append(stat_doc)
            
            return fight_stats
            
        except Exception as e:
            logger.error(f"Error creating mock fight stats: {e}")
            return []
    
    @staticmethod
    def batch_transform_fighters(fighters_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple fighters"""
        transformed = []
        for fighter_data in fighters_data:
            fighter_doc = DataTransformer.transform_fighter(fighter_data)
            if fighter_doc:
                transformed.append(fighter_doc)
        return transformed
    
    @staticmethod
    def batch_transform_events(events_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple events"""
        transformed = []
        for event_data in events_data:
            event_doc = DataTransformer.transform_event(event_data)
            if event_doc:
                transformed.append(event_doc)
        return transformed
