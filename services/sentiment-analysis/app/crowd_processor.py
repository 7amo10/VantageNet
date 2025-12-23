"""Crowd sentiment processor for VANTA-18."""
import asyncio
import logging
from datetime import datetime
from typing import Dict

from .crowd_aggregator import CrowdEmotionAggregator
from .redis_consumer import RedisConsumer
from .redis_publisher import RedisPublisher
from .database import DatabaseManager
from .rules_engine_v2 import RulesEngineV2

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
        
        # VANTA-24: Initialize rules engine for alert generation
        self.rules_engine = RulesEngineV2(db_manager=db_manager)
        
        # Metrics
        self.emotions_processed = 0
        self.sentiments_published = 0
        self.sentiments_published = 0
        self.sentiments_saved = 0
        
        # Buffer for raw emotions (VANTA-30 Analytics)
        self.raw_emotions_buffer = []
        
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
        
        # VANTA-24: Load rules from database
        try:
            await self.rules_engine.load_rules()
            logger.info(f"Loaded {len(self.rules_engine.rules)} rules from database")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
        
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
                # The emotion-detection service sends:
                # - faces: [{"bbox": [...], "confidence": x, "face_id": "face_X"}]
                # - emotions: [{"face_id": "face_X", "emotion": "sad", "confidence": x, "all_emotions": {...}}]
                # We need to use the 'emotions' field, not extract from 'faces'
                
                emotions_list = getattr(emotion_data, 'emotions', []) or []
                
                for emotion_entry in emotions_list:
                    if isinstance(emotion_entry, dict):
                        emotion = emotion_entry.get("emotion", "neutral")
                        confidence = emotion_entry.get("confidence", 0.5)
                        
                        # Add to aggregator
                        # Add to aggregator
                        self.aggregator.add_emotion(
                            camera_id=emotion_data.camera_id,
                            timestamp=emotion_data.timestamp,
                            emotion=emotion,
                            confidence=confidence
                        )
                        
                        # Buffer raw emotion for analytics
                        # Need to match keys expected by DatabaseManager.batch_save_emotions
                        self.raw_emotions_buffer.append({
                            "frame_id": getattr(emotion_data, 'frame_id', 'unknown'),
                            "face_id": emotion_entry.get("face_id", "unknown"),
                            "emotion": emotion,
                            "confidence": confidence,
                            "camera_id": emotion_data.camera_id,
                            "timestamp": emotion_data.timestamp,
                            "bounding_box": emotion_entry.get("box", {}), # 'box' from emotion-detection/models.py
                            "metadata": {}
                        })
                        
                        self.emotions_processed += 1
                
                if emotions_list:
                    logger.debug(
                        f"Processed {len(emotions_list)} emotions from {emotion_data.camera_id}, "
                        f"total: {self.emotions_processed}"
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
                await self._aggregate_and_publish()
        
        except asyncio.CancelledError:
            logger.info("Periodic publisher cancelled")
        except Exception as e:
            logger.error(f"Error in periodic publisher: {e}", exc_info=True)
    
    async def _aggregate_and_publish(self):
        """Aggregate emotions and publish sentiments (can be called manually or periodically)."""
        # Aggregate all cameras
        sentiments = self.aggregator.aggregate_all_cameras()
        
        if not sentiments:
            logger.debug("No sentiments to publish")
            return
        
        logger.info(f"Aggregated {len(sentiments)} camera sentiments")
        
        # Publish each sentiment
        for sentiment in sentiments:
            # Publish to Redis
            published = await self.redis_publisher.publish_crowd_sentiment(sentiment)
            if published:
                self.sentiments_published += 1
            
            # VANTA-24: Evaluate rules and generate alerts
            try:
                alerts = await self.rules_engine.evaluate_all(sentiment)
                if alerts:
                    logger.info(f"Generated {len(alerts)} alerts for camera {sentiment.camera_id}")
                    
                    # Store alerts to database
                    await self.rules_engine.store_alerts(alerts)
                    
                    # Publish alerts (notifications)
                    await self.rules_engine.publish_alerts(alerts)
            except Exception as e:
                logger.error(f"Error evaluating rules for camera {sentiment.camera_id}: {e}")
        
        # Batch save to database
        saved = await self.db_manager.batch_save_crowd_sentiments(sentiments)
        if saved:
            self.sentiments_saved += len(sentiments)
            logger.info(
                f"Published and saved {len(sentiments)} crowd sentiments. "
                f"Total: published={self.sentiments_published}, saved={self.sentiments_saved}"
            )

        # Save raw emotions (VANTA-30)
        if self.raw_emotions_buffer:
            logger.info(f"Saving {len(self.raw_emotions_buffer)} raw emotions to DB")
            buffer_to_save = self.raw_emotions_buffer
            self.raw_emotions_buffer = [] 
            await self.db_manager.batch_save_emotions(buffer_to_save)
    
    async def trigger_aggregation(self):
        """Manually trigger sentiment aggregation (useful for testing)."""
        logger.info("Manual aggregation triggered")
        await self._aggregate_and_publish()
    
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
