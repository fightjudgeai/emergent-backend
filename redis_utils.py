"""
Redis Utilities for Pub/Sub and Caching
"""

import os
import redis.asyncio as redis
import json
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    try:
        redis_client = await redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # Test connection
        await redis_client.ping()
        logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
        return redis_client
        
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        redis_client = None
        return None


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


class RedisPubSub:
    """Redis Pub/Sub manager"""
    
    def __init__(self, channel: str):
        self.channel = channel
        self.pubsub = None
    
    async def publish(self, message: dict):
        """Publish message to channel"""
        if redis_client is None:
            logger.debug(f"Redis not available, skipping publish to {self.channel}")
            return False
        
        try:
            message_json = json.dumps(message)
            await redis_client.publish(self.channel, message_json)
            logger.debug(f"Published to {self.channel}: {message}")
            return True
        except Exception as e:
            logger.error(f"Error publishing to {self.channel}: {e}")
            return False
    
    async def subscribe(self, callback: Callable):
        """Subscribe to channel and handle messages"""
        if redis_client is None:
            logger.warning(f"Redis not available, cannot subscribe to {self.channel}")
            return
        
        try:
            self.pubsub = redis_client.pubsub()
            await self.pubsub.subscribe(self.channel)
            logger.info(f"Subscribed to channel: {self.channel}")
            
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await callback(data)
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
        
        except Exception as e:
            logger.error(f"Error subscribing to {self.channel}: {e}")
    
    async def unsubscribe(self):
        """Unsubscribe from channel"""
        if self.pubsub:
            await self.pubsub.unsubscribe(self.channel)
            await self.pubsub.close()
            logger.info(f"Unsubscribed from {self.channel}")


# Calibration config pub/sub
calibration_pubsub = RedisPubSub('calibration:config:updates')
