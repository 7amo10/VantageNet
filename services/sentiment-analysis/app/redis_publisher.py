"""Redis publisher for sentiment results."""
import asyncio
import json
import logging
from typing import Optional
from datetime import datetime

import redis.asyncio as aioredis

from .config import settings
from .models import SentimentResult

logger = logging.getLogger(__name__)


class RedisPublisher:
    """Async Redis Stream publisher for sentiment results."""
    
    def __init__(self):
        """Initialize Redis publisher with connection pool."""
        self.redis_client: Optional[aioredis.Redis] = None
        self.output_stream = settings.redis_output_stream
        self._published_count = 0
        
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info(
                f"Redis publisher connected to {settings.redis_host}:{settings.redis_port}"
            )
            
        except Exception as e:
            logger.error(f"Failed to connect Redis publisher: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis publisher disconnected")
    
    async def publish_sentiment(self, sentiment: SentimentResult) -> bool:
        """
        Publish sentiment result to Redis stream.
        
        Args:
            sentiment: Sentiment result to publish
            
        Returns:
            bool: True if published successfully
        """
        if not self.redis_client:
            raise RuntimeError("Redis publisher not connected")
        
        try:
            # Convert sentiment to dict for Redis
            sentiment_dict = {
                "timestamp": sentiment.timestamp.isoformat(),
                "window_start": sentiment.window_start.isoformat(),
                "window_end": sentiment.window_end.isoformat(),
                "camera_ids": json.dumps(sentiment.camera_ids),
                "total_faces": str(sentiment.total_faces),
                "emotion_distribution": json.dumps(sentiment.emotion_distribution),
                "dominant_emotion": sentiment.dominant_emotion,
                "sentiment_score": str(sentiment.sentiment_score),
                "confidence": str(sentiment.confidence)
            }
            
            # Add to stream
            message_id = await self.redis_client.xadd(
                name=self.output_stream,
                fields=sentiment_dict,
                maxlen=10000  # Keep last 10k messages
            )
            
            self._published_count += 1
            
            logger.debug(
                f"Published sentiment to '{self.output_stream}': "
                f"id={message_id}, score={sentiment.sentiment_score:.2f}, "
                f"dominant={sentiment.dominant_emotion}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing sentiment: {e}")
            return False
    
    async def get_published_count(self) -> int:
        """
        Get count of published messages.
        
        Returns:
            int: Number of messages published
        """
        return self._published_count
    
    async def get_stream_length(self) -> Optional[int]:
        """
        Get current length of output stream.
        
        Returns:
            Optional[int]: Stream length or None if error
        """
        if not self.redis_client:
            return None
        
        try:
            length = await self.redis_client.xlen(self.output_stream)
            return length
        except Exception as e:
            logger.error(f"Error getting stream length: {e}")
            return None
