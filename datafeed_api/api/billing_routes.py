"""
Billing API Routes
Endpoints for usage metering and billing reports
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime

from auth.dependencies import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

# Global database client
db_client = None


def set_db_client(client):
    """Set database client"""
    global db_client
    db_client = client


@router.get("/billing/usage/current")
async def get_current_month_usage(
    client_info: dict = Depends(require_api_key)
):
    """
    Get current month usage for authenticated client
    
    Returns:
        Current billing period usage statistics
        
    Example Response:
    ```json
    {
        "client_id": "uuid",
        "client_name": "Partner ABC",
        "tier": "fantasy.basic",
        "period": "2024-01",
        "usage": {
            "api_calls": 15234,
            "websocket_minutes": 450,
            "data_mb_served": 1250.5
        },
        "limits": {
            "api_calls_per_month": 500000,
            "websocket_hours_per_month": 100
        }
    }
    ```
    """
    try:
        client_id = client_info['id']
        
        # Get current period
        current_period = datetime.utcnow().strftime('%Y-%m')
        
        # Get usage from billing table
        response = db_client.client.table('billing_usage')\
            .select('*')\
            .eq('client_id', client_id)\
            .eq('period', current_period)\
            .execute()
        
        if not response.data or len(response.data) == 0:
            # No usage yet this month
            usage_data = {
                'api_calls': 0,
                'websocket_minutes': 0,
                'data_bytes_served': 0
            }
        else:
            usage_data = response.data[0]
        
        # Calculate MB and GB
        data_mb = round(usage_data['data_bytes_served'] / 1024 / 1024, 2)
        data_gb = round(usage_data['data_bytes_served'] / 1024 / 1024 / 1024, 3)
        
        return {
            "client_id": client_id,
            "client_name": client_info['name'],
            "tier": client_info['tier'],
            "period": current_period,
            "usage": {
                "api_calls": usage_data['api_calls'],
                "websocket_minutes": usage_data['websocket_minutes'],
                "websocket_hours": round(usage_data['websocket_minutes'] / 60, 2),
                "data_bytes_served": usage_data['data_bytes_served'],
                "data_mb_served": data_mb,
                "data_gb_served": data_gb
            },
            "updated_at": usage_data.get('updated_at'),
            "note": "Usage is updated in real-time"
        }
    
    except Exception as e:
        logger.error(f"Error fetching usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching usage data"
        )


@router.get("/billing/usage/history")
async def get_usage_history(
    client_info: dict = Depends(require_api_key),
    months: int = Query(6, ge=1, le=12)
):
    """
    Get historical usage data
    
    Query params:
    - months: Number of months to retrieve (1-12, default 6)
    
    Returns:
        Historical usage by month
    """
    try:
        client_id = client_info['id']
        
        # Get historical usage
        response = db_client.client.table('billing_usage')\
            .select('*')\
            .eq('client_id', client_id)\
            .order('period', desc=True)\
            .limit(months)\
            .execute()
        
        usage_history = []
        
        for record in (response.data or []):
            data_gb = round(record['data_bytes_served'] / 1024 / 1024 / 1024, 3)
            
            usage_history.append({
                'period': record['period'],
                'api_calls': record['api_calls'],
                'websocket_hours': round(record['websocket_minutes'] / 60, 2),
                'data_gb_served': data_gb,
                'updated_at': record['updated_at']
            })
        
        return {
            "client_id": client_id,
            "tier": client_info['tier'],
            "history": usage_history,
            "total_months": len(usage_history)
        }
    
    except Exception as e:
        logger.error(f"Error fetching usage history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching usage history"
        )


@router.get("/admin/billing/summary")
async def get_billing_summary(
    period: Optional[str] = None
):
    """
    Get billing summary for all clients
    
    **Admin endpoint**
    
    Query params:
    - period: Billing period (YYYY-MM), defaults to current month
    
    Returns:
        Aggregated billing data for all clients
    """
    try:
        if not period:
            period = datetime.utcnow().strftime('%Y-%m')
        
        # Use the current_month_billing view
        response = db_client.client.table('current_month_billing')\
            .select('*')\
            .execute()
        
        summary = response.data if response.data else []
        
        # Calculate totals
        total_api_calls = sum(s.get('api_calls', 0) or 0 for s in summary)
        total_websocket_minutes = sum(s.get('websocket_minutes', 0) or 0 for s in summary)
        total_data_gb = sum(s.get('data_gb_served', 0) or 0 for s in summary)
        
        return {
            "period": period,
            "clients": summary,
            "total_clients": len(summary),
            "totals": {
                "api_calls": total_api_calls,
                "websocket_hours": round(total_websocket_minutes / 60, 2),
                "data_gb_served": round(total_data_gb, 2)
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching billing summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching billing summary"
        )


@router.get("/admin/billing/client/{client_id}")
async def get_client_billing_details(client_id: str):
    """
    Get detailed billing for specific client
    
    **Admin endpoint**
    
    Returns:
        Detailed billing information and usage trends
    """
    try:
        # Get all billing records for client
        response = db_client.client.table('billing_usage')\
            .select('*')\
            .eq('client_id', client_id)\
            .order('period', desc=True)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No billing data found for client {client_id}"
            )
        
        records = response.data
        
        # Calculate totals
        total_api_calls = sum(r['api_calls'] for r in records)
        total_websocket_minutes = sum(r['websocket_minutes'] for r in records)
        total_data_bytes = sum(r['data_bytes_served'] for r in records)
        
        return {
            "client_id": client_id,
            "billing_records": records,
            "total_periods": len(records),
            "lifetime_totals": {
                "api_calls": total_api_calls,
                "websocket_hours": round(total_websocket_minutes / 60, 2),
                "data_gb_served": round(total_data_bytes / 1024 / 1024 / 1024, 2)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client billing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching client billing data"
        )


@router.get("/admin/websocket/sessions")
async def get_websocket_sessions(
    active_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get WebSocket session history
    
    **Admin endpoint**
    
    Query params:
    - active_only: Show only active sessions (default false)
    - limit: Maximum sessions to return
    
    Returns:
        WebSocket session history with duration and billing info
    """
    try:
        if active_only:
            # Use active_websocket_sessions view
            response = db_client.client.table('active_websocket_sessions')\
                .select('*')\
                .limit(limit)\
                .execute()
        else:
            # Get all sessions
            response = db_client.client.table('websocket_sessions')\
                .select('*')\
                .order('connected_at', desc=True)\
                .limit(limit)\
                .execute()
        
        sessions = response.data if response.data else []
        
        return {
            "sessions": sessions,
            "total": len(sessions),
            "active_only": active_only
        }
    
    except Exception as e:
        logger.error(f"Error fetching WebSocket sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching session data"
        )
