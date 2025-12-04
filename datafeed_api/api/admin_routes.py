"""
Admin API Routes
Endpoints for managing API keys and viewing usage analytics
"""

import logging
import secrets
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# Global database client
db_client = None


def set_db_client(client):
    """Set database client"""
    global db_client
    db_client = client


class CreateAPIKeyRequest(BaseModel):
    """Request to create new API key"""
    name: str
    tier: str
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 3600
    rate_limit_per_day: int = 50000
    notes: Optional[str] = None


class UpdateAPIKeyRequest(BaseModel):
    """Request to update API key"""
    name: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    notes: Optional[str] = None


def generate_secure_api_key(prefix: str = "FJAI") -> str:
    """
    Generate cryptographically secure API key
    
    Args:
        prefix: Key prefix (default: FJAI)
    
    Returns:
        Secure API key string
    """
    # Generate 32 bytes (256 bits) of random data
    random_bytes = secrets.token_bytes(32)
    
    # Encode as URL-safe base64
    random_part = secrets.token_urlsafe(32)
    
    # Format: PREFIX_RANDOMPART
    api_key = f"{prefix}_{random_part}"
    
    return api_key


@router.post("/admin/api-keys")
async def create_api_key(request: CreateAPIKeyRequest):
    """
    Create a new API key
    
    **Admin only** - This endpoint should be protected with additional auth
    
    Request Body:
    {
        "name": "Partner Name",
        "tier": "fantasy.basic",
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 3600,
        "rate_limit_per_day": 50000,
        "notes": "Optional notes"
    }
    
    Returns:
        Created API key details including the generated key
    """
    try:
        # Validate tier
        valid_tiers = ['public', 'dev', 'fantasy.basic', 'fantasy.advanced', 'sportsbook.pro', 'promotion.enterprise']
        if request.tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
            )
        
        # Generate secure API key
        api_key = generate_secure_api_key()
        
        # Insert into database
        response = db_client.client.table('api_clients').insert({
            'name': request.name,
            'tier': request.tier,
            'api_key': api_key,
            'status': 'ACTIVE',
            'rate_limit_per_minute': request.rate_limit_per_minute,
            'rate_limit_per_hour': request.rate_limit_per_hour,
            'rate_limit_per_day': request.rate_limit_per_day,
            'notes': request.notes
        }).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )
        
        created = response.data[0]
        
        return {
            "id": created['id'],
            "name": created['name'],
            "tier": created['tier'],
            "api_key": api_key,  # Only shown once!
            "status": created['status'],
            "rate_limit_per_minute": created['rate_limit_per_minute'],
            "rate_limit_per_hour": created['rate_limit_per_hour'],
            "rate_limit_per_day": created['rate_limit_per_day'],
            "created_at": created['created_at'],
            "warning": "Save this API key securely. It will not be shown again."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating API key: {str(e)}"
        )


@router.get("/admin/api-keys")
async def list_api_keys(
    tier: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50
):
    """
    List all API keys (without revealing actual keys)
    
    Query params:
    - tier: Filter by tier
    - status_filter: Filter by status (ACTIVE, SUSPENDED, REVOKED)
    - limit: Maximum results (default 50)
    
    Returns:
        List of API key metadata
    """
    try:
        query = db_client.client.table('api_clients')\
            .select('id, name, tier, status, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day, created_at, last_used_at, notes')
        
        if tier:
            query = query.eq('tier', tier)
        
        if status_filter:
            query = query.eq('status', status_filter)
        
        response = query.order('created_at', desc=True).limit(limit).execute()
        
        return {
            "api_keys": response.data if response.data else [],
            "total": len(response.data) if response.data else 0
        }
    
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing API keys"
        )


