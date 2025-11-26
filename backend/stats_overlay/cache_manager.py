"""
Cache Manager

In-memory caching with 1-second TTL for sub-200ms latency.
"""

import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CacheManager:
    """In-memory cache with TTL management"""
    
    def __init__(self, ttl_seconds: float = 1.0):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/missing
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if time.time() - entry['timestamp'] > self.ttl:
            del self.cache[key]
            return None
        
        return entry['data']
    
    def set(self, key: str, value: Any) -> None:
        """
        Set cache value with current timestamp
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = {
            'data': value,
            'timestamp': time.time()
        }
    
    def invalidate(self, key: str) -> None:
        """Invalidate specific cache key"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = time.time()
        active_entries = sum(1 for entry in self.cache.values() if now - entry['timestamp'] <= self.ttl)
        
        return {
            'total_keys': len(self.cache),
            'active_entries': active_entries,
            'ttl_seconds': self.ttl
        }


# Global cache instance
overlay_cache = CacheManager(ttl_seconds=1.0)
