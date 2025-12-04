"""
Supabase Database Client
Provides a wrapper around Supabase REST API for database operations
"""

import os
from typing import List, Dict, Optional, Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class SupabaseDB:
    """Supabase database client wrapper"""
    
    def __init__(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.client: Client = create_client(supabase_url, supabase_key)
    
    async def validate_api_key(self, api_key: str) -> tuple[bool, Optional[str], Optional[dict]]:
        """Validate API key and return scope"""
        try:
            response = self.client.table('api_clients')\
                .select('id, name, scope, active, rate_limit_per_min')\
                .eq('api_key', api_key)\
                .eq('active', True)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return False, None, None
            
            row = response.data[0]
            
            # Update last_used_at
            self.client.table('api_clients')\
                .update({'last_used_at': 'now()'})\
                .eq('id', row['id'])\
                .execute()
            
            client_info = {
                'id': str(row['id']),
                'name': row['name'],
                'scope': row['scope'],
                'rate_limit': row['rate_limit_per_min']
            }
            
            return True, row['scope'], client_info
        
        except Exception as e:
            print(f"Error validating API key: {e}")
            return False, None, None
    
    def get_event(self, event_code: str) -> Optional[Dict]:
        """Get event by code"""
        response = self.client.table('events')\
            .select('*')\
            .eq('code', event_code)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_event_fights(self, event_id: str) -> List[Dict]:
        """Get all fights for an event with fighter details"""
        # Get fights first
        fights_response = self.client.table('fights')\
            .select('*')\
            .eq('event_id', event_id)\
            .order('bout_order', desc=True)\
            .execute()
        
        if not fights_response.data:
            return []
        
        # Get fighter details for each fight
        result = []
        for fight in fights_response.data:
            red_fighter = self.client.table('fighters').select('*').eq('id', fight['red_fighter_id']).execute().data[0]
            blue_fighter = self.client.table('fighters').select('*').eq('id', fight['blue_fighter_id']).execute().data[0]
            
            fight['red_fighter'] = red_fighter
            fight['blue_fighter'] = blue_fighter
            result.append(fight)
        
        return result
    
    def get_fight_by_code(self, fight_code: str) -> Optional[Dict]:
        """Get fight by code with event and fighter details"""
        response = self.client.table('fights')\
            .select('*')\
            .eq('code', fight_code)\
            .execute()
        
        if not response.data:
            return None
        
        fight = response.data[0]
        
        # Get related data
        event = self.client.table('events').select('*').eq('id', fight['event_id']).execute().data[0]
        red_fighter = self.client.table('fighters').select('*').eq('id', fight['red_fighter_id']).execute().data[0]
        blue_fighter = self.client.table('fighters').select('*').eq('id', fight['blue_fighter_id']).execute().data[0]
        
        fight['event'] = event
        fight['red_fighter'] = red_fighter
        fight['blue_fighter'] = blue_fighter
        
        return fight
    
    def get_fight_by_code_or_id(self, fight_identifier: str) -> Optional[Dict]:
        """Get fight by code or ID"""
        # Try as UUID first
        try:
            from uuid import UUID
            UUID(fight_identifier)
            # It's a valid UUID, query by ID
            response = self.client.table('fights')\
                .select('*')\
                .eq('id', fight_identifier)\
                .execute()
        except (ValueError, AttributeError):
            # Not a UUID, try as code
            response = self.client.table('fights')\
                .select('*')\
                .eq('code', fight_identifier)\
                .execute()
        
        if not response.data:
            return None
        
        return response.data[0]
    
    def get_latest_round_state(self, fight_id: str) -> Optional[Dict]:
        """Get latest round state for a fight"""
        response = self.client.table('round_state')\
            .select('*')\
            .eq('fight_id', fight_id)\
            .order('seq', desc=True)\
            .limit(1)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_fight_result(self, fight_id: str) -> Optional[Dict]:
        """Get fight result"""
        response = self.client.table('fight_results')\
            .select('*')\
            .eq('fight_id', fight_id)\
            .execute()
        
        return response.data[0] if response.data else None
    
    def get_round_states(self, fight_id: str, round_num: Optional[int] = None) -> List[Dict]:
        """Get round states for a fight"""
        query = self.client.table('round_state')\
            .select('*')\
            .eq('fight_id', fight_id)
        
        if round_num is not None:
            query = query.eq('round', round_num)
        
        response = query.order('seq').execute()
        
        return response.data if response.data else []
    
    def get_api_clients(self) -> List[Dict]:
        """Get all API clients"""
        response = self.client.table('api_clients')\
            .select('id, name, scope, active, rate_limit_per_min, created_at, last_used_at')\
            .order('created_at', desc=True)\
            .execute()
        
        return response.data if response.data else []
    
    def health_check(self) -> bool:
        """Check if database is accessible"""
        try:
            response = self.client.table('events').select('id').limit(1).execute()
            return True
        except Exception:
            return False