@router.get("/admin/api-keys/{key_id}")
async def get_api_key_details(key_id: str):
    """
    Get detailed information about a specific API key
    
    **Note**: Does not reveal the actual API key
    
    Returns:
        API key metadata and usage statistics
    """
    try:
        # Get client info
        client_response = db_client.client.table('api_clients')\
            .select('*')\
            .eq('id', key_id)\
            .execute()
        
        if not client_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found: {key_id}"
            )
        
        client = client_response.data[0]
        
        # Get usage statistics
        usage_response = db_client.client.table('api_usage_logs')\
            .select('*', count='exact')\
            .eq('client_id', key_id)\
            .execute()
        
        total_requests = usage_response.count if usage_response.count else 0
        
        # Mask the API key (show only first 10 chars)
        masked_key = client['api_key'][:10] + '...' if client.get('api_key') else 'N/A'
        
        return {
            "id": client['id'],
            "name": client['name'],
            "tier": client['tier'],
            "api_key": masked_key,
            "status": client['status'],
            "rate_limit_per_minute": client['rate_limit_per_minute'],
            "rate_limit_per_hour": client.get('rate_limit_per_hour'),
            "rate_limit_per_day": client.get('rate_limit_per_day'),
            "created_at": client['created_at'],
            "last_used_at": client.get('last_used_at'),
            "notes": client.get('notes'),
            "usage_statistics": {
                "total_requests": total_requests
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching API key details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching API key details"
        )


@router.patch("/admin/api-keys/{key_id}")
async def update_api_key(key_id: str, request: UpdateAPIKeyRequest):
    """
    Update API key settings
    
    Can update:
    - Name
    - Tier
    - Status (ACTIVE, SUSPENDED, REVOKED)
    - Rate limits
    - Notes
    
    **Cannot change**: The actual API key itself
    """
    try:
        # Build update dict
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.tier is not None:
            updates['tier'] = request.tier
        if request.status is not None:
            if request.status not in ['ACTIVE', 'SUSPENDED', 'REVOKED']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status. Must be ACTIVE, SUSPENDED, or REVOKED"
                )
            updates['status'] = request.status
        if request.rate_limit_per_minute is not None:
            updates['rate_limit_per_minute'] = request.rate_limit_per_minute
        if request.rate_limit_per_hour is not None:
            updates['rate_limit_per_hour'] = request.rate_limit_per_hour
        if request.rate_limit_per_day is not None:
            updates['rate_limit_per_day'] = request.rate_limit_per_day
        if request.notes is not None:
            updates['notes'] = request.notes
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        # Update database
        response = db_client.client.table('api_clients')\
            .update(updates)\
            .eq('id', key_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found: {key_id}"
            )
        
        return {
            "message": "API key updated successfully",
            "updated": response.data[0]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating API key: {str(e)}"
        )


@router.delete("/admin/api-keys/{key_id}")
async def revoke_api_key(key_id: str):
    """
    Revoke an API key (soft delete - sets status to REVOKED)
    
    Revoked keys cannot be reactivated and should be deleted after grace period
    """
    try:
        response = db_client.client.table('api_clients')\
            .update({
                'status': 'REVOKED',
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', key_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found: {key_id}"
            )
        
        return {
            "message": "API key revoked successfully",
            "id": key_id,
            "status": "REVOKED"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error revoking API key"
        )


@router.get("/admin/usage/summary")
async def get_usage_summary():
    """
    Get API usage summary across all clients
    
    Returns:
        Aggregated usage statistics
    """
    try:
        # Use the api_usage_summary view
        response = db_client.client.table('api_usage_summary')\
            .select('*')\
            .execute()
        
        return {
            "summary": response.data if response.data else [],
            "total_clients": len(response.data) if response.data else 0
        }
    
    except Exception as e:
        logger.error(f"Error fetching usage summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching usage summary"
        )


@router.get("/admin/usage/{client_id}")
async def get_client_usage(
    client_id: str,
    limit: int = 100
):
    """
    Get detailed usage logs for a specific client
    
    Query params:
    - limit: Maximum logs to return (default 100)
    
    Returns:
        Recent API usage logs for the client
    """
    try:
        response = db_client.client.table('api_usage_logs')\
            .select('*')\
            .eq('client_id', client_id)\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "client_id": client_id,
            "logs": response.data if response.data else [],
            "total": len(response.data) if response.data else 0
        }
    
    except Exception as e:
        logger.error(f"Error fetching client usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching client usage"
        )


