"""
Supabase database client using REST API (no SDK required)
Uses httpx for direct REST API calls to Supabase PostgreSQL
"""
import os
import json
import logging
from typing import Optional, Dict, List, Any
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

# Global async client
http_client: Optional[httpx.AsyncClient] = None

# Lazy-loaded credentials
_supabase_url: Optional[str] = None
_supabase_anon_key: Optional[str] = None
_rest_api_url: Optional[str] = None

def _load_credentials():
    """Load Supabase credentials from environment"""
    global _supabase_url, _supabase_anon_key, _rest_api_url
    
    if _supabase_url is not None:
        return  # Already loaded
    
    _supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    _supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    
    if _supabase_url:
        _rest_api_url = f"{_supabase_url}/rest/v1"

def get_headers(use_service_role: bool = False) -> Dict[str, str]:
    """Get headers for API requests"""
    _load_credentials()
    
    api_key = _supabase_anon_key
    if use_service_role:
        api_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "apikey": api_key,
        "Prefer": "return=representation"
    }

async def init_supabase():
    """Initialize Supabase REST client"""
    global http_client
    
    _load_credentials()
    
    if not _supabase_url or not _supabase_anon_key:
        logger.warning("Supabase credentials not configured. Supabase features disabled.")
        return False
    
    try:
        http_client = httpx.AsyncClient(timeout=30.0)
        
        # Test connection with a simple query
        headers = get_headers()
        response = await http_client.get(
            f"{_rest_api_url}/fights?select=id&limit=1",
            headers=headers
        )
        
        if response.status_code in [200, 206]:
            logger.info("✓ Supabase REST API client initialized successfully")
            return True
        else:
            logger.warning(f"Supabase health check returned status {response.status_code}: {response.text}")
            return False
                
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        return False

# ==============================================================================
# FIGHTS TABLE OPERATIONS
# ==============================================================================

async def create_fight(
    description: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict]:
    """Create a new fight record in Supabase"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        logger.warning("Supabase not initialized")
        return None
    
    try:
        fight_data = {
            "description": description,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        headers = get_headers()
        response = await http_client.post(
            f"{_rest_api_url}/fights",
            headers=headers,
            json=fight_data
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            logger.info(f"✓ Fight created: {data}")
            return data[0] if isinstance(data, list) else data
        else:
            logger.error(f"Error creating fight: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error creating fight: {e}")
        return None

async def get_fight(fight_id: str) -> Optional[Dict]:
    """Get a fight by ID"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return None
    
    try:
        headers = get_headers()
        response = await http_client.get(
            f"{_rest_api_url}/fights?id=eq.{fight_id}",
            headers=headers
        )
        
        if response.status_code in [200, 206]:
            data = response.json()
            return data[0] if data else None
        return None
    except Exception as e:
        logger.error(f"Error getting fight: {e}")
        return None

async def list_fights(user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """List fights, optionally filtered by user"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return []
    
    try:
        headers = get_headers()
        
        # Build query
        query = f"select=*&order=created_at.desc&limit={limit}"
        if user_id:
            query += f"&user_id=eq.{user_id}"
        
        response = await http_client.get(
            f"{_rest_api_url}/fights?{query}",
            headers=headers
        )
        
        if response.status_code in [200, 206]:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error listing fights: {e}")
        return []

async def update_fight(fight_id: str, updates: Dict) -> Optional[Dict]:
    """Update a fight record"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return None
    
    try:
        headers = get_headers()
        response = await http_client.patch(
            f"{_rest_api_url}/fights?id=eq.{fight_id}",
            headers=headers,
            json=updates
        )
        
        if response.status_code in [200, 204]:
            data = response.json() if response.text else []
            return data[0] if isinstance(data, list) and data else None
        else:
            logger.error(f"Error updating fight: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error updating fight: {e}")
        return None

# ==============================================================================
# JUDGMENTS TABLE OPERATIONS
# ==============================================================================

async def create_judgment(
    fight_id: str,
    winner: Optional[str],
    scores: Dict[str, Any],
    reasoning: str,
    ai_model: Optional[str] = None,
    user_id: Optional[str] = None
) -> Optional[Dict]:
    """Create a new judgment record"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        logger.warning("Supabase not initialized")
        return None
    
    try:
        judgment_data = {
            "fight_id": fight_id,
            "winner": winner,
            "scores": scores,
            "reasoning": reasoning,
            "ai_model": ai_model,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        headers = get_headers()
        response = await http_client.post(
            f"{_rest_api_url}/judgments",
            headers=headers,
            json=judgment_data
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            logger.info(f"✓ Judgment created: {data}")
            return data[0] if isinstance(data, list) else data
        else:
            logger.error(f"Error creating judgment: {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error creating judgment: {e}")
        return None

async def get_judgment(judgment_id: str) -> Optional[Dict]:
    """Get a judgment by ID"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return None
    
    try:
        headers = get_headers()
        response = await http_client.get(
            f"{_rest_api_url}/judgments?id=eq.{judgment_id}",
            headers=headers
        )
        
        if response.status_code in [200, 206]:
            data = response.json()
            return data[0] if data else None
        return None
    except Exception as e:
        logger.error(f"Error getting judgment: {e}")
        return None

async def get_fight_judgments(fight_id: str) -> List[Dict]:
    """Get all judgments for a fight"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return []
    
    try:
        headers = get_headers()
        response = await http_client.get(
            f"{_rest_api_url}/judgments?fight_id=eq.{fight_id}&order=created_at.desc",
            headers=headers
        )
        
        if response.status_code in [200, 206]:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error getting fight judgments: {e}")
        return []

async def list_judgments(user_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """List judgments, optionally filtered by user"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return []
    
    try:
        headers = get_headers()
        
        # Build query
        query = f"select=*&order=created_at.desc&limit={limit}"
        if user_id:
            query += f"&user_id=eq.{user_id}"
        
        response = await http_client.get(
            f"{_rest_api_url}/judgments?{query}",
            headers=headers
        )
        
        if response.status_code in [200, 206]:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error listing judgments: {e}")
        return []

async def update_judgment(judgment_id: str, updates: Dict) -> Optional[Dict]:
    """Update a judgment record"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return None
    
    try:
        headers = get_headers()
        response = await http_client.patch(
            f"{_rest_api_url}/judgments?id=eq.{judgment_id}",
            headers=headers,
            json=updates
        )
        
        if response.status_code in [200, 204]:
            data = response.json() if response.text else []
            return data[0] if isinstance(data, list) and data else None
        else:
            logger.error(f"Error updating judgment: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error updating judgment: {e}")
        return None

# ==============================================================================
# HEALTH CHECK
# ==============================================================================

async def check_supabase_health() -> bool:
    """Check if Supabase is accessible"""
    _load_credentials()
    
    if not http_client or not _rest_api_url:
        return False
    
    try:
        headers = get_headers()
        response = await http_client.get(
            f"{_rest_api_url}/fights?select=id&limit=1",
            headers=headers
        )
        
        if response.status_code in [200, 206]:
            logger.info("✓ Supabase health check passed")
            return True
        return False
    except Exception as e:
        logger.warning(f"Supabase health check failed: {e}")
        return False
