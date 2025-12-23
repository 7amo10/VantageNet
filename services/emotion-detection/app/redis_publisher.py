"""Redis publisher for emotion detection results."""
import asyncio
import json
import logging
from typing import Optional
import redis.asyncio as redis
from .config import settings
from .models import EmotionResult

logger = logging.getLogger(__name__)


class RedisPublisher:
    """Async Redis publisher for emotion detection results."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.connected = False
        
    async def connect(self) -> bool:
        """
        Connect to Redis.
        
        Returns:
            True if connection successful
        """
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True  # We're publishing JSON strings
            )
            
            # Test connection
            await self.client.ping()
            self.connected = True
            logger.info(f"✓ Publisher connected to Redis at {settings.redis_host}:{settings.redis_port}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.aclose()
            self.connected = False
            logger.info("Publisher disconnected from Redis")
    
    async def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        if not self.client or not self.connected:
            return False
        try:
            await self.client.ping()
            return True
        except:
            self.connected = False
            return False
    
    async def publish_result(self, result: EmotionResult) -> bool:
        """
        Publish emotion detection result to Redis Stream.
        
        Stream name format: emotion:results:{camera_id}
        
        Args:
            result: EmotionResult object to publish
            
        Returns:
            True if published successfully
        """
        if not await self.is_connected():
            logger.error("Cannot publish: Not connected to Redis")
            return False
        
        try:
            stream_name = f"emotion:results:{result.camera_id}"
            
            # Convert result to dict and then to JSON
            result_dict = result.model_dump(mode='json')
            
            # Prepare data for Redis Stream
            # Convert nested objects to JSON strings
            data = {
                "camera_id": result.camera_id,
                "frame_number": str(result.frame_number),
                "timestamp": result.timestamp,
                "processed_at": result.processed_at,
                "faces_detected": str(result.faces_detected),
                "processing_time_ms": str(result.processing_time_ms),
                "faces": json.dumps(result_dict["faces"]),
                "emotions": json.dumps(result_dict["emotions"]),
            }
            
            # Add frame dimensions if present
            if result.frame_width is not None:
                data["frame_width"] = str(result.frame_width)
            if result.frame_height is not None:
                data["frame_height"] = str(result.frame_height)
            
            # Add metadata if present
            if result.metadata:
                data["metadata"] = json.dumps(result.metadata)
            
            # Publish to stream
            message_id = await self.client.xadd(stream_name, data)
            
            logger.debug(
                f"📤 Published result | Stream: {stream_name} | "
                f"Frame: {result.frame_number} | Faces: {result.faces_detected} | "
                f"ID: {message_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish result: {e}", exc_info=True)
            return False
    
    async def publish_metrics(self, metrics: dict) -> bool:
        """
        Publish service metrics to Redis.
        
        Publishes to keys:
        - service:detection:fps
        - service:detection:avg_latency_ms
        - service:detection:errors_total
        
        Args:
            metrics: Dictionary with fps, avg_latency_ms, errors_total
            
        Returns:
            True if published successfully
        """
        if not await self.is_connected():
            return False
        
        try:
            pipe = self.client.pipeline()
            
            if "fps" in metrics:
                pipe.set("service:detection:fps", str(metrics["fps"]))
            
            if "avg_latency_ms" in metrics:
                pipe.set("service:detection:avg_latency_ms", str(metrics["avg_latency_ms"]))
            
            if "errors_total" in metrics:
                pipe.set("service:detection:errors_total", str(metrics["errors_total"]))
            
            await pipe.execute()
            
            logger.debug(f"📊 Published metrics: {metrics}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish metrics: {e}")
            return False
    
    async def get_stream_length(self, camera_id: str) -> int:
        """
        Get the length of a results stream.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Number of messages in stream, or 0 if error
        """
        if not await self.is_connected():
            return 0
        
        try:
            stream_name = f"emotion:results:{camera_id}"
            length = await self.client.xlen(stream_name)
            return length
        except:
            return 0


# Global publisher instance
redis_publisher = RedisPublisher()