@router.post("/admin/create-client")
async def admin_create_client(request: CreateAPIKeyRequest, admin_user: str = "admin"):
    """
    Admin endpoint to create new API client
    
    **RESTRICTED TO INTERNAL ADMIN ONLY**
    
    Body:
    {
        "name": "Partner Name",
        "tier": "fantasy.basic",
        "rate_limit_per_minute": 180
    }
    """
    try:
        # Generate API key
        api_key = generate_secure_api_key()
        
        # Insert client
        response = db_client.client.table('api_clients').insert({
            'name': request.name,
            'tier': request.tier,
            'api_key': api_key,
            'status': 'ACTIVE',
            'rate_limit_per_minute': request.rate_limit_per_minute,
            'rate_limit_per_hour': request.rate_limit_per_hour,
            'rate_limit_per_day': request.rate_limit_per_day,
            'notes': request.notes
        }).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create client"
            )
        
        created = response.data[0]
        
        # Log admin action
        db_client.client.table('admin_actions').insert({
            'admin_user': admin_user,
            'action_type': 'create_client',
            'target_client_id': created['id'],
            'new_value': {'name': request.name, 'tier': request.tier},
            'reason': 'New client created',
            'timestamp': datetime.utcnow().isoformat()
        }).execute()
        
        return {
            "id": created['id'],
            "name": created['name'],
            "tier": created['tier'],
            "api_key": api_key,
            "status": created['status'],
            "warning": "Save this API key securely. It will not be shown again."
        }
    
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/admin/suspend-client/{client_id}")
async def admin_suspend_client(
    client_id: str,
    reason: str,
    admin_user: str = "admin"
):
    """
    Admin endpoint to suspend client (emergency kill-switch per client)
    
    **RESTRICTED TO INTERNAL ADMIN ONLY**
    
    Suspended clients are immediately blocked from all access
    """
    try:
        # Get current client info
        old_client = db_client.client.table('api_clients')\
            .select('*')\
            .eq('id', client_id)\
            .execute()
        
        if not old_client.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client not found: {client_id}"
            )
        
        # Suspend client
        response = db_client.client.table('api_clients')\
            .update({
                'status': 'SUSPENDED',
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', client_id)\
            .execute()
        
        # Log admin action
        db_client.client.table('admin_actions').insert({
            'admin_user': admin_user,
            'action_type': 'suspend_client',
            'target_client_id': client_id,
            'old_value': {'status': old_client.data[0]['status']},
            'new_value': {'status': 'SUSPENDED'},
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }).execute()
        
        logger.warning(f"Client suspended: {client_id} by {admin_user}: {reason}")
        
        return {
            "message": "Client suspended successfully",
            "client_id": client_id,
            "status": "SUSPENDED",
            "reason": reason
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suspending client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/admin/change-tier/{client_id}")
async def admin_change_tier(
    client_id: str,
    new_tier: str,
    reason: str,
    admin_user: str = "admin"
):
    """
    Admin endpoint to change client tier
    
    **RESTRICTED TO INTERNAL ADMIN ONLY**
    
    Changes take effect immediately
    """
    try:
        # Validate tier
        valid_tiers = ['public', 'dev', 'fantasy.basic', 'fantasy.advanced', 'sportsbook.pro', 'promotion.enterprise']
        if new_tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
            )
        
        # Get current client info
        old_client = db_client.client.table('api_clients')\
            .select('*')\
            .eq('id', client_id)\
            .execute()
        
        if not old_client.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client not found: {client_id}"
            )
        
        old_tier = old_client.data[0]['tier']
        
        # Update tier
        response = db_client.client.table('api_clients')\
            .update({
                'tier': new_tier,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', client_id)\
            .execute()
        
        # Log admin action
        db_client.client.table('admin_actions').insert({
            'admin_user': admin_user,
            'action_type': 'change_tier',
            'target_client_id': client_id,
            'old_value': {'tier': old_tier},
            'new_value': {'tier': new_tier},
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }).execute()
        
        logger.info(f"Client tier changed: {client_id} from {old_tier} to {new_tier} by {admin_user}")
        
        return {
            "message": "Tier changed successfully",
            "client_id": client_id,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "reason": reason
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing tier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/admin/emergency-stop")
async def admin_emergency_stop(
    component: str,
    reason: str,
    admin_user: str = "admin"
):
    """
    Admin endpoint for emergency kill-switch
    
    **RESTRICTED TO INTERNAL ADMIN ONLY**
    
    Components: api, websocket, fantasy, markets, settlement
    
    Stops component immediately system-wide
    """
    try:
        # Update system status
        db_client.client.table('system_status')\
            .update({
                'status': 'emergency_stop',
                'reason': reason,
                'updated_by': admin_user,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('component', component)\
            .execute()
        
        # Log admin action
        db_client.client.table('admin_actions').insert({
            'admin_user': admin_user,
            'action_type': 'emergency_stop',
            'new_value': {'component': component, 'reason': reason},
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }).execute()
        
        logger.critical(f"EMERGENCY STOP: {component} stopped by {admin_user}: {reason}")
        
        return {
            "message": f"Emergency stop activated for {component}",
            "component": component,
            "status": "emergency_stop",
            "reason": reason,
            "admin": admin_user
        }
    
    except Exception as e:
        logger.error(f"Error executing emergency stop: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/admin/reactivate")
async def admin_reactivate_component(
    component: str,
    admin_user: str = "admin"
):
    """
    Admin endpoint to reactivate stopped component
    
    **RESTRICTED TO INTERNAL ADMIN ONLY**
    """
    try:
        db_client.client.table('system_status')\
            .update({
                'status': 'active',
                'reason': None,
                'updated_by': admin_user,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('component', component)\
            .execute()
        
        # Log admin action
        db_client.client.table('admin_actions').insert({
            'admin_user': admin_user,
            'action_type': 'reactivate_component',
            'new_value': {'component': component},
            'reason': 'Component reactivated',
            'timestamp': datetime.utcnow().isoformat()
        }).execute()
        
        logger.info(f"Component reactivated: {component} by {admin_user}")
        
        return {
            "message": f"Component {component} reactivated",
            "component": component,
            "status": "active"
        }
    
    except Exception as e:
        logger.error(f"Error reactivating component: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
