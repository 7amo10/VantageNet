"""Redis Stream consumer for processing video frames."""
import asyncio
import json
import logging
from typing import Dict, List, Optional, AsyncGenerator
import redis.asyncio as redis
from .config import settings
from .models import FrameData

logger = logging.getLogger(__name__)


class RedisConsumer:
    """Async Redis Stream consumer for frame processing."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.running = False
        self.streams: List[str] = []
        
    async def connect(self) -> bool:
        """
        Connect to Redis and initialize consumer group.
        
        Returns:
            True if connection successful
        """
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=False  # We need bytes for frame data
            )
            
            # Test connection
            await self.client.ping()
            logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
            
            # Discover all emotion:frames:* streams
            await self._discover_streams()
            
            # Create consumer group for each stream
            await self._create_consumer_groups()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.aclose()
            logger.info("Disconnected from Redis")
    
    async def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        if not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except:
            return False
    
    async def _discover_streams(self):
        """Discover all streams matching the pattern."""
        try:
            # Get all keys matching pattern
            pattern = settings.redis_stream_pattern.replace('*', '*')
            cursor = 0
            self.streams = []
            
            while True:
                cursor, keys = await self.client.scan(
                    cursor,
                    match=pattern.encode(),
                    count=100
                )
                
                for key in keys:
                    # Check if it's actually a stream
                    key_type = await self.client.type(key)
                    if key_type == b'stream':
                        self.streams.append(key.decode())
                
                if cursor == 0:
                    break
            
            logger.info(f"Discovered {len(self.streams)} streams: {self.streams}")
            
        except Exception as e:
            logger.error(f"Failed to discover streams: {e}")
    
    async def _create_consumer_groups(self):
        """Create consumer group for each discovered stream."""
        for stream in self.streams:
            try:
                # Try to create consumer group from beginning
                await self.client.xgroup_create(
                    name=stream,
                    groupname=settings.redis_consumer_group,
                    id='0',
                    mkstream=True
                )
                logger.info(f"Created consumer group '{settings.redis_consumer_group}' for {stream}")
            except redis.ResponseError as e:
                if 'BUSYGROUP' in str(e):
                    # Group already exists
                    logger.info(f"Consumer group already exists for {stream}")
                else:
                    logger.error(f"Failed to create consumer group for {stream}: {e}")
    
    async def read_frames(self) -> AsyncGenerator[FrameData, None]:
        """
        Read frames from Redis streams as an async generator.
        
        Yields:
            FrameData objects from the streams
        """
        self.running = True
        frame_counter = 0
        
        while self.running:
            try:
                # Periodically rediscover streams (every 100 frames)
                if frame_counter % 100 == 0:
                    await self._discover_streams()
                    await self._create_consumer_groups()
                
                if not self.streams:
                    logger.warning("No streams available, waiting...")
                    await asyncio.sleep(5)
                    continue
                
                # Build streams dict for XREADGROUP
                streams_dict = {stream: '>' for stream in self.streams}
                
                # Read from streams
                messages = await self.client.xreadgroup(
                    groupname=settings.redis_consumer_group,
                    consumername=settings.redis_consumer_name,
                    streams=streams_dict,
                    count=settings.redis_batch_size,
                    block=settings.redis_block_ms
                )
                
                if not messages:
                    continue
                
                # Process messages
                for stream, msg_list in messages:
                    stream_name = stream.decode() if isinstance(stream, bytes) else stream
                    
                    for msg_id, data in msg_list:
                        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                        
                        try:
                            # Parse frame data
                            frame_data = self._parse_frame_data(data)
                            frame_counter += 1
                            
                            yield frame_data
                            
                            # Acknowledge message
                            await self.client.xack(
                                stream_name,
                                settings.redis_consumer_group,
                                msg_id_str
                            )
                            
                        except Exception as e:
                            logger.error(f"Failed to parse frame from {stream_name}: {e}")
                            # Still acknowledge to avoid reprocessing
                            await self.client.xack(
                                stream_name,
                                settings.redis_consumer_group,
                                msg_id_str
                            )
                
            except asyncio.CancelledError:
                logger.info("Frame reading cancelled")
                break
            except Exception as e:
                logger.error(f"Error reading from Redis: {e}")
                await asyncio.sleep(1)
    
    def _parse_frame_data(self, data: Dict[bytes, bytes]) -> FrameData:
        """
        Parse raw Redis message data into FrameData model.
        
        Args:
            data: Raw message data from Redis
            
        Returns:
            Parsed FrameData object
        """
        # Decode string fields
        camera_id = data[b'camera_id'].decode()
        frame_number = int(data[b'frame_number'])
        timestamp = data[b'timestamp'].decode()
        frame_data_bytes = data[b'frame_data']
        frame_size = int(data[b'frame_size_bytes'])
        
        # Parse metadata if present
        metadata = None
        if b'metadata' in data:
            try:
                metadata = json.loads(data[b'metadata'].decode())
            except:
                pass
        
        return FrameData(
            camera_id=camera_id,
            frame_number=frame_number,
            timestamp=timestamp,
            frame_data=frame_data_bytes,
            frame_size_bytes=frame_size,
            metadata=metadata
        )
    
    async def stop(self):
        """Stop reading frames."""
        self.running = False
        logger.info("Stopping Redis consumer")


# Global consumer instance
redis_consumer = RedisConsumer()
