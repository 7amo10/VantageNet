"""Redis consumer for emotion detection results."""
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, List, Optional
from datetime import datetime

import redis.asyncio as aioredis
from redis.exceptions import ResponseError

from .config import settings
from .models import EmotionData

logger = logging.getLogger(__name__)


class RedisConsumer:
    """Async Redis Stream consumer for emotion results."""
    
    def __init__(self):
        """Initialize Redis consumer with connection pool."""
        self.redis_client: Optional[aioredis.Redis] = None
        self.consumer_group = settings.redis_consumer_group
        self.consumer_name = settings.redis_consumer_name
        self.input_pattern = settings.redis_input_pattern
        self.block_ms = settings.redis_block_ms
        self.batch_size = settings.redis_batch_size
        self._streams: List[str] = []
        
    async def connect(self) -> None:
        """Establish Redis connection and set up consumer groups."""
        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info(
                f"Connected to Redis at {settings.redis_host}:{settings.redis_port}"
            )
            
            # Discover and set up streams
            await self._discover_streams()
            await self._create_consumer_groups()
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def _discover_streams(self) -> None:
        """Discover all streams matching the input pattern."""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        try:
            # Get all keys matching pattern
            pattern = self.input_pattern
            keys = await self.redis_client.keys(pattern)
            
            # Filter for streams only
            self._streams = []
            for key in keys:
                key_type = await self.redis_client.type(key)
                if key_type == "stream":
                    self._streams.append(key)
            
            logger.info(f"Discovered {len(self._streams)} emotion result streams: {self._streams}")
            
        except Exception as e:
            logger.error(f"Error discovering streams: {e}")
            raise
    
    async def rediscover_streams(self) -> None:
        """Public method to force stream rediscovery (useful for testing)."""
        await self._discover_streams()
        await self._create_consumer_groups()
        logger.info(f"Rediscovered {len(self._streams)} streams")
    
    async def _create_consumer_groups(self) -> None:
        """Create consumer groups for all discovered streams."""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        for stream in self._streams:
            try:
                # Try to create consumer group from beginning of stream
                await self.redis_client.xgroup_create(
                    name=stream,
                    groupname=self.consumer_group,
                    id="0",
                    mkstream=True
                )
                logger.info(f"Created consumer group '{self.consumer_group}' for stream '{stream}'")
                
            except ResponseError as e:
                if "BUSYGROUP" in str(e):
                    # Consumer group already exists
                    logger.debug(f"Consumer group '{self.consumer_group}' already exists for '{stream}'")
                else:
                    logger.error(f"Error creating consumer group for '{stream}': {e}")
                    raise
    
    async def read_emotions(self) -> AsyncGenerator[EmotionData, None]:
        """
        Read emotion results from Redis streams.
        
        Yields:
            EmotionData: Parsed emotion detection result
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        # Periodically rediscover streams (every 60 seconds)
        last_discovery = datetime.now()
        discovery_interval = 60
        
        while True:
            try:
                # Rediscover streams if needed
                if (datetime.now() - last_discovery).total_seconds() > discovery_interval:
                    await self._discover_streams()
                    await self._create_consumer_groups()
                    last_discovery = datetime.now()
                
                if not self._streams:
                    logger.warning("No emotion result streams found, waiting...")
                    await asyncio.sleep(5)
                    continue
                
                # Read from all streams
                streams_dict = {stream: ">" for stream in self._streams}
                
                try:
                    messages = await self.redis_client.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        streams=streams_dict,
                        count=self.batch_size,
                        block=self.block_ms
                    )
                except ResponseError as e:
                    if "NOGROUP" in str(e):
                        # Consumer group was deleted (stream recreated), recreate it
                        logger.warning("Consumer group missing, recreating...")
                        await self._create_consumer_groups()
                        continue
                    raise
                
                if not messages:
                    continue
                
                # Process messages
                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            # Parse emotion data
                            emotion_data = self._parse_emotion_data(message_data)
                            
                            # Acknowledge message
                            await self.redis_client.xack(
                                stream_name,
                                self.consumer_group,
                                message_id
                            )
                            
                            yield emotion_data
                            
                        except Exception as e:
                            logger.error(
                                f"Error processing message {message_id} from {stream_name}: {e}"
                            )
                            # Don't acknowledge failed messages
                            continue
            
            except asyncio.CancelledError:
                logger.info("Emotion consumer cancelled")
                break
            except Exception as e:
                logger.error(f"Error reading from Redis: {e}")
                await asyncio.sleep(5)
    
    def _parse_emotion_data(self, message_data: Dict[str, str]) -> EmotionData:
        """
        Parse raw Redis message into EmotionData model.
        
        Args:
            message_data: Raw message data from Redis stream
            
        Returns:
            EmotionData: Parsed emotion data
        """
        try:
            # Parse JSON fields if they exist
            faces = json.loads(message_data.get("faces", "[]"))
            emotions = json.loads(message_data.get("emotions", "[]"))
            emotion_counts = json.loads(message_data.get("emotion_counts", "{}"))
            
            # Parse timestamp - prefer processed_at (when emotion was detected)
            # over timestamp (original frame time from video)
            timestamp_str = message_data.get("processed_at") or message_data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()
            
            return EmotionData(
                camera_id=message_data.get("camera_id", "unknown"),
                timestamp=timestamp,
                frame_number=int(message_data.get("frame_number", 0)),
                faces=faces,
                emotions=emotions,
                emotion_counts=emotion_counts,
                dominant_emotion=message_data.get("dominant_emotion")
            )
            
        except Exception as e:
            logger.error(f"Error parsing emotion data: {e}")
            raise
    
    async def get_status(self) -> Dict[str, any]:
        """
        Get consumer status information.
        
        Returns:
            Dict with connection status and stream info
        """
        if not self.redis_client:
            return {
                "connected": False,
                "input_streams": 0,
                "consumer_group_exists": False
            }
        
        try:
            await self.redis_client.ping()
            return {
                "connected": True,
                "input_streams": len(self._streams),
                "consumer_group_exists": len(self._streams) > 0
            }
        except Exception as e:
            return {
                "connected": False,
                "input_streams": 0,
                "consumer_group_exists": False,
                "error": str(e)
            }
