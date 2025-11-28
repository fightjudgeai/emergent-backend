"""
Organization Filters

Utility functions for filtering stats by organization_id.
"""

from typing import Dict, Optional, Any


def add_org_filter(query: Dict[str, Any], organization_id: Optional[str]) -> Dict[str, Any]:
    """
    Add organization_id filter to MongoDB query
    
    Args:
        query: Existing MongoDB query
        organization_id: Organization ID to filter by (optional)
        
    Returns:
        Updated query with org filter
    """
    if organization_id:
        query['organization_id'] = organization_id
    
    return query


def get_org_query(organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get base query with org filter
    
    Args:
        organization_id: Organization ID
        
    Returns:
        MongoDB query dict
    """
    if organization_id:
        return {'organization_id': organization_id}
    return {}
