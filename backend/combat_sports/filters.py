"""
Combat Sport Filters

Utility functions for filtering by sport type and organization.
"""

from typing import Dict, Optional, Any


def add_sport_filter(query: Dict[str, Any], sport_type: Optional[str], organization_id: Optional[str]) -> Dict[str, Any]:
    """
    Add sport and organization filters to MongoDB query
    
    Args:
        query: Existing MongoDB query
        sport_type: Sport type (mma, boxing, etc.)
        organization_id: Organization ID
        
    Returns:
        Updated query with filters
    """
    if sport_type:
        query['sport_type'] = sport_type
    
    if organization_id:
        query['organization_id'] = organization_id
    
    return query


def get_sport_query(sport_type: Optional[str] = None, organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get base query with sport and org filters
    
    Args:
        sport_type: Sport type
        organization_id: Organization ID
        
    Returns:
        MongoDB query dict
    """
    query = {}
    
    if sport_type:
        query['sport_type'] = sport_type
    
    if organization_id:
        query['organization_id'] = organization_id
    
    return query


def validate_sport_type(sport_type: str) -> bool:
    """
    Validate sport type
    
    Args:
        sport_type: Sport type to validate
        
    Returns:
        True if valid
    """
    valid_sports = ['mma', 'boxing', 'dirty_boxing', 'bkfc', 'karate_combat', 'other']
    return sport_type in valid_sports


def validate_organization(sport_type: str, organization_id: str) -> bool:
    """
    Validate organization belongs to sport type
    
    Args:
        sport_type: Sport type
        organization_id: Organization ID
        
    Returns:
        True if valid combination
    """
    from combat_sports import SPORT_TYPES
    
    if sport_type not in SPORT_TYPES:
        return False
    
    valid_orgs = SPORT_TYPES[sport_type].get('organizations', [])
    return organization_id in valid_orgs or organization_id == 'other'
