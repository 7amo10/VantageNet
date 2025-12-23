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
                asyncio.create_task(self._alerts_monitor_loop()),
                asyncio.create_task(self._emotion_events_loop())
            ]
            
            logger.info("WebSocket broadcaster started with emotion events")
            
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
                # XREAD BLOCK 5000 STREAMS alerts:events $
                streams = await self.redis_client.xread(
                    {'alerts:events': last_id},
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
    
    async def _emotion_events_loop(self):
        """
        Background task to monitor Redis emotion:results streams.
        Broadcasts ONLY the latest face detection and emotion data.
        """
        logger.info("Emotion events broadcast loop started")
        
        # Track last broadcast message ID per camera to avoid duplicates
        last_broadcast_ids: Dict[str, str] = {}
        broadcast_count = 0
        
        while self.running:
            try:
                # Discover all emotion result streams
                keys = await self.redis_client.keys("emotion:results:*")
                
                if not keys:
                    await asyncio.sleep(0.5)
                    continue
                
                for key in keys:
                    camera_id = key.replace("emotion:results:", "")
                    
                    try:
                        # Get ONLY the latest result (not historical ones)
                        entries = await self.redis_client.xrevrange(key, count=1)
                        
                        if entries:
                            message_id, data = entries[0]
                            
                            # Skip if we already broadcast this message
                            if last_broadcast_ids.get(key) == message_id:
                                continue
                            
                            last_broadcast_ids[key] = message_id
                            
                            # Check if there are active connections
                            if ws_manager.active_connections:
                                # Broadcast the latest emotion result
                                await self._broadcast_emotion_event(camera_id, data)
                                broadcast_count += 1
                                
                                if broadcast_count % 10 == 0:
                                    logger.info(f"Emotion broadcasts sent: {broadcast_count}")
                            
                    except Exception as e:
                        logger.error(f"Error reading latest from {key}: {e}")
                
                # Poll interval - 50ms for fast updates
                await asyncio.sleep(0.05)
                
            except asyncio.CancelledError:
                logger.info("Emotion events loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in emotion events loop: {e}")
                await asyncio.sleep(1)
    
    async def _broadcast_emotion_event(self, camera_id: str, data: Dict[str, str]):
        """
        Parse emotion result and broadcast to WebSocket clients.
        
        Args:
            camera_id: Camera ID from stream name
            data: Raw message data from Redis
        """
        try:
            # Parse faces and emotions from Redis data
            faces_raw = data.get("faces", "[]")
            emotions_raw = data.get("emotions", "[]")
            
            faces = json.loads(faces_raw) if isinstance(faces_raw, str) else faces_raw
            emotions = json.loads(emotions_raw) if isinstance(emotions_raw, str) else emotions_raw
            
            # Get frame dimensions (default to 640x480)
            frame_width = int(data.get("frame_width", "640"))
            frame_height = int(data.get("frame_height", "480"))
            
            if not emotions:
                return
            
            # Broadcast each detected face/emotion
            for emotion_data in emotions:
                face_id = emotion_data.get("face_id", "unknown")
                emotion = emotion_data.get("emotion", "neutral")
                confidence = float(emotion_data.get("confidence", 0.5))
                
                # Find matching bbox from faces
                bbox = {"x": 0, "y": 0, "width": 100, "height": 100}
                for face in faces:
                    if face.get("face_id") == face_id:
                        bbox_raw = face.get("bbox", [])
                        if len(bbox_raw) >= 4:
                            bbox = {
                                "x": bbox_raw[0],
                                "y": bbox_raw[1],
                                "width": bbox_raw[2] - bbox_raw[0],
                                "height": bbox_raw[3] - bbox_raw[1]
                            }
                        break
                
                # Send to WebSocket clients with frame dimensions
                await ws_manager.send_emotion_event({
                    "camera_id": camera_id,
                    "face_id": face_id,
                    "emotion": emotion,
                    "confidence": confidence,
                    "bbox": bbox,
                    "frame_width": frame_width,
                    "frame_height": frame_height,
                    "timestamp": data.get("processed_at", datetime.now().isoformat())
                })
                
                logger.debug(f"Emotion broadcasted: {camera_id} - {face_id} - {emotion}")
                
        except Exception as e:
            logger.error(f"Error broadcasting emotion event: {e}")
    
    async def _get_latest_sentiment(self) -> Optional[Dict[str, Any]]:
        """
        Get latest sentiment data from Redis stream.
        
        Returns:
            Latest sentiment data or None if unavailable
        """
        try:
            # Discover sentiment streams (sentiment:crowd:*)
            stream_keys = await self.redis_client.keys("sentiment:crowd:*")
            
            if not stream_keys:
                return None
            
            # Get latest entry from the first stream (single camera for now)
            latest_data = None
            latest_timestamp = None
            
            for stream_key in stream_keys:
                entries = await self.redis_client.xrevrange(stream_key, count=1)
                if entries:
                    message_id, data = entries[0]
                    timestamp = data.get("timestamp")
                    
                    # Keep the most recent entry across all streams
                    if latest_timestamp is None or (timestamp and timestamp > latest_timestamp):
                        latest_timestamp = timestamp
                        latest_data = data
            
            if not latest_data:
                return None
            
            # Parse emotion distribution from JSON
            emotion_dist = {}
            try:
                import json
                emotion_dist_raw = latest_data.get("emotion_distribution", "{}")
                if isinstance(emotion_dist_raw, str):
                    emotion_dist = json.loads(emotion_dist_raw)
                else:
                    emotion_dist = emotion_dist_raw
            except:
                pass
            
            # Parse sentiment data - new format from sentiment-analysis
            return {
                "timestamp": latest_data.get("timestamp", datetime.now().isoformat()),
                "camera_id": latest_data.get("camera_id", "unknown"),
                "total_faces": int(latest_data.get("total_faces_observed", 0)),
                "face_count": int(latest_data.get("total_faces_observed", 0)),
                "dominant_emotion": latest_data.get("dominant_emotion", "neutral"),
                "mood_score": float(latest_data.get("mood_score", 0.5)),
                "sentiment_score": float(latest_data.get("mood_score", 0.5)),
                "trend": latest_data.get("trend", "stable"),
                "emotion_distribution": {
                    emotion: stats.get("percentage", 0) / 100.0 if isinstance(stats, dict) else 0
                    for emotion, stats in emotion_dist.items()
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
                "alert_id": data.get("alert_id") or data.get("id"),
                "rule_id": data.get("rule_id"),
                "rule_name": data.get("rule_name"),
                "camera_id": data.get("camera_id"),
                "message": data.get("message"),
                "severity": data.get("severity", "medium"),
                # Handle timestamp / triggered_at mismatch
                "triggered_at": data.get("triggered_at") or data.get("timestamp") or datetime.now().isoformat(),
                "timestamp": data.get("input_timestamp") or data.get("timestamp"), # Pass original timestamp too
                # Handle metadata / sentiment_snapshot mismatch
                "metadata": json.loads(data.get("metadata", data.get("sentiment_snapshot", "{}")))
            }
        except Exception as e:
            logger.error(f"Error parsing alert message: {e}")
            return None


# Global broadcaster instance
broadcaster = WebSocketBroadcaster()
