"""
Redis client and stream publishing utilities
"""
import json
import base64
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for stream publishing"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """Establish connection to Redis"""
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=False  # Keep bytes for binary data
            )
            # Test connection
            await self.client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Disconnected from Redis")
    
    async def is_connected(self) -> bool:
        """Check if Redis connection is active"""
        if not self.client or not self._connected:
            return False
        try:
            await self.client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    async def publish_frame(
        self,
        camera_id: str,
        frame_data: bytes,
        frame_number: int,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish a frame to Redis Stream
        
        Args:
            camera_id: Unique camera identifier
            frame_data: JPEG-encoded frame bytes
            frame_number: Sequential frame number
            timestamp: Frame capture timestamp
            metadata: Additional frame metadata
            
        Returns:
            bool: True if published successfully
        """
        try:
            if not await self.is_connected():
                logger.error("Redis not connected, cannot publish frame")
                return False
            
            stream_key = f"{settings.redis_stream_prefix}:{camera_id}"
            
            # Prepare frame data
            message = {
                b"camera_id": camera_id.encode(),
                b"frame_number": str(frame_number).encode(),
                b"timestamp": timestamp.isoformat().encode(),
                b"frame_data": frame_data,
                b"frame_size_bytes": str(len(frame_data)).encode()
            }
            
            # Add metadata if provided
            if metadata:
                message[b"metadata"] = json.dumps(metadata).encode()
            
            # Add to stream
            message_id = await self.client.xadd(stream_key, message)
            
            logger.debug(
                f"Published frame {frame_number} to {stream_key} "
                f"(size: {len(frame_data)} bytes, id: {message_id})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish frame to Redis: {e}")
            return False
    
    async def trim_stream(self, camera_id: str, max_length: int = 1000):
        """
        Trim stream to prevent unbounded growth
        
        Args:
            camera_id: Camera identifier
            max_length: Maximum number of messages to keep
        """
        try:
            stream_key = f"{settings.redis_stream_prefix}:{camera_id}"
            await self.client.xtrim(stream_key, maxlen=max_length, approximate=True)
        except Exception as e:
            logger.warning(f"Failed to trim stream {camera_id}: {e}")


# Global Redis client instance
redis_client = RedisClient()
