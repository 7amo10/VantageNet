"""
Video capture and frame processing service
"""
import cv2
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from app.models import CameraSourceType, CameraStatus
from app.config import settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)


class VideoCapture:
    """Handles video capture from various sources"""
    
    def __init__(
        self,
        camera_id: str,
        name: str,
        source_type: CameraSourceType,
        source_url: str,
        fps: int = 10,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.camera_id = camera_id
        self.name = name
        self.source_type = source_type
        self.source_url = source_url
        self.target_fps = fps
        self.metadata = metadata or {}
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.status = CameraStatus.INACTIVE
        self.enabled = True
        
        self.frame_count = 0
        self.frames_dropped = 0
        self.last_frame_time: Optional[datetime] = None
        self.created_at = datetime.now()
        
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._reconnect_attempts = 0
    
    async def start(self):
        """Start video capture task"""
        if self._task and not self._task.done():
            logger.warning(f"Camera {self.camera_id} already running")
            return
        
        self._stop_event.clear()
        self._task = asyncio.create_task(self._capture_loop())
        logger.info(f"Started camera {self.camera_id} ({self.name})")
    
    async def stop(self):
        """Stop video capture task"""
        if not self._task or self._task.done():
            return
        
        self._stop_event.set()
        await self._task
        self._release_capture()
        logger.info(f"Stopped camera {self.camera_id} ({self.name})")
    
    def _open_capture(self) -> bool:
        """Open video capture device"""
        try:
            # Release existing capture if any
            self._release_capture()
            
            # Determine source
            if self.source_type == CameraSourceType.WEBCAM:
                # Webcam index (e.g., "0" -> 0)
                source = int(self.source_url)
            elif self.source_type == CameraSourceType.FILE:
                # File path
                source = self.source_url
            else:  # RTSP
                # RTSP URL
                source = self.source_url
            
            # Open capture
            self.cap = cv2.VideoCapture(source)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.camera_id}: {source}")
                return False
            
            # Get actual FPS if available
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if actual_fps > 0:
                logger.info(f"Camera {self.camera_id} opened (actual FPS: {actual_fps})")
            
            self.status = CameraStatus.ACTIVE
            self._reconnect_attempts = 0
            return True
            
        except Exception as e:
            logger.error(f"Error opening camera {self.camera_id}: {e}")
            return False
    
    def _release_capture(self):
        """Release video capture device"""
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def _compress_frame(self, frame) -> Optional[bytes]:
        """
        Compress frame to JPEG with target size
        
        Args:
            frame: OpenCV frame (numpy array)
            
        Returns:
            JPEG bytes or None if compression failed
        """
        try:
            target_size = settings.frame_max_size_kb * 1024
            quality = settings.jpeg_quality
            
            # Try compression with initial quality
            for attempt in range(5):
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                success, encoded = cv2.imencode('.jpg', frame, encode_param)
                
                if not success:
                    logger.error(f"Failed to encode frame for camera {self.camera_id}")
                    return None
                
                frame_bytes = encoded.tobytes()
                frame_size = len(frame_bytes)
                
                # Check if size is acceptable
                if frame_size <= target_size:
                    logger.debug(
                        f"Compressed frame: {frame_size} bytes "
                        f"(quality: {quality})"
                    )
                    return frame_bytes
                
                # Reduce quality for next attempt
                quality = max(20, quality - 15)
            
            # Return last attempt even if over size
            logger.warning(
                f"Frame size {frame_size} bytes exceeds target {target_size} bytes "
                f"for camera {self.camera_id}"
            )
            return frame_bytes
            
        except Exception as e:
            logger.error(f"Error compressing frame: {e}")
            return None
    
    async def _capture_loop(self):
        """Main capture loop"""
        frame_interval = 1.0 / self.target_fps
        
        while not self._stop_event.is_set() and self.enabled:
            try:
                # Open capture if not opened
                if not self.cap or not self.cap.isOpened():
                    if not self._open_capture():
                        # Failed to open, attempt reconnection
                        self.status = CameraStatus.RECONNECTING
                        self._reconnect_attempts += 1
                        
                        if self._reconnect_attempts > settings.max_reconnect_attempts:
                            logger.error(
                                f"Max reconnection attempts reached for camera {self.camera_id}"
                            )
                            self.status = CameraStatus.ERROR
                            break
                        
                        logger.warning(
                            f"Reconnecting camera {self.camera_id} "
                            f"(attempt {self._reconnect_attempts})"
                        )
                        await asyncio.sleep(settings.reconnect_interval_seconds)
                        continue
                
                # Read frame
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from camera {self.camera_id}")
                    self.frames_dropped += 1
                    self._release_capture()
                    continue
                
                # Compress frame
                compressed_frame = await asyncio.to_thread(self._compress_frame, frame)
                
                if compressed_frame is None:
                    self.frames_dropped += 1
                    await asyncio.sleep(frame_interval)
                    continue
                
                # Publish to Redis
                self.frame_count += 1
                self.last_frame_time = datetime.now()
                
                success = await redis_client.publish_frame(
                    camera_id=self.camera_id,
                    frame_data=compressed_frame,
                    frame_number=self.frame_count,
                    timestamp=self.last_frame_time,
                    metadata={
                        "camera_name": self.name,
                        "source_type": self.source_type.value,
                        **self.metadata
                    }
                )
                
                if not success:
                    self.frames_dropped += 1
                
                # Maintain target FPS
                await asyncio.sleep(frame_interval)
                
            except asyncio.CancelledError:
                logger.info(f"Capture loop cancelled for camera {self.camera_id}")
                break
            except Exception as e:
                logger.error(f"Error in capture loop for camera {self.camera_id}: {e}")
                self.frames_dropped += 1
                await asyncio.sleep(frame_interval)
        
        # Cleanup
        self._release_capture()
        self.status = CameraStatus.INACTIVE if not self.enabled else CameraStatus.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "source_type": self.source_type.value,
            "source_url": self.source_url,
            "fps": self.target_fps,
            "status": self.status.value,
            "enabled": self.enabled,
            "frames_processed": self.frame_count,
            "frames_dropped": self.frames_dropped,
            "last_frame_time": self.last_frame_time,
            "created_at": self.created_at,
            "metadata": self.metadata
        }
