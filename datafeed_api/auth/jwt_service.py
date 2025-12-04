"""
JWT Token Service for WebSocket Authentication
Generates and validates JWT tokens for WebSocket connections
"""

import logging
import hashlib
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = "your-secret-key-change-in-production"  # TODO: Move to env
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60  # Tokens expire after 1 hour


class JWTService:
    """Service for JWT token generation and validation"""
    
    def __init__(self, db_client, secret_key: Optional[str] = None):
        """
        Initialize JWT service
        
        Args:
            db_client: Database client
            secret_key: JWT secret key (defaults to config)
        """
        self.db = db_client
        self.secret_key = secret_key or JWT_SECRET
        self.algorithm = JWT_ALGORITHM
    
    def generate_token(
        self,
        client_id: str,
        tier: str,
        expiration_minutes: int = JWT_EXPIRATION_MINUTES
    ) -> Tuple[str, datetime]:
        """
        Generate JWT token for WebSocket authentication
        
        Args:
            client_id: Client UUID
            tier: Client tier
            expiration_minutes: Token expiration time
        
        Returns:
            Tuple of (token, expires_at)
        """
        try:
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            # Create payload
            payload = {
                'client_id': client_id,
                'tier': tier,
                'exp': expires_at.timestamp(),
                'iat': datetime.utcnow().timestamp(),
                'type': 'websocket'
            }
            
            # Generate token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Store token hash in database
            token_hash = self._hash_token(token)
            
            self.db.client.table('jwt_tokens').insert({
                'client_id': client_id,
                'token_hash': token_hash,
                'expires_at': expires_at.isoformat(),
                'revoked': False
            }).execute()
            
            logger.info(f"Generated JWT token for client {client_id}, expires at {expires_at}")
            
            return token, expires_at
        
        except Exception as e:
            logger.error(f"Error generating JWT token: {e}")
            raise
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            Tuple of (is_valid, payload)
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check token hash exists and not revoked
            token_hash = self._hash_token(token)
            
            response = self.db.client.table('jwt_tokens')\
                .select('*')\
                .eq('token_hash', token_hash)\
                .eq('revoked', False)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                logger.warning("Token not found or revoked")
                return False, None
            
            token_record = response.data[0]
            
            # Check expiration
            expires_at = datetime.fromisoformat(token_record['expires_at'].replace('Z', '+00:00'))
            if datetime.utcnow() > expires_at:
                logger.warning("Token expired")
                return False, None
            
            return True, payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired (JWT validation)")
            return False, None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, None
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a JWT token
        
        Args:
            token: JWT token to revoke
        
        Returns:
            True if revoked successfully
        """
        try:
            token_hash = self._hash_token(token)
            
            response = self.db.client.table('jwt_tokens')\
                .update({'revoked': True})\
                .eq('token_hash', token_hash)\
                .execute()
            
            if response.data:
                logger.info(f"Token revoked: {token_hash[:10]}...")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False
    
    def clean_expired_tokens(self) -> int:
        """
        Clean up expired tokens from database
        
        Returns:
            Number of tokens deleted
        """
        try:
            # Call database function
            response = self.db.client.rpc('clean_expired_tokens').execute()
            
            deleted_count = response.data if response.data else 0
            
            logger.info(f"Cleaned {deleted_count} expired tokens")
            
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning expired tokens: {e}")
            return 0
    
    def _hash_token(self, token: str) -> str:
        """
        Generate SHA256 hash of token for storage
        
        Args:
            token: JWT token
        
        Returns:
            Hex digest of token hash
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    def generate_websocket_url(
        self,
        client_id: str,
        tier: str,
        event_slug: str,
        base_url: str = "wss://fightjudge.ai"
    ) -> Tuple[str, str, datetime]:
        """
        Generate complete WebSocket URL with token
        
        Args:
            client_id: Client UUID
            tier: Client tier
            event_slug: Event slug
            base_url: Base WebSocket URL
        
        Returns:
            Tuple of (websocket_url, token, expires_at)
        """
        token, expires_at = self.generate_token(client_id, tier)
        
        ws_url = f"{base_url}/live/{event_slug}?token={token}"
        
        return ws_url, token, expires_at
