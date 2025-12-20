"""
WebSocket Broadcasting Service
Monitors Redis streams and broadcasts real-time updates to connected clients.
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any

import redis.asyncio as redis

from .config import settings
from .websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)


class WebSocketBroadcaster:
    """Manages background tasks for broadcasting real-time updates."""
    
    def __init__(self):
        """Initialize broadcaster."""
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self._tasks = []
        
    async def start(self):
        """Start all broadcasting tasks."""
        if self.running:
            logger.warning("Broadcaster already running")
            return
            
        try:
            # Connect to Redis
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis for WebSocket broadcasting")
            
            self.running = True
            
            # Start background tasks
            self._tasks = [
                asyncio.create_task(self._sentiment_broadcast_loop()),
                asyncio.create_task(self._alerts_monitor_loop())
            ]
            
            logger.info("WebSocket broadcaster started")
            
        except Exception as e:
            logger.error(f"Failed to start broadcaster: {e}")
            raise
    
    async def stop(self):
        """Stop all broadcasting tasks."""
        if not self.running:
            return
            
        self.running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("WebSocket broadcaster stopped")
    
    async def _sentiment_broadcast_loop(self):
        """
        Background task to broadcast sentiment updates every 2 seconds.
        Reads latest data from Redis sentiment-stats stream.
        """
        logger.info("Sentiment broadcast loop started")
        
        while self.running:
            try:
                # Get latest sentiment data from Redis stream
                sentiment_data = await self._get_latest_sentiment()
                
                if sentiment_data and ws_manager.active_connections:
                    # Broadcast to all connected clients
                    await ws_manager.send_sentiment_update(sentiment_data)
                    
                # Wait 2 seconds before next broadcast (VANTA-31 requirement)
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                logger.info("Sentiment broadcast loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in sentiment broadcast loop: {e}")
                await asyncio.sleep(2)  # Continue after error
    
    async def _alerts_monitor_loop(self):
        """
        Background task to monitor Redis alerts stream.
        Broadcasts alerts immediately when triggered.
        """
        logger.info("Alerts monitor loop started")
        
        last_id = '$'  # Start from new messages only
        
        while self.running:
            try:
                # Read from alerts stream with blocking
                # XREAD BLOCK 5000 STREAMS alerts:triggered $
                streams = await self.redis_client.xread(
                    {'alerts:triggered': last_id},
                    block=5000  # Block for 5 seconds max
                )
                
                if streams:
                    for stream_name, messages in streams:
                        for message_id, data in messages:
                            # Update last_id for next read
                            last_id = message_id
                            
                            # Parse alert data
                            alert_data = self._parse_alert_message(data)
                            
                            if alert_data:
                                # Broadcast immediately to all clients
                                await ws_manager.send_alert(alert_data)
                                logger.info(f"Alert broadcasted: {message_id}")
                
            except asyncio.CancelledError:
                logger.info("Alerts monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in alerts monitor loop: {e}")
                await asyncio.sleep(1)
    
    async def _get_latest_sentiment(self) -> Optional[Dict[str, Any]]:
        """
        Get latest sentiment data from Redis stream.
        
        Returns:
            Latest sentiment data or None if unavailable
        """
        try:
            # Read latest entry from sentiment:crowd stream
            # XREVRANGE sentiment:crowd + - COUNT 1
            entries = await self.redis_client.xrevrange(
                settings.redis_sentiment_stream,
                count=1
            )
            
            if not entries:
                return None
            
            message_id, data = entries[0]
            
            # Parse sentiment data
            return {
                "timestamp": datetime.now().isoformat(),
                "camera_id": data.get("camera_id", "unknown"),
                "total_faces": int(data.get("total_faces", 0)),
                "dominant_emotion": data.get("dominant_emotion", "neutral"),
                "mood_score": float(data.get("sentiment_score", 0.5)),
                "emotion_distribution": {
                    "happy": float(data.get("avg_happy", 0)),
                    "sad": float(data.get("avg_sad", 0)),
                    "angry": float(data.get("avg_angry", 0)),
                    "neutral": float(data.get("avg_neutral", 0)),
                    "surprise": float(data.get("avg_surprise", 0)),
                    "fear": float(data.get("avg_fear", 0)),
                    "disgust": float(data.get("avg_disgust", 0))
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting sentiment data: {e}")
            return None
    
    def _parse_alert_message(self, data: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Parse alert message from Redis stream.
        
        Args:
            data: Raw message data from Redis
            
        Returns:
            Parsed alert data or None if invalid
        """
        try:
            return {
                "alert_id": data.get("alert_id"),
                "rule_id": data.get("rule_id"),
                "camera_id": data.get("camera_id"),
                "message": data.get("message"),
                "severity": data.get("severity", "medium"),
                "triggered_at": data.get("triggered_at", datetime.now().isoformat()),
                "metadata": json.loads(data.get("metadata", "{}"))
            }
        except Exception as e:
            logger.error(f"Error parsing alert message: {e}")
            return None


# Global broadcaster instance
broadcaster = WebSocketBroadcaster()
