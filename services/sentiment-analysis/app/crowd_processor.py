"""Crowd sentiment processor for VANTA-18."""
import asyncio
import logging
from datetime import datetime
from typing import Dict

from .crowd_aggregator import CrowdEmotionAggregator
from .redis_consumer import RedisConsumer
from .redis_publisher import RedisPublisher
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class CrowdSentimentProcessor:
    """Processes emotions and generates crowd-level sentiment."""
    
    def __init__(
        self,
        redis_consumer: RedisConsumer,
        redis_publisher: RedisPublisher,
        db_manager: DatabaseManager,
        window_seconds: int = 30,
        publish_interval: int = 30
    ):
        """
        Initialize crowd sentiment processor.
        
        Args:
            redis_consumer: Redis consumer for reading emotions
            redis_publisher: Redis publisher for publishing sentiments
            db_manager: Database manager for persisting sentiments
            window_seconds: Aggregation window size (default: 30s)
            publish_interval: How often to publish/save sentiments (default: 30s)
        """
        self.redis_consumer = redis_consumer
        self.redis_publisher = redis_publisher
        self.db_manager = db_manager
        
        self.aggregator = CrowdEmotionAggregator(window_seconds=window_seconds)
        self.publish_interval = publish_interval
        
        # Metrics
        self.emotions_processed = 0
        self.sentiments_published = 0
        self.sentiments_saved = 0
        
        # Task handles
        self._emotion_task: asyncio.Task = None
        self._publish_task: asyncio.Task = None
        self._running = False
    
    async def start(self):
        """Start the processor tasks."""
        if self._running:
            logger.warning("Processor already running")
            return
        
        self._running = True
        logger.info("Starting crowd sentiment processor...")
        
        # Start emotion consumer task
        self._emotion_task = asyncio.create_task(self._consume_emotions())
        
        # Start periodic publish task
        self._publish_task = asyncio.create_task(self._periodic_publish())
        
        logger.info("Crowd sentiment processor started")
    
    async def stop(self):
        """Stop the processor tasks."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping crowd sentiment processor...")
        
        # Cancel tasks
        if self._emotion_task:
            self._emotion_task.cancel()
            try:
                await self._emotion_task
            except asyncio.CancelledError:
                pass
        
        if self._publish_task:
            self._publish_task.cancel()
            try:
                await self._publish_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Crowd sentiment processor stopped")
    
    async def _consume_emotions(self):
        """Consume emotions from Redis and add to aggregator."""
        try:
            async for emotion_data in self.redis_consumer.read_emotions():
                # Extract individual face emotions
                for face in emotion_data.faces:
                    # Get emotions from face
                    face_emotions = face.get("emotions", {})
                    
                    # Add each emotion to aggregator
                    for emotion, confidence in face_emotions.items():
                        self.aggregator.add_emotion(
                            camera_id=emotion_data.camera_id,
                            timestamp=emotion_data.timestamp,
                            emotion=emotion,
                            confidence=confidence
                        )
                        
                        self.emotions_processed += 1
                
                logger.debug(
                    f"Processed {len(emotion_data.faces)} faces from {emotion_data.camera_id}, "
                    f"total emotions: {self.emotions_processed}"
                )
        
        except asyncio.CancelledError:
            logger.info("Emotion consumer cancelled")
        except Exception as e:
            logger.error(f"Error consuming emotions: {e}", exc_info=True)
    
    async def _periodic_publish(self):
        """Periodically aggregate and publish crowd sentiments."""
        try:
            while self._running:
                await asyncio.sleep(self.publish_interval)
                
                # Aggregate all cameras
                sentiments = self.aggregator.aggregate_all_cameras()
                
                if not sentiments:
                    logger.debug("No sentiments to publish")
                    continue
                
                logger.info(f"Aggregated {len(sentiments)} camera sentiments")
                
                # Publish each sentiment
                for sentiment in sentiments:
                    # Publish to Redis
                    published = await self.redis_publisher.publish_crowd_sentiment(sentiment)
                    if published:
                        self.sentiments_published += 1
                
                # Batch save to database
                saved = await self.db_manager.batch_save_crowd_sentiments(sentiments)
                if saved:
                    self.sentiments_saved += len(sentiments)
                    logger.info(
                        f"Published and saved {len(sentiments)} crowd sentiments. "
                        f"Total: published={self.sentiments_published}, saved={self.sentiments_saved}"
                    )
        
        except asyncio.CancelledError:
            logger.info("Periodic publisher cancelled")
        except Exception as e:
            logger.error(f"Error in periodic publisher: {e}", exc_info=True)
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get processor metrics.
        
        Returns:
            Dictionary with metrics
        """
        buffer_stats = self.aggregator.get_buffer_stats()
        
        return {
            "emotions_processed": self.emotions_processed,
            "sentiments_published": self.sentiments_published,
            "sentiments_saved": self.sentiments_saved,
            "buffer_total_emotions": buffer_stats["total_emotions"],
            "buffer_active_cameras": buffer_stats["active_cameras"],
            "aggregation_window_seconds": buffer_stats["window_seconds"]
        }
