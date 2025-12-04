"""
Fantasy Scoring Service
Handles fantasy points calculation and management
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from database.supabase_client import SupabaseDB

logger = logging.getLogger(__name__)


class FantasyScoringService:
    """Service for fantasy scoring operations"""
    
    def __init__(self, db: SupabaseDB):
        self.db = db
    
    def get_all_profiles(self) -> List[Dict]:
        """Get all fantasy scoring profiles"""
        response = self.db.client.table('fantasy_scoring_profiles')\
            .select('*')\
            .order('id')\
            .execute()
        
        return response.data if response.data else []
    
    def get_profile(self, profile_id: str) -> Optional[Dict]:
        """Get a specific fantasy scoring profile"""
        response = self.db.client.table('fantasy_scoring_profiles')\
            .select('*')\
            .eq('id', profile_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def calculate_fantasy_points(
        self,
        fight_id: UUID,
        fighter_id: UUID,
        profile_id: str
    ) -> Dict[str, Any]:
        """
        Calculate fantasy points for a fighter in a fight
        Uses the SQL function calculate_fantasy_points
        """
        try:
            # Call the database function
            result = self.db.client.rpc(
                'calculate_fantasy_points',
                {
                    'p_fight_id': str(fight_id),
                    'p_fighter_id': str(fighter_id),
                    'p_profile_id': profile_id
                }
            ).execute()
            
            if not result.data or len(result.data) == 0:
                raise Exception("No data returned from calculation")
            
            data = result.data[0]
            fantasy_points = float(data.get('fantasy_points', 0))
            breakdown = data.get('breakdown', {})
            
            return {
                'fantasy_points': fantasy_points,
                'breakdown': breakdown
            }
        
        except Exception as e:
            logger.error(f"Error calculating fantasy points: {e}")
            raise
    
    def save_fantasy_stats(
        self,
        fight_id: UUID,
        fighter_id: UUID,
        profile_id: str,
        fantasy_points: float,
        breakdown: Dict[str, Any]
    ) -> Dict:
        """Save or update fantasy fight stats"""
        try:
            # Upsert fantasy stats
            response = self.db.client.table('fantasy_fight_stats')\
                .upsert({
                    'fight_id': str(fight_id),
                    'fighter_id': str(fighter_id),
                    'profile_id': profile_id,
                    'fantasy_points': fantasy_points,
                    'breakdown': breakdown
                }, on_conflict='fight_id,fighter_id,profile_id')\
                .execute()
            
            return response.data[0] if response.data else None
        
        except Exception as e:
            logger.error(f"Error saving fantasy stats: {e}")
            raise
    
    def calculate_and_save(
        self,
        fight_id: UUID,
        fighter_id: UUID,
        profile_id: str
    ) -> Dict[str, Any]:
        """Calculate fantasy points and save to database"""
        # Calculate points
        result = self.calculate_fantasy_points(fight_id, fighter_id, profile_id)
        
        # Save to database
        saved = self.save_fantasy_stats(
            fight_id,
            fighter_id,
            profile_id,
            result['fantasy_points'],
            result['breakdown']
        )
        
        return {
            'success': True,
            'fight_id': fight_id,
            'fighter_id': fighter_id,
            'profile_id': profile_id,
            'fantasy_points': result['fantasy_points'],
            'breakdown': result['breakdown']
        }
    
    def calculate_for_fight(
        self,
        fight_id: UUID,
        profile_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate fantasy points for all fighters in a fight
        across specified profiles
        """
        if profile_ids is None:
            profile_ids = ['fantasy.basic', 'fantasy.advanced', 'sportsbook.pro']
        
        # Get fight details to find both fighters
        fight = self.db.get_fight_by_code_or_id(str(fight_id))
        
        if not fight:
            raise Exception(f"Fight {fight_id} not found")
        
        red_fighter_id = fight['red_fighter_id']
        blue_fighter_id = fight['blue_fighter_id']
        
        results = []
        
        for profile_id in profile_ids:
            # Calculate for red corner
            try:
                result_red = self.calculate_and_save(
                    fight_id,
                    UUID(red_fighter_id),
                    profile_id
                )
                results.append(result_red)
            except Exception as e:
                logger.error(f"Error calculating for red fighter: {e}")
                results.append({
                    'success': False,
                    'fight_id': fight_id,
                    'fighter_id': red_fighter_id,
                    'profile_id': profile_id,
                    'error': str(e)
                })
            
            # Calculate for blue corner
            try:
                result_blue = self.calculate_and_save(
                    fight_id,
                    UUID(blue_fighter_id),
                    profile_id
                )
                results.append(result_blue)
            except Exception as e:
                logger.error(f"Error calculating for blue fighter: {e}")
                results.append({
                    'success': False,
                    'fight_id': fight_id,
                    'fighter_id': blue_fighter_id,
                    'profile_id': profile_id,
                    'error': str(e)
                })
        
        return results
    
    def get_fantasy_stats(
        self,
        fight_id: Optional[UUID] = None,
        fighter_id: Optional[UUID] = None,
        profile_id: Optional[str] = None
    ) -> List[Dict]:
        """Get fantasy stats with optional filters"""
        query = self.db.client.table('fantasy_fight_stats').select('*')
        
        if fight_id:
            query = query.eq('fight_id', str(fight_id))
        
        if fighter_id:
            query = query.eq('fighter_id', str(fighter_id))
        
        if profile_id:
            query = query.eq('profile_id', profile_id)
        
        response = query.order('fantasy_points', desc=True).execute()
        
        return response.data if response.data else []
    
    def get_fantasy_leaderboard(
        self,
        profile_id: str,
        event_code: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get fantasy leaderboard for a profile"""
        # Build query
        if event_code:
            # Get event ID
            event = self.db.get_event(event_code)
            if not event:
                raise Exception(f"Event {event_code} not found")
            
            # Get fights for event
            fights = self.db.get_event_fights(event['id'])
            fight_ids = [f['id'] for f in fights]
            
            # Get fantasy stats for those fights
            stats = []
            for fight_id in fight_ids:
                fight_stats = self.get_fantasy_stats(
                    fight_id=UUID(fight_id),
                    profile_id=profile_id
                )
                stats.extend(fight_stats)
        else:
            # Get all stats for profile
            stats = self.get_fantasy_stats(profile_id=profile_id)
        
        # Aggregate by fighter
        fighter_totals = {}
        for stat in stats:
            fighter_id = stat['fighter_id']
            
            if fighter_id not in fighter_totals:
                fighter_totals[fighter_id] = {
                    'fighter_id': fighter_id,
                    'total_points': 0,
                    'fights_count': 0
                }
            
            fighter_totals[fighter_id]['total_points'] += float(stat['fantasy_points'])
            fighter_totals[fighter_id]['fights_count'] += 1
        
        # Convert to list and sort
        leaderboard = []
        for fighter_id, data in fighter_totals.items():
            # Get fighter details
            fighter = self.db.client.table('fighters')\
                .select('*')\
                .eq('id', fighter_id)\
                .execute()\
                .data[0]
            
            leaderboard.append({
                'fighter_id': fighter_id,
                'fighter_name': f"{fighter['first_name']} {fighter['last_name']}",
                'fighter_nickname': fighter.get('nickname'),
                'fantasy_points': data['total_points'],
                'fights_count': data['fights_count'],
                'avg_points_per_fight': data['total_points'] / data['fights_count'] if data['fights_count'] > 0 else 0
            })
        
        # Sort by total points
        leaderboard.sort(key=lambda x: x['fantasy_points'], reverse=True)
        
        # Get profile name
        profile = self.get_profile(profile_id)
        profile_name = profile['name'] if profile else profile_id
        
        return {
            'profile_id': profile_id,
            'profile_name': profile_name,
            'event_code': event_code,
            'leaderboard': leaderboard[:limit],
            'total_fighters': len(leaderboard)
        }
