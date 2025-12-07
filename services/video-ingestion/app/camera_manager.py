"""
Camera manager - orchestrates multiple video captures
"""
import uuid
import logging
from typing import Dict, List, Optional
from app.video_capture import VideoCapture
from app.models import CameraCreate, CameraResponse, CameraSourceType

logger = logging.getLogger(__name__)


class CameraManager:
    """Manages multiple camera captures"""
    
    def __init__(self):
        self.cameras: Dict[str, VideoCapture] = {}
    
    async def add_camera(self, camera_data: CameraCreate) -> VideoCapture:
        """
        Add and start a new camera
        
        Args:
            camera_data: Camera configuration
            
        Returns:
            VideoCapture instance
        """
        camera_id = str(uuid.uuid4())
        
        camera = VideoCapture(
            camera_id=camera_id,
            name=camera_data.name,
            source_type=camera_data.source_type,
            source_url=camera_data.source_url,
            fps=camera_data.fps or 10,
            metadata=camera_data.metadata
        )
        
        camera.enabled = camera_data.enabled
        
        self.cameras[camera_id] = camera
        
        if camera.enabled:
            await camera.start()
        
        logger.info(f"Added camera {camera_id} ({camera_data.name})")
        return camera
    
    async def remove_camera(self, camera_id: str) -> bool:
        """
        Stop and remove a camera
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            bool: True if removed successfully
        """
        camera = self.cameras.get(camera_id)
        if not camera:
            return False
        
        await camera.stop()
        del self.cameras[camera_id]
        
        logger.info(f"Removed camera {camera_id}")
        return True
    
    def get_camera(self, camera_id: str) -> Optional[VideoCapture]:
        """Get camera by ID"""
        return self.cameras.get(camera_id)
    
    def list_cameras(self) -> List[VideoCapture]:
        """List all cameras"""
        return list(self.cameras.values())
    
    async def stop_all(self):
        """Stop all cameras"""
        for camera in self.cameras.values():
            await camera.stop()
        logger.info("Stopped all cameras")
    
    def get_stats(self) -> Dict:
        """Get aggregate statistics"""
        total_frames = sum(c.frame_count for c in self.cameras.values())
        total_dropped = sum(c.frames_dropped for c in self.cameras.values())
        active_cameras = sum(1 for c in self.cameras.values() if c.status.value == "active")
        
        return {
            "total_cameras": len(self.cameras),
            "active_cameras": active_cameras,
            "total_frames_processed": total_frames,
            "total_frames_dropped": total_dropped
        }


# Global camera manager instance
camera_manager = CameraManager()
