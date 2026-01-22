import redis.asyncio as redis
import json
import asyncio
import logging
from typing import Callable, Coroutine
from shared.config import settings

logger = logging.getLogger(__name__)


class RedisSubscriber:
    """
    Subscribe to Redis Pub/Sub channels and forward messages to WebSocket clients
    Enables horizontal scaling of WebSocket servers
    """
    
    def __init__(self, broadcast_callback: Callable[[str, dict], Coroutine]):
        """
        Args:
            broadcast_callback: Async function to call when message received
                                Function signature: async def(channel: str, message: dict)
        """
        self.redis_client: redis.Redis = None
        self.pubsub = None
        self.broadcast_callback = broadcast_callback
        self.is_running = False
        self.subscription_task = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            logger.info("Connected to Redis for Pub/Sub")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        self.is_running = False
        
        if self.subscription_task:
            self.subscription_task.cancel()
            try:
                await self.subscription_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Disconnected from Redis")
    
    async def subscribe_to_channel(self, channel: str):
        """Subscribe to a Redis channel"""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis")
        
        await self.pubsub.subscribe(channel)
        logger.info(f"Subscribed to Redis channel: {channel}")
    
    async def unsubscribe_from_channel(self, channel: str):
        """Unsubscribe from a Redis channel"""
        if not self.pubsub:
            return
        
        await self.pubsub.unsubscribe(channel)
        logger.info(f"Unsubscribed from Redis channel: {channel}")
    
    async def subscribe_to_pattern(self, pattern: str):
        """Subscribe to channels matching a pattern"""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis")
        
        await self.pubsub.psubscribe(pattern)
        logger.info(f"Subscribed to Redis pattern: {pattern}")
    
    async def listen(self):
        """
        Listen for messages from subscribed channels
        This should run as a background task
        """
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis")
        
        self.is_running = True
        logger.info("Started listening to Redis Pub/Sub")
        
        try:
            async for message in self.pubsub.listen():
                if not self.is_running:
                    break
                
                # Filter out subscription confirmation messages
                if message["type"] not in ["message", "pmessage"]:
                    continue
                
                try:
                    channel = message.get("channel", "")
                    data_str = message.get("data", "{}")
                    
                    # Parse JSON data
                    data = json.loads(data_str) if isinstance(data_str, str) else data_str
                    
                    # Call the broadcast callback
                    await self.broadcast_callback(channel, data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message from {channel}: {e}")
                except Exception as e:
                    logger.error(f"Error processing message from {channel}: {e}")
        
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Error in Redis listener: {e}")
        finally:
            self.is_running = False
            logger.info("Stopped listening to Redis Pub/Sub")
    
    def start_listening(self):
        """Start listening in background task"""
        if self.subscription_task is None or self.subscription_task.done():
            self.subscription_task = asyncio.create_task(self.listen())
        return self.subscription_task


class RedisPublisher:
    """
    Publish messages to Redis channels
    Used by market data service to broadcast updates
    """
    
    def __init__(self):
        self.redis_client: redis.Redis = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis publisher connected")
        except Exception as e:
            logger.error(f"Failed to connect Redis publisher: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis publisher disconnected")
    
    async def publish(self, channel: str, message: dict):
        """
        Publish message to a channel
        
        Args:
            channel: Redis channel name (e.g., "market_data:quotes:RELIANCE")
            message: Dictionary to publish (will be JSON serialized)
        """
        if not self.redis_client:
            raise RuntimeError("Redis publisher not connected")
        
        try:
            message_str = json.dumps(message)
            await self.redis_client.publish(channel, message_str)
            logger.debug(f"Published to {channel}: {message_str[:100]}")
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
