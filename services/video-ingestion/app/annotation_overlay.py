"""
Annotation overlay for video streams.
Reads emotion detection results from Redis and draws them on frames.
"""
import asyncio
import json
import logging
import cv2
import numpy as np
from typing import Optional, Dict, Any, List
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

# Emotion colors (BGR for OpenCV)
EMOTION_COLORS = {
    'happy': (75, 181, 16),      # Green
    'sad': (244, 130, 59),       # Blue
    'angry': (68, 68, 239),      # Red
    'surprised': (11, 158, 245), # Orange
    'surprise': (11, 158, 245),
    'neutral': (128, 114, 107),  # Gray
    'fear': (246, 92, 139),      # Purple
    'disgust': (22, 126, 249),   # Orange-red
}


class AnnotationOverlay:
    """Manages reading detection results and drawing annotations on frames."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False
        self._latest_detections: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """Connect to Redis for reading detection results."""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                decode_responses=True
            )
            await self.redis_client.ping()
            self.connected = True
            logger.info("Annotation overlay connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to connect annotation overlay to Redis: {e}")
            return False
    
    async def start(self):
        """Start the background polling task."""
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_detections())
        logger.info("Annotation overlay polling started")
    
    async def stop(self):
        """Stop the polling task."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self.redis_client:
            await self.redis_client.aclose()
        logger.info("Annotation overlay stopped")
    
    async def _poll_detections(self):
        """Background task to poll detection results from Redis."""
        while self._running:
            try:
                # Find all emotion result streams
                keys = await self.redis_client.keys("emotion:results:*")
                
                for key in keys:
                    camera_id = key.replace("emotion:results:", "")
                    
                    # Get latest detection result
                    entries = await self.redis_client.xrevrange(key, count=1)
                    if entries:
                        _, data = entries[0]
                        
                        async with self._lock:
                            self._latest_detections[camera_id] = data
                            
            except Exception as e:
                if "cancelled" not in str(e).lower():
                    logger.error(f"Error polling detections: {e}")
            
            await asyncio.sleep(0.05)  # 50ms polling interval
    
    def get_latest_detection(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest detection for a camera (sync method for frame processing)."""
        return self._latest_detections.get(camera_id)
    
    def draw_annotations(self, frame: bytes, camera_id: str) -> bytes:
        """
        Draw emotion detection annotations on a JPEG frame.
        
        Args:
            frame: JPEG-encoded frame bytes
            camera_id: Camera identifier
            
        Returns:
            JPEG-encoded frame with annotations
        """
        detection = self.get_latest_detection(camera_id)
        if not detection:
            return frame
        
        try:
            # Decode JPEG to numpy array
            np_arr = np.frombuffer(frame, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if img is None:
                return frame
            
            # Parse faces and emotions
            faces_raw = detection.get("faces", "[]")
            emotions_raw = detection.get("emotions", "[]")
            
            faces = json.loads(faces_raw) if isinstance(faces_raw, str) else faces_raw
            emotions = json.loads(emotions_raw) if isinstance(emotions_raw, str) else emotions_raw
            
            # Create emotion lookup by face_id
            emotion_lookup = {e.get("face_id"): e for e in emotions}
            
            # Draw each face
            for face in faces:
                face_id = face.get("face_id", "")
                bbox = face.get("bbox", [])
                
                if len(bbox) < 4:
                    continue
                
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                
                # Get emotion for this face
                emotion_data = emotion_lookup.get(face_id, {})
                emotion = emotion_data.get("emotion", "neutral")
                confidence = emotion_data.get("confidence", 0.0)
                
                # Get color for emotion
                color = EMOTION_COLORS.get(emotion.lower(), (128, 128, 128))
                
                # Draw bounding box
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                
                # Draw label background
                label = f"{emotion} ({confidence*100:.0f}%)"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                cv2.rectangle(img, (x1, y1 - text_height - 10), (x1 + text_width + 10, y1), color, -1)
                
                # Draw label text
                cv2.putText(img, label, (x1 + 5, y1 - 5), font, font_scale, (255, 255, 255), thickness)
            
            # Draw face count
            face_count = len(faces)
            if face_count > 0:
                count_label = f"{face_count} {'Face' if face_count == 1 else 'Faces'}"
                cv2.rectangle(img, (10, img.shape[0] - 40), (120, img.shape[0] - 10), (0, 0, 0), -1)
                cv2.putText(img, count_label, (15, img.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Re-encode as JPEG
            _, encoded = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return encoded.tobytes()
            
        except Exception as e:
            logger.error(f"Error drawing annotations: {e}")
            return frame


# Global instance
annotation_overlay = AnnotationOverlay()
